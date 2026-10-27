"""Biblioteca común de la consolidación (25/10/2026).

Velas de 1 minuto de BTCUSDT perpetuo (futuros USDⓈ-M de Binance, data.binance.vision, SHA-256 comprobado).
Todo en porcentajes. Comisión base 0,05 % por lado (0,10 % ida y vuelta) y repetición con el doble.
"""
import os
import numpy as np
import pandas as pd

DATOS = os.environ.get("DATOS_BTC", "/home/user/datos-btc/BTCUSDT_um_1m.npy")
CORTE = pd.Timestamp("2024-01-01", tz="UTC")  # ajuste: antes del corte; prueba: desde el corte


def cargar():
    a = np.load(DATOS)
    df = pd.DataFrame(a[:, 1:6], columns=["o", "h", "l", "c", "v"])
    df.index = pd.to_datetime(a[:, 0].astype("int64"), unit="ms", utc=True)
    return df


def remuestrear(m1, minutos):
    r = m1.resample(f"{minutos}min", label="left", closed="left")
    df = pd.DataFrame({"o": r["o"].first(), "h": r["h"].max(), "l": r["l"].min(),
                       "c": r["c"].last(), "v": r["v"].sum()}).dropna()
    return df


# ---------- patrones de vela del curso ----------

def patrones(df, n_tend=10):
    """Devuelve un DataFrame de booleanos (un patrón por columna) y un dict patrón -> lado (+1, -1 o 0).
    La vela del patrón es la última que forma el patrón; se opera al cierre de esa vela.
    «Tras bajada» y «tras subida»: el cierre previo al patrón frente al de n_tend velas antes."""
    o, h, l, c = (df[k].to_numpy() for k in "ohlc")
    cuerpo = np.abs(c - o)
    rango = h - l
    sup = h - np.maximum(o, c)
    inf = np.minimum(o, c) - l
    alc = c > o
    baj = c < o
    s = lambda x, k=1: np.concatenate([np.full(k, np.nan), x[:-k]]).astype(float)  # desplazar k velas
    sb = lambda x, k=1: np.concatenate([np.zeros(k, bool), x[:-k]])
    cuerpo_med = pd.Series(cuerpo).rolling(20, min_periods=20).mean().shift(1).to_numpy()
    rango_med = pd.Series(rango).rolling(20, min_periods=20).mean().shift(1).to_numpy()
    c_prev = s(c)
    tend = (c_prev - s(c, n_tend + 1)) / s(c, n_tend + 1)  # movimiento antes del patrón
    abajo = tend < 0
    arriba = tend > 0
    # tendencia "larga" para soldados y cuervos: antes de las tres velas
    tend3 = (s(c, 3) - s(c, n_tend + 3)) / s(c, n_tend + 3)
    with np.errstate(invalid="ignore", divide="ignore"):
        doji = (rango > 0) & (cuerpo <= 0.1 * rango)
        grande = cuerpo > cuerpo_med
        p = {}
        o1, c1, h1, l1, cu1 = s(o), s(c), s(h), s(l), s(cuerpo)
        alc1, baj1 = sb(alc), sb(baj)
        p["envolvente_alcista"] = abajo & baj1 & alc & (cuerpo > cu1) & (c >= o1) & (o <= c1)
        p["envolvente_bajista"] = arriba & alc1 & baj & (cuerpo > cu1) & (c <= o1) & (o >= c1)
        dentro = (np.maximum(o, c) <= np.maximum(o1, c1)) & (np.minimum(o, c) >= np.minimum(o1, c1))
        p["harami_alcista"] = abajo & baj1 & sb(grande) & dentro & (cuerpo < 0.5 * cu1)
        p["harami_bajista"] = arriba & alc1 & sb(grande) & dentro & (cuerpo < 0.5 * cu1)
        p["peonza"] = (rango > 0) & (cuerpo > 0.1 * rango) & (cuerpo <= 0.3 * rango) & (sup >= cuerpo) & (inf >= cuerpo)
        p["doji_piernas_largas"] = doji & (sup >= 0.3 * rango) & (inf >= 0.3 * rango) & (rango > rango_med)
        p["doji_cuatro_precios"] = (rango <= 0.1 * rango_med) & (cuerpo <= 0.1 * rango_med)
        p["doji_lapida"] = doji & (inf <= 0.1 * rango) & (sup >= 0.6 * rango) & arriba
        p["doji_libelula"] = doji & (sup <= 0.1 * rango) & (inf >= 0.6 * rango) & abajo
        tol = 0.05 * rango_med
        p["pinzas_arriba"] = arriba & alc1 & baj & (np.abs(h - h1) <= tol)
        p["pinzas_abajo"] = abajo & baj1 & alc & (np.abs(l - l1) <= tol)
        fuerte_a = alc & (cuerpo >= 0.5 * rango)
        fuerte_b = baj & (cuerpo >= 0.5 * rango)
        p["tres_soldados"] = (tend3 < 0) & fuerte_a & sb(fuerte_a) & sb(fuerte_a, 2) & (c > c1) & (c1 > s(c, 2))
        p["tres_cuervos"] = (tend3 > 0) & fuerte_b & sb(fuerte_b) & sb(fuerte_b, 2) & (c < c1) & (c1 < s(c, 2))
        o2, c2, cu2 = s(o, 2), s(c, 2), s(cuerpo, 2)
        tend2 = (s(c, 3) - s(c, n_tend + 3)) / s(c, n_tend + 3)
        p["estrella_manana"] = (tend2 < 0) & sb(baj, 2) & sb(grande, 2) & (cu1 <= 0.3 * cu2) & alc & (c >= (o2 + c2) / 2)
        p["estrella_tarde"] = (tend2 > 0) & sb(alc, 2) & sb(grande, 2) & (cu1 <= 0.3 * cu2) & baj & (c <= (o2 + c2) / 2)
        martillo_f = (cuerpo > 0) & (inf >= 2 * cuerpo) & (sup <= 0.5 * cuerpo) & (rango > 0.5 * rango_med)
        invertido_f = (cuerpo > 0) & (sup >= 2 * cuerpo) & (inf <= 0.5 * cuerpo) & (rango > 0.5 * rango_med)
        p["martillo"] = abajo & martillo_f
        p["martillo_invertido"] = abajo & invertido_f
        p["hombre_colgado"] = arriba & martillo_f
        p["estrella_fugaz"] = arriba & invertido_f
    lado = {"envolvente_alcista": 1, "envolvente_bajista": -1, "harami_alcista": 1, "harami_bajista": -1,
            "peonza": 0, "doji_piernas_largas": 0, "doji_cuatro_precios": 0, "doji_lapida": -1,
            "doji_libelula": 1, "pinzas_arriba": -1, "pinzas_abajo": 1, "tres_soldados": 1,
            "tres_cuervos": -1, "estrella_manana": 1, "estrella_tarde": -1, "martillo": 1,
            "martillo_invertido": 1, "hombre_colgado": -1, "estrella_fugaz": -1}
    out = pd.DataFrame({k: np.nan_to_num(v, nan=0).astype(bool) for k, v in p.items()}, index=df.index)
    return out, lado


# ---------- retornos hacia adelante con velas de 1 minuto ----------

def retorno_adelante(m1c, tiempos, horas):
    """Retorno % desde el cierre en `tiempos` (instante en que se puede operar) hasta `horas` después.
    m1c: Serie de cierres de 1 min. Usa el último cierre disponible en cada instante."""
    idx = m1c.index
    t0 = idx.searchsorted(tiempos, side="right") - 1
    t1 = idx.searchsorted(tiempos + pd.Timedelta(hours=horas), side="right") - 1
    ok = (t0 >= 0) & (t1 < len(idx)) & (idx[np.clip(t1, 0, len(idx) - 1)] >= tiempos + pd.Timedelta(hours=horas) - pd.Timedelta(minutes=1))
    v = m1c.to_numpy()
    r = np.full(len(tiempos), np.nan)
    r[ok] = (v[t1[ok]] / v[t0[ok]] - 1) * 100
    return r


def percentil_azar(media_obj, poblacion, n, sims=2000, semilla=7):
    """Percentil de una media frente a medias de n elementos sorteados de la población."""
    rng = np.random.default_rng(semilla)
    pob = poblacion[~np.isnan(poblacion)]
    if n == 0 or len(pob) == 0:
        return np.nan
    medias = np.array([pob[rng.integers(0, len(pob), n)].mean() for _ in range(sims)])
    return float((medias < media_obj).mean() * 100)


# ---------- motor de operaciones con velas de 1 minuto ----------

def resumen(netos, nombre="", extra=""):
    netos = np.asarray(netos, float)
    if len(netos) == 0:
        return f"{nombre}: 0 operaciones {extra}"
    eq = np.cumsum(netos)
    caida = float(np.max(np.maximum.accumulate(np.concatenate([[0], eq])) - np.concatenate([[0], eq])))
    racha, peor = 0, 0
    for x in netos:
        racha = racha + 1 if x <= 0 else 0
        peor = max(peor, racha)
    return (f"{nombre}: {len(netos)} ops, aciertos {np.mean(netos > 0) * 100:.1f} %, suma {netos.sum():+.1f} %, "
            f"media {netos.mean():+.3f} %, caída {caida:.1f} pts, peor racha {peor} {extra}")
