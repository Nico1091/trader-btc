#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas del verificador de llave. Solo biblioteca estándar. Datos inventados, sin llaves reales.

Ejecutar:  python prueba_verificador_llave.py
"""
import contextlib
import io
import json
import os
import tempfile
import unittest

import verificador_llave as v

AQUI = os.path.dirname(os.path.abspath(__file__))
EJEMPLO = os.path.join(AQUI, "ejemplo_restricciones_SINTETICO.json")


def base():
    """Una llave bien configurada (la del ejemplo), como dict nuevo."""
    with open(EJEMPLO, encoding="utf-8") as f:
        return json.load(f)


class PruebasVerificador(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def escribir(self, datos, nombre="r.json"):
        ruta = os.path.join(self.tmp, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            if isinstance(datos, str):
                f.write(datos)
            else:
                json.dump(datos, f)
        return ruta

    def correr(self, argv):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = v.main(argv)
        return codigo, salida.getvalue()

    def argv(self, ruta, ip_caja="203.0.113.10", ip_lista="203.0.113.10", extra=()):
        return [ruta, "--ip-caja", ip_caja, "--ip-lista", ip_lista, *extra]

    # ---- Caso bueno ----
    def test_ejemplo_sin_confirmar_prediccion_queda_pendiente(self):
        codigo, out = self.correr(self.argv(EJEMPLO))
        self.assertEqual(codigo, 1)
        self.assertIn("VEREDICTO: PENDIENTE", out)
        self.assertIn("Predicción", out)

    def test_ejemplo_con_prediccion_confirmada_es_apta(self):
        codigo, out = self.correr(self.argv(EJEMPLO, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 0)
        self.assertIn("VEREDICTO: APTA", out)
        self.assertNotIn("FALLA", out)

    # ---- Cada bandera prohibida, por separado ----
    def test_cada_bandera_prohibida_en_verdadero_da_no_apta(self):
        for campo in v.DEBEN_SER_MENTIRA:
            with self.subTest(campo=campo):
                d = base()
                d[campo] = True
                ruta = self.escribir(d, f"{campo}.json")
                codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
                self.assertEqual(codigo, 2)
                self.assertIn("VEREDICTO: NO APTA", out)
                self.assertIn(campo, out)

    def test_retiros_es_la_falla_mas_grave_y_se_dice_con_claridad(self):
        d = base()
        d["enableWithdrawals"] = True
        ruta = self.escribir(d)
        codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 2)
        self.assertIn("Retiros por API: enableWithdrawals = true. Debe ser false.", out)

    def test_lectura_apagada_da_no_apta(self):
        d = base()
        d["enableReading"] = False
        ruta = self.escribir(d)
        codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 2)
        self.assertIn("enableReading = false", out)

    def test_sin_restriccion_de_ip_da_no_apta(self):
        d = base()
        d["ipRestrict"] = False
        ruta = self.escribir(d)
        codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 2)
        self.assertIn("ipRestrict = false", out)

    def test_varias_fallas_se_listan_todas(self):
        d = base()
        d["enableWithdrawals"] = True
        d["enableFutures"] = True
        d["enableMargin"] = True
        ruta = self.escribir(d)
        codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 2)
        for txt in ("enableWithdrawals", "enableFutures", "enableMargin"):
            self.assertIn(txt, out)

    # ---- IP ----
    def test_ip_de_la_caja_fuera_de_la_lista_da_no_apta(self):
        ruta = self.escribir(base())
        codigo, out = self.correr(
            self.argv(ruta, ip_caja="203.0.113.10", ip_lista="198.51.100.7", extra=["--confirmo-prediccion"])
        )
        self.assertEqual(codigo, 2)
        self.assertIn("no está en la lista", out)
        self.assertIn("−2015", out)

    def test_lista_con_varias_ips_acepta_la_de_la_caja(self):
        ruta = self.escribir(base())
        codigo, _ = self.correr(
            self.argv(ruta, ip_caja="203.0.113.10", ip_lista="198.51.100.7, 203.0.113.10",
                      extra=["--confirmo-prediccion"])
        )
        self.assertEqual(codigo, 0)

    def test_ip_invalida_es_entrada_mala(self):
        ruta = self.escribir(base())
        codigo, out = self.correr(self.argv(ruta, ip_caja="no-es-ip"))
        self.assertEqual(codigo, 3)
        self.assertIn("ENTRADA MALA", out)

    def test_red_con_barra_no_se_acepta(self):
        ruta = self.escribir(base())
        codigo, _ = self.correr(self.argv(ruta, ip_lista="203.0.113.0/24"))
        self.assertEqual(codigo, 3)

    def test_lista_vacia_es_entrada_mala(self):
        ruta = self.escribir(base())
        codigo, _ = self.correr(self.argv(ruta, ip_lista=" , "))
        self.assertEqual(codigo, 3)

    # ---- Entrada que falla cerrado ----
    def test_campo_que_falta_da_no_apta(self):
        d = base()
        del d["enableFutures"]
        ruta = self.escribir(d)
        codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 2)
        self.assertIn("faltan en la respuesta: enableFutures", out)

    def test_valor_que_no_es_booleano_es_entrada_mala(self):
        d = base()
        d["enableFutures"] = "false"
        ruta = self.escribir(d)
        codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 3)
        self.assertIn("debe ser verdadero o falso", out)

    def test_json_que_no_es_objeto_es_entrada_mala(self):
        ruta = self.escribir([1, 2, 3])
        codigo, _ = self.correr(self.argv(ruta))
        self.assertEqual(codigo, 3)

    def test_json_roto_es_entrada_mala(self):
        ruta = self.escribir("{ esto no es json")
        codigo, out = self.correr(self.argv(ruta))
        self.assertEqual(codigo, 3)
        self.assertIn("no es JSON válido", out)

    def test_archivo_inexistente_es_entrada_mala(self):
        codigo, out = self.correr(self.argv(os.path.join(self.tmp, "no_existe.json")))
        self.assertEqual(codigo, 3)
        self.assertIn("no existe el archivo", out)

    def test_texto_largo_se_niega_y_no_se_muestra(self):
        # Simulación de una llave pegada por error. Se arma en tiempo de prueba y no existe en el repositorio.
        falsa = "AB" * 20
        d = base()
        d["oops"] = falsa
        ruta = self.escribir(d)
        codigo, out = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 3)
        self.assertIn("podría ser una llave", out)
        self.assertNotIn(falsa, out)

    def test_texto_corto_no_dispara_la_guarda(self):
        d = base()
        d["nota"] = "corto"
        ruta = self.escribir(d)
        codigo, _ = self.correr(self.argv(ruta, extra=["--confirmo-prediccion"]))
        self.assertEqual(codigo, 0)

    # ---- Informe JSON ----
    def test_informe_json_sin_valores_del_archivo(self):
        d = base()
        d["enableFutures"] = True
        d["createTime"] = 123456789
        ruta = self.escribir(d)
        salida = os.path.join(self.tmp, "informe.json")
        codigo, _ = self.correr(self.argv(ruta, extra=["--confirmo-prediccion", "--json", salida]))
        self.assertEqual(codigo, 2)
        with open(salida, encoding="utf-8") as f:
            inf = json.load(f)
        self.assertEqual(inf["veredicto"], "NO APTA")
        self.assertEqual(inf["ip_caja"], "203.0.113.10")
        self.assertTrue(any("enableFutures" in x for x in inf["fallas"]))
        self.assertNotIn("123456789", json.dumps(inf))

    # ---- Coherencia de las tablas ----
    def test_ninguna_bandera_esta_en_las_dos_listas(self):
        self.assertFalse(set(v.DEBEN_SER_VERDAD) & set(v.DEBEN_SER_MENTIRA))

    def test_las_banderas_nombradas_son_las_del_endpoint_oficial(self):
        # Nombres comprobados en la página oficial de Binance (api-key-permission).
        oficiales = {
            "ipRestrict", "createTime", "enableReading", "enableWithdrawals", "enableInternalTransfer",
            "enableMargin", "enableFutures", "permitsUniversalTransfer", "enableVanillaOptions",
            "enableFixApiTrade", "enableFixReadOnly", "enableSpotAndMarginTrading",
            "enablePortfolioMarginTrading",
        }
        usadas = set(v.DEBEN_SER_VERDAD) | set(v.DEBEN_SER_MENTIRA)
        self.assertTrue(usadas <= oficiales, usadas - oficiales)


if __name__ == "__main__":
    unittest.main(verbosity=2)
