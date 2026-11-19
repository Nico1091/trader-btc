#!/usr/bin/env python3
"""Pruebas del verificador de cifras de binarias. Biblioteca estándar.

Ejecutar:  python3 prueba_verificador.py
"""

import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verificador_cifras as v  # noqa: E402


def escribir(directorio, nombre, cabecera, filas, separador=";", bom=False):
    ruta = os.path.join(directorio, nombre)
    texto = io.StringIO()
    w = csv.writer(texto, delimiter=separador, lineterminator="\n")
    w.writerow(cabecera)
    w.writerows(filas)
    with open(ruta, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
        f.write(texto.getvalue())
    return ruta


class PruebasMatematicas(unittest.TestCase):
    def test_wilson_valor_conocido(self):
        # Intervalo de Wilson de 50 de 100 con z = 1,96: [0,4038; 0,5962]
        inf, sup = v.wilson(50, 100)
        self.assertAlmostEqual(inf, 0.4038, places=4)
        self.assertAlmostEqual(sup, 0.5962, places=4)

    def test_wilson_sin_datos(self):
        self.assertEqual(v.wilson(0, 0), (0.0, 1.0))

    def test_wilson_contiene_la_proporcion(self):
        for k, n in [(1, 10), (9829, 16961), (7121, 16961), (0, 5), (5, 5)]:
            inf, sup = v.wilson(k, n)
            self.assertLessEqual(inf, k / n)
            self.assertGreaterEqual(sup, k / n)
            self.assertGreaterEqual(inf, 0.0)
            self.assertLessEqual(sup, 1.0)

    def test_equilibrio_y_valor_esperado(self):
        self.assertAlmostEqual(v.equilibrio(0.5, 0.98), 0.5 / 0.98)
        # Con precio 0,5 y cobro 0,98, acertar la mitad da -0,02 por USDT
        self.assertAlmostEqual(v.valor_esperado(0.5, 0.5, 0.98), -0.02)
        # En el equilibrio el valor esperado es cero
        eq = v.equilibrio(0.544, 0.98)
        self.assertAlmostEqual(v.valor_esperado(eq, 0.544, 0.98), 0.0, places=12)

    def test_pago_fijo_085_da_el_54_1_del_bloc(self):
        # Pago neto 0,85 equivale a cobro/precio = 1,85 y equilibrio 1/1,85 = 54,05 %
        self.assertAlmostEqual(1 / 1.85, 0.5405, places=4)

    def test_veredicto(self):
        self.assertEqual(v.veredicto(0.51, 0.53, 0.50), "ventaja demostrada (IC 95 %)")
        self.assertEqual(v.veredicto(0.40, 0.47, 0.50), "pérdida demostrada (IC 95 %)")
        self.assertEqual(v.veredicto(0.45, 0.55, 0.50), "sin decidir")


class PruebasArchivos(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_separador_punto_y_coma_con_bom(self):
        filas = [["2021-01-01 00:00", "BAJA", "10", "acierta"]] * 3 + [["2021-01-01 00:10", "SUBE", "10", "falla"]]
        ruta = escribir(self.dir, "a_apuestas.csv",
                        ["fecha_hora_colombia", "sentido", "plazo_min", "resultado"], filas, ";", bom=True)
        res = v.analizar_archivo(ruta, [0.5], 0.98)
        self.assertEqual(res["n"], 4)
        self.assertEqual(res["aciertos"], 3)

    def test_separador_coma(self):
        filas = [["SUBE", "acierta"], ["SUBE", "falla"]]
        ruta = escribir(self.dir, "b_apuestas.csv", ["sentido", "resultado"], filas, ",")
        res = v.analizar_archivo(ruta, [0.5], 0.98)
        self.assertEqual((res["aciertos"], res["fallos"]), (1, 1))

    def test_empate_cuenta_como_fallo(self):
        filas = [["acierta"]] * 6 + [["falla"]] * 2 + [["empate"]] * 2
        ruta = escribir(self.dir, "c_apuestas.csv", ["resultado"], filas)
        res = v.analizar_archivo(ruta, [0.5], 0.98)
        self.assertEqual(res["n"], 10)
        self.assertAlmostEqual(res["acierto"], 0.6)  # 6 de 10, no 6 de 8

    def test_columna_60s_opcional(self):
        sin = escribir(self.dir, "d_apuestas.csv", ["resultado"], [["acierta"]])
        self.assertIsNone(v.analizar_archivo(sin, [0.5], 0.98)["acierto_60s"])
        con = escribir(self.dir, "e_apuestas.csv", ["resultado", "resultado_60s_tarde"],
                       [["acierta", "falla"], ["acierta", "acierta"], ["falla", "falla"], ["acierta", "falla"]])
        res = v.analizar_archivo(con, [0.5], 0.98)
        self.assertAlmostEqual(res["acierto"], 0.75)
        self.assertAlmostEqual(res["acierto_60s"], 0.25)
        self.assertIn("veredicto_60s", res["precios"][0])

    def test_valor_desconocido_es_error(self):
        ruta = escribir(self.dir, "f_apuestas.csv", ["resultado"], [["acierta"], ["quizá"]])
        with self.assertRaises(v.ErrorArchivo):
            v.analizar_archivo(ruta, [0.5], 0.98)

    def test_falta_columna_resultado_es_error(self):
        ruta = escribir(self.dir, "g_apuestas.csv", ["sentido"], [["SUBE"]])
        with self.assertRaises(v.ErrorArchivo):
            v.analizar_archivo(ruta, [0.5], 0.98)

    def test_archivo_vacio_es_error(self):
        ruta = escribir(self.dir, "h_apuestas.csv", ["resultado"], [])
        with self.assertRaises(v.ErrorArchivo):
            v.analizar_archivo(ruta, [0.5], 0.98)


class PruebasDecision(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_ventaja_grande_con_muchas_apuestas(self):
        # 6.000 aciertos de 10.000 (60 %) a precio 0,50: equilibrio 51 %, IC inferior ~59 %
        filas = [["acierta"]] * 6000 + [["falla"]] * 4000
        ruta = escribir(self.dir, "x_apuestas.csv", ["resultado"], filas)
        res = v.analizar_archivo(ruta, [0.50], 0.98)
        self.assertEqual(res["precios"][0]["veredicto"], "ventaja demostrada (IC 95 %)")
        self.assertAlmostEqual(res["pmax_ic95"], 0.98 * res["ic95"][0])

    def test_pocas_apuestas_no_deciden(self):
        # 12 de 20 a precio 0,55: el IC es amplio y cruza el equilibrio 56,1 %
        filas = [["acierta"]] * 12 + [["falla"]] * 8
        ruta = escribir(self.dir, "y_apuestas.csv", ["resultado"], filas)
        res = v.analizar_archivo(ruta, [0.55], 0.98)
        self.assertEqual(res["precios"][0]["veredicto"], "sin decidir")

    def test_perdida_grande(self):
        filas = [["falla"]] * 6000 + [["acierta"]] * 4000
        ruta = escribir(self.dir, "z_apuestas.csv", ["resultado"], filas)
        res = v.analizar_archivo(ruta, [0.50], 0.98)
        self.assertEqual(res["precios"][0]["veredicto"], "pérdida demostrada (IC 95 %)")
        self.assertLess(res["precios"][0]["ev"], 0)

    def test_precio_maximo_con_centro(self):
        filas = [["acierta"]] * 60 + [["falla"]] * 40
        ruta = escribir(self.dir, "p_apuestas.csv", ["resultado"], filas)
        res = v.analizar_archivo(ruta, [0.5], 0.98)
        self.assertAlmostEqual(res["pmax_centro"], 0.98 * 0.60)


class PruebasLinea(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _correr(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            codigo = v.main(argv)
        return codigo, out.getvalue(), err.getvalue()

    def test_carpeta_completa_y_json(self):
        escribir(self.dir, "t1_BTCUSDT_apuestas.csv", ["fecha_hora_colombia", "sentido", "plazo_min", "resultado"],
                 [["2021-01-01 00:00", "SUBE", "10", "acierta"], ["2021-01-01 00:10", "BAJA", "10", "falla"]])
        escribir(self.dir, "t1_ETHUSDT_apuestas.csv", ["resultado", "resultado_60s_tarde"],
                 [["acierta", "acierta"], ["falla", "falla"]])
        salida = os.path.join(self.dir, "res.json")
        codigo, out, err = self._correr([self.dir, "--json", salida])
        self.assertEqual(codigo, 0, err)
        self.assertIn("t1_BTCUSDT_apuestas.csv", out)
        self.assertIn("entrada 60 s tarde", out)  # solo aparece en el archivo que la trae
        import json
        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)
        self.assertEqual(len(datos["resultados"]), 2)
        self.assertEqual(datos["errores"], [])

    def test_archivo_malo_da_codigo_2_y_no_se_calla(self):
        escribir(self.dir, "bueno_apuestas.csv", ["resultado"], [["acierta"]])
        escribir(self.dir, "malo_apuestas.csv", ["resultado"], [["raro"]])
        codigo, out, err = self._correr([self.dir])
        self.assertEqual(codigo, 2)
        self.assertIn("malo_apuestas.csv", err)
        self.assertIn("bueno_apuestas.csv", out)

    def test_sin_archivos_da_codigo_2(self):
        codigo, _, err = self._correr([os.path.join(self.dir, "*_no_existe.csv")])
        self.assertEqual(codigo, 2)
        self.assertIn("no_existe", err)

    def test_cobro_y_precio_fuera_de_rango(self):
        escribir(self.dir, "ok_apuestas.csv", ["resultado"], [["acierta"]])
        self.assertEqual(self._correr([self.dir, "--cobro", "1.5"])[0], 2)
        self.assertEqual(self._correr([self.dir, "--precio", "1.2"])[0], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
