"""T9 (29/10/2026): su propuesta de apostar el 16 % del saldo con interés compuesto, con las mismas estrategias y el mismo mes.

Pedido de Nicolás: «opera 20.000 y da 28.000… el 16 % del total… y así sucesivamente vas operando, sobre el compuesto».
Mismas reglas que T7/T8 (4 binarias al día, una por franja de 6 h, una abierta a la vez, empate = se devuelve, pago 0,85),
cambiando solo el tamaño de la apuesta: 2, 5, 10 y 16 % del saldo del momento (interés compuesto en todos).
Uso: python -I t9_apuesta_16.py > t9_apuesta_16.txt"""
import importlib.util
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
_e = importlib.util.spec_from_file_location("t8", os.path.join(AQUI, "t8_prueba_directa.py"))
t8 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t8)
t7, p = t8.t7, t8.p


def main():
    t, o, h, l, c, ext = t7.cargar()
    S, T5, vol5 = t7.senales(t, o, h, l, c, ext)
    ctxd = t7.contexto(t, c)
    p("T9 · APOSTAR UN % FIJO DEL SALDO CON INTERÉS COMPUESTO · BTCUSDT · 4 binarias al día · pago 0,85 · desde 150 mil COP\n")
    for plan in ("Ganó en los dos · las cuatro juntas", "Plan 28/10 · tres cuervos al revés 5 min", "Plan de hoy · REV15 con contexto 10 min"):
        evs = []
        for est, conf in t8.PLANES[plan]:
            g, ts, ds = S[est]
            s = t7.preparar(t7.np.asarray(ts, dtype=t7.np.int64), t7.np.asarray(ds), t, o, c, ctxd, T5, vol5)
            evs += t7.eventos(est, s, conf)
        evs.sort()
        p(f"== {plan} ==")
        for apuesta in (0.02, 0.05, 0.10, 0.16):
            t7.APUESTA = apuesta
            for per, (a, b) in (("2024-26", (t7.INI, t7.MES0)), ("el mes", (t7.MES0, t7.MES1))):
                r = t7.operar(evs, a, b, False, registrar=True)
                saldos = [150000.0] + [x["saldo"] for x in r["log"]]
                pico, caida = saldos[0], 0.0
                for v in saldos:
                    pico = max(pico, v)
                    caida = max(caida, 1 - v / pico)
                peor_racha = mejor = 0
                for x in r["log"]:
                    peor_racha = peor_racha + 1 if x["res"] < 0 else 0
                    mejor = max(mejor, peor_racha)
                p(f"   apuesta {apuesta * 100:4.0f} % · {per:8s}: {r['apuestas']:5d} apuestas, acierto {r['acierto']:5.1f} % · 150 mil → "
                  f"{r['saldo']:>13,.0f} COP ({r['resultado']:+,.0f}) · caída máxima {caida * 100:4.0f} % · peor racha {mejor} pérdidas seguidas")
        p()
    t7.APUESTA = 0.02


if __name__ == "__main__":
    main()
