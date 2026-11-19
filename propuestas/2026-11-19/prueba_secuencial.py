#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de secuencial_ventaja.py. Ejecutar: python prueba_secuencial.py"""
import math
import os
import subprocess
import sys
import tempfile
import unittest

import secuencial_ventaja as sv


class Equilibrio(unittest.TestCase):
    def test_equilibrio_con_pago_098(self):
        self.assertAlmostEqual(sv.equilibrio(0.5), 0.5 / 0.98)
        self.assertAlmostEqual(sv.equilibrio(0.46), 0.46 / 0.98)

    def test_comision_cero_da_el_precio(self):
        self.assertAlmostEqual(sv.equilibrio(0.5, 0.0), 0.5)


class Incrementos(unittest.TestCase):
    def test_acierto_suma_y_fallo_resta(self):
        self.assertGreater(sv.incremento(0.5, True, 0.03), 0)
        self.assertLess(sv.incremento(0.5, False, 0.03), 0)

    def test_esperanza_bajo_h0_no_es_positiva(self):
        # Con p = equilibrio la esperanza del incremento es -KL(p0 || p1) <= 0:
        # una cuenta sin ventaja no deriva hacia el límite de declarar ventaja.
        for precio in (0.45, 0.5, 0.55, 0.8):
            p0 = sv.equilibrio(precio)
            for delta in (0.01, 0.03, 0.10):
                esp = p0 * sv.incremento(precio, True, delta) + (1 - p0) * sv.incremento(precio, False, delta)
                self.assertLessEqual(esp, 1e-12)
                self.assertAlmostEqual(esp, -sv.kl(p0, p0 + delta), places=12)

    def test_kl_es_cero_si_son_iguales_y_positiva_si_no(self):
        self.assertAlmostEqual(sv.kl(0.5, 0.5), 0.0)
        self.assertGreater(sv.kl(0.55, 0.5), 0)


class Umbrales(unittest.TestCase):
    def test_una_estrategia(self):
        arriba, abajo = sv.umbrales(0.05, 0.20, 1)
        self.assertAlmostEqual(arriba, math.log(20))
        self.assertAlmostEqual(abajo, math.log(0.2))

    def test_cinco_estrategias_reparten_el_alfa(self):
        arriba, _ = sv.umbrales(0.05, 0.20, 5)
        self.assertAlmostEqual(arriba, math.log(100))  # alfa por estrategia 0,01


class Lectura(unittest.TestCase):
    def test_csv_con_coma_y_punto(self):
        a = sv.cargar_apuestas('estrategia,precio,acierto,fecha\nE1,"0,51",1,2026-11-10\nE1,0.52,0,\n')
        self.assertEqual([x["precio"] for x in a], [0.51, 0.52])
        self.assertEqual([x["acierto"] for x in a], [True, False])

    def test_precio_51_se_rechaza(self):
        with self.assertRaisesRegex(sv.ErrorDatos, "línea 3"):
            sv.cargar_apuestas("estrategia,precio,acierto\nE1,0.5,1\nE1,51,1\n")

    def test_acierto_distinto_de_0_1_se_rechaza(self):
        with self.assertRaisesRegex(sv.ErrorDatos, "acierto"):
            sv.cargar_apuestas("estrategia,precio,acierto\nE1,0.5,2\n")

    def test_falta_columna(self):
        with self.assertRaisesRegex(sv.ErrorDatos, "encabezado"):
            sv.cargar_apuestas("estrategia,precio\nE1,0.5\n")

    def test_precio_donde_no_cabe_la_ventaja(self):
        with self.assertRaisesRegex(sv.ErrorDatos, "no cabe"):
            sv.cargar_apuestas("estrategia,precio,acierto\nE1,0.98,1\n", delta=0.03)

    def test_jsonl(self):
        a = sv.cargar_apuestas('{"estrategia":"E2","precio":0.4,"acierto":1}\n', formato="jsonl")
        self.assertEqual(a[0]["estrategia"], "E2")
        self.assertTrue(a[0]["acierto"])

    def test_jsonl_mal_formado_dice_la_linea(self):
        with self.assertRaisesRegex(sv.ErrorDatos, "línea 1"):
            sv.cargar_apuestas("{no es json}\n", formato="jsonl")


class Analisis(unittest.TestCase):
    def test_todo_aciertos_declara_ventaja_en_el_n_exacto(self):
        apuestas = [{"estrategia": "E1", "precio": 0.5, "acierto": True, "fecha": ""}] * 200
        res = sv.analizar(apuestas, delta=0.03, alfa=0.05, beta=0.2)
        r = res["resultados"][0]
        inc = sv.incremento(0.5, True, 0.03)
        n_esperado = math.ceil(sv.umbrales(0.05, 0.2, 1)[0] / inc)
        self.assertEqual(r["estado"], "VENTAJA")
        self.assertEqual(r["decidida_en"], n_esperado)

    def test_todo_fallos_descarta_sin_ventaja(self):
        apuestas = [{"estrategia": "E1", "precio": 0.5, "acierto": False, "fecha": ""}] * 100
        res = sv.analizar(apuestas, delta=0.03, alfa=0.05, beta=0.2)
        r = res["resultados"][0]
        self.assertEqual(r["estado"], "SIN VENTAJA")
        self.assertIsNone(r["faltan_aprox"])

    def test_pocas_apuestas_quedan_abiertas_y_dicen_cuantas_faltan(self):
        apuestas = [{"estrategia": "E1", "precio": 0.5, "acierto": i % 2 == 0, "fecha": ""} for i in range(10)]
        res = sv.analizar(apuestas, delta=0.03, alfa=0.05, beta=0.2)
        r = res["resultados"][0]
        self.assertEqual(r["estado"], "ABIERTA")
        self.assertGreater(r["faltan_aprox"], 0)

    def test_cada_estrategia_se_mira_por_separado(self):
        apuestas = ([{"estrategia": "E1", "precio": 0.5, "acierto": True, "fecha": ""}] * 200
                    + [{"estrategia": "E2", "precio": 0.5, "acierto": False, "fecha": ""}] * 100)
        res = sv.analizar(apuestas, delta=0.03, alfa=0.05, beta=0.2)
        estados = {r["estrategia"]: r["estado"] for r in res["resultados"]}
        self.assertEqual(estados, {"E1": "VENTAJA", "E2": "SIN VENTAJA"})


class Simulacion(unittest.TestCase):
    def test_sin_ventaja_la_prueba_secuencial_casi_nunca_arma(self):
        # Garantía teórica: P(arma por azar) <= alfa = 0,05. Con 300 réplicas
        # y semilla fija, el resultado es fijo; el umbral 0,10 deja margen.
        r = sv.simular(K=5, horizonte=600, reps=300, semilla=3, ventaja_real=0.0)
        self.assertLessEqual(r["secuencial"]["p_armar"], 0.10)

    def test_la_regla_actual_arma_casi_siempre_sin_ventaja(self):
        r = sv.simular(K=5, horizonte=600, reps=300, semilla=3, ventaja_real=0.0)
        self.assertGreater(r["actual"]["p_armar"], 0.90)

    def test_con_ventaja_grande_la_secuencial_arma(self):
        r = sv.simular(K=5, horizonte=1000, reps=100, semilla=5, ventaja_real=0.10)
        self.assertGreater(r["secuencial"]["p_armar"], 0.90)
        self.assertIsNotNone(r["secuencial"]["mediana_apuestas"])

    def test_misma_semilla_mismo_resultado(self):
        a = sv.simular(K=2, horizonte=200, reps=50, semilla=9)
        b = sv.simular(K=2, horizonte=200, reps=50, semilla=9)
        self.assertEqual(a, b)


class Linea(unittest.TestCase):
    def test_ejemplo_y_analisis_por_linea_de_comandos(self):
        carpeta = os.path.dirname(os.path.abspath(__file__))
        with tempfile.TemporaryDirectory(dir=carpeta) as tmp:
            ruta = os.path.join(tmp, "ejemplo.csv")
            self.assertEqual(sv.main(["--ejemplo", ruta]), 0)
            self.assertEqual(sv.main([ruta]), 0)
            res = subprocess.run([sys.executable, os.path.join(carpeta, "secuencial_ventaja.py"), ruta],
                                 capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0)
            self.assertIn("ABIERTA", res.stdout)

    def test_error_de_datos_sale_con_codigo_2(self):
        carpeta = os.path.dirname(os.path.abspath(__file__))
        with tempfile.TemporaryDirectory(dir=carpeta) as tmp:
            ruta = os.path.join(tmp, "malo.csv")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("estrategia,precio,acierto\nE1,51,1\n")
            self.assertEqual(sv.main([ruta]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
