"""Pronósticos de Claude y su puntuación: ¿la lectura vela por vela sabe algo, o es azar? (27/10/2026)

En cada ciclo Claude escribe, ANTES de ver el resultado, la probabilidad de que el precio esté más arriba dentro de
h velas de un marco. Después se puntúa con la regla de Brier y el logaritmo, frente a dos referencias que no saben nada:
decir siempre 50 %, y la frecuencia de subidas de esa misma muestra (la «climatología»). Si Claude no gana a las dos,
su lectura no aporta dirección, por bien escrita que esté.

Solo biblioteca estándar. Guarda en diario/pronosticos.jsonl (el diario no se sube a GitHub: es privado).
Uso:
  python -I consolidacion/pronosticos.py registrar --marco 15m --horizonte 4 --prob 0.58 --nota "por qué"
  python -I consolidacion/pronosticos.py puntuar            -> tabla por marco y horizonte, calibración y referencias
Marcos: 5m, 15m, 1h, 4h. La referencia del precio es el cierre de la última vela cerrada del marco al registrar."""
import argparse
import datetime as dt
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import velas_ciclo as vc  # noqa: E402

UTC = dt.timezone.utc
RUTA = os.path.join(os.environ.get("TRADER_DIARIO") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "diario"),
                    "pronosticos.jsonl")


def leer():
    if not os.path.exists(RUTA):
        return []
    with open(RUTA, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def registrar(marco, horizonte, prob, nota, fuente="auto"):
    if not 0.01 <= prob <= 0.99:
        raise SystemExit("La probabilidad va de 0,01 a 0,99 (0,50 = no sé).")
    v, src = vc.velas(marco, 5, fuente)
    base = v[-1]
    fila = {"t_registro": int(time.time()), "marco": marco, "horizonte": int(horizonte), "prob_sube": round(prob, 4),
            "base_t": base[0], "precio_base": base[4], "fuente": src, "nota": nota[:300]}
    os.makedirs(os.path.dirname(RUTA), exist_ok=True)
    with open(RUTA, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    vence = dt.datetime.fromtimestamp(base[0] + vc.SEG[marco] * (1 + int(horizonte)), UTC)
    print(f"Pronóstico registrado: {marco} a {horizonte} velas, P(sube) = {prob:.2f}, desde el cierre {base[4]:,.2f}; "
          f"se resuelve con la vela que cierra a las {vence:%H:%M} UTC.")


def resolver(filas, fuente="auto"):
    """Añade «sube» (1/0) a los pronósticos cuyo horizonte ya cerró. Una sola descarga por marco."""
    cache = {}
    for r in filas:
        fin = r["base_t"] + vc.SEG[r["marco"]] * (r["horizonte"] + 1)  # cierre de la vela h después de la base
        if fin > time.time():
            continue
        if r["marco"] not in cache:
            antiguedad = time.time() - min(x["base_t"] for x in filas if x["marco"] == r["marco"])
            n = int(antiguedad // vc.SEG[r["marco"]]) + 5
            cache[r["marco"]] = {x[0]: x[4] for x in vc.velas(r["marco"], min(n, 1400), fuente)[0]}
        cierres = cache[r["marco"]]
        t_obj = r["base_t"] + vc.SEG[r["marco"]] * r["horizonte"]
        if t_obj in cierres:
            r["sube"] = int(cierres[t_obj] > r["precio_base"])
    return [r for r in filas if "sube" in r]


def puntuar(fuente="auto"):
    res = resolver(leer(), fuente)
    if not res:
        print("Todavía no hay pronósticos resueltos.")
        return
    print(f"PUNTUACIÓN de {len(res)} pronósticos resueltos (Brier: 0 perfecto, 0,25 = decir siempre 50 %; menos es mejor)")
    grupos = {}
    for r in res:
        grupos.setdefault((r["marco"], r["horizonte"]), []).append(r)
    grupos[("TODOS", 0)] = res
    for (m, h), g in sorted(grupos.items(), key=lambda kv: (kv[0][0] == "TODOS", kv[0])):
        n = len(g)
        y = [r["sube"] for r in g]
        p = [r["prob_sube"] for r in g]
        base = sum(y) / n
        brier = sum((pi - yi) ** 2 for pi, yi in zip(p, y)) / n
        clim = sum((base - yi) ** 2 for yi in y) / n
        logl = -sum(yi * math.log(pi) + (1 - yi) * math.log(1 - pi) for pi, yi in zip(p, y)) / n
        acierto = sum((pi > 0.5) == bool(yi) for pi, yi in zip(p, y) if pi != 0.5) / max(1, sum(pi != 0.5 for pi in p))
        habil = 1 - brier / 0.25
        etiqueta = "todos" if m == "TODOS" else f"{m} a {h} velas"
        print(f"  {etiqueta:<16} n={n:>4} · Brier {brier:.4f} (50 %: 0,2500 · climatología {clim:.4f}) · log {logl:.4f} "
              f"(50 %: 0,6931) · acierto de dirección {acierto * 100:.1f} % · habilidad frente a 50 % {habil * 100:+.1f} % · "
              f"subió el {base * 100:.0f} %")
    print("  Calibración (todos): P(sube) dicha → frecuencia real")
    for lo, hi in ((0.0, 0.4), (0.4, 0.47), (0.47, 0.53), (0.53, 0.6), (0.6, 1.01)):
        g = [r for r in res if lo <= r["prob_sube"] < hi]
        if g:
            print(f"    {lo:.2f}-{min(hi, 1):.2f}: {len(g):>4} pronósticos · media dicha {sum(r['prob_sube'] for r in g) / len(g):.2f} · "
                  f"subió {sum(r['sube'] for r in g) / len(g) * 100:.0f} %")
    if len(res) < 100:
        print(f"  OJO: con {len(res)} pronósticos la diferencia con el azar no es fiable; hacen falta cientos.")


def main():
    if hasattr(sys.stdout, "reconfigure"):  # Windows: con la salida por tubería usa cp1252, sin «−», «≥» ni flechas
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Pronósticos de Claude y su puntuación frente al azar.")
    ap.add_argument("accion", choices=("registrar", "puntuar"))
    ap.add_argument("--marco", choices=("5m", "15m", "1h", "4h"))
    ap.add_argument("--horizonte", type=int)
    ap.add_argument("--prob", type=float)
    ap.add_argument("--nota", default="")
    ap.add_argument("--fuente", choices=("auto", "binance", "coinbase"), default="auto")
    a = ap.parse_args()
    if a.accion == "registrar":
        if not (a.marco and a.horizonte and a.prob is not None):
            raise SystemExit("Faltan --marco, --horizonte y --prob.")
        registrar(a.marco, a.horizonte, a.prob, a.nota, a.fuente)
    else:
        puntuar(a.fuente)


if __name__ == "__main__":
    main()
