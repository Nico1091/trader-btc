"""Base de la investigación cuantitativa de binarias (03/11/2026). Solo numpy y biblioteca estándar.

Construye, para BTCUSDT o ETHUSDT, una decisión cada 10 minutos (sin solapar plazos) con el resultado de la binaria de
10 min y los estados de las seis dimensiones pedidas por Nicolás el 03/11:
  1. Temporalidad: sesión (Asia, Europa, EE. UU., cierre) y fin de semana.
  2. Dirección: alineación de 1 h, 4 h y 1 día; impulso de 15 min frente a su volatilidad.
  3. Volatilidad: ATR de 5 min frente a su mediana de 30 días; contracción o expansión (ancho de Bollinger);
     ruptura del máximo o mínimo de 20 velas de 5 min.
  4. Liquidez y volumen: volumen de 15 min frente a su media de 7 días; flujo de órdenes (compra agresiva menos venta
     agresiva); barrido de liquidez (mecha que toma el máximo o mínimo de la hora previa y cierra dentro).
  5. Estructura: tendencia por estructura (último BOS), CHoCH reciente, FVG, order block, AMD (barrido del rango de Asia)
     y posición frente al área de valor del día anterior (AMT: VAH, POC, VAL).
  6. Estadística de resultados: se mide aparte (validacion.py): aciertos, fallos, expectativa, caída, rachas y reparto.
Todo se calcula solo con velas cerradas hasta el momento de la decisión. Empate = fallo.
"""
import datetime as dt
import os

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
PAGO = 0.85
EQUILIBRIO = 1 / (1 + PAGO)  # 54,05 %
TRAMOS = {  # en UTC
    "entrenamiento": (dt.datetime(2021, 1, 1), dt.datetime(2024, 1, 1)),
    "prueba": (dt.datetime(2024, 1, 1), dt.datetime(2026, 10, 1)),
    "adelante": (dt.datetime(2026, 10, 1), dt.datetime(2026, 11, 1)),
}


def _ts(d):
    return int(d.replace(tzinfo=dt.timezone.utc).timestamp())


def cargar(sim):
    a = np.load(os.path.join(DATOS, f"{sim}_um_1m_tb.npy"))
    t = (a[:, 0] // 1000).astype(np.int64)
    return t, a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5], a[:, 6]


def _rolling_max(x, n):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = sliding_window_view(x, n).max(axis=1)
    return out


def _rolling_min(x, n):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = sliding_window_view(x, n).min(axis=1)
    return out


def _rolling_mean(x, n):
    c = np.cumsum(np.insert(np.nan_to_num(x), 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def _rolling_median_sub(x, n, paso):
    """Mediana móvil aproximada: se calcula cada `paso` puntos y se repite (suficiente para normalizar)."""
    out = np.full(len(x), np.nan)
    for j in range(n, len(x), paso):
        m = np.nanmedian(x[j - n:j])
        out[j:j + paso] = m
    return out


def velas5(t, o, h, l, c, v, tb):
    """Velas de 5 min alineadas al reloj, con los índices de la vela de 1 min que las cierra."""
    k = (t // 300)
    corte = np.flatnonzero(np.diff(k)) + 1
    ini = np.r_[0, corte]
    fin = np.r_[corte, len(t)] - 1
    completas = (fin - ini) == 4
    ini, fin = ini[completas], fin[completas]
    O5, C5 = o[ini], c[fin]
    H5 = np.maximum.reduceat(h, ini)[:len(ini)] if False else np.array([h[a:b + 1].max() for a, b in zip(ini, fin)])
    L5 = np.array([l[a:b + 1].min() for a, b in zip(ini, fin)])
    cv, ctb = np.cumsum(np.r_[0, v]), np.cumsum(np.r_[0, tb])
    V5 = cv[fin + 1] - cv[ini]
    TB5 = ctb[fin + 1] - ctb[ini]
    return t[ini], O5, H5, L5, C5, V5, TB5, fin


def construir(sim, verbose=True, velas=None, minimo=2 * 1440 * 31, sin_futuro=False):
    """`velas`: (t, o, h, l, c, v, tb) en vez del archivo (lectura en vivo). `sin_futuro`: incluye las últimas decisiones
    aunque su resultado de 10 min todavía no exista (y = 0)."""
    t, o, h, l, c, v, tb = velas if velas is not None else cargar(sim)
    n = len(t)
    if verbose:
        print(f"{sim}: {n:,} velas de 1 min de {dt.datetime.utcfromtimestamp(t[0]):%Y-%m-%d} a {dt.datetime.utcfromtimestamp(t[-1]):%Y-%m-%d %H:%M}")
    # ---- decisiones cada 10 min: cierre de la vela que termina en múltiplo de 600 s
    fin_vela = t + 60
    if sin_futuro:
        i_dec = np.flatnonzero((fin_vela % 600 == 0) & (np.arange(n) >= minimo))
        mov = np.array([c[i + 10] - c[i] if i + 10 < n else 0.0 for i in i_dec])
    else:
        i_dec = np.flatnonzero((fin_vela % 600 == 0) & (np.arange(n) >= minimo) & (np.arange(n) + 10 < n))
        ok = (t[i_dec + 10] - t[i_dec]) == 600
        i_dec = i_dec[ok]
        mov = c[i_dec + 10] - c[i_dec]
    y = np.sign(mov).astype(np.int8)  # +1 sube, -1 baja, 0 empate (= fallo para cualquier lado)
    td = t[i_dec] + 60  # hora de la decisión (cierre de la vela)
    F = {}
    # ---- 1. temporalidad
    hora = (td % 86400) // 3600
    F["sesion"] = np.select([hora < 8, hora < 13, hora < 21], [0, 1, 2], 3).astype(np.int8)  # Asia, Europa, EE. UU., cierre
    dia = ((td // 86400) + 4) % 7  # 0 = lunes
    F["finde"] = (dia >= 5).astype(np.int8)
    # ---- 2. dirección
    lc = np.log(c)
    r1 = np.diff(lc, prepend=lc[0])
    sd1 = np.sqrt(_rolling_mean(r1 ** 2, 1440))  # volatilidad de 1 min del último día
    def ret(k):
        return lc[i_dec] - lc[i_dec - k]
    a60, a240, a1d = ret(60), ret(240), ret(1440)
    F["direccion"] = np.select([(a60 > 0) & (a240 > 0) & (a1d > 0), (a60 < 0) & (a240 < 0) & (a1d < 0)], [0, 1], 2).astype(np.int8)  # alcista, bajista, mixta
    z15 = ret(15) / (sd1[i_dec] * np.sqrt(15) + 1e-12)
    F["impulso"] = np.select([z15 < -1, z15 > 1], [0, 1], 2).astype(np.int8)  # cayó, subió, plano
    # ---- velas de 5 min para volatilidad y estructura
    T5, O5, H5, L5, C5, V5, TB5, fin5 = velas5(t, o, h, l, c, v, tb)
    j5 = np.searchsorted(fin5, i_dec, side="right") - 1  # última vela de 5 min cerrada en la decisión
    tr = np.maximum(H5 - L5, np.maximum(np.abs(H5 - np.r_[C5[0], C5[:-1]]), np.abs(L5 - np.r_[C5[0], C5[:-1]])))
    atr = _rolling_mean(tr, 14)
    atr_med = _rolling_median_sub(atr, 8640, 288)
    razon = atr[j5] / atr_med[j5]
    F["vol"] = np.select([razon < 0.8, razon > 1.25], [0, 2], 1).astype(np.int8)  # baja, normal, alta
    m20 = _rolling_mean(C5, 20)
    sd20 = np.sqrt(np.maximum(_rolling_mean(C5 ** 2, 20) - m20 ** 2, 0))
    ancho = 4 * sd20 / m20
    # percentil del ancho en los últimos 30 días (aproximado con ventana cada 288 velas)
    pct = np.full(len(ancho), np.nan)
    for j in range(8640, len(ancho), 288):
        ref = np.sort(ancho[j - 8640:j][~np.isnan(ancho[j - 8640:j])])
        seg = ancho[j:j + 288]
        pct[j:j + 288] = np.searchsorted(ref, seg) / max(len(ref), 1)
    F["bollinger"] = np.select([pct[j5] < 0.2, pct[j5] > 0.8], [0, 2], 1).astype(np.int8)  # contracción, normal, expansión
    hi20 = np.r_[np.nan, _rolling_max(H5, 20)[:-1]]
    lo20 = np.r_[np.nan, _rolling_min(L5, 20)[:-1]]
    F["ruptura"] = np.select([C5[j5] > hi20[j5], C5[j5] < lo20[j5]], [0, 1], 2).astype(np.int8)  # alcista, bajista, ninguna
    # ---- 4. liquidez y volumen
    cv, ctb = np.cumsum(np.r_[0, v]), np.cumsum(np.r_[0, tb])
    v15 = cv[i_dec + 1] - cv[i_dec - 14]
    tb15 = ctb[i_dec + 1] - ctb[i_dec - 14]
    lv = np.log(np.maximum(v15, 1e-9))
    ref = _rolling_mean(lv, 1008)  # 7 días de decisiones de 10 min
    rv = np.exp(lv - np.r_[np.nan, ref[:-1]])
    F["volumen"] = np.select([rv < 0.7, rv > 1.3], [0, 2], 1).astype(np.int8)  # bajo, normal, alto
    delta = np.where(v15 > 0, (2 * tb15 - v15) / np.maximum(v15, 1e-12), 0)
    F["flujo"] = np.select([delta > 0.08, delta < -0.08], [0, 1], 2).astype(np.int8)  # compradores, vendedores, parejo
    H60 = np.r_[np.full(15, np.nan), _rolling_max(h, 60)[:-15]]  # máximo de la hora previa a los últimos 15 min
    L60 = np.r_[np.full(15, np.nan), _rolling_min(l, 60)[:-15]]
    hmax15 = _rolling_max(h, 15)
    lmin15 = _rolling_min(l, 15)
    barrio_arr = (hmax15[i_dec] > H60[i_dec]) & (c[i_dec] < H60[i_dec])
    barrio_abj = (lmin15[i_dec] < L60[i_dec]) & (c[i_dec] > L60[i_dec])
    F["barrido"] = np.select([barrio_arr & ~barrio_abj, barrio_abj & ~barrio_arr], [0, 1], 2).astype(np.int8)  # tomó arriba, tomó abajo, ninguno
    # ---- 5. estructura (velas de 5 min, giros de 2 velas a cada lado, conocidos 2 velas después)
    m5 = len(C5)
    est = np.zeros(m5, np.int8)      # tendencia por estructura: 1 alcista (último BOS arriba), -1 bajista
    choch = np.zeros(m5, np.int8)    # 1 CHoCH alcista en las últimas 6 velas, -1 bajista
    fvg = np.zeros(m5, np.int8)      # 1 dentro de un FVG alcista abierto, -1 bajista
    ob = np.zeros(m5, np.int8)       # 1 retestea order block alcista, -1 bajista
    ult_sh, ult_sl, tend, ult_choch_k, ult_choch_dir = np.nan, np.nan, 0, -999, 0
    fvgs_alc, fvgs_baj = [], []      # (k, bajo, alto)
    ob_alc, ob_baj = None, None      # (k, bajo, alto)
    for k in range(4, m5):
        g = k - 2  # giro confirmado ahora
        if H5[g] > H5[g - 1] and H5[g] > H5[g - 2] and H5[g] >= H5[g + 1] and H5[g] >= H5[g + 2]:
            ult_sh = H5[g]
        if L5[g] < L5[g - 1] and L5[g] < L5[g - 2] and L5[g] <= L5[g + 1] and L5[g] <= L5[g + 2]:
            ult_sl = L5[g]
        if not np.isnan(ult_sh) and C5[k] > ult_sh:
            if tend == -1:
                ult_choch_k, ult_choch_dir = k, 1
            tend = 1
            # order block alcista: última vela bajista antes del empuje
            for q in range(k - 1, max(k - 10, 0), -1):
                if C5[q] < O5[q]:
                    ob_alc = (k, L5[q], H5[q])
                    break
            ult_sh = np.nan
        elif not np.isnan(ult_sl) and C5[k] < ult_sl:
            if tend == 1:
                ult_choch_k, ult_choch_dir = k, -1
            tend = -1
            for q in range(k - 1, max(k - 10, 0), -1):
                if C5[q] > O5[q]:
                    ob_baj = (k, L5[q], H5[q])
                    break
            ult_sl = np.nan
        est[k] = tend
        choch[k] = ult_choch_dir if k - ult_choch_k <= 6 else 0
        if L5[k] > H5[k - 2]:
            fvgs_alc.append((k, H5[k - 2], L5[k]))
        if H5[k] < L5[k - 2]:
            fvgs_baj.append((k, H5[k], L5[k - 2]))
        fvgs_alc = [x for x in fvgs_alc if k - x[0] <= 24 and L5[k] > x[1]]   # se cierra si el precio lo atraviesa
        fvgs_baj = [x for x in fvgs_baj if k - x[0] <= 24 and H5[k] < x[2]]
        if any(x[1] <= C5[k] <= x[2] for x in fvgs_alc):
            fvg[k] = 1
        elif any(x[1] <= C5[k] <= x[2] for x in fvgs_baj):
            fvg[k] = -1
        if ob_alc and k - ob_alc[0] <= 48 and ob_alc[1] <= L5[k] <= ob_alc[2]:
            ob[k] = 1
        elif ob_baj and k - ob_baj[0] <= 48 and ob_baj[1] <= H5[k] <= ob_baj[2]:
            ob[k] = -1
    F["estructura"] = np.where(est[j5] >= 0, 0, 1).astype(np.int8)  # alcista (o sin definir), bajista
    F["choch"] = np.select([choch[j5] == 1, choch[j5] == -1], [0, 1], 2).astype(np.int8)
    F["fvg"] = np.select([fvg[j5] == 1, fvg[j5] == -1], [0, 1], 2).astype(np.int8)
    F["ob"] = np.select([ob[j5] == 1, ob[j5] == -1], [0, 1], 2).astype(np.int8)
    # AMD: rango de Asia (0-8 UTC) del día y barrido posterior
    dia_utc = td // 86400
    amd = np.full(len(i_dec), 4, np.int8)  # 0 barrió alto de Asia, 1 barrió bajo, 2 ambos, 3 ninguno, 4 en Asia
    for d in np.unique(dia_utc):
        sel = np.flatnonzero(dia_utc == d)
        a0 = int(np.searchsorted(t, d * 86400))
        a1 = int(np.searchsorted(t, d * 86400 + 8 * 3600))
        if a1 - a0 < 400 or a1 >= n:
            continue
        ah, al = h[a0:a1].max(), l[a0:a1].min()
        for s in sel:
            if hora[s] < 8:
                continue
            if i_dec[s] + 1 <= a1:
                amd[s] = 3
                continue
            seg = slice(a1, i_dec[s] + 1)
            arriba, abajo = h[seg].max() > ah, l[seg].min() < al
            amd[s] = 2 if (arriba and abajo) else 0 if arriba else 1 if abajo else 3
    F["amd"] = amd
    # AMT: área de valor del día UTC anterior (volumen repartido en el cierre de cada vela de 1 min, cajas de 0,1 %)
    amt = np.full(len(i_dec), 1, np.int8)  # 0 encima del VAH, 1 dentro, 2 debajo del VAL
    perfil = {}
    for d in np.unique(dia_utc):
        a0 = int(np.searchsorted(t, (d - 1) * 86400))
        a1 = int(np.searchsorted(t, d * 86400))
        cc, vv = c[a0:a1], v[a0:a1]
        if len(cc) < 1000:
            continue
        cajas = np.floor(np.log(cc) / 0.001).astype(np.int64)
        u, inv = np.unique(cajas, return_inverse=True)
        vol = np.bincount(inv, weights=vv)
        o_ = np.argsort(vol)[::-1]
        acum = np.cumsum(vol[o_]) / vol.sum()
        dentro = u[o_[:np.searchsorted(acum, 0.7) + 1]]
        perfil[d] = (np.exp(dentro.min() * 0.001), np.exp((dentro.max() + 1) * 0.001))
    for s in range(len(i_dec)):
        p = perfil.get(dia_utc[s])
        if p:
            amt[s] = 0 if c[i_dec[s]] > p[1] else 2 if c[i_dec[s]] < p[0] else 1
    F["amt"] = amt
    # ---- tramos
    tramo = np.full(len(i_dec), -1, np.int8)
    for k, (nombre, (a, b)) in enumerate(TRAMOS.items()):
        tramo[(td >= _ts(a)) & (td < _ts(b))] = k
    extra = {"z15": z15, "delta": delta, "razon_atr": razon, "rv": rv, "a60": a60, "a240": a240, "a1d": a1d,
             "sd1": sd1[i_dec], "precio": c[i_dec]}
    return {"sim": sim, "t": td, "y": y, "tramo": tramo, "F": F, "extra": extra}


NOMBRES = {
    "sesion": ["Asia", "Europa", "EE. UU.", "cierre"], "finde": ["semana", "fin de semana"],
    "direccion": ["alcista 1h-4h-1d", "bajista 1h-4h-1d", "mixta"], "impulso": ["cayó en 15 min", "subió en 15 min", "plano"],
    "vol": ["vol. baja", "vol. normal", "vol. alta"], "bollinger": ["contracción", "ancho normal", "expansión"],
    "ruptura": ["ruptura alcista", "ruptura bajista", "sin ruptura"], "volumen": ["volumen bajo", "volumen normal", "volumen alto"],
    "flujo": ["compradores", "vendedores", "flujo parejo"], "barrido": ["barrió arriba", "barrió abajo", "sin barrido"],
    "estructura": ["estructura alcista", "estructura bajista"], "choch": ["CHoCH alcista", "CHoCH bajista", "sin CHoCH"],
    "fvg": ["en FVG alcista", "en FVG bajista", "sin FVG"], "ob": ["en OB alcista", "en OB bajista", "sin OB"],
    "amd": ["barrió alto de Asia", "barrió bajo de Asia", "barrió ambos", "sin barrido de Asia", "en Asia"],
    "amt": ["encima del VAH", "dentro del área de valor", "debajo del VAL"],
}
DIMENSION = {"sesion": 1, "finde": 1, "direccion": 2, "impulso": 2, "vol": 3, "bollinger": 3, "ruptura": 3,
             "volumen": 4, "flujo": 4, "barrido": 4, "estructura": 5, "choch": 5, "fvg": 5, "ob": 5, "amd": 5, "amt": 5}
