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
    lista = []
    for i in range(total):
        o = {"t": t0 + i * 900, "dir": -1, "res": 1 if i < aciertos else 0}
        if q is not None:
            o["q"] = q
        lista.append(o)
    return lista


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

# 1) la ganancia antes que el acierto
r = N.resumen(ops(20))
ok(r["con_ganancias"] and abs(r["neto"] - round(20 * (0.98 / 0.544 - 1) - 5, 3)) < 1e-9 and r["precio"] == 0.544
   and r["equilibrio"] == round(0.544 / 0.98, 3) and r["precio_supuesto"] == 25,
   "ganancia: 20 de 25 al 0,544 medido va con ganancias (neto +11,03) y dice que el precio es supuesto")
r = N.resumen(ops(20, q=0.86))
ok(not r["con_ganancias"] and r["neto"] < 0 and r["precio"] == 0.86 and r["precio_supuesto"] == 0,
   "ganancia: 20 de 25 pagando 0,86 va con pérdidas aunque el acierto sea 80 %")
r = N.resumen([{"t": 1, "dir": 1, "res": 0.5, "q": 0.5}])
ok(abs(r["neto"] - (0.98 / 2 / 0.5 - 1)) < 1e-9, "ganancia: el empate devuelve la mitad (0,49 / q − 1)")
ok(N.resumen([])["con_ganancias"] is False, "ganancia: sin cerradas no hay ganancias")


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
barato = N.resumen(ops(20) + [abierta])
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
            "neto": 11.029, "precio": 0.544, "equilibrio": 0.555, "con_ganancias": True, "precio_supuesto": 25, "alto": alto}


ahora = time.time()
V = int(ahora // 900) * 900                     # la ventana de 15 min en curso: el candado mira la hora real
ct = N.Central(c, {}, lambda W, t: None, lambda: False)

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
ok(lineas() == [] and ident in ct.esperando, "rutina: queda esperando su decisión; nada anotado todavía (no se compra)")
ok(A.falta(15, V, -1, time.time(), r=DEC) is not None, "candado: sin decisión de la rutina, el operador no compra")
ct.revisar_rutina()
ok(not Falso.lecturas, "rutina: no lee GitHub antes de 10 s")

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
ct2 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo2")), {}, lambda W, t: None, lambda: False)
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
ct3 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo3")), {}, lambda W, t: None, lambda: False)
os.makedirs(os.path.join(BASE, "nodo3"))
ct3.recibir(punto(15, V, -1, est="E1"))
ct3.recibir(punto(5, V5, 1, est="E3"))
ct3.recibir(punto(15, V + 900, 1, alto=False, est="E4"))     # bajo: no se manda
ct3.despachar()
nuevos = Falso.disparos[antes:]
ok(len(nuevos) == 1 and len(json.loads(nuevos[0]["cuerpo"]["text"])["puntos"]) == 2 and len(ct3.esperando) == 2,
   "rutina: los grupos listos van juntos en un solo disparo; el punto bajo no se manda")

# 9) tope por hora: sin disparo y sin compra
ct4 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo4"), tope_disparos=1), {}, lambda W, t: None, lambda: False)
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
ct5 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo5")), {}, lambda W, t: None, lambda: False)
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
ct6 = N.Central(dict(c, carpeta=os.path.join(BASE, "nodo6")), {}, lambda W, t: None, lambda: False)
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
ct7 = N.Central(dict(c_api, carpeta=os.path.join(BASE, "nodo7")), {}, lambda W, t: None, lambda: False)
os.makedirs(os.path.join(BASE, "nodo7"))
antes = len(Falso.disparos)
ct7.recibir(punto(15, V, -1, est="E1"))
ct7.despachar()
ok(len(llamadas) == 1 and len(Falso.disparos) == antes, "API: sin «decisor» sigue el camino de antes y no dispara la rutina")

srv.shutdown()
shutil.rmtree(BASE, ignore_errors=True)
print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
