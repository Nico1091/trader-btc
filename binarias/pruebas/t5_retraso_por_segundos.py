"""T5 (29/10/2026): ¿con cuántos segundos de retraso sigue ganando cada señal binaria, y con qué plazo de Binance?

Motivo: T4 mostró que con un minuto de retraso se pierde casi toda la ventaja, y Binance (Contratos de Evento) solo ofrece
plazos de 10 min, 30 min, 1 h y 1 día, sin acceso por API: en real habría que apostar a mano desde la app.
Datos: velas de 1 s de BTCUSDT contado de Binance, 01/05/2026 a 19/10/2026, sin huecos (datos/cache/contado-1s-BTCUSDT).
Contexto diario (para REV15 CTX): cierres diarios de futuros BTCUSDT (datos/um).

Reglas fijadas antes de mirar:
- Velas de 5 y 15 min armadas desde las de 1 s. Señales con las mismas definiciones de T3 y T4:
  C3R tres cuervos AL REVÉS (sube), S3R tres soldados AL REVÉS (baja), REV5 y REV15 (cuerpo ≥ 2 × media de 100 → en contra),
  REV15 CTX (REV15 solo a favor del contexto diario).
- Entrada al precio del segundo «cierre + retraso» (retraso 0, 1, 3, 5, 10, 20, 30 o 60 s); vence en 5, 10, 15 o 30 min
  contados desde la entrada. Empate = se devuelve. Acierto ± margen de error al 95 %.
Uso: python -I t5_retraso_por_segundos.py > t5_retraso_por_segundos.txt"""
import os
import re
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SEG = r"C:\Users\ni109\Ingresos\trader-btc\datos\cache\contado-1s-BTCUSDT."
UM = r"C:\Users\ni109\Ingresos\trader-btc\datos\um\BTCUSDT_um_1m.npy"
RETRASOS = (0, 1, 3, 5, 10, 20, 30, 60)
PLAZOS = (5, 10, 15, 30)


def es(s):
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "§", s)
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", s)
    return s.replace("§", ".")


def p(s=""):
    print(es(s))


def media_previa(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    m = np.full(len(x), np.nan)
    m[n:] = (cs[n:-1] - cs[:-n - 1]) / n
    return m


def atras(x, k):
    y = np.full(len(x), np.nan)
    y[k:] = x[:-k]
    return y


def velas(t, o, h, l, c, seg):
    i0 = int(np.argmax(t % seg == 0))
    n = (len(t) - i0) // seg * seg
    return (t[i0:i0 + n].reshape(-1, seg)[:, 0], o[i0:i0 + n].reshape(-1, seg)[:, 0], h[i0:i0 + n].reshape(-1, seg).max(1),
            l[i0:i0 + n].reshape(-1, seg).min(1), c[i0:i0 + n].reshape(-1, seg)[:, -1])


def contexto():
    x = np.load(UM, mmap_mode="r")
    t = (x[:, 0] // 1000).astype(np.int64)
    c = np.asarray(x[:, 4])
    dia = t // 86400
    ult = np.r_[np.flatnonzero(np.diff(dia)), len(dia) - 1]
    d, cd = dia[ult], c[ult]
    cs = np.concatenate([[0.0], np.cumsum(cd)])
    sma = np.full(len(cd), np.nan)
    sma[50:] = (cs[50:-1] - cs[:-51]) / 50
    ctx = np.zeros(len(cd))
    ctx[1:] = np.sign(cd[:-1] - sma[1:])
    return dict(zip(d.tolist(), np.nan_to_num(ctx).tolist()))


def main():
    t = (np.fromfile(SEG + "t.bin", dtype="<i8") // 1000).astype(np.int64)
    o, h, l, c = (np.fromfile(SEG + k + ".bin", dtype="<f8") for k in ("o", "h", "l", "c"))
    t0 = int(t[0])
    assert np.all(np.diff(t[:1000]) == 1)
    precio = lambda ts: c[np.clip(ts - t0 - 1, 0, len(c) - 1)]  # noqa: E731  precio en el segundo ts = cierre del segundo anterior
    ctxd = contexto()
    senales = {}
    for seg, nom in ((300, "5"), (900, "15")):
        T, O, H, L, C = velas(t, o, h, l, c, seg)
        cuerpo, rango = np.abs(C - O), H - L
        fuerte = cuerpo >= 2 * media_previa(cuerpo, 100)
        d_rev = np.where(fuerte, -np.sign(C - O), 0)
        senales[f"REV{nom}"] = (T + seg, d_rev)
        if nom == "15":
            ctx = np.array([ctxd.get(int(x) // 86400, 0.0) for x in T])
            senales["REV15 CTX"] = (T + seg, np.where(d_rev == ctx, d_rev, 0))
        if nom == "5":
            alc, baj = C > O, C < O
            fa, fb = alc & (cuerpo >= 0.5 * rango), baj & (cuerpo >= 0.5 * rango)
            c1, c2, c3, c13 = atras(C, 1), atras(C, 2), atras(C, 3), atras(C, 13)
            with np.errstate(invalid="ignore", divide="ignore"):
                t3 = (c3 - c13) / c13
            cuervos = (t3 > 0) & fb & np.r_[False, fb[:-1]] & np.r_[False, False, fb[:-2]] & (C < c1) & (c1 < c2)
            soldados = (t3 < 0) & fa & np.r_[False, fa[:-1]] & np.r_[False, False, fa[:-2]] & (C > c1) & (c1 > c2)
            senales["C3R"] = (T + seg, np.where(cuervos, 1, 0))
            senales["S3R"] = (T + seg, np.where(soldados, -1, 0))
    p(f"T5 · RETRASO EN SEGUNDOS · BTCUSDT contado, velas de 1 s del 01/05 al 19/10/2026 ({len(t):,} segundos)")
    p("acierto sin contar empates ± margen al 95 % · para no perder: 55.6 % con pago 0,80 · 54.1 % con 0,85 · 52.6 % con 0,90")
    p("plazos de Binance: 10 y 30 min (no hay 5 ni 15)\n")
    for nom in ("REV15 CTX", "REV15", "REV5", "C3R", "S3R"):
        tc, d = senales[nom]
        j = np.flatnonzero(d != 0)
        tc, d = tc[j], d[j]
        ok = tc + 60 + max(PLAZOS) * 60 < t[-1]
        tc, d = tc[ok], d[ok]
        p(f"== {nom}: {len(tc)} señales ({len(tc) / 172:.1f} al día) ==")
        p("   plazo  " + "".join(f"{f'{r} s':>17s}" for r in RETRASOS))
        for pl in PLAZOS:
            fila = f"   {pl:2d} min "
            for r in RETRASOS:
                pe = precio(tc + r)
                px = precio(tc + r + pl * 60)
                res = np.sign(d * (px - pe))
                w, ll = int((res > 0).sum()), int((res < 0).sum())
                q = w / (w + ll) if w + ll else float("nan")
                me = 1.96 * np.sqrt(q * (1 - q) / (w + ll)) if w + ll else float("nan")
                fila += f"{q * 100:9.1f} ± {me * 100:4.1f}"
            p(fila)
        p()


if __name__ == "__main__":
    main()
