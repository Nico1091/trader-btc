"""A8: prueba fuera de muestra de H1-H6, exactamente como quedaron en PREREGISTRO-PLAN-DIARIO.md (28/10/2026).

Activos VIEJOS (ya mirados): BTC, ETH, SOL, BNB, XRP, DOGE, ADA. NUEVOS (nunca mirados): LINK, AVAX, LTC, DOT, TRX.
Operaciones: investigacion/operaciones/ops_<ACTIVO>.csv (c1_operaciones.py, motor sin tocar). Velas: datos/um/<SIM>USDT_um_1m.npy
(o TRADER_DATOS/um). Comisión doble para el criterio: entrada 0,04 (creador) o 0,10 (tomador) y salida 0,10.

Definiciones causales (solo datos anteriores a la entrada):
  vol_alta  = ATR14 diario de los 14 días previos / apertura del día > mediana de ese cociente en los 365 días previos (≥ 180)
  ctx_lejos = |cierre de ayer / SMA 50 de los 50 cierres previos − 1| > mediana de ese valor en los 365 días previos (≥ 180)
H1 N8 con vol_alta · H2 P11 con e1h y e1d · H3 P05c con ctx_lejos y señal antes de las 17:00 UTC
H4 cartera (P05c en todos + P05b, P11 y N8 de BTC; 3 % de riesgo; hasta 3 posiciones) frente al libro actual de BTC
H5 corto de continuación R11 en 1 h · H6 reapertura tras la parada total (30 días, mitad del riesgo)
Criterio (sección 3 del preregistro): (1) en los 5 nuevos mejora la media neta con comisión doble en 4 de 5 o más y el IC 90 %
(bootstrap por meses) de la media conjunta con la regla excluye el cero; (2) en los 7 viejos mejora en 2020-23 y en 2024-26;
(3) conserva ≥ 30 % de las operaciones.
Uso: python -I a8_fuera_de_muestra.py > a8_fuera_de_muestra.txt"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "..", "..", "consolidacion"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VIEJOS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA"]
NUEVOS = ["LINK", "AVAX", "LTC", "DOT", "TRX"]
OPS = os.path.join(AQUI, "..", "operaciones")
DATOS = os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos")
CORTE = pd.Timestamp("2024-01-01", tz="UTC")


def velas(activo):
    a = np.load(os.path.join(DATOS, "um", f"{activo}USDT_um_1m.npy"))
    t = (a[:, 0] // 1000).astype("int64") if a[0, 0] > 1e11 else a[:, 0].astype("int64")
    return pd.DataFrame({"o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4], "v": a[:, 5]},
                        index=pd.to_datetime(t, unit="s", utc=True))


def diario_causal(m):
    d = m.resample("1D").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    tr = np.maximum(d.h - d.l, np.maximum((d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()))
    atr_prev = tr.shift(1).rolling(14).mean()
    volr = atr_prev / d.o
    sma = d.c.shift(1).rolling(50).mean()
    dist = (d.c.shift(1) / sma - 1).abs()
    med = lambda s: s.shift(1).rolling(365, min_periods=180).median()  # noqa: E731
    return pd.DataFrame({"vol_alta": volr > med(volr), "ctx_lejos": dist > med(dist)}, index=d.index)


def cargar(activo, causal):
    t = pd.read_csv(os.path.join(OPS, f"ops_{activo}.csv"), parse_dates=["entrada", "salida", "senal"])
    for c in ("entrada", "salida", "senal"):
        if t[c].dt.tz is None:
            t[c] = t[c].dt.tz_localize("UTC")
    cr = t.creador.astype(bool).to_numpy()
    t["neto"] = t.bruto - np.where(cr, 0.02, 0.05) - 0.05
    t["neto2"] = t.bruto - np.where(cr, 0.04, 0.10) - 0.10
    t["dist"] = np.where(t.apertura.notna(), (t.pe - t.apertura).abs() / t.pe, 0.03)
    t["activo"] = activo
    dia = t.entrada.dt.normalize()
    t["vol_alta"] = causal.vol_alta.reindex(dia).to_numpy(dtype=bool, na_value=False)
    t["ctx_lejos"] = causal.ctx_lejos.reindex(dia).to_numpy(dtype=bool, na_value=False)
    return t


REGLAS = {
    "H1 N8 con volatilidad alta": ("N8", lambda s: s.vol_alta),
    "H2 P11 con 1 h y 1 d a favor": ("P11", lambda s: s.e1h.astype(bool) & s.e1d.astype(bool)),
    "H3 P05c lejos de la SMA 50 y antes de las 17 UTC": ("P05c", lambda s: s.ctx_lejos & (s.senal.dt.hour < 17)),
}


def ic_bloques(t, x, sims=2000, semilla=1):
    mes = t.entrada.dt.strftime("%Y-%m").to_numpy()
    grupos = [x[mes == k] for k in np.unique(mes)]
    rng = np.random.default_rng(semilla)
    medias = [np.concatenate([grupos[i] for i in rng.integers(0, len(grupos), len(grupos))]).mean() for _ in range(sims)]
    return np.percentile(medias, 5), np.percentile(medias, 95)


def r11(m):
    """H5: corto al abrir la vela de 1 h siguiente si pendiente 60 h ≤ −0,10 %/h y posición en el rango de 60 h ≤ 0,20;
    stop 2,5 %, salida a las 6 h; tomador en las dos puntas (0,05 y 0,05; doble 0,10 y 0,10)."""
    h = m.resample("1h").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    c = h.c.to_numpy()
    x = np.arange(60) - 29.5
    res = []
    i = 60
    while i < len(c) - 7:
        y = c[i - 59:i + 1]
        pend = (x * (y - y.mean())).sum() / (x ** 2).sum() / c[i] * 100
        hi, lo = h.h.iloc[i - 59:i + 1].max(), h.l.iloc[i - 59:i + 1].min()
        pos = (c[i] - lo) / (hi - lo) if hi > lo else 0.5
        if pend <= -0.10 and pos <= 0.20:
            e = h.o.iloc[i + 1]
            sl = e * 1.025
            px = None
            for k in range(i + 1, i + 7):
                if h.h.iloc[k] >= sl:
                    px = sl
                    break
            if px is None:
                px = h.c.iloc[i + 6]
            bruto = -(px / e - 1) * 100
            res.append((h.index[i], bruto - 0.10, bruto - 0.20))
            i += 6
        else:
            i += 1
    return pd.DataFrame(res, columns=["t", "neto", "neto2"])


def main():
    print("A8 · FUERA DE MUESTRA según PREREGISTRO-PLAN-DIARIO.md (definiciones fijadas antes de bajar los activos nuevos)\n")
    datos, causal = {}, {}
    for a in VIEJOS + NUEVOS:
        if not os.path.exists(os.path.join(OPS, f"ops_{a}.csv")):
            print(f"  falta ops_{a}.csv: córrase c1_operaciones.py con sus velas")
            continue
        m = velas(a)
        causal[a] = diario_causal(m)
        datos[a] = (cargar(a, causal[a]), m.resample("1h").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna())
        del m
    for nombre, (estr, regla) in REGLAS.items():
        print(f"== {nombre} ==")
        mejoras_nuevos, todas = 0, []
        for a in NUEVOS:
            if a not in datos:
                continue
            t = datos[a][0]
            s = t[t.estrategia == estr]
            f = s[regla(s)]
            if len(s) == 0:
                continue
            mejor = f.neto2.mean() > s.neto2.mean() if len(f) else False
            mejoras_nuevos += bool(mejor)
            todas.append(f)
            print(f"   NUEVO {a:5s} sin regla {s.neto2.mean():+.3f} % (n={len(s)}) · con regla {f.neto2.mean() if len(f) else float('nan'):+.3f} % "
                  f"(n={len(f)}, {len(f) / len(s) * 100:.0f} %) · {'mejora' if mejor else 'no mejora'}")
        conj = pd.concat(todas) if todas else pd.DataFrame()
        ic = ic_bloques(conj, conj.neto2.to_numpy()) if len(conj) > 5 else (np.nan, np.nan)
        ok1 = mejoras_nuevos >= 4 and ic[0] > 0
        print(f"   (1) nuevos: mejora en {mejoras_nuevos} de {len(NUEVOS)} · media conjunta con regla {conj.neto2.mean() if len(conj) else float('nan'):+.3f} % "
              f"IC 90 % [{ic[0]:+.3f}, {ic[1]:+.3f}] -> {'CUMPLE' if ok1 else 'no cumple'}")
        tramo_ok = []
        for nom, sel in (("2020-23", lambda x: x.entrada < CORTE), ("2024-26", lambda x: x.entrada >= CORTE)):
            base_v, regla_v = [], []
            for a in VIEJOS:
                if a not in datos:
                    continue
                t = datos[a][0]
                s = t[(t.estrategia == estr) & sel(t)]
                base_v.append(s)
                regla_v.append(s[regla(s)])
            b, r = pd.concat(base_v), pd.concat(regla_v)
            tramo_ok.append(r.neto2.mean() > b.neto2.mean())
            print(f"   (2) viejos {nom}: sin regla {b.neto2.mean():+.3f} % (n={len(b)}) · con regla {r.neto2.mean():+.3f} % (n={len(r)}, {len(r) / max(1, len(b)) * 100:.0f} %)")
        base_n = sum(int((datos[a][0].estrategia == estr).sum()) for a in NUEVOS if a in datos)
        ok3 = base_n > 0 and len(conj) / base_n >= 0.30
        ok2 = all(tramo_ok)
        print(f"   (3) conserva {len(conj) / max(1, base_n) * 100:.0f} % de las operaciones de los nuevos -> {'CUMPLE' if ok3 else 'no cumple'}")
        print(f"   VEREDICTO: {'SE ADOPTA (cumple 1, 2 y 3)' if ok1 and ok2 and ok3 else 'NO se adopta'}\n")
    print("== H5 corto de continuación R11 (1 h) ==")
    filas = []
    for a in VIEJOS + NUEVOS:
        if a not in datos:
            continue
        r = r11(datos[a][1])
        if len(r) == 0:
            continue
        nuevo = a in NUEVOS
        filas.append((a, nuevo, r))
        print(f"   {'NUEVO' if nuevo else 'viejo'} {a:5s} {len(r):4d} cortos · neto {r.neto.mean():+.3f} % · doble {r.neto2.mean():+.3f} %"
              f" · 2024-26 doble {r[r.t >= CORTE].neto2.mean():+.3f} %")
    nuevos = [r for a, n, r in filas if n]
    if nuevos:
        conj = pd.concat(nuevos)
        pos = sum(1 for r in nuevos if r.neto2.mean() > 0)
        print(f"   nuevos positivos con comisión doble: {pos} de {len(nuevos)} · media conjunta doble {conj.neto2.mean():+.3f} % -> "
              f"{'CUMPLE (1)' if pos >= 4 and conj.neto2.mean() > 0 else 'no cumple'}\n")
    print("== H4 y H6: cartera frente al libro actual, en BTC + los 5 nuevos (todos los libros del plan; reapertura incluida) ==")
    import plan_diario as PD
    ops = []
    for a in ["BTC"] + NUEVOS:
        if a in datos:
            ops += PD.operaciones_historia(os.path.join(OPS, f"ops_{a}.csv"),
                                           estrategias=("P05c", "P11", "P05b", "N8") if a == "BTC" else ("P05c",))
    if ops:
        print(PD.informe(ops, "PLAN DIARIO · BTC + LINK, AVAX, LTC, DOT, TRX (P05c en todos; P05b, P11 y N8 solo en BTC)"))


if __name__ == "__main__":
    main()
