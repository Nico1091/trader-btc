#!/usr/bin/env python3
"""Pruebas de vigilancia_ventaja.py. Solo biblioteca estándar.

Ejecute:  python prueba_vigilancia.py

Los valores esperados están calculados a mano (o con una fórmula escrita aparte en la prueba),
no con el propio programa, para que una prueba pueda fallar de verdad.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vigilancia_ventaja as v  # noqa: E402


def serie(n, k):
    """n resultados con exactamente k aciertos, repartidos de forma uniforme en el tiempo."""
    return [1 if int((i + 1) * k / n) > int(i * k / n) else 0 for i in range(n)]


def escribir_csv(ruta, filas, sep=",", cabecera=None, bom=False):
    """filas: lista de listas en el orden de la cabecera."""
    with open(ruta, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
        f.write(sep.join(cabecera) + "\n")
        for fila in filas:
            f.write(sep.join(str(x) for x in fila) + "\n")


def filas_de_estrategia(nombre, resultados, inicio, dias_total, precio=0.52):
    """Reparte las apuestas de forma uniforme entre inicio y inicio + dias_total."""
    n = len(resultados)
    filas = []
    for i, a in enumerate(resultados):
        dia = inicio + timedelta(days=int(i * dias_total / n))
        filas.append([nombre, f"{precio:.2f}", a, dia.strftime("%Y-%m-%d")])
    return filas


class Wilson(unittest.TestCase):
    def test_50_de_100_con_z_de_95(self):
        lo, hi = v.wilson(50, 100, 1.96)
        self.assertAlmostEqual(lo, 0.4038, places=3)
        self.assertAlmostEqual(hi, 0.5962, places=3)

    def test_sin_datos(self):
        self.assertEqual(v.wilson(0, 0, 1.96), (0.0, 1.0))


class Corrección(unittest.TestCase):
    def test_un_grupo_da_z_95_normal(self):
        self.assertAlmostEqual(v.z_corregido(1, 0.95), 1.959964, places=5)

    def test_diez_grupos_dan_bonferroni(self):
        # alfa por cola = 0,05 / (2 * 10) = 0,0025 → z = Φ⁻¹(0,9975) ≈ 2,8070
        self.assertAlmostEqual(v.z_corregido(10, 0.95), 2.8070, places=3)


class Equilibrio(unittest.TestCase):
    def test_pago_085_da_541_por_ciento(self):
        self.assertAlmostEqual(v.equilibrio(None, False, 0.85, 0.02), 1 / 1.85)
        self.assertAlmostEqual(v.equilibrio(None, False, 0.85, 0.02) * 100, 54.054, places=3)

    def test_con_precio_usa_precio_sobre_uno_menos_comision(self):
        # 0,51 / 0,98 = 0,520408...
        self.assertAlmostEqual(v.equilibrio([0.51, 0.51], True, 0.85, 0.02), 0.51 / 0.98)


class Apuestas(unittest.TestCase):
    def test_n_necesaria_con_calculo_a_mano(self):
        # ((1,96·√0,25 + 0,8416·√0,24) / 0,10)² = (0,98 + 0,41231)² / 0,01 = 193,85 → 194
        self.assertEqual(v.n_necesaria(0.60, 0.50, 1.96, 0.80), 194)

    def test_sin_ventaja_medida_no_hay_cuenta(self):
        self.assertIsNone(v.n_necesaria(0.50, 0.5405, 1.96))
        self.assertIsNone(v.n_necesaria(0.5405, 0.5405, 1.96))


class Periodos(unittest.TestCase):
    def test_trimestre_mes_y_anio(self):
        f = datetime(2024, 3, 5, 10, 0)
        self.assertEqual(v.periodo_de(f, "trimestre"), "2024-T1")
        self.assertEqual(v.periodo_de(f, "mes"), "2024-03")
        self.assertEqual(v.periodo_de(f, "anio"), "2024")
        self.assertEqual(v.periodo_de(datetime(2024, 10, 2), "trimestre"), "2024-T4")

    def test_pendiente(self):
        self.assertAlmostEqual(v._pendiente([0.5, 0.6, 0.7]), 0.1)
        self.assertAlmostEqual(v._pendiente([0.7, 0.6, 0.5]), -0.1)

    def test_serie_tiene_k_aciertos_exactos(self):
        self.assertEqual(sum(serie(3000, 1800)), 1800)
        self.assertEqual(sum(serie(150, 87)), 87)


class Lectura(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_formato_con_punto_y_coma_y_bom_como_las_pruebas_del_bloc(self):
        ruta = os.path.join(self.dir, "t.csv")
        filas = [
            ["2024-01-02 10:00", "SUBE", 10, "acierta"],
            ["2024-01-03 10:00", "BAJA", 10, "falla"],
            ["2024-01-04 10:00", "SUBE", 10, "empate"],
        ]
        escribir_csv(ruta, filas, sep=";", cabecera=["fecha_hora_colombia", "sentido", "plazo_min", "resultado"], bom=True)
        por_grupo, meta = v.leer(ruta, grupos=["sentido"])
        self.assertEqual(meta["delimitador"], ";")
        self.assertEqual(meta["empates"], 1)
        self.assertEqual(sorted(por_grupo), ["BAJA", "SUBE"])
        self.assertEqual(sum(f.acierto for f in por_grupo["SUBE"]), 1)  # el empate cuenta como fallo
        self.assertFalse(meta["usa_precio"])

    def test_formato_evaluador_con_precio_y_coma_decimal(self):
        ruta = os.path.join(self.dir, "e.csv")
        # Con decimal coma, el separador debe ser ';' (con ',' la coma partiría el número).
        escribir_csv(ruta, [["E1", "0,51", 1, "2026-11-10"], ["E1", "0,52", 0, "2026-11-11"]],
                     sep=";", cabecera=["estrategia", "precio", "acierto", "fecha"])
        por_grupo, meta = v.leer(ruta)
        self.assertTrue(meta["usa_precio"])
        self.assertAlmostEqual(por_grupo["E1"][0].precio, 0.51)
        self.assertAlmostEqual(por_grupo["E1"][1].precio, 0.52)

    def test_resultado_raro_se_rechaza_con_su_linea(self):
        ruta = os.path.join(self.dir, "r.csv")
        escribir_csv(ruta, [["E1", 1, "2026-01-01"], ["E1", 0, "2026-01-02"], ["E1", "quizás", "2026-01-03"]],
                     cabecera=["estrategia", "acierto", "fecha"])
        with self.assertRaises(v.ErrorDeDatos) as cm:
            v.leer(ruta)
        self.assertIn("línea 4", str(cm.exception))

    def test_precio_51_en_vez_de_051_se_rechaza(self):
        ruta = os.path.join(self.dir, "p.csv")
        escribir_csv(ruta, [["E1", "51", 1, "2026-01-01"]], cabecera=["estrategia", "precio", "acierto", "fecha"])
        with self.assertRaises(v.ErrorDeDatos):
            v.leer(ruta)

    def test_sin_columna_de_resultado_se_rechaza(self):
        ruta = os.path.join(self.dir, "s.csv")
        escribir_csv(ruta, [["E1", "2026-01-01"]], cabecera=["estrategia", "fecha"])
        with self.assertRaises(v.ErrorDeDatos):
            v.leer(ruta)


class Veredictos(unittest.TestCase):
    """Casos con acierto conocido. Equilibrio fijo: precio 0,52 → 0,52 / 0,98 = 0,5306."""

    INICIO = datetime(2024, 1, 1)

    def _veredicto(self, resultados, dias=730, nombre="X"):
        ruta = os.path.join(self.tmp.name, f"{nombre}.csv")
        filas = filas_de_estrategia(nombre, resultados, self.INICIO, dias)
        escribir_csv(ruta, filas, cabecera=["estrategia", "precio", "acierto", "fecha"])
        por_grupo, meta = v.leer(ruta)
        res = v.analizar(por_grupo, meta, pago=0.85, comision=0.02, confianza=0.95,
                         min_total=100, min_periodo=30)
        return res["resultados"][0]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ventaja_estable_es_sostenida(self):
        r = self._veredicto(serie(3000, 1800))  # 60 %
        self.assertEqual(r["veredicto"], "SOSTENIDA")
        self.assertEqual(r["periodos_sobre"], r["periodos_validos"])

    def test_ventaja_que_se_gasta_no_es_sostenida(self):
        # 2024-2025 al 60 %, 2026 al 49 %: el agregado supera el equilibrio, el último periodo no.
        primera = serie(2000, 1200)
        ultima = serie(1000, 490)
        r = self._veredicto(primera + ultima, dias=730 + 365)
        self.assertGreater(r["ic_bajo"], r["equilibrio"])  # el agregado sí supera el equilibrio
        self.assertEqual(r["veredicto"], "VENTAJA NO SOSTENIDA")
        self.assertFalse(r["ultimo_sobre"])
        self.assertLess(r["pendiente_pp"], 0)

    def test_sin_ventaja_es_sin_ventaja(self):
        r = self._veredicto(serie(3000, 1500))  # 50 %
        self.assertEqual(r["veredicto"], "SIN VENTAJA")
        self.assertIsNone(r["apuestas_necesarias"])

    def test_pocas_apuestas_son_prueba_insuficiente(self):
        r = self._veredicto(serie(50, 35))
        self.assertEqual(r["veredicto"], "PRUEBA INSUFICIENTE")

    def test_dos_periodos_no_dan_tendencia(self):
        # 200 apuestas en 180 días: solo 2 trimestres válidos → sin pendiente (no hay tendencia que contar)
        r = self._veredicto(serie(200, 120), dias=180)
        self.assertEqual(r["periodos_validos"], 2)
        self.assertIsNone(r["pendiente_pp"])

    def test_intervalo_que_cruza_el_equilibrio_es_inconcluso(self):
        r = self._veredicto(serie(150, 87))  # 58 %, intervalo corregido cruza 53,1 %
        self.assertEqual(r["veredicto"], "INCONCLUSA")
        self.assertIsNotNone(r["apuestas_faltan"])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ejemplo_y_analisis_completos(self):
        ruta = os.path.join(self.tmp.name, "ej.csv")
        salida = os.path.join(self.tmp.name, "res.json")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(v.main(["--ejemplo", ruta]), 0)
        self.assertIn("SINTÉTICO", out.getvalue())
        with open(ruta, encoding="utf-8") as f:
            self.assertEqual(sum(1 for _ in f), 1 + 3 * 2400)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = v.main([ruta, "--json", salida, "--detalle"])
        self.assertEqual(code, 0)
        texto = out.getvalue()
        self.assertIn("[SINTETICA-A]", texto)
        self.assertIn("[SINTETICA-B]", texto)
        self.assertIn("[SINTETICA-C]", texto)
        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)
        self.assertEqual(len(datos["resultados"]), 3)
        self.assertEqual(datos["k"], 3)

    def test_error_devuelve_codigo_2(self):
        ruta = os.path.join(self.tmp.name, "malo.csv")
        escribir_csv(ruta, [["E1", "x", "2026-01-01"]], cabecera=["estrategia", "acierto", "fecha"])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = v.main([ruta])
        self.assertEqual(code, 2)
        self.assertIn("Error", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
