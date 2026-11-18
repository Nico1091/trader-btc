#!/usr/bin/env python3
"""Pruebas de evaluador_ventaja.py (solo biblioteca estándar).

Uso:
  python prueba_evaluador.py            corre todas las pruebas
  python prueba_evaluador.py --ejemplo  escribe ejemplo_SINTETICO.csv (datos inventados, no son del dueño)
"""

import csv
import json
import math
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evaluador_ventaja as ev  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
FALLOS = []
PASADAS = 0


def ver(nombre, cumple, detalle=""):
    global PASADAS
    if cumple:
        PASADAS += 1
        print(f"  ok   {nombre}")
    else:
        FALLOS.append(nombre)
        print(f"  FALLA {nombre} {detalle}")


def sintetica(semilla, estrategia, n, p, precio):
    """Apuestas inventadas: acierta con probabilidad p al precio dado. Semilla fija."""
    r = random.Random(semilla)
    return [ev.Apuesta(linea=i + 1, estrategia=estrategia, precio=precio,
                       acierto=1 if r.random() < p else 0, fecha="")
            for i in range(n)]


def escribir_csv(ruta, filas):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["estrategia", "precio", "acierto", "fecha"])
        w.writerows(filas)


def prueba_wilson():
    print("Intervalo de Wilson")
    lo, hi = ev.wilson(50, 100, 1.959964)
    ver("50 de 100 da 0,4038 – 0,5962 (valor de referencia)",
        abs(lo - 0.4038) < 1e-4 and abs(hi - 0.5962) < 1e-4, f"{lo:.4f} {hi:.4f}")
    lo, _ = ev.wilson(0, 10, 1.96)
    _, hi = ev.wilson(10, 10, 1.96)
    ver("0 de 10 tiene cota inferior 0; 10 de 10 tiene cota superior 1", lo == 0.0 and hi == 1.0)
    lo, hi = ev.wilson(19, 25, 1.96)
    ver("19 de 25 tiene cota inferior bajo 0,57 (25 apuestas no prueban nada)", lo < 0.57, f"{lo:.3f}")


def prueba_cuentas():
    print("Cuentas de equilibrio y ganancia")
    apuestas = sintetica(1, "X", 50, 0.5, 0.51)
    res = ev.evaluar(apuestas, minimo=10, comision=0.02)
    fila = res["filas"][0]
    ver("equilibrio con precio 0,51 y comisión 2 % es 0,51 / 0,98 = 0,5204",
        abs(fila["equilibrio"] - 0.51 / 0.98) < 1e-9, f"{fila['equilibrio']:.6f}")
    p = fila["acierto"]
    ver("ganancia esperada = p × 0,98 / 0,51 − 1",
        abs(fila["ganancia_esperada"] - (p * 0.98 / 0.51 - 1)) < 1e-9)
    ver("z de una sola estrategia es 1,96", abs(ev.z_corregido(1) - 1.96) < 0.001, str(ev.z_corregido(1)))
    ver("z sube al mirar más estrategias (corrección por elegir)", ev.z_corregido(20) > ev.z_corregido(1))


def prueba_veredictos():
    print("Veredictos")
    casos = [
        ("ventaja real y mucha prueba -> VENTAJA DEMOSTRADA",
         sintetica(11, "A", 3000, 0.56, 0.51), "VENTAJA DEMOSTRADA"),
        ("sin ventaja con muchos datos -> SIN VENTAJA",
         sintetica(12, "A", 5000, 0.50, 0.51), "SIN VENTAJA"),
        ("ventaja aparente con 150 apuestas -> NO DEMOSTRADA",
         sintetica(13, "A", 150, 0.53, 0.51), "NO DEMOSTRADA"),
        ("50 apuestas -> PRUEBA INSUFICIENTE aunque el acierto sea alto",
         sintetica(14, "A", 50, 0.70, 0.51), "PRUEBA INSUFICIENTE"),
    ]
    for nombre, apuestas, esperado in casos:
        res = ev.evaluar(apuestas, minimo=100, comision=0.02)
        obtenido = res["filas"][0]["veredicto"]
        ver(nombre, obtenido == esperado, f"obtuvo {obtenido}")

    # La regla del nodo (19 de 25 a precio 0,544; equilibrio 0,544 / 0,98 = 55,5 %).
    # Con z = 1,96 (una sola mirada) la cota inferior pasa el equilibrio por poco;
    # con la corrección de cinco estrategias ya no. Ver LEEME.md.
    lo_1, _ = ev.wilson(19, 25, 1.96)
    lo_5, _ = ev.wilson(19, 25, ev.z_corregido(5))
    ver("19 de 25 con z 1,96: cota inferior 56,6 % (pasa el equilibrio 55,5 % por poco)",
        abs(lo_1 - 0.5657) < 1e-3 and lo_1 > 0.5551, f"{lo_1:.4f}")
    ver("19 de 25 con corrección de 5 estrategias: cota inferior 50,2 % (no prueba nada)",
        abs(lo_5 - 0.5024) < 1e-3 and lo_5 < 0.5551, f"{lo_5:.4f}")
    exactas = [ev.Apuesta(i, "NODO", 0.544, 1 if i < 19 else 0, "") for i in range(25)]
    fila = ev.resumir("NODO", exactas, ev.z_corregido(5), 0.98, minimo=25)
    ver("19 de 25 a 0,544, corregido por 5 estrategias: no es VENTAJA DEMOSTRADA",
        fila["veredicto"] == "NO DEMOSTRADA", fila["veredicto"])

    # Muchas estrategias: la corrección de Bonferroni hace más difícil la ventaja
    una = ev.evaluar(sintetica(16, "A", 800, 0.575, 0.51), minimo=100)["filas"][0]
    varias = []
    for k in range(40):
        varias += sintetica(100 + k, f"V{k}", 800, 0.575, 0.51)
    res40 = ev.evaluar(varias, minimo=100)
    ver("con 40 estrategias el z corregido es mayor que con una",
        res40["z"] > ev.z_corregido(1))
    ver("con 40 estrategias, la cota inferior de cada una baja",
        res40["filas"][0]["intervalo"][0] < una["intervalo"][0] + 1e-12)


def prueba_lectura():
    print("Lectura y errores de datos")
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "buena.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("estrategia,precio,acierto,fecha\nE1,\"0,51\",1,2026-11-10\nE1,0.52,0,2026-11-10\n")
        ap = ev.leer_apuestas(ruta)
        ver("acepta precio con coma decimal (0,51)", ap[0].precio == 0.51 and ap[1].precio == 0.52)

        ruta = os.path.join(tmp, "buena.jsonl")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(json.dumps({"estrategia": "E2", "precio": 0.5, "acierto": True}) + "\n\n")
        ap = ev.leer_apuestas(ruta)
        ver("lee JSONL y salta líneas vacías", len(ap) == 1 and ap[0].acierto == 1)

        malas = {
            "precio 51 en lugar de 0,51": "estrategia,precio,acierto\nE1,51,1\n",
            "acierto 2": "estrategia,precio,acierto\nE1,0.5,2\n",
            "sin estrategia": "estrategia,precio,acierto\n ,0.5,1\n",
            "precio con letras": "estrategia,precio,acierto\nE1,barato,1\n",
        }
        for nombre, contenido in malas.items():
            ruta = os.path.join(tmp, "mala.csv")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            try:
                ev.leer_apuestas(ruta)
                ver(f"rechaza {nombre}", False, "no dio error")
            except ev.ErrorDatos as e:
                ver(f"rechaza {nombre} y dice la línea", "línea 2" in str(e), str(e))

        ruta = os.path.join(tmp, "roto.jsonl")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("{no es json}\n")
        try:
            ev.leer_apuestas(ruta)
            ver("rechaza JSONL roto", False)
        except ev.ErrorDatos as e:
            ver("rechaza JSONL roto y dice la línea", "línea 1" in str(e), str(e))

        codigo = ev.main([os.path.join(tmp, "no_existe.csv")])
        ver("archivo inexistente devuelve código 2", codigo == 2)


def prueba_cli():
    print("Línea de comandos")
    ruta_ejemplo = os.path.join(AQUI, "ejemplo_SINTETICO.csv")
    if not os.path.exists(ruta_ejemplo):
        generar_ejemplo(ruta_ejemplo)
    with tempfile.TemporaryDirectory() as tmp:
        salida = os.path.join(tmp, "res.json")
        codigo = ev.main([ruta_ejemplo, "--json", salida])
        ver("corre sobre el ejemplo y devuelve 0", codigo == 0)
        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)
        ver("el JSON trae una fila por estrategia más TODAS",
            [x["estrategia"] for x in datos["filas"]][-1] == "TODAS" and len(datos["filas"]) == 5,
            str([x["estrategia"] for x in datos["filas"]]))
        ver("comisión fuera de rango devuelve código 2", ev.main([ruta_ejemplo, "--comision", "2"]) == 2)


def generar_ejemplo(ruta):
    """Datos inventados con semilla fija. Sirven para ver la salida, no dicen nada del mercado."""
    filas = []
    perfiles = [("E1", 400, 0.58), ("E2", 150, 0.56), ("E3", 60, 0.62), ("E4", 900, 0.50)]
    for estrategia, n, p in perfiles:
        r = random.Random(f"ejemplo-{estrategia}")
        for i in range(n):
            precio = round(r.uniform(0.49, 0.55), 2)
            acierto = 1 if r.random() < p else 0
            filas.append([estrategia, f"{precio:.2f}".replace(".", ","), acierto, ""])
    escribir_csv(ruta, filas)


def main():
    if "--ejemplo" in sys.argv:
        generar_ejemplo(os.path.join(AQUI, "ejemplo_SINTETICO.csv"))
        print("ejemplo_SINTETICO.csv escrito (datos inventados)")
        return 0
    prueba_wilson()
    prueba_cuentas()
    prueba_veredictos()
    prueba_lectura()
    prueba_cli()
    print()
    print(f"{PASADAS} pruebas bien, {len(FALLOS)} fallas")
    for f in FALLOS:
        print(f"  - {f}")
    return 0 if not FALLOS else 1


if __name__ == "__main__":
    sys.exit(main())
