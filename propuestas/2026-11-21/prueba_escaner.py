#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas del escáner de secretos. Crea repositorios temporales con datos FALSOS.

Todos los valores con forma de credencial se generan al ejecutar (semilla fija),
para que ningún literal con aspecto real quede guardado en el repositorio.
Ejecutar:  python3 prueba_escaner.py
"""

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import escaner_secretos as E  # noqa: E402

ALFA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def aleatorio(n, semilla):
    r = random.Random(semilla)
    return "".join(r.choice(ALFA) for _ in range(n))


TOKEN_TG = "1234567890:" + aleatorio(35, 1)
CLAVE_BINANCE = aleatorio(64, 2)
CLAVE_ANT = "sk-" + "ant-" + "api03-" + aleatorio(40, 3)
CLAVE_ASIG = aleatorio(24, 4)
SENSIBLE = "frase-sensible-de-prueba"
USUARIO = "usuario_prueba"


def git(repo, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="prueba", GIT_AUTHOR_EMAIL="prueba@example.com",
               GIT_COMMITTER_NAME="prueba", GIT_COMMITTER_EMAIL="prueba@example.com")
    subprocess.run(["git", "-C", repo, *args], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def escribir(repo, nombre, contenido):
    ruta = os.path.join(repo, nombre)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    mode = "wb" if isinstance(contenido, bytes) else "w"
    with open(ruta, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
        f.write(contenido)


def repo_de_prueba(directorio):
    git(directorio, "init", "-q")
    git(directorio, "symbolic-ref", "HEAD", "refs/heads/master")
    escribir(directorio, "config.txt",
             "telegram = %s\ntoken_placeholder = \"TU_TOKEN_AQUI_123456\"\npassword = \"abc123\"\n" % TOKEN_TG)
    escribir(directorio, "red.txt", "ip publica 8.8.8.8 y privada 192.168.1.10\n"
             "ruta C:\\Users\\%s\\Documentos\\datos.txt\n" % USUARIO)
    escribir(directorio, "contacto.txt", "escribir a persona.prueba@correo-prueba.com\n"
             "robot noreply@github.com\n")
    escribir(directorio, "dato.bin", b"\0\1" + TOKEN_TG.encode())
    escribir(directorio, "sensible.txt", "linea con %s dentro\n" % SENSIBLE)
    git(directorio, "add", "-A")
    git(directorio, "commit", "-q", "-m", "inicial")
    git(directorio, "branch", "otra")
    git(directorio, "rm", "-q", "config.txt")
    git(directorio, "commit", "-q", "-m", "quitar config (sigue en el historial)")
    git(directorio, "checkout", "-q", "otra")
    escribir(directorio, "llave.txt", "binance_api_key_lectura = %s\n" % CLAVE_BINANCE)
    escribir(directorio, "clave.txt", "anthropic = %s\napi_key = \"%s\"\n" % (CLAVE_ANT, CLAVE_ASIG))
    git(directorio, "add", "-A")
    git(directorio, "commit", "-q", "-m", "llave solo en la rama otra")
    git(directorio, "checkout", "-q", "master")


def correr(repo, *extra):
    salida_json = os.path.join(os.path.dirname(os.path.abspath(repo)),
                               "salida_%s.json" % os.path.basename(repo))
    cmd = [sys.executable, os.path.join(AQUI, "escaner_secretos.py"), "--repo", repo,
           "--json", salida_json, *extra]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    with open(salida_json, encoding="utf-8") as f:
        crudo = f.read()
    return r.returncode, r.stdout + r.stderr, json.loads(crudo), crudo


class PruebasUnitarias(unittest.TestCase):
    def test_entropia(self):
        self.assertEqual(E.entropia(""), 0.0)
        self.assertAlmostEqual(E.entropia("ab"), 1.0)
        self.assertGreater(E.entropia(CLAVE_ASIG), 3.0)

    def test_marcadores_no_son_credenciales(self):
        self.assertTrue(E.es_marcador("TU_TOKEN_AQUI_123456"))
        self.assertTrue(E.es_marcador("aaaaaaaaaaaaaaaaaaaa"))
        self.assertFalse(E.es_marcador(CLAVE_ASIG))

    def test_asignacion(self):
        self.assertTrue(E.aceptar_asignacion(CLAVE_ASIG))
        self.assertFalse(E.aceptar_asignacion("abc123"))
        self.assertFalse(E.aceptar_asignacion("solo_letras_sin_digitos_x"))

    def test_ip_publica_y_privada(self):
        self.assertTrue(E.aceptar_ip("8.8.8.8"))
        self.assertFalse(E.aceptar_ip("192.168.1.10"))
        self.assertFalse(E.aceptar_ip("127.0.0.1"))

    def test_enmascarar_nunca_muestra_el_valor_completo(self):
        m = E.enmascarar(CLAVE_BINANCE)
        self.assertNotIn(CLAVE_BINANCE, m)
        self.assertTrue(m.startswith(CLAVE_BINANCE[:4]))
        self.assertIn("64 car.", m)

    def test_hash_hexadecimal_no_es_clave_binance(self):
        hexa = "0123456789abcdef" * 4  # 64 caracteres, solo hexadecimales
        self.assertEqual(E.analizar_texto("binance %s" % hexa), [])
        self.assertTrue(E.aceptar_binance(CLAVE_BINANCE))

    def test_token_publico_conocido_no_se_marca(self):
        publico = next(iter(E.PUBLICOS_CONOCIDOS))
        self.assertFalse(E.aceptar_asignacion(publico))
        hs = E.analizar_texto('TOKEN = "%s"' % publico)
        self.assertEqual(hs, [])

    def test_correo_con_extension_de_archivo_no_cuenta(self):
        self.assertFalse(E.aceptar_correo("usuario@informe.txt"))
        self.assertFalse(E.aceptar_correo("noreply@github.com"))
        self.assertTrue(E.aceptar_correo("persona@correo-prueba.com"))

    def test_etiquetas_no_muestran_el_dato(self):
        hs = E.analizar_texto("ruta C:\\Users\\%s\\x y mail a persona@correo-prueba.com" % USUARIO)
        self.assertNotIn(USUARIO, " ".join(h["mostrado"] for h in hs))
        self.assertNotIn("persona@", " ".join(h["mostrado"] for h in hs))

    def test_analizar_texto_solo_patrones_validos(self):
        hs = E.analizar_texto("api_key = %s\n%s\n" % (CLAVE_ASIG, CLAVE_BINANCE))
        ids = sorted(h["id"] for h in hs)
        self.assertIn("asignacion_secreta", ids)
        self.assertNotIn("posible_clave_binance", ids)  # sin la palabra binance no se marca
        hs2 = E.analizar_texto("binance %s" % CLAVE_BINANCE)
        self.assertIn("posible_clave_binance", [h["id"] for h in hs2])


class PruebasRepositorio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="escaner_prueba_")
        cls.repo = os.path.join(cls.tmp, "repo")
        os.makedirs(cls.repo)
        repo_de_prueba(cls.repo)
        sens = os.path.join(cls.tmp, "sensibles.txt")
        with open(sens, "w", encoding="utf-8") as f:
            f.write("# una cadena por línea\n%s\n" % SENSIBLE)
        cls.codigo, cls.texto, cls.res, cls.crudo = correr(cls.repo, "--sensibles", sens)
        cls.h = cls.res["hallazgos"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def buscar(self, id_, valor=None):
        return [h for h in self.h if h["id"] == id_ and (valor is None or h["valor"] == valor)]

    def test_secreto_borrado_sigue_en_el_historial(self):
        tg = self.buscar("token_telegram")
        self.assertEqual(len(tg), 1)
        self.assertEqual(tg[0]["nivel"], "CRITICO")
        self.assertIn("config.txt", tg[0]["rutas"])
        self.assertFalse(tg[0]["vigente_en_rama_principal"])

    def test_clave_solo_en_otra_rama_se_encuentra(self):
        bn = self.buscar("posible_clave_binance")
        self.assertEqual(len(bn), 1)
        self.assertIn("llave.txt", bn[0]["rutas"])

    def test_clave_anthropic_y_asignacion(self):
        self.assertEqual(len(self.buscar("clave_anthropic")), 1)
        asig = self.buscar("asignacion_secreta")
        self.assertEqual(len(asig), 1, "el marcador TU_TOKEN y la contraseña corta no deben contar")

    def test_marcadores_y_cortos_no_se_marcan(self):
        for h in self.h:
            self.assertNotIn("TU_TOKEN", json.dumps(h))
            self.assertNotIn("abc123", json.dumps(h))

    def test_ip_publica_si_privada_no(self):
        ips = [h["valor"] for h in self.buscar("ip_publica")]
        self.assertEqual(ips, ["8.8.8.8"])

    def test_ruta_de_usuario_enmascarada(self):
        rs = self.buscar("ruta_usuario_windows")
        self.assertEqual(len(rs), 1)
        self.assertNotIn(USUARIO, json.dumps(rs[0]))

    def test_correo_sin_los_de_robot(self):
        cs = self.buscar("correo")
        self.assertEqual(len(cs), 1, "solo el correo personal; noreply@ no cuenta")
        self.assertNotIn("persona.prueba", json.dumps(cs[0]))

    def test_lista_de_sensibles(self):
        self.assertTrue(self.buscar("dato_indicado_en_lista"))

    def test_binarios_omitidos_y_salida_limpia(self):
        self.assertGreaterEqual(self.res["resumen"]["blobs_omitidos_binarios_o_grandes"], 1)
        self.assertNotIn(TOKEN_TG, self.texto)
        self.assertNotIn(CLAVE_BINANCE, self.texto)
        self.assertNotIn(CLAVE_ANT, self.texto)
        self.assertNotIn(CLAVE_ASIG, self.texto)
        self.assertNotIn(CLAVE_ASIG, self.crudo)
        self.assertNotIn(USUARIO, self.texto)

    def test_codigo_de_salida_con_criticos(self):
        self.assertEqual(self.codigo, 1)

    def test_repositorio_limpio_da_cero(self):
        limpio = os.path.join(self.tmp, "limpio")
        os.makedirs(limpio)
        git(limpio, "init", "-q")
        git(limpio, "symbolic-ref", "HEAD", "refs/heads/master")
        escribir(limpio, "README.md", "sin datos sensibles\n")
        git(limpio, "add", "-A")
        git(limpio, "commit", "-q", "-m", "limpio")
        codigo, _, res, _ = correr(limpio)
        self.assertEqual(codigo, 0)
        self.assertEqual(res["resumen"]["criticos"], 0)
        self.assertEqual(res["resumen"]["revisar"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
