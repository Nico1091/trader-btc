"""T8 (29/10/2026): PRUEBA DIRECTA de los planes que ganaron antes, repetidos tal cual, con su margen operativo.

Pedido de Nicolás: «revisa esas operaciones en las que sí te dio ganancia y ahí es donde debes operar… opere tal cual como las
operaciones anteriores para ver qué margen te deja con esa misma operación… le metimos inversa… ahí están los mejores planes
inscritos… esas pruebas directas, con esas operaciones».
Mismas reglas que T7 (4 binarias al día, una por franja de 6 h, una abierta a la vez, 2 % del saldo desde 150.000 COP, empate
= se devuelve), sin optimizar nada: cada plan con la configuración con que quedó escrito.
  Plan del 28/10 (PROMPT BINARIAS BTC - RETOMAR): tres cuervos AL REVÉS 5 min (principal), tres soldados AL REVÉS 5 min,
  martillo invertido 10 min, y los tres juntos.
  Plan de hoy: REV15 a favor del contexto, 10 min (el del bot en papel).
  T95H: P05c a 15 min (55,6 % en la sesión del 28/10).
  Las cuatro que en T7 ganaron antes y también en el mes, con su configuración de T7, solas y juntas.
Periodos: 2024-01-01 a 2026-09-28 (antes) y 29/09-28/10/2026 (el mes). Pago 0,85; resultado también con 0,80.
Uso: python -I t8_prueba_directa.py > t8_prueba_directa.txt"""
import importlib.util
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
_e = importlib.util.spec_from_file_location("t7", os.path.join(AQUI, "t7_mes_operado.py"))
t7 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t7)
p = t7.p

PLANES = {
    "Plan 28/10 · tres cuervos al revés 5 min": [("tres cuervos AL REVÉS", {"sentido": 1, "plazo": 5})],
    "Plan 28/10 · tres soldados al revés 5 min": [("tres soldados AL REVÉS", {"sentido": 1, "plazo": 5})],
    "Plan 28/10 · martillo invertido 10 min": [("patrón martillo invertido", {"sentido": 1, "plazo": 10})],
    "Plan 28/10 · los tres juntos": [("tres cuervos AL REVÉS", {"sentido": 1, "plazo": 5}), ("tres soldados AL REVÉS", {"sentido": 1, "plazo": 5}),
                                     ("patrón martillo invertido", {"sentido": 1, "plazo": 10})],
    "Plan de hoy · REV15 con contexto 10 min": [("REV15", {"sentido": 1, "plazo": 10, "zona": True})],
    "T95H · P05c 15 min": [("P05c (T95H)", {"sentido": 1, "plazo": 15})],
    "Ganó en los dos · pendiente de la media al revés": [("pendiente de la media 48 (Quantdemy)", {"sentido": -1, "plazo": 5, "zona": True, "sesion": "América", "vol": "baja"})],
    "Ganó en los dos · alineación de medias al revés": [("alineación de medias 9/21/50", {"sentido": -1, "plazo": 15, "vol": "baja"})],
    "Ganó en los dos · harami alcista": [("patrón harami alcista", {"sentido": 1, "plazo": 5, "sesion": "América", "vol": "baja"})],
    "Ganó en los dos · doji lápida": [("patrón doji lapida", {"sentido": 1, "plazo": 10, "zona": True})],
}
PLANES["Ganó en los dos · las cuatro juntas"] = [x for k, v in PLANES.items() if k.startswith("Ganó") for x in v]


def margen(evs, desde, hasta, pago):
    r = t7.operar(evs, desde, hasta, False, pago=pago, registrar=True)
    ing = sum(x["g"] for x in r["log"] if x["g"] > 0)
    per = -sum(x["g"] for x in r["log"] if x["g"] < 0)
    r["ingresos"], r["perdidas"], r["margen"] = ing, per, (r["resultado"] / ing * 100 if ing else 0.0)
    return r


def main():
    t, o, h, l, c, ext = t7.cargar()
    S, T5, vol5 = t7.senales(t, o, h, l, c, ext)
    ctxd = t7.contexto(t, c)
    prep = {}
    p("T8 · PRUEBA DIRECTA DE LOS PLANES QUE GANARON ANTES, TAL CUAL · BTCUSDT · 4 binarias al día · 2 % del saldo desde 150 mil COP")
    p("pago 0,85 (hace falta 54.1 %) · margen operativo = resultado / lo cobrado en aciertos\n")
    p(f"{'plan':52s} {'periodo':10s} {'apuestas':>8s} {'acierto':>8s} {'ingresos':>10s} {'pérdidas':>10s} {'resultado':>11s} {'margen':>8s} "
      f"{'días +':>7s} {'con 0,80':>10s}")
    salida = []
    for nombre, piezas in PLANES.items():
        evs = []
        for est, conf in piezas:
            if est not in prep:
                g, ts, ds = S[est]
                prep[est] = t7.preparar(t7.np.asarray(ts, dtype=t7.np.int64), t7.np.asarray(ds), t, o, c, ctxd, T5, vol5)
            evs += t7.eventos(est, prep[est], conf)
        evs.sort()
        for per, (a, b) in (("2024-26", (t7.INI, t7.MES0)), ("EL MES", (t7.MES0, t7.MES1))):
            r = margen(evs, a, b, 0.85)
            r80 = t7.operar(evs, a, b, False, pago=0.80)
            p(f"{nombre[:52]:52s} {per:10s} {r['apuestas']:8d} {r['acierto']:7.1f} % {r['ingresos']:10,.0f} {r['perdidas']:10,.0f} "
              f"{r['resultado']:+11,.0f} {r['margen']:+7.1f} % {r['dias_pos']:3d}/{r['dias']:<3d} {r80['resultado']:+10,.0f}")
            salida.append({"plan": nombre, "periodo": per, **{k: v for k, v in r.items() if k != "log"}, "resultado80": r80["resultado"]})
        p()
    with open(os.path.join(AQUI, "..", "t8_prueba_directa.json"), "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, default=float)


if __name__ == "__main__":
    main()
