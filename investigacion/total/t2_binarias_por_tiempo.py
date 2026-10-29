"""T2 (29/10/2026): apuestas binarias por tiempo (vencimiento), con y sin preventivas, en las 12 monedas, 2020-2026.

Pedido de Nicolás: «operaciones binarias, en cuanto a tiempos», con preventivas por horario, zona y margen.
Una binaria gana si el precio al vencimiento queda del lado apostado: cobra el pago P o pierde lo apostado. Para no perder
hace falta acertar 1/(1+P): 55,6 % con P = 0,80; 54,1 % con 0,85; 52,6 % con 0,90; 52,1 % con 0,92.

Reglas fijadas ANTES de mirar resultados:
- Velas alineadas de 1, 5, 15 y 60 min armadas desde las de 1 min de futuros de Binance (sin huecos). Señal al cierre de la
  vela; precio de entrada = ese cierre (optimista: un bróker entra unos segundos después). Vencimientos de 1 y 3 velas.
  Empate = pérdida.
- Señales: REV vela fuerte (cuerpo ≥ 2 × la media de los 100 cuerpos previos) → apuesta en contra; CONT la misma vela → a
  favor; RECH la vela toca el máximo de las 20 previas y cierra bajista → abajo, o toca el mínimo y cierra alcista → arriba
  (su regla de las resistencias); AZAR una de cada diez velas con dirección al azar (control).
- Preventivas: horario ASIA 00-07, EUROPA 07-13, AMERICA 13-21 UTC; volatilidad VALTA (rango medio de las 20 velas previas
  mayor que el de las 500 previas) o VBAJA; zona CTX (apuesta a favor del contexto diario: cierre de ayer sobre o bajo la
  SMA 50) o CONTRA.
- Se adopta una combinación solo si acierta ≥ 54,1 % (pago 0,85) en 2020-23 Y en 2024-26 con ≥ 300 apuestas en cada mitad.
- Margen: apuesta fija del 2 % del saldo; crecimiento esperado por apuesta = p·0,85·0,02 − (1 − p)·0,02.
Uso: python -I t2_binarias_por_tiempo.py > t2_binarias_por_tiempo.txt"""
import datetime as dt
import json
import os
import re
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos"), "um")
CORTE = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp())
VIEJAS = ["ETH", "SOL", "BNB", "XRP", "DOGE", "ADA"]
NUEVAS = ["LINK", "AVAX", "LTC", "DOT", "TRX"]
ACTIVOS = ["BTC"] + VIEJAS + NUEVAS
TFS, VENC = (1, 5, 15, 60), (1, 3)
SENALES = ("REV", "CONT", "RECH", "AZAR")
FILTROS = ("—", "ASIA", "EUROPA", "AMERICA", "VALTA", "VBAJA", "CTX", "CONTRA")
EQUILIBRIO = 1 / 1.85


def es(s):
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "§", s)
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", s)
    return s.replace("§", ".")


def p(s=""):
    print(es(s))


def media_previa(x, n):
    """Media de los n valores ANTERIORES a cada posición (NaN al principio)."""
    cs = np.concatenate([[0.0], np.cumsum(x)])
    m = np.full(len(x), np.nan)
    m[n:] = (cs[n:-1] - cs[:-n - 1]) / n
    return m


def extremo_previo(x, n, f):
    out = np.full(len(x), np.nan)
    if len(x) > n:
        out[n:] = f(np.lib.stride_tricks.sliding_window_view(x[:-1], n), axis=1)
    return out


def contexto_diario(t, c):
    """+1 / −1 por día: cierre de ayer sobre o bajo la SMA 50 de los cierres diarios anteriores."""
    dia = t // 86400
    ultimo = np.r_[np.flatnonzero(np.diff(dia)), len(dia) - 1]
    d, cd = dia[ultimo], c[ultimo]
    sma = np.full(len(cd), np.nan)
    if len(cd) > 50:
        cs = np.concatenate([[0.0], np.cumsum(cd)])
        sma[50:] = (cs[50:-1] - cs[:-51]) / 50  # SMA 50 de los cierres hasta ayer, para el día siguiente
    ctx_hoy = np.zeros(len(cd))
    ctx_hoy[1:] = np.sign(cd[:-1] - sma[1:])
    return dict(zip(d.tolist(), np.nan_to_num(ctx_hoy).tolist()))


def procesar(activo, acum, rng):
    x = np.load(os.path.join(DATOS, f"{activo}USDT_um_1m.npy"), mmap_mode="r")
    t = (x[:, 0] // 1000).astype(np.int64)
    o1, h1, l1, c1 = (np.asarray(x[:, k]) for k in (1, 2, 3, 4))
    ctxd = contexto_diario(t, c1)
    grupo = "BTC" if activo == "BTC" else "VIEJAS" if activo in VIEJAS else "NUEVAS"
    for tf in TFS:
        i0 = int(np.argmax(t % (tf * 60) == 0))
        n = (len(t) - i0) // tf * tf
        T = t[i0:i0 + n].reshape(-1, tf)[:, 0]
        O = o1[i0:i0 + n].reshape(-1, tf)[:, 0]
        H = h1[i0:i0 + n].reshape(-1, tf).max(1)
        L = l1[i0:i0 + n].reshape(-1, tf).min(1)
        C = c1[i0:i0 + n].reshape(-1, tf)[:, -1]
        cuerpo = np.abs(C - O)
        fuerte = cuerpo >= 2 * media_previa(cuerpo, 100)
        hmax, lmin = extremo_previo(H, 20, np.max), extremo_previo(L, 20, np.min)
        rango = H - L
        valta = media_previa(rango, 20) > media_previa(rango, 500)
        hora = ((T + tf * 60) % 86400) // 3600
        ses = np.where(hora < 7, 0, np.where(hora < 13, 1, np.where(hora < 21, 2, 3)))
        ctx = np.array([ctxd.get(int(d), 0.0) for d in (T // 86400)])
        periodo = np.where(T < CORTE, 0, 1)
        sentido = np.sign(C - O)
        dirs = {
            "REV": np.where(fuerte, -sentido, 0),
            "CONT": np.where(fuerte, sentido, 0),
            "RECH": np.where((H >= hmax) & (C < O), -1, np.where((L <= lmin) & (C > O), 1, 0)),
            "AZAR": np.where(rng.random(len(C)) < 0.1, rng.choice([-1, 1], len(C)), 0),
        }
        for venc in VENC:
            futuro = np.full(len(C), np.nan)
            futuro[:-venc] = C[venc:]
            for s, d in dirs.items():
                ok = (d != 0) & ~np.isnan(futuro)
                gana = (d * (futuro - C) > 0)
                filtros = {"—": ok, "ASIA": ok & (ses == 0), "EUROPA": ok & (ses == 1), "AMERICA": ok & (ses == 2),
                           "VALTA": ok & valta, "VBAJA": ok & ~valta & ~np.isnan(media_previa(rango, 500)),
                           "CTX": ok & (d == ctx), "CONTRA": ok & (d == -ctx)}
                for fn, m in filtros.items():
                    for per in (0, 1):
                        mm = m & (periodo == per)
                        nn, gg = int(mm.sum()), int((gana & mm).sum())
                        for g in (grupo, "TODAS"):
                            k = (g, tf, venc, s, fn, per)
                            a = acum.setdefault(k, [0, 0])
                            a[0] += nn
                            a[1] += gg


def main():
    rng = np.random.default_rng(29102026)
    acum = {}
    for a in ACTIVOS:
        procesar(a, acum, rng)
        print(f"   … {a} listo", file=sys.stderr, flush=True)
    p("T2 · BINARIAS POR TIEMPO · 12 monedas de futuros de Binance, velas de 1 min de 2020-2026")
    p("acierto en 2020-23 / 2024-26 (n de la segunda mitad) · para no perder con pago 85 % hace falta 54.1 %\n")
    adoptadas = []
    for g in ("TODAS", "BTC", "VIEJAS", "NUEVAS"):
        for tf in TFS:
            for venc in VENC:
                for s in SENALES:
                    def tasa(fn, per):
                        n, w = acum.get((g, tf, venc, s, fn, per), (0, 0))
                        return (w / n * 100 if n else float("nan")), n
                    for fn in FILTROS:
                        (ra, na), (rb, nb) = tasa(fn, 0), tasa(fn, 1)
                        if na >= 300 and nb >= 300 and ra >= EQUILIBRIO * 100 and rb >= EQUILIBRIO * 100:
                            adoptadas.append((g, tf, venc, s, fn, ra, rb, na, nb))
                    if g == "TODAS":
                        (ra, na), (rb, nb) = tasa("—", 0), tasa("—", 1)
                        mejor = max(FILTROS[1:], key=lambda fn: min(tasa(fn, 0)[0], tasa(fn, 1)[0]))
                        (fa, _), (fb, fnb) = tasa(mejor, 0), tasa(mejor, 1)
                        p(f"vela {tf:>2d} min · vence en {venc * tf:>3d} min · {s:4s}: {ra:5.2f} % / {rb:5.2f} % (n={nb:,}) · "
                          f"mejor preventiva {mejor:7s}: {fa:5.2f} % / {fb:5.2f} % (n={fnb:,})")
    p(f"\nCOMBINACIONES QUE GANAN CON PAGO 85 % EN LAS DOS MITADES (≥ 54.1 % y ≥ 300 apuestas en cada una): {len(adoptadas)}")
    for g, tf, venc, s, fn, ra, rb, na, nb in sorted(adoptadas, key=lambda x: -min(x[5], x[6]))[:25]:
        r = min(ra, rb) / 100
        crec = r * 0.85 * 0.02 - (1 - r) * 0.02
        p(f"   {g:6s} vela {tf:>2d} min, vence {venc * tf:>3d} min, {s:4s} con {fn:7s}: {ra:.2f} % / {rb:.2f} % "
          f"(n {na:,} / {nb:,}) · con 2 % por apuesta, {crec * 100:+.3f} % del saldo por apuesta en la peor mitad")
    if not adoptadas:
        p("   ninguna: con pago 85 % ninguna señal, vela ni preventiva gana en las dos mitades.")
    with open(os.path.join(AQUI, "t2_binarias.json"), "w", encoding="utf-8") as f:
        json.dump({"|".join(map(str, k)): v for k, v in acum.items()}, f)


if __name__ == "__main__":
    main()
