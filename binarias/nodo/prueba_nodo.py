# -*- coding: utf-8 -*-
"""Pruebas del nodo puente (17/11/2026): el teléfono es el central y trabaja solo; la caja es respaldo.
Sin red externa: Telegram y Claude se sustituyen por funciones falsas; la red entre equipos es real, en 127.0.0.1."""
import json
import os
import shutil
import socket
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nodo as N  # noqa: E402

FALLOS, CUENTA = [], [0]


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


BASE = tempfile.mkdtemp(prefix="nodo_prueba_")
N.AQUI = BASE            # el registro (nodo.log) de la prueba va a la carpeta temporal, nunca al del equipo
FIN = chr(13) + chr(10)


def equipo(rol, puerto, par_puerto, centro=None, quince=None):
    raiz = os.path.join(BASE, rol)
    cent = os.path.join(raiz, "centinela")
    car = os.path.join(raiz, "nodo")
    os.makedirs(os.path.join(cent, "datos"), exist_ok=True)
    os.makedirs(car, exist_ok=True)
    if centro is not None:
        N.escribir_json(os.path.join(cent, "datos", "centro.json"), {"ops": centro})
    if quince is not None:
        N.escribir_json(os.path.join(cent, "quince.json"), {"ops": quince})
    return {"rol": rol, "centinela": cent, "operador": os.path.join(raiz, "operador"), "umbral": 19,
            "preferido": "telefono", "par_ip": "127.0.0.1", "puerto": puerto, "par_puerto": par_puerto, "carpeta": car}


def lineas(c, n):
    try:
        return [json.loads(x) for x in open(N.en(c, n), encoding="utf-8")]
    except OSError:
        return []


enviados, consultas = [], []
N.telegram = lambda texto: enviados.append(texto) or True
N.decision_claude = lambda grupo: (consultas.append(grupo) or ("COMPRAR BAJA", "coinciden y van altos"))
N.ESPERA_JUNTAR = 0
N.SECRETO = os.path.join(BASE, "secreto")
open(N.SECRETO, "w").write("prueba-secreta")
T = 1794930000

# 1) resumen con sumas en bucle
r = N.resumen(ops(20) + [{"t": 1, "dir": 1, "res": 1}, {"t": 2, "dir": 1, "res": 1}])
ok(r["aciertos"] == 20 and r["racha"] == 2, "resumen: últimas 25 y racha")

# 2) señales: lo abierto al arrancar no se reenvía; señal nueva alta; no se repite; señal baja
tel = equipo("telefono", 18801, 18802, centro={"E2": ops(20, abierta=(T, -1))})
est_t = {}
ok(N.puntos_nuevos(tel, est_t) == [], "primera vuelta: lo abierto al arrancar no se reenvía")
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E2": ops(20, abierta=(T + 900, -1))}})
nuevos = N.puntos_nuevos(tel, est_t)
ok(len(nuevos) == 1 and nuevos[0]["alto"], "señal nueva con 20 de 25: punto ALTO")
ok(N.puntos_nuevos(tel, est_t) == [], "la misma señal no se repite")
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E2": ops(16, abierta=(T + 1800, 1))}})
bajo = N.puntos_nuevos(tel, est_t)
ok(len(bajo) == 1 and not bajo[0]["alto"], "señal con 16 de 25: punto bajo")

# 3) EL TELÉFONO SOLO (la caja apagada): sube él mismo, sin depender de nadie
ct = N.Central(tel, est_t)
ok(ct.principal() and ct.activo(), "el teléfono es el nodo central")
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E1": ops(21, abierta=(T + 2700, -1))}})
N.vuelta(tel, est_t, ct)
ct.despachar()
ok(len(enviados) == 1 and "el teléfono (nodo central)" in enviados[0] and "COMPRAR BAJA" in enviados[0],
   "caja apagada: el teléfono sube solo a Telegram y a Claude")
ok(len(lineas(tel, "decisiones.jsonl")) == 1, "la decisión queda en el teléfono")
# un grupo sin puntos altos no se sube
ct.recibir(dict(bajo[0], t=T + 3000))
ct.despachar()
ok(len(enviados) == 1, "grupo sin puntos altos: no se sube")

# 4) LOS DOS ENCENDIDOS: el teléfono late, la caja aprende su IP y le entrega sus puntos; sube el teléfono
caja = equipo("caja", 18802, 18801, quince=ops(19, abierta=(T + 5400, -1)))
est_c = {}
cc = N.Central(caja, est_c)
ok(not cc.principal() and cc.activo(), "la caja sin latido del teléfono hace de central (respaldo)")
srv_t, srv_c = N.servidor(ct), N.servidor(cc)
time.sleep(0.3)
ok(N.enviar_par(tel, "127.0.0.1", "/latido", {"rol": "telefono"}), "latido del teléfono a la caja")
ok(not cc.activo() and cc.par["ip"] == "127.0.0.1", "con latido, la caja deja de ser central y conoce la IP del teléfono")
N.puntos_nuevos(caja, est_c)                  # primera vuelta de la caja
N.escribir_json(os.path.join(caja["centinela"], "quince.json"), {"ops": ops(19, abierta=(T + 6300, -1))})
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E1": ops(21, abierta=(T + 6300, -1))}})
antes = len(enviados)
N.vuelta(caja, est_c, cc)                     # la caja entrega al teléfono
N.vuelta(tel, est_t, ct)                      # el teléfono suma lo suyo
time.sleep(0.2)
cc.despachar()
ct.despachar()
ok(len(enviados) == antes + 1 and "Coinciden 2" in enviados[-1] and "caja" in enviados[-1] and "telefono" in enviados[-1],
   "los dos encendidos: un solo mensaje con los dos equipos, subido por el teléfono")
time.sleep(0.2)
ok(any(d.get("copia_de") for d in lineas(caja, "decisiones.jsonl")), "la decisión se copia a la caja (allí vive el operador)")

# 5) EL TELÉFONO CAÍDO: la caja no lo encuentra y sube lo suyo
srv_t.shutdown()
srv_t.server_close()
N.escribir_json(os.path.join(caja["centinela"], "quince.json"), {"ops": ops(20, abierta=(T + 8100, 1))})
antes = len(enviados)
N.vuelta(caja, est_c, cc)
cc.despachar()
ok(len(enviados) == antes + 1 and "la caja (respaldo" in enviados[-1], "teléfono caído: la caja sube lo suyo")

# 6) firma falsa: rechazada (403) y nada guardado
cuerpo = json.dumps([dict(nuevos[0], clave="falsa", t=T + 9000)]).encode()
pet = (f"POST /puntos HTTP/1.0{FIN}Host: x{FIN}X-Firma: {'0' * 64}{FIN}Content-Length: {len(cuerpo)}{FIN}{FIN}").encode() + cuerpo
with socket.create_connection(("127.0.0.1", 18802), timeout=4) as k:
    k.sendall(pet)
    resp = k.recv(200)
ok(b" 403" in resp and all(p["clave"] != "falsa" for g in cc.grupos.values() for p in g["puntos"]),
   "firma falsa: rechazada (403) y no se guarda")
srv_c.shutdown()
srv_c.server_close()

# 7) el operador de Fable: llenado + resultado del registro como su serie de aciertos
reg = os.path.join(BASE, "telefono", "operador", "registro")
os.makedirs(reg, exist_ok=True)
with open(os.path.join(reg, "20261117.jsonl"), "w", encoding="utf-8") as f:
    for i in range(25):
        t = 1794900000 + i * 900
        f.write(json.dumps({"tipo": "llenado", "t": t, "lado": -1, "llenado": "0.5", "sombra": False}) + "\n")
        f.write(json.dumps({"tipo": "resultado", "t": t, "ganador": -1 if i < 20 else 1}) + "\n")
    f.write(json.dumps({"tipo": "llenado", "t": T + 9000, "lado": 1, "sombra": False}) + "\n")
    f.write(json.dumps({"tipo": "llenado", "t": T + 9000, "lado": -1, "sombra": True}) + "\n")
fu = [x for x in N.leer_fuentes(tel) if x[0] == "operador"]
ok(len(fu) == 1 and fu[0][2]["aciertos"] == 20 and fu[0][2]["abierta"]["dir"] == 1,
   "operador de Fable: 20 de 25 desde su registro; la compra de sombra no cuenta")

# 8) Claude falla cerrado
ok(N.interpretar("COMPRAR SUBE\nporque sí")[0] == "COMPRAR SUBE", "Claude: COMPRAR SUBE se lee")
ok(N.interpretar("tal vez compre")[0] == "NO COMPRAR", "Claude: respuesta ilegible = NO COMPRAR")
ok(N.interpretar("")[0] is None, "Claude: respuesta vacía no compra")

shutil.rmtree(BASE, ignore_errors=True)
print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
