#!/usr/bin/env python3
"""Pruebas del simulador de la regla de armado. Solo biblioteca estándar.

Ejecución:  python prueba_simulador.py
"""

import contextlib
import io
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import simulador_regla70 as sim  # noqa: E402

EQ = sim.equilibrio(0.85)


class Equilibrio(unittest.TestCase):
    def test_pago_085_da_54_05_por_ciento(self):
        self.assertAlmostEqual(EQ, 1 / 1.85, places=12)
        self.assertAlmostEqual(EQ, 0.5405405405, places=9)

    def test_pago_fuera_de_rango_falla(self):
        with self.assertRaises(ValueError):
            sim.equilibrio(0)
        with self.assertRaises(ValueError):
            sim.equilibrio(-1)


class ProbabilidadExacta(unittest.TestCase):
    def test_18_de_25_con_moneda_justa_es_la_suma_exacta(self):
        # Suma exacta de C(25,k) para k de 18 a 25, dividida entre 2^25 (aritmética entera, sin aproximaciones).
        suma = sum(math.comb(25, k) for k in range(18, 26))
        self.assertEqual(suma, 726206)
        self.assertAlmostEqual(sim.prob_ventana(25, 18, 0.5), suma / 2 ** 25, places=15)
        self.assertAlmostEqual(sim.prob_ventana(25, 18, 0.5), 0.0216426253, places=9)

    def test_casos_extremos(self):
        self.assertEqual(sim.prob_ventana(25, 18, 0.0), 0.0)
        self.assertEqual(sim.prob_ventana(25, 18, 1.0), 1.0)

    def test_montecarlo_de_una_ventana_coincide_con_la_exacta(self):
        rng = random.Random(12345)
        p, veces, reps = EQ, 25, 20000
        cumple = 0
        for _ in range(reps):
            aciertos = sum(1 for _ in range(veces) if rng.random() < p)
            cumple += aciertos >= 18
        self.assertAlmostEqual(cumple / reps, sim.prob_ventana(25, 18, p), delta=0.006)


class Wilson(unittest.TestCase):
    def test_limite_con_todos_aciertos_tiene_forma_cerrada(self):
        # Con k = n, la cota inferior de Wilson es exactamente 1 / (1 + z^2 / n).
        self.assertAlmostEqual(sim.cota_inferior_wilson(25, 25), 1 / (1 + 1.96 ** 2 / 25), places=12)

    def test_valor_de_18_de_25(self):
        # Valor de la fórmula de Wilson con z = 1,96, evaluada aparte del código de la simulación.
        self.assertAlmostEqual(sim.cota_inferior_wilson(18, 25), 0.524230281, places=8)

    def test_sin_apuestas_da_cero(self):
        self.assertEqual(sim.cota_inferior_wilson(0, 0), 0.0)

    def test_sin_aciertos_no_da_ventaja(self):
        # Con 0 aciertos de 10 la cota inferior es 0 (no puede ser negativa en la práctica: se acota por la fórmula).
        self.assertAlmostEqual(sim.cota_inferior_wilson(0, 10), 0.0, places=12)


class Reglas(unittest.TestCase):
    def test_k_de_n_se_cumple_desde_k(self):
        r = sim.parsear_regla("18/25", EQ)
        self.assertEqual(r.ventana, 25)
        self.assertFalse(r.cumple(17))
        self.assertTrue(r.cumple(18))
        self.assertTrue(r.cumple(25))

    def test_wilson_exige_pasar_el_equilibrio_con_muchas_apuestas(self):
        r = sim.parsear_regla("wilson:200:1.96", EQ)
        self.assertEqual(r.ventana, 200)
        self.assertFalse(r.cumple(120))  # 60 %: la cota inferior queda por debajo de 54,05 %
        self.assertTrue(r.cumple(125))   # 62,5 %: la cota inferior queda por encima

    def test_reglas_mal_escritas_fallan(self):
        for mala in ("18/17", "0/25", "xx", "wilson:200", "wilson:0:1.96", "18/25/3"):
            with self.subTest(regla=mala), self.assertRaises(ValueError):
                sim.parsear_regla(mala, EQ)


class Simulacion(unittest.TestCase):
    def test_sin_aciertos_nunca_arma(self):
        rng = random.Random(1)
        regla = sim.parsear_regla("18/25", EQ)
        for _ in range(50):
            self.assertIsNone(sim.primer_armado(rng, sim.TASAS_CENTRO_POR_DIA, [0.0] * 5, 30, regla))

    def test_con_todos_aciertos_arma_en_los_primeros_dias(self):
        rng = random.Random(2)
        regla = sim.parsear_regla("18/25", EQ)
        for _ in range(50):
            d = sim.primer_armado(rng, sim.TASAS_CENTRO_POR_DIA, [1.0] * 5, 30, regla)
            self.assertIsNotNone(d)
            self.assertLessEqual(d, 3)

    def test_ventana_incompleta_no_arma(self):
        # Con 0,01 apuestas al día no hay 25 cierres en 30 días: la regla no puede cumplirse nunca.
        rng = random.Random(3)
        regla = sim.parsear_regla("18/25", EQ)
        for _ in range(50):
            self.assertIsNone(sim.primer_armado(rng, [0.01] * 5, [1.0] * 5, 30, regla))

    def test_misma_semilla_misma_salida(self):
        regla = sim.parsear_regla("18/25", EQ)
        a = sim.estimar(regla, [0.5] * 5, sim.TASAS_CENTRO_POR_DIA, 30, 300, random.Random(99))
        b = sim.estimar(regla, [0.5] * 5, sim.TASAS_CENTRO_POR_DIA, 30, 300, random.Random(99))
        self.assertEqual(a, b)

    def test_con_moneda_justa_la_regla_actual_arma_casi_siempre(self):
        regla = sim.parsear_regla("18/25", EQ)
        prob, _ = sim.estimar(regla, [0.5] * 5, sim.TASAS_CENTRO_POR_DIA, 30, 300, random.Random(7))
        self.assertGreater(prob, 0.9)

    def test_wilson_400_casi_no_arma_sin_ventaja(self):
        regla = sim.parsear_regla("wilson:400:1.96", EQ)
        prob, _ = sim.estimar(regla, [0.5] * 5, sim.TASAS_CENTRO_POR_DIA, 30, 300, random.Random(7))
        self.assertLess(prob, 0.05)


class _AciertosFijos:
    """Generador falso: cada cierre ocurre a 1 día del anterior y el acierto sigue la lista dada (1 = acierta)."""

    def __init__(self, aciertos):
        self.aciertos = list(aciertos)
        self.i = 0

    def expovariate(self, tasa):
        return 1.0 / tasa

    def random(self):
        v = 0.1 if self.aciertos[self.i] else 0.9  # con p = 0,5: 0,1 acierta y 0,9 falla
        self.i += 1
        return v


class Determinista(unittest.TestCase):
    """Orden exacto de la ventana deslizante, sin azar: así se detecta un error de conteo o de desplazamiento."""

    def test_todos_aciertos_arma_al_llenar_la_ventana(self):
        regla = sim.parsear_regla("18/25", EQ)
        d = sim.primer_armado(_AciertosFijos([1] * 60), [1.0], [0.5], 60, regla)
        self.assertEqual(d, 25)  # antes de 25 cierres la ventana no está llena; a los 25 tiene 25 de 25

    def test_la_ventana_desplaza_los_fallos_antiguos(self):
        # 25 fallos y luego aciertos: la ventana llena (25 fallos) tiene 0; en el cierre 25 + m tiene m aciertos.
        # Con 18 de 25 la regla se cumple con m = 18, es decir, en el cierre 43.
        regla = sim.parsear_regla("18/25", EQ)
        d = sim.primer_armado(_AciertosFijos([0] * 25 + [1] * 40), [1.0], [0.5], 60, regla)
        self.assertEqual(d, 43)

    def test_sin_suficientes_aciertos_no_arma(self):
        regla = sim.parsear_regla("18/25", EQ)
        self.assertIsNone(sim.primer_armado(_AciertosFijos([1] * 17 + [0] * 40), [1.0], [0.5], 30, regla))


class Linea(unittest.TestCase):
    def test_salida_completa_y_codigo_cero(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = sim.main(["--reps", "50", "--reglas", "18/25,wilson:200:1.96", "--p", "0.5,0.58"])
        self.assertEqual(codigo, 0)
        texto = salida.getvalue()
        self.assertIn("18 de 25 (actual)", texto)
        self.assertIn("Wilson 200 apuestas", texto)
        self.assertIn("No modela", texto)

    def test_regla_mal_escrita_da_error(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            codigo = sim.main(["--reglas", "18/17"])
        self.assertEqual(codigo, 2)
        self.assertIn("error", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
