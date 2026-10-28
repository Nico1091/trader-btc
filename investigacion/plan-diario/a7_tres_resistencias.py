"""A7 (28/10/2026): ingeniería inversa de la regla de Nicolás: «si hay por lo menos 3 resistencias, sé que cae: apuesto a la caída».

Su regla, convertida en algo medible y fijada ANTES de mirar resultados:
- Pivote alto: vela cuyo máximo es el mayor de las 2 anteriores y las 2 siguientes (se confirma 2 velas después: sin mirar el futuro).
- RESISTENCIA: el pivote alto más reciente de las últimas 60 velas y al menos otro pivote alto a menos de 0,25 ATR14 de él
  (2 toques previos), sin ningún cierre por encima de la zona + 0,25 ATR desde el primer toque.
- TERCER TOQUE: la vela actual llega a la zona (máximo ≥ zona − 0,25 ATR), no la rompe (máximo ≤ zona + 0,25 ATR) y cierra
  por debajo (cierre < zona − 0,25 ATR): CORTO al cierre. Al revés con soportes (3 toques abajo): LARGO.
- Una apuesta abierta a la vez por marco. Marcos: 5 m, 15 m y 1 h.
- (A) Apuesta de dirección: gana si el cierre 2, 4 u 8 velas después está a favor; pagos de 80, 85, 88 y 92 %.
- (B) Futuros de Binance como lo haría un trader: stop 0,25 ATR por encima de la zona (debajo del soporte), objetivo a 1,5 veces
  la distancia del stop, máximo 8 velas; entrada tomador 0,05 %, objetivo creador 0,02 %, stop y tiempo tomador 0,05 %;
  si en el mismo minuto se tocan los dos, cuenta el stop.
- Tamaños de 1 a 100 % del saldo. Elegir en 2020-2023 y comprobar en 2024-2026.
Uso: python -I a7_tres_resistencias.py RUTA_npy ETIQUETA > a7_tres_resistencias_ETIQUETA.txt"""
import bisect
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a6_reversion_corta import agregar, compuesto, CORTE, TAM  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VENTANA, TOL, K = 60, 0.25, 2


def pivotes(x, alto):
    n = len(x)
    out = []
    for i in range(K, n - K):
        w = x[i - K:i + K + 1]
        if (alto and x[i] == w.max() and x[i] > x[i - 1]) or (not alto and x[i] == w.min() and x[i] < x[i - 1]):
            out.append(i)
    return out


def senales(T, Hh, L, C, atr):
    ph, pl = pivotes(Hh, True), pivotes(L, False)
    out, libre = [], 0
    for i in range(VENTANA + 5, len(C) - 9):
        if i < libre:
            continue
        tol = TOL * atr[i]
        if tol <= 0:
            continue
        for alto, piv, ext in ((True, ph, Hh), (False, pl, L)):
            a = bisect.bisect_left(piv, i - VENTANA)
            b = bisect.bisect_right(piv, i - K - 1)  # pivotes ya confirmados
            rec = piv[a:b]
            if len(rec) < 2:
                continue
            j1 = rec[-1]
            grupo = [j for j in rec if abs(ext[j] - ext[j1]) <= tol]
            if len(grupo) < 2:
                continue
            if alto:
                zona = max(ext[j] for j in grupo)
                limpia = C[min(grupo):i].max() <= zona + tol
                toca = Hh[i] >= zona - tol and Hh[i] <= zona + tol and C[i] < zona - tol
            else:
                zona = min(ext[j] for j in grupo)
                limpia = C[min(grupo):i].min() >= zona - tol
                toca = L[i] <= zona + tol and L[i] >= zona - tol and C[i] > zona + tol
            if limpia and toca:
                out.append((i, -1 if alto else 1, zona, tol))
                libre = i + 8
                break
    return out


def main():
    a = np.load(sys.argv[1])
    etq = sys.argv[2] if len(sys.argv) > 2 else "BTC"
    t1 = (a[:, 0] // 1000).astype("int64") if a[0, 0] > 1e11 else a[:, 0].astype("int64")
    o1, h1, l1, c1, v1 = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    print(f"A7 · {etq}: regla de las 3 resistencias / 3 soportes de Nicolás. Elegir en 2020-23, comprobar en 2024-26.")
    for marco, seg in (("5m", 300), ("15m", 900), ("1h", 3600)):
        T, O, Hh, L, C, V, i0, i1 = agregar(t1, o1, h1, l1, c1, v1, seg)
        tr = np.maximum(Hh - L, np.maximum(np.abs(Hh - np.roll(C, 1)), np.abs(L - np.roll(C, 1))))
        atr = np.concatenate([[tr[0]], np.convolve(tr, np.ones(14) / 14, mode="full")[:len(tr) - 1]])
        sen = senales(T, Hh, L, C, atr)
        dias_tot = (T[-1] - T[0]) / 86400
        print(f"\n== {marco}: {len(sen):,} señales ({len(sen) / dias_tot:.1f} por día; cortos en resistencia "
              f"{sum(1 for s in sen if s[1] < 0):,}, largos en soporte {sum(1 for s in sen if s[1] > 0):,}) ==")
        for tramo, sel in (("2020-23", lambda tt: tt < CORTE), ("2024-26", lambda tt: tt >= CORTE)):
            ss = [s for s in sen if sel(T[s[0]])]
            if not ss:
                continue
            dias = (T[ss[-1][0]] - T[ss[0][0]]) / 86400
            for h in (2, 4, 8):
                res = []
                for i, lado, _, _ in ss:
                    d = lado * (C[i + h] - C[i])
                    res.append((T[i], 1 if d > 0 else -1 if d < 0 else 0))
                g_, p_ = sum(1 for _, r in res if r > 0), sum(1 for _, r in res if r < 0)
                ac = g_ / max(1, g_ + p_)
                cort = [r for (t, r), s in zip(res, ss) if s[1] < 0]
                larg = [r for (t, r), s in zip(res, ss) if s[1] > 0]
                ac_c = sum(1 for r in cort if r > 0) / max(1, sum(1 for r in cort if r != 0))
                ac_l = sum(1 for r in larg if r > 0) / max(1, sum(1 for r in larg if r != 0))
                filas = []
                for pago in (0.80, 0.85, 0.88, 0.92):
                    ev = ac * pago - (1 - ac)
                    mejor = max(((f, compuesto([(t, pago if r > 0 else -1.0 if r < 0 else 0.0) for t, r in res], dias, f)) for f in TAM),
                                key=lambda x: x[1][1])
                    f, (E, g, cm, ruina) = mejor
                    filas.append(f"pago {pago * 100:.0f}: EV {ev * 100:+.1f} %, mejor tamaño {f * 100:.0f} % -> "
                                 f"{'RUINA' if ruina else f'{g * 100:+.2f} %/día, caída {cm * 100:.0f} %'}")
                print(f"  {tramo} · apuesta a {h} velas: {len(res):,} apuestas, acierto {ac * 100:.1f} % (cortos {ac_c * 100:.1f} %, "
                      f"largos {ac_l * 100:.1f} %)")
                for x in filas:
                    print("       " + x)
            rs = []
            for i, lado, zona, tol in ss:
                e = C[i]
                sl = zona + tol if lado < 0 else zona - tol
                dist = abs(sl - e) / e
                if dist <= 0:
                    continue
                tp = e * (1 + lado * 1.5 * dist)
                a_, b_ = i1[i], i1[min(i + 8, len(i1) - 1)]
                hh, ll = h1[a_:b_], l1[a_:b_]
                toca_sl = (hh >= sl) if lado < 0 else (ll <= sl)
                toca_tp = (ll <= tp) if lado < 0 else (hh >= tp)
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
            print(f"  {tramo} · FUTUROS (stop tras la zona, objetivo 1,5×): {len(rs):,} ops, acierto {(R > 0).mean() * 100:.1f} %, "
                  f"R medio {R.mean():+.3f} · " + " · ".join(filas))


if __name__ == "__main__":
    main()
