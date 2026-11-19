"""Modelo de las binarias (regresión logística propia, numpy): una sola fuente para t19 y para el centinela.

Rasgos en cada cierre de vela de 5 min, todos con datos anteriores a la entrada (ver t19). Por mes: se normaliza y se ajusta con
los meses M-12 a M-4, el umbral simétrico de confianza se elige con M-3 a M-1 (solo apuestas vencidas antes de M) y se opera M."""
import math

import numpy as np

from . import senales as SEN

TAUS = np.round(np.arange(0.505, 0.7001, 0.005), 3)
LG, LP = math.log(1 + 0.16 * 0.85), math.log(1 - 0.16)
ALFA = 1e-3


def rasgos(t, o, h, l, c, v, vivo=False):
    """Muestras en cada cierre de 5 min: tiempo de entrada, índice del minuto de entrada y matriz de rasgos.
    En las pruebas solo entran muestras con resultado conocido (61 min después); en vivo entra también la última."""
    t0, N = int(t[0]), len(c)
    T5, O5, H5, L5, C5 = SEN.velas(t, o, h, l, c, 300)
    te = T5 + 300
    k = (te - t0) // 60
    ok = (k - 1 - 1440 >= 0) & ((k <= N) if vivo else (k + 61 < N)) & (np.arange(len(T5)) >= 288)
    lc = np.log(c)
    r1 = np.r_[0.0, np.diff(lc)]
    R, Q = np.cumsum(r1), np.cumsum(r1 * r1)
    V, C = np.cumsum(v), np.cumsum(c)
    kk = np.where(ok, k, 1500)
    j = kk - 1

    def ret(n):
        return lc[j] - lc[j - n]

    def sig(n):
        m = (R[j] - R[j - n]) / n
        return np.sqrt(np.maximum((Q[j] - Q[j - n]) / n - m * m, 1e-14))

    s15, s60, s240, s1440 = sig(15), sig(60), sig(240), sig(1440)
    F, nombres = [], []
    for n in (1, 3, 5, 10, 15, 30, 60, 120, 240):
        F.append(ret(n) / (s240 * math.sqrt(n)))
        nombres.append(f"rendimiento {n} min")
    F += [np.log(s15 / s240), np.log(s60 / s1440), np.log(s240)]
    nombres += ["volatilidad 15/240", "volatilidad 60/1440", "volatilidad 240"]
    vb = (V[j] - V[j - 1440]) / 1440 + 1e-9
    F += [np.log(((V[j] - V[j - 5]) / 5 + 1e-9) / vb), np.log(((V[j] - V[j - 60]) / 60 + 1e-9) / vb)]
    nombres += ["volumen 5 min", "volumen 60 min"]
    for n in (240, 1440):
        sm = (C[j] - C[j - n]) / n
        F.append(np.log(c[j] / sm) / (s240 * math.sqrt(n)))
        nombres.append(f"distancia a la media de {n} min")
    sm240, sm240p = (C[j] - C[j - 240]) / 240, (C[j - 60] - C[j - 300]) / 240
    F.append(np.log(sm240 / sm240p) / (s240 * math.sqrt(60)))
    nombres.append("pendiente de la media de 240 min")
    with np.errstate(invalid="ignore", divide="ignore"):
        for n in (48, 288):
            hi, lo = SEN.rodante(H5, n, np.max), SEN.rodante(L5, n, np.min)
            F.append(np.nan_to_num((C5 - lo) / (hi - lo), nan=0.5))
            nombres.append(f"posición en el rango de {n * 5 // 60} h")
        rg = np.maximum(H5 - L5, 1e-9)
        F += [(C5 - O5) / rg, (H5 - np.maximum(O5, C5)) / rg, (np.minimum(O5, C5) - L5) / rg]
    nombres += ["cuerpo de la vela", "mecha de arriba", "mecha de abajo"]
    hora = (te % 86400) / 3600
    F += [np.sin(2 * np.pi * hora / 24), np.cos(2 * np.pi * hora / 24), (((te // 86400) + 3) % 7 >= 5).astype(float)]
    nombres += ["hora (seno)", "hora (coseno)", "fin de semana"]
    ctxd = SEN.contexto(t, c)
    F.append(np.array([ctxd.get(int(x) // 86400, 0.0) for x in te]))
    nombres.append("contexto diario")
    S, _, _ = SEN.senales_AC(t, o, h, l, c)
    for nom, (g, ts, ds) in S.items():
        if g != "A":
            continue
        x = np.zeros(len(te))
        ts = np.asarray(ts, dtype=np.int64)
        i = np.searchsorted(te, ts)
        bien = i < len(te)
        bien[bien] &= te[i[bien]] == ts[bien]
        x[i[bien]] = np.asarray(ds, dtype=float)[bien]
        F.append(x)
        nombres.append(nom)
    X = np.column_stack(F)[ok]
    return te[ok], k[ok], np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0), nombres


def ajustar_logit(X, y, iters=8):
    n, d = X.shape
    Xb = np.c_[np.ones(n), X]
    w = np.zeros(d + 1)
    reg = ALFA * np.r_[0.0, np.ones(d)]
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(Xb @ w, -30, 30)))
        g = Xb.T @ (p - y) / n + reg * w
        H = (Xb.T * (p * (1 - p))) @ Xb / n + np.diag(reg)
        w -= np.linalg.solve(H, g)
    return w


def prob(w, Z):
    return 1 / (1 + np.exp(-np.clip(w[0] + Z @ w[1:], -30, 30)))


def normalizar(X, mu, de):
    return np.clip((X - mu) / de, -5, 5)


def elegir_tau(pc, te, mov, plazo):
    """Umbral simétrico que más hace crecer la cuenta al 16 % en la calibración, con al menos 100 apuestas sin solapes."""
    mejor = None
    for tau in TAUS:
        d = np.where(pc >= tau, 1, np.where(pc <= 1 - tau, -1, 0))
        m = d != 0
        tw = te[m]
        if len(tw) < 100:
            continue
        keep = np.r_[True, np.diff(tw) >= plazo * 60]
        r = np.sign(d[m][keep] * mov[m][keep])
        n, wv = len(r), int((r > 0).sum())
        gro = wv * LG + (n - wv) * LP
        if n >= 100 and gro > 0 and (mejor is None or gro > mejor[0]):
            mejor = (gro, float(tau))
    return mejor[1] if mejor else None


def entrenar(te, X, mov, a, f, b, plazo):
    """Ajuste con [a, f), umbral con [f, b − 61 min). Devuelve los parámetros del mes que empieza en b."""
    ia, if_, ib = (int(x) for x in np.searchsorted(te, [a, f, b - 61 * 60]))
    aj = slice(ia, if_)
    nz = mov[aj] != 0
    mu, de = X[aj].mean(0), X[aj].std(0) + 1e-9
    w = ajustar_logit(normalizar(X[aj], mu, de)[nz], (mov[aj] > 0).astype(float)[nz])
    pc = prob(w, normalizar(X[if_:ib], mu, de))
    return {"w": w, "mu": mu, "de": de, "tau": elegir_tau(pc, te[if_:ib], mov[if_:ib], plazo), "plazo": plazo}


def decidir(params, x):
    """Dirección (+1, −1 o 0) y probabilidad de subida para una fila de rasgos."""
    p = float(prob(params["w"], normalizar(x[None, :], params["mu"], params["de"]))[0])
    tau = params["tau"]
    if tau is None:
        return 0, p
    return (1 if p >= tau else -1 if p <= 1 - tau else 0), p
