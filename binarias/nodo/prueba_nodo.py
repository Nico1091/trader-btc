# -*- coding: utf-8 -*-
"""Pruebas del nodo puente con datos simulados (17/11/2026). Sin red: Telegram y Claude se sustituyen por funciones falsas."""
import json
import os
import shutil
import sys
import tempfile
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nodo as N  # noqa: E402

FALLOS = []
CUENTA = [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que)
    if not cond:
        FALLOS.append(que)


def ops(aciertos, total=25, abierta=None, t0=1794900000):
    lista = [{"t": t0 + i * 900, "dir": -1, "res": 1 if i < aciertos else 0} for i in range(total)]
    if abierta:
        lista.append({"t": abierta[0], "dir": abierta[1], "base": 65000.0, "res": None})
    return lista


def montar(base, rol, centro=None, quince=None):
    cent = os.path.join(base, rol, "centinela")
    os.makedirs(os.path.join(cent, "datos"), exist_ok=True)
    if centro is not None:
        N.escribir_json(os.path.join(cent, "datos", "centro.json"), {"ops": centro})
    if quince is not None:
        N.escribir_json(os.path.join(cent, "quince.json"), {"ops": quince})
    return {"rol": rol, "centinela": cent, "operador": os.path.join(base, rol, "operador"), "umbral": 19,
            "caja_ip": "127.0.0.1"}


enviados, consultas = [], []
N.telegram = lambda texto: enviados.append(texto) or True
N.decision_claude = lambda grupo: (consultas.append(grupo) or ("COMPRAR BAJA", "coinciden y van altos"))
N.AQUI = tempfile.mkdtemp(prefix="nodo_prueba_")
base = tempfile.mkdtemp(prefix="nodo_fuentes_")
T = 1794930000

# 1) resumen: últimas 25, racha y fondo, con sumas en bucle
r = N.resumen(ops(20) + [{"t": 1, "dir": 1, "res": 1}, {"t": 2, "dir": 1, "res": 1}])
ok(r["aciertos"] == 20 and r["racha"] == 2, "resumen: últimas 25 y racha")

# 2) al arrancar no reenvía lo que ya estaba abierto
c = montar(base, "telefono", centro={"E2": ops(20, abierta=(T, -1))})
est = {}
ok(N.puntos_nuevos(c, est) == [], "primera vuelta: lo abierto al arrancar no se reenvía")
# 3) señal nueva con 20 de 25 = punto ALTO
N.escribir_json(os.path.join(c["centinela"], "datos", "centro.json"), {"ops": {"E2": ops(20, abierta=(T + 900, -1))}})
nuevos = N.puntos_nuevos(c, est)
ok(len(nuevos) == 1 and nuevos[0]["alto"] and nuevos[0]["aciertos"] == 20, "señal nueva con 20 de 25: punto ALTO")
ok(N.puntos_nuevos(c, est) == [], "la misma señal no se repite")
# 4) señal nueva con 16 de 25 = punto bajo
N.escribir_json(os.path.join(c["centinela"], "datos", "centro.json"), {"ops": {"E2": ops(16, abierta=(T + 1800, 1))}})
bajo = N.puntos_nuevos(c, est)
ok(len(bajo) == 1 and not bajo[0]["alto"], "señal con 16 de 25: punto bajo (no se envía)")

# 5) caja central: junta los puntos que coinciden en mercado y sentido en un solo mensaje, y consulta a Claude
cc = montar(base, "caja", quince=ops(19, abierta=(T - 100, -1)))
central = N.Central(cc)
N.ESPERA_JUNTAR = 0
p_tel = dict(nuevos[0], t=T + 900)
p_caja = dict(p_tel, clave="caja|quince|quince|x", equipo="caja", fuente="quince", estrategia="quince",
              nombre="vigía de 15 min", aciertos=19)
central.recibir(p_tel)
central.recibir(p_caja)
central.recibir(p_tel)                       # repetido: no cuenta dos veces
central.despachar()
ok(len(enviados) == 1 and "Coinciden 2" in enviados[0] and "COMPRAR BAJA" in enviados[0],
   "caja: dos fuentes que coinciden salen en un mensaje con la decisión de Claude")
ok(len(consultas) == 1 and len(consultas[0]) == 2, "Claude recibe un solo paquete con las dos fuentes")
# 6) un grupo solo con puntos bajos no se envía
central.recibir(dict(bajo[0], t=T + 3000))
central.despachar()
ok(len(enviados) == 1, "grupo sin puntos altos: no se envía")

# 7) teléfono con la caja caída: envía él mismo (basta con que uno esté conectado)
c2 = dict(c, caja_ip="127.0.0.1")
N.PUERTO = 1                                  # nadie escucha: la caja «no responde»
est2 = {"iniciado": True, "vistos": []}
N.escribir_json(os.path.join(c["centinela"], "datos", "centro.json"), {"ops": {"E1": ops(21, abierta=(T + 5000, 1))}})
antes = len(enviados)
N.vuelta(c2, est2)
ok(len(enviados) == antes + 1 and "lo envía el teléfono" in enviados[-1], "caja caída: el teléfono envía lo suyo")

# 8) teléfono con la caja viva: entrega por la red con firma y la caja lo recibe
N.PUERTO = 18799
os.makedirs(os.path.join(os.path.expanduser("~"), ".config", "binarias"), exist_ok=True)
secreto_falso = os.path.join(N.AQUI, "secreto")
open(secreto_falso, "w").write("prueba-secreta")
N.SECRETO = secreto_falso
central2 = N.Central(cc)
srv = N.servidor(central2)
time.sleep(0.3)
N.escribir_json(os.path.join(c["centinela"], "datos", "centro.json"), {"ops": {"E3": ops(22, abierta=(T + 7000, -1))}})
antes = len(enviados)
N.vuelta(c2, est2)
time.sleep(0.3)
recibidos = [p for g in central2.grupos.values() for p in g["puntos"]]
ok(len(recibidos) == 1 and recibidos[0]["estrategia"] == "E3" and len(enviados) == antes,
   "caja viva: el teléfono le entrega el punto firmado y no lo duplica")
# 9) firma falsa: la caja la rechaza
import socket as _s
cuerpo = json.dumps([dict(recibidos[0], clave="falsa")]).encode()
FIN = chr(13) + chr(10)
pet = (f"POST /puntos HTTP/1.0{FIN}Host: x{FIN}X-Firma: {'0' * 64}{FIN}Content-Length: {len(cuerpo)}{FIN}{FIN}").encode() + cuerpo
with _s.create_connection(("127.0.0.1", N.PUERTO), timeout=4) as k:
    k.sendall(pet)
    resp = k.recv(200)
ok(b" 403" in resp and all(p["clave"] != "falsa" for g in central2.grupos.values() for p in g["puntos"]),
   "firma falsa: la caja la rechaza (403) y no guarda el punto")
srv.shutdown()

# 9b) el operador de Fable: llenado + resultado del registro se leen como su propia serie de aciertos
reg = os.path.join(base, "caja", "operador", "registro")
os.makedirs(reg, exist_ok=True)
with open(os.path.join(reg, "20261117.jsonl"), "w", encoding="utf-8") as f:
    for i in range(25):
        t = 1794900000 + i * 900
        f.write(json.dumps({"tipo": "llenado", "t": t, "lado": -1, "llenado": "0.5", "sombra": False}) + "\n")
        f.write(json.dumps({"tipo": "resultado", "t": t, "ganador": -1 if i < 20 else 1}) + "\n")
    f.write(json.dumps({"tipo": "llenado", "t": T + 9000, "lado": 1, "sombra": False}) + "\n")
    f.write(json.dumps({"tipo": "llenado", "t": T + 9000, "lado": -1, "sombra": True}) + "\n")
fu = [x for x in N.leer_fuentes(cc) if x[0] == "operador"]
ok(len(fu) == 1 and fu[0][2]["aciertos"] == 20 and fu[0][2]["abierta"]["dir"] == 1,
   "operador de Fable: 20 de 25 desde su registro, y la compra de sombra no cuenta")

# 10) interpretar falla cerrado
ok(N.interpretar("COMPRAR SUBE\nporque sí")[0] == "COMPRAR SUBE", "Claude: COMPRAR SUBE se lee")
ok(N.interpretar("tal vez compre")[0] == "NO COMPRAR", "Claude: respuesta ilegible = NO COMPRAR")
ok(N.interpretar("")[0] is None, "Claude: respuesta vacía no compra")

shutil.rmtree(N.AQUI, ignore_errors=True)
shutil.rmtree(base, ignore_errors=True)
print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
