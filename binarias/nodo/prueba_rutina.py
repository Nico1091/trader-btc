# -*- coding: utf-8 -*-
"""Pruebas del decisor «rutina» y de la ganancia antes que el acierto (17/11/2026). Sin red externa ni claves de verdad: la
rutina aprobadora (/fire) y GitHub (contents) son un servidor falso en 127.0.0.1; Telegram, una función falsa. El candado del
operador (operador/aprobacion.py) se usa tal cual para comprobar que la decisión de la rutina abre o cierra la compra.
Uso: python3 -I prueba_rutina.py"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import nodo as N  # noqa: E402

OPERADOR = next((d for d in (os.path.join(AQUI, "..", "operador"), os.path.join(os.path.expanduser("~"), "operador"))
                 if os.path.exists(os.path.join(d, "aprobacion.py"))), None)
if OPERADOR:
    sys.path.insert(0, OPERADOR)
import aprobacion as A  # noqa: E402

FALLOS, CUENTA = [], [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


def ops(aciertos, total=25, q=None, t0=1794900000):
    """Señales cerradas de BAJA; con q, compradas a ese precio real y con su ganador oficial (g), como las del operador."""
    lista = []
    for i in range(total):
        o = {"t": t0 + i * 900, "dir": -1, "res": 1 if i < aciertos else 0}
        if q is not None:
            o["q"] = q
            o["g"] = -1 if i < aciertos else 1
        lista.append(o)
    return lista


def vector(q_sube=0.40, q_baja=0.62, serie="papel", m=1):
    """Una mirada del operador con el libro real (o sin libro, con serie «sin_llave»)."""
    real = serie == "papel"
    return {"W": 15, "tipo": "mirada", "serie": serie, "m": m, "hora": time.time(), "resta_s": 800.0, "z": 0.1, "decide": 0,
            "lados": {"1": {"papel": "perdedor", "p": 0.4, "p_prud": 0.38, "q": q_sube if real else None, "G_prud": -0.1, "limite": 0.3},
                      "-1": {"papel": "ganador", "p": 0.6, "p_prud": 0.58, "q": q_baja if real else None, "G_prud": -0.1, "limite": 0.5}}}


VEC = vector()


BASE = tempfile.mkdtemp(prefix="rutina_prueba_")
N.AQUI = BASE                     # el registro del nodo va a la carpeta temporal
N.RUTINA_TOKEN = os.path.join(BASE, "token_rutina")
N.GITHUB_TOKEN = os.path.join(BASE, "token_github")
open(N.RUTINA_TOKEN, "w").write("token-rutina-falso\n")
open(N.GITHUB_TOKEN, "w").write("token-github-falso\n")
N.SECRETO = os.path.join(BASE, "secreto")
open(N.SECRETO, "w").write("prueba")
ENVIADOS = []
N.telegram = lambda texto: ENVIADOS.append(texto) or True
N.ESPERA_JUNTAR = 0

# 1) la ganancia antes que el acierto, contada como a mano (18/11/2026): precio real y ganador oficial, nunca un precio supuesto
r = N.resumen(ops(20, q=0.544))
ok(r["con_ganancias"] and abs(r["neto"] - round(20 * (0.98 / 0.544 - 1) - 5, 3)) < 1e-9 and r["precio"] == 0.544
   and r["equilibrio"] == round(0.544 / 0.98, 3) and r["precio_supuesto"] == 0 and r["cuenta"] == "a mano",
   "ganancia: 20 de 25 comprados a 0,544 de verdad van con ganancias (neto +11,03)")
r = N.resumen(ops(20))
ok(r["de"] == 0 and not r["con_ganancias"] and r["aciertos_propios"] == 20 and r["de_propios"] == 25 and r["precio"] is None,
   "ganancia: sin precio real no hay cuenta de dinero (nada de 0,544 supuesto); la medida propia queda aparte")
r = N.resumen(ops(20, q=0.86))
ok(not r["con_ganancias"] and r["neto"] < 0 and r["precio"] == 0.86 and r["precio_supuesto"] == 0,
   "ganancia: 20 de 25 pagando 0,86 va con pérdidas aunque el acierto sea 80 %")
r = N.cuenta([{"t": 1, "dir": 1, "g": 0, "q": 0.5}])
ok(abs(r["neto"] - (0.98 / 2 / 0.5 - 1)) < 1e-9, "ganancia: el empate devuelve la mitad (0,49 / q − 1)")
ok(N.cuenta([])["con_ganancias"] is False and N.cuenta([{"t": 1, "dir": 1, "g": 1}])["de"] == 0,
   "ganancia: sin cerradas, o sin precio real, no hay ganancias")
ok(N.cuenta([{"t": 1, "dir": 1, "g": 1, "q": 0.46}])["neto"] == round(0.98 / 0.46 - 1, 3) == 1.13,
   "ganancia: Up a 0,46 que acierta paga 2,13 por USDT, como el «Ganar» de la app (neto +1,13)")


class FuentesFalsas:
    def __init__(self, filas):
        self.filas = filas

    def leer(self):
        return self.filas


c0 = {"rol": "telefono", "umbral": 19}
est = {}
N.puntos_nuevos(c0, est, FuentesFalsas([]))          # primera vuelta: marca el arranque
abierta = {"t": 1794931200, "dir": -1, "base": 65000.0, "res": None}
caro = N.resumen(ops(20, q=0.86) + [abierta])
barato = N.resumen(ops(20, q=0.544) + [abierta])
pts = N.puntos_nuevos(c0, est, FuentesFalsas([("operador", "operador15", 15, caro), ("centro", "E1", 15, barato)]))
p_caro = next(p for p in pts if p["fuente"] == "operador")
p_barato = next(p for p in pts if p["fuente"] == "centro")
ok(not p_caro["alto"] and p_caro["con_ganancias"] is False, "punto: 80 % con pérdidas NO es alto (no se le manda a la rutina)")
ok(p_barato["alto"] and p_barato["neto"] > 0, "punto: 80 % con ganancias sí es alto")


# 2) servidor falso: rutina (/fire) y GitHub (contents)
class Falso(BaseHTTPRequestHandler):
    disparos, lecturas, decisiones = [], [], {}
    estado_fire = [200]

    def log_message(self, *a):
        pass

    def _resp(self, codigo, cuerpo):
        datos = json.dumps(cuerpo).encode() if not isinstance(cuerpo, bytes) else cuerpo
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        cuerpo = json.loads(self.rfile.read(n) or b"{}")
        Falso.disparos.append({"ruta": self.path, "cab": {k.lower(): v for k, v in self.headers.items()}, "cuerpo": cuerpo})
        if Falso.estado_fire[0] != 200:
            return self._resp(Falso.estado_fire[0], {"type": "error", "error": {"type": "authentication_error"}})
        self._resp(200, {"type": "routine_fire", "claude_code_session_id": "session_falsa",
                         "claude_code_session_url": "https://claude.ai/code/session_falsa"})

    def do_GET(self):
        Falso.lecturas.append({"ruta": self.path, "cab": {k.lower(): v for k, v in self.headers.items()}})
        nombre = self.path.split("/decisiones/", 1)[-1].split(".json", 1)[0]
        if "/decisiones/" in self.path and nombre in Falso.decisiones:
            d = Falso.decisiones[nombre]
            return self._resp(200, d if isinstance(d, bytes) else json.dumps(d).encode())
        self._resp(404, {"message": "Not Found"})


srv = ThreadingHTTPServer(("127.0.0.1", 18811), Falso)
threading.Thread(target=srv.serve_forever, daemon=True).start()

CARPETA = os.path.join(BASE, "nodo")
os.makedirs(CARPETA)
DEC = os.path.join(CARPETA, "decisiones.jsonl")
c = {"rol": "telefono", "preferido": "telefono", "par_ip": "127.0.0.1", "puerto": 18812, "par_puerto": 18813,
     "carpeta": CARPETA, "umbral": 19, "decisor": "rutina", "rutina_id": "trig_falsa",
     "rutina_url": "http://127.0.0.1:18811/v1/claude_code/routines/trig_falsa/fire", "github_api": "http://127.0.0.1:18811",
     "repo_decisiones": "Nico1091/binarias-aprobador", "tope_disparos": 25}


def lineas():
    try:
        return [json.loads(x) for x in open(DEC, encoding="utf-8")]
    except OSError:
        return []


def punto(W, ventana, d, alto=True, est="E1", t=None):
    return {"clave": f"telefono|centro|{est}|{ventana}|{d}|{W}", "equipo": "telefono", "fuente": "centro", "estrategia": est,
            "nombre": N.NOMBRES.get(est, est), "t": t or ventana, "dir": d, "base": 65000.0, "W": W, "ventana": ventana,
            "minuto": 0, "alineado": True, "aciertos": 20, "de": 25, "racha": 3, "fondo": 56.0, "vivo": [60, 100],
            "neto": 11.029, "precio": 0.544, "equilibrio": 0.555, "con_ganancias": True, "precio_supuesto": 0, "alto": alto,
            "cuenta": "a mano", "aciertos_propios": 20, "de_propios": 25}


def con_libro(W, t):
    return VEC


ahora = time.time()
V = int(ahora // 900) * 900                     # la ventana de 15 min en curso: el candado mira la hora real
ct = N.Central(c, {}, con_libro, lambda: False)

# 3) un punto alto: se dispara la rutina con su forma exacta y todavía no hay decisión
ct.recibir(punto(15, V, -1))
ct.despachar()
ok(len(Falso.disparos) == 1, "rutina: un punto alto dispara la rutina una vez")
f = Falso.disparos[-1]
ok(f["ruta"] == "/v1/claude_code/routines/trig_falsa/fire" and f["cab"].get("authorization") == "Bearer token-rutina-falso"
   and f["cab"].get("anthropic-beta") == "experimental-cc-routine-2026-04-01" and f["cab"].get("anthropic-version") == "2023-06-01",
   "rutina: POST a /fire con su token, la cabecera beta y la versión de la documentación")
carga = json.loads(f["cuerpo"]["text"])
ident = carga["puntos"][0]["id"]
pq = carga["puntos"][0]["paquete"]
ok(ident.startswith(f"telefono-15m-{V}-baja-1-") and len(ident) <= 80 and all(ch.isalnum() or ch in "-_" for ch in ident),
   "rutina: el id lleva equipo, mercado, ventana, sentido, envío y hora (único tras un reinicio; solo letras, números y guiones)")
ok(list(f["cuerpo"]) == ["text"] and carga["puntos"][0]["id"] == ident and pq["sentido"] == "BAJA" and pq["W"] == 15
   and pq["puntos"][0]["con_ganancias"] is True and pq["puntos"][0]["neto"] == 11.029,
   "rutina: el texto lleva {\"puntos\": [{id, paquete}]} como la espera la rutina, con el neto y si va con ganancias")
lb = pq["operador"]["lados"]["BAJA"]
ok(lb["q"] == 0.62 and lb["paga"] == round(0.98 / 0.62, 2) and lb["equilibrio"] == round(0.62 / 0.98, 3) and lb["compra_hasta"] == 0.64
   and pq["puntos"][0]["cuenta"] == "a mano",
   "paridad: la IA ve de cada lado el precio real, lo que paga por USDT, el equilibrio y hasta cuánto se compra")
ok(lineas() == [] and ident in ct.esperando, "rutina: queda esperando su decisión; nada anotado todavía (no se compra)")
ok(A.falta(15, V, -1, time.time(), r=DEC) is not None, "candado: sin decisión de la rutina, el operador no compra")
ct.revisar_rutina()
ok(not Falso.lecturas and N.MIRAR_DECISION == 3, "rutina: lee GitHub cada 3 s, no antes")

# 4) la rutina responde COMPRAR BAJA: se anota donde la lee el candado
N.MIRAR_DECISION = 0
Falso.decisiones[ident] = {"id": ident, "decision": "COMPRAR BAJA", "motivo": "E1 con ganancias y alineada", "t": int(time.time())}
ct.revisar_rutina()
lec = Falso.lecturas[-1] if Falso.lecturas else {"ruta": "", "cab": {}}
ok(lec["ruta"] == f"/repos/Nico1091/binarias-aprobador/contents/decisiones/{ident}.json?ref=main"
   and lec["cab"].get("authorization") == "Bearer token-github-falso" and "raw" in lec["cab"].get("accept", ""),
   "GitHub: lee decisiones/<id>.json de binarias-aprobador (main) con el acceso del equipo")
L = lineas()
ok(len(L) == 1 and L[0]["decision"] == "COMPRAR BAJA" and L[0]["W"] == 15 and L[0]["ventana"] == V and L[0]["dir"] == -1
   and L[0]["ruta"] == "rutina" and L[0]["id"] == ident and ident not in ct.esperando,
   "rutina: su COMPRAR BAJA queda en decisiones.jsonl con mercado, ventana, sentido e id")
ok(L[0].get("precios") == {"1": 0.40, "-1": 0.62} and L[0].get("precios_m") == 1 and L[0]["vence"] - L[0]["t"] <= 120,
   "paridad: la decisión guarda los precios que vio la IA y vale 2 min como mucho")
ok(A.falta(15, V, -1, time.time(), r=DEC) is None, "candado: con el COMPRAR BAJA de la rutina, el operador puede comprar BAJA")
ok(A.falta(15, V, 1, time.time(), r=DEC) is not None, "candado: no puede comprar SUBE con un COMPRAR BAJA")
ok(any("Decisión de Claude: COMPRAR BAJA" in m and "rutina aprobadora" in m and "con ganancias" in m for m in ENVIADOS),
   "Telegram: avisa la decisión, que la tomó la rutina y que el punto va con ganancias")

# 5) 18/11/2026: la rutina ordena el lado contrario al punto y sin motivo: su orden queda tal cual y abre ese lado
V5 = int(time.time() // 300) * 300
ct.recibir(punto(5, V5, 1, est="E3"))
ct.despachar()
ident2 = json.loads(Falso.disparos[-1]["cuerpo"]["text"])["puntos"][0]["id"]
Falso.decisiones[ident2] = {"id": ident2, "decision": "COMPRAR BAJA", "t": int(time.time())}
ct.revisar_rutina()
ok(lineas()[-1]["decision"] == "COMPRAR BAJA" and lineas()[-1]["id"] == ident2 and lineas()[-1]["dir"] == 1,
   "rutina: si ordena el lado contrario al punto (vender), queda su orden tal cual")
ok(A.orden(5, V5, time.time(), r=DEC)[0] == -1 and A.falta(5, V5, 1, time.time(), r=DEC) is not None,
   "candado: esa orden abre vender (BAJA) en el mercado de 5 min, no comprar (SUBE)")
ok(any("COMPRAR BAJA (vender)" in m for m in ENVIADOS), "Telegram: la orden sin motivo se avisa como «vender»")

# 6) decisión ilegible o de otro id: NO COMPRAR
ct.recibir(punto(15, V, 1, est="E2"))
ct.despachar()
ident3 = json.loads(Falso.disparos[-1]["cuerpo"]["text"])["puntos"][0]["id"]
Falso.decisiones[ident3] = b"esto no es json"
ct.revisar_rutina()
ok(lineas()[-1]["decision"] == "NO COMPRAR" and "ilegible" in lineas()[-1]["detalle"], "rutina: decisión ilegible = NO COMPRAR")

# 7) la rutina no responde: vence y no se compra
ct2 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo2")), {}, con_libro, lambda: False)
os.makedirs(os.path.join(BASE, "nodo2"))
DEC2 = os.path.join(BASE, "nodo2", "decisiones.jsonl")
ct2.recibir(punto(15, V, -1, est="E5"))
ct2.despachar()
espera_antes = N.ESPERA_RUTINA
N.ESPERA_RUTINA = 0
ct2.revisar_rutina()
N.ESPERA_RUTINA = espera_antes
L2 = [json.loads(x) for x in open(DEC2, encoding="utf-8")]
ok(len(L2) == 1 and L2[0]["decision"] is None and "no respondió" in L2[0]["detalle"] and L2[0]["error"] == "rutina_sin_respuesta",
   "rutina: sin respuesta en el plazo, queda sin decisión")
ok(A.falta(15, V, -1, time.time(), r=DEC2) is not None, "candado: sin respuesta de la rutina no hay compra")

# 8) un lote: dos grupos listos a la vez van en un solo disparo
antes = len(Falso.disparos)
ct3 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo3")), {}, con_libro, lambda: False)
os.makedirs(os.path.join(BASE, "nodo3"))
ct3.recibir(punto(15, V, -1, est="E1"))
ct3.recibir(punto(5, V5, 1, est="E3"))
ct3.recibir(punto(15, V + 900, 1, alto=False, est="E4"))     # bajo: no se manda
ct3.despachar()
nuevos = Falso.disparos[antes:]
ok(len(nuevos) == 1 and len(json.loads(nuevos[0]["cuerpo"]["text"])["puntos"]) == 2 and len(ct3.esperando) == 2,
   "rutina: los grupos listos van juntos en un solo disparo; el punto bajo no se manda")

# 9) tope por hora: sin disparo y sin compra
ct4 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo4"), tope_disparos=1), {}, con_libro, lambda: False)
os.makedirs(os.path.join(BASE, "nodo4"))
ct4.disparos = [time.time()]
antes = len(Falso.disparos)
ct4.recibir(punto(15, V, -1, est="E1"))
ct4.despachar()
L4 = [json.loads(x) for x in open(os.path.join(BASE, "nodo4", "decisiones.jsonl"), encoding="utf-8")]
ok(len(Falso.disparos) == antes and L4[0]["decision"] is None and L4[0]["error"] == "rutina_tope",
   "rutina: con el tope de la hora alcanzado no se dispara y no se compra")

# 10) sin token de la rutina: no dispara, avisa una vez y no se compra
os.remove(N.RUTINA_TOKEN)
ENVIADOS.clear()
ct5 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo5")), {}, con_libro, lambda: False)
os.makedirs(os.path.join(BASE, "nodo5"))
antes = len(Falso.disparos)
ct5.recibir(punto(15, V, -1, est="E2"))
ct5.despachar()
L5 = [json.loads(x) for x in open(os.path.join(BASE, "nodo5", "decisiones.jsonl"), encoding="utf-8")]
ok(len(Falso.disparos) == antes and L5[0]["decision"] is None and L5[0]["error"] == "sin_token_rutina"
   and any("Generate token" in m for m in ENVIADOS), "rutina: sin token no dispara, no compra y avisa cómo generarlo")
open(N.RUTINA_TOKEN, "w").write("token-rutina-falso\n")

# 11) token rechazado (401): error del token y aviso
Falso.estado_fire[0] = 401
ENVIADOS.clear()
ct6 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo6")), {}, con_libro, lambda: False)
os.makedirs(os.path.join(BASE, "nodo6"))
ct6.recibir(punto(15, V, -1, est="E3"))
ct6.despachar()
L6 = [json.loads(x) for x in open(os.path.join(BASE, "nodo6", "decisiones.jsonl"), encoding="utf-8")]
ok(L6[0]["decision"] is None and L6[0]["error"] == "rutina_token" and any("volver a generarlo" in m for m in ENVIADOS),
   "rutina: token rechazado (401) = sin decisión y aviso para regenerarlo")
Falso.estado_fire[0] = 200

# 12) el camino de la API sigue igual sin «decisor»
c_api = {k: v for k, v in c.items() if k != "decisor"}
llamadas = []
N.decision_claude = lambda paquete, cc=None, plazo=90: llamadas.append(paquete) or {"decision": "NO COMPRAR", "motivo": "x",
                                                                                     "ruta": "directa"}
ct7 = N.Central(dict(c_api, carpeta=os.path.join(BASE, "nodo7")), {}, con_libro, lambda: False)
os.makedirs(os.path.join(BASE, "nodo7"))
antes = len(Falso.disparos)
ct7.recibir(punto(15, V, -1, est="E1"))
ct7.despachar()
ok(len(llamadas) == 1 and len(Falso.disparos) == antes, "API: sin «decisor» sigue el camino de antes y no dispara la rutina")

# 13) 18/11/2026, paridad: sin precio real del libro no se consulta a la IA (ni se gasta una corrida de la rutina)
for nombre, vec in (("sin mirada del operador", lambda W, t: None), ("mirada sin libro", lambda W, t: vector(serie="sin_llave"))):
    carpeta = os.path.join(BASE, "nodo8-" + str(len(nombre)))
    os.makedirs(carpeta)
    ct8 = N.Central(dict(c, carpeta=carpeta), {}, vec, lambda: False)
    antes = len(Falso.disparos)
    ct8.recibir(punto(15, V, -1, est="E1"))
    ct8.despachar()
    L8 = [json.loads(x) for x in open(os.path.join(carpeta, "decisiones.jsonl"), encoding="utf-8")]
    ok(len(Falso.disparos) == antes and len(L8) == 1 and L8[0]["decision"] is None and L8[0]["error"] == "sin_precio"
       and L8[0]["precios"] is None and A.falta(15, V, -1, time.time(), r=os.path.join(carpeta, "decisiones.jsonl")) is not None,
       f"paridad: {nombre}: no se dispara la rutina, queda «sin precio» y el candado no deja comprar")

# 14) 18/11/2026: un punto alto de un nodo sin la cuenta a mano (la caja con el código de antes) no cuenta como alto
ct9 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo9")), {}, con_libro, lambda: False)
os.makedirs(os.path.join(BASE, "nodo9"))
viejo = {k: v for k, v in punto(15, V, -1, est="E2").items() if k != "cuenta"}
viejo["equipo"] = "caja"
antes = len(Falso.disparos)
ct9.recibir(viejo)
ct9.despachar()
ok(len(Falso.disparos) == antes and not any(p["alto"] for g in ct9.grupos.values() for p in g["puntos"]),
   "paridad: el punto alto de un nodo sin la cuenta a mano se muestra, pero no es alto ni dispara")

srv.shutdown()
shutil.rmtree(BASE, ignore_errors=True)
print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
