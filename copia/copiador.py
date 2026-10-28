"""Copiador en papel de los líderes de copy trading de Binance, con su pantalla (28/10/2026). Solo biblioteca estándar.

Pedido de Nicolás: «pruebe haciendo copy trading en papel con los mejores; cree una pantalla y yo tomo esos riesgos».

Cada minuto lee las posiciones abiertas públicas de los líderes de copia/config.json (los que las muestran) y las copia en
papel con precios reales de Binance futuros:
- posición nueva del líder → abre con margen = «margen %» del saldo libre, su mismo apalancamiento;
- el líder agrega o reduce → agrega o reduce en la misma proporción;
- el líder cierra → cierra al precio del momento (hasta un minuto tarde, como un copiador real).
Las posiciones que el líder ya tenía al arrancar no se copian (un copiador real tampoco las recibe).
Cobra comisión de tomador (0,05 % del nocional al entrar, agregar, reducir y salir) y la parte del líder (10 % de la ganancia
de cada posición cerrada con ganancia). Cada 30 minutos registra los cierres de los 10 líderes, también los que esconden sus
posiciones, para ver si los mejores siguen ganando (seguimiento.jsonl).

Su método operado por Claude (28/10, pedido: «haz como el tipo hace… así operas tú»): cuenta de papel aparte (150.000 COP) que
aplica la regla de 迪亚马特 medida en su historial (investigacion/copy-trading/c3 y c4): cada minuto lee los 24 h de todos los
perpetuos USDT de Binance; si una moneda subió ≥ 30 % y ya bajó ≥ 3 % desde su máximo de 24 h, vende en corto a 5× en margen
cruzado y cierra cuando el precio cae 5 %; sin stop; a las 96 h cierra a mercado. Revisa con velas de 1 minuto, cobra comisión,
deslizamiento y financiación, y si las pérdidas abiertas alcanzan el saldo la cuenta se liquida entera (margen cruzado).
Preventiva al alza (opcional, pedido «ves que sube y apuestas para arriba»): si el precio sube «alza_pct» sobre la entrada, corta
el corto y abre un largo a 5× que sale al caer «seguimiento_pct» desde su máximo. Avisos a su Telegram (texto, sin ventanas).

Pantalla: http://127.0.0.1:8791 (saldo en pesos, posiciones, cierres, seguimiento y el riesgo de cada líder, que se cambia ahí).
Uso:  pythonw copiador.py          (sin ventana; registro en copia/copiador.log)
      python copiador.py --una-vez (una vuelta, para probar)
Parar: crear el archivo copia/PARAR, o cerrar el proceso pythonw.exe del copiador."""
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
CONFIG = os.path.join(AQUI, "config.json")
ESTADO = os.path.join(AQUI, "estado.json")
EVENTOS = os.path.join(AQUI, "operaciones.jsonl")
SEGUIM = os.path.join(AQUI, "seguimiento.jsonl")
REGISTRO = os.path.join(AQUI, "copiador.log")
PARAR = os.path.join(AQUI, "PARAR")
PUERTO = 8791
API = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/141.0 Safari/537.36",
     "Content-Type": "application/json", "clienttype": "web"}
TAKER = 0.0005
MAKER, DESLIZ = 0.0002, 0.0005
FAPI = "https://fapi.binance.com/fapi/v1/"
METODO = os.path.join(AQUI, "metodo.json")
METODO_EV = os.path.join(AQUI, "metodo.jsonl")
ALERTAS = os.path.join(AQUI, "alertas")
TG = os.path.join(os.path.dirname(AQUI), "tg_pc.py")
METODO_DEF = {"activo": True, "capital_cop": 150000, "margen_pct": 10, "max_abiertas": 5, "apal": 5, "umbral_pct": 30,
              "giro_pct": 3, "objetivo_pct": 5, "max_horas": 96, "alza_pct": 0, "seguimiento_pct": 20, "max_largo_h": 48,
              "alertas": True, "reiniciar_t": 0, "monedas": ["BMTUSDT"]}  # su orden: solo la moneda donde él más acierta
UTC = dt.timezone.utc
COL = dt.timezone(dt.timedelta(hours=-5))
CANDADO = threading.Lock()


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def leer(ruta, defecto):
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except Exception:
        return defecto


def escribir(ruta, datos):
    tmp = ruta + ".tmp"
    json.dump(datos, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def anotar(ruta, fila):
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def red(ruta, cuerpo=None):
    req = urllib.request.Request(API + ruta, data=json.dumps(cuerpo).encode() if cuerpo else None, headers=H,
                                 method="POST" if cuerpo else "GET")
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def precio(simbolo):
    u = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={simbolo}"
    return float(json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=15).read())["price"])


def posiciones_lider(pid):
    d = red(f"lead-data/positions?portfolioId={pid}").get("data") or []
    out = {}
    for x in d:
        amt = float(x.get("positionAmount") or 0)
        if amt == 0:
            continue
        out[f"{x['symbol']}|{x.get('positionSide') or ('LONG' if amt > 0 else 'SHORT')}"] = {
            "simbolo": x["symbol"], "lado": 1 if amt > 0 else -1, "cantidad": abs(amt),
            "precio": float(x.get("markPrice") or x.get("entryPrice") or 0), "apal": int(float(x.get("leverage") or 1))}
    return out


def estado_inicial(cfg):
    return {"efectivo": cfg["capital_cop"] / cfg["cop_usdt"], "inicio": int(time.time()), "posiciones": {}, "ignorar": {},
            "lider_previo": {}, "cerradas": 0, "ganadas": 0, "pnl_cerrado": 0.0, "equidad": [], "ultimo_seguimiento": 0}


def vuelta(cfg, est):
    """Una vuelta del copiador. Devuelve el estado actualizado."""
    primera = not est["lider_previo"]
    for lid in cfg["lideres"]:
        pid = lid["id"]
        if not lid.get("visible", True):
            continue
        try:
            ahora = posiciones_lider(pid)
        except Exception as e:
            log(f"{lid['nombre']}: no se pudo leer ({type(e).__name__})")
            continue
        previo = est["lider_previo"].get(pid, {})
        ign = set(est["ignorar"].get(pid, []))
        if primera or pid not in est["lider_previo"]:
            ign |= set(ahora)  # lo que ya estaba abierto al empezar no se copia
        for clave, p in ahora.items():
            nuestra = est["posiciones"].get(f"{pid}|{clave}")
            if clave in ign:
                continue
            if nuestra is None and lid.get("activo", True):
                px = precio(p["simbolo"])
                margen = min(est["efectivo"], est["efectivo"] * lid["margen_pct"] / 100)
                if margen * p["apal"] < 5:
                    continue
                qty = margen * p["apal"] / px
                est["efectivo"] -= margen + qty * px * TAKER
                est["posiciones"][f"{pid}|{clave}"] = {"lider": lid["nombre"], "pid": pid, "simbolo": p["simbolo"], "lado": p["lado"],
                                                      "qty": qty, "entrada": px, "margen": margen, "apal": p["apal"],
                                                      "ref_lider": p["cantidad"], "abierta": int(time.time())}
                anotar(EVENTOS, {"t": int(time.time()), "lider": lid["nombre"], "evento": "abre", "simbolo": p["simbolo"],
                                 "lado": p["lado"], "precio": px, "margen": margen, "apal": p["apal"]})
            elif nuestra is not None and abs(p["cantidad"] - nuestra["ref_lider"]) / nuestra["ref_lider"] > 0.01:
                px = precio(p["simbolo"])
                factor = p["cantidad"] / nuestra["ref_lider"]
                delta = nuestra["qty"] * (factor - 1)
                if delta > 0:  # agrega
                    margen_extra = delta * px / nuestra["apal"]
                    margen_extra = min(margen_extra, est["efectivo"])
                    delta = margen_extra * nuestra["apal"] / px
                    nuestra["entrada"] = (nuestra["entrada"] * nuestra["qty"] + px * delta) / (nuestra["qty"] + delta)
                    nuestra["qty"] += delta
                    nuestra["margen"] += margen_extra
                    est["efectivo"] -= margen_extra + delta * px * TAKER
                    evento = "agrega"
                else:  # reduce
                    parte = min(-delta, nuestra["qty"])
                    pnl = nuestra["lado"] * (px - nuestra["entrada"]) * parte
                    libera = nuestra["margen"] * parte / nuestra["qty"]
                    est["efectivo"] += libera + pnl - parte * px * TAKER
                    nuestra["qty"] -= parte
                    nuestra["margen"] -= libera
                    est["pnl_cerrado"] += pnl
                    evento = "reduce"
                nuestra["ref_lider"] = p["cantidad"]
                anotar(EVENTOS, {"t": int(time.time()), "lider": lid["nombre"], "evento": evento, "simbolo": p["simbolo"], "precio": px})
        # cierres: lo nuestro del líder que ya no está en sus posiciones
        for k in [k for k, v in est["posiciones"].items() if v["pid"] == pid and k.split("|", 1)[1] not in ahora]:
            v = est["posiciones"].pop(k)
            try:
                px = precio(v["simbolo"])
            except Exception:
                est["posiciones"][k] = v
                continue
            pnl = v["lado"] * (px - v["entrada"]) * v["qty"]
            pnl = max(pnl, -v["margen"])  # como mucho se pierde el margen de esa copia
            parte_lider = 0.10 * pnl if pnl > 0 else 0.0
            est["efectivo"] += v["margen"] + pnl - v["qty"] * px * TAKER - parte_lider
            est["pnl_cerrado"] += pnl - parte_lider
            est["cerradas"] += 1
            est["ganadas"] += pnl > 0
            anotar(EVENTOS, {"t": int(time.time()), "lider": v["lider"], "evento": "cierra", "simbolo": v["simbolo"], "lado": v["lado"],
                             "entrada": v["entrada"], "precio": px, "pnl_usdt": pnl - parte_lider,
                             "pnl_margen_pct": (pnl - parte_lider) / v["margen"] * 100 if v["margen"] else 0})
        est["ignorar"][pid] = sorted(ign & set(ahora))
        est["lider_previo"][pid] = {k: v["cantidad"] for k, v in ahora.items()}
    # equidad
    abierto = 0.0
    for v in est["posiciones"].values():
        try:
            px = precio(v["simbolo"])
            v["actual"] = px
        except Exception:
            px = v.get("actual", v["entrada"])
        abierto += v["margen"] + max(v["lado"] * (px - v["entrada"]) * v["qty"], -v["margen"])
    est["equidad_usdt"] = est["efectivo"] + abierto
    if not est["equidad"] or time.time() - est["equidad"][-1][0] >= 300:
        est["equidad"].append([int(time.time()), round(est["equidad_usdt"], 6)])
        est["equidad"] = est["equidad"][-3000:]
    return est


def seguimiento(cfg, est):
    """Cada 30 min: cierres nuevos de los 10 líderes (también los que esconden posiciones)."""
    if time.time() - est.get("ultimo_seguimiento", 0) < 1800:
        return est
    vistos = set(est.get("vistos", []))
    for lid in cfg["lideres"] + cfg.get("seguir", []):
        try:
            d = red("lead-portfolio/position-history", {"pageNumber": 1, "pageSize": 20, "portfolioId": lid["id"], "sort": "OPENING"})["data"]
        except Exception:
            continue
        for p in d.get("list") or []:
            clave = f"{lid['id']}|{p.get('positionId') or p.get('id')}"
            if p.get("closed") and p["closed"] / 1000 >= est["inicio"] and clave not in vistos:
                vistos.add(clave)
                anotar(SEGUIM, {"t": int(p["closed"] / 1000), "lider": lid["nombre"], "simbolo": p.get("symbol"), "lado": p.get("side"),
                                "roi_margen_pct": float(p.get("roi") or 0) * 100, "apal": p.get("leverage")})
        time.sleep(0.6)
    est["vistos"] = sorted(vistos)[-5000:]
    est["ultimo_seguimiento"] = int(time.time())
    return est


# ---------------------------------------------------------------- su método, operado por Claude
def fapi(ruta):
    return json.loads(urllib.request.urlopen(urllib.request.Request(FAPI + ruta, headers=H), timeout=20).read())


def alerta(lineas):
    """Manda los eventos de la vuelta a su Telegram como texto, en segundo plano y sin abrir ventanas."""
    if not lineas or not os.path.exists(TG):
        return
    os.makedirs(ALERTAS, exist_ok=True)
    ruta = os.path.join(ALERTAS, f"{int(time.time() * 1000)}.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("[Claude Code · su método en papel]\n" + "\n".join(lineas))
    py = os.path.join(os.path.dirname(sys.executable), "python.exe")

    def enviar():
        try:
            r = subprocess.run([py, "-I", TG, ruta], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            log(f"aviso a Telegram: {(r.stdout or r.stderr).strip()[-120:]}")
            if "ok" in (r.stdout or ""):
                os.remove(ruta)
        except Exception as e:
            log(f"aviso a Telegram falló ({type(e).__name__})")

    threading.Thread(target=enviar, daemon=True).start()


def metodo_inicial(m, tasa):
    return {"capital_usdt": m["capital_cop"] / tasa, "efectivo": m["capital_cop"] / tasa, "inicio": int(time.time()),
            "posiciones": {}, "cerradas": 0, "ganadas": 0, "pnl_cerrado": 0.0, "equidad": [], "liquidada": None,
            "elegibles": [], "elegibles_t": 0, "avisadas": {}}


def metodo_equidad(me):
    return me["efectivo"] + sum(p["margen"] + p["lado"] * (p["actual"] - p["entrada"]) * p["qty"] for p in me["posiciones"].values())


def metodo_abrir(me, m, s, px, lado, motivo, eventos):
    margen = min(me["efectivo"], metodo_equidad(me) * m["margen_pct"] / 100)
    if margen <= 0 or margen * m["apal"] < 5:  # mínimo de Binance: 5 USDT de nocional
        return
    entrada = px * (1 + lado * DESLIZ)
    qty = margen * m["apal"] / entrada
    costo = qty * entrada * TAKER
    me["efectivo"] -= margen + costo
    t = time.time()
    me["posiciones"][f"{s}|{'LARGO' if lado > 0 else 'CORTO'}|{int(t)}"] = {
        "simbolo": s, "lado": lado, "qty": qty, "entrada": entrada, "margen": margen, "apal": m["apal"], "abierta": int(t),
        "costo_entrada": costo, "financiacion": 0.0, "alto": entrada, "bajo": entrada, "actual": entrada, "maximo": entrada,
        "revisado": int(t // 60 + 1) * 60000, "ultimo_cobro": int(t * 1000), "revisar_cobro": 0, "motivo": motivo}
    anotar(METODO_EV, {"t": int(t), "evento": "abre", "simbolo": s, "lado": lado, "precio": entrada, "margen": margen,
                       "apal": m["apal"], "motivo": motivo})
    eventos.append(f"Abre {'LARGO' if lado > 0 else 'CORTO'} {s} a {entrada:.6g} ({m['apal']}×, margen {margen:.2f} USDT): {motivo}")


def metodo_cerrar(me, k, px, comision, motivo, eventos):
    p = me["posiciones"].pop(k)
    bruto = p["lado"] * (px - p["entrada"]) * p["qty"]
    costo = p["qty"] * px * comision
    me["efectivo"] += p["margen"] + bruto - costo
    neto = bruto - costo - p["costo_entrada"] + p["financiacion"]
    me["pnl_cerrado"] += neto
    me["cerradas"] += 1
    me["ganadas"] += neto > 0
    anotar(METODO_EV, {"t": int(time.time()), "evento": "cierra", "simbolo": p["simbolo"], "lado": p["lado"], "entrada": p["entrada"],
                       "precio": px, "margen": p["margen"], "neto_usdt": neto, "neto_margen_pct": neto / p["margen"] * 100,
                       "horas": (time.time() - p["abierta"]) / 3600, "motivo": motivo})
    eventos.append(f"{'Gana' if neto > 0 else 'Pierde'} {p['simbolo']} ({'largo' if p['lado'] > 0 else 'corto'}): "
                   f"{neto / p['margen'] * 100:+.1f} % del margen ({motivo})")


def metodo_vuelta(cfg, me):
    """Una vuelta de su método: revisa lo abierto con velas de 1 minuto, la cuenta en margen cruzado, y abre lo nuevo."""
    m = {**METODO_DEF, **cfg.get("metodo", {})}
    tasa = cfg.get("cop_usdt", 3177.85)
    if m["reiniciar_t"] > me["inicio"]:
        me = metodo_inicial(m, tasa)
        log("su método: cuenta reiniciada desde la pantalla")
    ahora, eventos = time.time(), []
    if ahora - me.get("elegibles_t", 0) > 6 * 3600:
        me["elegibles"] = sorted(s["symbol"] for s in fapi("exchangeInfo")["symbols"]
                                 if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING"
                                 and s.get("underlyingType", "COIN") == "COIN" and s["symbol"] not in ("BTCUSDT", "ETHUSDT"))
        me["elegibles_t"] = int(ahora)
    eleg = set(me["elegibles"])
    tick = {t["symbol"]: t for t in fapi("ticker/24hr") if t["symbol"] in eleg and int(t.get("closeTime") or 0) > (ahora - 600) * 1000}
    lista = set(m["monedas"])  # vacía = todas
    perdida_peor = 0.0
    for k, p in list(me["posiciones"].items()):
        if lista and p["simbolo"] not in lista and p["simbolo"] in tick:
            px = float(tick[p["simbolo"]]["lastPrice"])
            p["actual"] = px
            metodo_cerrar(me, k, px * (1 - p["lado"] * DESLIZ), TAKER, "fuera de su lista: solo opera " + ", ".join(sorted(lista)), eventos)
            continue
        try:
            v = fapi(f"klines?symbol={p['simbolo']}&interval=1m&startTime={p['revisado']}&limit=200")
        except Exception:
            v = []
        if v:
            alto, bajo = max(float(x[2]) for x in v), min(float(x[3]) for x in v)
            p["actual"], p["revisado"] = float(v[-1][4]), int(v[-1][0])  # la última vela puede seguir abierta: se relee
        else:
            alto = bajo = p["actual"] = float(tick[p["simbolo"]]["lastPrice"]) if p["simbolo"] in tick else p["actual"]
        p["alto"], p["bajo"] = max(p["alto"], alto), min(p["bajo"], bajo)
        if ahora >= p["revisar_cobro"]:
            try:
                for c in fapi(f"fundingRate?symbol={p['simbolo']}&startTime={p['ultimo_cobro'] + 1}&limit=50"):
                    pago = -p["lado"] * float(c["fundingRate"]) * p["qty"] * p["actual"]
                    me["efectivo"] += pago
                    p["financiacion"] += pago
                    p["ultimo_cobro"] = int(c["fundingTime"])
            except Exception:
                pass
            p["revisar_cobro"] = ahora + 300
        if p["lado"] < 0:
            giro = p["entrada"] * (1 + m["alza_pct"] / 100) if m["alza_pct"] else None
            if giro and alto >= giro:  # si en el mismo minuto toca las dos cosas, cuenta lo peor: el giro
                metodo_cerrar(me, k, giro * (1 + DESLIZ), TAKER, f"preventiva: subió +{m['alza_pct']:g} %", eventos)
                metodo_abrir(me, m, p["simbolo"], giro, 1, "preventiva al alza: sigue subiendo", eventos)
            elif bajo <= p["entrada"] * (1 - m["objetivo_pct"] / 100):
                metodo_cerrar(me, k, p["entrada"] * (1 - m["objetivo_pct"] / 100), MAKER, f"objetivo −{m['objetivo_pct']:g} %", eventos)
            elif ahora - p["abierta"] >= m["max_horas"] * 3600:
                metodo_cerrar(me, k, p["actual"] * (1 + DESLIZ), TAKER, f"{m['max_horas']} h sin llegar al objetivo", eventos)
            else:
                perdida_peor += max(0.0, (alto - p["entrada"]) * p["qty"])
                p["peor"] = alto
        else:
            nivel = p["maximo"] * (1 - m["seguimiento_pct"] / 100)
            if bajo <= nivel:
                metodo_cerrar(me, k, nivel * (1 - DESLIZ), TAKER, f"cayó {m['seguimiento_pct']:g} % desde su máximo", eventos)
            elif ahora - p["abierta"] >= m["max_largo_h"] * 3600:
                metodo_cerrar(me, k, p["actual"] * (1 - DESLIZ), TAKER, f"{m['max_largo_h']} h", eventos)
            else:
                p["maximo"] = max(p["maximo"], alto)
                perdida_peor += max(0.0, (p["entrada"] - bajo) * p["qty"])
                p["peor"] = bajo
    # margen cruzado: si al peor precio del minuto las pérdidas abiertas alcanzan el saldo, la cuenta se liquida entera
    if me["posiciones"] and me["efectivo"] + sum(p["margen"] for p in me["posiciones"].values()) - perdida_peor <= 0:
        for k, p in list(me["posiciones"].items()):
            metodo_cerrar(me, k, p.get("peor", p["actual"]), TAKER, "cuenta liquidada", eventos)
        me["efectivo"] = max(0.0, me["efectivo"])
        me["liquidada"] = int(ahora)
        eventos.append("CUENTA LIQUIDADA: las pérdidas abiertas alcanzaron el saldo (margen cruzado). El método se detiene.")
    if m["activo"] and not me.get("liquidada"):
        abiertas = {p["simbolo"] for p in me["posiciones"].values()}
        candidatos = []
        for s, t in tick.items():
            cambio, ultimo, alto24 = float(t["priceChangePercent"]), float(t["lastPrice"]), float(t["highPrice"])
            if cambio < m["umbral_pct"] or (lista and s not in lista):
                continue
            if ahora - me["avisadas"].get(s, 0) > 12 * 3600:
                me["avisadas"][s] = int(ahora)
                eventos.append(f"Alerta: {s} sube {cambio:+.0f} % en 24 h (máximo {alto24:.6g}, ahora {ultimo:.6g})")
            if s not in abiertas and ultimo <= alto24 * (1 - m["giro_pct"] / 100):
                candidatos.append((cambio, s, ultimo, alto24))
        for cambio, s, ultimo, alto24 in sorted(candidatos, reverse=True):
            if len(me["posiciones"]) >= m["max_abiertas"]:
                break
            metodo_abrir(me, m, s, ultimo, -1, f"subió {cambio:+.0f} % en 24 h y ya bajó {(1 - ultimo / alto24) * 100:.1f} % desde el máximo", eventos)
    me["avisadas"] = {s: t for s, t in me["avisadas"].items() if ahora - t < 24 * 3600}
    me["equidad_usdt"] = metodo_equidad(me)
    if not me["equidad"] or ahora - me["equidad"][-1][0] >= 300:
        me["equidad"].append([int(ahora), round(me["equidad_usdt"], 6)])
        me["equidad"] = me["equidad"][-6000:]
    if m["alertas"]:
        alerta(eventos)
    return me


def seccion_metodo(cfg, tasa):
    m = {**METODO_DEF, **cfg.get("metodo", {})}
    me = leer(METODO, None)
    e = html.escape
    if not me:
        return "<section><h2>Su método (迪亚马特), operado por Claude</h2><p>Arranca en la próxima vuelta (un minuto).</p></section>"
    cap = me["capital_usdt"] * tasa
    eq = me.get("equidad_usdt", me["capital_usdt"]) * tasa
    dias = max(1 / 24, (time.time() - me["inicio"]) / 86400)
    por_dia, previo = {}, me["capital_usdt"]
    for t, v in me.get("equidad", []):  # cada día se mide desde el cierre del anterior
        d = dt.datetime.fromtimestamp(t, COL).strftime("%d/%m")
        por_dia.setdefault(d, [previo, v])[1] = v
        previo = v
    hoy = dt.datetime.now(COL).strftime("%d/%m")
    if hoy in por_dia:
        por_dia[hoy][1] = me.get("equidad_usdt", por_dia[hoy][1])
    diario = "".join(f"<tr><td>{d}</td><td class='{clase((b - a) * tasa)}'>{cop((b - a) * tasa, True)} COP</td>"
                     f"<td>{(b / a - 1) * 100 if a else 0:+.2f} %</td></tr>" for d, (a, b) in list(por_dia.items())[-14:])
    pos = "".join(
        f"<tr><td>{e(p['simbolo'])}</td><td>{'Largo' if p['lado'] > 0 else 'Corto'} {p['apal']}×</td><td>{p['entrada']:.6g}</td>"
        f"<td>{p['actual']:.6g}</td><td>{p['entrada'] * (1 - m['objetivo_pct'] / 100):.6g}</td>"
        f"<td>{max(0.0, ((p['alto'] / p['entrada'] - 1) if p['lado'] < 0 else (1 - p['bajo'] / p['entrada'])) * 100 * p['apal']):.0f} %</td>"
        f"<td class='{clase(p['lado'] * (p['actual'] - p['entrada']) * p['qty'] * tasa)}'>{cop(p['lado'] * (p['actual'] - p['entrada']) * p['qty'] * tasa, True)}</td></tr>"
        for p in me["posiciones"].values()) or "<tr><td colspan=7>Sin posiciones: abre cuando una moneda sube ≥ 30 % en 24 h y ya bajó 3 % desde su máximo.</td></tr>"
    cier = "".join(
        f"<tr><td>{dt.datetime.fromtimestamp(x['t'], COL):%d/%m %H:%M}</td><td>{e(x['simbolo'])}</td><td>{e(x['motivo'])}</td>"
        f"<td>{x['neto_margen_pct']:+.1f} %</td><td class='{clase(x['neto_usdt'] * tasa)}'>{cop(x['neto_usdt'] * tasa, True)}</td></tr>"
        for x in reversed([y for y in filas_jsonl(METODO_EV, 600) if y.get("evento") == "cierra"][-20:])) or "<tr><td colspan=5>Todavía no hay cierres.</td></tr>"
    estado = (f"<b class='pierde'>liquidada el {dt.datetime.fromtimestamp(me['liquidada'], COL):%d/%m %H:%M}</b>" if me.get("liquidada")
              else "<b class='gana'>operando</b>" if m["activo"] else "<b>en pausa</b>")
    return f"""<section><h2>Su método (迪亚马特), operado por Claude · cuenta aparte de {cop(cap)} COP</h2>
<div class="cifras"><div class="c">Saldo<b>{cop(eq)} COP</b></div><div class="c">Desde el inicio<b class="{clase(eq - cap)}">{(eq / cap - 1) * 100:+.2f} %</b></div>
<div class="c">Por día (media)<b>{f"{((max(eq, 0.01) / cap) ** (1 / dias) - 1) * 100:+.2f} %" if dias >= 1 else f"lleva {dias * 24:.1f} h"}</b></div>
<div class="c">Cerradas<b>{me['cerradas']} · {me['ganadas'] / max(1, me['cerradas']) * 100:.0f} % ganadas</b></div><div class="c">Estado{estado}</div></div>
<h2>Posiciones abiertas</h2><table><tr><th>Moneda</th><th>Lado</th><th>Entrada</th><th>Ahora</th><th>Objetivo</th><th>En contra máx (margen)</th><th>Resultado (COP)</th></tr>{pos}</table>
<h2 style="margin-top:14px">Cierres</h2><table><tr><th>Hora</th><th>Moneda</th><th>Por qué</th><th>Margen</th><th>Resultado (COP)</th></tr>{cier}</table>
<h2 style="margin-top:14px">Por día</h2><table><tr><th>Día</th><th>Resultado</th><th>%</th></tr>{diario}</table>
<form method="post" action="/metodo" style="margin-top:14px"><table>
<tr><td>Monedas que opera (separadas por coma; vacío = todas)</td><td><input type="text" name="monedas" value="{e(', '.join(m['monedas']))}" style="width:220px"></td></tr>
<tr><td>Margen por operación (% del saldo)</td><td><input type="number" name="margen_pct" value="{m['margen_pct']:g}" min="1" max="100" step="1"> %</td></tr>
<tr><td>Máximo de posiciones a la vez</td><td><input type="number" name="max_abiertas" value="{m['max_abiertas']}" min="1" max="20" step="1"></td></tr>
<tr><td>Preventiva al alza: si sube este % sobre la entrada, corta y apuesta al alza (0 = apagada)</td><td><input type="number" name="alza_pct" value="{m['alza_pct']:g}" min="0" max="200" step="1"> %</td></tr>
<tr><td>El largo de la preventiva sale al caer este % desde su máximo</td><td><input type="number" name="seguimiento_pct" value="{m['seguimiento_pct']:g}" min="1" max="90" step="1"> %</td></tr>
<tr><td>Operar</td><td><input type="checkbox" name="activo" {'checked' if m['activo'] else ''}></td></tr>
<tr><td>Avisos a Telegram</td><td><input type="checkbox" name="alertas" {'checked' if m['alertas'] else ''}></td></tr></table>
<p><button>Guardar</button> <button name="reiniciar" value="1" style="background:#6b7280">Reiniciar la cuenta con {cop(m['capital_cop'])} COP</button></p>
<div class="nota">Regla medida en su historial: corto a {m['apal']}× cuando una moneda subió ≥ {m['umbral_pct']:g} % en 24 h y ya bajó {m['giro_pct']:g} % desde su máximo;
cierra al caer {m['objetivo_pct']:g} %; sin stop; margen cruzado. Solo opera las monedas de la lista: BMT dio 20 de 20 en su historial y
18 de 18 con esta regla desde marzo de 2025, en rachas (unas pocas por mes cuando se dispara; meses sin ninguna). En otras monedas, como MYX o
BTR (que se multiplicaron ×3 a ×8), la misma regla borra la cuenta en margen cruzado: por eso se liquida entera si las pérdidas abiertas alcanzan el saldo.</div></form></section>"""


# ---------------------------------------------------------------- pantalla
def filas_jsonl(ruta, n=40):
    try:
        return [json.loads(x) for x in open(ruta, encoding="utf-8").read().splitlines()[-n:] if x.strip()]
    except Exception:
        return []


def cop(x, signo=False):
    """Pesos con punto de miles, como en Colombia; sin «−0»."""
    if abs(x) < 0.5:
        return "0"
    t = f"{x:+,.0f}" if signo else f"{x:,.0f}"
    return t.replace(",", ".")


def clase(x):
    return "gana" if x >= 0.5 else "pierde" if x <= -0.5 else ""


def pagina():
    cfg = leer(CONFIG, {})
    est = leer(ESTADO, {})
    tasa = cfg.get("cop_usdt", 3177.85)
    cap = cfg.get("capital_cop", 40000)
    eq = est.get("equidad_usdt", cap / tasa) * tasa
    hoy0 = dt.datetime.now(COL).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    eqs = est.get("equidad", [])
    base_hoy = next((v for t, v in eqs if t >= hoy0), eqs[-1][1] if eqs else cap / tasa) * tasa
    dias = max(1 / 24, (time.time() - est.get("inicio", time.time())) / 86400)
    e = html.escape
    pos = "".join(
        f"<tr><td>{e(v['lider'])}</td><td>{e(v['simbolo'])}</td><td>{'Largo' if v['lado'] > 0 else 'Corto'} {v['apal']}×</td>"
        f"<td>{v['entrada']:.6g}</td><td>{v.get('actual', v['entrada']):.6g}</td>"
        f"<td class='{'gana' if v['lado'] * (v.get('actual', v['entrada']) - v['entrada']) >= 0 else 'pierde'}'>"
        f"{cop(v['lado'] * (v.get('actual', v['entrada']) - v['entrada']) * v['qty'] * tasa, True)}</td></tr>"
        for v in est.get("posiciones", {}).values()) or "<tr><td colspan=6>Sin copias abiertas: se abren cuando un líder abre una posición nueva.</td></tr>"
    cier = "".join(
        f"<tr><td>{dt.datetime.fromtimestamp(x['t'], COL):%d/%m %H:%M}</td><td>{e(x['lider'])}</td><td>{e(x['simbolo'])}</td>"
        f"<td class='{clase(x['pnl_usdt'] * tasa)}'>{cop(x['pnl_usdt'] * tasa, True)}</td></tr>"
        for x in reversed([y for y in filas_jsonl(EVENTOS, 400) if y.get("evento") == "cierra"][-20:])) or "<tr><td colspan=4>Todavía no hay cierres.</td></tr>"
    seg = {}
    for x in filas_jsonl(SEGUIM, 5000):
        s = seg.setdefault(x["lider"], [0, 0, 0.0])
        s[0] += 1
        s[1] += x["roi_margen_pct"] > 0
        s[2] += x["roi_margen_pct"]
    segt = "".join(f"<tr><td>{e(k)}</td><td>{v[0]}</td><td>{v[1] / v[0] * 100:.0f} %</td><td>{v[2] / v[0]:+.1f} %</td></tr>"
                   for k, v in sorted(seg.items(), key=lambda kv: -kv[1][2] / max(1, kv[1][0]))) or \
        "<tr><td colspan=4>Se llena cada 30 minutos con los cierres nuevos de los 10 líderes.</td></tr>"
    lideres = "".join(
        f"<tr><td>{e(l['nombre'])}</td><td>{'visible' if l.get('visible', True) else 'esconde sus posiciones'}</td>"
        f"<td><input type='number' name='m_{e(l['id'])}' value='{l['margen_pct']}' min='1' max='100' step='1'> %</td>"
        f"<td><input type='checkbox' name='a_{e(l['id'])}' {'checked' if l.get('activo', True) else ''}></td></tr>"
        for l in cfg.get("lideres", []))
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta http-equiv="refresh" content="30">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Copy trading en papel</title><style>
:root{{--fondo:#f6f7f9;--carta:#fff;--texto:#1d2330;--suave:#5b6474;--verde:#13804b;--rojo:#c0392b;--borde:#e3e6eb}}
[hidden]{{display:none!important}} body{{margin:0;padding:24px;font:15px/1.45 system-ui,Segoe UI,sans-serif;background:var(--fondo);color:var(--texto)}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:var(--suave);margin-bottom:20px}}
.cifras{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:20px}}
.c{{background:var(--carta);border:1px solid var(--borde);border-radius:10px;padding:14px}} .c b{{display:block;font-size:22px}}
section{{background:var(--carta);border:1px solid var(--borde);border-radius:10px;padding:14px;margin-bottom:16px;overflow-x:auto}}
h2{{font-size:16px;margin:0 0 10px}} table{{border-collapse:collapse;width:100%}} td,th{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--borde);white-space:nowrap}}
.gana{{color:var(--verde)}} .pierde{{color:var(--rojo)}} input[type=number]{{width:70px}} button{{padding:8px 16px;border-radius:8px;border:0;background:#1d4ed8;color:#fff;font-size:15px}}
.nota{{color:var(--suave);font-size:13px;margin-top:8px}}</style></head><body>
<h1>Trading en papel</h1><div class="sub">Su método operado por Claude y la copia de los líderes de Binance, con precios reales. Papel: no se mueve dinero.
Se actualiza cada 30 s · {dt.datetime.now(COL):%d/%m/%Y %H:%M} Colombia</div>
{seccion_metodo(cfg, tasa)}
<h2 style="margin:18px 0 10px">Copia de los líderes · cuenta aparte de {cop(cap)} COP</h2>
<div class="cifras"><div class="c">Saldo<b>{cop(eq)} COP</b></div><div class="c">Desde el inicio<b class="{clase(eq - cap)}">{(eq / cap - 1) * 100:+.2f} %</b></div>
<div class="c">Hoy<b class="{clase(eq - base_hoy)}">{cop(eq - base_hoy, True)} COP</b></div>
<div class="c">Por día (media)<b>{f"{((eq / cap) ** (1 / dias) - 1) * 100:+.2f} %" if dias >= 1 else f"lleva {dias * 24:.1f} h"}</b></div>
<div class="c">Cerradas<b>{est.get('cerradas', 0)} · {est.get('ganadas', 0) / max(1, est.get('cerradas', 0)) * 100:.0f} % ganadas</b></div></div>
<section><h2>Copias abiertas</h2><table><tr><th>Líder</th><th>Moneda</th><th>Lado</th><th>Entrada</th><th>Ahora</th><th>Resultado (COP)</th></tr>{pos}</table></section>
<section><h2>Últimos cierres</h2><table><tr><th>Hora</th><th>Líder</th><th>Moneda</th><th>Resultado (COP)</th></tr>{cier}</table></section>
<section><h2>Riesgo por líder (usted decide)</h2><form method="post" action="/riesgo"><table><tr><th>Líder</th><th>Posiciones</th>
<th>Margen por copia (% del saldo)</th><th>Copiar</th></tr>{lideres}</table><p><button>Guardar riesgo</button></p>
<div class="nota">Margen por copia: cuánto del saldo libre se pone en cada posición nueva del líder, con su mismo apalancamiento.
Más margen, más ganancia y más pérdida: con 20 % o más, una mala racha puede llevar el saldo cerca de cero.</div></form></section>
<section><h2>¿Siguen ganando los 10 mejores? (cierres desde que arrancó)</h2><table><tr><th>Líder</th><th>Cierres</th><th>Ganadas</th><th>Resultado medio sobre el margen</th></tr>{segt}</table></section>
</body></html>"""


class Pantalla(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        cuerpo = pagina().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        datos = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
        if self.path == "/metodo":
            with CANDADO:
                cfg = leer(CONFIG, {})
                m = cfg.setdefault("metodo", {})
                for campo, lo, hi in (("margen_pct", 1, 100), ("max_abiertas", 1, 20), ("alza_pct", 0, 200), ("seguimiento_pct", 1, 90)):
                    if datos.get(campo):
                        m[campo] = max(lo, min(hi, float(datos[campo][0])))
                m["max_abiertas"] = int(m.get("max_abiertas", METODO_DEF["max_abiertas"]))
                if "monedas" in datos or "margen_pct" in datos:  # el campo vacío no llega en el formulario: vacío = todas
                    nombres = (datos.get("monedas") or [""])[0].replace(",", " ").upper().split()
                    m["monedas"] = [x if x.endswith("USDT") else x + "USDT" for x in nombres]
                m["activo"], m["alertas"] = "activo" in datos, "alertas" in datos
                if datos.get("reiniciar"):
                    m["reiniciar_t"] = int(time.time())
                escribir(CONFIG, cfg)
            log("su método, cambiado desde la pantalla: " + json.dumps(m, ensure_ascii=False))
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        with CANDADO:
            cfg = leer(CONFIG, {})
            for l in cfg.get("lideres", []):
                v = datos.get(f"m_{l['id']}")
                if v:
                    l["margen_pct"] = max(1, min(100, float(v[0])))
                l["activo"] = f"a_{l['id']}" in datos
            escribir(CONFIG, cfg)
        log("riesgo cambiado desde la pantalla: " + ", ".join(f"{l['nombre']} {l['margen_pct']} % {'sí' if l['activo'] else 'no'}" for l in cfg["lideres"]))
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()


class Servidor(ThreadingHTTPServer):
    allow_reuse_address = False  # en Windows, reutilizar permite dos servidores en el mismo puerto


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
    if sys.stdout is None:  # pythonw: sin consola
        sys.stdout = sys.stderr = open(os.devnull, "w")
    una = "--una-vez" in sys.argv
    if not una and not puerto_libre():
        log("ya hay un copiador corriendo (puerto ocupado): salgo")
        return
    if not una:
        srv = Servidor(("127.0.0.1", PUERTO), Pantalla)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log(f"pantalla en http://127.0.0.1:{PUERTO}")
    while True:
        try:
            with CANDADO:
                cfg = leer(CONFIG, {})
                est = leer(ESTADO, None) or estado_inicial(cfg)
            est = vuelta(cfg, est)
            est = seguimiento(cfg, est)
            with CANDADO:
                escribir(ESTADO, est)
        except Exception:
            log("error en la vuelta: " + traceback.format_exc().replace("\n", " | ")[:1500])
        try:
            with CANDADO:
                cfg = leer(CONFIG, {})
                m = {**METODO_DEF, **cfg.get("metodo", {})}
                me = leer(METODO, None) or metodo_inicial(m, cfg.get("cop_usdt", 3177.85))
            me = metodo_vuelta(cfg, me)
            with CANDADO:
                escribir(METODO, me)
        except Exception:
            log("error en su método: " + traceback.format_exc().replace("\n", " | ")[:1500])
        if una or os.path.exists(PARAR):
            if os.path.exists(PARAR):
                os.remove(PARAR)
                log("PARAR: salgo")
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
