"""Métricas comunes de la investigación. Todo en % del nocional de cada operación (1x, sin apalancamiento).

Metodología (explícita, porque el informe anterior no la daba):
- «suma»: suma simple de los % netos por operación (lo que publicó la consolidación).
- «compuesto»: producto de (1 + r) operación a operación con el 100 % del saldo en cada una, sin solaparse.
- Sharpe y Sortino: sobre la serie DIARIA de calendario (P&L de las operaciones que cierran ese día, 0 los días sin
  operación), anualizados con 365 días (cripto opera todos los días). Sortino con la desviación a la baja sobre todos los días.
- IC 90 % de la media por operación: bootstrap por bloques de meses (respeta la dependencia dentro de cada mes).
"""
import numpy as np
import pandas as pd

CORTE_PRUEBA = pd.Timestamp("2024-01-01", tz="UTC")
TRAMOS = {"2020-2023": (pd.Timestamp("2020-01-01", tz="UTC"), CORTE_PRUEBA),
          "2024-2026": (CORTE_PRUEBA, pd.Timestamp("2027-01-01", tz="UTC"))}

# costes por lado en %: (entrada de creador, entrada de tomador, salida)
COSTES = {
    "futuros base": (0.02, 0.05, 0.05),
    "futuros doble": (0.04, 0.10, 0.10),
    "adverso (todo tomador + 0,02 desliz.)": (0.07, 0.07, 0.07),
    "contado BNB 0,075": (0.075, 0.075, 0.075),
    "contado 0,10": (0.10, 0.10, 0.10),
    "contado doble 0,15": (0.15, 0.15, 0.15),
}


def cargar(etq):
    t = pd.read_csv(f"/home/user/trader-btc-investigacion/investigacion/operaciones/ops_{etq}.csv",
                    parse_dates=["entrada", "salida", "senal", "dia"])
    for c in ("entrada", "salida", "senal", "dia"):
        if t[c].dt.tz is None:
            t[c] = t[c].dt.tz_localize("UTC")
    return t


def neto(t, coste="futuros base"):
    cm, tm, sal = COSTES[coste]
    return t.bruto.to_numpy() - np.where(t.creador.to_numpy(bool), cm, tm) - sal


def diario(t, x, ini=None, fin=None):
    s = pd.Series(x, index=t.salida.dt.normalize()).groupby(level=0).sum()
    ini = ini or t.entrada.min().normalize()
    fin = fin or t.salida.max().normalize()
    return s.reindex(pd.date_range(ini, fin, freq="D", tz="UTC"), fill_value=0.0)


def ic_bloques(t, x, sims=2000, semilla=1, nivel=90):
    if len(x) < 5:
        return (np.nan, np.nan)
    mes = t.entrada.dt.strftime("%Y-%m").to_numpy()
    grupos = [x[mes == m] for m in np.unique(mes)]
    rng = np.random.default_rng(semilla)
    medias = []
    for _ in range(sims):
        k = rng.integers(0, len(grupos), len(grupos))
        v = np.concatenate([grupos[i] for i in k])
        medias.append(v.mean())
    a = (100 - nivel) / 2
    return tuple(np.percentile(medias, [a, 100 - a]))


def curva(x):
    eq = np.cumprod(1 + np.asarray(x) / 100)
    pico = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    return eq, (1 - eq / pico) * 100


def duracion_caida(t, x):
    """Días de calendario de la caída más larga (de un máximo hasta recuperarlo, o hasta el final)."""
    if len(x) == 0:
        return 0
    eq, _ = curva(x)
    fechas = t.salida.dt.tz_localize(None).to_numpy()
    pico_v, pico_f, peor = 1.0, t.entrada.dt.tz_localize(None).to_numpy()[0], np.timedelta64(0, "D")
    for v, f in zip(eq, fechas):
        if v >= pico_v:
            peor = max(peor, f - pico_f)
            pico_v, pico_f = v, f
    peor = max(peor, fechas[-1] - pico_f)
    return int(peor / np.timedelta64(1, "D"))


def metricas(t, x, minutos_tramo=None):
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return dict(ops=0)
    gan, per = x[x > 0], x[x <= 0]
    eq, dd = curva(x)
    d = diario(t, x)
    sd = d.std(ddof=1)
    baja = np.sqrt(np.mean(np.minimum(d.to_numpy(), 0) ** 2))
    orden = np.sort(x)[::-1]
    ic = ic_bloques(t, x)
    expo = ((t.salida - t.entrada).dt.total_seconds().sum() / 60 / minutos_tramo * 100) if minutos_tramo else np.nan
    return dict(
        ops=n, aciertos=(x > 0).mean() * 100, media=x.mean(), mediana=np.median(x),
        gan_media=gan.mean() if len(gan) else 0.0, per_media=per.mean() if len(per) else 0.0,
        pf=gan.sum() / -per.sum() if per.sum() < 0 else np.inf, suma=x.sum(), compuesto=(eq[-1] - 1) * 100,
        caida_max=dd.max(), dur_caida_dias=duracion_caida(t, x),
        sharpe=d.mean() / sd * np.sqrt(365) if sd > 0 else np.nan,
        sortino=d.mean() / baja * np.sqrt(365) if baja > 0 else np.nan,
        t_media=x.mean() / (x.std(ddof=1) / np.sqrt(n)) if n > 2 else np.nan,
        ic90_lo=ic[0], ic90_hi=ic[1],
        top5_pct=orden[:5].sum() / x.sum() * 100 if x.sum() > 0 else np.nan,
        sin_top5=x.sum() - orden[:5].sum(), sin_top10=x.sum() - orden[:10].sum(),
        exposicion_pct=expo, peor_op=x.min(), mejor_op=x.max(),
    )


def tramo(t, nombre):
    a, b = TRAMOS[nombre]
    return t[(t.entrada >= a) & (t.entrada < b)]
