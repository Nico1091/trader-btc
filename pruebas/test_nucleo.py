"""Pruebas del núcleo.  Uso:  python -I -m unittest discover -s pruebas -v   (desde trader-btc)"""
import math
import os
import random
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import indicadores as ind  # noqa: E402
from datos import Velas  # noqa: E402
from simulador import Reglas, Senal, simular  # noqa: E402
import red  # noqa: E402

MIN = 60_000


def velas_1m(precios, t0=1_700_000_000_000 // MIN * MIN):
    """precios: lista de (o, h, l, c) por minuto."""
    v = Velas()
    for k, (o, h, l, c) in enumerate(precios):
        v.t.append(t0 + k * MIN)
        v.o.append(o)
        v.h.append(h)
        v.l.append(l)
        v.c.append(c)
        v.v.append(1.0)
        v.tb.append(0.5)
    return v


class Indicadores(unittest.TestCase):
    def test_pendiente_exacta(self):
        c = [100 * 1.01 ** i for i in range(50)]
        p = ind.pendiente_log(c, 10)
        self.assertTrue(math.isnan(p[8]))
        self.assertAlmostEqual(p[20], (1.01 ** 9 - 1) * 100, places=6)
        self.assertAlmostEqual(p[49], (1.01 ** 9 - 1) * 100, places=6)

    def test_maximo_minimo_fuerza_bruta(self):
        rnd = random.Random(7)
        h = [rnd.uniform(1, 2) for _ in range(500)]
        l = [x - rnd.uniform(0, 0.5) for x in h]
        mx, mn = ind.maximo_minimo(h, l, 17)
        for i in range(16, 500):
            self.assertEqual(mx[i], max(h[i - 16:i + 1]))
            self.assertEqual(mn[i], min(l[i - 16:i + 1]))

    def test_sin_mirar_al_futuro(self):
        rnd = random.Random(3)
        c = [100.0]
        for _ in range(400):
            c.append(c[-1] * (1 + rnd.gauss(0, 0.01)))
        base = ind.ema(c, 20)[:300], ind.rsi(c, 14)[:300], ind.pendiente_log(c, 24)[:300]
        c2 = c[:300] + [x * 3 for x in c[300:]]          # cambiar el futuro no puede cambiar el pasado
        otra = ind.ema(c2, 20)[:300], ind.rsi(c2, 14)[:300], ind.pendiente_log(c2, 24)[:300]
        for a, b in zip(base, otra):
            self.assertEqual([x for x in a if x == x], [x for x in b if x == x])

    def test_alinear_no_usa_vela_abierta(self):
        t15 = [k * 15 * MIN for k in range(16)]
        t60 = [k * 60 * MIN for k in range(4)]
        idx = ind.alinear(t15, 15 * MIN, t60, 60 * MIN)
        self.assertEqual(idx[2], -1)          # la de 15m que cierra a los 45 min no ve ninguna de 1h
        self.assertEqual(idx[3], 0)           # la que cierra a los 60 min ya ve la primera hora
        self.assertEqual(idx[6], 0)
        self.assertEqual(idx[7], 1)

    def test_envolvente_alcista(self):
        o = [10, 10, 9.5, 9.0]
        c = [10, 9.5, 9.0, 9.8]
        h = [10.1, 10.1, 9.6, 9.9]
        l = [9.9, 9.4, 8.9, 8.95]
        puntaje, nombres = ind.patrones(o, h, l, c, 3, True, False)
        self.assertIn("envolvente_alcista", nombres)
        self.assertGreater(puntaje, 0)


class Simulador(unittest.TestCase):
    def reglas(self, **kw):
        return Reglas(capital=10.0, comision=0.001, deslizamiento=0.0, paso=0.00001, nocional_min=5.0, **kw)

    def test_objetivo_con_comisiones_y_polvo(self):
        p = 81234.56
        precios = [(p,) * 4] * 3 + [(p, p * 1.015, p * 0.999, p * 1.012)] + [(p * 1.012,) * 4] * 5
        v = velas_1m(precios)
        s = Senal(v.t[0] + MIN, stop_pct=0.01, objetivo_pct=0.01, max_min=30)
        r = simular(v, [s], Reglas(capital=9.7, comision=0.001, deslizamiento=0.0, riesgo_max=1.0))
        op = r["operaciones"][0]
        self.assertEqual(op["motivo"], "OBJETIVO")
        self.assertAlmostEqual(op["entrada"], p)
        self.assertAlmostEqual(op["salida"], p * 1.01)
        q = 0.00011                                   # 9,7 USDT / 81.234,56 = 0,000119 -> 11 pasos
        q_neto = q * 0.999                            # la comisión de compra se cobra en BTC
        q_venta = 0.00010                             # solo 10 pasos enteros se pueden vender
        esperado = 9.7 - q * p + q_venta * p * 1.01 * 0.999
        self.assertAlmostEqual(r["efectivo"], esperado, places=9)
        self.assertAlmostEqual(r["polvo_btc"], q_neto - q_venta, places=12)

    def test_el_polvo_se_vende_con_la_siguiente(self):
        p = 81234.56
        precios = [(p,) * 4] * 2 + [(p, p * 1.012, p, p)] + [(p,) * 4] * 4 + [(p, p * 1.012, p, p)] + [(p,) * 4] * 3
        v = velas_1m(precios)
        s1 = Senal(v.t[0] + MIN, 0.01, 0.01, 3)
        s2 = Senal(v.t[5] + MIN, 0.01, 0.01, 3)
        r = simular(v, [s1, s2], Reglas(capital=9.7, comision=0.001, deslizamiento=0.0, riesgo_max=1.0))
        self.assertEqual(len(r["operaciones"]), 2)
        self.assertLess(r["polvo_btc"], 0.00001)       # el polvo nunca pasa de un paso: se arrastra

    def test_empate_en_el_mismo_minuto_cuenta_como_stop(self):
        precios = [(100.0,) * 4] * 2 + [(100.0, 101.5, 98.5, 100.0)] + [(100.0,) * 4] * 3
        v = velas_1m(precios)
        s = Senal(v.t[0] + MIN, stop_pct=0.01, objetivo_pct=0.01, max_min=30)
        op = simular(v, [s], self.reglas(riesgo_max=1.0))["operaciones"][0]
        self.assertEqual(op["motivo"], "STOP")
        self.assertLess(op["ganancia_usdt"], 0)

    def test_apertura_por_debajo_del_stop_se_llena_en_la_apertura(self):
        precios = [(100.0,) * 4] * 2 + [(97.0, 97.5, 96.5, 97.0)] + [(97.0,) * 4] * 2
        v = velas_1m(precios)
        s = Senal(v.t[0] + MIN, stop_pct=0.01, objetivo_pct=0.02, max_min=30)
        op = simular(v, [s], self.reglas(riesgo_max=1.0))["operaciones"][0]
        self.assertEqual(op["motivo"], "STOP")
        self.assertAlmostEqual(op["salida"], 97.0)

    def test_minimo_nocional_omite(self):
        v = velas_1m([(100.0,) * 4] * 10)
        s = Senal(v.t[0] + MIN, stop_pct=0.01, objetivo_pct=0.02, max_min=5)
        r = simular(v, [s], Reglas(capital=4.0, comision=0.001, deslizamiento=0.0))
        self.assertEqual(r["operaciones"], [])
        self.assertEqual(r["omitidas"]["minimo"], 1)

    def test_riesgo_limita_el_tamano(self):
        v = velas_1m([(100.0,) * 4] * 2 + [(100.0, 100.0, 89.0, 90.0)] + [(90.0,) * 4] * 2)
        s = Senal(v.t[0] + MIN, stop_pct=0.10, objetivo_pct=0.2, max_min=30)
        r = simular(v, [s], Reglas(capital=200.0, comision=0.001, deslizamiento=0.0, riesgo_max=0.03))
        op = r["operaciones"][0]
        self.assertLessEqual(-op["ganancia_usdt"], 200.0 * 0.03 * 1.001)

    def test_no_se_abren_dos_posiciones(self):
        v = velas_1m([(100.0,) * 4] * 40)
        s1 = Senal(v.t[0] + MIN, 0.01, 0.01, 20)
        s2 = Senal(v.t[5] + MIN, 0.01, 0.01, 20)
        r = simular(v, [s1, s2], self.reglas(riesgo_max=1.0))
        self.assertEqual(len(r["operaciones"]), 1)
        self.assertEqual(r["omitidas"]["posicion_abierta"], 1)


class WebSocket(unittest.TestCase):
    def test_marco_enmascarado_ida_y_vuelta(self):
        ws = red.WebSocket("wss://ejemplo.invalid/x")
        enviados = []

        class Falso:
            def sendall(self, b):
                enviados.append(b)

        ws.sock = Falso()
        ws.enviar("hola " * 40)
        marco = enviados[0]
        self.assertEqual(marco[0], 0x81)
        self.assertTrue(marco[1] & 0x80)                # el cliente siempre enmascara
        largo = struct.unpack(">H", marco[2:4])[0]
        mascara = marco[4:8]
        carga = bytes(c ^ mascara[i % 4] for i, c in enumerate(marco[8:8 + largo]))
        self.assertEqual(carga.decode(), "hola " * 40)
        # el servidor responde sin máscara: lo leemos con el lector real
        ws._buf = bytearray(b"\x81\x05hola!")
        self.assertEqual(ws.recibir(), "hola!")


if __name__ == "__main__":
    unittest.main()
