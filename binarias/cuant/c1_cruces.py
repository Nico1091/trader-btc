"""C1 (03/11/2026): cruce de las seis dimensiones y probabilidades condicionadas, a ciegas.

Regla escrita antes de ver resultados:
- Objetivo: binaria de 10 min (sube o baja), una decisión cada 10 min, empate = fallo, pago 0,85 (equilibrio 54,05 %).
- Se elige SOLO con 2021-2023. Se juzga intacto en 2024 a septiembre de 2026 (prueba) y en octubre de 2026 (adelante).
- Celdas: cada estado solo, y cada combinación de 2 y 3 estados de variables distintas. El sentido de la apuesta sale del
  entrenamiento. Una celda se elige si (a) sobrevive a Benjamini-Hochberg con q = 0,05 sobre todas las celdas probadas,
  (b) su límite inferior de Wilson al 95 % en entrenamiento supera 54,05 % y (c) tiene al menos 300 apuestas.
- Cartera: se apuesta cuando dispara alguna celda elegida y todas las que disparan coinciden en el sentido.
- Sobreajuste: PBO por CSCV con 16 bloques de 2021 a septiembre de 2026 sobre todas las celdas con 600 apuestas o más.
- Meta de Nicolás (85,7 %): se cuentan las celdas que la alcanzan en entrenamiento y se mira qué les pasa fuera.
Uso: python -I c1_cruces.py [BTCUSDT ETHUSDT]
"""
import itertools
import json
import os
import sys
import time

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base as B  # noqa: E402
import validacion as V  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, "cache")
SALIDA = os.path.join(AQUI, "resultados")
EQ = B.EQUILIBRIO
MIN_N = 300


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x):
    return "–" if x != x else es(100 * x) + " %"


def datos(sim):
    os.makedirs(CACHE, exist_ok=True)
    ruta = os.path.join(CACHE, f"{sim}.npz")
    if os.path.exists(ruta):
        z = np.load(ruta, allow_pickle=True)
        return {"sim": sim, "t": z["t"], "y": z["y"], "tramo": z["tramo"], "F": z["F"].item(), "extra": z["extra"].item()}
    t0 = time.time()
    d = B.construir(sim)
    np.savez_compressed(ruta, t=d["t"], y=d["y"], tramo=d["tramo"], F=np.array(d["F"], dtype=object), extra=np.array(d["extra"], dtype=object))
    print(f"  rasgos de {sim} en {time.time() - t0:.0f} s")
    return d


def tabla(d, variables):
    """Conteos por celda y tramo: sube, baja y total."""
    F, y, tr = d["F"], d["y"], d["tramo"]
    ks = [len(B.NOMBRES[v]) for v in variables]
    cod = np.zeros(len(y), np.int64)
    for v, k in zip(variables, ks):
        cod = cod * k + F[v].astype(np.int64)
    nc = int(np.prod(ks))
    out = {}
    for j in range(3):
        m = tr == j
        out[j] = (np.bincount(cod[m & (y == 1)], minlength=nc), np.bincount(cod[m & (y == -1)], minlength=nc), np.bincount(cod[m], minlength=nc))
    return cod, nc, ks, out


def nombre_celda(variables, ks, c):
    partes = []
    for v, k in reversed(list(zip(variables, ks))):
        partes.append(B.NOMBRES[v][c % k])
        c //= k
    return " + ".join(reversed(partes))


def estudio(sim):
    d = datos(sim)
    y, tr, t = d["y"], d["tramo"], d["t"]
    dias = {j: max(1.0, (t[tr == j].max() - t[tr == j].min()) / 86400) if (tr == j).any() else 1.0 for j in range(3)}
    vars_ = list(B.NOMBRES)
    lineas = [f"C1 · {sim} · cruce de las seis dimensiones · binaria de 10 min, una decisión cada 10 min, empate = fallo",
              f"decisiones: entrenamiento {np.sum(tr == 0):,} · prueba {np.sum(tr == 1):,} · adelante {np.sum(tr == 2):,}".replace(",", "."),
              f"base (apostar siempre SUBE): entrenamiento {pct(np.mean(y[tr == 0] == 1))} · prueba {pct(np.mean(y[tr == 1] == 1))} · adelante {pct(np.mean(y[tr == 2] == 1))}",
              f"equilibrio con pago 0,85: {pct(EQ)} · con 0,80: {pct(V.equilibrio(0.80))} · con 0,90: {pct(V.equilibrio(0.90))}", ""]
    celdas = []
    combos = [(v,) for v in vars_] + list(itertools.combinations(vars_, 2)) + list(itertools.combinations(vars_, 3))
    codigos = {}
    for vs in combos:
        cod, nc, ks, out = tabla(d, vs)
        codigos[vs] = (cod, ks)
        su0, ba0, n0 = out[0]
        for c in np.flatnonzero(n0 >= 30):
            sentido = 1 if su0[c] >= ba0[c] else -1
            k0 = su0[c] if sentido == 1 else ba0[c]
            fila = {"vars": vs, "c": int(c), "sentido": sentido, "n0": int(n0[c]), "k0": int(k0)}
            for j in (1, 2):
                su, ba, n = out[j]
                fila[f"n{j}"] = int(n[c])
                fila[f"k{j}"] = int(su[c] if sentido == 1 else ba[c])
            celdas.append(fila)
    probadas = [c for c in celdas if c["n0"] >= MIN_N]
    pv = [min(1.0, 2 * V.binomial_cola(c["k0"], c["n0"], 0.5)) for c in probadas]
    bh = V.benjamini_hochberg(pv, 0.05)
    elegidas = []
    for c, p, ok in zip(probadas, pv, bh):
        lb = V.wilson(c["k0"], c["n0"])[0]
        c["p"], c["lb0"] = p, lb
        if ok and lb > EQ:
            elegidas.append(c)
    lineas.append(f"Celdas probadas: {len(celdas):,} con 30+ apuestas; {len(probadas):,} con {MIN_N}+ (las únicas elegibles). "
                  f"Sobreviven a Benjamini-Hochberg: {int(bh.sum()):,}. Elegidas (además Wilson > equilibrio): {len(elegidas):,}.".replace(",", "."))
    # univariado
    lineas.append("")
    lineas.append("UNA SOLA VARIABLE (sentido elegido en entrenamiento) · acierto entrenamiento / prueba / adelante (apuestas)")
    for c in sorted([c for c in celdas if len(c["vars"]) == 1], key=lambda c: (B.DIMENSION[c["vars"][0]], c["vars"][0], c["c"])):
        nom = nombre_celda(c["vars"], [len(B.NOMBRES[c["vars"][0]])], c["c"])
        lineas.append(f"  D{B.DIMENSION[c['vars'][0]]} {nom:<28} {'SUBE' if c['sentido'] == 1 else 'BAJA'}: "
                      f"{pct(c['k0'] / c['n0'])} / {pct(c['k1'] / c['n1'] if c['n1'] else float('nan'))} / {pct(c['k2'] / c['n2'] if c['n2'] else float('nan'))}"
                      f" ({c['n0']:,} / {c['n1']:,} / {c['n2']:,})".replace(",", "."))
    # elegidas
    lineas.append("")
    lineas.append("LAS 25 ELEGIDAS DE MAYOR LÍMITE DE WILSON EN ENTRENAMIENTO · entrenamiento → prueba → adelante")
    for c in sorted(elegidas, key=lambda c: -c["lb0"])[:25]:
        ks = [len(B.NOMBRES[v]) for v in c["vars"]]
        lineas.append(f"  {'SUBE' if c['sentido'] == 1 else 'BAJA'} si {nombre_celda(c['vars'], ks, c['c'])}: {pct(c['k0'] / c['n0'])} (n {c['n0']:,}) → "
                      f"{pct(c['k1'] / c['n1'] if c['n1'] else float('nan'))} (n {c['n1']:,}) → {pct(c['k2'] / c['n2'] if c['n2'] else float('nan'))} (n {c['n2']:,})".replace(",", "."))
    sostienen = [c for c in elegidas if c["n1"] >= 100 and c["k1"] / c["n1"] > EQ]
    lineas.append(f"De las {len(elegidas)} elegidas, {len(sostienen)} siguen sobre el equilibrio en la prueba (con 100+ apuestas).")
    # cartera
    voto = np.zeros(len(y), np.int64)
    dispara = np.zeros(len(y), np.int64)
    for c in elegidas:
        cod, ks = codigos[c["vars"]]
        m = cod == c["c"]
        voto += m * c["sentido"]
        dispara += m
    apuesta = np.where((dispara > 0) & (np.abs(voto) == dispara), np.sign(voto), 0)
    lineas.append("")
    lineas.append("CARTERA (todas las elegidas; se apuesta si las que disparan coinciden)")
    res = {}
    for j, nom in enumerate(("entrenamiento", "prueba", "adelante")):
        m = (tr == j) & (apuesta != 0)
        n = int(m.sum())
        k = int(np.sum(y[m] == apuesta[m]))
        lb, ub = V.wilson(k, n)
        res[nom] = {"n": n, "k": k, "acierto": k / n if n else None, "por_dia": n / dias[j]}
        lineas.append(f"  {nom:<14} {n:>7,} apuestas · {n / dias[j]:5.1f} al día · acierto {pct(k / n if n else float('nan'))} (IC 95 %: {pct(lb)} a {pct(ub)})"
                      f" · expectativa por apuesta con 0,85: {es(100 * V.expectativa(k / n, 0.85), 2) if n else '–'} %".replace(",", "."))
    for año in range(2024, 2027):
        import datetime as dt
        a0 = dt.datetime(año, 1, 1, tzinfo=dt.timezone.utc).timestamp()
        a1 = dt.datetime(año + 1, 1, 1, tzinfo=dt.timezone.utc).timestamp()
        m = (t >= a0) & (t < a1) & (apuesta != 0) & (tr >= 1)
        n = int(m.sum())
        if n:
            lineas.append(f"     {año}: {n:,} apuestas · acierto {pct(np.mean(y[m] == apuesta[m]))}".replace(",", "."))
    # rachas de la cartera en la prueba
    m = (tr == 1) & (apuesta != 0)
    g = (y[m] == apuesta[m]).astype(int)
    if len(g) > 50:
        R = V.rachas(g)
        lineas.append(f"  Rachas en la prueba: acierto tras acertar {pct(R['tras_1_acierto'][0])} (n {R['tras_1_acierto'][1]:,}), tras fallar {pct(R['tras_1_fallo'][0])}, "
                      f"tras 3 aciertos seguidos {pct(R['tras_3_aciertos'][0])} (n {R['tras_3_aciertos'][1]:,}); z de Wald-Wolfowitz {es(R['z'], 2)}; peor racha de fallos {R['peor_racha_de_fallos']}.".replace(",", "."))
        for fr in (0.02, 0.05):
            q, cm = V.remuestreo_quiebra(g, 0.85, fr, apuestas=300)
            lineas.append(f"  300 apuestas al {es(100 * fr, 0)} % del saldo desde 100.000 COP (remuestreo por bloques): quiebra {pct(q)}, caída mediana {pct(cm)}")
    # PBO
    import datetime as dt
    t_a, t_b = dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp(), dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc).timestamp()
    bloque = np.floor((t - t_a) / ((t_b - t_a) / 16)).astype(int)
    validos = (t >= t_a) & (t < t_b)
    columnas = []
    for vs, (cod, ks) in codigos.items():
        nc = int(np.prod(ks))
        for sentido in (1, -1):
            gan = (y == sentido) & validos
            n_b = np.bincount(cod[validos] + nc * bloque[validos], minlength=16 * nc).reshape(16, nc)
            k_b = np.bincount(cod[gan] + nc * bloque[gan], minlength=16 * nc).reshape(16, nc)
            usar = n_b.sum(axis=0) >= 600
            with np.errstate(invalid="ignore", divide="ignore"):
                columnas.append(np.where(n_b[:, usar] > 0, k_b[:, usar] / np.maximum(n_b[:, usar], 1), np.nan))
    M = np.hstack(columnas)
    pbo, logit = V.pbo_cscv(M)
    lineas.append("")
    lineas.append(f"SOBREAJUSTE: PBO por CSCV con 16 bloques y {M.shape[1]:,} estrategias (celda y sentido) = {pct(pbo)} (mediana del logit {es(logit, 2)}). "
                  "Un PBO alto dice que la mejor celda del pasado suele quedar en la mitad de abajo en el futuro.".replace(",", "."))
    # meta de 85,7 %
    lineas.append("")
    meta = [c for c in celdas if c["k0"] / c["n0"] >= 0.857]
    fuera = [c for c in meta if c["n1"] >= 10]
    lineas.append(f"META DE 85,7 %: {len(meta)} celdas la tienen en entrenamiento (todas con pocas apuestas: máximo {max([c['n0'] for c in meta], default=0)}). "
                  f"De ellas, {len(fuera)} tienen 10+ apuestas en la prueba, con acierto medio {pct(np.mean([c['k1'] / c['n1'] for c in fuera]) if fuera else float('nan'))} "
                  f"y {sum(1 for c in fuera if c['k1'] / c['n1'] >= 0.857)} siguen en 85,7 % o más.")
    grandes = [c for c in celdas if c["n1"] >= 100]
    mejor = max(grandes, key=lambda c: c["k1"] / c["n1"]) if grandes else None
    if mejor:
        ks = [len(B.NOMBRES[v]) for v in mejor["vars"]]
        lineas.append(f"La mejor celda en la PRUEBA (mirando el resultado, o sea, con trampa) con 100+ apuestas: {pct(mejor['k1'] / mejor['n1'])} en {mejor['n1']} "
                      f"({'SUBE' if mejor['sentido'] == 1 else 'BAJA'} si {nombre_celda(mejor['vars'], ks, mejor['c'])}); el azar daría hasta "
                      f"{pct(V.acierto_maximo_por_azar(100, len(grandes)))} con {len(grandes):,} celdas de 100 apuestas.".replace(",", "."))
    lineas.append(f"Apuestas necesarias para distinguir 85,7 % de 54,05 % con 95 % y potencia 80 %: {V.muestra_necesaria(0.857, EQ)}; "
                  f"para distinguir 57 % de 54,05 %: {V.muestra_necesaria(0.57, EQ):,}.".replace(",", "."))
    os.makedirs(SALIDA, exist_ok=True)
    texto = "\n".join(lineas)
    open(os.path.join(SALIDA, f"c1_{sim}.txt"), "w", encoding="utf-8").write(texto + "\n")
    json.dump({"sim": sim, "probadas": len(probadas), "bh": int(bh.sum()), "elegidas": len(elegidas), "sostienen": len(sostienen),
               "cartera": res, "pbo": pbo, "meta_857": {"entrenamiento": len(meta), "con_prueba": len(fuera)}},
              open(os.path.join(SALIDA, f"c1_{sim}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(texto)


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["BTCUSDT", "ETHUSDT"]):
        estudio(s)
