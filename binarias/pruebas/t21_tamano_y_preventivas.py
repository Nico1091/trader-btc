"""T21 (29/10/2026): tamaño de la apuesta, preventivas y procedimiento por historial, todo a ciegas.

Nicolás (29/10, 21:50): «apueste el porcentaje que crea y lo que crea, sin stop loss o los que usted crea y diga».
Insumo: las apuestas a ciegas de T18 (reglas en BTC y ETH) y T19 (modelo a 10, 30 y 60 min en BTC y ETH).
Reglas fijadas antes de mirar:
- Procedimiento por historial: cada mes M se opera el procedimiento con mayor límite de Wilson (95 %) de su acierto a ciegas en los
  12 meses anteriores, si supera 54,1 %. Dos versiones: entre las 2 reglas (lo que hoy corre en vivo) y entre los 8.
- Tamaños: 16 %; siempre el mínimo (5 USDT); medio Kelly y Kelly entero con el acierto a ciegas de los 6 meses anteriores del
  procedimiento operado (si no supera 54,1 %, ese mes no se apuesta). Siempre al menos 5 USDT; quiebra si no los cubre.
- Preventivas: ninguna; parar el día tras 3 fallos seguidos; parar el día al perder 3 apuestas netas. Se elige con 2022-23 y se
  verifica con 2024-26: solo se adopta si mejora la mediana y baja la quiebra en los dos tramos.
- Medida: 100.000 COP arrancando cada día, a 30, 90 y 365 días. Pago 0,85; empate = fallo.
Uso: python -I t21_tamano_y_preventivas.py"""
import bisect
import ctypes
import datetime as dt
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
from motor import historial as H  # noqa: E402
PAGO, MINIMO, CAP = 0.85, 5 * 3180.0, 100000.0
EQ = 1 / (1 + PAGO)


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def meses(desde, hasta):
    y, m = desde
    while (y, m) <= hasta:
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def por_historial(P, S, procs):
    """Cada mes, el procedimiento de mayor límite de Wilson en los 12 meses anteriores (motor/historial.elegir)."""
    elegido, apuestas = {}, []
    for mes in meses((2022, 1), (2026, 10)):
        mejor = H.elegir(S, mes, procs)
        elegido[mes] = mejor[0] if mejor else None
        if mejor:
            apuestas += [(d, mes, r, mejor[0]) for d, me, r in P[mejor[0]] if me == mes]
    apuestas.sort(key=lambda x: x[0])
    return apuestas, elegido


def simular(ap, S, regla, prev, dias):
    """ap: [(día, mes, acierto, proc)]. Devuelve los saldos finales de cada arranque diario."""
    ds = [a[0] for a in ap]
    out = []
    cache_f = {}
    for d0 in range(ds[0], ds[-1] - dias + 2):
        i0, i1 = bisect.bisect_left(ds, d0), bisect.bisect_left(ds, d0 + dias)
        s, dia, seg, neto, parado = CAP, None, 0, 0, False
        for d, mes, r, pr in ap[i0:i1]:
            if s < MINIMO:
                s = 0.0
                break
            if d != dia:
                dia, seg, neto, parado = d, 0, 0, False
            if parado:
                continue
            if regla == "16 %":
                m = max(0.16 * s, MINIMO)
            elif regla == "mínimo fijo":
                m = MINIMO
            else:
                clave = (pr, mes)
                if clave not in cache_f:
                    cache_f[clave] = H.fraccion(S, pr, mes, 0.5 if regla == "medio Kelly" else 1.0)
                f = cache_f[clave]
                if f <= 0:
                    continue
                m = max(f * s, MINIMO)
            s += m * PAGO if r else -m
            seg = 0 if r else seg + 1
            neto += 1 if r else -1
            if (prev == "3 fallos seguidos" and seg >= 3) or (prev == "-3 netas" and neto <= -3):
                parado = True
        out.append(s)
    return out


def medida(saldos):
    s = sorted(saldos)
    if not s:
        return None
    return {"arriba": sum(1 for x in s if x > CAP) / len(s), "quiebra": sum(1 for x in s if x < MINIMO) / len(s), "mediana": s[len(s) // 2],
            "p10": s[len(s) // 10], "p90": s[9 * len(s) // 10], "n": len(s)}


def txt(m):
    return (f"arriba {es(100 * m['arriba'])} % · quiebra {es(100 * m['quiebra'])} % · mediana {es(m['mediana'], 0)} · "
            f"peor 10 % {es(m['p10'], 0)} · mejor 10 % {es(m['p90'], 0)}") if m else "sin datos"


def main():
    P = H.cargar()
    S = H.stats_mes(P)
    lineas = []
    p = lambda x="": (lineas.append(x), print(x, flush=True))
    p("T21 · TAMAÑO, PREVENTIVAS Y PROCEDIMIENTO POR HISTORIAL · todo a ciegas · pago 0,85 · desde 100.000 COP · mínimo 5 USDT\n")
    reglas2 = [k for k in P if k.startswith("reglas")]
    todos8 = list(P)
    fuentes = {"reglas BTC fijo (lo que corre hoy)": [(d, me, r, "reglas BTC") for d, me, r in P["reglas BTC"] if me >= "2022-01"]}
    for nom, procs in (("por historial entre las 2 reglas", reglas2), ("por historial entre los 8", todos8)):
        ap, eleg = por_historial(P, S, procs)
        fuentes[nom] = ap
        cuenta = {}
        for v in eleg.values():
            cuenta[v] = cuenta.get(v, 0) + 1
        p(f"{nom}: meses elegidos por procedimiento " + ", ".join(f"{k or 'ninguno'} {v}" for k, v in sorted(cuenta.items(), key=lambda x: -x[1])))
        p(f"   elegido para 2026-10: {eleg.get('2026-10')} · para 2026-11 se elegiría con 2025-11 a 2026-10")
    p()
    for nom, ap in fuentes.items():
        for y0, y1 in (("2022", "2023"), ("2024", "2026")):
            sub = [a for a in ap if y0 <= a[1][:4] <= y1]
            n = len(sub)
            w = sum(1 for a in sub if a[2])
            p(f"{nom} · {y0}-{y1[2:]}: {es(n, 0)} apuestas, {es(100 * w / n) if n else '-'} % de acierto")
        sub = [a for a in ap if a[1][:4] == "2026"]
        p(f"{nom} · 2026: {es(len(sub), 0)} apuestas, {es(100 * sum(1 for a in sub if a[2]) / max(1, len(sub)))} %")
    reglas_t = ("16 %", "mínimo fijo", "medio Kelly", "Kelly entero")
    for dias in (30, 90, 365):
        p(f"\n== {dias} DÍAS desde 100.000 COP, arrancando cada día de 2022 a 2026 ==")
        for nom, ap in fuentes.items():
            for rg in reglas_t:
                p(f"{nom} · {rg}: {txt(medida(simular(ap, S, rg, 'ninguna', dias)))}")
    p("\n== PREVENTIVAS (30 días, medio Kelly): se eligen con 2022-23 y se verifican con 2024-26 ==")
    for nom, ap in fuentes.items():
        for prev in ("ninguna", "3 fallos seguidos", "-3 netas"):
            r = []
            for y0, y1 in (("2022", "2023"), ("2024", "2026")):
                sub = [a for a in ap if y0 <= a[1][:4] <= y1]
                r.append(f"{y0}-{y1[2:]}: {txt(medida(simular(sub, S, 'medio Kelly', prev, 30)))}")
            p(f"{nom} · {prev}\n      " + "\n      ".join(r))
    p("\n== FRACCIÓN DE MEDIO KELLY QUE SE USARÍA EN NOVIEMBRE DE 2026 (acierto a ciegas de mayo a octubre) ==")
    for pr in P:
        w, n = H.ventana(S, pr, "2026-11", 6)
        f = H.fraccion(S, pr, "2026-11", 0.5)
        p(f"{pr}: {w}/{n} = {es(100 * w / max(1, n))} % → medio Kelly {es(100 * f, 2)} % del saldo · saldo para que supere 5 USDT: "
          f"{es(MINIMO / f, 0) if f > 0 else 'no se apuesta'} COP")
    open(os.path.join(AQUI, "t21_tamano_y_preventivas.txt"), "w", encoding="utf-8").write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    main()
