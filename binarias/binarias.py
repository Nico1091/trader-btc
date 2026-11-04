"""Centinela de las binarias, v4 (29/10/2026). Pantalla: http://127.0.0.1:8792 · PLAN.md y REVISION.md.

Nicolás (29/10, 21:50): «apueste el porcentaje que crea… sin stop loss o los que usted crea y diga». Decidido con t21 (a ciegas):
- Procedimiento del mes: entre los 8 del banco (reglas en BTC y ETH; modelo a 10, 30 y 60 min en BTC y ETH), el de mejor
  historial a ciegas en los 12 meses anteriores (motor/historial.py). Lo operan REGLA (toda señal), CLAUDE (lo que aprueba el
  operador) y AZAR (misma hora y plazo, sentido al azar). BTC FIJO sigue con las reglas de BTC, el principal de la v3.
- Tamaño: medio Kelly con el acierto a ciegas de los 6 meses anteriores de cada procedimiento, nunca menos de 5 USDT; si ese
  acierto no supera el equilibrio, la cuenta no apuesta ese mes. Sin stop y sin preventivas: en t21 no mejoraron a ciegas.
- Cada mes: reglas elegidas con los 12 meses anteriores (motor/seleccion.py), banco puesto al día (t18 y t19 con las velas
  nuevas), procedimiento por historial y, si es el modelo, ajuste con el mismo código de t19 (motor/modelo.py).
- 70 s antes del cierre de cada vela de 5 min: ficha para el operador si el procedimiento del mes va a disparar. 3 s después
  del cierre: apuestas en papel. Una abierta a la vez por cuenta; hasta 16 al día; pago 0,85; empate = fallo.
- Precio del libro (como el banco) y de 20 s después (el que vería Nicolás al tocar); CLAUDE se liquida con el de 20 s.
- Paridad diaria a las 00:15 contra el cálculo completo. Telegram: cada apuesta de CLAUDE y su resultado.
Uso: pythonw -I binarias.py · python -I binarias.py --prueba (prepara el mes, informa y sale) · Parar: crear el archivo PARAR."""
import datetime as dt
import json
import os
import random
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from motor import historial as HI  # noqa: E402
from motor import modelo as MOD  # noqa: E402
from motor import senales as SEN  # noqa: E402
from motor import seleccion as SEL  # noqa: E402

ESTADO, APUESTAS, REGISTRO = (os.path.join(AQUI, x) for x in ("estado.json", "apuestas.jsonl", "binarias.log"))
PARAR, FICHAS, DECISIONES = (os.path.join(AQUI, x) for x in ("PARAR", "fichas", "decisiones"))
SELECCION, VIVO, OPERADOR = (os.path.join(AQUI, x) for x in ("seleccion.json", "senales_vivo.jsonl", "operador.latido"))
PRUEBAS, DATOS = os.path.join(AQUI, "pruebas"), os.path.join(AQUI, "datos")
TG = os.path.join(os.path.dirname(AQUI), "tg_pc.py")
NPY = os.environ.get("BINARIAS_NPY_BASE", r"C:\Users\ni109\Ingresos\trader-btc\datos\um\{}_um_1m.npy")
NPY_VIVO = os.path.join(DATOS, "{}_um_1m_vivo.npy")
PUERTO = int(os.environ.get("BINARIAS_PUERTO", "8792"))
HOST = os.environ.get("BINARIAS_HOST", "127.0.0.1")
FAPI = "https://fapi.binance.com/fapi/v1/"
H = {"User-Agent": "binarias-centinela"}
SIMBOLOS = ("BTCUSDT", "ETHUSDT")
CUENTAS = {"REGLA": "mes", "CLAUDE": "mes", "AZAR": "mes", "BTC FIJO": "fijo"}
FIJO = "reglas BTC"
DIAS_MEMORIA, DIAS_SENALES, DIAS_MODELO = 460, 200, 62
PREVIA, GRACIA, TOQUE = 70, 5, 20
CAP, PAGO, TASA, TOPE = 100000.0, 0.85, 3180.0, 16
MINIMO = 5 * TASA
HCOL = 5 * 3600
COL = dt.timezone(dt.timedelta(hours=-5))
UTC = dt.timezone.utc
CANDADO = threading.Lock()
DESFASE = 0.0
VIGENTE = {"sel": {}}  # la elección del mes en uso; la cambia el hilo que prepara cada mes


# ---------------------------------------------------------------- utilidades
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
    """Escritura atómica con reintentos: otro proceso puede tener el archivo abierto un instante (WinError 5)."""
    tmp = f"{ruta}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    for i in range(10):
        try:
            os.replace(tmp, ruta)
            return True
        except PermissionError:
            time.sleep(0.1 * (i + 1))
    log(f"no se pudo guardar {os.path.basename(ruta)} tras 10 intentos; queda en memoria")
    return False


def anexar(ruta, fila):
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def red(ruta, timeout=10):
    return json.loads(urllib.request.urlopen(urllib.request.Request(FAPI + ruta, headers=H), timeout=timeout).read())


def ahora():
    return time.time() + DESFASE


def sincronizar():
    global DESFASE
    t1 = time.time()
    s = red("time")["serverTime"] / 1000
    t2 = time.time()
    DESFASE = s - (t1 + t2) / 2


def hora(ts, f="%H:%M:%S"):
    return dt.datetime.fromtimestamp(ts, COL).strftime(f)


def cop(x, signo=False):
    t = f"{x:+,.0f}" if signo else f"{x:,.0f}"
    return "0" if abs(x) < 0.5 else t.replace(",", ".")


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def mes_de(ts):
    f = dt.datetime.fromtimestamp(ts - HCOL, UTC)
    return f.year, f.month


def mes_ini(y, m):
    return int(dt.datetime(y, m, 1, 5, tzinfo=UTC).timestamp())


def sumar(y, m, k):
    i = y * 12 + (m - 1) + k
    return i // 12, i % 12 + 1


def python_con_consola():
    if os.name != "nt":  # Linux y Android (T95H y teléfono): el mismo intérprete
        return sys.executable
    return os.path.join(os.path.dirname(sys.executable), "python.exe")


def avisar(texto):
    if not os.path.exists(TG):
        return
    ruta = os.path.join(AQUI, "alertas", f"{int(time.time() * 1000)}.txt")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("[Claude Code · binarias en papel]\n" + texto)

    def enviar():
        try:
            r = subprocess.run([python_con_consola(), "-I", TG, ruta], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if "ok" in (r.stdout or ""):
                os.remove(ruta)
            else:
                log("aviso a Telegram sin confirmar: " + (r.stdout or r.stderr).strip()[-120:])
        except Exception as e:
            log(f"aviso a Telegram falló ({type(e).__name__})")

    threading.Thread(target=enviar, daemon=True).start()


def sin_freno_de_windows():
    """Windows 11 frena los procesos sin ventana (EcoQoS); se pide la velocidad normal (como el agente de trader-btc)."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class Estado(ctypes.Structure):
            _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k32.SetProcessInformation.restype = wintypes.BOOL
        e = Estado(1, 0x1, 0x0)
        return bool(k32.SetProcessInformation(k32.GetCurrentProcess(), 4, ctypes.byref(e), ctypes.sizeof(e)))
    except Exception:
        return False


# ---------------------------------------------------------------- mercado
class Mercado:
    """Velas de 1 min cerradas de un símbolo (las de la historia guardada más las que trae Binance) y la vela en curso."""

    def __init__(self, sim):
        self.sim, self.vivo, self.precio, self.t_precio, self.huecos = sim, None, None, 0.0, 0
        ruta = NPY_VIVO.format(sim) if os.path.exists(NPY_VIVO.format(sim)) else NPY.format(sim)
        a = np.load(ruta, mmap_mode="r")
        i = int(np.searchsorted(a[:, 0], (time.time() - DIAS_MEMORIA * 86400) * 1000))
        b = np.array(a[i:])
        self.t = (b[:, 0] // 1000).astype(np.int64)
        self.o, self.h, self.l, self.c, self.v = (b[:, j].copy() for j in range(1, 6))
        self.completar()

    def completar(self):
        while True:
            x = red(f"klines?symbol={self.sim}&interval=1m&startTime={int(self.t[-1] + 60) * 1000}&limit=1500", 20)
            n = ahora() * 1000
            self.agregar([k for k in x if int(k[6]) < n])
            if len(x) < 1500:
                ab = [k for k in x if int(k[6]) >= n]
                if ab:
                    self.vivo = tuple([int(ab[-1][0]) // 1000] + [float(v) for v in ab[-1][1:6]])
                    self.precio, self.t_precio = float(ab[-1][4]), ahora()
                return

    def agregar(self, ks):
        nuevos, ult = [], int(self.t[-1])
        for k in ks:
            tk = int(k[0]) // 1000
            if tk <= ult:
                continue
            while ult + 60 < tk:  # hueco: vela plana con el último cierre, para no correr los índices
                ult += 60
                pc = nuevos[-1][4] if nuevos else float(self.c[-1])
                nuevos.append((ult, pc, pc, pc, pc, 0.0))
                self.huecos += 1
            ult = tk
            nuevos.append((tk, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
        if not nuevos:
            return
        arr = np.array(nuevos)
        self.t = np.r_[self.t, arr[:, 0].astype(np.int64)]
        self.o, self.h, self.l, self.c, self.v = (np.r_[x, arr[:, j]] for j, x in enumerate((self.o, self.h, self.l, self.c, self.v), 1))
        if self.t[0] < self.t[-1] - (DIAS_MEMORIA + 1) * 86400:
            i = int(np.searchsorted(self.t, self.t[-1] - DIAS_MEMORIA * 86400))
            self.t, self.o, self.h, self.l, self.c, self.v = (x[i:] for x in (self.t, self.o, self.h, self.l, self.c, self.v))

    def actualizar(self):
        x = red(f"klines?symbol={self.sim}&interval=1m&limit=3", 8)
        n = ahora() * 1000
        self.agregar([k for k in x if int(k[6]) < n])
        ab = [k for k in x if int(k[6]) >= n]
        if ab:
            self.vivo = tuple([int(ab[-1][0]) // 1000] + [float(v) for v in ab[-1][1:6]])
        self.precio, self.t_precio = float(x[-1][4]), ahora()

    def ventana(self, B, provisional, dias=DIAS_SENALES):
        """Velas de 1 min desde B − `dias` hasta B (sin incluir B). Provisional: completa con la vela en curso y con el precio
        actual los minutos que faltan para llegar a B."""
        i0, j = (int(x) for x in np.searchsorted(self.t, [B - dias * 86400, B]))
        t, o, h, l, c, v = (x[i0:j] for x in (self.t, self.o, self.h, self.l, self.c, self.v))
        if provisional and len(t):
            extra, sig = [], int(t[-1]) + 60
            while sig < B:
                if self.vivo and self.vivo[0] == sig:
                    extra.append(self.vivo)
                else:
                    p = self.precio
                    extra.append((sig, p, p, p, p, 0.0))
                sig += 60
            if extra:
                e = np.array(extra, dtype=float)
                t = np.r_[t, e[:, 0].astype(np.int64)]
                o, h, l, c, v = (np.r_[x, e[:, k]] for k, x in enumerate((o, h, l, c, v), 1))
        return t, o, h, l, c, v

    def hasta(self, B):
        """Todas las velas en memoria anteriores a B."""
        i = int(np.searchsorted(self.t, B))
        return self.t[:i], self.o[:i], self.h[:i], self.l[:i], self.c[:i], self.v[:i]

    def apertura(self, tm):
        i = int(np.searchsorted(self.t, tm))
        if i < len(self.t) and self.t[i] == tm:
            return float(self.o[i])
        if self.vivo and self.vivo[0] == tm:
            return self.vivo[1]
        return None

    def cierre(self, tm):
        i = int(np.searchsorted(self.t, tm))
        return float(self.c[i]) if i < len(self.t) and self.t[i] == tm else None


# ---------------------------------------------------------------- señales de los procedimientos
def calcular(m, B, provisional):
    t, o, h, l, c, v = m.ventana(B, provisional)
    S, T5, vol5, ctxd = SEN.todas(t, o, h, l, c)
    return S, T5, vol5, ctxd, (t, c)


def disparos(S, T5, vol5, ctxd, elegidos, B):
    """Las reglas elegidas que disparan con entrada en B, con los mismos filtros que motor/seleccion.mascara, ordenadas por
    nombre como en el banco (la primera es la que se apuesta)."""
    out = []
    for e in elegidos:
        if e["nombre"] not in S:
            continue
        _, ts, ds = S[e["nombre"]]
        ts, ds = np.asarray(ts, dtype=np.int64), np.asarray(ds, dtype=float)
        conf = e["conf"]
        for i in np.flatnonzero(ts == B).tolist():
            d = float(ds[i])
            if d == 0:
                continue
            if conf.get("zona") and conf["sentido"] * d != ctxd.get(B // 86400, 0.0):
                continue
            if conf.get("sesion"):
                lo, hi = SEL.SESIONES[conf["sesion"]]
                if not lo <= (B % 86400) // 3600 < hi:
                    continue
            if conf.get("vol"):
                j5 = int(np.clip(np.searchsorted(T5, B - 300, side="right") - 1, 0, len(T5) - 1))
                if bool(vol5[j5]) != (conf["vol"] == "alta"):
                    continue
            out.append({"estrategia": e["nombre"], "dir": int(conf["sentido"] * d), "plazo": int(conf["plazo"]),
                        "a_ciegas": f"{e['aciertos']}/{e['apuestas']} en la ventana (límite {num(100 * e['lb'], 1)} %)"})
    out.sort(key=lambda x: x["estrategia"])
    return out


def senal_modelo(m, B, provisional, par, nombre):
    t, o, h, l, c, v = m.ventana(B, provisional, DIAS_MODELO)
    te, _, X, _ = MOD.rasgos(t, o, h, l, c, v, vivo=True)
    i = np.flatnonzero(te == B)
    if not len(i):
        return [], None
    d, p = MOD.decidir(par, X[i[-1]])
    hit = {"estrategia": nombre, "dir": int(d), "plazo": int(par["plazo"]), "p": round(p, 6), "tau": par["tau"],
           "a_ciegas": f"probabilidad de subida {num(p, 3)} · umbral {num(par['tau'], 3)} (apuesta si ≥ umbral o ≤ 1 − umbral)"}
    return ([hit] if d else []), p


def senal(proc, merc, sel, B, provisional):
    """Señales del procedimiento con entrada en B: (hits, probabilidad del modelo o None)."""
    m = merc[proc["sim"]]
    if proc["tipo"] == "modelo":
        par = sel.get("modelo")
        if not par or par.get("tau") is None:
            return [], None
        return senal_modelo(m, B, provisional, par, proc["nombre"])
    S, T5, vol5, ctxd, _ = calcular(m, B, provisional)
    return disparos(S, T5, vol5, ctxd, sel.get("reglas", {}).get(proc["sim"], []), B), None


def otras(S, B):
    sube = baja = 0
    for _, (g, ts, ds) in S.items():
        ts, ds = np.asarray(ts, dtype=np.int64), np.asarray(ds, dtype=float)
        for d in ds[ts == B].tolist():
            sube += d > 0
            baja += d < 0
    return sube, baja


def recorrido(t, c, B):
    """Movimiento de 5, 15 y 60 min antes de B, en % y en veces la volatilidad normal (desviación de 1 min de 4 h)."""
    j = int(np.searchsorted(t, B)) - 1
    if j < 300:
        return {}
    r = np.diff(np.log(c[j - 240:j + 1]))
    s = float(r.std()) or 1e-9
    out = {}
    for n in (5, 15, 60):
        x = float(np.log(c[j] / c[j - n]))
        out[f"{n} min"] = {"pct": round(100 * x, 3), "sigmas": round(x / (s * n ** 0.5), 2)}
    r15 = np.diff(np.log(c[j - 15:j + 1]))
    out["volatilidad 15 min / 4 h"] = round(float(r15.std()) / s, 2)
    rg = np.abs(np.diff(np.log(c[j - 5:j + 1])))
    out["vela de 1 min más grande de las últimas 5 / media de la hora"] = round(float(rg.max()) / (float(np.abs(r[-60:]).mean()) or 1e-9), 2)
    return out


# ---------------------------------------------------------------- preparación de cada mes
def elegir_reglas(m, ym):
    a, b = mes_ini(*sumar(*ym, -12)), mes_ini(*ym)
    t, o, h, l, c, _ = m.hasta(b)
    S, T5, vol5, ctxd = SEN.todas(t, o, h, l, c)
    P = SEL.preparar(S, T5, vol5, ctxd, t, o, c)
    return SEL.elegir(P, a, b - 61 * 60, 3)


def entrenar_modelo(m, ym, pl):
    """El mismo ajuste de t19 para el mes ym, con las velas en memoria."""
    a, f, b = mes_ini(*sumar(*ym, -12)), mes_ini(*sumar(*ym, -3)), mes_ini(*ym)
    t, o, h, l, c, v = m.hasta(b)
    te, k, X, _ = MOD.rasgos(t, o, h, l, c, v)
    mov = c[k + pl - 1] - o[k]
    par = MOD.entrenar(te, X, mov, a, f, b, pl)
    return {"w": par["w"].tolist(), "mu": par["mu"].tolist(), "de": par["de"].tolist(), "tau": par["tau"], "plazo": pl, "sim": m.sim}


def banco_hasta():
    """Hasta dónde llegan las velas con que se corrió el banco (t18 y t19)."""
    r = leer(os.path.join(PRUEBAS, "banco_hasta.json"), None)
    if r:
        return r["t"]
    a = np.load(NPY.format("BTCUSDT"), mmap_mode="r")
    return int(a[-1, 0] // 1000)


def poner_al_dia_el_banco(merc):
    """Guarda las velas nuevas (historia + memoria) y vuelve a correr t18 y t19 en los dos símbolos, con prioridad baja."""
    os.makedirs(DATOS, exist_ok=True)
    fin = None
    for sim, m in merc.items():
        base = np.load(NPY.format(sim), mmap_mode="r")
        ult = int(base[-1, 0] // 1000)
        i = int(np.searchsorted(m.t, ult + 60))
        extra = np.column_stack([m.t[i:] * 1000.0, m.o[i:], m.h[i:], m.l[i:], m.c[i:], m.v[i:]])
        todo = np.vstack([np.asarray(base), extra])
        tmp = NPY_VIVO.format(sim) + ".nuevo.npy"
        np.save(tmp, todo)
        os.replace(tmp, NPY_VIVO.format(sim))
        fin = int(todo[-1, 0] // 1000) if fin is None else min(fin, int(todo[-1, 0] // 1000))
    for script in ("t18_reglas_a_ciegas.py", "t19_modelo_a_ciegas.py"):
        for sim in merc:
            r = subprocess.run([python_con_consola(), "-I", os.path.join(PRUEBAS, script), sim, NPY_VIVO.format(sim)], cwd=PRUEBAS,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600,
                               creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) | 0x4000) if os.name == "nt" else 0)
            log(f"banco: {script} {sim} terminó con código {r.returncode}")
            if r.returncode:
                raise RuntimeError(f"{script} {sim}: " + (r.stderr or "")[-300:])
    escribir(os.path.join(PRUEBAS, "banco_hasta.json"), {"t": fin, "texto": hora(fin, "%Y-%m-%d %H:%M")})


def preparar_mes(merc, ym, anterior):
    clave = f"{ym[0]}-{ym[1]:02d}"
    s = {"version": 4, "mes": clave, "listo": False, "anterior": anterior,
         "reglas": {sim: elegir_reglas(merc[sim], ym) for sim in SIMBOLOS}}
    VIGENTE["sel"] = s  # BTC FIJO puede operar ya; el procedimiento del mes espera
    if banco_hasta() < mes_ini(*ym) - 3600:
        log(f"poniendo al día el banco para elegir el procedimiento de {clave}")
        poner_al_dia_el_banco(merc)
    S = HI.stats_mes(HI.cargar())
    w, n = HI.ventana(S, FIJO, clave, 12)
    s["fijo"] = {"nombre": FIJO, "tipo": "reglas", "sim": "BTCUSDT", "plazo": None, "fraccion": HI.fraccion(S, FIJO, clave),
                 "aciertos": w, "apuestas": n}
    el = HI.elegir(S, clave)
    s["procedimiento"] = None
    if el:
        nombre, lb, w, n = el
        tipo, sim, pl = HI.describir(nombre)
        s["procedimiento"] = {"nombre": nombre, "tipo": tipo, "sim": sim, "plazo": pl, "lb": lb, "aciertos": w, "apuestas": n,
                              "fraccion": HI.fraccion(S, nombre, clave)}
        if tipo == "modelo":
            s["modelo"] = entrenar_modelo(merc[sim], ym, pl)
    s["listo"], s["calculada"] = True, hora(ahora(), "%Y-%m-%d %H:%M:%S")
    escribir(SELECCION, s)
    VIGENTE["sel"] = s
    p = s["procedimiento"]
    log(f"mes {clave} listo: procedimiento {p['nombre'] if p else 'ninguno'} (fracción {num(100 * p['fraccion']) if p else '0'} %"
        + (f", umbral {s['modelo']['tau']}" if s.get("modelo") else "") + f") · BTC FIJO fracción {num(100 * s['fijo']['fraccion'])} % · "
        + " · ".join(f"{sim}: {', '.join(e['nombre'] for e in s['reglas'][sim]) or 'ninguna'}" for sim in SIMBOLOS))


def asegurar_mes(merc, en_hilo=True):
    """Prepara el mes si la elección guardada no es la del mes en curso."""
    ym = mes_de(ahora())
    clave = f"{ym[0]}-{ym[1]:02d}"
    s = leer(SELECCION, {})
    if s.get("version") == 4 and s.get("mes") == clave and s.get("listo"):
        VIGENTE["sel"] = s
        return
    if VIGENTE.get("preparando") == clave:
        return
    VIGENTE["preparando"] = clave
    anterior = {k: v for k, v in s.items() if k != "anterior"} if s.get("version") == 4 and s.get("listo") else None

    def trabajo():
        try:
            preparar_mes(merc, ym, anterior)
        except Exception:
            log("error preparando el mes: " + traceback.format_exc().replace("\n", " | ")[-900:])
            VIGENTE["preparando"] = None

    if en_hilo:
        threading.Thread(target=trabajo, daemon=True).start()
    else:
        trabajo()


def procedimientos(sel):
    """[(rol, procedimiento)] listos para operar."""
    out = []
    if sel.get("listo") and sel.get("procedimiento"):
        out.append(("mes", sel["procedimiento"]))
    if sel.get("reglas", {}).get("BTCUSDT") is not None:
        out.append(("fijo", sel.get("fijo") or {"nombre": FIJO, "tipo": "reglas", "sim": "BTCUSDT", "fraccion": 0.0}))
    return out


# ---------------------------------------------------------------- cuentas
def cuenta_nueva():
    return {"saldo": CAP, "ocupado": 0, "dia": None, "n_dia": 0, "aciertos": 0, "fallos": 0, "empates": 0, "quebrada": False}


def estado_inicial():
    return {"version": 4, "inicio": ahora(), "latido": ahora(), "cuentas": {k: cuenta_nueva() for k in CUENTAS},
            "abiertas": [], "ultimas": [], "fichas": [], "paridad": {}, "motivo": "arrancando", "errores": 0}


def puede(cu, B):
    d = (B - HCOL) // 86400
    if cu["dia"] != d:
        cu["dia"], cu["n_dia"] = d, 0
    return not cu["quebrada"] and B >= cu["ocupado"] and cu["n_dia"] < TOPE


def monto_de(cu, fraccion):
    if fraccion <= 0 or cu["saldo"] < MINIMO:
        return None
    return max(fraccion * cu["saldo"], MINIMO)


def apostar(est, nombre, proc, hit, B, extra=None):
    cu = est["cuentas"][nombre]
    if cu["saldo"] < MINIMO:
        cu["quebrada"] = True
        return None
    monto = monto_de(cu, proc.get("fraccion", 0.0))
    if monto is None:
        return None
    ap = {"id": f"{nombre}-{proc['sim']}-{B}", "cuenta": nombre, "sim": proc["sim"], "procedimiento": proc["nombre"], "t": B,
          "estrategia": hit["estrategia"], "dir": hit["dir"], "plazo": hit["plazo"], "monto": round(monto), "saldo_antes": round(cu["saldo"]),
          "fraccion": round(proc.get("fraccion", 0.0), 5), "pe_libro": None, "px_libro": None, "pe_toque": None, "px_toque": None}
    if extra:
        ap.update(extra)
    cu["ocupado"] = B + hit["plazo"] * 60
    cu["n_dia"] += 1
    est["abiertas"].append(ap)
    return ap


def resolver(est, merc):
    """Toma los precios que faltan y cierra las apuestas vencidas."""
    t_ahora = ahora()
    quedan = []
    for ap in est["abiertas"]:
        m = merc[ap["sim"]]
        B, pl = ap["t"], ap["plazo"]
        if ap["pe_libro"] is None:
            ap["pe_libro"] = m.apertura(B)
        if ap["px_libro"] is None:
            ap["px_libro"] = m.cierre(B + pl * 60 - 60)
        if ap["pe_toque"] is None and t_ahora >= B + TOQUE and m.precio and m.t_precio >= B + TOQUE - 1:
            ap["pe_toque"], ap["t_pe_toque"] = m.precio, round(m.t_precio, 1)
        if ap["px_toque"] is None and t_ahora >= B + TOQUE + pl * 60 and m.precio and m.t_precio >= B + TOQUE + pl * 60 - 1:
            ap["px_toque"], ap["t_px_toque"] = m.precio, round(m.t_precio, 1)
        listo = None not in (ap["pe_libro"], ap["px_libro"], ap["pe_toque"], ap["px_toque"])
        if not listo and t_ahora > B + pl * 60 + 900:  # 15 min de gracia: se cierra con lo que haya
            listo = None not in (ap["pe_libro"], ap["px_libro"])
        if not listo:
            quedan.append(ap)
            continue
        r_libro = int(np.sign(ap["dir"] * (ap["px_libro"] - ap["pe_libro"])))
        r_toque = int(np.sign(ap["dir"] * (ap["px_toque"] - ap["pe_toque"]))) if ap["px_toque"] and ap["pe_toque"] else None
        r = r_toque if ap["cuenta"] == "CLAUDE" and r_toque is not None else r_libro
        cu = est["cuentas"][ap["cuenta"]]
        g = ap["monto"] * PAGO if r > 0 else -ap["monto"]
        cu["saldo"] += g
        cu["aciertos"] += r > 0
        cu["fallos"] += r < 0
        cu["empates"] += r == 0
        if cu["saldo"] < MINIMO:
            cu["quebrada"] = True
        ap.update({"res_libro": r_libro, "res_toque": r_toque, "res": r, "ganancia": round(g), "saldo": round(cu["saldo"]),
                   "cerrada": hora(t_ahora, "%Y-%m-%d %H:%M:%S")})
        anexar(APUESTAS, ap)
        est["ultimas"] = ([ap] + est["ultimas"])[:80]
        if ap["cuenta"] == "CLAUDE":
            avisar(f"RESULTADO · cuenta CLAUDE · {ap['sim'][:3]} {'▲ SUBE' if ap['dir'] > 0 else '▼ BAJA'} {pl} min · "
                   f"{'ACIERTA' if r > 0 else 'EMPATE (cuenta como fallo)' if r == 0 else 'FALLA'} {cop(g, True)} COP · saldo {cop(cu['saldo'])} COP")
    est["abiertas"] = quedan


# ---------------------------------------------------------------- fichas y decisiones
def escribir_ficha(est, merc, proc, B, hits):
    cu = est["cuentas"]["CLAUDE"]
    m = merc[proc["sim"]]
    h0 = hits[0]
    S, _, _, _, (t, c) = calcular(m, B, True)
    sube, baja = otras(S, B)
    monto = monto_de(cu, proc.get("fraccion", 0.0)) or MINIMO
    ficha = {"id": f"{m.sim}-{B}", "simbolo": m.sim, "procedimiento": proc["nombre"], "cierre": hora(B), "limite": B + GRACIA,
             "limite_txt": hora(B + GRACIA), "creada": round(ahora(), 1), "precio": m.precio, "edad_precio_s": round(ahora() - m.t_precio, 1),
             "propuesta": {"sentido": "SUBE" if h0["dir"] > 0 else "BAJA", "plazo_min": h0["plazo"], "estrategia": h0["estrategia"],
                           "detalle": h0.get("a_ciegas", ""), "monto_cop": round(monto), "monto_usdt": round(monto / TASA, 2)},
             "historial_del_procedimiento": f"{proc.get('aciertos', 0)}/{proc.get('apuestas', 0)} a ciegas en los 12 meses anteriores "
                                            f"({num(100 * proc.get('aciertos', 0) / max(1, proc.get('apuestas', 1)), 1)} %)",
             "otras_elegidas": [{"estrategia": x["estrategia"], "sentido": "SUBE" if x["dir"] > 0 else "BAJA", "plazo_min": x["plazo"]} for x in hits[1:]],
             "todas_las_estrategias_en_esta_vela": {"sube": sube, "baja": baja},
             "contexto_del_dia": {1.0: "alcista", -1.0: "bajista"}.get(SEN.contexto(t, c).get(B // 86400, 0.0), "sin dato"),
             "mercado": recorrido(t, c, B),
             "cuenta_CLAUDE": {"saldo_cop": round(cu["saldo"]), "apuestas_hoy": cu["n_dia"], "aciertos": cu["aciertos"], "fallos": cu["fallos"]}}
    os.makedirs(FICHAS, exist_ok=True)
    escribir(os.path.join(FICHAS, ficha["id"] + ".json"), ficha)
    est["fichas"] = ([{"id": ficha["id"], "cierre": ficha["cierre"], "simbolo": m.sim, "propuesta": ficha["propuesta"], "estado": "esperando"}]
                     + est["fichas"])[:60]
    return ficha


def decision(fid, limite):
    d = leer(os.path.join(DECISIONES, fid + ".json"), None)
    if not d:
        return "sin decisión", None
    if d.get("t", 1e18) > limite:
        return "tarde", d
    return ("aprobada" if d.get("decision") == "aprobar" else "descartada"), d


def marcar_ficha(est, fid, estado, d=None):
    for f in est["fichas"]:
        if f["id"] == fid:
            f["estado"] = estado
            if d:
                f.update({"confianza": d.get("confianza"), "razon": d.get("razon")})


# ---------------------------------------------------------------- ciclo
def previa(est, merc, sel, B):
    p = sel.get("procedimiento") if sel.get("listo") else None
    if not p or p.get("fraccion", 0) <= 0 or not puede(est["cuentas"]["CLAUDE"], B):
        return
    hits, _ = senal(p, merc, sel, B, True)
    if hits:
        f = escribir_ficha(est, merc, p, B, hits)
        log(f"ficha {f['id']}: {f['propuesta']['sentido']} {f['propuesta']['plazo_min']} min · {f['propuesta']['estrategia']}")


def final(est, merc, sel, B):
    """Evalúa cada procedimiento con la vela cerrada y apuesta. Devuelve el texto para el estado."""
    textos, vistos = [], {}
    for rol, proc in procedimientos(sel):
        clave = proc["nombre"]
        if clave not in vistos:
            vistos[clave] = senal(proc, merc, sel, B, False)
            hits, p = vistos[clave]
            anexar(VIVO, {"proc": clave, "sim": proc["sim"], "B": B, "mes": sel.get("mes"), "p": p,
                          "hits": [[x["estrategia"], x["dir"], x["plazo"]] for x in hits]})
        hits, p = vistos[clave]
        if rol == "mes":
            fid = f"{proc['sim']}-{B}"
            f = leer(os.path.join(FICHAS, fid + ".json"), None)
            if f:
                estado, d = decision(fid, f["limite"])
                q = f["propuesta"]
                igual = bool(hits) and hits[0]["estrategia"] == q["estrategia"] and (1 if q["sentido"] == "SUBE" else -1) == hits[0]["dir"]
                if estado == "aprobada" and not igual:
                    estado = "aprobada, pero la vela cerrada no confirmó la señal"
                marcar_ficha(est, fid, estado, d)
                if estado == "aprobada" and puede(est["cuentas"]["CLAUDE"], B):
                    ap = apostar(est, "CLAUDE", proc, hits[0], B, {"confianza": d.get("confianza"), "razon": d.get("razon")})
                    if ap:
                        conf = d.get("confianza")
                        conf_txt = f" · confianza {num(conf)}" if isinstance(conf, (int, float)) else ""
                        avisar(f"APUESTA EN PAPEL · cuenta CLAUDE · {ap['sim'][:3]} {'▲ SUBE' if ap['dir'] > 0 else '▼ BAJA'} · vence en {ap['plazo']} min · "
                               f"{cop(ap['monto'])} COP ({num(ap['monto'] / TASA)} USDT) · vela de las {hora(B, '%H:%M')} · {ap['estrategia']}{conf_txt}")
            if hits:
                for nombre in ("REGLA", "AZAR"):
                    if puede(est["cuentas"][nombre], B):
                        h = dict(hits[0])
                        if nombre == "AZAR":
                            h["dir"] = random.Random(B).choice((-1, 1))
                        apostar(est, nombre, proc, h, B)
        elif hits and puede(est["cuentas"]["BTC FIJO"], B):
            apostar(est, "BTC FIJO", proc, hits[0], B)
        textos.append(f"{clave}: " + (", ".join(f"{'sube' if h['dir'] > 0 else 'baja'} {h['plazo']} min" for h in hits) if hits else "sin señal")
                      + (f" (p {num(p, 3)})" if p is not None else ""))
    return f"vela de las {hora(B, '%H:%M')}: " + " · ".join(textos) if textos else f"vela de las {hora(B, '%H:%M')}: eligiendo el procedimiento del mes"


def paridad(est, merc):
    """Señales en vivo de ayer (hora de Colombia) frente al cálculo completo sobre las mismas velas, con la elección del mes en que
    se evaluó cada vela."""
    hoy0 = ((int(ahora()) - HCOL) // 86400) * 86400 + HCOL
    ayer0 = hoy0 - 86400
    s = leer(SELECCION, {})
    por_mes = {s.get("mes"): s}
    if s.get("anterior"):
        por_mes[s["anterior"].get("mes")] = s["anterior"]
    vivo = {}
    if os.path.exists(VIVO):
        for ln in open(VIVO, encoding="utf-8"):
            x = json.loads(ln)
            if ayer0 <= x["B"] < hoy0 and "proc" in x:
                vivo[(x["proc"], x["B"])] = x
    coinciden = difieren = 0
    detalle, dp = [], 0.0
    cache = {}
    for (nombre, B), x in sorted(vivo.items(), key=lambda kv: kv[0][1]):
        sm = por_mes.get(x.get("mes"))
        if not sm:
            continue
        tipo, sim, pl = HI.describir(nombre)
        m = merc[sim]
        if tipo == "modelo":
            par = sm.get("modelo")
            if not par:
                continue
            if ("modelo", sim) not in cache:
                t, o, h, l, c, v = m.ventana(hoy0, False, DIAS_MODELO + 1)
                te, _, X, _ = MOD.rasgos(t, o, h, l, c, v, vivo=True)
                cache[("modelo", sim)] = (te, X)
            te, X = cache[("modelo", sim)]
            i = np.flatnonzero(te == B)
            if not len(i):
                continue
            d, p = MOD.decidir(par, X[i[-1]])
            esperado = [[nombre, int(d), int(par["plazo"])]] if d else []
            if x.get("p") is not None:
                dp = max(dp, abs(p - x["p"]))
        else:
            if ("reglas", sim) not in cache:
                S, T5, vol5, ctxd, _ = calcular(m, hoy0, False)
                cache[("reglas", sim)] = (S, T5, vol5, ctxd)
            S, T5, vol5, ctxd = cache[("reglas", sim)]
            esperado = [[h["estrategia"], h["dir"], h["plazo"]] for h in disparos(S, T5, vol5, ctxd, sm.get("reglas", {}).get(sim, []), B)]
        if sorted(map(tuple, esperado)) == sorted(map(tuple, x["hits"])):
            coinciden += 1
        else:
            difieren += 1
            detalle.append(f"{nombre} {hora(B, '%H:%M')}: vivo {x['hits']} · completo {esperado}")
    est["paridad"] = {"dia": hora(ayer0, "%Y-%m-%d"), "coinciden": coinciden, "difieren": difieren, "detalle": detalle[:20],
                      "max_diferencia_probabilidad": dp}
    log(f"paridad de {est['paridad']['dia']}: {coinciden} velas iguales, {difieren} distintas, diferencia máxima de probabilidad {dp:.2e}")


def motor(prueba=False):
    sin_freno_de_windows()
    sincronizar()
    merc = {sim: Mercado(sim) for sim in SIMBOLOS}
    est = leer(ESTADO, {})
    if est.get("version") != 4:
        est = estado_inicial()
    asegurar_mes(merc, en_hilo=prueba is False)
    if prueba:
        return merc, est, VIGENTE["sel"]
    log(f"centinela v4 en marcha · desfase {DESFASE:+.2f} s · " + " · ".join(f"{s}: {len(merc[s].t)} velas" for s in SIMBOLOS))
    hechas, t_sync, t_par, t_red, t_guardado, t_mes = set(), time.time(), None, 0.0, 0.0, 0.0
    arranque = ahora()
    while not os.path.exists(PARAR):
        try:
            if time.time() - t_red >= 2:
                for m in merc.values():
                    m.actualizar()
                t_red = time.time()
            if time.time() - t_sync > 3600:
                sincronizar()
                t_sync = time.time()
            now = ahora()
            if time.time() - t_mes > 30:
                asegurar_mes(merc)
                t_mes = time.time()
            sel = VIGENTE["sel"]
            B = (int(now) // 300 + 1) * 300
            if now >= B - PREVIA and ("p", B) not in hechas:
                hechas.add(("p", B))
                with CANDADO:
                    previa(est, merc, sel, B)
            Bp = B - 300
            if ("f", Bp) not in hechas and now >= Bp + 3:
                listo = all(merc[s].t[-1] >= Bp - 60 for s in SIMBOLOS)
                if listo or now >= Bp + 45:
                    hechas.add(("f", Bp))
                    if Bp + 3 >= arranque:
                        if not listo:
                            log(f"la vela de las {hora(Bp, '%H:%M')} no llegó a tiempo; no se evalúa")
                        else:
                            with CANDADO:
                                est["motivo"] = final(est, merc, sel, Bp)
            with CANDADO:
                resolver(est, merc)
            hcol = dt.datetime.fromtimestamp(now, COL)
            if hcol.hour == 0 and hcol.minute >= 15 and t_par != hcol.date():
                t_par = hcol.date()
                with CANDADO:
                    paridad(est, merc)
            est["latido"], est["proxima"], est["desfase"] = now, B, round(DESFASE, 3)
            est["huecos"] = {s: merc[s].huecos for s in SIMBOLOS}
            est["precios"] = {s: merc[s].precio for s in SIMBOLOS}
            est["seleccion"] = {k: v for k, v in sel.items() if k not in ("modelo", "anterior")}
            if time.time() - t_guardado >= 5:
                with CANDADO:
                    escribir(ESTADO, est)
                t_guardado = time.time()
            hechas = {x for x in hechas if x[-1] > now - 3600}
        except Exception:
            est["errores"] = est.get("errores", 0) + 1
            log("error: " + traceback.format_exc().replace("\n", " | ")[-900:])
            time.sleep(3)
        time.sleep(0.5)
    with CANDADO:
        escribir(ESTADO, est)
    log("PARAR: salgo")


# ---------------------------------------------------------------- pantalla
def resumen_pruebas():
    out = {}
    for s in SIMBOLOS:
        r = leer(os.path.join(PRUEBAS, f"t18_{s}.json"), {})
        if r:
            out[f"reglas {s[:3]}"] = {"apuestas": r.get("apuestas"), "acierto": r.get("acierto"), "tramos": r.get("tramos"), "por_dia": r.get("por_dia")}
        m = leer(os.path.join(PRUEBAS, f"t19_{s}.json"), {})
        for pl, x in (m.get("plazos") or {}).items():
            out[f"modelo {pl} min {s[:3]}"] = {"apuestas": x.get("apuestas"), "acierto": x.get("acierto"), "tramos": x.get("tramos"), "por_dia": x.get("por_dia")}
    return out


def datos():
    with CANDADO:
        est = json.loads(json.dumps(leer(ESTADO, {})))
    op = leer(OPERADOR, {})
    est["operador"] = {"visto_hace_s": round(time.time() - op.get("t", 0)), "accion": op.get("accion")} if op else None
    est["ahora"] = ahora()
    est["pruebas"] = resumen_pruebas()
    return est


PAGINA = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Binarias · centinela</title><style>
:root{--f:#f6f4ef;--t:#1d1b18;--s:#6b665d;--c:#fffdf8;--v:#1f7a4d;--r:#b3402e;--a:#8a6d1d}
@media (prefers-color-scheme:dark){:root{--f:#161513;--t:#ece8df;--s:#a39d91;--c:#211f1c;--v:#5fc28f;--r:#e7826f;--a:#d9b75d}}
body{margin:0;background:var(--f);color:var(--t);font:14px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1100px;margin:auto;padding:20px 16px 60px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}
.sub{color:var(--s)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.card{background:var(--c);border-radius:12px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.big{font-size:22px;font-weight:600}.v{color:var(--v)}.r{color:var(--r)}.a{color:var(--a)}
.tabla{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;padding:6px 10px;vertical-align:top}
tr:nth-child(even) td{background:rgba(127,127,127,.07)}th{color:var(--s);font-weight:500}.n{text-align:right;font-variant-numeric:tabular-nums}
</style></head><body><main>
<h1>Binarias en papel · centinela</h1><p class="sub" id="cab">cargando…</p>
<h2>Procedimiento del mes y tamaño de la apuesta</h2><div id="sel"></div>
<h2>Cuentas (100.000 COP cada una · medio Kelly, mínimo 5 USDT · pago 0,85 · sin stop)</h2><div class="grid" id="cuentas"></div>
<h2>Apuestas abiertas</h2><div class="tabla"><table id="abiertas"></table></div>
<h2>Fichas para Claude y sus decisiones</h2><div class="tabla"><table id="fichas"></table></div>
<h2>Últimas apuestas cerradas</h2><div class="tabla"><table id="ultimas"></table></div>
<h2>Pruebas a ciegas 2021-2026 (cada mes elegido sin ver el futuro)</h2><div class="tabla"><table id="pruebas"></table></div>
<h2>Paridad con el banco de pruebas</h2><p id="par" class="sub"></p>
</main><script>
const $=id=>document.getElementById(id),cop=x=>Math.round(x).toLocaleString("es-CO"),pc=x=>x==null?"–":(100*x).toFixed(1).replace(".",",")+" %";
const f=ts=>new Date(ts*1000).toLocaleString("es-CO",{timeZone:"America/Bogota",hour12:false,day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
const sent=d=>d>0?"▲ sube":"▼ baja",res=r=>r==null?"…":r>0?'<span class="v">acierta</span>':r<0?'<span class="r">falla</span>':'<span class="a">empate (fallo)</span>';
const desc=e=>`${e.nombre} [${e.conf.sentido<0?"al revés":"normal"}, ${e.conf.plazo} min${e.conf.zona?", a favor del contexto":""}${e.conf.sesion?", "+e.conf.sesion:""}${e.conf.vol?", volatilidad "+e.conf.vol:""}]`;
async function cargar(){let d;try{d=await (await fetch("datos.json",{cache:"no-store"})).json()}catch(e){$("cab").textContent="sin conexión con el centinela";return}
const lat=Math.round(d.ahora-(d.latido||0)),op=d.operador;
$("cab").innerHTML=`Latido hace ${lat} s ${lat>30?'<span class="r">(detenido)</span>':''} · ${d.motivo||""} · BTC ${d.precios?cop(d.precios.BTCUSDT):"–"} · ETH ${d.precios?cop(d.precios.ETHUSDT):"–"} · operador Claude: ${op?(op.visto_hace_s<1800?'esperando fichas (visto hace '+op.visto_hace_s+' s)':'<span class="r">sin señales hace '+Math.round(op.visto_hace_s/60)+' min</span>'):'<span class="r">no ha arrancado</span>'}`;
const s=d.seleccion||{},p=s.procedimiento,fj=s.fijo;
$("sel").innerHTML=!s.listo?'<p class="sub">eligiendo el procedimiento del mes…</p>':`<p><b>${s.mes}: ${p?p.nombre:"ninguno supera el equilibrio"}</b>${p?` · ${p.aciertos}/${p.apuestas} a ciegas en los 12 meses anteriores (${pc(p.aciertos/p.apuestas)}) · apuesta ${(100*p.fraccion).toFixed(2).replace(".",",")} % del saldo, mínimo 5 USDT`:""}</p>
<p class="sub">BTC FIJO (reglas de BTC): apuesta ${fj?(100*fj.fraccion).toFixed(2).replace(".",","):"–"} % del saldo, mínimo 5 USDT · reglas del mes en BTC: ${(s.reglas&&s.reglas.BTCUSDT||[]).map(desc).join("; ")||"ninguna"} · en ETH: ${(s.reglas&&s.reglas.ETHUSDT||[]).map(desc).join("; ")||"ninguna"}</p>`;
$("cuentas").innerHTML=Object.entries(d.cuentas||{}).map(([k,c])=>{const n=c.aciertos+c.fallos+c.empates,g=c.saldo-100000;
return `<div class="card"><div class="sub">${k}${k=="CLAUDE"?" · decide Claude":k=="AZAR"?" · sentido al azar":k=="BTC FIJO"?" · reglas de BTC":" · toda señal"}</div><div class="big">${cop(c.saldo)} COP</div>
<div class="${g>=0?"v":"r"}">${g>=0?"+":""}${cop(g)} COP</div><div class="sub">${n} apuestas · ${c.aciertos} aciertos · ${n?pc(c.aciertos/n):"–"}${c.quebrada?' · <span class="r">quebrada</span>':""}</div></div>`}).join("");
const fila=a=>`<td>${f(a.t)}</td><td>${a.cuenta}</td><td>${a.sim.slice(0,3)} · ${a.estrategia}</td><td>${sent(a.dir)} · ${a.plazo} min</td><td class="n">${cop(a.monto)}</td>`;
$("abiertas").innerHTML="<tr><th>Vela</th><th>Cuenta</th><th>Estrategia</th><th>Apuesta</th><th class=n>COP</th></tr>"+((d.abiertas||[]).map(a=>"<tr>"+fila(a)+"</tr>").join("")||'<tr><td colspan=5 class=sub>ninguna</td></tr>');
$("fichas").innerHTML="<tr><th>Vela</th><th>Propuesta</th><th>Decisión</th><th>Confianza</th><th>Razón</th></tr>"+((d.fichas||[]).slice(0,25).map(x=>`<tr><td>${x.cierre}</td><td>${(x.simbolo||"").slice(0,3)} ${x.propuesta.sentido} ${x.propuesta.plazo_min} min · ${x.propuesta.estrategia}</td><td>${x.estado}</td><td class=n>${x.confianza??"–"}</td><td>${x.razon??""}</td></tr>`).join("")||'<tr><td colspan=5 class=sub>todavía no hay fichas</td></tr>');
$("ultimas").innerHTML="<tr><th>Vela</th><th>Cuenta</th><th>Estrategia</th><th>Apuesta</th><th class=n>COP</th><th>Resultado</th><th class=n>Ganancia</th><th class=n>Saldo</th></tr>"+((d.ultimas||[]).slice(0,40).map(a=>"<tr>"+fila(a)+`<td>${res(a.res)}</td><td class="n ${a.ganancia>=0?"v":"r"}">${a.ganancia>=0?"+":""}${cop(a.ganancia)}</td><td class=n>${cop(a.saldo)}</td></tr>`).join("")||'<tr><td colspan=8 class=sub>todavía no hay apuestas cerradas</td></tr>');
$("pruebas").innerHTML="<tr><th>Procedimiento</th><th class=n>Apuestas</th><th class=n>Al día</th><th class=n>Acierto</th><th class=n>2021-23</th><th class=n>2024-26</th></tr>"+Object.entries(d.pruebas||{}).map(([k,x])=>{const tr=x.tramos||{},a=tr["2021-2023"],b=tr["2024-2026"];
return `<tr><td>${k}</td><td class=n>${cop(x.apuestas||0)}</td><td class=n>${(x.por_dia||0).toFixed(1).replace(".",",")}</td><td class=n>${pc(x.acierto)}</td><td class=n>${a?pc(a[1]/a[0]):"–"}</td><td class=n>${b?pc(b[1]/b[0]):"–"}</td></tr>`}).join("");
const q=d.paridad||{};$("par").textContent=q.dia?`${q.dia}: ${q.coinciden} velas iguales y ${q.difieren} distintas`+(q.detalle&&q.detalle.length?" · "+q.detalle.join(" · "):""):"la primera comparación se hace a las 00:15";}
cargar();setInterval(cargar,5000);
</script></body></html>"""


class Pantalla(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path.startswith("/datos.json"):
                cuerpo, tipo = json.dumps(datos(), ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8"
            else:
                cuerpo, tipo = PAGINA.encode("utf-8"), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)
        except Exception:
            pass

    def log_message(self, *a):
        pass


def main():
    if "--prueba" in sys.argv:
        merc, est, sel = motor(prueba=True)
        print(f"desfase {DESFASE:+.2f} s")
        for s in SIMBOLOS:
            m = merc[s]
            print(f"{s}: {len(m.t)} velas hasta {hora(int(m.t[-1]), '%Y-%m-%d %H:%M')} · huecos {m.huecos} · precio {m.precio}")
        p = sel.get("procedimiento")
        print(f"mes {sel.get('mes')} · listo {sel.get('listo')} · procedimiento {p}")
        print(f"fijo {sel.get('fijo')}")
        if sel.get("modelo"):
            print(f"modelo: umbral {sel['modelo']['tau']} · plazo {sel['modelo']['plazo']} · {sel['modelo']['sim']}")
        for s in SIMBOLOS:
            print(f"reglas {s}: " + "; ".join(f"{e['nombre']} {e['conf']}" for e in sel.get("reglas", {}).get(s, [])))
        return
    try:
        srv = ThreadingHTTPServer((HOST, PUERTO), Pantalla)
    except OSError:
        log("ya hay un centinela en el puerto 8792: salgo")
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log(f"pantalla en http://127.0.0.1:{PUERTO}")
    espera = 30
    while not os.path.exists(PARAR):
        try:
            motor()
            return
        except OSError as e:
            # Al arrancar con Windows la red suele tardar: se espera y se vuelve a intentar.
            log(f"sin red al arrancar ({type(e).__name__}: {e}); reintento en {espera} s")
            time.sleep(espera)
            espera = min(espera * 2, 300)
        except Exception:
            log("error fatal: " + traceback.format_exc().replace("\n", " | ")[-900:])
            raise


if __name__ == "__main__":
    main()
