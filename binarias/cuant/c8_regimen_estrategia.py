"""C8 (03/11/2026, 22:00): el «factor probabilístico» de la racha de la propia estrategia, y E1 (familia de reversión).

Pregunta de Nicolás (03/11): ¿hay un factor probabilístico del comportamiento que acierte a futuro? Su plan: operar en
real solo los días en que la estrategia está dando resultados. Reglas escritas antes de ver resultados:
1. Corrección de C7: la «ruptura al revés» en BTC se mide entrando 60 s tarde (cierre del minuto siguiente a la señal y
   vencimiento 10 min después), como él tocaría a mano. Empate = fallo.
2. Factor probabilístico (HMM de la racha): modelo oculto de Markov de 2 estados (racha buena, racha mala) con salidas
   de acierto o fallo (Bernoulli), ajustado con Baum-Welch solo con las apuestas de 2021-2023. Después se FILTRA hacia
   adelante: al empezar cada día de Colombia, probabilidad de estar en racha buena con lo visto hasta ese momento.
   Semáforo H: VERDE si esa probabilidad es 0,5 o más. Se compara en 2024 a sep-2026 y oct-2026 con el semáforo S2
   (últimas 100 en 58 % o más), con «siempre» y con días al azar (la misma cantidad de días). Entra al semáforo de los
   equipos solo si supera a S2 en la prueba por 0,5 puntos o más con al menos tantos días encendidos.
3. E1 (PLAN-v5, sección 7): apuesta si dispara la ruptura al revés, el impulso de 15 min al revés (|z| > 1) o la anomalía
   de 10 min al revés (z robusto >= 4), y ninguna contradice a otra. Entra si en la prueba da 56 % o más con 4 o más
   apuestas al día y Wilson sobre 54,05 %, y en oct-2026 no baja de 54 %. Medido con entrada 60 s tarde.
Uso: python -I c8_regimen_estrategia.py
"""
import datetime as dt
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
COL = dt.timezone(dt.timedelta(hours=-5))
EQ = B.EQUILIBRIO


def resultado_tarde(t1, c1, td, sentido):
    """Acierto entrando 60 s tarde: entrada = cierre del minuto que termina en td+60; salida = 10 min después."""
    i_ent = np.searchsorted(t1, td) # vela que empieza en td (termina en td+60)
    ok = (i_ent + 10 < len(t1))
    i_ent = np.minimum(i_ent, len(t1) - 11)
    ok &= (t1[i_ent] == td) & (t1[i_ent + 10] == td + 600)
    mov = c1[i_ent + 10] - c1[i_ent]
    gana = (np.sign(mov) == sentido) & (sentido != 0)
    return gana.astype(int), ok


def hmm_bernoulli(x, iters=60):
    """Baum-Welch de 2 estados con salidas 0/1. Devuelve (p_acierto por estado, matriz de paso, pi) con el estado 1 = bueno."""
    p = np.array([0.50, 0.62])
    A = np.array([[0.98, 0.02], [0.02, 0.98]])
    pi = np.array([0.5, 0.5])
    T = len(x)
    for _ in range(iters):
        b = np.where(x[:, None] == 1, p[None, :], 1 - p[None, :])
        alfa = np.zeros((T, 2)); c = np.zeros(T)
        a = pi * b[0]; c[0] = a.sum(); alfa[0] = a / c[0]
        for t in range(1, T):
            a = (alfa[t - 1] @ A) * b[t]; c[t] = a.sum(); alfa[t] = a / c[t]
        beta = np.ones((T, 2))
        for t in range(T - 2, -1, -1):
            beta[t] = (A @ (b[t + 1] * beta[t + 1])) / c[t + 1]
        g = alfa * beta; g /= g.sum(axis=1, keepdims=True)
        xi = np.zeros((2, 2))
        for t in range(T - 1):
            m = (alfa[t][:, None] * A) * (b[t + 1] * beta[t + 1])[None, :]
            xi += m / m.sum()
        A = xi / xi.sum(axis=1, keepdims=True)
        pi = g[0]
        p = np.clip((g * x[:, None]).sum(axis=0) / g.sum(axis=0), 0.01, 0.99)
    if p[0] > p[1]:
        p, A, pi = p[::-1], A[::-1, ::-1], pi[::-1]
    return p, A, pi


def filtrar(x, p, A, pi):
    """P(racha buena) ANTES de ver cada apuesta (solo con las anteriores)."""
    out = np.zeros(len(x))
    a = pi.copy()
    for t in range(len(x)):
        pred = a @ A if t else a
        out[t] = pred[1] / pred.sum()
        b = np.array([p[0] if x[t] else 1 - p[0], p[1] if x[t] else 1 - p[1]])
        a = pred * b
        a /= a.sum()
    return out


def por_dia(t):
    return np.array([dt.datetime.fromtimestamp(int(x), COL).strftime("%Y-%m-%d") for x in t])


def evaluar_semaforo(dias, gana, tramo, encendido_dia, nombre, L, rng):
    """encendido_dia: dict día -> bool (decidido al empezar el día). Mide en prueba (1) y adelante (2)."""
    for j, nt in ((1, "prueba"), (2, "adelante")):
        m = tramo == j
        dj = dias[m]; gj = gana[m]
        on = np.array([encendido_dia.get(d, False) for d in dj])
        n_on, n_all = int(on.sum()), len(gj)
        acc_on = gj[on].mean() if n_on else float("nan")
        unicos = np.unique(dj)
        dias_on = [d for d in unicos if encendido_dia.get(d, False)]
        # azar: misma cantidad de días
        accs = []
        for _ in range(300):
            elegidos = set(rng.choice(unicos, size=len(dias_on), replace=False)) if dias_on else set()
            mm = np.array([d in elegidos for d in dj])
            if mm.any():
                accs.append(gj[mm].mean())
        p = float(np.mean(np.array(accs) >= acc_on)) if accs and n_on else float("nan")
        L.append(f"   {nombre:<26} {nt:<9} días encendidos {len(dias_on):>4}/{len(unicos):<4} · apuestas {n_on:>6,} · acierto {pct(acc_on)} "
                 f"(siempre {pct(gj.mean())}; azar mismos días {pct(np.mean(accs)) if accs else '–'}, p = {es(p, 3)})".replace(",", "."))


def main():
    sim = "BTCUSDT"
    d = datos(sim)
    t1, o1, h1, l1, c1, v1, tb1 = B.cargar(sim)
    td, tr, F, E = d["t"], d["tramo"], d["F"], d["extra"]
    rng = np.random.default_rng(3112026)
    L = [f"C8 · {sim} · el factor probabilístico de la racha (HMM) y E1, con entrada 60 s tarde", ""]
    # señales de la familia de reversión
    rup = np.where(F["ruptura"] == 0, -1, np.where(F["ruptura"] == 1, 1, 0))
    imp = np.where(F["impulso"] == 0, 1, np.where(F["impulso"] == 1, -1, 0))
    lp = np.log(E["precio"]); r = np.r_[np.nan, np.diff(lp)]
    consec = np.r_[False, np.diff(td) == 600]
    med = np.full(len(r), np.nan); mad = np.full(len(r), np.nan)
    for a in range(4320, len(r), 144):
        seg = r[a - 4320:a]; seg = seg[~np.isnan(seg)]
        if len(seg) > 1000:
            m_ = np.median(seg); med[a:a + 144] = m_; mad[a:a + 144] = np.median(np.abs(seg - m_)) * 1.4826
    z = (r - med) / (mad + 1e-12)
    ano = np.where(consec & (np.abs(z) >= 4), -np.sign(z), 0).astype(int)
    # 1) ruptura al revés con 60 s de retraso
    g_rup, ok_rup = resultado_tarde(t1, c1, td, rup)
    L.append("1. RUPTURA AL REVÉS (núcleo), entrada 60 s tarde:")
    for j, nt in enumerate(("entrenamiento", "prueba", "adelante")):
        m = (rup != 0) & ok_rup & (tr == j)
        n = int(m.sum()); k = int(g_rup[m].sum())
        L.append(f"   {nt:<14} {n:>6,} apuestas · acierto {pct(k / n if n else float('nan'))} · Wilson {pct(V.wilson(k, n)[0])}".replace(",", "."))
    # 2) HMM de la racha
    sel = (rup != 0) & ok_rup & (tr >= 0)
    t_b, g_b, tr_b = td[sel], g_rup[sel], tr[sel]
    dias_b = por_dia(t_b)
    p, A, pi = hmm_bernoulli(g_b[tr_b == 0].astype(float))
    L.append("")
    L.append(f"2. HMM DE LA RACHA (ajustado con 2021-2023): acierto en racha buena {pct(p[1])}, en racha mala {pct(p[0])}; "
             f"permanencia: buena {pct(A[1, 1])}, mala {pct(A[0, 0])} (duración media {es(1 / max(1 - A[1, 1], 1e-9), 0)} y {es(1 / max(1 - A[0, 0], 1e-9), 0)} apuestas)")
    pb = filtrar(g_b.astype(float), p, A, pi)
    # decisión al empezar cada día: la probabilidad antes de la primera apuesta del día
    enc_H, enc_S2, enc_siempre = {}, {}, {}
    _, ini = np.unique(dias_b, return_index=True)
    for i0 in sorted(ini):
        dia = dias_b[i0]
        enc_H[dia] = pb[i0] >= 0.5
        prev = g_b[:i0][-100:]
        enc_S2[dia] = len(prev) >= 100 and prev.mean() >= 0.58
        enc_siempre[dia] = True
    evaluar_semaforo(dias_b, g_b, tr_b, enc_siempre, "siempre (sin semáforo)", L, rng)
    evaluar_semaforo(dias_b, g_b, tr_b, enc_S2, "S2 (últimas 100 >= 58 %)", L, rng)
    evaluar_semaforo(dias_b, g_b, tr_b, enc_H, "H (HMM: P(buena) >= 0,5)", L, rng)
    # persistencia: acierto de las últimas 100 frente al del día siguiente (prueba)
    xs, ys = [], []
    for i0 in sorted(ini):
        if tr_b[i0] != 1 or i0 < 100:
            continue
        dia = dias_b[i0]
        hoy = g_b[dias_b == dia]
        xs.append(g_b[i0 - 100:i0].mean()); ys.append(hoy.mean())
    if len(xs) > 30:
        rho = np.corrcoef(xs, ys)[0, 1]
        L.append(f"   persistencia en la prueba: correlación entre el acierto de las últimas 100 y el del día siguiente = {es(rho, 3)} "
                 f"(n {len(xs)} días; con n así, |r| > {es(1.96 / math.sqrt(len(xs)), 3)} no es ruido)")
    # 3) E1 familia de reversión
    L.append("")
    voto = np.zeros(len(td), int)
    hay = np.zeros(len(td), int)
    for s in (rup, imp, ano):
        voto += s; hay += (s != 0)
    e1 = np.where((hay > 0) & (np.abs(voto) == hay), np.sign(voto), 0)
    g_e1, ok_e1 = resultado_tarde(t1, c1, td, e1)
    L.append("3. E1 · FAMILIA DE REVERSIÓN (ruptura, impulso y anomalía al revés; sin contradicciones), entrada 60 s tarde:")
    res = {}
    for j, nt in enumerate(("entrenamiento", "prueba", "adelante")):
        m = (e1 != 0) & ok_e1 & (tr == j)
        n = int(m.sum()); k = int(g_e1[m].sum())
        dias_t = max(1.0, (td[tr == j].max() - td[tr == j].min()) / 86400) if (tr == j).any() else 1.0
        res[nt] = (k / n if n else float("nan"), n / dias_t, V.wilson(k, n)[0])
        L.append(f"   {nt:<14} {n:>6,} apuestas · {n / dias_t:4.1f} al día · acierto {pct(k / n if n else float('nan'))} · Wilson {pct(V.wilson(k, n)[0])}".replace(",", "."))
    pasa = res["prueba"][0] >= 0.56 and res["prueba"][1] >= 4 and res["prueba"][2] > EQ and res["adelante"][0] >= 0.54
    L.append(f"   Veredicto E1 (regla escrita antes): {'ENTRA' if pasa else 'NO ENTRA'} · prueba {pct(res['prueba'][0])} con {es(res['prueba'][1], 1)} al día "
             f"y Wilson {pct(res['prueba'][2])}; adelante {pct(res['adelante'][0])}.")
    # coherencia interna: cuando dos miembros disparan a la vez, ¿apuntan al mismo lado?
    ambos = (rup != 0) & (imp != 0)
    L.append(f"   Coherencia de la familia: cuando la ruptura y el impulso disparan a la vez, coinciden en el sentido el "
             f"{pct(np.mean(rup[ambos] == imp[ambos]))} de las veces ({int(ambos.sum()):,} casos).".replace(",", "."))
    os.makedirs(SALIDA, exist_ok=True)
    texto = "\n".join(L)
    open(os.path.join(SALIDA, f"c8_{sim}.txt"), "w", encoding="utf-8").write(texto + "\n")
    np.save(os.path.join(SALIDA, "c8_hmm_racha.npy"), np.array({"p": p, "A": A, "pi": pi}, dtype=object))
    print(texto)


if __name__ == "__main__":
    main()
