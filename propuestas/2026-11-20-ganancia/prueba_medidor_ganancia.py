#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas del medidor de ganancia. Solo biblioteca estándar.

  python3 prueba_medidor_ganancia.py            # corre las pruebas
  python3 prueba_medidor_ganancia.py --generar  # escribe ejemplo_SINTETICO.csv (datos inventados)
"""

import csv
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import medidor_ganancia as mg  # noqa: E402

EJEMPLO = os.path.join(AQUI, "ejemplo_SINTETICO.csv")

# (nombre, precio base, aciertos exactos de cada 400, apuestas)
ESCENARIOS = [
    ("A_moneda_al_50", 0.50, 200, 400),
    ("B_acierta_caro", 0.80, 296, 400),   # 74 % de acierto: supera 18 de 25, pero pierde dinero
    ("C_barato_gana", 0.20, 250, 1000),   # 25 % a precio 0,20: gana dinero (hace falta muestra con 5 estrategias)
    ("D_barato_azar", 0.20, 80, 400),     # 20 % a precio 0,20: equilibrio
    ("E_pocas", 0.30, 36, 60),            # muestra corta
]


def generar(ruta):
    rng = random.Random(20261120)
    filas = []
    for nombre, base, aciertos, n in ESCENARIOS:
        pesos = [1] * aciertos + [0] * (n - aciertos)
        rng.shuffle(pesos)
        for w in pesos:
            p = round(min(0.99, max(0.01, base + rng.uniform(-0.02, 0.02))), 2)
            filas.append({"estrategia": nombre, "precio": "%.2f" % p, "acierto": w})
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        esc = csv.DictWriter(f, fieldnames=["estrategia", "precio", "acierto"])
        esc.writeheader()
        esc.writerows(filas)
    return len(filas)


class Convencion(unittest.TestCase):
    def test_pago_si_acierta_a_046(self):
        r = mg.evaluar([(0.46, 1)] * 10, B=200)
        self.assertAlmostEqual(r["usdt_por_apuesta"], 0.98 / 0.46 - 1, places=9)  # 1,1304

    def test_falla_pierde_una_unidad(self):
        r = mg.evaluar([(0.46, 0)] * 10, B=200)
        self.assertAlmostEqual(r["usdt_por_apuesta"], -1.0, places=9)

    def test_equilibrio_a_precio_fijo(self):
        r = mg.evaluar([(0.80, 1)] * 5 + [(0.80, 0)] * 5, B=200)
        self.assertAlmostEqual(r["equilibrio"], 0.80 / 0.98, places=9)  # 81,6 %

    def test_neto_en_usdt_con_apuesta(self):
        r = mg.evaluar([(0.50, 1), (0.50, 0)], apuesta=2.0, B=200, minimo=2)
        self.assertAlmostEqual(r["neto_usdt"], 2.0 * (0.96 - 1), places=9)


class Decision(unittest.TestCase):
    def test_18_de_25_a_080_no_basta_con_poca_muestra(self):
        pares = [(0.80, 1)] * 18 + [(0.80, 0)] * 7
        r = mg.evaluar(pares, minimo=100, B=200)
        self.assertEqual(r["decision"], mg.ETIQUETAS["poca"])
        self.assertAlmostEqual(r["usdt_por_apuesta"], -2.95 / 25, places=9)  # -0,118

    def test_acierto_72_pero_precio_80_pierde_con_muestra_grande(self):
        pares = [(0.80, 1)] * 720 + [(0.80, 0)] * 280
        r = mg.evaluar(pares, B=500)
        self.assertEqual(r["decision"], mg.ETIQUETAS["pierde"])
        self.assertLess(r["sup_normal"], 0)
        self.assertLess(r["sup_boot"], 0)

    def test_barato_con_25_por_ciento_gana_con_muestra_grande(self):
        pares = [(0.20, 1)] * 125 + [(0.20, 0)] * 375
        r = mg.evaluar(pares, B=500)
        self.assertEqual(r["decision"], mg.ETIQUETAS["gana"])
        self.assertGreater(r["inf_normal"], 0)
        self.assertGreater(r["inf_boot"], 0)

    def test_correccion_por_muchas_estrategias_quita_la_ganancia(self):
        pares = [(0.20, 1)] * 125 + [(0.20, 0)] * 375
        con_una = mg.evaluar(pares, k=1, B=500)
        con_mil = mg.evaluar(pares, k=1000, B=500)
        self.assertEqual(con_una["decision"], mg.ETIQUETAS["gana"])
        self.assertEqual(con_mil["decision"], mg.ETIQUETAS["no"])

    def test_todas_perdidas_da_perdida(self):
        r = mg.evaluar([(0.50, 0)] * 300, B=200)
        self.assertEqual(r["decision"], mg.ETIQUETAS["pierde"])

    def test_limites_en_orden(self):
        pares = [(0.30, 1)] * 90 + [(0.30, 0)] * 210
        r = mg.evaluar(pares, B=300)
        self.assertLessEqual(r["inf_normal"], r["usdt_por_apuesta"])
        self.assertLessEqual(r["usdt_por_apuesta"], r["sup_normal"])
        self.assertLessEqual(r["inf_boot"], r["sup_boot"])


class Registro(unittest.TestCase):
    def _escribir(self, nombre, texto):
        ruta = os.path.join(self.tmp, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        return ruta

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_csv_con_coma_decimal_y_si_no(self):
        ruta = self._escribir("r.csv", "estrategia,precio,acierto\nE1,\"0,46\",sí\nE1,0.30,no\n")
        filas, malas = mg.leer_registro(ruta)
        self.assertEqual(malas, [])
        self.assertEqual(filas, [("E1", 0.46, 1), ("E1", 0.30, 0)])

    def test_jsonl_y_booleanos(self):
        ruta = self._escribir("r.jsonl", json.dumps({"estrategia": "E2", "precio": 0.5, "acierto": True}) + "\n"
                              + json.dumps({"estrategia": "E2", "precio": 0.5, "acierto": False}) + "\n")
        filas, malas = mg.leer_registro(ruta)
        self.assertEqual(malas, [])
        self.assertEqual([w for _, _, w in filas], [1, 0])

    def test_filas_malas_se_cuentan(self):
        ruta = self._escribir("m.jsonl", "\n".join([
            json.dumps({"estrategia": "E", "precio": 1.2, "acierto": 1}),
            json.dumps({"estrategia": "E", "precio": 0.4, "acierto": "tal vez"}),
            json.dumps({"precio": 0.4, "acierto": 1}),
            "no es json",
            json.dumps({"estrategia": "E", "precio": 0.4, "acierto": 1}),
        ]) + "\n")
        filas, malas = mg.leer_registro(ruta)
        self.assertEqual(len(filas), 1)
        self.assertEqual(len(malas), 4)

    def test_cli_sobre_el_ejemplo(self):
        if not os.path.isfile(EJEMPLO):
            generar(EJEMPLO)
        salida = subprocess.run([sys.executable, os.path.join(AQUI, "medidor_ganancia.py"),
                                 "--registro", EJEMPLO], capture_output=True, text=True, check=True).stdout
        self.assertIn("B_acierta_caro", salida)
        lineas = {l.split()[0]: l for l in salida.splitlines() if l.strip()}
        self.assertIn(mg.ETIQUETAS["pierde"], lineas["B_acierta_caro"])
        self.assertIn(mg.ETIQUETAS["gana"], lineas["C_barato_gana"])
        self.assertIn(mg.ETIQUETAS["no"], lineas["A_moneda_al_50"])
        self.assertIn(mg.ETIQUETAS["poca"], lineas["E_pocas"])
        self.assertIn("Decisión final: C_barato_gana", salida)


if __name__ == "__main__":
    if "--generar" in sys.argv:
        n = generar(EJEMPLO)
        print("Escritas %d filas SINTÉTICAS en %s" % (n, EJEMPLO))
        sys.exit(0)
    unittest.main(argv=[sys.argv[0]], verbosity=2)
