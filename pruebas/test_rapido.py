"""Pruebas del trading seguido.  Uso:  python -I -m unittest discover -s pruebas -v   (desde trader-btc)"""
import datetime as dt
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import probabilidad as pb  # noqa: E402
import rapido as rp  # noqa: E402
from datos import Velas  # noqa: E402

SEG, MIN = 1000, 60_000
T0 = 1_780_000_000_000 // MIN * MIN          # un minuto exacto (UTC)


def velas_aleatorias(n, semilla=1, t0=T0, paso=SEG, vol=0.0004, p0=80_000.0):
    rnd = random.Random(semilla)
    v = Velas()
    p = p0
    for k in range(n):
        o = p
        c = o * math.exp(rnd.gauss(0, vol))
        h = max(o, c) * (1 + abs(rnd.gauss(0, vol / 2)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, vol / 2)))
        cantidad = rnd.uniform(0.01, 2.0)
        v.t.append(t0 + k * paso)
        v.o.append(o)
        v.h.append(h)
        v.l.append(l)
        v.c.append(c)
        v.v.append(cantidad)
        v.tb.append(cantidad * rnd.random())
        v.n.append(float(rnd.randint(1, 40)))
        p = c
    return v


def recorrer_lento(s, p, j0):
    for j in range(j0, min(p.fin, s.largo - 1) + 1):
        r = rp.paso_salida(p, j, s.o[j], s.h[j], s.l[j], s.c[j])
        if r:
            return r[0], j, r[1]
    j = min(p.fin, s.largo - 1)
    return "TIEMPO", j, s.c[j] * (1 - p.desliz) if p.largo else s.c[j] * (1 + p.desliz)


class Recorrido(unittest.TestCase):
    def test_saltar_minutos_da_lo_mismo_que_segundo_a_segundo(self):
        v = velas_aleatorias(30_000, semilla=5)
        s = rp.Serie(v, rasgos=False)
        rnd = random.Random(9)
        for _ in range(400):
            j0 = rnd.randint(0, 25_000)
            b = rnd.choice((0.0005, 0.001, 0.002, 0.004))
            largo = rnd.random() < 0.5
            e = s.o[j0]
            p = rp.Posicion(largo, e, e * (1 + b) if largo else e * (1 - b), e * (1 - b) if largo else e * (1 + b),
                            j0 + rnd.choice((60, 300, 900, 1800)) - 1)
            self.assertEqual(rp.recorrer(s, p, j0), recorrer_lento(s, p, j0))

    def test_con_serie_que_no_empieza_en_minuto_exacto(self):
        v = velas_aleatorias(5_000, semilla=6, t0=T0 + 17 * SEG)
        s = rp.Serie(v, rasgos=False)
        self.assertEqual(s.desfase, 43)
        e = s.o[100]
        p = rp.Posicion(True, e, e * 1.003, e * 0.997, 100 + 1799)
        self.assertEqual(rp.recorrer(s, p, 100), recorrer_lento(s, p, 100))

    def test_primer_toque_igual_a_segundo_a_segundo(self):
        v = velas_aleatorias(20_000, semilla=21, t0=T0 + 7 * SEG)
        s = rp.Serie(v, rasgos=False)
        rnd = random.Random(4)
        for _ in range(500):
            j0 = rnd.randint(0, 18_000)
            b = rnd.choice((0.0005, 0.001, 0.003))
            T = rnd.choice((60, 300, 1800))
            arriba, abajo = s.o[j0] * (1 + b) * 1.0001, s.o[j0] * (1 - b) * 0.9999
            esperado = 0
            for j in range(j0, min(j0 + T - 1, s.largo - 1) + 1):
                sube, baja = s.h[j] >= arriba, s.l[j] <= abajo
                if sube or baja:
                    esperado = 0 if (sube and baja) else (1 if sube else -1)
                    break
            self.assertEqual(rp.primer_toque(s, j0, b, T), esperado)

    def test_esperanza_y_barrera(self):
        self.assertAlmostEqual(rp.esperanza(0.002, 1.0, 0.5, 0.0, 0.0)[0], 0.0)
        el, ec = rp.esperanza(0.002, 0.8, 0.7, 0.0004, 0.0008)
        self.assertAlmostEqual(el, 0.8 * (0.7 * 0.0016 - 0.3 * 0.0028) - 0.2 * 0.0008)
        self.assertLess(ec, el)
        self.assertAlmostEqual(rp.barrera_de(0.6, 900, 1.0, 0.001), 0.0001 * 30)    # σ = 0,01 % por segundo
        self.assertEqual(rp.barrera_de(0.06, 900, 1.0, 0.001), 0.001)               # mínimo
        self.assertEqual(rp.barrera_de(float("nan"), 900, 1.0, 0.001), 0.001)

    def test_empate_en_el_mismo_segundo_es_stop(self):
        v = velas_aleatorias(200, semilla=2)
        s = rp.Serie(v, rasgos=False)
        e = 100.0
        p = rp.Posicion(True, e, 100.5, 99.5, 150)
        self.assertEqual(rp.paso_salida(p, 10, 100.0, 101.0, 99.0, 100.0)[0], "STOP")
        p = rp.Posicion(False, e, 99.5, 100.5, 150)
        self.assertEqual(rp.paso_salida(p, 10, 100.0, 101.0, 99.0, 100.0)[0], "STOP")
        self.assertIsNotNone(s)

    def test_objetivo_exige_atravesar(self):
        p = rp.Posicion(True, 100.0, 101.0, 99.0, 50)
        self.assertIsNone(rp.paso_salida(p, 1, 100.5, 101.0, 100.2, 100.8))      # tocar no basta
        self.assertEqual(rp.paso_salida(p, 1, 100.5, 101.02, 100.2, 100.8), ("OBJETIVO", 101.0))

    def test_hueco_al_abrir_por_debajo_del_stop(self):
        p = rp.Posicion(True, 100.0, 101.0, 99.0, 50, desliz=0.0)
        self.assertEqual(rp.paso_salida(p, 1, 98.0, 98.5, 97.5, 98.2), ("STOP", 98.0))


class Rasgos(unittest.TestCase):
    def test_no_miran_al_futuro(self):
        v = velas_aleatorias(8_000, semilla=3)
        s = rp.Serie(v)
        ctx = {k: 0.0 for k in ("tend1h", "pend1h", "rsi15m", "pos15m", "rsi1m", "patron1m", "atr1m", "vwap",
                                "r1d", "r3d", "oi1h", "fin", "hs", "hc")}
        i = 6000
        antes = rp.rasgos_segundo(s, i, ctx)
        v2 = velas_aleatorias(8_000, semilla=3)
        for k in range(i + 1, 8000):                     # el futuro cambia por completo
            v2.c[k] *= 1.5
            v2.h[k] *= 1.6
            v2.l[k] *= 0.5
            v2.v[k] *= 9
            v2.tb[k] = 0.0
        despues = rp.rasgos_segundo(rp.Serie(v2), i, ctx)
        self.assertEqual(antes, despues)
        self.assertEqual(len(antes), len(rp.RASGOS))
        self.assertIsNone(rp.rasgos_segundo(s, 100, ctx))

    def test_flujo_y_rango(self):
        v = velas_aleatorias(4_000, semilla=4)
        for k in range(len(v.t)):
            v.tb[k] = v.v[k]                             # todo comprador agresor
        s = rp.Serie(v)
        ctx = {k: 0.0 for k in ("tend1h", "pend1h", "rsi15m", "pos15m", "rsi1m", "patron1m", "atr1m", "vwap",
                                "r1d", "r3d", "oi1h", "fin", "hs", "hc")}
        x = dict(zip(rp.RASGOS, rp.rasgos_segundo(s, 3_900, ctx)))
        self.assertAlmostEqual(x["fl10"], 0.5)
        self.assertTrue(0.0 <= x["pr300"] <= 1.0 and 0.0 <= x["pr3600"] <= 1.0)
        self.assertAlmostEqual(x["r60"], (math.log(v.c[3900]) - math.log(v.c[3840])) * 100)

    def test_contexto_usa_solo_velas_cerradas(self):
        v1m = velas_aleatorias(6 * 1440, semilla=8, paso=MIN, vol=0.002)
        ctx = rp.Contexto(v1m)
        T = v1m.t[5000] + 30 * SEG                       # a mitad del minuto 5000
        a = ctx._calcular(T // MIN * MIN)
        v2 = velas_aleatorias(6 * 1440, semilla=8, paso=MIN, vol=0.002)
        for k in range(5000, len(v2.t)):                 # la vela en curso y lo que viene
            v2.c[k] *= 2
            v2.h[k] *= 2
            v2.l[k] *= 0.5
        b = rp.Contexto(v2)._calcular(T // MIN * MIN)
        for k in a:
            if a[k] == a[k]:
                self.assertAlmostEqual(a[k], b[k], places=9, msg=k)


class Libros(unittest.TestCase):
    def test_corto_en_futuros_con_comisiones_de_creador(self):
        inst = rp.INSTRUMENTOS["futuros"]
        lib = rp.Libro(inst, rp.Gestion(capital=10.0))
        q = 0.001
        g = lib.cerrar(False, q, 80_000.0, 79_880.0, "OBJETIVO", 0, 1, True)
        esperado = q * 120.0 - q * 80_000 * 0.0002 - q * 79_880 * 0.0002
        self.assertAlmostEqual(g, esperado, places=9)
        self.assertAlmostEqual(lib.efectivo, 10.0 + esperado, places=9)

    def test_contado_cobra_la_compra_en_btc_y_arrastra_el_polvo(self):
        inst = rp.INSTRUMENTOS["contado"]
        lib = rp.Libro(inst, rp.Gestion(capital=9.7))
        q = 0.00011
        lib.cerrar(True, q, 81_234.56, 81_234.56 * 1.01, "OBJETIVO", 0, 1, False)
        q_venta = 0.00010
        esperado = 9.7 - q * 81_234.56 + q_venta * 81_234.56 * 1.01 * 0.999
        self.assertAlmostEqual(lib.efectivo, esperado, places=9)
        self.assertAlmostEqual(lib.polvo, q * 0.999 - q_venta, places=12)

    def test_tamano_respeta_el_tres_por_ciento(self):
        lib = rp.Libro(rp.INSTRUMENTOS["futuros"], rp.Gestion(capital=10.0))
        self.assertEqual(lib.tamano(83_000.0, 0.0040), 0.0)          # 0,40 %: no cabe en el 3 %
        self.assertAlmostEqual(lib.tamano(83_000.0, 0.0015), 0.001)  # 0,15 %: una unidad mínima
        lib_c = rp.Libro(rp.INSTRUMENTOS["contado"], rp.Gestion(capital=9.7))
        q = lib_c.tamano(83_000.0, 0.002)
        self.assertLessEqual(q * 83_000.0, 9.7)
        perdida = q * 83_000.0 * (0.002 + sum(rp.INSTRUMENTOS["contado"].costos()[1:]))
        self.assertLessEqual(perdida, 9.7 * 0.03 + 1e-9)

    def test_freno_diario_salta_al_dia_siguiente(self):
        lib = rp.Libro(rp.INSTRUMENTOS["contado"], rp.Gestion(capital=10.0))
        t = int(dt.datetime(2026, 10, 20, 9, 0, tzinfo=rp.BOGOTA).timestamp() * 1000)
        self.assertIsNone(lib.frenos(t, 80_000.0))
        lib.efectivo = 8.4                                 # -16 % en el día
        volver = lib.frenos(t + 60_000, 80_000.0)
        self.assertEqual(volver, int(dt.datetime(2026, 10, 21, 0, 0, tzinfo=rp.BOGOTA).timestamp() * 1000))

    def test_entrada_de_creador_no_se_llena_sin_atravesar(self):
        v = Velas()
        for k in range(400):
            v.t.append(T0 + k * SEG)
            for campo, valor in (("o", 100.0), ("h", 100.0), ("l", 100.0), ("c", 100.0), ("v", 1.0),
                                 ("tb", 0.5), ("n", 1.0)):
                getattr(v, campo).append(valor)
        s = rp.Serie(v, rasgos=False)
        inst = rp.Instrumento("prueba", com_creador=0.0, entrada_creador=True, espera_creador=10)
        lib, _ = rp.simular_libro(s, s, 0, 400, lambda i: ("largo", 0.002), inst, rp.Gestion(capital=10.0), 60)
        self.assertEqual(lib.ciclos, [])
        self.assertGreater(lib.intentos_sin_llenar, 10)

    def test_tandas_pausan_y_frenan(self):
        g = rp.Gestion(capital=10.0, tanda=3, pausa_tanda=600, freno_tanda=0.05)
        lib = rp.Libro(rp.INSTRUMENTOS["futuros"], g)
        for k in range(3):
            lib.cerrar(True, 0.001, 80_000.0, 79_700.0, "STOP", k, k + 1, True)
            libre = lib.tras_ciclo(T0 + k * SEG, 79_700.0)
        self.assertEqual(len(lib.tandas), 1)
        self.assertTrue(lib.detenido)
        self.assertGreaterEqual(libre, T0 + 2 * SEG + 600 * SEG)


class Probabilidad(unittest.TestCase):
    def test_logistica_recupera_coeficientes(self):
        rnd = random.Random(11)
        X, y = [], []
        for _ in range(20_000):
            a, b, c = rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1)
            p = pb.sigmoide(0.3 + 1.2 * a - 0.7 * b)
            X.append([a, b, c])
            y.append(1 if rnd.random() < p else 0)
        m = pb.Logistica(["a", "b", "c"], l2=0.1).ajustar(X, y)
        self.assertAlmostEqual(m.beta[1], 1.2, delta=0.08)
        self.assertAlmostEqual(m.beta[2], -0.7, delta=0.08)
        self.assertAlmostEqual(m.beta[3], 0.0, delta=0.08)
        p = [m.prob(x) for x in X]
        self.assertGreater(pb.auc(p, y), 0.75)
        self.assertAlmostEqual(sum(p) / len(p), sum(y) / len(y), delta=0.01)
        m2 = pb.Logistica.desde_dict(m.a_dict())
        self.assertEqual(m2.prob(X[0]), m.prob(X[0]))

    def test_platt_corrige_exceso_de_confianza(self):
        rnd = random.Random(12)
        X, y = [], []
        for _ in range(10_000):
            a = rnd.gauss(0, 1)
            X.append([a])
            y.append(1 if rnd.random() < pb.sigmoide(0.5 * a) else 0)
        m = pb.Logistica(["a"], l2=0.0)
        m.media, m.desvio, m.beta = [0.0], [1.0], [0.0, 2.0]          # el doble de confiado
        m.recalibrar(X, y)
        self.assertAlmostEqual(m.platt[1], 0.25, delta=0.06)

    def test_auc_con_empates_y_extremos(self):
        self.assertEqual(pb.auc([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1]), 1.0)
        self.assertEqual(pb.auc([0.5, 0.5, 0.5, 0.5], [0, 1, 0, 1]), 0.5)

    def test_minima_para_ganar(self):
        self.assertAlmostEqual(pb.minima_para_ganar(0.004, 0.004, 0.002, 0.002), 0.75)
        self.assertAlmostEqual(pb.minima_para_ganar(0.001, 0.001, 0.0, 0.0), 0.5)


if __name__ == "__main__":
    unittest.main()
