# -*- coding: utf-8 -*-
"""Pruebas del nodo puente (17/11/2026): el teléfono es el central y trabaja solo; la caja es respaldo; Claude decide y el
operador solo compra con su aprobación. Sin red externa: Telegram se sustituye por una función falsa; Claude, por una función
falsa o por un servidor falso de la API de mensajes en 127.0.0.1 al que se llega con curl de verdad; la red entre equipos es
real, en 127.0.0.1. Uso: python3 -I prueba_nodo.py"""
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nodo as N  # noqa: E402

FALLOS, CUENTA = [], [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


def ops(aciertos, total=25, abierta=None, t0=1794900000):
    lista = [{"t": t0 + i * 900, "dir": -1, "res": 1 if i < aciertos else 0} for i in range(total)]
    if abierta:
        lista.append({"t": abierta[0], "dir": abierta[1], "base": 65000.0, "res": None})
    return lista


def ops_dinero(aciertos=80, total=100, abierta=None, t0=1794900000):
    """Plan v9: una fuente que de verdad gana dinero (a 0,50, 80 de 100 dejan +0,57 por USDT), con los aciertos repartidos
    para que sus últimas 25 tampoco pierdan."""
    lista = [{"t": t0 + i * 900, "dir": -1, "res": 1 if (i * aciertos) % total < aciertos else 0} for i in range(total)]
    if abierta:
        lista.append({"t": abierta[0], "dir": abierta[1], "base": 65000.0, "res": None})
    return lista


# Ventanas propias de cada estrategia de la prueba, para que sus mercados no se pisen (un mercado tiene un solo ganador)
T_E2, T_E4, T_E1, T_Q = 1794900000, 1794000000, 1794600000, 1794300000


def con_libro(c, lista, q=0.5):
    """Lo que el operador habría anotado (18/11/2026, cuenta a mano): por cada señal cerrada, la mirada con libro real del
    minuto de entrada (el de la señal más uno) y el ganador oficial de su mercado de 15 min."""
    reg = os.path.join(c["operador"], "registro")
    os.makedirs(reg, exist_ok=True)
    with open(os.path.join(reg, "20261101.jsonl"), "a", encoding="utf-8") as f:
        for o in lista:
            if o.get("res") not in (0, 1, 0.5):
                continue
            v = o["t"] - o["t"] % 900
            m = (o["t"] - v) // 60 + 1
            g = o["dir"] if o["res"] == 1 else (0 if o["res"] == 0.5 else -o["dir"])
            f.write(json.dumps({"W": 15, "tipo": "mirada", "serie": "papel", "t": v, "m": m, "hora": v + 60 * m, "decide": 0,
                                "lados": {"1": {"q": q}, "-1": {"q": q}}}) + "\n")
            f.write(json.dumps({"W": 15, "tipo": "resultado", "serie": "papel", "t": v, "ganador": g, "fuente": "oficial"}) + "\n")


VEC = {"W": 15, "tipo": "mirada", "serie": "papel", "m": 1, "hora": 0, "decide": 0,
       "lados": {"1": {"papel": "perdedor", "p": 0.4, "p_prud": 0.38, "q": 0.40, "limite": 0.3},
                 "-1": {"papel": "ganador", "p": 0.6, "p_prud": 0.58, "q": 0.62, "limite": 0.5}}}


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
            "preferido": "telefono", "par_ip": "127.0.0.1", "puerto": puerto, "par_puerto": par_puerto, "carpeta": car,
            "rutas_claude": [("directa", ["--noproxy", "*"])], "esfuerzo": "low"}


def lineas(c, n):
    try:
        return [json.loads(x) for x in open(N.en(c, n), encoding="utf-8")]
    except OSError:
        return []


enviados, consultas = [], []
RESPUESTA = {"decision": "COMPRAR BAJA", "motivo": "coinciden y van altos"}


def claude_falso(paq, c=None):
    consultas.append(paq)
    return dict({"motivo": "", "uso": {"input_tokens": 400, "cache_read_input_tokens": 2600, "output_tokens": 150},
                 "costo_usd": 0.0052, "segundos": 4.0, "ruta": "directa", "error": None}, **RESPUESTA)


N.telegram = lambda texto: enviados.append(texto) or True
claude_verdadero = N.decision_claude
N.decision_claude = claude_falso
N.ESPERA_JUNTAR = 0
N.AVISOS_DINERO = False         # los avisos de dinero del plan v9 se prueban en prueba_ganancia.py
N.Libreta.REVISAR = 100000      # las libretas de la prueba llegan de golpe (en el equipo llegan de a una)
N.SECRETO = os.path.join(BASE, "secreto")
open(N.SECRETO, "w").write("prueba-secreta")
T = 1794930300   # múltiplo de 900
V = int(time.time() // 900) * 900   # la ventana de 15 min en curso: el candado del operador mira la hora real

# 1) resumen con sumas en bucle; el empate del vigía (0,5) cuenta como cerrada y como fallo (medida propia)
r = N.resumen(ops(20) + [{"t": 1, "dir": 1, "res": 1}, {"t": 2, "dir": 1, "res": 1}])
ok(r["aciertos_propios"] == 20 and r["racha"] == 2, "resumen: últimas 25 y racha")
r = N.resumen(ops(20) + [{"t": 3, "dir": 1, "res": 0.5}])
ok(r["abierta"] is None and r["racha"] == 0 and r["de_propios"] == 25 and r["aciertos_propios"] == 19,
   "resumen: un empate (0,5) es cerrada y fallo, no una señal abierta")

# 2) mercado de cada señal
ok(N.mercado_de("centro", {"t": T}) == (15, T, 0, True), "mercado: señal del Centro en la apertura: ventana de 15 alineada")
ok(N.mercado_de("centro", {"t": T + 300}) == (15, T, 5, False), "mercado: señal a los 5 min: la ventana de 15 en curso, no alineada")
ok(N.mercado_de("operador", {"t": T + 300, "m": 2}, 5) == (5, T + 300, 2, True), "mercado: el operador trae su mercado de 5 min")

# 3) señales: lo abierto al arrancar no se reenvía; señal nueva alta; no se repite; señal baja
tel = equipo("telefono", 18801, 18802, centro={"E2": ops(20, abierta=(T, -1))})
con_libro(tel, ops(20, t0=T_E2))
ft = N.Fuentes(tel)
est_t = {}
ok(N.puntos_nuevos(tel, est_t, ft) == [], "primera vuelta: lo abierto al arrancar no se reenvía")
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E2": ops(20, abierta=(T + 900, -1))}})
nuevos = N.puntos_nuevos(tel, est_t, ft)
ok(len(nuevos) == 1 and not nuevos[0]["alto"] and nuevos[0]["W"] == 15 and nuevos[0]["ventana"] == T + 900
   and nuevos[0]["cuenta"] == "a mano" and nuevos[0]["aciertos"] == 20 and nuevos[0]["de"] == 25
   and nuevos[0]["dinero"]["estado"] == N.POCA and nuevos[0]["dinero"]["n"] == 25,
   "plan v9: 20 de 25 a mano (precio real y ganador oficial) ya NO es punto alto: 25 apuestas no demuestran dinero")
ok(N.puntos_nuevos(tel, est_t, ft) == [], "la misma señal no se repite")
con_libro(tel, ops(16, t0=T_E4))
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E4": ops(16, abierta=(T + 1800, 1), t0=T_E4)}})
bajo = N.puntos_nuevos(tel, est_t, ft)
ok(len(bajo) == 1 and not bajo[0]["alto"], "señal con 16 de 25: punto bajo")
ft.leer()
ok(ft.leidos == 0, "sin cambios en los archivos: la vuelta no lee nada (0 bytes)")
sin_libro = equipo("solo", 18899, 18898, centro={"E2": ops(20, abierta=(T, -1))})
fs, est_s = N.Fuentes(sin_libro), {}
N.puntos_nuevos(sin_libro, est_s, fs)
N.escribir_json(os.path.join(sin_libro["centinela"], "datos", "centro.json"), {"ops": {"E2": ops(20, abierta=(T + 900, -1))}})
ps = N.puntos_nuevos(sin_libro, est_s, fs)
ok(len(ps) == 1 and not ps[0]["alto"] and ps[0]["de"] == 0 and ps[0]["aciertos_propios"] == 20,
   "paridad: 20 de 25 propios sin precio real del libro no son alto (nada de precio supuesto)")

# 4) EL TELÉFONO SOLO (la caja apagada): sube él mismo, sin depender de nadie
ct = N.Central(tel, est_t, lambda W, t: ft.vector(W, t) or VEC, ft.operador_vivo)
ok(ct.principal() and ct.activo(), "el teléfono es el nodo central")
con_libro(tel, ops_dinero(80, 100, t0=T_E1))
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E1": ops_dinero(80, 100, abierta=(T + 2700, -1), t0=T_E1)}})
N.vuelta(tel, est_t, ct, ft)
ct.despachar()
ok(len(enviados) == 1 and "el teléfono (nodo central)" in enviados[0] and "COMPRAR BAJA" in enviados[0],
   "caja apagada: el teléfono sube solo a Telegram y a Claude (E1 con ganancia de dinero demostrada)")
dec = lineas(tel, "decisiones.jsonl")
ok(len(dec) == 1 and dec[0]["W"] == 15 and dec[0]["ventana"] == T + 2700 and dec[0]["dir"] == -1 and dec[0]["decision"] == "COMPRAR BAJA",
   "la decisión queda en el teléfono con su mercado, ventana y sentido")
ok(dec[0].get("precios") == {"1": 0.40, "-1": 0.62} and "paga 1,58 por USDT" in enviados[0]
   and "100 apuestas a precio real" in enviados[0] and N.GANA in enviados[0] and "de 25" not in enviados[0],
   "paridad y plan v9: la decisión guarda los precios que vio la IA; el aviso dice lo que paga cada lado y el dinero, no aciertos")
ok(dec[0]["costo_usd"] == 0.0052 and dec[0]["uso"]["cache_read_input_tokens"] == 2600 and est_t["claude_hoy"]["consultas"] == 1,
   "la decisión guarda tokens y costo, y se suma al gasto del día")
ct.recibir(dict(bajo[0], clave="bajo-otro", t=T + 3600, ventana=T + 3600))
ct.despachar()
ok(len(enviados) == 1, "grupo sin puntos altos: no se sube")

# 5) LOS DOS ENCENDIDOS: el teléfono late, la caja aprende su IP y le entrega sus puntos; sube el teléfono
caja = equipo("caja", 18802, 18801, quince=ops_dinero(80, 100, abierta=(T + 5400, -1), t0=T_Q))
con_libro(caja, ops_dinero(80, 100, t0=T_Q))
fc = N.Fuentes(caja)
est_c = {}
cc = N.Central(caja, est_c, lambda W, t: fc.vector(W, t) or VEC, fc.operador_vivo)
ok(not cc.principal() and cc.activo(), "la caja sin latido del teléfono hace de central (respaldo)")
srv_t, srv_c = N.servidor(ct), N.servidor(cc)
time.sleep(0.3)
ok(N.enviar_par(tel, "127.0.0.1", "/latido", {"rol": "telefono"}), "latido del teléfono a la caja")
ok(not cc.activo() and cc.par["ip"] == "127.0.0.1", "con latido, la caja deja de ser central y conoce la IP del teléfono")
N.puntos_nuevos(caja, est_c, fc)                  # primera vuelta de la caja
N.escribir_json(os.path.join(caja["centinela"], "quince.json"), {"ops": ops_dinero(80, 100, abierta=(T + 6300, -1), t0=T_Q)})
N.escribir_json(os.path.join(tel["centinela"], "datos", "centro.json"), {"ops": {"E1": ops_dinero(80, 100, abierta=(T + 6300, -1), t0=T_E1)}})
antes = len(enviados)
N.vuelta(caja, est_c, cc, fc)                     # la caja entrega al teléfono
N.vuelta(tel, est_t, ct, ft)                      # el teléfono suma lo suyo
time.sleep(0.2)
cc.despachar()
ct.despachar()
ok(len(enviados) == antes + 1 and "Coinciden 2" in enviados[-1] and "caja" in enviados[-1] and "telefono" in enviados[-1],
   "los dos encendidos: un solo mensaje con los dos equipos, subido por el teléfono")
time.sleep(0.2)
ok(any(d.get("copia_de") for d in lineas(caja, "decisiones.jsonl")), "la decisión se copia a la caja")

# 6) un punto de un nodo viejo (sin mercado) se pone en su mercado al llegar
ct.recibir({"clave": "viejo|quince", "equipo": "caja", "fuente": "quince", "estrategia": "quince", "nombre": "vigía",
            "t": T + 7200, "dir": 1, "aciertos": 20, "de": 25, "racha": 1, "fondo": 55.0, "alto": True})
ok((15, T + 7200, 1) in ct.grupos, "punto de un nodo viejo: se pone en el mercado de 15 min de su ventana")

# 7) EL TELÉFONO CAÍDO: la caja no lo encuentra y sube lo suyo
srv_t.shutdown()
srv_t.server_close()
N.escribir_json(os.path.join(caja["centinela"], "quince.json"), {"ops": ops_dinero(80, 100, abierta=(T + 8100, 1), t0=T_Q)})
antes = len(enviados)
N.vuelta(caja, est_c, cc, fc)
cc.despachar()
ok(len(enviados) == antes + 1 and "la caja (respaldo" in enviados[-1], "teléfono caído: la caja sube lo suyo")

# 8) firma falsa: rechazada (403) y nada guardado
cuerpo = json.dumps([dict(nuevos[0], clave="falsa", t=T + 9000)]).encode()
pet = (f"POST /puntos HTTP/1.0{FIN}Host: x{FIN}X-Firma: {'0' * 64}{FIN}Content-Length: {len(cuerpo)}{FIN}{FIN}").encode() + cuerpo
with socket.create_connection(("127.0.0.1", 18802), timeout=4) as k:
    k.sendall(pet)
    resp = k.recv(200)
ok(b" 403" in resp and all(p["clave"] != "falsa" for g in cc.grupos.values() for p in g["puntos"]),
   "firma falsa: rechazada (403) y no se guarda")
srv_c.shutdown()
srv_c.server_close()

# 9) el operador de Fable: llenado + resultado del registro como su serie, por mercado; lectura incremental
reg = os.path.join(BASE, "telefono", "operador", "registro")
os.makedirs(reg, exist_ok=True)
dia = os.path.join(reg, "20261117.jsonl")
ahora = time.time()
with open(dia, "w", encoding="utf-8") as f:
    for i in range(25):
        t = 1794900000 + i * 900
        f.write(json.dumps({"W": 15, "tipo": "llenado", "t": t, "lado": -1, "llenado": 5, "compra": True, "sombra": False, "q": 0.4}) + "\n")
        f.write(json.dumps({"W": 15, "tipo": "llenado", "t": t, "lado": -1, "llenado": 15, "compra": True, "sombra": False}) + "\n")
        f.write(json.dumps({"W": 15, "tipo": "resultado", "serie": "papel", "t": t, "ganador": -1 if i < 20 else 1}) + "\n")
        f.write(json.dumps({"W": 5, "tipo": "resultado", "serie": "papel", "t": t, "ganador": 1}) + "\n")   # mismo t, otro mercado
    f.write(json.dumps({"W": 15, "tipo": "llenado", "t": V, "lado": 1, "llenado": 5, "compra": True, "sombra": False}) + "\n")
    f.write(json.dumps({"W": 15, "tipo": "llenado", "t": V, "lado": -1, "llenado": 5, "compra": True, "sombra": True}) + "\n")
    f.write(json.dumps({"W": 15, "tipo": "llenado", "t": V + 900, "lado": -1, "llenado": 5, "compra": False, "motivo": "se escapó"}) + "\n")
ft2 = N.Fuentes(tel)
fu = [x for x in ft2.leer() if x[0] == "operador"]
ok(len(fu) == 1 and fu[0][1] == "operador15" and fu[0][3]["aciertos"] == 20 and fu[0][3]["abierta"]["dir"] == 1,
   "operador: 20 de 25 en su mercado de 15 min; la sombra, la escapada y el resultado del de 5 min no cuentan")
leido = ft2.cola.leidos
with open(dia, "a", encoding="utf-8") as f:
    f.write(json.dumps({"W": 15, "tipo": "mirada", "serie": "papel", "t": V, "m": 3, "hora": ahora, "decide": 0,
                        "lados": {"1": {"papel": "perdedor", "p": 0.31, "p_prud": 0.29, "q": 0.33, "limite": 0.25},
                                  "-1": {"papel": "ganador", "p": 0.69, "p_prud": 0.66, "q": 0.69, "limite": 0.58}}}) + "\n")
    f.write('{"W": 15, "tipo": "mirada", "t": ')      # línea a medio escribir
ft2.leer()
ok(ft2.cola.leidos - leido < 1000 and ft2.vector(15, V)["m"] == 3, "registro: solo lee lo nuevo y espera la línea incompleta")
ok(ft2.operador_vivo(), "operador vivo: anotó una mirada hace menos de 5 min")

# 10) grupos por mercado, puntos en contra y vector del operador en el paquete; espera la mirada del operador
consultas.clear()
est3 = {}
c3 = N.Central(tel, est3, lambda W, t: ft2.vector(W, t) or (VEC if t < V else None), ft2.operador_vivo)
p15 = {"clave": "a", "equipo": "telefono", "fuente": "centro", "estrategia": "E1", "nombre": N.NOMBRES["E1"], "t": V,
       "dir": 1, "W": 15, "ventana": V, "minuto": 0, "alineado": True, "aciertos": 20, "de": 25, "racha": 2,
       "fondo": 55.0, "vivo": [69, 121], "alto": True, "cuenta": "a mano", "aciertos_propios": 20, "de_propios": 25,
       "dinero": {"estado": N.GANA, "alto": True, "pausa": False, "n": 300, "neto": 60.0, "por_usdt": 0.2, "prueba": 5000.0,
                  "umbral_prueba": 160.0}}
c3.recibir(p15)
c3.recibir(dict(p15, clave="b", W=5, ventana=V))
c3.recibir(dict(p15, clave="c", estrategia="E5", dir=-1, alto=False))
ok(len(c3.grupos) == 3, "grupos separados por mercado (15 y 5 min) y por sentido")
ok(c3._listo((15, V, 1), c3.grupos[(15, V, 1)], time.time()), "con la mirada del operador ya hecha, el grupo está listo")
RESPUESTA.update(decision="COMPRAR SUBE", motivo="E1 alta y el operador no se opone")
c3.despachar()
paq = next((q for q in consultas if q["W"] == 15), None)
ok(paq and paq["operador"]["minuto"] == 3 and paq["operador"]["lados"]["SUBE"]["p_prud"] == 0.29,
   "el paquete lleva el vector de ganancia del operador de ese mercado")
ok(paq and paq["operador"]["lados"]["SUBE"]["paga"] == 2.97 and paq["operador"]["lados"]["SUBE"]["compra_hasta"] == 0.35
   and paq["operador"]["lados"]["BAJA"]["equilibrio"] == round(0.69 / 0.98, 3),
   "paridad: el paquete dice lo que paga cada lado (0,98 / 0,33 = 2,97), su equilibrio y hasta cuánto se compra")
ok(c3.grupos[(5, V, 1)]["pendiente"] and not any(q["W"] == 5 for q in consultas),
   "paridad: con el operador vivo, el de 5 min sin mirada con libro espera su mirada (hasta 90 s)")
c3.grupos[(5, V, 1)]["desde"] -= N.ESPERA_OPERADOR + 1          # pasan los 90 s sin mirada con libro en el de 5 min
c3.despachar()
d5 = [d for d in lineas(tel, "decisiones.jsonl") if d["W"] == 5 and d["ventana"] == V]
ok(not any(q["W"] == 5 for q in consultas) and d5 and d5[-1]["error"] == "sin_precio",
   "paridad: a los 90 s sin libro, el de 5 min no se consulta a la IA («sin precio») y no se compra")
ok(paq and len(paq["en_contra"]) == 1 and paq["en_contra"][0]["estrategia"] == "E5", "el paquete lleva los puntos en contra de la misma ventana")
c3.grupos[(15, V + 900, 1)] = {"desde": time.time() - 30, "puntos": [dict(p15, clave="d", t=V + 900, ventana=V + 900)],
                                 "pendiente": True, "envios": 0}
ok(not c3._listo((15, V + 900, 1), c3.grupos[(15, V + 900, 1)], time.time()), "sin mirada del operador en esa ventana: espera")
ok(c3._listo((15, V + 900, 1), c3.grupos[(15, V + 900, 1)], time.time() + N.ESPERA_OPERADOR),
   "a los 90 s sin mirada del operador: sube igual")
# un punto alto nuevo después de subir: se vuelve a subir con la información nueva
n_antes = len(consultas)
c3.recibir(dict(p15, clave="e", estrategia="E2"))
c3.despachar()
ok(len(consultas) == n_antes + 1 and len(consultas[-1]["puntos"]) == 2, "punto alto nuevo en un grupo ya subido: se vuelve a consultar")

# 11) 18/11/2026: la IA ordena el lado contrario al punto: su orden queda tal cual (vender), sin cambiarla
RESPUESTA.update(decision="COMPRAR BAJA", motivo="al revés")
c3.recibir(dict(p15, clave="f", t=T + 10800, ventana=T + 10800))
c3.grupos[(15, T + 10800, 1)]["desde"] -= 200
c3.despachar()
ult = lineas(tel, "decisiones.jsonl")[-1]
ok(ult["ventana"] == T + 10800 and ult["decision"] == "COMPRAR BAJA" and ult["dir"] == 1 and "propuso" not in (ult["detalle"] or ""),
   "la IA ordena el lado contrario al punto: queda su orden (vender) tal cual")

# 12) del nodo al operador: la decisión del nodo es la que abre (o no) el candado del operador
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "operador"))
import aprobacion as A  # noqa: E402
A.RUTAS = (N.en(tel, "decisiones.jsonl"),)
v15 = V
_f = A.falta(15, v15, 1, time.time())
ok(_f is None, "el candado del operador acepta el COMPRAR SUBE del nodo para su mercado y sentido" + (f" (dice: {_f})" if _f else ""))
ok(A.falta(15, v15, -1, time.time()) is not None and A.falta(5, v15, 1, time.time()) is not None,
   "el candado no acepta el otro sentido ni el otro mercado")

# 13) Claude falla cerrado (lectura de la respuesta)
ok(N.interpretar("COMPRAR SUBE\nporque sí")[0] == "COMPRAR SUBE", "Claude: COMPRAR SUBE se lee")
ok(N.interpretar("**COMPRAR BAJA**\nmotivo")[0] == "COMPRAR BAJA", "Claude: con negritas también se lee")
ok(N.interpretar("tal vez compre")[0] == "NO COMPRAR", "Claude: respuesta ilegible = NO COMPRAR")
ok(N.interpretar("")[0] is None, "Claude: respuesta vacía no compra")
ok(N.leer_decision('{"decision": "COMPRAR SUBE", "motivo": "x"}') == ("COMPRAR SUBE", "x"), "Claude: el JSON del esquema se lee")
ok(N.leer_decision('{"decision": "COMPRAR TODO"}')[0] == "NO COMPRAR", "Claude: un JSON con otra decisión = NO COMPRAR")
ok(abs(N.costo({"input_tokens": 420, "cache_read_input_tokens": 2600, "output_tokens": 180}) - 0.0058) < 1e-9
   and abs(N.costo({"input_tokens": 400, "cache_creation_input_tokens": 3000, "output_tokens": 200}) - 0.0296) < 1e-9,
   "costo: 0,58 centavos con caché leída; 2,96 centavos escribiendo la caché de 1 h")


# 14) la llamada de verdad (curl) contra un servidor falso de la API de mensajes
class Falso(BaseHTTPRequestHandler):
    guion, pedidos = [], []

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        cuerpo = self.rfile.read(n)
        Falso.pedidos.append({"ruta": self.path, "cab": {k.lower(): v for k, v in self.headers.items()}, "cuerpo": json.loads(cuerpo)})
        codigo, datos, demora = Falso.guion.pop(0) if Falso.guion else (500, {"type": "error"}, 0)
        time.sleep(demora)
        crudo = datos if isinstance(datos, bytes) else json.dumps(datos).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(crudo)))
        self.end_headers()
        self.wfile.write(crudo)


def mensaje_api(texto, parada="end_turn", uso=None, extra=None):
    d = {"id": "msg_prueba", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
         "content": [{"type": "thinking", "thinking": "", "signature": "firma"}] + ([{"type": "text", "text": texto}] if texto else []),
         "stop_reason": parada, "stop_details": None,
         "usage": uso or {"input_tokens": 420, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 2600,
                          "output_tokens": 180, "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0}}}
    d.update(extra or {})
    return d


class Callado(ThreadingHTTPServer):
    def handle_error(self, *a):      # la prueba del plazo corta la conexión a propósito
        pass


srv = Callado(("127.0.0.1", 0), Falso)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/v1/messages"
cfg = {"rutas_claude": [("directa", ["--noproxy", "*"])], "api_url": url, "esfuerzo": "low"}
N.CLAUDE = os.path.join(BASE, "claude-clave")
paq0 = N.paquete((15, v15, 1), [p15], [], ft2.vector(15, v15))
r0 = claude_verdadero(paq0, cfg)
ok(r0["decision"] is None and r0["error"] == "sin_clave" and "pendiente" in r0["motivo"], "API: sin clave en el equipo: pendiente, no compra")
open(N.CLAUDE, "w").write("clave-falsa-de-prueba\n")
N.escribir_json(os.path.join(BASE, "CONTEXTO-NODO.md"), "contexto de prueba")
Falso.guion.append((200, mensaje_api('{"decision":"COMPRAR SUBE","motivo":"dos fuentes altas"}'), 0))
r1 = claude_verdadero(paq0, cfg)
pd = Falso.pedidos[-1]
cu = pd["cuerpo"]
ok(r1["decision"] == "COMPRAR SUBE" and r1["motivo"] == "dos fuentes altas" and r1["error"] is None, "API: respuesta JSON del esquema leída")
ok(pd["ruta"] == "/v1/messages" and pd["cab"].get("x-api-key") == "clave-falsa-de-prueba" and pd["cab"].get("anthropic-version") == "2026-10-21"
   and pd["cab"].get("content-type") == "application/json", "API: cabeceras x-api-key, anthropic-version 2026-10-21 y content-type")
ok(cu["model"] == "claude-opus-5-5" and cu["max_tokens"] == 2048 and "temperature" not in cu and "thinking" not in cu
   and cu["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
   and cu["output_config"]["effort"] == "low" and cu["output_config"]["format"]["type"] == "json_schema",
   "API: cuerpo con Opus 5.5, contexto en caché de 1 h, esfuerzo bajo y salida en JSON forzada")
ok(abs(r1["costo_usd"] - 0.0058) < 1e-9 and r1["uso"]["cache_read_input_tokens"] == 2600 and r1["ruta"] == "directa",
   "API: uso y costo anotados")
ok(not os.path.exists(os.path.join(BASE, "peticion_claude.json")), "API: el archivo de la petición se borra")
Falso.guion.append((200, mensaje_api("", parada="refusal", extra={"stop_details": {"type": "refusal", "category": "cyber"}}), 0))
ok(claude_verdadero(paq0, cfg)["decision"] == "NO COMPRAR", "API: si Claude declina responder, NO COMPRAR")
Falso.guion.append((200, mensaje_api("", parada="max_tokens"), 0))
ok(claude_verdadero(paq0, cfg)["decision"] == "NO COMPRAR", "API: respuesta cortada por max_tokens, NO COMPRAR")
Falso.guion.append((401, {"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}, 0))
r401 = claude_verdadero(paq0, cfg)
ok(r401["decision"] is None and r401["error"] == "autenticacion", "API: clave mala (401): sin decisión, no compra")
antes = len(enviados)
c3._alerta(r401)
c3._alerta(r401)
ok(len(enviados) == antes + 1 and "no está decidiendo" in enviados[-1], "API: la clave mala se avisa a Telegram una sola vez")
dormir = N.time.sleep
N.time.sleep = lambda s: None
Falso.guion += [(529, {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}, 0),
                (200, mensaje_api('{"decision":"NO COMPRAR","motivo":"contradicción"}'), 0)]
r529 = claude_verdadero(paq0, cfg)
ok(r529["decision"] == "NO COMPRAR" and r529["motivo"] == "contradicción", "API: Claude ocupado (529): un reintento y decide")
Falso.guion += [(529, {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}, 0)] * 2
ok(claude_verdadero(paq0, cfg)["error"] == "servidor", "API: ocupado dos veces seguidas: sin decisión, no compra")
N.time.sleep = dormir
Falso.guion.append((200, b"<html>Bad Gateway</html>", 0))
ok(claude_verdadero(paq0, cfg)["decision"] is None, "API: respuesta que no es JSON: sin decisión, no compra")
Falso.guion.append((200, mensaje_api("COMPRAR BAJA\nlo dijo en dos líneas"), 0))
ok(claude_verdadero(paq0, cfg)["decision"] == "COMPRAR BAJA", "API: si no viene en JSON, se lee el formato de dos líneas")
Falso.guion.append((200, mensaje_api('{"decision":"COMPRAR SUBE","motivo":"tarde"}'), 4))
rt = claude_verdadero(paq0, cfg, plazo=1)
ok(rt["decision"] is None and rt["error"] == "red", "API: sin respuesta a tiempo: sin decisión, no compra")
time.sleep(3.5)
Falso.guion.append((200, mensaje_api('{"decision":"COMPRAR SUBE","motivo":"por la segunda ruta"}'), 0))
cfg2 = dict(cfg, rutas_claude=[("rota", ["--noproxy", "", "--proxy", "http://127.0.0.1:9"]), ("directa", ["--noproxy", "*"])])
r2 = claude_verdadero(paq0, cfg2)
ok(r2["decision"] == "COMPRAR SUBE" and r2["ruta"] == "directa", "API: si la primera ruta no conecta, prueba la segunda")
cfg3 = dict(cfg, rutas_claude=[("rota", ["--noproxy", "", "--proxy", "http://127.0.0.1:9"])])
r3 = claude_verdadero(paq0, cfg3)
ok(r3["decision"] is None and r3["error"] == "red", "API: ninguna ruta conecta: sin decisión, no compra")
srv.shutdown()
srv.server_close()

# 15) papel de la combinación frente a cada fuente sola (medir_combinacion.py)
import medir_combinacion as MC  # noqa: E402
raiz = os.path.join(BASE, "medir")
for d in ("registro", "nodo", os.path.join("centinela", "datos")):
    os.makedirs(os.path.join(raiz, d), exist_ok=True)
t1, t2 = V - 7200, V - 5400
with open(os.path.join(raiz, "registro", "20261117.jsonl"), "w", encoding="utf-8") as f:
    for fila in ({"W": 15, "tipo": "mirada", "serie": "papel", "t": t1, "m": 1, "hora": t1 + 62, "decide": 0,
                  "lados": {"1": {"q": 0.50}, "-1": {"q": 0.52}}},
                 {"W": 15, "tipo": "mirada", "serie": "papel", "t": t1, "m": 3, "hora": t1 + 182, "decide": 1,
                  "lados": {"1": {"q": 0.45}, "-1": {"q": 0.57}}},
                 {"W": 15, "tipo": "llenado", "t": t1, "lado": 1, "llenado": 5, "compra": True, "sombra": False, "q": 0.45},
                 {"W": 15, "tipo": "resultado", "serie": "papel", "t": t1, "ganador": 1},
                 {"W": 15, "tipo": "mirada", "serie": "papel", "t": t2, "m": 2, "hora": t2 + 122, "decide": -1,
                  "lados": {"1": {"q": 0.70}, "-1": {"q": 0.30}}},
                 {"W": 15, "tipo": "resultado", "serie": "papel", "t": t2, "ganador": 1}):
        f.write(json.dumps(fila) + "\n")
N.escribir_json(os.path.join(raiz, "centinela", "datos", "centro.json"),
                {"ops": {"E1": [{"t": t1, "dir": 1, "res": 1}, {"t": t1 - 300, "dir": 1, "res": 1}, {"t": t2, "dir": -1, "res": 0, "semilla": True}]}})
with open(os.path.join(raiz, "nodo", "decisiones.jsonl"), "w", encoding="utf-8") as f:
    f.write(json.dumps({"t": t1 + 70, "W": 15, "ventana": t1, "dir": 1, "decision": "COMPRAR SUBE"}) + "\n")
    f.write(json.dumps({"t": t1 + 75, "W": 15, "ventana": t1, "dir": 1, "decision": "COMPRAR SUBE", "copia_de": "x"}) + "\n")
texto, cu, paradas = MC.medir(14, os.path.join(raiz, "nodo"), raiz, os.path.join(raiz, "centinela"), ahora=V)
cn = {x.nombre[:2]: x for x in cu}
ok(cn["A."].n == 1 and abs(cn["A."].neto - 0.96) < 1e-9, "medir: E1 sola, solo la señal viva alineada, al precio de la primera mirada")
b15 = [x for x in cu if x.nombre.startswith("B. operador de 15")][0]
ok(b15.n == 1 and abs(b15.neto - (0.98 / 0.45 - 1)) < 1e-9, "medir: el operador solo, a su precio de papel")
c_claude = [x for x in cu if x.nombre.startswith("C.")][0]
c_comb = [x for x in cu if x.nombre.startswith("D.")][0]
ok(c_claude.n == 1 and abs(c_claude.neto - (0.98 / 0.45 - 1)) < 1e-9, "medir: Claude solo, en la mirada siguiente a su decisión")
ok(c_comb.n == 1 and c_comb.k == 1 and paradas == 1, "medir: la combinación compra lo aprobado y cuenta lo que el candado paró")
ok(any("Equilibrio" in x for x in texto), "medir: el informe dice el equilibrio")

shutil.rmtree(BASE, ignore_errors=True)
print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
