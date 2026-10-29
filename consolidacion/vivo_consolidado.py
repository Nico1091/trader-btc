"""Agente consolidado en vivo (29/10/2026): opera en papel y en tiempo real la configuración elegida por la prueba total.

Pedido de Nicolás: «tú como agente debes operar primero y mostrarme cada resultado… un programa que me muestre los
operativos en tiempo real… para ver si es verdad que se reflejan las ganancias en libro y reales».

Cada minuto, para cada moneda de la cartera, el motor de las pruebas (sistema.Dia, el mismo del simulador) lee las velas del
día hasta ese momento y da las operaciones del LIBRO. Con las MISMAS operaciones y el mismo tamaño se llevan dos cuentas:
- LIBRO: los precios que dan las velas (lo que dicen las pruebas);
- REAL: lo que el agente de verdad podía hacer en el instante en que lo vio:
  · órdenes límite (P05b, P05c, N9): se llenan al nivel, como en el libro, solo si el agente estaba operando cuando salió la
    señal (si el equipo estaba apagado o dormido, la operación queda solo en el libro: «no vista a tiempo»);
  · compras a mercado (P11, N8 a las 00:00 UTC): al precio del momento en que el agente las ve, con deslizamiento;
  · stop del 3 % (P11, N8): orden en el libro de órdenes, se llena en el nivel con deslizamiento;
  · salida por cierre de 15 min y cierre del día: a mercado cuando el agente las ve, al precio de ese instante.
Tamaño: riesgo × saldo / distancia al stop, con tope de apalancamiento y de posiciones (agente_consolidado.json).
Costos: creador 0,02 %, tomador 0,05 %, financiación 0,017 % por operación y deslizamiento 0,03 % en lo que va a mercado.
Estado: C:\\Users\\ni109\\Ingresos\\copia-papel\\consolidado.json (lo lee la pantalla de operaciones en tiempo real).
Uso: pythonw vivo_consolidado.py (sin ventana) · python vivo_consolidado.py --una-vez (una vuelta, para probar)
Parar: crear C:\\Users\\ni109\\Ingresos\\copia-papel\\PARAR-CONSOLIDADO."""
import datetime as dt
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import sistema  # noqa: E402

CONF = os.path.join(AQUI, "agente_consolidado.json")
RAIZ = os.environ.get("COPIA_PAPEL") or r"C:\Users\ni109\Ingresos\copia-papel"
ESTADO = os.path.join(RAIZ, "consolidado.json")
EVENTOS = os.path.join(RAIZ, "consolidado.jsonl")
REGISTRO = os.path.join(RAIZ, "consolidado.log")
PARAR = os.path.join(RAIZ, "PARAR-CONSOLIDADO")
TG = os.path.join(os.path.dirname(RAIZ), "tg_pc.py")
UTC = dt.timezone.utc
COL = dt.timezone(dt.timedelta(hours=-5))
COP = 3177.85
CREADOR, TOMADOR, FIN, DESLIZ = 0.0002, 0.0005, 0.00017, 0.0003
MERCADO = ("P11", "N8")  # entran a mercado a las 00:00 UTC; las demás con orden límite


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def escribir(ruta, datos):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def anotar(fila):
    with open(EVENTOS, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def avisar(lineas):
    """Texto a su Telegram, en segundo plano y sin abrir ventanas."""
    if not lineas or not os.path.exists(TG):
        return
    ruta = os.path.join(RAIZ, "alertas", f"c{int(time.time() * 1000)}.txt")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("[Claude Code · agente consolidado en papel]\n" + "\n".join(lineas))
    py = os.path.join(os.path.dirname(sys.executable), "python.exe")

    def enviar():
        try:
            r = subprocess.run([py, "-I", TG, ruta], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            log("aviso a Telegram: " + (r.stdout or r.stderr).strip()[-80:])
            if "ok" in (r.stdout or ""):
                os.remove(ruta)
        except Exception as e:
            log(f"aviso a Telegram falló ({type(e).__name__})")

    threading.Thread(target=enviar, daemon=True).start()


class FuenteViva:
    """BinanceFut con caché: diarias una vez al día, 1 h una vez por hora, 1 min solo lo nuevo. Mismas velas que sin caché."""

    def __init__(self, activo):
        self.base, self.cache, self.leido = sistema.BinanceFut(activo), {}, {}

    def velas(self, gran, ini, fin):
        k = (gran, ini)
        v = self.cache.get(k)
        ahora = time.time()
        if v is None:
            v = self.base.velas(gran, ini, fin)
            self.leido[k] = ahora
        elif v:
            t_ult = v[-1][0]
            cerrada = self.leido[k] >= t_ult + gran  # la última vela ya estaba cerrada cuando se leyó
            if ahora >= t_ult + gran and (not cerrada or t_ult + gran < fin):
                nuevas = self.base.velas(gran, t_ult, fin)
                if nuevas:
                    v = [x for x in v if x[0] < nuevas[0][0]] + nuevas
                    self.leido[k] = ahora
        self.cache[k] = v
        if len(self.cache) > 8:  # solo las claves de hoy y ayer
            for kk in sorted(self.cache, key=lambda kk: kk[1])[:-8]:
                self.cache.pop(kk, None)
                self.leido.pop(kk, None)
        return [x for x in v if ini <= x[0] < fin]


def precios_vivos():
    u = "https://fapi.binance.com/fapi/v1/ticker/price"
    x = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "sistema"}), timeout=15).read())
    return {d["symbol"]: float(d["price"]) for d in x}


def estado_inicial(conf):
    cap = conf["capital_cop"] / COP
    return {"inicio": int(time.time()), "capital_usdt": cap, "real": cap, "libro": cap, "maximo": cap, "abiertas": {},
            "cerradas": [], "vistas": {}, "notas": {}, "contexto": {}, "equidad": [], "ultima_vuelta": 0, "corrida_desde": 0,
            "parada": None, "dias": {}, "pendientes_libro": {}}


def clave(dia, activo, o):
    return f"{dia}|{activo}|{o['estrategia']}|{int(o['senal'])}"


def costo(o_estr, salida_mercado=True):
    return (TOMADOR if o_estr in MERCADO else CREADOR) + (TOMADOR if salida_mercado else CREADOR) + FIN


def cerrar_pos(est, k, px_real, t_real, motivo, eventos, px_libro=None):
    p = est["abiertas"].pop(k)
    c = p["noc"] * costo(p["estrategia"])
    g_real = p["noc"] * p["lado"] * (px_real / p["pe_real"] - 1) - c
    est["real"] += max(g_real, -est["real"])
    fila = {"k": k, "activo": p["activo"], "estrategia": p["estrategia"], "lado": p["lado"], "t0": p["t_real"], "t1": int(t_real),
            "pe_libro": p["pe_libro"], "pe_real": p["pe_real"], "px_real": px_real, "noc": p["noc"], "g_real": g_real,
            "motivo": motivo, "px_libro": px_libro, "g_libro": None}
    if px_libro is not None:
        fila["g_libro"] = p["noc"] * p["lado"] * (px_libro / p["pe_libro"] - 1) - c
        est["libro"] += max(fila["g_libro"], -est["libro"])
    else:
        est["pendientes_libro"][k] = fila  # el libro de una salida «tiempo» se completa con el día cerrado
    est["cerradas"].append(fila)
    est["cerradas"] = est["cerradas"][-400:]
    d = dt.datetime.fromtimestamp(t_real, COL).strftime("%Y-%m-%d")
    est["dias"].setdefault(d, {"real": 0.0, "libro": 0.0, "ops": 0})
    est["dias"][d]["real"] += g_real
    est["dias"][d]["libro"] += fila["g_libro"] or 0.0
    est["dias"][d]["ops"] += 1
    anotar(dict(fila, evento="cierra"))
    eventos.append(f"{'Gana' if g_real > 0 else 'Pierde'} {p['activo']} {p['estrategia']} "
                   f"({'largo' if p['lado'] > 0 else 'corto'}): real {g_real * COP:+,.0f} COP"
                   + (f" · libro {fila['g_libro'] * COP:+,.0f} COP" if fila["g_libro"] is not None else " · libro al cierre del día")
                   + f" ({motivo})")


def vuelta(est, conf, fuentes):
    ahora = time.time()
    hoy = dt.datetime.fromtimestamp(ahora, UTC).date()
    d0 = int(dt.datetime.combine(hoy, dt.time(), UTC).timestamp())
    eventos = []
    if ahora - est["ultima_vuelta"] > 150:  # el agente estuvo apagado o dormido: desde aquí vuelve a ver las señales
        est["corrida_desde"] = int(ahora)
        if est["ultima_vuelta"]:
            log(f"el agente estuvo detenido desde {dt.datetime.fromtimestamp(est['ultima_vuelta'], COL):%d/%m %H:%M}")
    precios = precios_vivos()
    # 0) libro de los días anteriores que quedó pendiente (salidas por «tiempo»)
    for k, fila in list(est["pendientes_libro"].items()):
        dia_s, a, e, s = k.split("|")
        dia = dt.date.fromisoformat(dia_s)
        if dia >= hoy:
            continue
        try:
            D = sistema.Dia(fuentes[a], dia)
            o = next((o for o in D.todo()[0] if o["estrategia"] == e and int(o["senal"]) == int(s)), None)
        except Exception:
            continue
        if o:
            c = fila["noc"] * costo(e)
            fila["px_libro"] = o["px"]
            fila["g_libro"] = fila["noc"] * fila["lado"] * (o["px"] / fila["pe_libro"] - 1) - c
            est["libro"] += max(fila["g_libro"], -est["libro"])
            dd = dt.datetime.fromtimestamp(fila["t1"], COL).strftime("%Y-%m-%d")
            est["dias"].setdefault(dd, {"real": 0.0, "libro": 0.0, "ops": 0})["libro"] += fila["g_libro"]
            for x in est["cerradas"]:
                if x["k"] == k:
                    x.update(px_libro=o["px"], g_libro=fila["g_libro"])
            anotar({"evento": "libro", "k": k, "px_libro": o["px"], "g_libro": fila["g_libro"]})
        est["pendientes_libro"].pop(k)
    # 1) lo que da el motor hoy, moneda por moneda
    libro = {}
    for a, fuente in fuentes.items():
        permitidas = conf["estrategias_btc"] if a == "BTC" else conf["estrategias_resto"]
        try:
            D = sistema.Dia(fuente, hoy, int(ahora))
            ops, notas = D.todo()
        except Exception as e:
            est["notas"][a] = [f"sin lectura todavía ({type(e).__name__})"]
            continue
        est["contexto"][a] = {"ctx": D.ctx, "ap": D.ap, "atr": D.atr, "sma50": D.sma50, "cierre_ayer": D.cierre_ayer}
        est["notas"][a] = [n for n in notas if n.split(":")[0].split(" ")[0] in permitidas]
        for o in ops:
            if o["estrategia"] in permitidas:
                libro[clave(hoy, a, o)] = (a, o, D)
    # 2) posiciones abiertas: salidas
    for k, p in list(est["abiertas"].items()):
        sim = p["activo"] + "USDT"
        vivo = precios.get(sim, p.get("actual", p["pe_real"]))
        p["actual"] = vivo
        if k in libro:
            a, o, D = libro[k]
            if o["motivo"] == "stop" and p["estrategia"] in MERCADO:  # stop del 3 %: orden puesta, se llena en el nivel
                cerrar_pos(est, k, o["px"] * (1 - p["lado"] * DESLIZ), o["salida"], "stop del 3 %", eventos, px_libro=o["px"])
            elif o["motivo"] == "stop":  # cierre de 15 min contra la referencia: a mercado al verlo
                cerrar_pos(est, k, vivo * (1 - p["lado"] * DESLIZ), ahora, "cierre de 15 min contra la apertura", eventos, px_libro=o["px"])
            elif ahora >= d0 + 86400 - 60:
                cerrar_pos(est, k, vivo * (1 - p["lado"] * DESLIZ), ahora, "cierre del día", eventos)
            else:
                p["libro_actual"] = o["px"]
        elif not k.startswith(str(hoy)):  # posición de un día anterior que no se cerró a tiempo (equipo apagado)
            cerrar_pos(est, k, vivo * (1 - p["lado"] * DESLIZ), ahora, "cierre del día, atrasado", eventos)
    # 3) entradas nuevas (mismas operaciones que el libro; REAL solo si el agente estaba operando al salir la señal)
    for k, (a, o, D) in sorted(libro.items(), key=lambda kv: kv[1][1]["entrada"]):
        if k in est["vistas"]:
            continue
        est["vistas"][k] = int(ahora)
        if est["parada"]:
            continue
        en_mercado = o["estrategia"] in MERCADO
        vista = o["senal"] >= est["corrida_desde"] - 60
        if not vista:
            anotar({"evento": "no vista a tiempo", "k": k, "activo": a, "estrategia": o["estrategia"], "pe_libro": o["pe"]})
            eventos.append(f"{a} {o['estrategia']}: la señal salió con el agente detenido; queda solo en el libro")
            continue
        if len(est["abiertas"]) >= conf["max_abiertas"]:
            anotar({"evento": "omitida", "k": k, "motivo": "posiciones a la vez completas"})
            continue
        dias_hoy = est["dias"].get(dt.datetime.fromtimestamp(ahora, COL).strftime("%Y-%m-%d"), {"real": 0.0})
        if dias_hoy["real"] <= -conf["paradas"]["dia"] * est["real"]:
            anotar({"evento": "omitida", "k": k, "motivo": "tope de pérdida del día"})
            continue
        ref = sistema.referencia(D, o)
        dist = abs(o["pe"] - ref) / o["pe"] if ref else 0.03
        noc = conf["riesgo"] * est["real"] / max(dist, 1e-6)
        noc = min(noc, conf["apal_max"] * est["real"] - sum(x["noc"] for x in est["abiertas"].values()))
        if noc < 5:
            continue
        vivo = precios.get(a + "USDT", o["pe"])
        pe_real = vivo * (1 + o["lado"] * DESLIZ) if en_mercado else o["pe"]
        est["abiertas"][k] = {"activo": a, "estrategia": o["estrategia"], "lado": o["lado"], "senal": o["senal"],
                              "t_libro": o["entrada"], "t_real": int(ahora) if en_mercado else o["entrada"], "pe_libro": o["pe"],
                              "pe_real": pe_real, "noc": noc, "dist": dist, "actual": vivo, "ref": ref}
        anotar({"evento": "abre", "k": k, "activo": a, "estrategia": o["estrategia"], "lado": o["lado"], "pe_libro": o["pe"],
                "pe_real": pe_real, "noc": noc, "dist": dist})
        eventos.append(f"Abre {'LARGO' if o['lado'] > 0 else 'CORTO'} {a} {o['estrategia']}: libro {o['pe']:.6g}, real {pe_real:.6g}, "
                       f"nocional {noc:.2f} USDT ({noc / est['real']:.1f}× del saldo), stop {ref if ref else o['pe'] * (1 - o['lado'] * 0.03):.6g}")
    # 4) saldo, máximo y parada total
    abierto = sum(p["noc"] * p["lado"] * (p["actual"] / p["pe_real"] - 1) for p in est["abiertas"].values())
    est["real_vivo"] = est["real"] + abierto
    est["libro_vivo"] = est["libro"] + sum(p["noc"] * p["lado"] * (p["actual"] / p["pe_libro"] - 1) for p in est["abiertas"].values())
    est["maximo"] = max(est["maximo"], est["real_vivo"])
    if not est["parada"] and est["real_vivo"] <= (1 - conf["paradas"]["total"]) * est["maximo"]:
        est["parada"] = int(ahora)
        eventos.append("PARADA TOTAL: el saldo cayó el 60 % desde su máximo; el agente deja de abrir.")
    if not est["equidad"] or ahora - est["equidad"][-1][0] >= 300:
        est["equidad"].append([int(ahora), round(est["real_vivo"], 6), round(est["libro_vivo"], 6)])
        est["equidad"] = est["equidad"][-8000:]
    est["vistas"] = {k: v for k, v in est["vistas"].items() if ahora - v < 3 * 86400}
    est["ultima_vuelta"] = int(ahora)
    return est, eventos


def main():
    if sys.stdout is None:
        sys.stdout = sys.stderr = open(os.devnull, "w")
    una = "--una-vez" in sys.argv
    os.makedirs(RAIZ, exist_ok=True)
    conf = json.load(open(CONF, encoding="utf-8"))
    activos = ["BTC"] + [a for a in sistema.ACTIVOS_LC if a != "BTC"]
    fuentes = {a: FuenteViva(a) for a in activos}
    try:
        est = json.load(open(ESTADO, encoding="utf-8"))
    except Exception:
        est = estado_inicial(conf)
    log(f"agente consolidado en marcha: {conf['mezcla']} · riesgo {conf['riesgo'] * 100:.0f} % · hasta {conf['max_abiertas']} a la vez · tope {conf['apal_max']}×")
    while True:
        try:
            est, eventos = vuelta(est, conf, fuentes)
            escribir(ESTADO, est)
            if eventos:
                avisar(eventos)
        except Exception:
            log("error en la vuelta: " + traceback.format_exc().replace("\n", " | ")[:1500])
        if una:
            break
        if os.path.exists(PARAR):
            os.remove(PARAR)
            log("PARAR: salgo")
            break
        time.sleep(max(1.0, 63 - time.time() % 60))  # una vuelta por minuto, 3 s después de cada cierre


if __name__ == "__main__":
    main()
