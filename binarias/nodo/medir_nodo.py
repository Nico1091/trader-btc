# -*- coding: utf-8 -*-
"""Costo de una revisión del nodo (17/11/2026): tiempo de proceso y bytes leídos, con archivos del tamaño de los reales.
No toca los archivos del equipo: arma copias falsas en una carpeta temporal. Sirve para medir en el teléfono mismo.

Arma: centro.json con 5 estrategias de 2.000 señales cada una (lo máximo que guarda el Centro), quince.json con 400 y tres
días de registro del operador con una mirada por minuto en los dos mercados (unos 2,5 MB por día, como en el estado 1).
Mide: la primera vuelta (al arrancar), una vuelta sin cambios (la de casi siempre, cada 10 s), una vuelta cuando el Centro
reescribe su archivo (una vez por minuto) y una con miradas nuevas del operador.
Uso: python3 -I medir_nodo.py"""
import json
import os
import random
import shutil
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nodo as N  # noqa: E402


def mirada(W, t, m, hora):
    lados = {str(k): {"papel": "perdedor", "p": 0.3123456, "p_prud": 0.2934567, "q": None, "G": None, "G_prud": None,
                      "limite": 0.25, "kelly": None, "bid": None, "libro": []} for k in (1, -1)}
    return {"W": W, "tipo": "mirada", "serie": "sin_llave", "t": t, "topic": None, "m": m, "plazo": "15 min", "hora": hora,
            "demora_s": 1.23, "strike": 73500.12, "cierre": 73480.5, "vivo": 73481.2, "resta_s": 600.0, "z": -0.8123,
            "z_cierre": -0.8011, "p": 0.312345, "p_cierre": 0.309876, "perdedor": 1, "x": [round(random.random(), 6) for _ in range(12)],
            "lados": lados, "decide": 0, "motivo": "sin libro: solo se mide el modelo", "celda": None, "sombra": False,
            "modelo": "55ae2f665546aa40", "politica": 1, "margen": 0.1, "comision": 0.02}


def armar(base, ahora):
    cent = os.path.join(base, "centinela")
    os.makedirs(os.path.join(cent, "datos"), exist_ok=True)
    ops = {}
    for e in ("E1", "E2", "E3", "E4", "E5"):
        lista = []
        for i in range(2000):
            t = int(ahora // 300 * 300) - (2000 - i) * 1200
            o = {"t": t, "dir": 1 if i % 2 else -1, "base": 73500.0 + i, "res": i % 2, "semilla": i < 1800, "si": False,
                 "doi": 0.0001, "salida": 73510.0}
            if i >= 1800:
                o.update(tg=1000 + i, tg_txt="E1 · Ruptura de 20 velas, al revés\n▲ SUBE · BTC en 73.500 · entra 12:31 · vence 12:46\n"
                         "Últimas 25: 16 de 25 (64 %) · racha 1 · fondo 54,6 %\nNO por su regla: su papel de hoy va -0,40.\nPapel: el Centro no compra.")
            lista.append(o)
        ops[e] = lista
    N.escribir_json(os.path.join(cent, "datos", "centro.json"), {"ops": ops, "ultimo5": 0, "niveles": {}})
    N.escribir_json(os.path.join(cent, "quince.json"), {"ops": [{"t": int(ahora // 900 * 900) - (400 - i) * 900, "dir": 1, "base": 73500.0,
                                                                  "res": i % 2} for i in range(400)]})
    reg = os.path.join(base, "operador", "registro")
    os.makedirs(reg, exist_ok=True)
    for d in range(3):
        dia = ahora - (2 - d) * 86400
        with open(os.path.join(reg, time.strftime("%Y%m%d", time.gmtime(dia - 5 * 3600)) + ".jsonl"), "w", encoding="utf-8") as f:
            for k in range(1440 if d < 2 else 600):
                h = dia - 86400 + k * 60 if d < 2 else ahora - (600 - k) * 60
                for W in (15, 5):
                    t = int(h // (60 * W) * 60 * W)
                    f.write(json.dumps(mirada(W, t, int((h - t) // 60) or 1, h), ensure_ascii=False) + "\n")
    car = os.path.join(base, "nodo")
    os.makedirs(car, exist_ok=True)
    return {"rol": "telefono", "centinela": cent, "operador": os.path.join(base, "operador"), "umbral": 19, "preferido": "telefono",
            "par_ip": "127.0.0.1", "puerto": 0, "par_puerto": 9, "carpeta": car, "rutas_claude": list(N.RUTAS_CLAUDE), "esfuerzo": "low"}


def medir_vuelta(c, estado, central, fuentes):
    t1, p1 = time.perf_counter(), time.process_time()
    N.vuelta(c, estado, central, fuentes)
    return (time.perf_counter() - t1) * 1000, (time.process_time() - p1) * 1000, fuentes.leidos


def main():
    base = tempfile.mkdtemp(prefix="medir_nodo_")
    N.AQUI = base
    ahora = time.time()
    c = armar(base, ahora)
    tam = {n: os.path.getsize(os.path.join(r, n)) for r, _d, fs in os.walk(base) for n in fs}
    estado = {}
    fuentes = N.Fuentes(c)
    central = N.Central(c, estado, fuentes.vector, fuentes.operador_vivo)
    filas = [("primera vuelta (al arrancar)",) + medir_vuelta(c, estado, central, fuentes)]
    sin = [medir_vuelta(c, estado, central, fuentes) for _ in range(20)]
    filas.append(("vuelta sin cambios (media de 20)", sum(x[0] for x in sin) / 20, sum(x[1] for x in sin) / 20, sum(x[2] for x in sin) / 20))
    ruta_c = os.path.join(c["centinela"], "datos", "centro.json")
    os.utime(ruta_c, (ahora + 5, ahora + 5))
    filas.append(("vuelta con el Centro reescrito (1 por minuto)",) + medir_vuelta(c, estado, central, fuentes))
    hoy = sorted(os.listdir(os.path.join(c["operador"], "registro")))[-1]
    with open(os.path.join(c["operador"], "registro", hoy), "a", encoding="utf-8") as f:
        for W in (15, 5):
            f.write(json.dumps(mirada(W, int(ahora // (60 * W) * 60 * W), 1, ahora), ensure_ascii=False) + "\n")
    filas.append(("vuelta con dos miradas nuevas del operador",) + medir_vuelta(c, estado, central, fuentes))
    print(f"Python {sys.version.split()[0]} · archivos: centro.json {tam.get('centro.json', 0) / 1e6:.2f} MB, quince.json "
          f"{tam.get('quince.json', 0) / 1e3:.0f} KB, registro del operador {sum(v for k, v in tam.items() if k.endswith('.jsonl')) / 1e6:.1f} MB en 3 días")
    for nombre, ms, cpu, b in filas:
        print(f"- {nombre}: {ms:.1f} ms de reloj, {cpu:.1f} ms de procesador, {b / 1024:.1f} KB leídos")
    n_min = 6
    cpu_min = (filas[1][2] * (n_min - 1) + filas[2][2]) / n_min
    print(f"Promedio por revisión en un minuto típico (5 sin cambios y 1 con el Centro reescrito): {cpu_min:.1f} ms de procesador; "
          f"al día {cpu_min * 8640 / 1000:.0f} s de procesador.")
    shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
