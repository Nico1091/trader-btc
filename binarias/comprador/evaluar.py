"""Evaluación de la red para el comprador por ganancia esperada (12/11/2026). Solo historia y cuentas: nada compra.

Sigue REGLAS-ANTES-DE-MEDIR.md (R1 y R2), escritas antes de correr esto:
- Extiende la red de la pérdida a los minutos 1 a 14 (mismos doce rasgos, misma logística), aprendiendo con 2021-2023.
- La compara a ciegas con la fórmula normal, la tabla por minuto y |z|, la logística de tres rasgos y un perceptrón 12-16-8.
- Mide, trimestre por trimestre, cuánto se aparta lo ocurrido de lo predicho en cada tramo de probabilidad (h y H).
- Prueba la recalibración mensual con los 90 días anteriores.
Deja datos\\modelo.json (lo que usan la Mesa, la caja y la placa) y datos\\evaluacion.json (todas las cifras).
Uso: python -X utf8 evaluar.py            (unos minutos; pide ~1,5 GB de memoria)"""
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(os.path.dirname(AQUI), "laboratorio")
sys.path.insert(0, LAB)
import perdida_red as PRED  # noqa: E402
import velas as VL  # noqa: E402
from comun import DESDE_RED, TRAMO  # noqa: E402
from red import MLP  # noqa: E402

sys.path.insert(0, AQUI)
import ganancia as G  # noqa: E402

SALIDA = os.path.join(AQUI, "datos", "evaluacion.json")
BORDES = np.array(list(G.TRAMOS_P) + [1.01])
CUBOS_Z = np.array([0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 1e9])


def construir(vel, desde, hasta):
    """Todas las miradas de los minutos 1 a 14 de las ventanas completas entre desde y hasta, con las fórmulas de
    perdida_red.rasgos pero por columnas. Devuelve X (n × 12), y, ventana (s), minuto, z, empate y el índice s de la rejilla."""
    n, t0 = vel.n, vel.t0
    O, Hh, Ll, C, V = (vel.A[k, :n] for k in range(5))
    a = max(0, -(-(int(desde) - t0) // 900) * 15)
    b = min(n, (int(hasta) - t0) // 60)
    s = np.arange(a, b - 14, 15, dtype=np.int64)
    s = s[s >= 62]
    cn = np.r_[0, np.cumsum(np.isnan(C).astype(np.int64))]
    s = s[((cn[s + 15] - cn[s - 61]) == 0) & np.isfinite(O[s])]
    with np.errstate(invalid="ignore", divide="ignore"):
        lc = np.log(C)
    r = np.r_[np.nan, np.diff(lc)]
    c2 = np.r_[0.0, np.cumsum(np.nan_to_num(r * r))]
    cv = np.r_[0.0, np.cumsum(np.nan_to_num(V))]
    ref, fin = O[s], C[s + 14]
    lref = np.log(ref)
    hi, lo, cruces = np.full(len(s), -np.inf), np.full(len(s), np.inf), np.zeros(len(s))
    Xs, ys, ws, ms, zs, es, ss = [], [], [], [], [], [], []
    for m in range(1, 15):
        j = s + m - 1
        hi, lo = np.maximum(hi, Hh[j]), np.minimum(lo, Ll[j])
        if m >= 2:
            cruces = cruces + ((C[j - 1] - ref) * (C[j] - ref) < 0)
        sig = np.sqrt(np.maximum((c2[j + 1] - c2[j - 59]) / 60, 1e-12))
        sig5 = np.sqrt(np.maximum((c2[j + 1] - c2[j - 4]) / 5, 1e-12))
        mov = lc[j] - lref
        z = mov / (sig * math.sqrt(15 - m))
        lado = np.where(z > 0, -1.0, 1.0)
        aa = np.minimum(np.abs(z), 8.0)
        v3 = (V[j] + V[j - 1] + V[j - 2]) / 3
        v60 = (cv[j + 1] - cv[j - 59]) / 60
        hora = ((t0 + 60 * j + 60) % 86400) / 3600
        X = np.column_stack([aa, aa * aa, np.full(len(s), (15 - m) / 5), sig5 / sig, r[j] * lado / sig,
                             (lc[j] - lc[j - 3]) * lado / (sig * math.sqrt(3)), (hi - lo) / (ref * sig * math.sqrt(m)),
                             cruces / 3, np.log((v3 + 1e-9) / (v60 + 1e-9)), np.sin(2 * np.pi * hora / 24),
                             np.cos(2 * np.pi * hora / 24), np.log(aa + 0.05)])
        ok = (mov != 0) & np.isfinite(X).all(axis=1)
        Xs.append(X[ok])
        ys.append((((fin - ref) * lado) > 0)[ok].astype(np.float64))
        ws.append((t0 + 60 * s)[ok])
        ms.append(np.full(int(ok.sum()), m, dtype=np.int64))
        zs.append(z[ok])
        es.append((fin == ref)[ok])
        ss.append(s[ok])
    return {"X": np.concatenate(Xs), "y": np.concatenate(ys), "w": np.concatenate(ws), "m": np.concatenate(ms),
            "z": np.concatenate(zs), "empate": np.concatenate(es), "s": np.concatenate(ss)}


def paridad(vel, D, cuantas=3000, semilla=7):
    """Los rasgos por columnas frente a perdida_red.rasgos (la función del vivo) en miradas al azar: mayor diferencia."""
    rng = np.random.default_rng(semilla)
    idx = rng.choice(len(D["y"]), size=min(cuantas, len(D["y"])), replace=False)
    n = vel.n
    O, Hh, Ll, C, V = (vel.A[k, :n] for k in range(5))
    peor = 0.0
    for i in idx.tolist():
        s, m = int(D["s"][i]), int(D["m"][i])
        a = max(0, s - 70)
        x, _lado = PRED.rasgos(C[a:s + 15].tolist(), Hh[a:s + 15].tolist(), Ll[a:s + 15].tolist(), V[a:s + 15].tolist(),
                               s - a, m, float(O[s]), vel.t0 + 60 * (s + m - 1))
        peor = max(peor, float(np.max(np.abs(np.array(x) - D["X"][i]))))
    return peor


def logistica(X, y, iters=25, lam=1.0):
    return PRED.ajustar(X, y, iters, lam)


def pred_log(modelo, X):
    w, mu, de = np.array(modelo["w"]), np.array(modelo["mu"]), np.array(modelo["de"])
    return 1 / (1 + np.exp(-np.clip(w[0] + ((X - mu) / de) @ w[1:], -40, 40)))


def perdida_log(p, y):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def fi(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


def trimestre(w):
    """Número de trimestre de cada ventana; el trimestre con menos de dos meses de datos se une al anterior."""
    meses = w.astype("datetime64[s]").astype("datetime64[M]").astype(np.int64)  # meses desde 1970
    q = meses // 3
    for qq in np.unique(q):
        if len(np.unique(meses[q == qq])) < 2 and (q == qq - 1).any():
            q[q == qq] = qq - 1
    return q


def nombre_trimestre(q):
    return f"{1970 + int(q) // 4}-T{int(q) % 4 + 1}"


def cocientes(p, y, w):
    """Por tramo de probabilidad predicha y trimestre: n, esperado, ocurrido y cociente ocurrido/esperado."""
    q = trimestre(w)
    tr = np.digitize(p, BORDES[1:-1])
    out = []
    for k in range(len(BORDES) - 1):
        fila = []
        for qq in np.unique(q):
            sel = (tr == k) & (q == qq)
            n, esp, ocu = int(sel.sum()), float(p[sel].sum()), float(y[sel].sum())
            fila.append({"trimestre": nombre_trimestre(qq), "n": n, "esperado": round(esp, 2), "ocurrido": int(ocu),
                         "cociente": round(ocu / esp, 4) if esp > 0 else None})
        out.append(fila)
    return out


def h_y_H(coc, minimo_esperado=20):
    """El cociente más bajo (h) y el más alto (H) de cada tramo; no cuentan los trimestres con menos de 20 aciertos esperados."""
    h, H = [], []
    for fila in coc:
        v = [f["cociente"] for f in fila if f["cociente"] is not None and f["esperado"] >= minimo_esperado]
        h.append(round(min(1.0, min(v)), 4) if v else 0.5)
        H.append(round(max(1.0, max(v)), 4) if v else 2.0)
    return h, H


def platt(p, y, iters=20):
    """Dos números (desplazamiento y pendiente) para el logit de p, por Newton."""
    lg = np.log(np.clip(p, 1e-12, 1) / np.clip(1 - p, 1e-12, 1))
    A = np.c_[np.ones(len(lg)), lg]
    w = np.array([0.0, 1.0])
    for _ in range(iters):
        q = 1 / (1 + np.exp(-np.clip(A @ w, -40, 40)))
        g = A.T @ (q - y)
        Hs = (A * (q * (1 - q))[:, None]).T @ A + 1e-6 * np.eye(2)
        w = w - np.linalg.solve(Hs, g)
    return w


def recalibrar_mensual(p, y, w, desde, hasta, dias=90):
    """Cada mes entre desde y hasta se corrige con los dos números ajustados en los `dias` anteriores (solo ventanas ya cerradas)."""
    out = p.copy()
    mes = w.astype("datetime64[s]").astype("datetime64[M]")
    lg = np.log(np.clip(p, 1e-12, 1) / np.clip(1 - p, 1e-12, 1))
    pares = []
    for mm in np.unique(mes[(w >= desde) & (w < hasta)]):
        ini = int(mm.astype("datetime64[s]").astype(np.int64))
        ent = (w >= ini - dias * 86400) & (w < ini - 900)
        if ent.sum() < 5000:
            continue
        ab = platt(p[ent], y[ent])
        sel = mes == mm
        out[sel] = 1 / (1 + np.exp(-np.clip(ab[0] + ab[1] * lg[sel], -40, 40)))
        pares.append([str(mm), round(float(ab[0]), 4), round(float(ab[1]), 4)])
    return out, pares


def tabla_z(z, m, y):
    """Frecuencia del perdedor por minuto y cubo de |z| (la referencia «tabla»)."""
    k = np.digitize(np.abs(z), CUBOS_Z[1:-1])
    T = np.zeros((15, len(CUBOS_Z) - 1, 2))
    np.add.at(T, (m, k, 0), 1)
    np.add.at(T, (m, k, 1), y)
    return T


def pred_tabla(T, z, m, base):
    k = np.digitize(np.abs(z), CUBOS_Z[1:-1])
    n, s = T[m, k, 0], T[m, k, 1]
    return (s + 5 * base) / (n + 5)  # suavizado con cinco observaciones de la frecuencia general


def main():
    t_ini = time.time()
    vel = VL.Velas(*VL.historia(DESDE_RED))
    D = construir(vel, TRAMO["aprende"][0], TRAMO["juzga"][1])
    X, y, w, m, z = D["X"], D["y"], D["w"], D["m"], D["z"]
    R = {"hecha": dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).strftime("%d/%m/%Y %H:%M"),
         "muestras": int(len(y)), "ventanas": int(len(np.unique(w))),
         "paridad_rasgos": paridad(vel, D), "empate": float(D["empate"].mean())}
    print(f"muestras {len(y):,} en {R['ventanas']:,} ventanas; paridad de rasgos {R['paridad_rasgos']:.2e}; "
          f"empates {100 * R['empate']:.4f} %", flush=True)
    sel = {n: (w >= a) & (w < b) for n, (a, b) in TRAMO.items()}
    ap, el, ju = sel["aprende"], sel["elige"], sel["juzga"]

    # ---------------- R1: modelos, todos aprendiendo solo con 2021-2023
    base = float(y[ap].mean())
    mod = logistica(X[ap], y[ap])
    p_log = pred_log(mod, X)
    mod3 = logistica(X[ap][:, :3], y[ap])
    p_log3 = pred_log(mod3, X[:, :3])
    p_fi = 0.5 * np.vectorize(math.erfc)(np.abs(z) / math.sqrt(2))
    T = tabla_z(z[ap], m[ap], y[ap])
    p_tab = pred_tabla(T, z, m, base)
    red = MLP([12, 16, 8, 1], semilla=0).ajustar(X[ap], y[ap], epocas=8, lote=2048, lr=1e-3, l2=1e-4, semilla=0)
    p_red = red.predecir(X)
    R["base_aprende"] = base
    R["modelos"] = {}
    for nombre, p in (("normal Φ(−|z|)", p_fi), ("tabla por minuto y |z|", p_tab), ("logística de 3 rasgos", p_log3),
                      ("logística de 12 rasgos", p_log), ("perceptrón 12-16-8", p_red)):
        R["modelos"][nombre] = {t: {"perdida_log": perdida_log(p[s_], y[s_]), "brier": brier(p[s_], y[s_])}
                                for t, s_ in (("elige", el), ("juzga", ju))}
        print(f"{nombre:26s} elige {R['modelos'][nombre]['elige']['perdida_log']:.5f}  juzga "
              f"{R['modelos'][nombre]['juzga']['perdida_log']:.5f}", flush=True)
    mejora = 1 - R["modelos"]["perceptrón 12-16-8"]["elige"]["perdida_log"] / R["modelos"]["logística de 12 rasgos"]["elige"]["perdida_log"]
    usa_red = mejora > 0.005
    R["mejora_perceptron_en_elige"] = mejora
    R["elegido"] = "perceptrón 12-16-8" if usa_red else "logística de 12 rasgos"
    p = p_red if usa_red else p_log
    print(f"mejora del perceptrón en elige: {100 * mejora:.3f} % → se usa {R['elegido']}", flush=True)

    # por minuto, en juzga: cuánto aporta el modelo elegido sobre la tabla
    R["por_minuto_juzga"] = {}
    for mm in range(1, 15):
        s_ = ju & (m == mm)
        R["por_minuto_juzga"][str(mm)] = {"n": int(s_.sum()), "base": float(y[s_].mean()), "tabla": perdida_log(p_tab[s_], y[s_]),
                                          "modelo": perdida_log(p[s_], y[s_])}

    # ---------------- R2: cocientes por trimestre y tramo
    coc_el, coc_ju = cocientes(p[el], y[el], w[el]), cocientes(p[ju], y[ju], w[ju])
    coc_todo = cocientes(p[el | ju], y[el | ju], w[el | ju])
    h_el, H_el = h_y_H(coc_el)
    h_todo, H_todo = h_y_H(coc_todo)
    R["cocientes"] = {"elige": coc_el, "juzga": coc_ju}
    R["h_elige"], R["H_elige"], R["h_vivo"], R["H_vivo"] = h_el, H_el, h_todo, H_todo
    print("h elige ", h_el, "\nH elige ", H_el, "\nh vivo  ", h_todo, "\nH vivo  ", H_todo, flush=True)

    # recalibración mensual con 90 días
    p_rec, pares = recalibrar_mensual(p, y, w, TRAMO["elige"][0], TRAMO["juzga"][1])
    h_rec, H_rec = h_y_H(cocientes(p_rec[el], y[el], w[el]))
    ancho = float(np.mean(np.array(H_el) - np.array(h_el)))
    ancho_rec = float(np.mean(np.array(H_rec) - np.array(h_rec)))
    entra_rec = ancho_rec < ancho and min(h_rec) > min(h_el)
    R["recalibracion"] = {"h_elige": h_rec, "H_elige": H_rec, "ancho_sin": ancho, "ancho_con": ancho_rec, "entra": bool(entra_rec),
                          "perdida_log_elige": perdida_log(p_rec[el], y[el]), "perdida_log_juzga": perdida_log(p_rec[ju], y[ju])}
    print(f"recalibración: ancho medio {ancho:.3f} → {ancho_rec:.3f}; h mínimo {min(h_el)} → {min(h_rec)}; entra: {entra_rec}", flush=True)

    # ---------------- la regla prudente, juzgada una vez en «juzga» con h y H de «elige»
    tr = np.digitize(p, BORDES[1:-1])
    p_prud = p * np.array(h_el)[tr]
    p_alta = np.minimum(1.0, p * np.array(H_el)[tr])
    R["prudente_en_juzga"] = []
    for k in range(len(BORDES) - 1):
        s_ = ju & (tr == k)
        n = int(s_.sum())
        R["prudente_en_juzga"].append({"tramo": [float(BORDES[k]), float(BORDES[k + 1])], "n": n,
                                       "predicho": float(p[s_].mean()) if n else None, "prudente": float(p_prud[s_].mean()) if n else None,
                                       "alta": float(p_alta[s_].mean()) if n else None, "ocurrido": float(y[s_].mean()) if n else None})
    for f in R["prudente_en_juzga"]:
        if f["n"]:
            print(f"  tramo {f['tramo']}: n {f['n']:,} predicho {100 * f['predicho']:.3f} % prudente {100 * f['prudente']:.3f} % "
                  f"ocurrido {100 * f['ocurrido']:.3f} % alta {100 * f['alta']:.3f} %", flush=True)

    # ---------------- precio justo por minuto y |z| en juzga (lo que vale el lado perdedor), para el informe
    R["justo_juzga"] = {}
    for mm in (3, 6, 9, 11, 12, 13, 14):
        fila = {}
        for lo, hi in ((0.5, 1), (1, 1.5), (1.5, 2), (2, 2.5), (2.5, 3), (3, 4), (4, 1e9)):
            s_ = ju & (m == mm) & (np.abs(z) >= lo) & (np.abs(z) < hi)
            n = int(s_.sum())
            fila[f"{lo:g}-{hi:g}" if hi < 1e8 else f"{lo:g}+"] = {"n": n, "ocurrido": float(y[s_].mean()) if n else None,
                                                                  "modelo": float(p[s_].mean()) if n else None}
        R["justo_juzga"][str(mm)] = fila

    # ---------------- cuánto separa la red dentro de una misma celda de la tabla (lo que añade a mirar solo |z| y el minuto)
    R["separa"] = []
    for mm in (11, 12, 13, 14):
        for lo, hi in ((1, 1.5), (1.5, 2), (2, 3)):
            s_ = ju & (m == mm) & (np.abs(z) >= lo) & (np.abs(z) < hi)
            if s_.sum() < 2000:
                continue
            pp, yy = p[s_], y[s_]
            corte = np.quantile(pp, 0.8)
            alto = pp >= corte
            R["separa"].append({"minuto": mm, "z": f"{lo:g}-{hi:g}", "n": int(s_.sum()), "todo": float(yy.mean()),
                                "quinto_alto_predicho": float(pp[alto].mean()), "quinto_alto_ocurrido": float(yy[alto].mean()),
                                "resto_ocurrido": float(yy[~alto].mean())})

    # ---------------- modelo para el vivo: el elegido, con h y H de los once trimestres
    if usa_red:
        modelo = {"tipo": "perceptron", **red.a_dict()}
    else:
        modelo = {"tipo": "logistica", "w": mod["w"], "mu": mod["mu"], "de": mod["de"]}
    modelo.update({"nombres": PRED.NOMBRES, "minutos": [1, 14], "tramos_p": list(G.TRAMOS_P), "h": h_todo, "H": H_todo,
                   "h_elige": h_el, "H_elige": H_el, "p_empate": R["empate"], "aprende": "2021-2023", "hecho": R["hecha"],
                   "recalibracion": None})
    cuerpo = json.dumps({k: modelo[k] for k in sorted(modelo) if k != "huella"}, sort_keys=True).encode()
    modelo["huella"] = hashlib.sha256(cuerpo).hexdigest()[:16]
    with open(G.MODELO, "w", encoding="utf-8") as f:
        json.dump(modelo, f, ensure_ascii=False, indent=1)
    R["huella_modelo"] = modelo["huella"]
    R["segundos"] = round(time.time() - t_ini, 1)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
    np.savez_compressed(os.path.join(AQUI, "datos", "probabilidades.npz"), w=w, m=m.astype(np.int8), z=z.astype(np.float32),
                        y=y.astype(np.int8), p=p.astype(np.float32), empate=D["empate"])
    print(f"listo en {R['segundos']} s; modelo {modelo['huella']}", flush=True)


if __name__ == "__main__":
    main()
