"""Modelo unificado de las binarias (PLAN.md, sección 11): una sola fuente para t25 y para el centinela.

Una regresión logística por activo (BTCUSDT y ETHUSDT) en cada cierre de vela de 5 min, a 10 min. Rasgos, todos con datos
anteriores a la entrada:
- los del modelo de t19 (motor/modelo.rasgos: rendimientos, volatilidad, volumen, rangos, medias, vela, hora y grupo A);
- las señales de los grupos C y E;
- el otro activo: rendimientos de 1 a 60 min, rendimiento relativo, cuerpo de su vela de 5 min y su posición en el rango de 4 h;
- el flujo de órdenes: proporción de compras agresivas (taker buy) en 1, 5, 15 y 60 min, del activo y del otro.
Por mes: ajuste con M-12 a M-4, umbral con M-3 a M-1 (solo apuestas vencidas antes de M) y operación de M. El umbral es el que más
hace crecer la cuenta en la calibración entre los que dan al menos `min_dia` apuestas al día; si ninguno crece con esa frecuencia,
el que más crezca; si ninguno crece, ese activo no apuesta ese mes. En cada cierre se apuesta el activo cuya probabilidad esté
más lejos de 0,5 entre los que pasan su umbral."""
import math

import numpy as np

from . import modelo as MOD
from . import senales as SEN

ACTIVOS = ("BTCUSDT", "ETHUSDT")
PLAZO = 10
MIN_DIA = 2.0


def alinear(A, B):
    """Recorta dos series de 1 min (7 columnas: ms, o, h, l, c, v, compras agresivas) al mismo rango de minutos."""
    t0, t1 = max(A[0, 0], B[0, 0]), min(A[-1, 0], B[-1, 0])
    ia0, ia1 = np.searchsorted(A[:, 0], [t0, t1])
    ib0, ib1 = np.searchsorted(B[:, 0], [t0, t1])
    A, B = A[ia0:ia1 + 1], B[ib0:ib1 + 1]
    assert len(A) == len(B) and A[0, 0] == B[0, 0] and A[-1, 0] == B[-1, 0], "las dos series no están alineadas"
    return A, B


def rasgos(A, B, vivo=False):
    """A: el activo; B: el otro, alineados minuto a minuto. Devuelve tiempos de entrada, índices del minuto de entrada, rasgos y
    nombres."""
    t = (A[:, 0] // 1000).astype(np.int64)
    o, h, l, c, v = (A[:, j] for j in range(1, 6))
    te, k, X1, n1 = MOD.rasgos(t, o, h, l, c, v, vivo=vivo)
    F, nombres = [], []
    S, _, _ = SEN.senales_AC(t, o, h, l, c)
    S.update(SEN.senales_E(t, o, h, l, c))
    for nom, (g, ts, ds) in S.items():
        if g == "A":
            continue
        x = np.zeros(len(te))
        ts = np.asarray(ts, dtype=np.int64)
        i = np.searchsorted(te, ts)
        bien = i < len(te)
        bien[bien] &= te[i[bien]] == ts[bien]
        x[i[bien]] = np.asarray(ds, dtype=float)[bien]
        F.append(x)
        nombres.append(nom)
    j = k - 1

    def sig240(lc):
        r1 = np.r_[0.0, np.diff(lc)]
        R, Q = np.cumsum(r1), np.cumsum(r1 * r1)
        m = (R[j] - R[j - 240]) / 240
        return np.sqrt(np.maximum((Q[j] - Q[j - 240]) / 240 - m * m, 1e-14))

    lcA, lcB = np.log(A[:, 4]), np.log(B[:, 4])
    sA, sB = sig240(lcA), sig240(lcB)
    rA = {n: (lcA[j] - lcA[j - n]) / (sA * math.sqrt(n)) for n in (1, 5, 15, 60)}
    rB = {n: (lcB[j] - lcB[j - n]) / (sB * math.sqrt(n)) for n in (1, 5, 15, 60)}
    for n in (1, 5, 15, 60):
        F.append(rB[n])
        nombres.append(f"otro activo {n} min")
    for n in (5, 15, 60):
        F.append(rA[n] - rB[n])
        nombres.append(f"relativo al otro {n} min")
    tB = (B[:, 0] // 1000).astype(np.int64)
    T5, O5, H5, L5, C5 = SEN.velas(tB, B[:, 1], B[:, 2], B[:, 3], B[:, 4], 300)
    i5 = np.clip(np.searchsorted(T5 + 300, te), 0, len(T5) - 1)
    bien5 = (T5[i5] + 300) == te
    with np.errstate(invalid="ignore", divide="ignore"):
        rg = np.maximum(H5 - L5, 1e-9)
        hi, lo = SEN.rodante(H5, 48, np.max), SEN.rodante(L5, 48, np.min)
        pos = np.nan_to_num((C5 - lo) / (hi - lo), nan=0.5)
    F.append(np.where(bien5, ((C5 - O5) / rg)[i5], 0.0))
    nombres.append("cuerpo de la vela del otro")
    F.append(np.where(bien5, pos[i5], 0.5))
    nombres.append("posición del otro en el rango de 4 h")
    for arr, quien in ((A, "propias"), (B, "del otro")):
        V, TB = np.cumsum(arr[:, 5]), np.cumsum(arr[:, 6])
        for n in (1, 5, 15, 60):
            vol, tbn = V[j] - V[j - n], TB[j] - TB[j - n]
            F.append(np.where(vol > 0, (2 * tbn - vol) / np.maximum(vol, 1e-12), 0.0))
            nombres.append(f"compras agresivas {quien} {n} min")
    X = np.column_stack([X1] + [np.nan_to_num(f, nan=0.0, posinf=0.0, neginf=0.0) for f in F])
    return te, k, X, n1 + nombres


def elegir_tau(pc, te, mov, dias, min_dia=MIN_DIA, plazo=PLAZO):
    mejor_f = mejor = None
    for tau in MOD.TAUS:
        d = np.where(pc >= tau, 1, np.where(pc <= 1 - tau, -1, 0))
        m = d != 0
        tw = te[m]
        if len(tw) < 100:
            continue
        keep = np.r_[True, np.diff(tw) >= plazo * 60]
        r = np.sign(d[m][keep] * mov[m][keep])
        n, w = len(r), int((r > 0).sum())
        gro = w * MOD.LG + (n - w) * MOD.LP
        if n < 100 or gro <= 0:
            continue
        if n / dias >= min_dia and (mejor_f is None or gro > mejor_f[0]):
            mejor_f = (gro, float(tau))
        if mejor is None or gro > mejor[0]:
            mejor = (gro, float(tau))
    elegido = mejor_f or mejor
    return elegido[1] if elegido else None


def entrenar(te, X, mov, a, f, b, min_dia=MIN_DIA, columnas=None):
    """Ajuste con [a, f), umbral con [f, b − 61 min). `columnas` permite quitar grupos de rasgos (solo para la sensibilidad)."""
    if columnas is not None:
        X = X[:, columnas]
    ia, if_, ib = (int(x) for x in np.searchsorted(te, [a, f, b - 61 * 60]))
    aj = slice(ia, if_)
    nz = mov[aj] != 0
    mu, de = X[aj].mean(0), X[aj].std(0) + 1e-9
    w = MOD.ajustar_logit(MOD.normalizar(X[aj], mu, de)[nz], (mov[aj] > 0).astype(float)[nz])
    pc = MOD.prob(w, MOD.normalizar(X[if_:ib], mu, de))
    dias = max(1.0, (b - 61 * 60 - f) / 86400)
    return {"w": w, "mu": mu, "de": de, "tau": elegir_tau(pc, te[if_:ib], mov[if_:ib], dias, min_dia), "plazo": PLAZO, "columnas": columnas}


def probabilidad(par, X):
    if par.get("columnas") is not None:
        X = X[:, par["columnas"]]
    return MOD.prob(np.asarray(par["w"]), MOD.normalizar(X, np.asarray(par["mu"]), np.asarray(par["de"])))


def elegir_apuesta(probs):
    """probs: {activo: (probabilidad de subida, umbral)}. Devuelve (activo, dirección, probabilidad) o None."""
    cands = []
    for a, (p, tau) in probs.items():
        if tau is None or p is None:
            continue
        if p >= tau:
            cands.append((p - 0.5, a, 1, p))
        elif p <= 1 - tau:
            cands.append((0.5 - p, a, -1, p))
    if not cands:
        return None
    cands.sort(key=lambda x: (-x[0], x[1]))
    return cands[0][1], cands[0][2], cands[0][3]
