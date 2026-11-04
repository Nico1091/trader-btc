"""C2 (03/11/2026): regímenes, Markov, HMM, agrupamiento, autocorrelación, anomalías y rachas. A ciegas.

Regla escrita antes de ver resultados (igual que C1): se ajusta con 2021-2023 y se juzga intacto en 2024 a septiembre
de 2026 (prueba) y octubre de 2026 (adelante). Binaria de 10 min, una decisión cada 10 min, empate = fallo.
1. Cadena de Markov: el siguiente tramo de 10 min según el signo de los 1, 2 y 3 tramos anteriores.
2. HMM gaussiano de 3 estados (código propio, Baum-Welch) sobre velas de 1 h (rendimiento y rango). Se ajusta con
   2021-2023 y después solo se FILTRA hacia adelante (sin mirar el futuro). Se mide el acierto por régimen.
3. Agrupamiento k-medias (k = 8) del comportamiento: impulso, dirección de 1 h, 4 h y 1 día, volatilidad, volumen y
   flujo de órdenes. Sentido de cada grupo elegido en entrenamiento.
4. Autocorrelación y razón de varianzas (Lo y MacKinlay, robusta a heterocedasticidad) de los rendimientos de 10 min.
5. Anomalías: movimiento de 10 min con z robusto (mediana y MAD de 30 días) de 3, 4 o 5 o más; ¿se devuelve?
6. Rachas en las secuencias reales de apuestas a ciegas (t18 y t19): ¿acertar sube la probabilidad de acertar la
   siguiente? Es la prueba de su idea de operar «cuando hay suerte».
Uso: python -I c2_regimenes.py [BTCUSDT ETHUSDT]
"""
import math
import os
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base as B  # noqa: E402
import validacion as V  # noqa: E402
from c1_cruces import datos, es, pct  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "resultados")
PRUEBAS = os.path.join(B.RAIZ, "pruebas")
TRAMO = ("entrenamiento", "prueba", "adelante")


def acierto_por(estado, sentido, y, tr, j):
    m = (tr == j) & (sentido != 0)
    n = int(m.sum())
    return (float(np.mean(y[m] == sentido[m])) if n else float("nan")), n


def sentido_por_grupo(g, y, tr, k):
    s = np.zeros(k, int)
    for c in range(k):
        m = (tr == 0) & (g == c)
        s[c] = 1 if np.sum(y[m] == 1) >= np.sum(y[m] == -1) else -1
    return s


# ---------------------------------------------------------------- HMM gaussiano propio
def hmm_ajustar(X, k=3, iters=25, semilla=3112026):
    T, D = X.shape
    orden = np.argsort(X[:, 1])  # se arranca ordenando por rango (calma → agitado)
    mu = np.array([X[orden[int((i + 0.5) * T / k)]] for i in range(k)])
    var = np.tile(X.var(axis=0), (k, 1))
    A = np.full((k, k), 0.05 / (k - 1))
    np.fill_diagonal(A, 0.95)
    pi = np.full(k, 1.0 / k)
    for _ in range(iters):
        logb = -0.5 * (((X[:, None, :] - mu[None]) ** 2) / var[None] + np.log(2 * np.pi * var[None])).sum(axis=2)
        b = np.exp(logb - logb.max(axis=1, keepdims=True))
        alfa = np.zeros((T, k))
        c = np.zeros(T)
        a = pi * b[0]
        c[0] = a.sum()
        alfa[0] = a / c[0]
        for t in range(1, T):
            a = (alfa[t - 1] @ A) * b[t]
            c[t] = a.sum()
            alfa[t] = a / c[t]
        beta = np.ones((T, k))
        for t in range(T - 2, -1, -1):
            beta[t] = (A @ (b[t + 1] * beta[t + 1])) / c[t + 1]
        gamma = alfa * beta
        gamma /= gamma.sum(axis=1, keepdims=True)
        xi = np.zeros((k, k))
        for t in range(T - 1):
            x = (alfa[t][:, None] * A) * (b[t + 1] * beta[t + 1])[None, :]
            xi += x / x.sum()
        A = xi / xi.sum(axis=1, keepdims=True)
        pi = gamma[0]
        w = gamma.sum(axis=0)
        mu = (gamma.T @ X) / w[:, None]
        var = np.maximum((gamma.T @ (X ** 2)) / w[:, None] - mu ** 2, 1e-12)
    o = np.argsort(mu[:, 1])  # estado 0 = el de menor rango
    return {"mu": mu[o], "var": var[o], "A": A[np.ix_(o, o)], "pi": pi[o]}


def hmm_filtrar(X, P):
    """Probabilidad de cada régimen en cada hora usando solo lo visto hasta esa hora."""
    mu, var, A, pi = P["mu"], P["var"], P["A"], P["pi"]
    k = len(pi)
    logb = -0.5 * (((X[:, None, :] - mu[None]) ** 2) / var[None] + np.log(2 * np.pi * var[None])).sum(axis=2)
    b = np.exp(logb - logb.max(axis=1, keepdims=True))
    out = np.zeros((len(X), k))
    a = pi * b[0]
    out[0] = a / a.sum()
    for t in range(1, len(X)):
        a = (out[t - 1] @ A) * b[t]
        out[t] = a / a.sum()
    return out


def velas_hora(sim):
    t, o, h, l, c, v, tb = B.cargar(sim)
    hr = t // 3600
    corte = np.flatnonzero(np.diff(hr)) + 1
    ini, fin = np.r_[0, corte], np.r_[corte, len(t)] - 1
    H = np.maximum.reduceat(h, ini)
    L = np.minimum.reduceat(l, ini)
    return hr[ini], o[ini], H, L, c[fin], fin - ini + 1


# ---------------------------------------------------------------- k-medias propio
def kmedias(X, k=8, iters=40, semilla=3112026):
    rng = np.random.default_rng(semilla)
    C = [X[rng.integers(len(X))]]
    for _ in range(1, k):
        d2 = np.min(((X[:, None, :] - np.array(C)[None]) ** 2).sum(axis=2), axis=1)
        C.append(X[rng.choice(len(X), p=d2 / d2.sum())])
    C = np.array(C)
    for _ in range(iters):
        g = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(axis=2), axis=1)
        C = np.array([X[g == j].mean(axis=0) if np.any(g == j) else C[j] for j in range(k)])
    return C


def asignar(X, C):
    out = np.empty(len(X), int)
    for a in range(0, len(X), 50000):
        out[a:a + 50000] = np.argmin(((X[a:a + 50000, None, :] - C[None]) ** 2).sum(axis=2), axis=1)
    return out


def razon_varianzas(r, q):
    """Lo y MacKinlay (1988), z robusta a heterocedasticidad."""
    r = r - r.mean()
    n = len(r)
    var1 = np.mean(r ** 2)
    rq = np.convolve(r, np.ones(q), "valid")
    varq = np.mean(rq ** 2) / q
    vr = varq / var1
    delta = 0.0
    for j in range(1, q):
        dj = np.sum((r[j:] ** 2) * (r[:-j] ** 2)) / (np.sum(r ** 2) ** 2) * n
        delta += (2 * (q - j) / q) ** 2 * dj
    z = (vr - 1) / math.sqrt(delta / n) if delta > 0 else 0.0
    return vr, z


def estudio(sim):
    d = datos(sim)
    y, tr, t, F, E = d["y"].astype(int), d["tramo"], d["t"], d["F"], d["extra"]
    L = [f"C2 · {sim} · regímenes, Markov, HMM, agrupamiento, autocorrelación, anomalías y rachas", ""]
    consec = np.r_[False, np.diff(t) == 600]
    # 1. Markov
    L.append("1. CADENA DE MARKOV (signo de los tramos de 10 min anteriores → siguiente)")
    prev = [np.r_[np.zeros(k, int), y[:-k]] for k in (1, 2, 3)]
    ok3 = consec & np.r_[False, consec[:-1]] & np.r_[False, False, consec[:-2]]
    for orden in (1, 2, 3):
        patrones = {}
        for idx in np.ndindex(*([2] * orden)):
            m = ok3.copy()
            for j, s in enumerate(idx):
                m &= prev[j] == (1 if s == 0 else -1)
            patrones[idx] = m
        filas = []
        for idx, m in patrones.items():
            m0 = m & (tr == 0)
            s = 1 if np.sum(y[m0] == 1) >= np.sum(y[m0] == -1) else -1
            accs = [np.mean(y[m & (tr == j)] == s) if np.any(m & (tr == j)) else float("nan") for j in range(3)]
            etiqueta = "".join("▲" if x == 0 else "▼" for x in idx[::-1])
            filas.append(f"{etiqueta}→{'SUBE' if s == 1 else 'BAJA'} {pct(accs[0])}/{pct(accs[1])}/{pct(accs[2])}")
        L.append(f"   orden {orden}: " + " · ".join(filas))
    # 2. HMM
    L.append("")
    L.append("2. HMM GAUSSIANO DE 3 REGÍMENES (velas de 1 h; ajuste 2021-23, filtrado hacia adelante)")
    hr, O, H, Lw, C, nmin = velas_hora(sim)
    X = np.column_stack([np.log(C / O), np.log(np.maximum(H / Lw, 1 + 1e-9))])
    a21, a24 = 1609459200 // 3600, 1704067200 // 3600
    entreno = (hr >= a21) & (hr < a24)
    P = hmm_ajustar(X[entreno])
    filt = hmm_filtrar(X, P)
    reg_h = np.argmax(filt, axis=1)
    pos = np.searchsorted(hr, t // 3600) - 1  # última hora cerrada antes de la decisión
    regimen = np.where(pos >= 0, reg_h[np.maximum(pos, 0)], -1)
    nombres = ["calma", "normal", "agitado"]
    L.append("   medias por régimen (rendimiento %, rango %): " + " · ".join(
        f"{nombres[j]} {es(100 * P['mu'][j, 0], 3)} / {es(100 * math.exp(P['mu'][j, 1]) - 100, 2)}" for j in range(3)))
    L.append("   permanencia (probabilidad de seguir en el mismo régimen la hora siguiente): " + " · ".join(f"{nombres[j]} {pct(P['A'][j, j])}" for j in range(3)))
    imp = F["impulso"]
    rev = np.where(imp == 0, 1, np.where(imp == 1, -1, 0))  # la reversión de 15 min (base de REV)
    for j in range(3):
        m = regimen == j
        base = [np.mean(y[m & (tr == q)] == 1) if np.any(m & (tr == q)) else float("nan") for q in range(3)]
        accs = [acierto_por(None, np.where(m, rev, 0), y, tr, q) for q in range(3)]
        L.append(f"   {nombres[j]:<8} sube {pct(base[0])}/{pct(base[1])}/{pct(base[2])} · reversión de 15 min: "
                 f"{pct(accs[0][0])} ({accs[0][1]:,}) / {pct(accs[1][0])} ({accs[1][1]:,}) / {pct(accs[2][0])} ({accs[2][1]:,})".replace(",", "."))
    ultimo = filt[-1]
    L.append(f"   régimen de la última hora de los datos: {nombres[int(np.argmax(ultimo))]} ({pct(ultimo.max())})")
    # 3. k-medias
    L.append("")
    L.append("3. AGRUPAMIENTO K-MEDIAS DEL COMPORTAMIENTO (k = 8; sentido de cada grupo elegido en 2021-23)")
    sd = E["sd1"] + 1e-12
    Z = np.column_stack([E["z15"], E["a60"] / (sd * math.sqrt(60)), E["a240"] / (sd * math.sqrt(240)), E["a1d"] / (sd * math.sqrt(1440)),
                         np.log(np.clip(E["razon_atr"], 0.05, 20)), np.log(np.clip(E["rv"], 0.05, 20)), E["delta"]])
    Z = np.nan_to_num(Z)
    mu_z, sd_z = Z[tr == 0].mean(axis=0), Z[tr == 0].std(axis=0) + 1e-12
    Zs = (Z - mu_z) / sd_z
    rng = np.random.default_rng(3112026)
    idx0 = np.flatnonzero(tr == 0)
    Cc = kmedias(Zs[rng.choice(idx0, min(60000, len(idx0)), replace=False)])
    g = asignar(Zs, Cc)
    sg = sentido_por_grupo(g, y, tr, 8)
    for c in range(8):
        m = g == c
        accs = [np.mean(y[m & (tr == q)] == sg[c]) if np.any(m & (tr == q)) else float("nan") for q in range(3)]
        rasgo = ", ".join(f"{n_} {es(v_, 1)}" for n_, v_ in zip(("imp", "1h", "4h", "1d", "atr", "vol", "flujo"), Cc[c]))
        L.append(f"   grupo {c} ({np.mean(m[tr == 0]) * 100:4.1f} %) {'SUBE' if sg[c] == 1 else 'BAJA'}: {pct(accs[0])}/{pct(accs[1])}/{pct(accs[2])} · centro: {rasgo}")
    # 4. autocorrelación
    L.append("")
    L.append("4. AUTOCORRELACIÓN Y RAZÓN DE VARIANZAS (rendimientos de 10 min)")
    lp = np.log(E["precio"])
    r = np.r_[np.nan, np.diff(lp)]
    for j, nom in enumerate(TRAMO[:2]):
        m = (tr == j) & consec
        rr = r[m]
        rr = rr[~np.isnan(rr)]
        acf = [np.corrcoef(rr[k:], rr[:-k])[0, 1] for k in range(1, 7)]
        ic = 1.96 / math.sqrt(len(rr))
        vrs = [razon_varianzas(rr, q) for q in (2, 3, 6)]
        L.append(f"   {nom}: autocorrelación lag 1-6: " + " ".join(es(a, 3) for a in acf) + f" (±{es(ic, 3)} es ruido) · "
                 + " · ".join(f"VR({q}) {es(v_, 3)} (z {es(z_, 1)})" for q, (v_, z_) in zip((2, 3, 6), vrs)))
    # 5. anomalías
    L.append("")
    L.append("5. ANOMALÍAS: tras un movimiento de 10 min fuera de lo normal, ¿se devuelve? (apostar en contra)")
    med = np.full(len(r), np.nan)
    mad = np.full(len(r), np.nan)
    for a in range(4320, len(r), 144):
        seg = r[a - 4320:a]
        seg = seg[~np.isnan(seg)]
        if len(seg) > 1000:
            m_ = np.median(seg)
            med[a:a + 144] = m_
            mad[a:a + 144] = np.median(np.abs(seg - m_)) * 1.4826
    zr = (r - med) / (mad + 1e-12)
    for umbral in (3, 4, 5):
        s = np.where(consec & (np.abs(zr) >= umbral), -np.sign(zr).astype(int), 0)
        accs = [acierto_por(None, s, y, tr, q) for q in range(3)]
        L.append(f"   |z| ≥ {umbral}: " + " / ".join(f"{pct(a_)} ({n_:,})".replace(",", ".") for a_, n_ in accs))
    # 6. rachas en las apuestas reales a ciegas
    L.append("")
    L.append("6. RACHAS EN LAS APUESTAS A CIEGAS DEL BANCO (¿operar «cuando hay suerte» sirve?)")
    for nombre in (f"t18_{sim}_apuestas.csv", f"t19_{sim}_apuestas.csv"):
        ruta = os.path.join(PRUEBAS, nombre)
        if not os.path.exists(ruta):
            continue
        lin = open(ruta, encoding="utf-8-sig").read().splitlines()
        cab = lin[0].split(";")
        jr = cab.index("resultado")
        x = [1 if f.split(";")[jr] == "acierta" else 0 for f in lin[1:]]
        R = V.rachas(x)
        L.append(f"   {nombre}: {R['n']:,} apuestas, acierto {pct(R['acierto'])} · tras acertar {pct(R['tras_1_acierto'][0])} · tras fallar {pct(R['tras_1_fallo'][0])} · "
                 f"tras 3 aciertos {pct(R['tras_3_aciertos'][0])} ({R['tras_3_aciertos'][1]:,}) · tras 3 fallos {pct(R['tras_3_fallos'][0])} ({R['tras_3_fallos'][1]:,}) · "
                 f"z de rachas {es(R['z'], 2)} · peor racha de fallos {R['peor_racha_de_fallos']}".replace(",", "."))
    os.makedirs(SALIDA, exist_ok=True)
    texto = "\n".join(L)
    open(os.path.join(SALIDA, f"c2_{sim}.txt"), "w", encoding="utf-8").write(texto + "\n")
    np.save(os.path.join(SALIDA, f"c2_{sim}_hmm.npy"), np.array({"mu": P["mu"], "var": P["var"], "A": P["A"], "pi": P["pi"]}, dtype=object))
    print(texto)


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["BTCUSDT", "ETHUSDT"]):
        estudio(s)
