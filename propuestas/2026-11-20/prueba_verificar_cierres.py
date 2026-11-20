#!/usr/bin/env python3
"""Pruebas de verificar_cierres.py (solo biblioteca estándar).

Usa el día real de velas públicas de BTCUSDT del 18/11/2026 (velas_BTCUSDT_1m_2026-11-18.csv) y registros de
prueba construidos sobre ellas. Los ganadores «oficiales» de esos registros son INVENTADOS a propósito (se les
da la vuelta un número conocido de ventanas): sirven para comprobar que el verificador cuenta bien, no dicen
nada del mercado real.

Uso:  python3 prueba_verificar_cierres.py            (corre las pruebas)
      python3 prueba_verificar_cierres.py --generar  (escribe ejemplo_registro_SINTETICO.jsonl)
"""
import calendar
import datetime as dt
import json
import os
import random
import sys
import tempfile
import unittest

import verificar_cierres as v

AQUI = os.path.dirname(os.path.abspath(__file__))
VELAS_DIA = os.path.join(AQUI, "velas_BTCUSDT_1m_2026-11-18.csv")
INICIO_DIA = calendar.timegm(dt.date(2026, 11, 18).timetuple())


def ventanas_del_dia(velas, W):
    """Todas las ventanas de W minutos alineadas que caben en el día con sus velas completas."""
    return [t for t in range(INICIO_DIA, INICIO_DIA + 86400, W * 60)
            if v.ganador_velas(velas, t, W) is not None]


def registro_de_prueba(velas, volteadas, con_velas_del_operador=False):
    """Filas tipo resultado con fuente oficial. `volteadas` es el conjunto de (W, t) cuyo ganador oficial se
    invierte a propósito. Las filas «velas» reflejan la regla de papel.py sin inventar nada."""
    filas = []
    for W in (5, 15):
        for t in ventanas_del_dia(velas, W):
            g = v.ganador_velas(velas, t, W)
            oficial = (-g if g != 0 else 1) if (W, t) in volteadas else g
            filas.append({"tipo": "resultado", "serie": "papel", "fuente": "oficial", "W": W, "t": t,
                          "ganador": oficial, "hora": t + W * 60 + 35})
            if con_velas_del_operador:
                filas.append({"tipo": "resultado", "serie": "velas", "fuente": "velas", "W": W, "t": t,
                              "ganador": g, "hora": t + W * 60 + 5})
    return filas


def escribir_registro(filas, carpeta):
    ruta = os.path.join(carpeta, "registro.jsonl")
    with open(ruta, "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila) + "\n")
    return ruta


class PruebasRegla(unittest.TestCase):
    def setUp(self):
        self.velas = {}
        for i in range(15):
            self.velas[1000 + 60 * i] = (100.0, 100.0)       # minutos planos
        self.t = 1000

    def test_sube(self):
        self.velas[1000] = (100.0, 100.0)
        self.velas[1000 + 14 * 60] = (100.0, 101.0)
        self.assertEqual(v.ganador_velas(self.velas, 1000, 15), 1)

    def test_baja(self):
        self.velas[1000 + 14 * 60] = (100.0, 99.0)
        self.assertEqual(v.ganador_velas(self.velas, 1000, 15), -1)

    def test_empate_cuando_cierra_igual_que_abre(self):
        self.assertEqual(v.ganador_velas(self.velas, 1000, 15), 0)

    def test_sin_datos_si_falta_un_minuto(self):
        del self.velas[1000 + 5 * 60]
        self.assertIsNone(v.ganador_velas(self.velas, 1000, 15))

    def test_sin_datos_si_falta_el_ultimo_minuto(self):
        del self.velas[1000 + 14 * 60]
        self.assertIsNone(v.ganador_velas(self.velas, 1000, 15))

    def test_usa_apertura_del_primero_y_cierre_del_ultimo(self):
        # El cierre del minuto del medio no decide: solo cuenta el último.
        self.velas[1000 + 7 * 60] = (100.0, 150.0)
        self.velas[1000 + 14 * 60] = (100.0, 100.5)
        self.assertEqual(v.ganador_velas(self.velas, 1000, 15), 1)


class PruebasWilson(unittest.TestCase):
    def test_cero_de_cien(self):
        lo, hi = v.wilson(0, 100)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.0370, places=4)

    def test_simetria(self):
        lo, hi = v.wilson(30, 100)
        lo2, hi2 = v.wilson(70, 100)
        self.assertAlmostEqual(lo, 1 - hi2, places=10)
        self.assertAlmostEqual(hi, 1 - lo2, places=10)

    def test_sin_datos(self):
        self.assertEqual(v.wilson(0, 0), (0.0, 1.0))


class PruebasLectura(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_velas_sin_columnas_son_error(self):
        ruta = os.path.join(self.tmp.name, "mal.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("open_time_ms,open\n1,2\n")
        with self.assertRaises(v.ErrorUso):
            v.leer_velas(ruta)

    def test_registro_cuenta_lineas_malas_y_sin_tocar_otros_tipos(self):
        ruta = os.path.join(self.tmp.name, "r.jsonl")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write('{"tipo": "compra", "W": 5, "t": 300}\n')          # otro tipo: se ignora
            f.write("esto no es json\n")                               # mala
            f.write('{"tipo": "resultado", "W": 5, "t": 300, "ganador": 7}\n')   # mala: ganador inválido
            f.write('{"tipo": "resultado", "W": 5, "t": 300, "ganador": 1, "fuente": "oficial"}\n')
        res, cuentas = v.leer_registro([ruta])
        self.assertEqual(len(res), 1)
        self.assertEqual(cuentas["malas"], 2)

    def test_conflictos_se_dejan_fuera(self):
        res = [{"serie": "papel", "fuente": "oficial", "W": 5, "t": 300, "ganador": 1},
               {"serie": "papel", "fuente": "oficial", "W": 5, "t": 300, "ganador": -1},
               {"serie": "papel", "fuente": "oficial", "W": 5, "t": 600, "ganador": 1}]
        cuentas = v.Counter()
        quedan = v.quitar_conflictos(res, cuentas)
        self.assertEqual(cuentas["conflictos"], 1)
        self.assertEqual([r["t"] for r in quedan], [600])

    def test_fecha_que_no_se_lee(self):
        with self.assertRaises(v.ErrorUso):
            v._fecha_a_segundos("18/11/2026")


class PruebasDescarga(unittest.TestCase):
    def test_pagina_hasta_completar_sin_duplicar(self):
        inicio = 1_700_000_000 - (1_700_000_000 % 60)
        total = 2500
        def pedir(url):
            # Simula la API: 1.000 velas por página desde startTime.
            desde = int(url.split("startTime=")[1].split("&")[0])
            salida = []
            for i in range(1000):
                ms = desde + 60_000 * i
                if (ms - inicio * 1000) // 60_000 >= total:
                    break
                salida.append([ms, "1", "2", "0", str(2 + i), "0"])
            return salida
        velas = v.descargar_velas(inicio, inicio + 60 * total, pedir=pedir)
        self.assertEqual(len(velas), total)
        self.assertTrue(all((inicio + 60 * i) in velas for i in range(total)))

    def test_respuesta_vacia_termina(self):
        self.assertEqual(v.descargar_velas(0, 3600, pedir=lambda url: []), {})


class PruebasDia(unittest.TestCase):
    """Día real de velas: 288 ventanas de 5 min y 96 de 15 min, todas con velas completas."""

    @classmethod
    def setUpClass(cls):
        cls.velas = v.leer_velas(VELAS_DIA)

    def test_el_dia_real_esta_completo(self):
        self.assertEqual(len(self.velas), 1440)
        self.assertEqual(len(ventanas_del_dia(self.velas, 5)), 288)
        self.assertEqual(len(ventanas_del_dia(self.velas, 15)), 96)

    def test_registro_que_coincide_da_cero_discordancia_y_sirven(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = escribir_registro(registro_de_prueba(self.velas, set()), carpeta)
            texto, codigo, datos = v.verificar([ruta], self.velas)
        self.assertEqual(datos["comparadas"], 384)
        self.assertEqual(datos["difieren"], 0)
        self.assertIn("LAS VELAS SIRVEN", texto)
        self.assertEqual(v.veredicto(384, 0)[1], 0)

    def test_discordancias_inyectadas_se_cuentan_exactas(self):
        candidatas = [(5, t) for t in ventanas_del_dia(self.velas, 5)] + \
                     [(15, t) for t in ventanas_del_dia(self.velas, 15)]
        volteadas = set(random.Random(20261120).sample(candidatas, 40))
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = escribir_registro(registro_de_prueba(self.velas, volteadas), carpeta)
            texto, codigo, datos = v.verificar([ruta], self.velas)
        self.assertEqual(datos["comparadas"], 384)
        self.assertEqual(datos["difieren"], 40)
        self.assertIn("LAS VELAS NO SIRVEN", texto)
        self.assertEqual(codigo, 1)

    def test_fuente_velas_se_recalcula(self):
        with tempfile.TemporaryDirectory() as carpeta:
            filas = registro_de_prueba(self.velas, set(), con_velas_del_operador=True)
            ruta = escribir_registro(filas, carpeta)
            texto, _, _ = v.verificar([ruta], self.velas)
        self.assertIn("coinciden 384, difieren 0", texto)

    def test_ventana_sin_velas_no_se_compara(self):
        velas = dict(self.velas)
        del velas[INICIO_DIA + 60 * 10]               # quita un minuto dentro de la primera ventana de 15
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = escribir_registro(registro_de_prueba(self.velas, set()), carpeta)
            res, cuentas = v.leer_registro([ruta])
            tabla, _ = v.analizar(res, velas, cuentas)
        self.assertEqual(tabla[15]["sin_velas"], 1)

    def test_ventana_desalineada_no_se_compara(self):
        res = [{"serie": "papel", "fuente": "oficial", "W": 5, "t": INICIO_DIA + 60, "ganador": 1}]
        cuentas = v.Counter()
        tabla, _ = v.analizar(res, self.velas, cuentas)
        self.assertEqual(cuentas["desalineadas"], 1)
        self.assertEqual(tabla[5]["coinciden"] + tabla[5]["difieren"], 0)


class PruebasVeredicto(unittest.TestCase):
    def test_muestra_insuficiente(self):
        texto, codigo = v.veredicto(50, 0)
        self.assertIn("MUESTRA INSUFICIENTE", texto)
        self.assertEqual(codigo, 1)

    def test_indeciso(self):
        # 15 de 300: intervalo de Wilson aprox. 3,1 % a 8,1 %, a caballo entre 2 % y 5 %.
        texto, codigo = v.veredicto(300, 15)
        self.assertIn("INDECISO", texto)
        self.assertEqual(codigo, 1)

    def test_sirven_con_cero_de_300(self):
        texto, codigo = v.veredicto(300, 0)
        self.assertIn("LAS VELAS SIRVEN", texto)
        self.assertEqual(codigo, 0)


class PruebasLineaDeComandos(unittest.TestCase):
    def test_guardar_sin_descargar_es_error_de_uso(self):
        self.assertEqual(v.principal(["--registro", AQUI, "--velas", VELAS_DIA, "--guardar", "x.csv"]), 2)

    def test_registro_inexistente_es_error_de_uso(self):
        self.assertEqual(v.principal(["--registro", "no_existe_xyz", "--velas", VELAS_DIA]), 2)

    def test_ejecucion_completa_con_salida_json(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = escribir_registro(registro_de_prueba(v.leer_velas(VELAS_DIA), set()), carpeta)
            salida = os.path.join(carpeta, "salida.json")
            codigo = v.principal(["--registro", ruta, "--velas", VELAS_DIA, "--json", salida])
            with open(salida, encoding="utf-8") as f:
                datos = json.load(f)
        self.assertEqual(codigo, 0)
        self.assertEqual(datos["comparadas"], 384)


def generar_ejemplo():
    velas = v.leer_velas(VELAS_DIA)
    candidatas = [(5, t) for t in ventanas_del_dia(velas, 5)] + [(15, t) for t in ventanas_del_dia(velas, 15)]
    volteadas = set(random.Random(20261120).sample(candidatas, 40))
    ruta = os.path.join(AQUI, "ejemplo_registro_SINTETICO.jsonl")
    with open(ruta, "w", encoding="utf-8") as f:
        for fila in registro_de_prueba(velas, volteadas, con_velas_del_operador=True):
            f.write(json.dumps(fila) + "\n")
    print("escrito:", ruta)


if __name__ == "__main__":
    if "--generar" in sys.argv:
        generar_ejemplo()
        sys.exit(0)
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
