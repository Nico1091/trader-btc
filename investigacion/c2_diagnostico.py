"""C2: diagnóstico de rentabilidad por estrategia, activo, tramo, año, dirección, sesión y régimen, con costes 1x, 2x y
adversos, concentración y solapamiento entre estrategias. Uso: python3 -I c2_diagnostico.py > c2_diagnostico.txt"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from metricas import cargar, neto, metricas, tramo, TRAMOS, COSTES, diario  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
F = lambda v: f"{v:,.2f}"  # noqa: E731
ORDEN = ["P05b", "P11", "P05c", "N9", "N8"]
FIN = {"BTC": pd.Timestamp("2026-10-25", tz="UTC"), "ETH": pd.Timestamp("2026-10-26", tz="UTC")}

salida_csv = []
for etq in ("BTC", "ETH"):
    T = cargar(etq)
    print(f"\n{'=' * 30} {etq} {'=' * 30}")
    # ---------- 1. tabla principal (futuros base) por estrategia y tramo
    filas = []
    for nb in ORDEN:
        for tr, (a, b) in TRAMOS.items():
            t = tramo(T[T.estrategia == nb], tr)
            mins = (min(b, FIN[etq]) - a).total_seconds() / 60
            m = metricas(t, neto(t), mins)
            m.update(activo=etq, estrategia=nb, tramo=tr)
            filas.append(m)
    tab = pd.DataFrame(filas).set_index(["estrategia", "tramo"])
    salida_csv.append(tab.reset_index())
    print("\n1. MÉTRICAS CON COSTE DE FUTUROS BASE (creador 0,02 / tomador 0,05), en % del nocional por operación")
    cols = ["ops", "exposicion_pct", "aciertos", "media", "mediana", "gan_media", "per_media", "pf", "suma", "compuesto",
            "caida_max", "dur_caida_dias", "sharpe", "sortino", "t_media", "ic90_lo", "ic90_hi"]
    print(tab[cols].to_string(float_format=F))
    print("\n   Concentración: % de la suma que aportan las 5 mejores, y la suma sin las 5 y sin las 10 mejores")
    print(tab[["suma", "top5_pct", "sin_top5", "sin_top10", "mejor_op", "peor_op"]].to_string(float_format=F))

    # ---------- 2. sensibilidad a costes: media neta por operación
    print("\n2. MEDIA NETA POR OPERACIÓN (%) SEGÚN COSTES  [bruto = sin costes]")
    filas = []
    for nb in ORDEN:
        for tr in TRAMOS:
            t = tramo(T[T.estrategia == nb], tr)
            r = {"estrategia": nb, "tramo": tr, "bruto": t.bruto.mean()}
            r.update({c: neto(t, c).mean() for c in COSTES})
            filas.append(r)
    print(pd.DataFrame(filas).set_index(["estrategia", "tramo"]).to_string(float_format=lambda v: f"{v:+.3f}"))

    # ---------- 3. por año (suma neta futuros base) y número de operaciones
    T["anio"] = T.entrada.dt.year
    T["n"] = neto(T)
    print("\n3. POR AÑO: suma neta % (futuros base) | operaciones")
    s = T.pivot_table(index="estrategia", columns="anio", values="n", aggfunc="sum").reindex(ORDEN)
    c = T.pivot_table(index="estrategia", columns="anio", values="n", aggfunc="count").reindex(ORDEN)
    print(s.to_string(float_format=lambda v: f"{v:+.1f}"))
    print(c.to_string())

    # ---------- 4. por dirección
    print("\n4. POR DIRECCIÓN (todo el periodo): ops, media neta, suma")
    print(T.groupby(["estrategia", "lado"]).n.agg(["count", "mean", "sum"]).reindex(ORDEN, level=0).to_string(float_format=lambda v: f"{v:+.3f}"))

    # ---------- 5. por sesión de la señal (P05b, P05c)
    T["sesion"] = pd.cut(T.senal.dt.hour, [-1, 6, 12, 16, 24], labels=["Asia 00-07", "Londres 07-13", "NY 13-17", "tarde 17-21"])
    print("\n5. P05b y P05c POR HORA DE LA SEÑAL (UTC): ops, media neta, suma; por tramo")
    for nb in ("P05b", "P05c"):
        x = T[T.estrategia == nb].copy()
        x["tramo"] = np.where(x.entrada < pd.Timestamp("2024-01-01", tz="UTC"), "2020-2023", "2024-2026")
        print(f"   {nb}")
        print(x.groupby(["sesion", "tramo"], observed=True).n.agg(["count", "mean", "sum"]).to_string(float_format=lambda v: f"{v:+.3f}"))

    # ---------- 6. por régimen de volatilidad (ATR14 / precio, terciles de toda la muestra: descriptivo)
    T["vol"] = T.atr14 / T.precio_dia * 100
    cortes = np.nanpercentile(T.drop_duplicates("dia").vol, [33.3, 66.7])
    T["reg_vol"] = pd.cut(T.vol, [-np.inf, cortes[0], cortes[1], np.inf], labels=["baja", "media", "alta"])
    print(f"\n6. POR RÉGIMEN DE VOLATILIDAD (ATR14/precio; cortes {cortes[0]:.2f} % y {cortes[1]:.2f} %): ops, media neta, suma")
    print(T.groupby(["estrategia", "reg_vol"], observed=True).n.agg(["count", "mean", "sum"]).reindex(ORDEN, level=0).to_string(float_format=lambda v: f"{v:+.3f}"))
    # distancia al contexto
    T["ctx_fuerza"] = pd.cut(T.ctx_dist.abs(), [-np.inf, 2, 5, 10, np.inf], labels=["<2 %", "2-5 %", "5-10 %", ">10 %"])
    print("\n   POR DISTANCIA DEL CIERRE DE AYER A LA SMA 50 (fuerza del contexto): ops, media neta")
    print(T.groupby(["estrategia", "ctx_fuerza"], observed=True).n.agg(["count", "mean"]).unstack().reindex(ORDEN).to_string(float_format=lambda v: f"{v:+.3f}"))

    # ---------- 7. motivo de salida
    print("\n7. MOTIVO DE SALIDA: ops, media neta")
    print(T.groupby(["estrategia", "motivo"]).n.agg(["count", "mean"]).reindex(ORDEN, level=0).to_string(float_format=lambda v: f"{v:+.3f}"))

    # ---------- 8. solapamiento y correlación entre estrategias
    print("\n8. ¿SON ESTRATEGIAS DISTINTAS? días en común con el mismo lado (sobre los días de la fila) y correlación del P&L diario")
    dias = {nb: set(zip(T[T.estrategia == nb].dia, T[T.estrategia == nb].lado)) for nb in ORDEN}
    sol = pd.DataFrame({b: {a: len(dias[a] & dias[b]) / max(len(dias[a]), 1) * 100 for a in ORDEN} for b in ORDEN})
    print(sol.reindex(ORDEN)[ORDEN].to_string(float_format=lambda v: f"{v:.0f} %"))
    ini, fin = T.entrada.min().normalize(), T.salida.max().normalize()
    D = pd.DataFrame({nb: diario(T[T.estrategia == nb], T[T.estrategia == nb].n.to_numpy(), ini, fin) for nb in ORDEN})
    print("   correlación del P&L diario (todos los días):")
    print(D.corr().to_string(float_format=lambda v: f"{v:+.2f}"))
    Dn = D.replace(0, np.nan)
    print("   correlación solo en días en que operan las dos:")
    print(Dn.corr(min_periods=20).to_string(float_format=lambda v: f"{v:+.2f}"))

pd.concat(salida_csv).to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "c2_metricas.csv"), index=False)
