"""T4 (29/10/2026): las señales del curso de Nicolás como binarias, confirmadas con datos que no se usaron para elegirlas.

Origen: sesión del 28/10 (PROMPT BINARIAS BTC - RETOMAR.txt): en BTC, velas de 5 min, «tres cuervos al revés» (apostar a que
sube) acertó 58,4 % (2020-23) y 54,9 % (2024-26); «tres soldados al revés» 55,8 / 53,7 %; martillo invertido a 10 min
55,1 / 52,7 %. Esa misma sesión dejó dicho: «lo de al revés salió mirando los mismos datos: hay que confirmarlo con datos
nuevos antes de creerlo». Aquí los datos nuevos son las otras 11 monedas, con las mismas reglas.

Reglas fijadas antes de mirar (definiciones idénticas a consolidacion/patrones_std.py, en numpy):
- Velas de 5 min alineadas desde las de 1 min de futuros de Binance (2020-2026, sin huecos).
- tres_cuervos: tendencia previa al alza (cierre i−3 > cierre i−13), tres velas bajistas fuertes (cuerpo ≥ 50 % del rango)
  con cierres decrecientes → AL REVÉS: apuesta a que SUBE. tres_soldados: el espejo → AL REVÉS: apuesta a que BAJA.
  martillo_invertido: tendencia previa a la baja, mecha superior ≥ 2 cuerpos, inferior ≤ 0,5 cuerpo, rango > 0,5 × media
  de 20 → apuesta a que SUBE (sin dar vuelta).
- LIBRO: entra al abrir el minuto siguiente a la vela del patrón; vence al cierre del minuto entrada + plazo − 1.
  REAL: entra un minuto después (el agente ve la vela, decide y apuesta) y vence un plazo después de su entrada.
- Empate = se devuelve lo apostado (no cuenta). Plazos de 5, 10 y 15 min.
- Una señal queda confirmada si en las monedas nuevas (las 11 que no son BTC) acierta, con entrada REAL, por encima de lo
  necesario con pago 0,85 (54,1 %) en 2020-23 y en 2024-26, con ≥ 300 apuestas en cada mitad.
Uso: python -I t4_patrones_binarias.py > t4_patrones_binarias.txt"""
import datetime as dt
import os
import re
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DATOS = os.environ.get("TRADER_DATOS_UM") or r"C:\Users\ni109\Ingresos\trader-btc\datos\um"
CORTE = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp())
ACTIVOS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "LINK", "AVAX", "LTC", "DOT", "TRX"]
PLAZOS = (5, 10, 15)
SENALES = {"tres_cuervos AL REVÉS (sube)": 1, "tres_soldados AL REVÉS (baja)": -1, "martillo_invertido (sube)": 1}


def es(s):
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "§", s)
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", s)
    return s.replace("§", ".")


def p(s=""):
    print(es(s))


def atras(x, k):
    y = np.full(len(x), np.nan)
    y[k:] = x[:-k]
    return y


def patrones(O, H, L, C):
    cuerpo, rango = np.abs(C - O), H - L
    sup, inf = H - np.maximum(O, C), np.minimum(O, C) - L
    alc, baj = C > O, C < O
    fa, fb = alc & (cuerpo >= 0.5 * rango), baj & (cuerpo >= 0.5 * rango)
    fa1, fa2 = np.r_[False, fa[:-1]], np.r_[False, False, fa[:-2]]
    fb1, fb2 = np.r_[False, fb[:-1]], np.r_[False, False, fb[:-2]]
    c1, c2, c3, c11, c13 = atras(C, 1), atras(C, 2), atras(C, 3), atras(C, 11), atras(C, 13)
    with np.errstate(invalid="ignore", divide="ignore"):
        t = (c1 - c11) / c11
        t3 = (c3 - c13) / c13
        cs = np.concatenate([[0.0], np.cumsum(rango)])
        rmed = np.full(len(C), np.nan)
        rmed[20:] = (cs[20:-1] - cs[:-21]) / 20
        inv = (cuerpo > 0) & (sup >= 2 * cuerpo) & (inf <= 0.5 * cuerpo) & (rango > 0.5 * rmed)
        return {"tres_cuervos AL REVÉS (sube)": (t3 > 0) & fb & fb1 & fb2 & (C < c1) & (c1 < c2),
                "tres_soldados AL REVÉS (baja)": (t3 < 0) & fa & fa1 & fa2 & (C > c1) & (c1 > c2),
                "martillo_invertido (sube)": (t < 0) & inv}


def medir(activo, acum):
    x = np.load(os.path.join(DATOS, f"{activo}USDT_um_1m.npy"), mmap_mode="r")
    t = (x[:, 0] // 1000).astype(np.int64)
    o1, h1, l1, c1 = (np.asarray(x[:, k]) for k in (1, 2, 3, 4))
    i0 = int(np.argmax(t % 300 == 0))
    n = (len(t) - i0) // 5 * 5
    O = o1[i0:i0 + n].reshape(-1, 5)[:, 0]
    H = h1[i0:i0 + n].reshape(-1, 5).max(1)
    L = l1[i0:i0 + n].reshape(-1, 5).min(1)
    C = c1[i0:i0 + n].reshape(-1, 5)[:, -1]
    T = t[i0:i0 + n].reshape(-1, 5)[:, 0]
    grupo = "BTC" if activo == "BTC" else "NUEVAS"
    for nombre, mascara in patrones(O, H, L, C).items():
        lado = SENALES[nombre]
        j = np.flatnonzero(mascara)
        k = i0 + (j + 1) * 5  # primer minuto después de la vela del patrón
        per = (T[j] + 300 >= CORTE).astype(int)
        for plazo in PLAZOS:
            ok_l = k + plazo - 1 < len(c1)
            ok_r = k + 1 + plazo < len(c1)
            res_l = np.sign((c1[np.minimum(k + plazo - 1, len(c1) - 1)] - o1[np.minimum(k, len(c1) - 1)]) * lado) * ok_l
            res_r = np.sign((c1[np.minimum(k + plazo, len(c1) - 1)] - c1[np.minimum(k, len(c1) - 1)]) * lado) * ok_r
            for g in (grupo, "TODAS"):
                for tipo, res in (("libro", res_l), ("real", res_r)):
                    for pp in (0, 1):
                        m = per == pp
                        a = acum.setdefault((g, nombre, plazo, tipo, pp), [0, 0])
                        a[0] += int((res[m] > 0).sum())
                        a[1] += int((res[m] < 0).sum())


def main():
    acum = {}
    for a in ACTIVOS:
        medir(a, acum)
        print(f"   … {a}", file=sys.stderr, flush=True)
    p("T4 · SEÑALES DEL CURSO COMO BINARIAS · velas de 5 min de futuros de Binance, 2020-2026 · empate = se devuelve")
    p("acierto 2020-23 / 2024-26 (apuestas de la segunda mitad) · LIBRO = entra al cierre de la vela · REAL = un minuto después")
    p("para no perder: 55.6 % con pago 0,80 · 54.1 % con 0,85 · 52.6 % con 0,90 · 52.1 % con 0,92\n")
    confirmadas = []
    for nombre in SENALES:
        p(f"== {nombre} ==")
        for plazo in PLAZOS:
            linea = f"   vence en {plazo:2d} min:"
            for g in ("BTC", "NUEVAS"):
                for tipo in ("libro", "real"):
                    v = []
                    for pp in (0, 1):
                        w, l = acum.get((g, nombre, plazo, tipo, pp), (0, 0))
                        v.append((w / (w + l) * 100 if w + l else float("nan"), w + l))
                    linea += f"  {g} {tipo} {v[0][0]:5.2f} / {v[1][0]:5.2f} % (n={v[1][1]:,})"
                    if g == "NUEVAS" and tipo == "real" and min(v[0][1], v[1][1]) >= 300 and min(v[0][0], v[1][0]) >= 100 / 1.85:
                        confirmadas.append((nombre, plazo, v[0][0], v[1][0]))
            p(linea)
        p()
    p("CONFIRMADAS EN LAS 11 MONEDAS NUEVAS (entrada REAL, ≥ 54,1 % en las dos mitades): " + (
        "; ".join(f"{n} a {pl} min ({a:.2f} / {b:.2f} %)" for n, pl, a, b in confirmadas) if confirmadas else "ninguna"))


if __name__ == "__main__":
    main()
