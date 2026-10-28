"""A6 (28/10/2026): apuestas cortas a la reversión después de velas fuertes, al estilo de Nicolás (muchas al día, más riesgo).

Pedido: «0,5 % no me sirve; arriesgue más y piénselo con mejores estrategias. Antes apostaba 50.000 y a los segundos tenía 100.000».
Hallazgo de a5_base_velas.txt: después de una vela bajista fuerte o de un impulso bajista con volumen, BTC sube en las 4 velas
siguientes el 53-57 % de las veces (en 5 m, 15 m, 1 h y 4 h, igual en 2020-23 y 2024-26); después de las alcistas fuertes,
baja el 51-53 %. Aquí se mide si eso deja dinero apostando muchas veces al día.

Reglas fijadas ANTES de mirar resultados (una sola definición, la de consolidacion/clases_vela.py):
- Señal al cierre de una vela de M (5 m, 15 m o 1 h): LARGO si la vela es «impulso bajista con volumen» o «bajista fuerte que
  cierra abajo»; CORTO si es «impulso alcista con volumen» o «alcista fuerte que cierra arriba». Una apuesta abierta a la vez
  por marco: mientras dura, las señales nuevas se ignoran.
- (A) APUESTA DE DIRECCIÓN (opción binaria): gana si el cierre 4 velas después está a favor; empate = se devuelve. Pago
  80, 85, 88 o 92 % de lo apostado.
- (B) FUTUROS DE BINANCE: entrada al cierre de la señal (tomador 0,05 %); objetivo y stop simétricos a 0,5 o 1,0 ATR14 del
  marco; si en un mismo minuto se tocan los dos, cuenta el stop; si no toca ninguno, sale al cierre de la 4.ª vela (tomador).
  El objetivo sale con orden límite (creador 0,02 %). Riesgo por apuesta = fracción del saldo que se pierde en el stop.
- Tamaños: 1, 2, 5, 10, 25, 50 y 100 % del saldo por apuesta. Tramos 2020-2023 (elegir) y 2024-2026 (comprobar).
Uso: python -I a6_reversion_corta.py RUTA_npy ETIQUETA > a6_reversion_corta_ETIQUETA.txt"""
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "consolidacion"))
import clases_vela as CV  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CORTE = 1704067200
H = 4
LARGO = {"impulso_bajista_vol", "fuerte_bajista"}
CORTO = {"impulso_alcista_vol", "fuerte_alcista"}
TAM = (0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1.00)


def agregar(t, o, h, l, c, v, seg):
    g = t - t % seg
    cortes = np.flatnonzero(np.diff(g)) + 1
    i0 = np.concatenate([[0], cortes])
    i1 = np.concatenate([cortes, [len(t)]])
    return g[i0], o[i0], np.maximum.reduceat(h, i0), np.minimum.reduceat(l, i0), c[i1 - 1], np.add.reduceat(v, i0), i0, i1


def senales(T, O, Hh, L, C, V):
    cl = CV.clasificar_serie(O.tolist(), Hh.tolist(), L.tolist(), C.tolist(), V.tolist())
    out, libre = [], 0
    for i in range(40, len(C) - H):
        if i < libre:
            continue
        lado = 1 if cl[i] in LARGO else -1 if cl[i] in CORTO else 0
        if lado:
            out.append((i, lado))
            libre = i + H  # una apuesta abierta a la vez por marco
    return out


def compuesto(rets, dias, f):
    """rets: lista de (t, r) con r = resultado por unidad apostada/arriesgada. Devuelve saldo final, caída máxima, ruina."""
    E, pico, cm, ruina = 1.0, 1.0, 0.0, None
    for t, r in rets:
        E *= max(1 + f * r, 0.0)
        pico = max(pico, E)
        cm = max(cm, 1 - E / pico if pico > 0 else 1)
        if E < 0.01:
            ruina = t
            break
    g = E ** (1 / dias) - 1 if E > 0 else -1.0
    return E, g, cm, ruina


def main():
    a = np.load(sys.argv[1])
    etq = sys.argv[2] if len(sys.argv) > 2 else "BTC"
    t1 = (a[:, 0] // 1000).astype("int64") if a[0, 0] > 1e11 else a[:, 0].astype("int64")
    o1, h1, l1, c1, v1 = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    print(f"A6 · {etq}: apuestas a la reversión tras velas fuertes. Elegir en 2020-23, comprobar en 2024-26.")
    for marco, seg in (("5m", 300), ("15m", 900), ("1h", 3600)):
        T, O, Hh, L, C, V, i0, i1 = agregar(t1, o1, h1, l1, c1, v1, seg)
        sen = senales(T, O, Hh, L, C, V)
        tr = np.array([max(Hh[k] - L[k], abs(Hh[k] - C[k - 1]), abs(L[k] - C[k - 1])) if k else Hh[k] - L[k] for k in range(len(C))])
        atr = np.convolve(tr, np.ones(14) / 14, mode="full")[:len(tr)]
        atr = np.concatenate([[atr[0]], atr[:-1]])  # ATR de las 14 velas anteriores
        print(f"\n== {marco}: {len(sen):,} apuestas posibles ({len(sen) / ((T[-1] - T[40]) / 86400):.1f} por día, una abierta a la vez) ==")
        for tramo, sel in (("2020-23", lambda tt: tt < CORTE), ("2024-26", lambda tt: tt >= CORTE)):
            ss = [(i, lado) for i, lado in sen if sel(T[i])]
            if not ss:
                continue
            dias = (T[ss[-1][0]] - T[ss[0][0]]) / 86400
            # (A) apuesta de dirección
            res = []
            for i, lado in ss:
                d = lado * (C[i + H] - C[i])
                res.append((T[i], 1 if d > 0 else -1 if d < 0 else 0))
            gan = sum(1 for _, r in res if r > 0)
            per = sum(1 for _, r in res if r < 0)
            acierto = gan / max(1, gan + per)
            print(f"  {tramo} · APUESTA DE DIRECCIÓN: {len(res):,} apuestas, acierto {acierto * 100:.2f} % (empates aparte)")
            for pago in (0.80, 0.85, 0.88, 0.92):
                ev = acierto * pago - (1 - acierto)
                kelly = max(0.0, (acierto * pago - (1 - acierto)) / pago)
                filas = []
                for f in TAM:
                    E, g, cm, ruina = compuesto([(t, pago if r > 0 else -1.0 if r < 0 else 0.0) for t, r in res], dias, f)
                    filas.append(f"{f * 100:.0f}%:{'RUINA' if ruina else f'{g * 100:+.2f}%/d c{cm * 100:.0f}%'}")
                print(f"     pago {pago * 100:.0f} %: valor esperado {ev * 100:+.2f} % por apuesta · Kelly {kelly * 100:.1f} % · " + " · ".join(filas))
            # (B) futuros con objetivo y stop simétricos
            for k in (0.5, 1.0):
                rs = []
                for i, lado in ss:
                    e = C[i]
                    dist = k * atr[i] / e
                    if dist <= 0:
                        continue
                    tp, sl = e * (1 + lado * dist), e * (1 - lado * dist)
                    a_, b_ = i1[i], i1[min(i + H, len(i1) - 1)]  # minutos de las 4 velas siguientes
                    hh, ll = h1[a_:b_], l1[a_:b_]
                    toca_sl = (ll <= sl) if lado > 0 else (hh >= sl)
                    toca_tp = (hh >= tp) if lado > 0 else (ll <= tp)
                    j_sl = np.argmax(toca_sl) if toca_sl.any() else 10 ** 9
                    j_tp = np.argmax(toca_tp) if toca_tp.any() else 10 ** 9
                    if j_sl == 10 ** 9 and j_tp == 10 ** 9:
                        px, sal = c1[b_ - 1], 0.05
                    elif j_sl <= j_tp:
                        px, sal = sl, 0.05
                    else:
                        px, sal = tp, 0.02
                    neto = lado * (px / e - 1) * 100 - 0.05 - sal
                    rs.append((T[i], neto / 100 / dist))
                R = np.array([r for _, r in rs])
                filas = []
                for f in TAM[:5]:
                    E, g, cm, ruina = compuesto(rs, dias, f)
                    filas.append(f"{f * 100:.0f}%:{'RUINA' if ruina else f'{g * 100:+.2f}%/d c{cm * 100:.0f}%'}")
                print(f"     FUTUROS objetivo/stop {k} ATR: {len(rs):,} ops, acierto {(R > 0).mean() * 100:.1f} %, R medio {R.mean():+.3f} · " + " · ".join(filas))


if __name__ == "__main__":
    main()
