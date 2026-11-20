#!/usr/bin/env python3
"""Pruebas del conciliador de binarias. Solo biblioteca estándar.

Los registros se fabrican en una carpeta temporal en cada prueba; no queda nada en el repositorio.
Ejecución: python3 -I prueba_conciliador.py
"""

import csv
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import conciliador_dinero as C  # noqa: E402

AHORA = dt.datetime(2026, 11, 12, 19, 0, tzinfo=C.ZONA).timestamp()
FEE = 0.98


def lectura(oid, orden, estado, final, comprado, precio, contratos, hora):
    return {"tipo": "orden leída", "id": oid, "orden": orden, "estado": estado, "final": final,
            "comprado": comprado, "precio": precio, "contratos": contratos, "hora": hora}


def liquidacion(oid, orden, res, comprado, pago, neto, hora):
    return {"tipo": "liquidación", "id": oid, "orden": orden, "res": res,
            "comprado": comprado, "pago": pago, "neto": neto, "hora": hora}


def cobro(oid, orden, estado, monto, hora):
    return {"tipo": "cobro", "id": oid, "orden": orden, "estado": estado, "monto": monto, "hora": hora}


def escribir(carpeta, filas, lineas_extra=()):
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "20261112.jsonl"), "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
        for l in lineas_extra:
            f.write(l + "\n")
    return carpeta


def escribir_extracto(ruta, filas):
    """CSV bien formado: los valores con coma decimal van entre comillas, como lo haría una hoja de cálculo."""
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["orden", "importe_usdt", "cobrado_usdt"])
        for orden, importe, cobrado in filas:
            escritor.writerow([orden, importe, cobrado])
    return ruta


def pago_de_win(comprado, precio):
    """Pago de una orden ganadora: comprado × 0,98 ÷ precio (la fórmula del bloc)."""
    return round(comprado * FEE / precio, 4)


def registro_12_11(cobro_baja="cobrado"):
    """Las dos compras reales del 12/11 según el bloc: SUBE 4,62 a 0,55 (perdió); BAJA 4,11 a 0,86 (ganó 0,57)."""
    pago_baja = pago_de_win(4.11, 0.86)
    neto_baja = round(pago_baja - 4.11, 4)
    filas = [
        lectura("A1", "ord-1", "FILLED", True, 4.62, 0.55, round(4.62 * FEE / 0.55, 4), AHORA - 900),
        liquidacion("A1", "ord-1", 0, 4.62, 0.0, -4.62, AHORA - 600),
        lectura("A2", "ord-2", "FILLED", True, 4.11, 0.86, pago_baja, AHORA - 900),
        liquidacion("A2", "ord-2", 1, 4.11, pago_baja, neto_baja, AHORA - 600),
        cobro("A2", "ord-2", cobro_baja, pago_baja, AHORA - 580),
    ]
    return filas


def criticas(alertas):
    return [a for a in alertas if a["nivel"] == "critica"]


def codigos(alertas):
    return {(a["orden"], a["codigo"]) for a in alertas}


def correr(carpeta, extracto=None, gracia=30.0):
    res, alertas, cruce, texto, _ = C.conciliar(carpeta, extracto, gracia)
    return res, alertas, cruce, texto


def t_registro_real_12_11():
    with tempfile.TemporaryDirectory() as d:
        carpeta = escribir(os.path.join(d, "registro"), registro_12_11())
        res, alertas, _, _ = correr(carpeta)
        assert res["compradas"] == 2, res
        assert res["liquidadas"] == 2 and res["aciertos"] == 1, res
        assert abs(res["usdt_comprados"] - 8.73) < 1e-6, res
        # Lo que dice el bloc: 12/11, neto real −4,05 USDT.
        assert abs(res["neto_registro"] - (-4.05)) < 0.01, res["neto_registro"]
        assert alertas == [], alertas  # ni críticas ni avisos: valida también el 0,98 frente al bloc
        assert res["abiertas"] == 0


def t_ganancia_sin_cobrar():
    with tempfile.TemporaryDirectory() as d:
        carpeta = escribir(os.path.join(d, "registro"), registro_12_11(cobro_baja="pedido"))
        _, alertas, _, texto = correr(carpeta)
        assert ("A2", "ganancia_sin_cobrar") in codigos(alertas), alertas
        assert "gana 4.68 USDT" in texto, texto
        assert "CRÍTICA" in texto


def t_sin_cierre_con_dinero():
    with tempfile.TemporaryDirectory() as d:
        filas = [lectura("A3", "ord-3", "SUBMITTED", False, 5.0, 0.5, 0.0, AHORA - 3600),
                 lectura("A9", None, "FILLED", True, 0.0, None, 0.0, AHORA)]
        carpeta = escribir(os.path.join(d, "registro"), filas)
        _, alertas, _, _ = correr(carpeta)
        cod = codigos(alertas)
        assert ("A3", "sin_cierre") in cod, alertas
        marca = [a for a in alertas if a["codigo"] == "sin_cierre"][0]
        assert marca["nivel"] == "critica" and "5.00 USDT en juego" in marca["texto"], marca


def t_sin_liquidar_respeta_la_gracia():
    with tempfile.TemporaryDirectory() as d:
        filas = [
            lectura("A4", "ord-4", "FILLED", True, 3.0, 0.5, 6.0, AHORA - 10 * 60),   # 10 min: dentro de la gracia
            lectura("A5", "ord-5", "FILLED", True, 3.0, 0.5, 6.0, AHORA - 60 * 60),   # 60 min: fuera
            lectura("A9", None, "FILLED", True, 0.0, None, 0.0, AHORA),
        ]
        carpeta = escribir(os.path.join(d, "registro"), filas)
        _, alertas, _, _ = correr(carpeta, gracia=30)
        cod = codigos(alertas)
        assert ("A5", "sin_liquidar") in cod, alertas
        assert ("A4", "sin_liquidar") not in cod, alertas


def t_descuadres_y_pagos():
    with tempfile.TemporaryDirectory() as d:
        filas = [
            lectura("A7", "ord-7", "FILLED", True, 4.0, 0.5, 0.0, AHORA - 3000),
            liquidacion("A7", "ord-7", 0, 4.0, 0.0, -3.0, AHORA - 2900),              # neto mal anotado
            lectura("A8", "ord-8", "FILLED", True, 4.0, 0.5, 7.84, AHORA - 3000),
            liquidacion("A8", "ord-8", 1, 4.0, 7.0, 3.0, AHORA - 2900),               # pago debía ser 7,84
            cobro("A8", "ord-8", "cobrado", 7.0, AHORA - 2800),
            lectura("A9", None, "FILLED", True, 0.0, None, 0.0, AHORA),
        ]
        carpeta = escribir(os.path.join(d, "registro"), filas)
        _, alertas, _, _ = correr(carpeta)
        cod = codigos(alertas)
        assert ("A7", "descuadre_neto") in cod, alertas
        assert ("A8", "pago_no_cuadra") in cod, alertas


def t_pago_fuera_de_formula_es_aviso():
    with tempfile.TemporaryDirectory() as d:
        pago = round(pago_de_win(4.0, 0.5) * 1.05, 4)                               # 5 % por encima
        filas = [
            lectura("A6", "ord-6", "FILLED", True, 4.0, 0.5, pago, AHORA - 3000),
            liquidacion("A6", "ord-6", 1, 4.0, pago, round(pago - 4.0, 4), AHORA - 2900),
            cobro("A6", "ord-6", "cobrado", pago, AHORA - 2800),
            lectura("A9", None, "FILLED", True, 0.0, None, 0.0, AHORA),
        ]
        carpeta = escribir(os.path.join(d, "registro"), filas)
        _, alertas, _, _ = correr(carpeta)
        marca = [a for a in alertas if a["orden"] == "A6"]
        assert len(marca) == 1 and marca[0]["codigo"] == "pago_fuera_de_formula" and marca[0]["nivel"] == "aviso", alertas


def t_liquidacion_repetida_y_linea_ilegible():
    with tempfile.TemporaryDirectory() as d:
        filas = [
            lectura("A10", "ord-10", "FILLED", True, 2.0, 0.5, 3.92, AHORA - 3000),
            liquidacion("A10", "ord-10", 1, 2.0, 3.92, 1.92, AHORA - 2900),
            liquidacion("A10", "ord-10", 1, 2.0, 3.92, 1.92, AHORA - 2890),
            cobro("A10", "ord-10", "cobrado", 3.92, AHORA - 2800),
        ]
        carpeta = escribir(os.path.join(d, "registro"), filas, lineas_extra=["{esto no es json"])
        _, alertas, _, _ = correr(carpeta)
        cod = codigos(alertas)
        assert ("A10", "liquidacion_repetida") in cod, alertas
        assert any(a["codigo"] == "linea_ilegible" and a["nivel"] == "aviso" for a in alertas), alertas


def t_extracto_que_cuadra():
    with tempfile.TemporaryDirectory() as d:
        carpeta = escribir(os.path.join(d, "registro"), registro_12_11())
        ext = escribir_extracto(os.path.join(d, "extracto.csv"),
                                [("ord-1", "4,62", "0"), ("ord-2", "4.11", "4,6835")])
        res, alertas, cruce, texto = correr(carpeta, ext)
        assert criticas(alertas) == [], alertas
        assert abs(cruce["caja_extracto"] - cruce["caja_registro"]) < 0.01, cruce
        assert abs(cruce["caja_extracto"] - (-4.0465)) < 0.01, cruce
        assert "Caja según el extracto" in texto


def t_extracto_con_movimiento_no_registrado():
    with tempfile.TemporaryDirectory() as d:
        carpeta = escribir(os.path.join(d, "registro"), registro_12_11())
        ext = escribir_extracto(os.path.join(d, "extracto.csv"),
                                [("ord-1", "4.62", "0"), ("ord-2", "4.11", "4.6835"), ("ord-99", "2.00", "0")])
        _, alertas, _, _ = correr(carpeta, ext)
        cod = {a["codigo"] for a in criticas(alertas)}
        assert "movimiento_no_registrado" in cod and "caja_no_cuadra" in cod, alertas


def t_extracto_con_cobro_distinto_e_importe_distinto():
    with tempfile.TemporaryDirectory() as d:
        carpeta = escribir(os.path.join(d, "registro"), registro_12_11())
        ext = escribir_extracto(os.path.join(d, "extracto.csv"),
                                [("ord-1", "4.50", "0"), ("ord-2", "4.11", "4.00")])
        _, alertas, _, _ = correr(carpeta, ext)
        cod = codigos(criticas(alertas))
        assert ("ord-1", "importe_distinto") in cod, alertas
        assert ("ord-2", "cobro_distinto") in cod, alertas


def t_orden_del_registro_fuera_del_extracto_es_aviso():
    with tempfile.TemporaryDirectory() as d:
        carpeta = escribir(os.path.join(d, "registro"), registro_12_11())
        ext = escribir_extracto(os.path.join(d, "extracto.csv"), [("ord-1", "4.62", "0")])
        _, alertas, _, _ = correr(carpeta, ext)
        avisos = [a for a in alertas if a["codigo"] == "no_aparece_en_extracto"]
        assert len(avisos) == 1 and avisos[0]["orden"] == "ord-2" and avisos[0]["nivel"] == "aviso", alertas


def t_cli_codigos_de_salida_y_salidas():
    script = os.path.join(AQUI, "conciliador_dinero.py")
    with tempfile.TemporaryDirectory() as d:
        limpio = escribir(os.path.join(d, "limpio"), registro_12_11())
        malo = escribir(os.path.join(d, "malo"), registro_12_11(cobro_baja="pedido"))
        antes = {n: hashlib.sha256(open(os.path.join(malo, n), "rb").read()).hexdigest()
                 for n in os.listdir(malo)}
        detalle, texto = os.path.join(d, "detalle.json"), os.path.join(d, "texto.txt")

        r0 = subprocess.run([sys.executable, "-I", script, "--registro", limpio], capture_output=True, text=True)
        assert r0.returncode == 0, (r0.returncode, r0.stderr)
        assert "[Proyectos]" in r0.stdout

        r1 = subprocess.run([sys.executable, "-I", script, "--registro", malo, "--detalle", detalle,
                             "--texto", texto], capture_output=True, text=True)
        assert r1.returncode == 1, (r1.returncode, r1.stdout, r1.stderr)
        assert os.path.getsize(detalle) > 0 and os.path.getsize(texto) > 0
        with open(detalle, encoding="utf-8") as f:
            assert "alertas" in json.load(f)

        r2 = subprocess.run([sys.executable, "-I", script, "--registro", os.path.join(d, "no_existe")],
                            capture_output=True, text=True)
        assert r2.returncode == 2 and "no existe" in r2.stderr, (r2.returncode, r2.stderr)

        malext = os.path.join(d, "malo.csv")
        with open(malext, "w", encoding="utf-8") as f:
            f.write("orden,importe\nord-1,4\n")
        r3 = subprocess.run([sys.executable, "-I", script, "--registro", limpio, "--extracto", malext],
                            capture_output=True, text=True)
        assert r3.returncode == 2 and "columnas" in r3.stderr, (r3.returncode, r3.stderr)

        despues = {n: hashlib.sha256(open(os.path.join(malo, n), "rb").read()).hexdigest()
                   for n in os.listdir(malo)}
        assert antes == despues, "el conciliador no debe modificar el registro"


def t_texto_telegram_cabe_en_un_mensaje():
    with tempfile.TemporaryDirectory() as d:
        filas = []
        for i in range(120):
            oid = f"B{i}"
            filas += [lectura(oid, f"ord-b{i}", "SUBMITTED", False, 2.0, 0.5, 0.0, AHORA - 3000)]
        filas.append(lectura("Z", None, "FILLED", True, 0.0, None, 0.0, AHORA))
        carpeta = escribir(os.path.join(d, "registro"), filas)
        _, _, _, texto = correr(carpeta)
        assert len(texto) <= C.MAX_TEXTO, len(texto)
        assert "y " in texto and "más en el detalle" in texto


def t_extracto_con_coma_decimal_sin_comillas_se_rechaza():
    with tempfile.TemporaryDirectory() as d:
        carpeta = escribir(os.path.join(d, "registro"), registro_12_11())
        ruta = os.path.join(d, "malo.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("orden,importe_usdt,cobrado_usdt\nord-1,4,62,0\n")   # 4,62 sin comillas: 4 columnas
        try:
            correr(carpeta, ruta)
        except C.ErrorDatos as ex:
            assert "mismas columnas" in str(ex), ex
        else:
            raise AssertionError("un extracto con filas mal formadas debía rechazarse")


PRUEBAS = [v for k, v in sorted(globals().items()) if k.startswith("t_") and callable(v)]


def main():
    fallos = 0
    for prueba in PRUEBAS:
        try:
            prueba()
            print(f"OK    {prueba.__name__}")
        except AssertionError as ex:
            fallos += 1
            print(f"FALLO {prueba.__name__}: {ex}")
    print(f"\n{len(PRUEBAS) - fallos} de {len(PRUEBAS)} pruebas bien")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
