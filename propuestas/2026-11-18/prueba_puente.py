#!/usr/bin/env python3
"""Pruebas del puente entre el registro de papel y el evaluador (biblioteca estándar, unittest).

Correr:  python prueba_puente.py
Los valores esperados están calculados a mano sobre el caso de abajo, no sobre la salida del programa."""
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import puente_papel as P  # noqa: E402

T0 = 1700000000   # 2023-11-14 22:13:20 UTC = 17:13 en Colombia


def compra(W, t, lado, q, hora, sombra=False, serie="papel", compra_si=True, llenado=5):
    return {"tipo": "llenado", "serie": serie, "W": W, "t": t, "lado": lado, "compra": compra_si,
            "sombra": sombra, "llenado": llenado, "q": q, "hora": hora}


def resultado(W, t, g, serie="papel"):
    return {"tipo": "resultado", "serie": serie, "W": W, "t": t, "ganador": g, "fuente": "oficial", "hora": t + 200}


def caso():
    """Filas en el formato de operador/papel.py. Cada caso está explicado en su línea."""
    return [
        compra(5, T0, 1, 0.55, T0 + 62),                 # A: apuesta a SUBE, 0,55, gana (ganador 1)
        compra(5, T0, 1, 0.56, T0 + 72, llenado=15),     # A2: segundo llenado de la misma ventana, no cuenta
        resultado(5, T0, 1),
        compra(5, T0 + 300, -1, 0.60, T0 + 362),         # B: apuesta a BAJA, 0,60, pierde (ganador 1)
        resultado(5, T0 + 300, 1),
        compra(5, T0 + 600, 1, 0.50, T0 + 662),          # C: apuesta a SUBE, 0,50, empate (ganador 0) = fallo
        resultado(5, T0 + 600, 0),
        compra(15, T0, -1, 0.52, T0 + 62),               # D: 15 min sin ganador oficial: no cuenta
        resultado(15, T0, None),
        compra(15, T0 + 3600, 1, 0.54, T0 + 3662),       # E: 15 min sin fila de resultado: abierta
        compra(5, T0 + 900, 1, 0.53, T0 + 962, sombra=True),   # S: medición en sombra, no se opera
        resultado(5, T0 + 900, -1),
        compra(5, T0 + 1200, 1, 0.51, T0 + 1262, compra_si=False),  # escape: no es compra
        {"tipo": "mirada", "serie": "papel", "W": 5, "t": T0 + 1500, "decide": 1},
        resultado(5, T0 + 1500, 1, serie="sin_llave"),   # serie distinta: se ignora
    ]


def escribir_jsonl(ruta, filas, extra_lineas=()):
    import json
    with open(ruta, "w", encoding="utf-8") as f:
        for d in filas:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
        for linea in extra_lineas:
            f.write(linea + "\n")


class PruebasNucleo(unittest.TestCase):
    def test_apuestas_por_defecto(self):
        apuestas, cuentas, malas = P.construir([(" ", i, d) for i, d in enumerate(caso(), 1)])
        self.assertEqual(malas, [])
        self.assertEqual([(a["estrategia"], a["precio"], a["acierto"], a["fecha"]) for a in apuestas], [
            ("papel-5min", 0.55, 1, "2023-11-14"),   # A
            ("papel-5min", 0.60, 0, "2023-11-14"),   # B
            ("papel-5min", 0.50, 0, "2023-11-14"),   # C (empate cuenta como fallo)
        ])
        self.assertEqual(cuentas["compras"], 7)          # A, A2, B, C, D, E, S (el escape no cuenta)
        self.assertEqual(cuentas["llenados_extra"], 1)   # A2
        self.assertEqual(cuentas["sombra"], 1)           # S
        self.assertEqual(cuentas["abiertas"], 1)         # E
        self.assertEqual(cuentas["sin_ganador"], 1)      # D
        self.assertEqual(cuentas["empates"], 1)          # C

    def test_con_sombra_es_estrategia_aparte(self):
        apuestas, _, _ = P.construir([(" ", i, d) for i, d in enumerate(caso(), 1)], con_sombra=True)
        sombra = [a for a in apuestas if a["estrategia"] == "sombra-5min"]
        self.assertEqual(len(sombra), 1)
        self.assertEqual((sombra[0]["precio"], sombra[0]["acierto"]), (0.53, 0))  # SUBE contra ganador -1

    def test_una_apuesta_por_ventana_usa_la_primera_hora(self):
        filas = [compra(5, T0, 1, 0.58, T0 + 90), compra(5, T0, 1, 0.55, T0 + 70), resultado(5, T0, 1)]
        apuestas, _, _ = P.construir([(" ", i, d) for i, d in enumerate(filas, 1)])
        self.assertEqual(len(apuestas), 1)
        self.assertEqual(apuestas[0]["precio"], 0.55)

    def test_resultado_en_conflicto_se_excluye(self):
        filas = [compra(5, T0, 1, 0.55, T0 + 62), resultado(5, T0, 1), resultado(5, T0, -1)]
        apuestas, cuentas, _ = P.construir([(" ", i, d) for i, d in enumerate(filas, 1)])
        self.assertEqual(apuestas, [])
        self.assertEqual(cuentas["conflictos"], 1)

    def test_fecha_es_dia_de_colombia(self):
        # 1700006400 = 00:00 UTC del 15/11; en Colombia son las 19:00 del 14/11
        self.assertEqual(P._fecha(1700006400), "2023-11-14")
        self.assertEqual(P._fecha(T0), "2023-11-14")

    def test_compra_mal_formada_se_reporta(self):
        malas_esperadas = [
            compra(5, T0, 1, 1.2, T0 + 62),        # precio fuera de (0, 1)
            compra(5, T0, 0, 0.5, T0 + 62),        # lado 0
            compra(5, T0, 1, True, T0 + 62),       # precio booleano
        ]
        filas = [(" ", i, d) for i, d in enumerate(malas_esperadas, 1)]
        apuestas, _, malas = P.construir(filas)
        self.assertEqual(apuestas, [])
        self.assertEqual(len(malas), 3)

    def test_csv_tiene_las_columnas_del_evaluador(self):
        apuestas, _, _ = P.construir([(" ", i, d) for i, d in enumerate(caso(), 1)])
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "a.csv")
            P.escribir_csv(ruta, apuestas)
            with open(ruta, encoding="utf-8") as f:
                lector = csv.DictReader(f)
                self.assertEqual(lector.fieldnames, ["estrategia", "precio", "acierto", "fecha"])
                filas = list(lector)
        self.assertEqual(len(filas), 3)
        self.assertEqual(filas[0]["precio"], "0.55")


class PruebasCli(unittest.TestCase):
    def test_extremo_a_extremo_y_salida(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = os.path.join(tmp, "registro")
            os.makedirs(reg)
            escribir_jsonl(os.path.join(reg, "20231114.jsonl"), caso())
            salida = os.path.join(tmp, "apuestas.csv")
            buf = io.StringIO()
            with redirect_stdout(buf):
                codigo = P.main([reg, "--salida", salida])
            self.assertEqual(codigo, 0)
            self.assertTrue(os.path.exists(salida))
            self.assertIn("papel-5min: 3 apuestas, 1 aciertos", buf.getvalue())

    def test_estricto_con_linea_mala_no_escribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "20231114.jsonl")
            escribir_jsonl(ruta, caso(), extra_lineas=["{esto no es json"])
            salida = os.path.join(tmp, "apuestas.csv")
            with redirect_stdout(io.StringIO()):
                codigo = P.main([ruta, "--salida", salida, "--estricto"])
            self.assertEqual(codigo, 1)
            self.assertFalse(os.path.exists(salida))

    def test_sin_apuestas_no_escribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "x.jsonl")
            escribir_jsonl(ruta, [compra(5, T0, 1, 0.55, T0 + 62)])   # sin resultado: abierta
            salida = os.path.join(tmp, "apuestas.csv")
            with redirect_stdout(io.StringIO()):
                codigo = P.main([ruta, "--salida", salida])
            self.assertEqual(codigo, 1)
            self.assertFalse(os.path.exists(salida))

    def test_ruta_inexistente(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(P.main(["no_existe_esta_ruta"]), 2)

    def test_ejemplo_sintetico_es_legible_y_marcado(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "ejemplo.jsonl")
            P.generar_ejemplo(ruta)
            filas, malas = P.leer([ruta])
            self.assertEqual(malas, [])
            self.assertTrue(all(d.get("_SINTETICO") for _, _, d in filas))
            apuestas, cuentas, malas2 = P.construir(filas)
            self.assertEqual(malas2, [])
            self.assertGreater(len(apuestas), 100)


class PruebaConEvaluador(unittest.TestCase):
    """Si el evaluador de la rama propuestas/2026-11-17 está al lado, comprueba que acepta el CSV."""

    def test_el_evaluador_lee_el_csv(self):
        evaluador = os.path.join(AQUI, "..", "2026-11-17", "evaluador_ventaja.py")
        if not os.path.exists(evaluador):
            self.skipTest("evaluador_ventaja.py no está al lado; se prueba a mano según LEEME.md")
        with tempfile.TemporaryDirectory() as tmp:
            ejemplo = os.path.join(tmp, "e.jsonl")
            P.generar_ejemplo(ejemplo)
            csv_ruta = os.path.join(tmp, "apuestas.csv")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(P.main([ejemplo, "--salida", csv_ruta]), 0)
            r = subprocess.run([sys.executable, "-X", "utf8", evaluador, csv_ruta, "--min", "10"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
