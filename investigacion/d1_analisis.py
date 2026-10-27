"""Análisis de registro_variantes_*.csv con la regla de adopción del PREREGISTRO.md (punto 3):

Una variante solo se propone si (a) mejora la media neta con comisión doble en entrenamiento (2020-22) Y en validación
(2023), (b) no empeora la caída máxima de entrenamiento en más de un 20 % relativo, (c) conserva al menos el 40 % de las
operaciones de la base, (d) sus vecinos de parámetro también mejoran en entrenamiento (no es un pico aislado) y
(e) en el walk-forward anclado (elegir con los años < Y, aplicar a Y, Y = 2022..2026) lo elegido supera a la base en la
mayoría de los años. La prueba 2024-2026 se informa, pero no decide (está contaminada en BTC).
Además: ¿lo que se elegiría en BTC funciona en los otros 6 activos?
Uso: python3 -I d1_analisis.py > d1_analisis.txt"""
import glob
import os
import numpy as np
import pandas as pd

pd.set_option("display.width", 250)
R = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "variantes", "registro_variantes_*.csv")))])
R["clave"] = R.apply(lambda r: (f"k={r.k} W={int(r.W)} h={int(r.hora)} {r.salida}" if r.familia == "P05b" else
                                f"k={r.k} {r.salida}" if r.familia == "P05c" else
                                f"07-{int(r.hora)} {r.salida}" if r.familia == "N9" else r.salida), axis=1)
BASE = {"P05b": "k=0.5 W=60 h=21 actual", "P05c": "k=1.0 actual", "N9": "07-13 actual", "P11": "stop 3.0 %", "N8": "stop 3.0 %"}
E, V, P = "entreno 2020-22", "valida 2023", "prueba 2024-26"
ACTIVOS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA"]
print("Activos con registro:", sorted(R.activo.unique()), "· variantes por activo:", R.groupby("activo").size().to_dict())


def vecinos_mejoran(fam, fila, X, base_e):
    """Para P05b: los vecinos en k (±0,1) con el mismo W, hora y salida también mejoran en entrenamiento."""
    if fam != "P05b":
        return True
    v = X[(X.W == fila.W) & (X.hora == fila.hora) & (X.salida == fila.salida) & ((X.k - fila.k).abs().between(0.05, 0.15))]
    return len(v) > 0 and (v[f"{E}|media2"] > base_e).all()


for fam in ("P05b", "P05c", "N9", "P11", "N8"):
    X = R[(R.activo == "BTC") & (R.familia == fam)].copy()
    b = X[X.clave == BASE[fam]].iloc[0]
    print(f"\n{'=' * 20} {fam} (BTC): {len(X)} variantes · base «{BASE[fam]}» {'=' * 20}")
    print(f"  base: entreno {b[f'{E}|media2']:+.3f} ({int(b[f'{E}|ops'])} ops, caída {b[f'{E}|caida']:.1f} %) · validación "
          f"{b[f'{V}|media2']:+.3f} ({int(b[f'{V}|ops'])}) · prueba {b[f'{P}|media2']:+.3f} ({int(b[f'{P}|ops'])})")
    X["mejora_E"] = X[f"{E}|media2"] > b[f"{E}|media2"]
    X["mejora_V"] = X[f"{V}|media2"] > b[f"{V}|media2"]
    X["caida_ok"] = X[f"{E}|caida"] <= b[f"{E}|caida"] * 1.2
    X["ops_ok"] = X[f"{E}|ops"] >= 0.4 * b[f"{E}|ops"]
    X["vecinos"] = [vecinos_mejoran(fam, r, X, b[f"{E}|media2"]) for r in X.itertuples()]
    X["pasa_a_d"] = X.mejora_E & X.mejora_V & X.caida_ok & X.ops_ok & X.vecinos & (X.clave != BASE[fam])
    print(f"  mejoran en entreno: {X.mejora_E.sum() - 1 if X.mejora_E[X.clave == BASE[fam]].any() else X.mejora_E.sum()} · "
          f"en entreno Y validación: {(X.mejora_E & X.mejora_V).sum()} · pasan (a)-(d): {X.pasa_a_d.sum()}")
    cols = ["clave", f"{E}|ops", f"{E}|media2", f"{E}|caida", f"{V}|ops", f"{V}|media2", f"{P}|ops", f"{P}|media2", f"{P}|caida"]
    top = X.sort_values(f"{E}|media2", ascending=False).head(8)
    print("  las 8 mejores en ENTRENAMIENTO (así se elegiría ingenuamente) y cómo les fue después:")
    print(top[cols + ["pasa_a_d"]].to_string(index=False, float_format=lambda v: f"{v:+.3f}" if abs(v) < 5 else f"{v:.0f}"))
    if fam in ("P05b", "P05c", "N9"):
        s = X[(X.k == b.k) | X.k.isna()] if fam != "P05b" else X[(X.k == 0.5) & (X.W == 60) & (X.hora == 21)]
        print("  SALIDAS (resto de parámetros como la base): media doble por tramo y caída de entrenamiento")
        print(s[["salida", f"{E}|media2", f"{E}|caida", f"{V}|media2", f"{P}|media2", f"{P}|caida"]].to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
    if fam == "P05b":
        print("  SENSIBILIDAD k × W (hora 21, salida actual), media doble en ENTRENAMIENTO | en PRUEBA:")
        s = X[(X.hora == 21) & (X.salida == "actual")]
        print(s.pivot_table(index="k", columns="W", values=f"{E}|media2").to_string(float_format=lambda v: f"{v:+.3f}"))
        print(s.pivot_table(index="k", columns="W", values=f"{P}|media2").to_string(float_format=lambda v: f"{v:+.3f}"))
        print("  hora tope (k 0,5, W 60, salida actual): " + "; ".join(
            f"{int(r.hora)} h: entreno {r[f'{E}|media2']:+.3f}, validación {r[f'{V}|media2']:+.3f}, prueba {r[f'{P}|media2']:+.3f}"
            for _, r in X[(X.k == 0.5) & (X.W == 60) & (X.salida == "actual")].iterrows()))

    # walk-forward anclado
    gana, filas = 0, []
    for Y in range(2022, 2027):
        prev = [f"año {y}|" for y in range(2020, Y)]
        ops_prev = sum(X[p + "ops"].fillna(0) for p in prev)
        suma_prev = sum((X[p + "media2"].fillna(0) * X[p + "ops"].fillna(0)) for p in prev)
        X["m_prev"] = suma_prev / ops_prev.replace(0, np.nan)
        base_ops_prev = float(ops_prev[X.clave == BASE[fam]].iloc[0])
        cand = X[ops_prev >= 0.4 * base_ops_prev]
        elegida = cand.sort_values("m_prev", ascending=False).iloc[0]
        bY = X[X.clave == BASE[fam]].iloc[0]
        eY, bmY = elegida[f"año {Y}|media2"], bY[f"año {Y}|media2"]
        gana += eY > bmY
        filas.append(f"{Y}: elige «{elegida.clave}» → {eY:+.3f} ({int(elegida[f'año {Y}|ops'])} ops) vs base {bmY:+.3f} ({int(bY[f'año {Y}|ops'])})")
    print("  WALK-FORWARD (elige la mejor media doble de los años anteriores; aplica al año siguiente):")
    for f in filas:
        print("    " + f)
    print(f"    lo elegido supera a la base en {gana} de 5 años")

    # ¿lo mejor en entrenamiento de BTC funciona en otros activos?
    mejor = X[X.ops_ok].sort_values(f"{E}|media2", ascending=False).iloc[0].clave
    tot =R[(R.familia == fam) & (R.clave.isin([mejor, BASE[fam]]))].copy()
    tot["todo"] = sum(tot[f"año {y}|media2"].fillna(0) * tot[f"año {y}|ops"].fillna(0) for y in range(2020, 2027)) / \
        sum(tot[f"año {y}|ops"].fillna(0) for y in range(2020, 2027))
    t2 = tot.pivot_table(index="activo", columns="clave", values="todo").reindex([a for a in ACTIVOS if a in tot.activo.unique()])
    if mejor != BASE[fam]:
        print(f"  TRANSFERENCIA: la mejor de entrenamiento en BTC («{mejor}») frente a la base, media doble de TODO el periodo por activo:")
        print(t2.to_string(float_format=lambda v: f"{v:+.3f}"))
        print(f"    mejora en {(t2[mejor] > t2[BASE[fam]]).sum()} de {len(t2)} activos")
