# -*- coding: utf-8 -*-
"""Prueba del Centro con el plan v9 (20/11/2026), criterio A7: con ganancia.json del nodo, los avisos muestran dinero y no
«k de 25», y se apagan los avisos de 75 % y 82 %; sin el archivo (la Mesa del PC), todo queda como antes.
Sin red: el Centro se monta sin conexión y sus avisos se recogen en una lista. Uso: python -I prueba_centro_dinero.py"""
import json
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
for d in (AQUI, os.path.join(AQUI, "..", "dispositivos")):
    if os.path.isdir(d):
        sys.path.insert(0, d)
import centro as CE  # noqa: E402

FALLOS, CUENTA = [], [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


BASE = tempfile.mkdtemp(prefix="centro_dinero_")
CE.DATOS = os.path.join(BASE, "datos")
CE.ARCHIVO = os.path.join(CE.DATOS, "centro.json")
CE.GANANCIA = os.path.join(BASE, "nodo", "ganancia.json")
T = 1795209300


def montar():
    c = CE.Centro(None)
    c.foto = {"precio": 63000.0, "estrategias": [{"id": "E1", "n25": 25, "k25": 21, "apta": True, "pct25": 84, "racha": 3,
                                                 "azar": 0.01, "largo": 54.6}]}
    c.ops["E1"] = [{"t": T - 3600 * (i + 1), "dir": 1, "res": 0 if i in (0, 12) else 1, "base": 63000.0, "salida": 63100.0}
                   for i in range(25)][::-1]      # 23 de 25: apta (82 %) con la medida de antes
    enviados = []
    c.notificar = lambda aviso, al=None: enviados.append(aviso)
    return c, enviados


op = {"t": T, "dir": 1, "si": False, "doi": None, "base": 63000.0, "res": None}

# sin ganancia.json: como antes
c, env = montar()
c._avisar_senal("E1", dict(op))
ok(env and "de 25" in env[-1]["corto"] and "APTA (82 %)" in env[-1]["texto"], "sin ganancia.json (Mesa del PC): la señal dice «k de 25» como antes")
ok(c._niveles() is True and any("APTA" in a["corto"] for a in env), "sin ganancia.json: el aviso de apta (82 %) sigue como antes")

# con ganancia.json: dinero
os.makedirs(os.path.dirname(CE.GANANCIA))
with open(CE.GANANCIA, "w", encoding="utf-8") as f:
    json.dump({"version": "v9", "hora": T, "fuentes": {"centro|E1": {
        "estado": "MUESTRA INSUFICIENTE", "n": 41, "neto": -8.64, "por_usdt": -0.211, "prueba": 0.4012, "umbral_prueba": 160.0,
        "alto": False, "pausa": False}}}, f)
c, env = montar()
c._avisar_senal("E1", dict(op))
s = env[-1]
ok("de 25" not in s["corto"] and "dinero -8,64 en 41" in s["corto"] and "de 25" not in s["texto"] and "APTA" not in s["texto"]
   and "En dinero: 41 apuestas a precio real" in s["texto"] and "MUESTRA INSUFICIENTE" in s["texto"],
   "con ganancia.json: la señal dice el dinero a precio real (−8,64 en 41) y no «k de 25» ni APTA")
o = dict(op, res=1, salida=63200.0, tg="11", tg_txt=s["texto"])
c._avisar_resultado("E1", o)
r = env[-1]
ok("por su medida propia, ACIERTO" in r["texto"] and "En dinero" in r["texto"] and "de 25" not in r["corto"],
   "con ganancia.json: el resultado dice que el acierto es de su medida propia y repite el dinero")
n = len(env)
ok(c._niveles() is False and len(env) == n, "con ganancia.json: no salen los avisos de 75 % ni de 82 % (los de dinero los manda el nodo)")
with open(CE.GANANCIA, "w", encoding="utf-8") as f:
    json.dump({"version": "v9", "hora": T, "fuentes": {}}, f)
c._avisar_senal("E1", dict(op, t=T + 900))
ok("sin precio real" in env[-1]["corto"] and "todavía sin apuestas" in env[-1]["texto"],
   "con ganancia.json sin esa estrategia: dice que todavía no hay apuestas con precio real")

shutil.rmtree(BASE, ignore_errors=True)
print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
