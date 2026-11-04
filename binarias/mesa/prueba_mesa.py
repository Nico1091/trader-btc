"""Pruebas de la Mesa, sin red y sin órdenes: Binance va simulada. Uso: python -I prueba_mesa.py"""
import ast
import os
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "dispositivos"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np  # noqa: E402

import analista  # noqa: E402
import borrador as Bo  # noqa: E402
import conexion as C  # noqa: E402
import reglas as R  # noqa: E402

fallos = 0


def ver(nombre, cond):
    global fallos
    print(("bien " if cond else "FALLA") + " · " + nombre)
    fallos += 0 if cond else 1


# 1) la señal es la misma de la caja: se compara con el código real de semaforo.py
fuente = open(os.path.join(os.path.dirname(AQUI), "dispositivos", "semaforo.py"), encoding="utf-8").read()
nodo = next(n for n in ast.parse(fuente).body if isinstance(n, ast.FunctionDef) and n.name == "senal")
ns = {}
exec(compile(ast.Module([nodo], []), "semaforo", "exec"), ns)
a = np.load(os.path.join(os.path.dirname(AQUI), "datos", "BTCUSDT_um_1m_tb.npy"), mmap_mode="r")[-200000:]
v = [(int(x[0]) // 1000, float(x[2]), float(x[3]), float(x[4])) for x in a]
iguales, con_senal = 0, 0
idx = [i for i, x in enumerate(v) if i > 140 and (x[0] + 60) % 900 == 0]
for i in idx:
    w, t = v[i - 130:i + 1], v[i][0] + 60
    s1, s2 = Bo.senal(w, t), ns["senal"](w, t)
    iguales += s1 == s2
    con_senal += s1 != 0
ver(f"señal idéntica a semaforo.py en {len(idx)} decisiones de 15 min ({con_senal} con señal)", iguales == len(idx))


def op(t, res=1, neto=0.9, si=False, semilla=False, d=1, doi=0.0):
    return {"t": t, "dir": d, "res": res, "neto": neto, "si": si, "semilla": semilla, "doi": doi}


# 2) el arnés
ahora = 1793833200.0 + 3600 * 5
hoy = R.ini_dia(ahora)
buenas = [op(hoy - 90000 + 900 * i) for i in range(25)]
mer = {"ask": {1: 0.51, -1: 0.51}}
K = dict(mercado=mer, autorizado=True, billetera=True, saldo=46.28)
abierta = {"t": ahora - 10, "dir": 1, "res": None, "si": True, "doi": 0.0}
pos = [op(ahora - 3000)]
e = R.evaluar([], ahora, None)
ver("sin operaciones de hoy: NO", e["nivel"] == "NO" and not e["dando"])
e = R.evaluar(buenas + pos, ahora, mer)
ver("borrador sumando sin señal: ATENTO", e["nivel"] == "ATENTO" and e["dando"])
e = R.evaluar(buenas + [op(ahora - 3000, 0, -1.02)], ahora, mer)
ver("borrador perdiendo: NO", e["nivel"] == "NO" and not e["dando"])
ver("un SÍ perdió hoy: NO aunque sume", R.evaluar(buenas + pos * 3 + [op(ahora - 2000, 0, -1.02, si=True)], ahora, mer)["nivel"] == "NO")
e = R.evaluar(buenas + pos + [abierta], ahora, **K)
ver("todo cumplido y sube: COMPRE con botón", e["nivel"] == "COMPRE" and e["boton"])
e = R.evaluar(buenas + pos + [{**abierta, "dir": -1}], ahora, **K)
ver("baja: VENDA con botón", e["nivel"] == "VENDA" and e["boton"] and e["sentido"] == -1)
ver("señal sin SÍ: NO, sin botón", not R.evaluar(buenas + pos + [{**abierta, "si": False}], ahora, **K)["boton"])
ver("sin su autorización: ESPERE", R.evaluar(buenas + pos + [abierta], ahora, **{**K, "autorizado": False})["nivel"] == "ESPERE")
ver("sin billetera: ESPERE", R.evaluar(buenas + pos + [abierta], ahora, **{**K, "billetera": False})["nivel"] == "ESPERE")
ver("precio caro: ESPERE", R.evaluar(buenas + pos + [abierta], ahora, **{**K, "mercado": {"ask": {1: 0.54}}})["nivel"] == "ESPERE")
ver("sin precio: ESPERE", R.evaluar(buenas + pos + [abierta], ahora, **{**K, "mercado": None})["nivel"] == "ESPERE")
ver("señal vieja, fuera de la ventana: sin botón", not R.evaluar(buenas + pos + [{**abierta, "t": ahora - 90}], ahora, **K)["boton"])
malas = [op(hoy - 90000 + 900 * i, 1 if i < 18 else 0) for i in range(25)]
ver("72 % de aciertos: ESPERE (pide 75 %)", R.evaluar(malas + pos + [abierta], ahora, **K)["nivel"] == "ESPERE")
semillas = [op(hoy - 90000 + 900 * i, semilla=True) for i in range(25)]
ver("sembradas no cuentan como precio real: ESPERE", R.evaluar(semillas + [{**pos[0], "semilla": True}, abierta], ahora, **K)["nivel"] == "ESPERE")
ver("importe 5 % de 46,28 = 2,31", R.importe(46.28, 5) == 2.31)
ver("pedir 50 % se queda en el tope de 16 %", R.importe(46.28, 50) == 7.4)
ver("saldo que no alcanza el mínimo dentro del tope: None", R.importe(10, 5) is None)
ver("comprar a 0,51 y acertar: +0,9408 por unidad", abs(R.neto_op(1, 0.51) - 0.9408) < 0.0001)
ver("fallar: −1,02", abs(R.neto_op(0, 0.51) + 1.02) < 1e-9)

# 3) el analista propio, sin IA
vv = [(1793833200 + 60 * i, 80000.0, 80100.0 + i % 7, 79900.0 - i % 5, 80000.0) for i in range(150)]
d = analista.disparadores(vv)
ver("disparadores: máximo y mínimo de 20 velas de 5 min", d == (80106.0, 79896.0))
eA = R.evaluar(buenas + pos, ahora, mer)
ver("ATENTO: dice los dos precios y no manda a operar", "80.106" in analista.leer(eA, vv, None, ahora)["explicacion"] and "Compre" not in analista.leer(eA, vv, None, ahora)["titular"])
eC = R.evaluar(buenas + pos + [abierta], ahora, **K)
ver("COMPRE: flecha de sube", analista.leer(eC, vv, None, ahora)["marcas"][0]["tipo"] == "flecha_sube")

# 4) órdenes con Binance simulada: ningún camino sale fuera de las reglas
import mesa as M  # noqa: E402

llamadas = []
tmp = tempfile.mkdtemp()
M.REALES, M.AUTORIZADO = os.path.join(tmp, "r.jsonl"), os.path.join(tmp, "A")
Bo.ARCHIVO = os.path.join(tmp, "b.json")
open(M.AUTORIZADO, "w").close()
C.saldo_spot = lambda: 46.28
C.billetera = lambda: {"walletAddress": "0xabc", "walletId": "w"}
C.mercado_15m = lambda t: {"t": t, "topic": 9, "tokens": {1: "U", -1: "D"}}
C.libro = lambda m, lado: (0.51, 0.50)
precio_cot = [0.51]


def cotizar(*a):
    llamadas.append(("cotizar", a))
    return {"averagePrice": precio_cot[0], "quoteId": "q"}


def ordenar(*a):
    llamadas.append(("ordenar", a))
    return {"orderId": "1"}


C.cotizar, C.ordenar, M.log = cotizar, ordenar, lambda m: None
mo = M.Motor()
mo.bor._guardar = lambda: None
ah = int(time.time())
R.ini_dia = lambda x: ah - 3000  # el «hoy» de la prueba no depende de la hora en que corra
mo.bor.ops = [op(ah - 90000 + 900 * i) for i in range(25)] + [op(ah - 2500)] + [{"t": ah - 5, "dir": 1, "res": None, "si": True, "doi": 0.0}]
r = mo.ordenar(-1, 5)
ver("vender cuando la señal es sube: rechazado sin tocar Binance", not r["ok"] and not llamadas)
r = mo.ordenar(1, 5)
ver("comprar con todo cumplido: una cotización y una orden", r["ok"] and [x[0] for x in llamadas] == ["cotizar", "ordenar"])
ver("la orden va por el token de sube", llamadas[0][1][1] == "U")
r = mo.ordenar(1, 5)
ver("segundo toque en la misma señal: rechazado", not r["ok"] and len(llamadas) == 2)
open(M.REALES, "w").close()
precio_cot[0], n = 0.60, len(llamadas)
r = mo.ordenar(1, 5)
ver("cotización cara: cotiza pero no ordena", not r["ok"] and [x[0] for x in llamadas[n:]] == ["cotizar"])
os.remove(M.AUTORIZADO)
n = len(llamadas)
ver("sin autorización: nada", not mo.ordenar(1, 5)["ok"] and len(llamadas) == n)
print("\nFALLOS:", fallos)
sys.exit(1 if fallos else 0)
