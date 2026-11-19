"""T7 (29/10/2026): UN MES OPERADO como si fuera en vivo: 4 binarias al día, solo BTC/USDT, plazos de 5, 10 y 15 min.

Pedido de Nicolás (29/10): «operar única y exclusivamente Bitcoin dólar, máximo 15 minutos, operaciones binarias de tiempo…
medir cada estrategia… las de la T95H… 4 operaciones diarias durante un mes completo… con cada estrategia, mezclando, con
una sola, con muchas, cada una optimizándola, usando inversa… preventivas… y consolidar un agente que termine ganando».
«Estrategias consolidadas tuyas, más las estrategias de la T95H: ambas son aparte».

Grupos (todas sobre BTCUSDT de futuros de Binance, velas de 1 min armadas en 5 y 15 min):
  A · SUS LIBROS: los 19 patrones de vela de patrones_std (su dirección de libro) y las reglas del curso: tres resistencias
      (prueba a7, en 5 y 15 min), 50 SMA + precio, pendiente de la media 48 (Quantdemy), alineación de medias 9/21/50,
      pullback en tendencia, techo y piso del rango de 24 h, rompimiento de 20 velas.
  B · LA T95H (motor v3 de la caja): P05b, P05c, P11, N8, N9 (sistema.Dia), apostando en el instante de su señal.
  C · MIS CONSOLIDADAS: REV5, REV15, REV15 CTX (vela fuerte → en contra) y tres cuervos / tres soldados AL REVÉS.

Reglas fijadas ANTES de mirar resultados:
- Apuesta: entra al abrir el minuto siguiente al cierre de la vela de la señal; vence al cierre del minuto entrada + plazo − 1.
  Empate = se devuelve. Pago 0,85 (también se informa 0,80). 2 % del saldo por apuesta, desde 150.000 COP.
- Día de operación en hora de Colombia: como máximo 4 apuestas, una por franja de 6 horas (00-06, 06-12, 12-18, 18-24),
  una abierta a la vez; dentro de cada franja, la primera señal.
- ENTRENAMIENTO = 01/01/2024 a 28/09/2026; MES = 29/09/2026 a 28/10/2026 (30 días, hora de Colombia), nunca visto al optimizar.
- Optimización de cada estrategia SOLO con el entrenamiento, en este orden y quedándose con lo que sube el acierto con ≥ 200
  apuestas: sentido (normal o inversa) × plazo (5, 10, 15) → zona (solo a favor del contexto del día) → horario (Asia 00-07,
  Europa 07-13 o América 13-21 UTC) → volatilidad (alta o baja: rango de 20 velas de 5 min frente al de 500) → racha
  (parar el día tras 2 pérdidas seguidas, si sube el saldo final).
- Mezclas: la mejor sola, las 3 y las 5 mejores, las 3 mejores de cada grupo y todas las que pasan 54,1 % en el
  entrenamiento; cada una con la configuración optimizada de sus estrategias.
- AGENTE CONSOLIDADO: la estrategia o mezcla con mayor crecimiento diario en el entrenamiento (pago 0,85) con ≥ 300 apuestas.
  Su mes se muestra día por día. Elegir mirando el mes sería trampa: el mes solo se mira para informar.
Salidas: t7_mes_operado.txt y ../t7_resultados.json (para la pantalla).
Uso: python -I t7_mes_operado.py > t7_mes_operado.txt"""
import bisect
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
TB = r"C:\Users\ni109\Ingresos\trader-btc\.claude\worktrees\maestro-v2"
sys.path.insert(0, os.path.join(TB, "consolidacion"))
import patrones_std  # noqa: E402
import sistema  # noqa: E402

NPY = r"C:\Users\ni109\Ingresos\trader-btc\datos\um\BTCUSDT_um_1m.npy"
DATOS = os.path.join(AQUI, "..", "datos")
UTC = dt.timezone.utc
HCOL = 5 * 3600
INI = int(dt.datetime(2024, 1, 1, tzinfo=UTC).timestamp())
MES0 = int(dt.datetime(2026, 9, 29, 5, tzinfo=UTC).timestamp())  # 29/09 00:00 en Colombia
MES1 = int(dt.datetime(2026, 10, 29, 5, tzinfo=UTC).timestamp())  # 29/10 00:00 en Colombia
PLAZOS = (5, 10, 15)
APUESTA, CAP = 0.02, 150000.0
EQ85 = 100 / 1.85


def es(s):
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "§", s)
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", s)
    return s.replace("§", ".")


def p(s=""):
    print(es(s), flush=True)


# ---------------------------------------------------------------- datos
def cargar():
    a = np.load(NPY)
    a = a[a[:, 0] >= (INI - 140 * 86400) * 1000]
    ruta = os.path.join(DATOS, "cola_1m.json")
    os.makedirs(DATOS, exist_ok=True)
    cola = []
    if os.path.exists(ruta) and time.time() - os.path.getmtime(ruta) < 3600:
        cola = json.load(open(ruta))
    else:
        t = int(a[-1, 0]) + 60000
        while t < time.time() * 1000 - 60000:
            u = f"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&startTime={t}&limit=1500"
            x = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "t7"}), timeout=30).read())
            if not x:
                break
            cola += [[float(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in x if int(k[6]) < time.time() * 1000]
            t = int(x[-1][0]) + 60000
            time.sleep(0.3)
        json.dump(cola, open(ruta, "w"))
    if cola:
        a = np.vstack([a, np.array(cola)])
    t = (a[:, 0] // 1000).astype(np.int64)
    huecos = int((np.diff(t) != 60).sum())
    if huecos:
        p(f"AVISO: {huecos} huecos en las velas de 1 min (se usan tal cual)")
    ext = os.path.join(DATOS, "BTCUSDT_1m_ext.npy")
    np.save(ext, a)
    return t, a[:, 1], a[:, 2], a[:, 3], a[:, 4], ext


def velas(t, o, h, l, c, seg):
    k = seg // 60
    i0 = int(np.argmax(t % seg == 0))
    n = (len(t) - i0) // k * k
    return (t[i0:i0 + n].reshape(-1, k)[:, 0], o[i0:i0 + n].reshape(-1, k)[:, 0], h[i0:i0 + n].reshape(-1, k).max(1),
            l[i0:i0 + n].reshape(-1, k).min(1), c[i0:i0 + n].reshape(-1, k)[:, -1])


def media_previa(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    m = np.full(len(x), np.nan)
    m[n:] = (cs[n:-1] - cs[:-n - 1]) / n
    return m


def sma(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    m = np.full(len(x), np.nan)
    m[n - 1:] = (cs[n:] - cs[:-n]) / n
    return m


def ema(x, n):
    a, out, v = 2 / (n + 1), np.empty(len(x)), x[0]
    for i, xi in enumerate(x):
        v = a * xi + (1 - a) * v
        out[i] = v
    return out


def extremo_previo(x, n, f):
    out = np.full(len(x), np.nan)
    if len(x) > n:
        out[n:] = f(np.lib.stride_tricks.sliding_window_view(x[:-1], n), axis=1)
    return out


def transicion(m):
    return m & ~np.r_[False, m[:-1]]


# ---------------------------------------------------------------- tres resistencias (a7, copiado tal cual)
VENTANA, TOL, K = 60, 0.25, 2


def pivotes(x, alto):
    out = []
    for i in range(K, len(x) - K):
        w = x[i - K:i + K + 1]
        if (alto and x[i] == w.max() and x[i] > x[i - 1]) or (not alto and x[i] == w.min() and x[i] < x[i - 1]):
            out.append(i)
    return out


def tres_resistencias(Hh, L, C):
    tr = np.maximum(Hh - L, np.maximum(np.abs(Hh - np.r_[C[0], C[:-1]]), np.abs(L - np.r_[C[0], C[:-1]])))
    atr = np.concatenate([[tr[0]], np.convolve(tr, np.ones(14) / 14, mode="full")[:len(tr) - 1]])
    ph, pl = pivotes(Hh, True), pivotes(L, False)
    out, libre = [], 0
    for i in range(VENTANA + 5, len(C) - 9):
        if i < libre:
            continue
        tol = TOL * atr[i]
        if tol <= 0:
            continue
        for alto, piv, ext in ((True, ph, Hh), (False, pl, L)):
            a = bisect.bisect_left(piv, i - VENTANA)
            b = bisect.bisect_right(piv, i - K - 1)
            rec = piv[a:b]
            if len(rec) < 2:
                continue
            j1 = rec[-1]
            grupo = [j for j in rec if abs(ext[j] - ext[j1]) <= tol]
            if len(grupo) < 2:
                continue
            if alto:
                zona = max(ext[j] for j in grupo)
                ok = C[min(grupo):i].max() <= zona + tol and zona - tol <= Hh[i] <= zona + tol and C[i] < zona - tol
            else:
                zona = min(ext[j] for j in grupo)
                ok = C[min(grupo):i].min() >= zona - tol and zona - tol <= L[i] <= zona + tol and C[i] > zona + tol
            if ok:
                out.append((i, -1 if alto else 1))
                libre = i + 8
                break
    return out


# ---------------------------------------------------------------- señales
def senales(t, o, h, l, c, ext):
    S = {}  # nombre -> (grupo, tiempos de apuesta, dirección)
    T5, O5, H5, L5, C5 = velas(t, o, h, l, c, 300)
    T15, O15, H15, L15, C15 = velas(t, o, h, l, c, 900)
    P = patrones_std.patrones(O5.tolist(), H5.tolist(), L5.tolist(), C5.tolist())
    for nom, m in P.items():
        m = np.array(m)
        S[f"patrón {nom.replace('_', ' ')}"] = ("A", T5[m] + 300, np.full(int(m.sum()), patrones_std.LADO[nom]))
    for nom, (T, Hh, L, C, seg) in (("tres resistencias 5 min", (T5, H5, L5, C5, 300)), ("tres resistencias 15 min", (T15, H15, L15, C15, 900))):
        r = tres_resistencias(Hh, L, C)
        S[nom] = ("A", np.array([T[i] + seg for i, d in r]), np.array([d for i, d in r]))
    s50 = sma(C5, 50)
    up, dn = transicion(C5 > s50), transicion(C5 < s50)
    S["50 SMA + precio"] = ("A", np.r_[T5[up], T5[dn]] + 300, np.r_[np.ones(up.sum()), -np.ones(dn.sum())])
    m48 = sma(C5, 48)
    pu = transicion((m48 > np.r_[np.nan, m48[:-1]]) & (C5 > m48 * 0.995))
    pd_ = transicion((m48 < np.r_[np.nan, m48[:-1]]) & (C5 < m48 * 1.005))
    S["pendiente de la media 48 (Quantdemy)"] = ("A", np.r_[T5[pu], T5[pd_]] + 300, np.r_[np.ones(pu.sum()), -np.ones(pd_.sum())])
    e9, e21, e50 = ema(C5, 9), ema(C5, 21), ema(C5, 50)
    au, ad = transicion((e9 > e21) & (e21 > e50)), transicion((e9 < e21) & (e21 < e50))
    S["alineación de medias 9/21/50"] = ("A", np.r_[T5[au], T5[ad]] + 300, np.r_[np.ones(au.sum()), -np.ones(ad.sum())])
    s200 = sma(C5, 200)
    hi48, lo48 = extremo_previo(H5, 48, np.max), extremo_previo(L5, 48, np.min)
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = (C5 - lo48) / (hi48 - lo48)
        pos1 = np.r_[np.nan, pos[:-1]]
        tend_up = (C5 > s200) & (s50 > np.r_[np.full(12, np.nan), s50[:-12]])
        tend_dn = (C5 < s200) & (s50 < np.r_[np.full(12, np.nan), s50[:-12]])
        pbu = tend_up & (pos >= 0.35) & (pos <= 0.65) & (pos1 > 0.65)
        pbd = tend_dn & (pos >= 0.35) & (pos <= 0.65) & (pos1 < 0.35)
        hi288, lo288 = extremo_previo(H5, 288, np.max), extremo_previo(L5, 288, np.min)
        p288 = (C5 - lo288) / (hi288 - lo288)
        techo, piso = transicion(p288 >= 0.9), transicion(p288 <= 0.1)
        hi20, lo20 = extremo_previo(H5, 20, np.max), extremo_previo(L5, 20, np.min)
        ru, rd = transicion(C5 > hi20), transicion(C5 < lo20)
    S["pullback en tendencia"] = ("A", np.r_[T5[pbu], T5[pbd]] + 300, np.r_[np.ones(pbu.sum()), -np.ones(pbd.sum())])
    S["techo y piso de 24 h"] = ("A", np.r_[T5[techo], T5[piso]] + 300, np.r_[-np.ones(techo.sum()), np.ones(piso.sum())])
    S["rompimiento de 20 velas"] = ("A", np.r_[T5[ru], T5[rd]] + 300, np.r_[np.ones(ru.sum()), -np.ones(rd.sum())])
    # B · motor v3 de la caja T95H, día por día
    F = sistema.Npy(ext)
    por = {k: ([], []) for k in ("P05b", "P05c", "P11", "N8", "N9")}
    d = dt.date(2024, 1, 1)
    fin = dt.datetime.fromtimestamp(MES1, UTC).date()
    while d <= fin:
        try:
            ops, _ = sistema.Dia(F, d).todo()
        except Exception:
            ops = []
        for op in ops:
            if op["estrategia"] in por:
                por[op["estrategia"]][0].append(int(op["senal"]))
                por[op["estrategia"]][1].append(int(op["lado"]))
        d += dt.timedelta(days=1)
    for k, (ts, ds) in por.items():
        S[f"{k} (T95H)"] = ("B", np.array(ts), np.array(ds))
    # C · mis consolidadas
    for nom, (T, O, C, seg) in (("REV5", (T5, O5, C5, 300)), ("REV15", (T15, O15, C15, 900))):
        cu = np.abs(C - O)
        f = cu >= 2 * media_previa(cu, 100)
        S[nom] = ("C", T[f] + seg, -np.sign(C[f] - O[f]))
    S["tres cuervos AL REVÉS"] = ("C", T5[np.array(P["tres_cuervos"])] + 300, np.ones(int(np.sum(P["tres_cuervos"]))))
    S["tres soldados AL REVÉS"] = ("C", T5[np.array(P["tres_soldados"])] + 300, -np.ones(int(np.sum(P["tres_soldados"]))))
    rng5 = H5 - L5
    vol5 = media_previa(rng5, 20) > media_previa(rng5, 500)
    return S, T5, vol5


def contexto(t, c):
    dia = t // 86400
    ult = np.r_[np.flatnonzero(np.diff(dia)), len(dia) - 1]
    d, cd = dia[ult], c[ult]
    s = np.full(len(cd), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(cd)])
    s[50:] = (cs[50:-1] - cs[:-51]) / 50
    x = np.zeros(len(cd))
    x[1:] = np.sign(cd[:-1] - s[1:])
    return dict(zip(d.tolist(), np.nan_to_num(x).tolist()))


# ---------------------------------------------------------------- operación diaria
def preparar(ts, ds, t, o, c, ctxd, T5, vol5):
    """Para cada señal: resultado a 5, 10 y 15 min (+1/0/−1 en su dirección), contexto, sesión y volatilidad."""
    t0 = int(t[0])
    k = (ts - t0) // 60
    ok = (ts >= INI) & (k >= 0) & (k + max(PLAZOS) < len(c)) & (ds != 0)
    ts, ds, k = ts[ok], ds[ok].astype(int), k[ok]
    orden = np.argsort(ts, kind="stable")
    ts, ds, k = ts[orden], ds[orden], k[orden]
    res = {pl: np.sign(ds * (c[k + pl - 1] - o[k])).astype(int) for pl in PLAZOS}
    pe = o[k]
    px = {pl: c[k + pl - 1] for pl in PLAZOS}
    j5 = np.clip(np.searchsorted(T5, ts - 300, side="right") - 1, 0, len(T5) - 1)
    return {"t": ts, "d": ds, "res": res, "pe": pe, "px": px, "ctx": np.array([ctxd.get(int(x) // 86400, 0.0) for x in ts]) == ds,
            "hora": (ts % 86400) // 3600, "valta": vol5[j5]}


def filtrar(s, conf):
    m = np.ones(len(s["t"]), bool)
    if conf.get("zona"):
        m &= s["ctx"] if conf["sentido"] > 0 else ~s["ctx"]  # en la inversa, «a favor del contexto» es la apuesta dada vuelta
    if conf.get("sesion"):
        lo, hi = {"Asia": (0, 7), "Europa": (7, 13), "América": (13, 21)}[conf["sesion"]]
        m &= (s["hora"] >= lo) & (s["hora"] < hi)
    if conf.get("vol"):
        m &= s["valta"] if conf["vol"] == "alta" else ~s["valta"]
    return m


def eventos(nombre, s, conf):
    m = filtrar(s, conf)
    pl = conf["plazo"]
    return [(int(a), nombre, conf["sentido"] * int(d), conf["sentido"] * int(r), pl, float(pe), float(px))
            for a, d, r, pe, px in zip(s["t"][m], s["d"][m], s["res"][pl][m], s["pe"][m], s["px"][pl][m])]


def operar(evs, desde, hasta, racha=False, pago=0.85, registrar=False):
    """4 al día (una por franja de 6 h, hora de Colombia), una abierta a la vez, 2 % del saldo."""
    saldo, dia_act, n_dia, franjas, seguidas, parado, ocupado = CAP, None, 0, set(), 0, False, 0
    g_tot = w = l = e = 0
    dias, log = {}, []
    for ts, nom, d, r, pl, pe, px in evs:
        if ts < desde or ts >= hasta:
            continue
        col = ts - HCOL
        dia, franja = col // 86400, (col % 86400) // 21600
        if dia != dia_act:
            dia_act, n_dia, franjas, seguidas, parado = dia, 0, set(), 0, False
        if parado or n_dia >= 4 or franja in franjas or ts < ocupado:
            continue
        monto = APUESTA * saldo
        g = monto * pago if r > 0 else -monto if r < 0 else 0.0
        saldo += g
        n_dia += 1
        franjas.add(franja)
        ocupado = ts + pl * 60
        w, l, e = w + (r > 0), l + (r < 0), e + (r == 0)
        seguidas = seguidas + 1 if r < 0 else 0 if r > 0 else seguidas
        if racha and seguidas >= 2:
            parado = True
        dias[dia] = dias.get(dia, 0.0) + g
        if registrar:
            log.append({"t": ts, "estrategia": nom, "d": d, "plazo": pl, "pe": pe, "px": px, "res": r, "monto": monto, "g": g, "saldo": saldo})
    n = w + l
    nd = max(1.0, (hasta - desde) / 86400)
    r = {"apuestas": n + e, "acierto": w / n * 100 if n else float("nan"), "saldo": saldo, "resultado": saldo - CAP,
         "crec_dia": ((saldo / CAP) ** (1 / nd) - 1) * 100, "dias_pos": sum(1 for v in dias.values() if v > 0), "dias": len(dias)}
    if registrar:
        r["log"] = log
    return r


def optimizar(nombre, s):
    """Solo con el entrenamiento. Devuelve la configuración y su resultado en entrenamiento."""
    def prueba(conf):
        return operar(eventos(nombre, s, conf), INI, MES0, conf.get("racha", False))
    mejor = None
    for sentido in (1, -1):
        for pl in PLAZOS:
            conf = {"sentido": sentido, "plazo": pl}
            r = prueba(conf)
            if r["apuestas"] >= 200 and (mejor is None or r["acierto"] > mejor[1]["acierto"]):
                mejor = (conf, r)
    if mejor is None:
        conf = {"sentido": 1, "plazo": 5}
        return conf, prueba(conf), True
    base = dict(mejor[0])
    for clave, opciones in (("zona", (True,)), ("sesion", ("Asia", "Europa", "América")), ("vol", ("alta", "baja"))):
        for op in opciones:
            conf = dict(mejor[0], **{clave: op})
            r = prueba(conf)
            if r["apuestas"] >= 200 and r["acierto"] > mejor[1]["acierto"]:
                mejor = (conf, r)
    conf = dict(mejor[0], racha=True)
    r = prueba(conf)
    if r["saldo"] > mejor[1]["saldo"]:
        mejor = (conf, r)
    mejor[0]["base"] = base
    return mejor[0], mejor[1], False


def describir(conf):
    x = [("al revés" if conf["sentido"] < 0 else "normal"), f"{conf['plazo']} min"]
    if conf.get("zona"):
        x.append("a favor del contexto")
    if conf.get("sesion"):
        x.append(conf["sesion"])
    if conf.get("vol"):
        x.append(f"volatilidad {conf['vol']}")
    if conf.get("racha"):
        x.append("para tras 2 pérdidas")
    return ", ".join(x)


def main():
    t, o, h, l, c, ext = cargar()
    p(f"T7 · UN MES OPERADO · BTCUSDT · velas hasta {dt.datetime.fromtimestamp(int(t[-1]), UTC) - dt.timedelta(hours=5):%d/%m/%Y %H:%M} (Colombia)")
    p("4 binarias al día (una por franja de 6 h), 2 % del saldo, pago 0,85 · entrenamiento 01/01/2024-28/09/2026 · mes 29/09-28/10/2026")
    p(f"para no perder hace falta 54.1 % con pago 0,85 y 55.6 % con 0,80\n")
    S, T5, vol5 = senales(t, o, h, l, c, ext)
    ctxd = contexto(t, c)
    filas = []
    for nombre, (grupo, ts, ds) in S.items():
        s = preparar(np.asarray(ts, dtype=np.int64), np.asarray(ds), t, o, c, ctxd, T5, vol5)
        conf, rt, poca = optimizar(nombre, s)
        rm = operar(eventos(nombre, s, conf), MES0, MES1, conf.get("racha", False))
        b = conf.get("base", conf)
        rb = operar(eventos(nombre, s, {"sentido": 1, "plazo": b["plazo"]}), MES0, MES1)
        filas.append({"grupo": grupo, "nombre": nombre, "conf": conf, "desc": describir(conf), "ent": rt, "mes": rm,
                      "mes_sin": rb, "poca": poca, "s": s})
    nombres_g = {"A": "A · SUS LIBROS", "B": "B · LA T95H (motor v3)", "C": "C · MIS CONSOLIDADAS"}
    for g in ("A", "B", "C"):
        p(f"== {nombres_g[g]} ==   (entrenamiento: acierto y apuestas · MES: acierto, apuestas y resultado desde 150 mil COP)")
        for f in sorted((x for x in filas if x["grupo"] == g), key=lambda x: -x["ent"]["acierto"] if x["ent"]["acierto"] == x["ent"]["acierto"] else 0):
            e, m, sn = f["ent"], f["mes"], f["mes_sin"]
            marca = "GANA" if e["acierto"] >= EQ85 and m["acierto"] >= EQ85 else "gana solo antes" if e["acierto"] >= EQ85 else ""
            p(f"   {f['nombre'][:38]:38s} {f['desc'][:58]:58s} ent {e['acierto']:5.1f} % ({e['apuestas']:4d}) · MES {m['acierto']:5.1f} % "
              f"({m['apuestas']:3d}) {m['resultado']:+9,.0f} COP · sin preventivas {sn['acierto']:5.1f} % {sn['resultado']:+9,.0f}"
              + (f"  ← {marca}" if marca else "") + ("  (poca muestra)" if f["poca"] else ""))
        p()
    # mezclas
    ranking = sorted((x for x in filas if not x["poca"] and x["ent"]["apuestas"] >= 300), key=lambda x: -x["ent"]["crec_dia"])
    def mezcla(sel):
        evs = sorted(ev for x in sel for ev in eventos(x["nombre"], x["s"], x["conf"]))
        return evs
    candidatos = {"la mejor sola": ranking[:1], "las 3 mejores": ranking[:3], "las 5 mejores": ranking[:5]}
    for g in ("A", "B", "C"):
        candidatos[f"las 3 mejores de {nombres_g[g][4:]}"] = [x for x in ranking if x["grupo"] == g][:3]
    candidatos["todas las que pasan 54,1 %"] = [x for x in ranking if x["ent"]["acierto"] >= EQ85]
    p("== MEZCLAS (cada estrategia con su configuración optimizada; 4 al día) ==")
    mejores = []
    for nom, sel in candidatos.items():
        if not sel:
            continue
        evs = mezcla(sel)
        for racha in (False, True):
            rt = operar(evs, INI, MES0, racha)
            rm = operar(evs, MES0, MES1, racha)
            rm80 = operar(evs, MES0, MES1, racha, pago=0.80)
            mejores.append((nom + (" · parar tras 2 pérdidas" if racha else ""), sel, racha, rt, rm, rm80))
            p(f"   {nom + (' + parar tras 2' if racha else ''):46s} ent {rt['acierto']:5.1f} % ({rt['apuestas']:4d}) {rt['crec_dia']:+.3f} %/día · "
              f"MES {rm['acierto']:5.1f} % ({rm['apuestas']:3d}) {rm['resultado']:+9,.0f} COP con 0,85 · {rm80['resultado']:+9,.0f} con 0,80 · "
              f"días positivos {rm['dias_pos']} de {rm['dias']}")
    todos = [(f["nombre"], [f], f["conf"].get("racha", False), f["ent"], f["mes"], None) for f in ranking] + mejores
    nom, sel, racha, rt, rm, _ = max((x for x in todos if x[3]["apuestas"] >= 300), key=lambda x: x[3]["crec_dia"])
    evs = mezcla(sel)
    final = operar(evs, MES0, MES1, racha, registrar=True)
    p(f"\nAGENTE CONSOLIDADO (regla fijada: mayor crecimiento en el entrenamiento): {nom}")
    for x in sel:
        p(f"   · {x['nombre']} ({x['desc']})")
    p(f"   entrenamiento: {rt['acierto']:.1f} % en {rt['apuestas']} apuestas, {rt['crec_dia']:+.3f} %/día")
    p(f"   MES: {final['acierto']:.1f} % en {final['apuestas']} apuestas · 150 mil → {final['saldo']:,.0f} COP ({final['resultado']:+,.0f}) · "
      f"días positivos {final['dias_pos']} de {final['dias']}\n")
    p("   EL MES, DÍA POR DÍA (hora de Colombia):")
    dia_ant = None
    for x in final["log"]:
        cdt = dt.datetime.fromtimestamp(x["t"], UTC) - dt.timedelta(hours=5)
        if cdt.date() != dia_ant:
            dia_ant = cdt.date()
            p(f"   {cdt:%d/%m}")
        p(f"      {cdt:%H:%M} {x['estrategia'][:34]:34s} {'▲ sube' if x['d'] > 0 else '▼ baja'} {x['plazo']:2d} min "
          f"{x['pe']:>10,.1f} → {x['px']:>10,.1f} {'ganó' if x['res'] > 0 else 'perdió' if x['res'] < 0 else 'empate'} "
          f"{x['g']:+8,.0f} · saldo {x['saldo']:,.0f}")
    salida = {"estrategias": [{k: v for k, v in f.items() if k != "s"} for f in filas],
              "mezclas": [{"nombre": n, "estrategias": [x["nombre"] for x in s_], "racha": r_, "ent": a_, "mes": b_, "mes80": c_}
                          for n, s_, r_, a_, b_, c_ in mejores],
              "agente": {"nombre": nom, "estrategias": [{"nombre": x["nombre"], "grupo": x["grupo"], "conf": x["conf"]} for x in sel],
                         "racha": racha, "ent": rt, "mes": {k: v for k, v in final.items() if k != "log"}, "log": final["log"]}}
    with open(os.path.join(AQUI, "..", "t7_resultados.json"), "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, default=float)


if __name__ == "__main__":
    main()
