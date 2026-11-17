"""Entrena el modelo del operador para una ventana de 5 o de 15 minutos (16/11/2026). Solo historia y cuentas: nada compra.

Mismo procedimiento del 12/11 (comprador/evaluar.py, reglas R1 y R2): logística de doce rasgos con penalización, aprendida
solo con 2021-2023; cocientes por trimestre y tramo de probabilidad en «elige» y «juzga»; h y H para la probabilidad prudente.
Con W = 15 debe reproducir comprador/datos/modelo.json (pesos, h y H): es la prueba de que esta receta es la misma.
Corre solo en el PC (usa numpy y la historia de velas del laboratorio).

Uso: python -X utf8 entrenar.py 15      reproduce el de 15 y lo compara con el del 12/11
     python -X utf8 entrenar.py 5       hace el de 5 (enmienda 2)
Deja datos/modelo_W.json (lo que usa la caja) y datos/evaluacion_W.json (las cifras)."""
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "laboratorio"))
import perdida_red as PRED  # noqa: E402  el mismo ajuste (Newton con penalización) del 12/11
import velas as VL  # noqa: E402
from comun import DESDE_RED, TRAMO  # noqa: E402

sys.path.insert(0, AQUI)
import nucleo as N  # noqa: E402

BORDES = np.array(list(N.TRAMOS_P) + [1.01])
MODELO_1211 = os.path.join(RAIZ, "comprador", "datos", "modelo.json")


def construir(vel, desde, hasta, W):
    """Todas las miradas de los minutos 1 a W − 1 de las ventanas completas entre desde y hasta, con las fórmulas de
    nucleo.rasgos pero por columnas. Devuelve X (n × 12), y, ventana (s), minuto, z, empate y el índice s de la rejilla."""
    n, t0 = vel.n, vel.t0
    O, Hh, Ll, C, V = (vel.A[k, :n] for k in range(5))
    a = max(0, -(-(int(desde) - t0) // (60 * W)) * W)
    b = min(n, (int(hasta) - t0) // 60)
    s = np.arange(a, b - (W - 1), W, dtype=np.int64)
    s = s[s >= 62]
    cn = np.r_[0, np.cumsum(np.isnan(C).astype(np.int64))]
    s = s[((cn[s + W] - cn[s - 61]) == 0) & np.isfinite(O[s])]
    with np.errstate(invalid="ignore", divide="ignore"):
        lc = np.log(C)
    r = np.r_[np.nan, np.diff(lc)]
    c2 = np.r_[0.0, np.cumsum(np.nan_to_num(r * r))]
    cv = np.r_[0.0, np.cumsum(np.nan_to_num(V))]
    ref, fin = O[s], C[s + W - 1]
    lref = np.log(ref)
    hi, lo, cruces = np.full(len(s), -np.inf), np.full(len(s), np.inf), np.zeros(len(s))
    Xs, ys, ws, ms, zs, es, ss = [], [], [], [], [], [], []
    for m in range(1, W):
        j = s + m - 1
        hi, lo = np.maximum(hi, Hh[j]), np.minimum(lo, Ll[j])
        if m >= 2:
            cruces = cruces + ((C[j - 1] - ref) * (C[j] - ref) < 0)
        sig = np.sqrt(np.maximum((c2[j + 1] - c2[j - 59]) / 60, 1e-12))
        sig5 = np.sqrt(np.maximum((c2[j + 1] - c2[j - 4]) / 5, 1e-12))
        mov = lc[j] - lref
        z = mov / (sig * math.sqrt(W - m))
        lado = np.where(z > 0, -1.0, 1.0)
        aa = np.minimum(np.abs(z), 8.0)
        v3 = (V[j] + V[j - 1] + V[j - 2]) / 3
        v60 = (cv[j + 1] - cv[j - 59]) / 60
        hora = ((t0 + 60 * j + 60) % 86400) / 3600
        X = np.column_stack([aa, aa * aa, np.full(len(s), (W - m) / 5), sig5 / sig, r[j] * lado / sig,
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


def paridad_rasgos(vel, D, W, cuantas=3000, semilla=7):
    """Los rasgos por columnas frente a nucleo.rasgos (la función del vivo) en miradas al azar: mayor diferencia."""
    rng = np.random.default_rng(semilla)
    idx = rng.choice(len(D["y"]), size=min(cuantas, len(D["y"])), replace=False)
    n = vel.n
    O, Hh, Ll, C, V = (vel.A[k, :n] for k in range(5))
    peor = 0.0
    for i in idx.tolist():
        s, m = int(D["s"][i]), int(D["m"][i])
        a = max(0, s - 70)
        x, _lado = N.rasgos(C[a:s + W].tolist(), Hh[a:s + W].tolist(), Ll[a:s + W].tolist(), V[a:s + W].tolist(),
                            s - a, m, float(O[s]), vel.t0 + 60 * (s + m - 1), W)
        peor = max(peor, float(np.max(np.abs(np.array(x) - D["X"][i]))))
    return peor


def pred_log(modelo, X):
    w, mu, de = np.array(modelo["w"]), np.array(modelo["mu"]), np.array(modelo["de"])
    return 1 / (1 + np.exp(-np.clip(w[0] + ((X - mu) / de) @ w[1:], -40, 40)))


def perdida_log(p, y):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(p, y):
    return float(np.mean((p - y) ** 2))


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


def main(W):
    t_ini = time.time()
    vel = VL.Velas(*VL.historia(DESDE_RED))
    D = construir(vel, TRAMO["aprende"][0], TRAMO["juzga"][1], W)
    X, y, w, m, z = D["X"], D["y"], D["w"], D["m"], D["z"]
    R = {"ventana": W, "hecha": dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).strftime("%d/%m/%Y %H:%M"),
         "muestras": int(len(y)), "ventanas": int(len(np.unique(w))),
         "paridad_rasgos": paridad_rasgos(vel, D, W), "empate": float(D["empate"].mean())}
    print(f"ventana de {W} min: {len(y):,} miradas en {R['ventanas']:,} ventanas; paridad de rasgos {R['paridad_rasgos']:.2e}; "
          f"empates {100 * R['empate']:.4f} %", flush=True)
    sel = {n: (w >= a) & (w < b) for n, (a, b) in TRAMO.items()}
    ap, el, ju = sel["aprende"], sel["elige"], sel["juzga"]

    # R1: la logística de doce rasgos, aprendiendo solo con 2021-2023; referencias: la fórmula normal y la de tres rasgos
    base = float(y[ap].mean())
    mod = PRED.ajustar(X[ap], y[ap], 25, 1.0)
    p = pred_log(mod, X)
    mod3 = PRED.ajustar(X[ap][:, :3], y[ap], 25, 1.0)
    p3 = pred_log(mod3, X[:, :3])
    p_fi = 0.5 * np.vectorize(math.erfc)(np.abs(z) / math.sqrt(2))
    R["base_aprende"] = base
    R["modelos"] = {}
    for nombre, pp in (("normal Φ(−|z|)", p_fi), ("logística de 3 rasgos", p3), ("logística de 12 rasgos", p)):
        R["modelos"][nombre] = {t: {"perdida_log": perdida_log(pp[s_], y[s_]), "brier": brier(pp[s_], y[s_])}
                                for t, s_ in (("elige", el), ("juzga", ju))}
        print(f"{nombre:26s} elige {R['modelos'][nombre]['elige']['perdida_log']:.5f}  juzga "
              f"{R['modelos'][nombre]['juzga']['perdida_log']:.5f}", flush=True)
    R["mejora_sobre_normal_en_elige"] = 1 - R["modelos"]["logística de 12 rasgos"]["elige"]["perdida_log"] / R["modelos"]["normal Φ(−|z|)"]["elige"]["perdida_log"]
    R["por_minuto_juzga"] = {}
    for mm in range(1, W):
        s_ = ju & (m == mm)
        R["por_minuto_juzga"][str(mm)] = {"n": int(s_.sum()), "base": float(y[s_].mean()), "normal": perdida_log(p_fi[s_], y[s_]),
                                          "modelo": perdida_log(p[s_], y[s_])}

    # R2: cocientes por trimestre y tramo
    coc_el, coc_ju = cocientes(p[el], y[el], w[el]), cocientes(p[ju], y[ju], w[ju])
    coc_todo = cocientes(p[el | ju], y[el | ju], w[el | ju])
    h_el, H_el = h_y_H(coc_el)
    h_todo, H_todo = h_y_H(coc_todo)
    R["cocientes"] = {"elige": coc_el, "juzga": coc_ju}
    R["h_elige"], R["H_elige"], R["h_vivo"], R["H_vivo"] = h_el, H_el, h_todo, H_todo
    print("h elige ", h_el, "\nH elige ", H_el, "\nh vivo  ", h_todo, "\nH vivo  ", H_todo, flush=True)

    # la regla prudente, juzgada una vez en «juzga» con h y H de «elige»
    tr = np.digitize(p, BORDES[1:-1])
    p_prud = p * np.array(h_el)[tr]
    R["prudente_en_juzga"] = []
    for k in range(len(BORDES) - 1):
        s_ = ju & (tr == k)
        n = int(s_.sum())
        R["prudente_en_juzga"].append({"tramo": [float(BORDES[k]), float(BORDES[k + 1])], "n": n,
                                       "predicho": float(p[s_].mean()) if n else None, "prudente": float(p_prud[s_].mean()) if n else None,
                                       "ocurrido": float(y[s_].mean()) if n else None})
    for f in R["prudente_en_juzga"]:
        if f["n"]:
            print(f"  tramo {f['tramo']}: n {f['n']:,} predicho {100 * f['predicho']:.3f} % prudente {100 * f['prudente']:.3f} % "
                  f"ocurrido {100 * f['ocurrido']:.3f} %", flush=True)

    modelo = {"tipo": "logistica", "w": mod["w"], "mu": mod["mu"], "de": mod["de"]}
    modelo.update({"nombres": N.NOMBRES, "minutos": [1, W - 1], "tramos_p": list(N.TRAMOS_P), "h": h_todo, "H": H_todo,
                   "h_elige": h_el, "H_elige": H_el, "p_empate": R["empate"], "aprende": "2021-2023", "hecho": R["hecha"],
                   "recalibracion": None})
    if W != 15:
        modelo["ventana"] = W
    cuerpo = json.dumps({k: modelo[k] for k in sorted(modelo) if k != "huella"}, sort_keys=True).encode()
    modelo["huella"] = hashlib.sha256(cuerpo).hexdigest()[:16]

    if W == 15 and os.path.exists(MODELO_1211):  # criterio 1: la receta reproduce el modelo del 12/11
        ref = json.load(open(MODELO_1211, encoding="utf-8"))
        dif = {k: float(np.max(np.abs(np.array(modelo[k]) - np.array(ref[k])))) for k in ("w", "mu", "de", "h", "H", "h_elige", "H_elige")}
        dif["p_empate"] = abs(modelo["p_empate"] - ref["p_empate"])
        R["paridad_con_modelo_1211"] = {"huella_1211": ref.get("huella"), "diferencias": dif, "igual": max(dif.values()) < 1e-9}
        print("paridad con el modelo del 12/11:", {k: f"{v:.1e}" for k, v in dif.items()}, "→",
              "IGUAL" if R["paridad_con_modelo_1211"]["igual"] else "DISTINTO", flush=True)
        if R["paridad_con_modelo_1211"]["igual"]:   # se usa el archivo del 12/11 tal cual, con su huella
            modelo = ref
    R["huella_modelo"] = modelo["huella"]
    R["segundos"] = round(time.time() - t_ini, 1)
    os.makedirs(N.DATOS, exist_ok=True)
    with open(N.ruta_modelo(W), "w", encoding="utf-8") as f:
        json.dump(modelo, f, ensure_ascii=False, indent=1)
    with open(os.path.join(N.DATOS, f"evaluacion_{W}.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
    print(f"listo en {R['segundos']} s; modelo de {W} min: {modelo['huella']}", flush=True)


if __name__ == "__main__":
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if W not in N.VENTANAS:
        sys.exit("uso: python -X utf8 entrenar.py 15 | 5")   # un argumento que no se reconoce no hace nada
    main(W)
