"""Binarias en papel, en tiempo real (29/10/2026). Solo biblioteca estándar. Pantalla: http://127.0.0.1:8792

Pedido de Nicolás: «operaciones binarias, no trading común»; «tú como agente debes operar primero y mostrarme cada
resultado»; «un programa que me muestre los operativos en tiempo real… para ver si es verdad que se reflejan las ganancias
en libro y reales»; «haz de cuenta de que las pruebas se ejecutan en tiempo real».

Qué hace (configuración de investigacion/total/t3_binarias_libro.py, en config.json):
- 2 s después de cada cierre de vela de 15 min de BTCUSDT (futuros de Binance), mira la vela recién cerrada: si su cuerpo es
  ≥ 2 veces la media de los 100 cuerpos anteriores, apuesta EN CONTRA de esa vela, solo si esa dirección va a favor del
  contexto diario (cierre de ayer sobre o bajo la SMA 50). Vence a los 10 min, el plazo más corto de los Contratos de Evento
  de Binance (pruebas/t5 y t6: 55-56 % de acierto en 2024-2026 apostando en los primeros 30 s).
- SOMBRA (sin dinero): «tres cuervos al revés» de su curso en velas de 5 min, apostando a que sube; se mide a 5 y 10 min.
- Preventivas de la sesión del 28/10: para el día tras 4 pérdidas seguidas o −6 % del saldo del día; cada 100 apuestas, si
  el acierto de las últimas 100 no alcanza lo necesario para el pago, la estrategia se apaga sola y avisa.
- REAL: entra al precio vivo del momento en que apuesta y cobra con el precio vivo al vencer (empate = se devuelve).
- LIBRO: la misma apuesta medida como en las pruebas: del cierre de la vela al cierre 15 min después.
- Cada libro es una cuenta de 150.000 COP que apuesta el mismo % de su saldo, con el mismo pago.
- Cada resultado va a su Telegram como texto. Página /replay: las apuestas del último trimestre de la prueba, como si fueran
  en vivo, con reloj acelerado.
Uso: pythonw binarias.py (sin ventana) · python binarias.py --una-vez (prueba)   Parar: crear el archivo PARAR."""
import datetime as dt
import html
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
CONFIG, ESTADO = os.path.join(AQUI, "config.json"), os.path.join(AQUI, "estado.json")
APUESTAS, REGISTRO, PARAR = os.path.join(AQUI, "apuestas.jsonl"), os.path.join(AQUI, "binarias.log"), os.path.join(AQUI, "PARAR")
REPLAY, CUADRO = os.path.join(AQUI, "replay_10min.json"), os.path.join(AQUI, "cuadro_10min.json")
TG = os.path.join(os.path.dirname(AQUI), "tg_pc.py")
PUERTO = 8792
FAPI = "https://fapi.binance.com/fapi/v1/"
H = {"User-Agent": "binarias-papel"}
COL = dt.timezone(dt.timedelta(hours=-5))
CANDADO = threading.Lock()
DEF = {"simbolo": "BTCUSDT", "vela_min": 15, "vence_min": 10, "apuesta": 0.02, "pago": 0.85, "capital_cop": 150000,
       "activo": True, "avisos": True, "preventiva": "CTX", "reiniciar_t": 0, "max_seguidas": 4, "tope_dia": 0.06,
       "revision": 100, "sombra": True}


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def leer(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defecto


def escribir(ruta, datos):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def red(ruta):
    return json.loads(urllib.request.urlopen(urllib.request.Request(FAPI + ruta, headers=H), timeout=15).read())


def precio(sim):
    return float(red(f"ticker/price?symbol={sim}")["price"])


def cop(x, signo=False):
    t = f"{x:+,.0f}" if signo else f"{x:,.0f}"
    return "0" if abs(x) < 0.5 else t.replace(",", ".")


def avisar(texto):
    if not os.path.exists(TG):
        return
    ruta = os.path.join(AQUI, "alertas", f"{int(time.time() * 1000)}.txt")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("[Claude Code · binarias en papel]\n" + texto)
    py = os.path.join(os.path.dirname(sys.executable), "python.exe")

    def enviar():
        try:
            r = subprocess.run([py, "-I", TG, ruta], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if "ok" in (r.stdout or ""):
                os.remove(ruta)
            else:
                log("aviso a Telegram sin confirmar: " + (r.stdout or r.stderr).strip()[-120:])
        except Exception as e:
            log(f"aviso a Telegram falló ({type(e).__name__})")

    threading.Thread(target=enviar, daemon=True).start()


# ---------------------------------------------------------------- motor
def estado_inicial(cfg):
    return {"inicio": int(time.time()), "real": float(cfg["capital_cop"]), "libro": float(cfg["capital_cop"]),
            "pendientes": [], "hechas": [], "sombras": [], "sombras_hechas": [], "ultima_vela": 0, "ultimo_motivo": "",
            "contexto": 0, "dia": "", "inicio_dia": float(cfg["capital_cop"]), "seguidas": 0, "parada_dia": None,
            "apagada": None}


def contexto_diario(sim):
    """+1 / −1: cierre de ayer sobre o bajo la media de los 50 cierres diarios hasta ayer (igual que en T3)."""
    ahora = time.time() * 1000
    d = [x for x in red(f"klines?symbol={sim}&interval=1d&limit=60") if x[6] < ahora]
    c = [float(x[4]) for x in d]
    sma = sum(c[-50:]) / 50
    return 1 if c[-1] > sma else -1 if c[-1] < sma else 0


def velas_cerradas(sim, tf, n):
    ahora_ms = time.time() * 1000
    return [x for x in red(f"klines?symbol={sim}&interval={tf}m&limit={n + 2}") if x[6] < ahora_ms]


def revisar_rev15(cfg, est):
    """Al cierre de una vela de 15 min: ¿hay señal REV15 CTX? Devuelve la apuesta abierta o None, y deja escrito el motivo."""
    sim = cfg["simbolo"]
    v = velas_cerradas(sim, 15, 101)
    if len(v) < 101:
        est["ultimo_motivo"] = "faltan velas para medir"
        return None
    ult, previas = v[-1], v[-101:-1]
    o, c = float(ult[1]), float(ult[4])
    cuerpo = abs(c - o)
    media = sum(abs(float(x[4]) - float(x[1])) for x in previas) / 100
    t_cierre = (int(ult[6]) + 1) // 1000
    est["ultima_vela"] = t_cierre
    h = dt.datetime.fromtimestamp(t_cierre, COL).strftime("%H:%M")
    if cuerpo < 2 * media:
        est["ultimo_motivo"] = f"vela de las {h}: cuerpo {cuerpo / media:.1f} veces la media (hace falta 2): no apuesta"
        return None
    d = -1 if c > o else 1
    est["contexto"] = ctx = contexto_diario(sim)
    if cfg["preventiva"] == "CTX" and d != ctx:
        est["ultimo_motivo"] = (f"vela de las {h} fuerte ({cuerpo / media:.1f} veces la media), pero apostar "
                                f"{'arriba' if d > 0 else 'abajo'} va contra el contexto del día: no apuesta")
        return None
    if est.get("parada_dia"):
        est["ultimo_motivo"] = f"vela de las {h} con señal, pero el día está parado por la preventiva: no apuesta"
        return None
    if est.get("apagada"):
        est["ultimo_motivo"] = f"vela de las {h} con señal, pero la estrategia está apagada por bajo acierto: no apuesta"
        return None
    if any(a.get("tipo") == "principal" for a in est["pendientes"]):
        est["ultimo_motivo"] = f"vela de las {h} con señal, pero ya hay una apuesta abierta (una a la vez)"
        return None
    pe = precio(sim)
    ahora = time.time()
    a = {"id": f"{t_cierre}", "tipo": "principal", "estrategia": "REV15 CTX", "sim": sim, "d": d, "t_cierre": t_cierre,
         "pe_libro": c, "t_real": ahora, "pe_real": pe, "plazo": cfg["vence_min"], "vence_real": ahora + cfg["vence_min"] * 60,
         "vence_libro": t_cierre + cfg["vence_min"] * 60, "monto_real": round(cfg["apuesta"] * est["real"]),
         "monto_libro": round(cfg["apuesta"] * est["libro"]), "pago": cfg["pago"], "fuerza": round(cuerpo / media, 2),
         "res_real": None, "res_libro": None}
    est["ultimo_motivo"] = f"vela de las {h} fuerte ({a['fuerza']} veces la media): apuesta {'ARRIBA' if d > 0 else 'ABAJO'}"
    return a


def revisar_c3r(cfg, est):
    """SOMBRA: «tres cuervos al revés» en velas de 5 min (definición de patrones_std). Sin dinero: solo se mide."""
    v = velas_cerradas(cfg["simbolo"], 5, 14)
    if len(v) < 14:
        return None
    O, C, H, L = ([float(x[k]) for x in v] for k in (1, 4, 2, 3))
    fb = [C[i] < O[i] and abs(C[i] - O[i]) >= 0.5 * (H[i] - L[i]) for i in range(len(C))]
    t3 = (C[-4] - C[-14]) / C[-14]
    if not (t3 > 0 and fb[-1] and fb[-2] and fb[-3] and C[-1] < C[-2] < C[-3]):
        return None
    t_cierre = (int(v[-1][6]) + 1) // 1000
    ahora = time.time()
    pe = precio(cfg["simbolo"])
    return {"id": f"s{t_cierre}", "tipo": "sombra", "estrategia": "tres cuervos al revés", "sim": cfg["simbolo"], "d": 1,
            "t_cierre": t_cierre, "pe_libro": C[-1], "t_real": ahora, "pe_real": pe, "plazos": [5, 10],
            "res": {}, "px": {}}


def resolver(cfg, est):
    """Cobra lo que venció. Real: precio vivo al vencer. Libro: cierre del minuto en que vence, contado desde el cierre de la vela."""
    ahora = time.time()
    for a in est["pendientes"]:
        if a["res_real"] is None and ahora >= a["vence_real"]:
            px = precio(a["sim"])
            a["px_real"], a["res_real"] = px, ((px > a["pe_real"]) - (px < a["pe_real"])) * a["d"]
            a["g_real"] = a["monto_real"] * a["pago"] if a["res_real"] > 0 else -a["monto_real"] if a["res_real"] < 0 else 0
            est["real"] += a["g_real"]
            if a["res_real"] < 0:
                est["seguidas"] += 1
            elif a["res_real"] > 0:
                est["seguidas"] = 0
        if a["res_libro"] is None and ahora >= a["vence_libro"] + 2:
            m = red(f"klines?symbol={a['sim']}&interval=1m&startTime={(a['vence_libro'] - 60) * 1000}&limit=1")
            if m and int(m[0][0]) // 1000 == a["vence_libro"] - 60 and m[0][6] < ahora * 1000:
                px = float(m[0][4])
                a["px_libro"], a["res_libro"] = px, ((px > a["pe_libro"]) - (px < a["pe_libro"])) * a["d"]
                a["g_libro"] = a["monto_libro"] * a["pago"] if a["res_libro"] > 0 else -a["monto_libro"] if a["res_libro"] < 0 else 0
                est["libro"] += a["g_libro"]
    for s in est["sombras"]:
        for pl in s["plazos"]:
            k = str(pl)
            if k not in s["res"] and ahora >= s["t_real"] + pl * 60:
                px = precio(s["sim"])
                s["px"][k], s["res"][k] = px, ((px > s["pe_real"]) - (px < s["pe_real"])) * s["d"]
    for s in [x for x in est["sombras"] if len(x["res"]) == len(x["plazos"])]:
        est["sombras"].remove(s)
        est["sombras_hechas"].append(s)
    est["sombras_hechas"] = est["sombras_hechas"][-500:]
    nom = lambda r: "GANÓ" if r > 0 else "PERDIÓ" if r < 0 else "EMPATE (se devuelve)"  # noqa: E731
    for a in [x for x in est["pendientes"] if x["res_real"] is not None and x["res_libro"] is not None]:
        est["pendientes"].remove(a)
        est["hechas"].append(a)
        with open(APUESTAS, "a", encoding="utf-8") as f:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
        avisos = []
        if cfg["avisos"]:
            avisos.append(f"RESULTADO · BTC {'▲ ARRIBA' if a['d'] > 0 else '▼ ABAJO'}, {a['plazo']} min, {cop(a['monto_real'])} COP\n"
                          f"REAL: {a['pe_real']:,.1f} → {a['px_real']:,.1f}: {nom(a['res_real'])} {cop(a['g_real'], True)} COP\n"
                          f"LIBRO: {a['pe_libro']:,.1f} → {a['px_libro']:,.1f}: {nom(a['res_libro'])} {cop(a['g_libro'], True)} COP\n"
                          f"Saldo real {cop(est['real'])} COP · libro {cop(est['libro'])} COP")
        # preventiva del día: 4 pérdidas seguidas o −6 % del saldo con que empezó el día
        if not est.get("parada_dia") and (est["seguidas"] >= cfg["max_seguidas"] or est["real"] - est["inicio_dia"] <= -cfg["tope_dia"] * est["inicio_dia"]):
            est["parada_dia"] = int(time.time())
            avisos.append(f"PREVENTIVA DEL DÍA: {est['seguidas']} pérdidas seguidas o −{cfg['tope_dia'] * 100:.0f} % del día. "
                          "No se apuesta más hasta mañana.")
        # preventiva de la estrategia: revisa las últimas 100 cada 100 apuestas
        hechas = [x for x in est["hechas"] if x.get("tipo", "principal") == "principal"]
        if len(hechas) % cfg["revision"] == 0:
            ult = [x for x in hechas[-cfg["revision"]:] if x["res_real"] != 0]
            acierto = sum(1 for x in ult if x["res_real"] > 0) / max(1, len(ult))
            necesario = 1 / (1 + cfg["pago"])
            if acierto < necesario:
                est["apagada"] = int(time.time())
                avisos.append(f"PREVENTIVA DE LA ESTRATEGIA: en las últimas {cfg['revision']} apuestas acertó {acierto * 100:.1f} % y con pago "
                              f"{cfg['pago']:.2f} hace falta {necesario * 100:.1f} %. Queda apagada; se vuelve a encender desde la pantalla.")
        if avisos:
            avisar("\n\n".join(avisos))
    est["hechas"] = est["hechas"][-2000:]


def motor(una=False):
    proxima = None
    while True:
        try:
            with CANDADO:
                cfg = {**DEF, **leer(CONFIG, {})}
                est = leer(ESTADO, None) or estado_inicial(cfg)
                if cfg["reiniciar_t"] > est["inicio"]:
                    est = estado_inicial(cfg)
                    log("cuentas reiniciadas desde la pantalla")
                for k, v in estado_inicial(cfg).items():
                    est.setdefault(k, v)
                if est.get("apagada") and cfg.get("reencender_t", 0) > est["apagada"]:
                    est["apagada"] = None
            ahora = time.time()
            hoy = dt.datetime.fromtimestamp(ahora, COL).strftime("%Y-%m-%d")
            if est["dia"] != hoy:  # día nuevo en Colombia: la preventiva del día vuelve a cero
                est.update(dia=hoy, inicio_dia=est["real"], seguidas=0, parada_dia=None)
            if proxima is None:
                proxima = ahora - ahora % 300 + 300
            resolver(cfg, est)
            if ahora >= proxima + 2 or una:
                cierre = int(ahora - ahora % 300)
                proxima = cierre + 300
                if cfg["sombra"]:
                    s = revisar_c3r(cfg, est)
                    if s:
                        est["sombras"].append(s)
                        log(f"sombra: tres cuervos al revés a {s['pe_real']}")
                if cierre % 900 == 0 or una:
                    if cfg["activo"]:
                        a = revisar_rev15(cfg, est)
                        if a:
                            est["pendientes"].append(a)
                            log(f"apuesta {a['id']} {'arriba' if a['d'] > 0 else 'abajo'} a {a['pe_real']}")
                            if cfg["avisos"]:
                                avisar(f"APUESTA EN PAPEL · BTC {'▲ ARRIBA' if a['d'] > 0 else '▼ ABAJO'} · vence en {a['plazo']} min\n"
                                       f"Entró a {a['pe_real']:,.1f} ({dt.datetime.fromtimestamp(a['t_real'], COL):%H:%M:%S}) con "
                                       f"{cop(a['monto_real'])} COP. Vela de 15 min fuerte ({a['fuerza']} veces la media), apuesta en contra.\n"
                                       f"Si quiere copiarla en Binance (Contratos de Evento, BTCUSDT, {a['plazo']} min), tiene unos 30 segundos.")
                    else:
                        est["ultimo_motivo"] = "en pausa desde la pantalla"
            est["latido"] = int(time.time())
            est["proxima_vela"] = int(proxima - (proxima % 900) + (900 if proxima % 900 else 0))
            with CANDADO:
                escribir(ESTADO, est)
        except Exception:
            log("error: " + traceback.format_exc().replace("\n", " | ")[:1200])
        if una:
            return
        if os.path.exists(PARAR):
            os.remove(PARAR)
            log("PARAR: salgo")
            os._exit(0)
        time.sleep(1)


# ---------------------------------------------------------------- pantalla
_vivo = {"t": 0.0, "px": None}


def precio_vivo(sim):
    if time.time() - _vivo["t"] > 1:
        try:
            _vivo["px"], _vivo["t"] = precio(sim), time.time()
        except Exception:
            pass
    return _vivo["px"]


def datos():
    cfg = {**DEF, **leer(CONFIG, {})}
    est = leer(ESTADO, None) or estado_inicial(cfg)
    for k, v in estado_inicial(cfg).items():
        est.setdefault(k, v)
    hechas = est["hechas"]
    hoy = dt.datetime.now(COL).strftime("%Y-%m-%d")
    dias = {}
    for a in hechas:
        d = dt.datetime.fromtimestamp(a["t_real"], COL).strftime("%Y-%m-%d")
        x = dias.setdefault(d, {"n": 0, "g": 0, "real": 0.0, "libro": 0.0})
        x["n"] += 1
        x["g"] += a["res_real"] > 0
        x["real"] += a["g_real"]
        x["libro"] += a["g_libro"]
    con = [a for a in hechas if a["res_real"] != 0]
    return {"ahora": time.time(), "cfg": cfg, "real": est["real"], "libro": est["libro"], "capital": cfg["capital_cop"],
            "pendientes": est["pendientes"], "hechas": hechas[-40:][::-1], "dias": sorted(dias.items(), reverse=True)[:14],
            "hoy": dias.get(hoy, {"n": 0, "g": 0, "real": 0.0, "libro": 0.0}),
            "aciertos": [sum(1 for a in con if a["res_real"] > 0), len(con)],
            "aciertos_libro": [sum(1 for a in hechas if a["res_libro"] > 0), sum(1 for a in hechas if a["res_libro"] != 0)],
            "motivo": est.get("ultimo_motivo", ""), "proxima": est.get("proxima_vela"), "latido": est.get("latido", 0),
            "contexto": est.get("contexto", 0), "precio": precio_vivo(cfg["simbolo"]), "inicio": est["inicio"],
            "sombras": est.get("sombras", []), "sombras_hechas": est.get("sombras_hechas", [])[-30:][::-1],
            "sombra_tasa": {k: [sum(1 for x in est.get("sombras_hechas", []) if x["res"].get(k, 0) > 0),
                                sum(1 for x in est.get("sombras_hechas", []) if x["res"].get(k, 0) != 0)] for k in ("5", "10")},
            "seguidas": est.get("seguidas", 0), "parada_dia": est.get("parada_dia"), "apagada": est.get("apagada"),
            "inicio_dia": est.get("inicio_dia", est["real"])}


ESTILO = """
:root{--fondo:#141A21;--superficie:#1E2630;--texto:#E6EDF3;--acento:#F2B84B;--gana:#3FB97F;--pierde:#F06A5E;
--texto-2:rgba(230,237,243,.72);--fila:rgba(230,237,243,.04);
--f-titulo:"Segoe UI Variable Display","Segoe UI",system-ui,sans-serif;--f-cuerpo:"Segoe UI",system-ui,sans-serif;
--f-datos:"Cascadia Mono",Consolas,ui-monospace,monospace;
--t-xs:12.8px;--t-s:16px;--t-m:20px;--t-l:25px;--t-xl:31.25px;--t-2xl:39px;--e1:4px;--e2:8px;--e3:16px;--e4:24px;--e5:32px;--e6:48px}
*{box-sizing:border-box}html{background:var(--fondo)}body{margin:0;background:var(--fondo);color:var(--texto);font:400 var(--t-s)/1.6 var(--f-cuerpo)}
.marco{max-width:1120px;margin:0 auto;padding:var(--e5) var(--e3)}
header{display:flex;flex-wrap:wrap;gap:var(--e3);align-items:baseline;justify-content:space-between;margin-bottom:var(--e5)}
h1{font:600 var(--t-xl)/1.2 var(--f-titulo);margin:0}h2{font:600 var(--t-m)/1.3 var(--f-titulo);margin:0 0 var(--e3)}
.sub{color:var(--texto-2);margin:var(--e1) 0 0}.datos{font-family:var(--f-datos);font-variant-numeric:tabular-nums}
.pastilla{display:inline-flex;gap:var(--e2);align-items:center;background:var(--superficie);padding:var(--e2) var(--e3);border-radius:999px}
.punto{width:var(--e2);height:var(--e2);border-radius:50%;background:var(--gana)}.punto.quieto{background:var(--pierde)}
section{margin-bottom:var(--e5)}
.apuesta{background:var(--superficie);border-radius:16px;padding:var(--e4);display:grid;gap:var(--e3)}
.dir{font:600 var(--t-2xl)/1 var(--f-titulo)}.dir small{font:400 var(--t-s) var(--f-cuerpo);color:var(--texto-2);margin-left:var(--e2)}
.precios{display:flex;flex-wrap:wrap;gap:var(--e4)}.precios div span{display:block;color:var(--texto-2);font-size:var(--t-xs)}
.precios b{font:500 var(--t-l) var(--f-datos);font-variant-numeric:tabular-nums}
.barra{height:var(--e2);border-radius:999px;background:var(--fila);overflow:hidden}.barra i{display:block;height:100%;background:var(--acento);width:0}
.estado{font:600 var(--t-m) var(--f-titulo)}
.gana{color:var(--gana)}.pierde{color:var(--pierde)}.tenue{color:var(--texto-2)}
.vacio{background:var(--superficie);border-radius:16px;padding:var(--e4);color:var(--texto-2)}
.cifras{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--e3)}
.c{background:var(--superficie);border-radius:12px;padding:var(--e3)}.c span{color:var(--texto-2);font-size:var(--t-xs)}
.c b{display:block;font:500 var(--t-l) var(--f-datos);font-variant-numeric:tabular-nums;margin-top:var(--e1)}
.tabla{background:var(--superficie);border-radius:12px;padding:var(--e2);overflow-x:auto}
table{border-collapse:collapse;width:100%}th{font:600 var(--t-xs) var(--f-cuerpo);color:var(--texto-2);text-align:left;padding:var(--e2) var(--e3)}
td{padding:var(--e2) var(--e3);white-space:nowrap}tbody tr:nth-child(odd){background:var(--fila)}td.n{font-family:var(--f-datos);font-variant-numeric:tabular-nums;text-align:right}
form{background:var(--superficie);border-radius:12px;padding:var(--e4);display:grid;gap:var(--e3)}
label{display:flex;flex-wrap:wrap;gap:var(--e2);align-items:center;justify-content:space-between}
input,select{font:500 var(--t-s) var(--f-datos);background:var(--fondo);color:var(--texto);border:0;border-radius:8px;padding:var(--e2) var(--e3)}
button{font:600 var(--t-s) var(--f-cuerpo);background:var(--acento);color:var(--fondo);border:0;border-radius:8px;padding:var(--e2) var(--e4);cursor:pointer}
button.otro{background:var(--fila);color:var(--texto)}
:focus-visible{outline:3px solid var(--acento);outline-offset:2px}
a{color:var(--acento)}footer{color:var(--texto-2);font-size:var(--t-xs);padding-top:var(--e4)}
.nota{color:var(--texto-2);font-size:var(--t-xs);margin-top:var(--e2)}
@media (prefers-reduced-motion:no-preference){.barra i{transition:width 1s linear}}
@media (max-width:480px){.dir{font-size:var(--t-xl)}.precios b{font-size:var(--t-m)}}
"""

PAGINA = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Binarias en papel · tiempo real</title><style>""" + ESTILO + """</style></head><body><div class="marco">
<header><div><h1>Binarias en papel, en tiempo real</h1><p class="sub">BTC · señal en velas de 15 min · vence a los 10 min, como los Contratos de Evento de Binance · precios vivos. Papel: no se mueve dinero.</p></div>
<div class="pastilla" role="status"><span class="punto" id="punto" aria-hidden="true"></span><span id="latido">conectando…</span></div></header>
<main>
<section aria-labelledby="t-curso"><h2 id="t-curso">Apuesta en curso</h2><div id="curso"></div></section>
<section aria-label="Resumen"><div class="cifras">
<div class="c"><span>Saldo real</span><b id="s-real">…</b><span id="s-real-2"></span></div>
<div class="c"><span>Hoy</span><b id="s-hoy">…</b><span id="s-hoy-2"></span></div>
<div class="c"><span>Aciertos reales</span><b id="s-ac">…</b><span id="s-ac-2"></span></div>
<div class="c"><span>Libro frente a real</span><b id="s-lib">…</b><span id="s-lib-2"></span></div>
<div class="c"><span>Preventivas</span><b id="s-prev">…</b><span id="s-prev-2"></span></div></div></section>
<section aria-labelledby="t-ap"><h2 id="t-ap">Apuestas</h2><div class="tabla"><table><thead><tr><th>Hora</th><th>Apuesta</th><th>Entrada real</th><th>Al vencer</th>
<th>Resultado real</th><th>Libro</th><th>Saldo real</th></tr></thead><tbody id="ap"></tbody></table></div></section>
<section aria-labelledby="t-som"><h2 id="t-som">Sombra: «tres cuervos al revés» de su curso (sin dinero)</h2>
<p class="nota" id="som-tasa">Se mide sola en velas de 5 min, apostando a que sube, a 5 y 10 min.</p>
<div class="tabla"><table><thead><tr><th>Hora</th><th>Entrada</th><th>A 5 min</th><th>A 10 min</th></tr></thead><tbody id="som"></tbody></table></div></section>
<section aria-labelledby="t-dia"><h2 id="t-dia">Por día</h2><div class="tabla"><table><thead><tr><th>Día</th><th>Apuestas</th><th>Aciertos</th>
<th>Real (COP)</th><th>Libro (COP)</th></tr></thead><tbody id="dias"></tbody></table></div></section>
<section aria-labelledby="t-cuadro"><h2 id="t-cuadro">Cuadro de margen operativo de las pruebas (esta señal, 10 min, 2020-2026, desde 150.000 COP)</h2>
<div class="tabla"><table><thead><tr><th>Entrada</th><th>Pago</th><th>Apuesta</th><th>Margen operativo</th><th>% al día 2020-26</th><th>% al día 2024-26</th>
<th>COP al día al empezar (2024-26)</th><th>Caída máxima 2024-26</th></tr></thead><tbody id="cuadro"></tbody></table></div>
<p class="nota">Margen operativo = resultado / lo cobrado en aciertos. Para no perder hay que acertar 55,6 % con pago 0,80; 54,1 % con 0,85; 52,6 % con 0,90.</p></section>
<section aria-labelledby="t-aj"><h2 id="t-aj">Ajustes de la cuenta en papel</h2><form method="post" action="/ajustes">
<label>Apuesta, en % del saldo <input type="number" name="apuesta" min="0.5" max="20" step="0.5" id="f-ap"></label>
<label>Pago del bróker si acierta <select name="pago" id="f-pago"><option value="0.80">0,80</option><option value="0.85">0,85</option><option value="0.90">0,90</option><option value="0.92">0,92</option></select></label>
<label>Operar <input type="checkbox" name="activo" id="f-act"></label><label>Avisos a Telegram <input type="checkbox" name="avisos" id="f-av"></label>
<div><button>Guardar ajustes</button> <button class="otro" name="reiniciar" value="1">Reiniciar las dos cuentas con 150.000 COP</button></div></form></section>
</main><footer><a href="/replay">Ver las pruebas como si pasaran en vivo</a> · <a href="http://127.0.0.1:8791">Su método y la copia de líderes</a><br>
Señal: vela de 15 min con cuerpo de 2 o más veces la media de las 100 anteriores → apuesta en contra, solo a favor del contexto del día.
Real = precio vivo al apostar y al vencer. Libro = cierre de la vela y precio 10 min después.
En Binance la apuesta mínima es 5 USDT (unos 15.900 COP): con 150.000 COP sería el 10,6 % del saldo; para apostar el 2 % hacen falta unos 795.000 COP.</footer></div>
<script>
const $=id=>document.getElementById(id);let ajustado=false,desfase=0;
const cop=(x,s)=>{const v=Math.round(x);if(Math.abs(v)<1)return"0";return(s&&v>0?"+":v<0?"−":"")+Math.abs(v).toLocaleString("es-CO")};
const px=x=>x==null?"…":x.toLocaleString("es-CO",{minimumFractionDigits:1,maximumFractionDigits:1});
const hora=t=>new Date(t*1000).toLocaleTimeString("es-CO",{timeZone:"America/Bogota",hour:"2-digit",minute:"2-digit",second:"2-digit"});
const res=(r,g)=>r==null?'<span class="tenue">pendiente</span>':r>0?`<span class="gana">▲ ganó ${cop(g,1)}</span>`:r<0?`<span class="pierde">▼ perdió ${cop(g,1)}</span>`:'<span class="tenue">= empate</span>';
function pinta(d){desfase=d.ahora-Date.now()/1000;const vivo=(Date.now()/1000-d.latido)<10;
$("punto").className="punto"+(vivo?"":" quieto");
$("latido").textContent=vivo?`operando · próxima vela ${d.proxima?hora(d.proxima):"…"}`:"el agente no responde: revise que esté abierto";
const c=$("curso");if(!d.pendientes.length){c.innerHTML=`<div class="vacio">Sin apuesta abierta. ${d.motivo||"Esperando el cierre de la próxima vela de 15 minutos."}</div>`}else{
c.innerHTML=d.pendientes.map(a=>{const vence=a.vence_real,quedan=Math.max(0,vence-d.ahora),tot=vence-a.t_real,va=d.precio==null?0:Math.sign((d.precio-a.pe_real)*a.d);
return`<div class="apuesta"><div class="dir">${a.d>0?"▲ ARRIBA":"▼ ABAJO"}<small>${cop(a.monto_real)} COP · pago ${String(a.pago).replace(".",",")} · vela de ${hora(a.t_cierre).slice(0,5)}</small></div>
<div class="precios"><div><span>Entró a</span><b>${px(a.pe_real)}</b></div><div><span>Ahora</span><b>${px(d.precio)}</b></div><div><span>Vence en</span><b data-vence="${vence}">${Math.floor(quedan/60)}:${String(Math.floor(quedan%60)).padStart(2,"0")}</b></div></div>
<div class="barra" role="progressbar" aria-label="Tiempo hasta el vencimiento" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round((1-quedan/tot)*100)}"><i style="width:${(1-quedan/tot)*100}%"></i></div>
<div class="estado ${va>0?"gana":va<0?"pierde":"tenue"}">${va>0?"▲ Va ganando: cobraría "+cop(a.monto_real*a.pago,1)+" COP":va<0?"▼ Va perdiendo: perdería "+cop(-a.monto_real,1)+" COP":"= Igual al precio de entrada"}</div></div>`}).join("")}
$("s-real").textContent=cop(d.real)+" COP";$("s-real-2").textContent=`empezó con ${cop(d.capital)} · ${(d.real/d.capital*100-100).toFixed(2).replace(".",",")} %`;
$("s-hoy").innerHTML=`<span class="${d.hoy.real>=0?"gana":"pierde"}">${d.hoy.real>=0?"▲":"▼"} ${cop(d.hoy.real,1)} COP</span>`;$("s-hoy-2").textContent=`${d.hoy.n} apuestas hoy`;
$("s-ac").textContent=d.aciertos[1]?`${(d.aciertos[0]/d.aciertos[1]*100).toFixed(1).replace(".",",")} %`:"—";$("s-ac-2").textContent=`${d.aciertos[0]} de ${d.aciertos[1]} sin contar empates · hace falta ${(100/(1+d.cfg.pago)).toFixed(1).replace(".",",")} %`;
$("s-lib").textContent=cop(d.libro-d.real,1)+" COP";$("s-lib-2").textContent=`libro ${cop(d.libro)} · aciertos del libro ${d.aciertos_libro[0]} de ${d.aciertos_libro[1]}`;
const nec=100/(1+d.cfg.pago),pd=(d.real-d.inicio_dia)/d.inicio_dia*100;
$("s-prev").innerHTML=d.apagada?'<span class="pierde">▼ estrategia apagada</span>':d.parada_dia?'<span class="pierde">▼ día parado</span>':'<span class="gana">▲ en orden</span>';
$("s-prev-2").textContent=`pérdidas seguidas ${d.seguidas} de ${d.cfg.max_seguidas} · el día va ${pd.toFixed(1).replace(".",",")} % (tope −${Math.round(d.cfg.tope_dia*100)} %)`;
const st=d.sombra_tasa,tx=k=>st[k][1]?`${(st[k][0]/st[k][1]*100).toFixed(1).replace(".",",")} % (${st[k][0]} de ${st[k][1]})`:"sin datos";
$("som-tasa").textContent=`Acierto en vivo: a 5 min ${tx("5")} · a 10 min ${tx("10")} · para no perder con pago ${String(d.cfg.pago).replace(".",",")} hace falta ${nec.toFixed(1).replace(".",",")} %.`;
const sr=r=>r==null?'<span class="tenue">corriendo</span>':r>0?'<span class="gana">▲ acertó</span>':r<0?'<span class="pierde">▼ falló</span>':'<span class="tenue">= empate</span>';
$("som").innerHTML=[...d.sombras,...d.sombras_hechas].map(x=>`<tr><td>${hora(x.t_real)}</td><td class="n">${px(x.pe_real)}</td><td>${sr(x.res["5"])}</td><td>${sr(x.res["10"])}</td></tr>`).join("")||'<tr><td colspan="4" class="tenue">Todavía no ha salido la señal: aparece cuando hay tres velas bajistas fuertes seguidas después de una subida.</td></tr>';
$("ap").innerHTML=d.hechas.map(a=>`<tr><td>${hora(a.t_real)}</td><td>${a.d>0?"▲ arriba":"▼ abajo"} · ${cop(a.monto_real)}</td><td class="n">${px(a.pe_real)}</td><td class="n">${px(a.px_real)}</td><td>${res(a.res_real,a.g_real)}</td><td>${res(a.res_libro,a.g_libro)}</td><td class="n">—</td></tr>`).join("")||'<tr><td colspan="7" class="tenue">Todavía no hay apuestas cerradas: la primera aparece aquí 15 minutos después de abrirse.</td></tr>';
$("dias").innerHTML=d.dias.map(([k,x])=>`<tr><td>${k}</td><td class="n">${x.n}</td><td class="n">${x.g}</td><td class="n ${x.real>=0?"gana":"pierde"}">${cop(x.real,1)}</td><td class="n">${cop(x.libro,1)}</td></tr>`).join("")||'<tr><td colspan="5" class="tenue">Sin días cerrados todavía.</td></tr>';
if(!ajustado){$("f-ap").value=(d.cfg.apuesta*100);$("f-pago").value=d.cfg.pago.toFixed(2);$("f-act").checked=d.cfg.activo;$("f-av").checked=d.cfg.avisos;ajustado=true}}
async function ciclo(){try{const r=await fetch("/datos.json",{cache:"no-store"});pinta(await r.json())}catch(e){$("latido").textContent="sin conexión con el agente local";$("punto").className="punto quieto"}}
async function cuadro(){try{const q=await (await fetch("/cuadro.json")).json();$("cuadro").innerHTML=q.filter(x=>x.apuesta<=0.05).map(x=>`<tr><td>${x.entrada}</td><td class="n">${x.pago.toFixed(2).replace(".",",")}</td><td class="n">${Math.round(x.apuesta*100)} %</td><td class="n ${x.todo.margen>=0?"gana":"pierde"}">${x.todo.margen>=0?"▲":"▼"} ${x.todo.margen.toFixed(1).replace(".",",")} %</td><td class="n">${x.todo.crec_dia.toFixed(3).replace(".",",")} %</td><td class="n ${x.B.crec_dia>=0?"gana":"pierde"}">${x.B.crec_dia>=0?"▲":"▼"} ${x.B.crec_dia.toFixed(3).replace(".",",")} %</td><td class="n">${cop(150000*x.B.crec_dia/100,1)}</td><td class="n">${Math.round(x.B.caida)} %</td></tr>`).join("")}catch(e){}}
ciclo();cuadro();setInterval(ciclo,1000);
</script></body></html>"""

REPRO = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pruebas de binarias como si fueran en vivo</title><style>""" + ESTILO + """
canvas{width:100%;height:220px;background:var(--superficie);border-radius:12px}.mandos{display:flex;flex-wrap:wrap;gap:var(--e3);align-items:center;margin-bottom:var(--e4)}</style></head>
<body><div class="marco"><header><div><h1>Las pruebas, como si pasaran en vivo</h1><p class="sub">Apuestas de la prueba en el último trimestre de datos (señal REV15 CTX, vence a los 10 min, entrada al cierre). El reloj corre acelerado.</p></div>
<div class="pastilla" role="status"><span id="reloj" class="datos">…</span></div></header><main>
<div class="mandos"><button id="play">Reproducir</button><label>Velocidad <select id="vel"><option value="60">1 hora por minuto</option><option value="600" selected>10 horas por minuto</option><option value="3600">2,5 días por minuto</option></select></label>
<label>Pago <select id="pago"><option value="0.80">0,80</option><option value="0.85" selected>0,85</option><option value="0.90">0,90</option></select></label>
<label>Apuesta <select id="ap"><option value="0.01">1 % del saldo</option><option value="0.02" selected>2 % del saldo</option><option value="0.05">5 % del saldo</option></select></label>
<button class="otro" id="reset">Volver al principio</button></div>
<section><h2>Apuesta en curso</h2><div id="curso" class="vacio">Pulse «Reproducir».</div></section>
<section><div class="cifras"><div class="c"><span>Saldo</span><b id="s">150.000 COP</b></div><div class="c"><span>Apuestas</span><b id="n">0</b></div>
<div class="c"><span>Aciertos</span><b id="a">—</b></div><div class="c"><span>Resultado del día simulado</span><b id="h">0</b></div></div></section>
<section><h2>Saldo apuesta a apuesta</h2><canvas id="g" role="img" aria-label="Curva del saldo de la reproducción"></canvas></section>
<section><h2>Últimas apuestas</h2><div class="tabla"><table><thead><tr><th>Hora (Colombia)</th><th>Apuesta</th><th>Entrada</th><th>Al vencer</th><th>Resultado</th><th>Saldo</th></tr></thead><tbody id="t"></tbody></table></div></section>
</main><footer><a href="/">Volver a las binarias en vivo</a></footer></div>
<script>
const $=id=>document.getElementById(id);let A=[],venc=900,i=0,reloj=0,corre=false,saldo=150000,serie=[150000],hechas=[],ultimo=0,dia={};
const cop=(x,s)=>{const v=Math.round(x);if(Math.abs(v)<1)return"0";return(s&&v>0?"+":v<0?"−":"")+Math.abs(v).toLocaleString("es-CO")};
const f=t=>new Date(t*1000).toLocaleString("es-CO",{timeZone:"America/Bogota",day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
const px=x=>x.toLocaleString("es-CO",{maximumFractionDigits:4});
function reinicia(){i=0;saldo=150000;serie=[150000];hechas=[];dia={};reloj=A.length?A[0].t-60:0;pinta()}
function paso(dt){if(!corre||!A.length)return;reloj+=dt*Number($("vel").value);const pago=Number($("pago").value),ap=Number($("ap").value);
while(i<A.length&&A[i].t+venc<=reloj){const x=A[i],m=Math.round(ap*saldo),g=x.res>0?m*pago:x.res<0?-m:0;saldo+=g;serie.push(saldo);const k=f(x.t).slice(0,5);dia[k]=(dia[k]||0)+g;hechas.unshift({...x,m,g,saldo});if(hechas.length>15)hechas.pop();i++}
if(i>=A.length){corre=false;$("play").textContent="Reproducir"}pinta()}
function pinta(){$("reloj").textContent=reloj?f(reloj):"…";$("s").textContent=cop(saldo)+" COP";$("n").textContent=hechas.length?serie.length-1:0;
const g=A.slice(0,i).filter(x=>x.res!==0),w=g.filter(x=>x.res>0).length;$("a").textContent=g.length?(w/g.length*100).toFixed(1).replace(".",",")+" % ("+w+" de "+g.length+")":"—";
const k=reloj?f(reloj).slice(0,5):"";$("h").innerHTML=`<span class="${(dia[k]||0)>=0?"gana":"pierde"}">${cop(dia[k]||0,1)} COP</span>`;
const cur=A[i]&&A[i].t<=reloj?A[i]:null;if(cur){const q=cur.t+venc-reloj;$("curso").className="apuesta";$("curso").innerHTML=`<div class="dir">${cur.d>0?"▲ ARRIBA":"▼ ABAJO"}<small>${cur.a} · ${f(cur.t)}</small></div><div class="precios"><div><span>Entró a</span><b>${px(cur.pe)}</b></div><div><span>Vence en</span><b>${Math.floor(q/60)}:${String(Math.floor(q%60)).padStart(2,"0")}</b></div></div><div class="barra"><i style="width:${(1-q/venc)*100}%"></i></div>`}else{$("curso").className="vacio";$("curso").textContent=corre?"Esperando la próxima vela fuerte…":"En pausa."}
$("t").innerHTML=hechas.map(x=>`<tr><td>${f(x.t)}</td><td>${x.a} ${x.d>0?"▲ arriba":"▼ abajo"} · ${cop(x.m)}</td><td class="n">${px(x.pe)}</td><td class="n">${px(x.px)}</td><td>${x.res>0?'<span class="gana">▲ ganó '+cop(x.g,1)+"</span>":x.res<0?'<span class="pierde">▼ perdió '+cop(x.g,1)+"</span>":"= empate"}</td><td class="n">${cop(x.saldo)}</td></tr>`).join("");
const c=$("g"),r=c.getBoundingClientRect(),dpr=devicePixelRatio||1;c.width=r.width*dpr;c.height=r.height*dpr;const x=c.getContext("2d");x.scale(dpr,dpr);
const mn=Math.min(...serie),mx=Math.max(...serie),W=r.width-32,Hh=r.height-32;x.strokeStyle="rgba(230,237,243,.25)";x.setLineDash([4,4]);const y0=16+Hh-(150000-mn)/((mx-mn)||1)*Hh;x.beginPath();x.moveTo(16,y0);x.lineTo(16+W,y0);x.stroke();x.setLineDash([]);
x.strokeStyle=saldo>=150000?"#3FB97F":"#F06A5E";x.lineWidth=2;x.beginPath();serie.forEach((v,j)=>{const X=16+j/Math.max(1,serie.length-1)*W,Y=16+Hh-(v-mn)/((mx-mn)||1)*Hh;j?x.lineTo(X,Y):x.moveTo(X,Y)});x.stroke();
c.setAttribute("aria-label",`Saldo de la reproducción: de 150.000 a ${cop(saldo)} COP en ${serie.length-1} apuestas`)}
$("play").onclick=()=>{corre=!corre;$("play").textContent=corre?"Pausar":"Reproducir";ultimo=performance.now()};$("reset").onclick=()=>{corre=false;$("play").textContent="Reproducir";reinicia()};
function bucle(t){if(corre){paso((t-ultimo)/1000)}ultimo=t;requestAnimationFrame(bucle)}
fetch("/replay.json").then(r=>r.json()).then(d=>{A=d.apuestas;venc=d.vencimiento_min*60;reinicia();requestAnimationFrame(bucle)}).catch(()=>{$("curso").textContent="No se encontró el archivo de la prueba (t3_replay.json)."});
</script></body></html>"""


class Pantalla(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def enviar(self, cuerpo, tipo):
        b = cuerpo if isinstance(cuerpo, bytes) else cuerpo.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta == "/datos.json":
            self.enviar(json.dumps(datos(), ensure_ascii=False), "application/json; charset=utf-8")
        elif ruta in ("/replay.json", "/cuadro.json"):
            p = REPLAY if ruta == "/replay.json" else CUADRO
            self.enviar(open(p, "rb").read() if os.path.exists(p) else b"[]", "application/json; charset=utf-8")
        elif ruta == "/replay":
            self.enviar(REPRO, "text/html; charset=utf-8")
        else:
            self.enviar(PAGINA, "text/html; charset=utf-8")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        d = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
        with CANDADO:
            cfg = {**DEF, **leer(CONFIG, {})}
            if d.get("apuesta"):
                cfg["apuesta"] = max(0.005, min(0.20, float(d["apuesta"][0]) / 100))
            if d.get("pago"):
                cfg["pago"] = float(d["pago"][0])
            if "activo" in d and not cfg["activo"]:
                cfg["reencender_t"] = int(time.time())
            cfg["activo"], cfg["avisos"] = "activo" in d, "avisos" in d
            if d.get("reiniciar"):
                cfg["reiniciar_t"] = int(time.time())
            escribir(CONFIG, cfg)
        log("ajustes desde la pantalla: " + json.dumps({k: cfg[k] for k in ("apuesta", "pago", "activo", "avisos")}))
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()


class Servidor(ThreadingHTTPServer):
    allow_reuse_address = False


def puerto_libre():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", PUERTO))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main():
    if sys.stdout is None:
        sys.stdout = sys.stderr = open(os.devnull, "w")
    if "--una-vez" in sys.argv:
        motor(una=True)
        print(json.dumps({k: v for k, v in leer(ESTADO, {}).items() if k != "hechas"}, ensure_ascii=False, indent=1)[:1500])
        return
    if not puerto_libre():
        log("ya hay unas binarias corriendo (puerto ocupado): salgo")
        return
    srv = Servidor(("127.0.0.1", PUERTO), Pantalla)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log(f"pantalla en http://127.0.0.1:{PUERTO}")
    motor()


if __name__ == "__main__":
    main()
