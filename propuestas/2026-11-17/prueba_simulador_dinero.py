#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas del simulador del dinero real de binarias (solo biblioteca estándar).

Ejecutar:  python3 prueba_simulador_dinero.py
Los valores esperados se calcularon a mano o con una fórmula aparte (se indica en cada prueba).
"""

import contextlib
import io
import random
import unittest

import simulador_dinero_real as S


def estado_armado(saldo=20.50):
    e = S.Estado(saldo)
    e.fijar_dia(0)
    e.armado = True
    return e


class Economia(unittest.TestCase):
    def test_cobro_0_98_entre_precio(self):
        # El bloc dice «2,13 = 0,98 / 0,46».
        self.assertAlmostEqual(S.pago_bruto(0.46), 2.13043, places=4)

    def test_mercado_justo_pierde_la_comision(self):
        # Si el acierto iguala al precio, cada USDT pierde 2 %: −0,02 para cualquier precio.
        for p in (0.46, 0.544, 0.58, 0.8):
            self.assertAlmostEqual(S.valor_esperado_por_usdt(p, p), -0.02, places=9)

    def test_equilibrio_precio_entre_0_98(self):
        # 0,544 ÷ 0,98 = 0,55510...
        self.assertAlmostEqual(S.equilibrio(0.544), 0.555102, places=5)

    def test_valor_esperado_formula_a_mano(self):
        # acierto 0,6 y precio 0,5: 0,6 · (0,98/0,5 − 1) − 0,4 = 0,6 · 0,96 − 0,4 = 0,176
        self.assertAlmostEqual(S.valor_esperado_por_usdt(0.6, 0.5), 0.176, places=9)

    def test_valor_esperado_cero_en_el_equilibrio(self):
        for p in (0.46, 0.544, 0.58):
            self.assertAlmostEqual(S.valor_esperado_por_usdt(S.equilibrio(p), p), 0.0, places=9)

    def test_azar_18_de_25(self):
        # Suma exacta de C(25,k) para k = 18..25, dividida entre 2^25 = 726206 / 33554432.
        self.assertAlmostEqual(S.prob_cola(25, 18), 726206 / 33554432, places=12)
        self.assertAlmostEqual(S.prob_cola(25, 18), 0.0216, places=4)

    def test_montecarlo_coincide_con_la_formula(self):
        # Con 200 000 apuestas de 1 USDT a acierto 0,6 y precio 0,5, la ganancia media debe ser 0,176.
        rng = random.Random(7)
        n = 200000
        total = 0.0
        for _ in range(n):
            total += S.ganancia_si_acierta(0.5) if rng.random() < 0.6 else -1.0
        self.assertAlmostEqual(total / n, 0.176, delta=0.005)


class Compuerta(unittest.TestCase):
    def test_19_de_25_es_el_minimo(self):
        self.assertFalse(S.compuerta_orden(18, 0.544))
        self.assertTrue(S.compuerta_orden(19, 0.544))

    def test_el_precio_alto_anula_la_ganancia(self):
        # Con 19 de 25 a precio 0,99 el neto es 19 · (0,98/0,99 − 1) − 6 < 0: no compra.
        self.assertFalse(S.compuerta_orden(19, 0.99))

    def test_precio_bajo_deja_pasar(self):
        self.assertTrue(S.compuerta_orden(19, 0.46))


class Armado(unittest.TestCase):
    def _llenar(self, e, aciertos_de_25, estrategia="E1"):
        for i in range(25):
            e.registrar(estrategia, i < aciertos_de_25)

    def test_18_de_25_arma(self):
        e = S.Estado(20.50)
        self._llenar(e, 18)
        self.assertTrue(e.regla_cumplida())

    def test_17_de_25_no_arma(self):
        e = S.Estado(20.50)
        self._llenar(e, 17)
        self.assertFalse(e.regla_cumplida())

    def test_menos_de_25_cerradas_no_cuentan(self):
        e = S.Estado(20.50)
        for _ in range(24):
            e.registrar("E1", True)
        self.assertIsNone(e.k_de("E1"))
        self.assertFalse(e.regla_cumplida())

    def test_cualquier_estrategia_basta(self):
        e = S.Estado(20.50)
        self._llenar(e, 10, "E1")
        self._llenar(e, 18, "E3")
        self.assertTrue(e.regla_cumplida())


class Frenos(unittest.TestCase):
    def test_cupo_inicial_es_16_por_ciento(self):
        # 20,50 · 0,16 = 3,28 USDT.
        self.assertAlmostEqual(estado_armado().cupo(), 3.28, places=9)

    def test_con_una_orden_abierta_no_cabe_otra(self):
        # 3,28 − 2 = 1,28 < 2: no entra una segunda orden mientras la primera está abierta.
        e = estado_armado()
        e.abrir(0.544)
        self.assertEqual(e.motivo_no_comprar(19, 0.544), "freno del día")

    def test_una_perdida_apaga_el_dia(self):
        # Después de perder 2 USDT: cupo 1,28 < 2. Lo que dice el bloc: la primera pérdida apaga el día.
        e = estado_armado()
        o = e.abrir(0.544)
        e.liquidar(o, False)
        self.assertAlmostEqual(e.pnl_dia, -2.0, places=9)
        self.assertEqual(e.motivo_no_comprar(19, 0.544), "freno del día")

    def test_una_ganancia_restaura_el_cupo(self):
        # Ganar 2 · (0,98/0,544 − 1) = 1,6029 USDT resta de lo perdido: cupo 4,88, se puede comprar.
        e = estado_armado()
        o = e.abrir(0.544)
        e.liquidar(o, True)
        self.assertAlmostEqual(e.pnl_dia, 2 * (0.98 / 0.544 - 1), places=9)
        self.assertIsNone(e.motivo_no_comprar(19, 0.544))

    def test_dia_nuevo_reinicia_el_freno(self):
        e = estado_armado()
        o = e.abrir(0.544)
        e.liquidar(o, False)
        self.assertEqual(e.motivo_no_comprar(19, 0.544), "freno del día")
        e.fijar_dia(1)
        # Saldo 18,50: cupo 0,16 · 18,50 = 2,96 ≥ 2.
        self.assertIsNone(e.motivo_no_comprar(19, 0.544))

    def test_tope_de_20_ordenes_al_dia(self):
        e = estado_armado(saldo=1000.0)   # con saldo grande el freno no estorba: solo cuenta el tope
        for _ in range(20):
            e.liquidar(e.abrir(0.544), True)
        self.assertEqual(e.ordenes_dia, 20)
        self.assertEqual(e.motivo_no_comprar(19, 0.544), "tope diario de órdenes")

    def test_tope_por_orden_16_por_ciento_del_saldo(self):
        # Con 10 USDT el 16 % son 1,60: no cabe una orden de 2.
        e = estado_armado(saldo=10.0)
        self.assertEqual(e.motivo_no_comprar(19, 0.544), "tope por orden (16 % del saldo)")

    def test_sin_armar_no_compra(self):
        e = S.Estado(20.50)
        e.fijar_dia(0)
        self.assertEqual(e.motivo_no_comprar(19, 0.544), "no armado")

    def test_el_perdido_nunca_pasa_del_freno(self):
        e = estado_armado()
        o = e.abrir(0.544)
        self.assertLessEqual(e.perdido(), S.FRENO_DIA * e.saldo_dia + 1e-9)
        e.liquidar(o, False)
        self.assertLessEqual(e.max_frac, S.FRENO_DIA + 1e-9)


class Replicas(unittest.TestCase):
    def test_misma_semilla_mismo_resultado(self):
        cfg = S.Escenario(precio=0.46, ventaja=0.14, dias=10)
        a = S.replica(cfg, random.Random(5))
        b = S.replica(cfg, random.Random(5))
        self.assertEqual(a, b)

    def test_sin_aprobacion_de_la_ia_no_hay_ordenes(self):
        cfg = S.Escenario(precio=0.46, ventaja=0.14, dias=30, aprobacion=0.0)
        for r in range(50):
            res = S.replica(cfg, random.Random(100 + r))
            self.assertEqual(res["ordenes"], 0)
            self.assertEqual(res["pnl"], 0.0)

    def test_pnl_cuadra_con_aciertos_y_fallos(self):
        # Todas las órdenes se liquidan dentro del periodo: pnl = aciertos · 2 · (0,98/p − 1) − fallos · 2.
        cfg = S.Escenario(precio=0.46, ventaja=0.16, dias=30)
        gan = 2 * S.ganancia_si_acierta(0.46)
        for r in range(60):
            res = S.replica(cfg, random.Random(900 + r))
            fallos = res["ordenes"] - res["aciertos"]
            esperado = res["aciertos"] * gan - fallos * 2.0
            self.assertAlmostEqual(res["pnl"], esperado, places=6)

    def test_el_freno_nunca_se_rompe(self):
        # Con acierto alto y precio bajo hay muchas órdenes: ninguna réplica puede pasar del 16 % del día.
        cfg = S.Escenario(precio=0.46, ventaja=0.16, dias=30)
        ordenes = 0
        for r in range(300):
            res = S.replica(cfg, random.Random(4000 + r))
            ordenes += res["ordenes"]
            self.assertLessEqual(res["max_frac"], S.FRENO_DIA + 1e-9)
        self.assertGreater(ordenes, 0, "la prueba debe ejercitar órdenes para tener valor")

    def test_tope_total_detiene_las_compras(self):
        # Mercado justo a precio 0,58: el armado se produce casi siempre y hay muchas pérdidas.
        # Con tope del 10 % el saldo no baja del suelo (18,45) más de una orden de 2 USDT: la pérdida no pasa de −4,05.
        # Sin tope, en las mismas réplicas, sí se pasa (medido: −10,0 en el peor caso).
        con = S.Escenario(precio=0.58, ventaja=0.0, dias=30, tope_total=0.10)
        sin = S.Escenario(precio=0.58, ventaja=0.0, dias=30, tope_total=0.0)
        peor_con, peor_sin = 0.0, 0.0
        perdidas_con = 0
        for r in range(200):
            rc = S.replica(con, random.Random(7000 + r))
            rs = S.replica(sin, random.Random(7000 + r))
            peor_con = min(peor_con, rc["pnl"])
            peor_sin = min(peor_sin, rs["pnl"])
            perdidas_con += rc["pnl"] < -2.0
        self.assertGreaterEqual(peor_con, -4.05 - 1e-9)
        self.assertLess(peor_sin, -4.05, "sin tope las mismas réplicas deben perder más")
        self.assertGreater(perdidas_con, 0, "la prueba debe ejercitar pérdidas para tener valor")

    def test_correr_es_repetible(self):
        cfg = S.Escenario(precio=0.544, ventaja=0.027, dias=30)
        a = S.correr(cfg, 40, 2026)
        b = S.correr(cfg, 40, 2026)
        self.assertEqual(a, b)


class Interfaz(unittest.TestCase):
    def test_cli_corre_y_escribe_tabla(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            codigo = S.principal(["--reps", "20", "--dias", "5", "--ventaja", "0", "--precio", "0.544"])
        self.assertEqual(codigo, 0)
        self.assertIn("P(armado)", buf.getvalue())

    def test_listas_con_punto_y_coma_y_coma_decimal(self):
        # «0,46;0,544» son dos precios, no cuatro: la coma decimal no separa.
        self.assertEqual(S.lista_numeros("0,46;0,544"), [0.46, 0.544])
        self.assertEqual(S.lista_numeros("0.5; 0.60"), [0.5, 0.6])

    def test_cli_rechaza_numeros_malos(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                S.principal(["--precio", "abc"])
        self.assertEqual(cm.exception.code, 2)

    def test_cli_rechaza_precio_fuera_de_rango(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                S.principal(["--precio", "1,5"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
