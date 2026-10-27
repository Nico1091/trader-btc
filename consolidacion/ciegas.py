"""Entrenamiento a ciegas: ¿la lectura de velas de Claude gana cuando no sabe ni la fecha ni el precio? (27/10/2026)

1. «mostrar» elige un momento al azar de los últimos 12 meses que nunca se usó y enseña SOLO lo anterior a él:
   48 velas de 1 h, 16 de 15 m y 30 de 1 m, en % frente al último cierre, sin fecha ni precio. El momento queda
   guardado en diario/ciegas.jsonl, ofuscado: no lo abras.
2. «decidir» guarda tu decisión ANTES de ver el resultado: largo, corto o nada, stop y objetivo en %, horas (máx. 6)
   y tu probabilidad de que suba en ese tiempo.
3. «revelar» recorre las velas de 1 m posteriores: entra a mercado en la apertura del minuto del momento, sale por stop,
   objetivo (si en un mismo minuto se tocan los dos, cuenta el stop) o tiempo, con 0,05 % de comisión por lado.
   Mide además un testigo con la misma gestión y lado al azar.
4. «marcador»: tu total frente al testigo y la puntuación de Brier de tus probabilidades.

Uso:
  python -I consolidacion/ciegas.py mostrar
  python -I consolidacion/ciegas.py decidir --id 7 --lado largo --stop 0.8 --objetivo 1.6 --horas 6 --prob 0.58 --nota "..."
  python -I consolidacion/ciegas.py revelar --id 7
  python -I consolidacion/ciegas.py marcador"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import velas_ciclo as vc  # noqa: E402

RUTA = os.path.join(os.environ.get("TRADER_DIARIO") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "diario"),
                    "ciegas.jsonl")
CLAVE = 0x5A17C3E9
COM = 0.05


def leer():
    if not os.path.exists(RUTA):
        return []
    with open(RUTA, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def guardar(filas):
    os.makedirs(os.path.dirname(RUTA), exist_ok=True)
    tmp = RUTA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in filas:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, RUTA)


def momento(r):
    return r["oculto"] ^ CLAVE


def mostrar(fuente):
    filas = leer()
    usados = {momento(r) // 3600 for r in filas}
    rng = random.SystemRandom()
    ahora = int(time.time()) // 60 * 60
    while True:
        t = ahora - rng.randrange(2 * 86400, 365 * 86400) // 60 * 60
        if t // 3600 not in usados:
            break
    h1, src = vc.rango("1h", t - 48 * 3600 - (t % 3600), t - (t % 3600), fuente)
    m15, _ = vc.rango("15m", t - 16 * 900 - (t % 900), t - (t % 900), fuente)
    m1, _ = vc.rango("1m", t - 30 * 60, t, fuente)
    if len(h1) < 40 or len(m15) < 12 or len(m1) < 25:
        raise SystemExit("Faltan velas en ese momento; vuelve a pedir otro.")
    ref = m1[-1][4]
    nid = max([r["id"] for r in filas], default=0) + 1
    filas.append({"id": nid, "oculto": t ^ CLAVE, "fuente": src})
    guardar(filas)
    print(f"CIEGA #{nid} · todo en % frente al último cierre (= 0,00); sin fecha ni precio. Decide antes de revelar.")
    for nombre, v in (("1 h (48)", h1), ("15 m (16)", m15), ("1 m (30)", m1)):
        vm = sum(x[5] for x in v) / len(v)
        print(f"--- {nombre}: apertura / máximo / mínimo / cierre en %, volumen frente a la media de estas velas ---")
        for x in v:
            print(f"  {(x[1] / ref - 1) * 100:+7.2f} {(x[2] / ref - 1) * 100:+7.2f} {(x[3] / ref - 1) * 100:+7.2f} "
                  f"{(x[4] / ref - 1) * 100:+7.2f}   vol ×{x[5] / vm:4.2f}")


def decidir(i, lado, stop, objetivo, horas, prob, nota):
    filas = leer()
    r = next((x for x in filas if x["id"] == i), None)
    if r is None:
        raise SystemExit("No existe esa ciega.")
    if "resultado" in r:
        raise SystemExit("Esa ciega ya se reveló: no se puede decidir después de ver el resultado.")
    if not 0 < horas <= 6 or not 0.01 <= prob <= 0.99:
        raise SystemExit("Horas de 0 a 6 y probabilidad de 0,01 a 0,99.")
    r["decision"] = {"lado": lado, "stop": stop, "objetivo": objetivo, "horas": horas, "prob_sube": prob, "nota": nota[:300],
                     "t": int(time.time())}
    guardar(filas)
    print(f"Decisión de la ciega #{i} guardada: {lado}, stop {stop} %, objetivo {objetivo} %, {horas} h, P(sube) {prob}.")


def recorrer(v, lado, stop, objetivo):
    pe = v[0][1]
    s = 1 if lado == "largo" else -1
    sl, tp = pe * (1 - s * stop / 100), pe * (1 + s * objetivo / 100)
    for x in v:
        toca_sl = x[3] <= sl if s > 0 else x[2] >= sl
        toca_tp = x[2] >= tp if s > 0 else x[3] <= tp
        if toca_sl:
            return s * (sl / pe - 1) * 100 - 2 * COM, "stop"
        if toca_tp:
            return s * (tp / pe - 1) * 100 - 2 * COM, "objetivo"
    return s * (v[-1][4] / pe - 1) * 100 - 2 * COM, "tiempo"


def revelar(i, fuente):
    filas = leer()
    r = next((x for x in filas if x["id"] == i), None)
    if r is None or "decision" not in r:
        raise SystemExit("Primero «decidir»: sin decisión escrita no se revela.")
    d, t = r["decision"], momento(r)
    v, _ = vc.rango("1m", t, t + int(d["horas"] * 3600), fuente)
    sube = int(v[-1][4] > v[0][1])
    res = {"sube": sube, "movimiento_pct": (v[-1][4] / v[0][1] - 1) * 100}
    if d["lado"] in ("largo", "corto"):
        res["neto"], res["motivo"] = recorrer(v, d["lado"], d["stop"], d["objetivo"])
        lado_azar = random.Random(t).choice(["largo", "corto"])
        res["azar"], _ = recorrer(v, lado_azar, d["stop"], d["objetivo"])
    r["resultado"] = res
    guardar(filas)
    import datetime as dt
    print(f"CIEGA #{i}: era el {dt.datetime.fromtimestamp(t, dt.timezone.utc):%Y-%m-%d %H:%M} UTC. En {d['horas']} h el precio "
          f"{'subió' if sube else 'bajó'} {res['movimiento_pct']:+.2f} %.")
    if "neto" in res:
        print(f"  Tu {d['lado']}: {res['neto']:+.3f} % neto ({res['motivo']}) · testigo al azar con la misma gestión: {res['azar']:+.3f} %")
    else:
        print("  No operaste: cuenta solo tu probabilidad.")


def marcador():
    filas = [r for r in leer() if "resultado" in r]
    if not filas:
        print("Sin ciegas reveladas todavía.")
        return
    ops = [r for r in filas if "neto" in r["resultado"]]
    brier = sum((r["decision"]["prob_sube"] - r["resultado"]["sube"]) ** 2 for r in filas) / len(filas)
    print(f"MARCADOR A CIEGAS: {len(filas)} reveladas · operadas {len(ops)} · neto total {sum(r['resultado']['neto'] for r in ops):+.2f} % "
          f"(media {sum(r['resultado']['neto'] for r in ops) / max(1, len(ops)):+.3f} %) · testigo al azar "
          f"{sum(r['resultado']['azar'] for r in ops):+.2f} % · aciertos {sum(r['resultado']['neto'] > 0 for r in ops)}/{len(ops)}")
    print(f"  Brier de tus probabilidades {brier:.4f} (decir 50 % siempre: 0,2500; menos es mejor)")
    if len(filas) < 100:
        print(f"  OJO: {len(filas)} ciegas no bastan para afirmar nada; hacen falta cientos.")


def main():
    if hasattr(sys.stdout, "reconfigure"):  # Windows: con la salida por tubería usa cp1252, sin «−», «≥» ni flechas
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Entrenamiento a ciegas de la lectura de velas.")
    ap.add_argument("accion", choices=("mostrar", "decidir", "revelar", "marcador"))
    ap.add_argument("--id", type=int)
    ap.add_argument("--lado", choices=("largo", "corto", "nada"))
    ap.add_argument("--stop", type=float, default=0.8)
    ap.add_argument("--objetivo", type=float, default=1.6)
    ap.add_argument("--horas", type=float, default=6)
    ap.add_argument("--prob", type=float, default=0.5)
    ap.add_argument("--nota", default="")
    ap.add_argument("--fuente", choices=("auto", "binance", "coinbase"), default="auto")
    a = ap.parse_args()
    if a.accion == "mostrar":
        mostrar(a.fuente)
    elif a.accion == "decidir":
        decidir(a.id, a.lado, a.stop, a.objetivo, a.horas, a.prob, a.nota)
    elif a.accion == "revelar":
        revelar(a.id, a.fuente)
    else:
        marcador()


if __name__ == "__main__":
    main()
