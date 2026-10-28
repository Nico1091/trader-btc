"""Prueba 10 (28/10/2026): el motor en vivo (sistema.Dia) da en otras monedas las mismas operaciones que el simulador.

La referencia son las operaciones del simulador guardadas en investigacion/operaciones/ops_<ACTIVO>.csv (c1_operaciones.py,
mismo motor que la consolidación). Para cada activo se comparan todos los días con operaciones de los últimos 120 días del
archivo y 20 días sin operaciones elegidos al azar (semilla fija): lado, minuto de entrada y de salida y precios.
Uso: python -I consolidacion/prueba_multiactivo.py SOL DOGE   (datos en datos/um/<ACTIVO>USDT_um_1m.npy o TRADER_DATOS)"""
import csv
import datetime as dt
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sistema as S  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "datos")
ESTR = ("P05b", "P05c", "P11", "N8", "N9")


def ts(x):
    return int(dt.datetime.fromisoformat(x).timestamp())


def probar(activo):
    ref = {}
    with open(os.path.join(AQUI, "..", "investigacion", "operaciones", f"ops_{activo}.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = dt.datetime.fromisoformat(r["entrada"]).date()
            ref.setdefault((d, r["estrategia"]), []).append(
                (int(r["lado"]), ts(r["entrada"]), float(r["pe"]), ts(r["salida"]), float(r["px"])))
    dias_ref = sorted({d for d, _ in ref})
    fin = dias_ref[-1]
    con = [d for d in dias_ref if d > fin - dt.timedelta(days=120)]
    todos = [fin - dt.timedelta(days=i) for i in range(1, 400)]
    sin = random.Random(10).sample([d for d in todos if d not in set(dias_ref) and d.year >= 2021], 20)
    fuente = S.Npy(os.path.join(DATOS, "um", f"{activo}USDT_um_1m.npy"))
    iguales = distintas = 0
    detalle = []
    for d in sorted(set(con) | set(sin)):
        try:
            D = S.Dia(fuente, d)
        except S.LecturaInsuficiente as e:
            detalle.append(f"{d}: lectura insuficiente ({e})")
            distintas += 1
            continue
        ops, _ = D.todo()
        vivo = {}
        for o in ops:
            if o["estrategia"] in ESTR:
                vivo.setdefault(o["estrategia"], []).append((o["lado"], o["entrada"], o["pe"], o["salida"], o["px"]))
        for e in ESTR:
            a, b = ref.get((d, e), []), vivo.get(e, [])
            ok = len(a) == len(b) and all(x[0] == y[0] and x[1] == y[1] and x[3] == y[3]
                                          and abs(x[2] - y[2]) <= 1e-9 * max(1, abs(x[2])) and abs(x[4] - y[4]) <= 1e-9 * max(1, abs(x[4]))
                                          for x, y in zip(a, b))
            if ok:
                iguales += 1
            else:
                distintas += 1
                detalle.append(f"{d} {e}: simulador {a} · vivo {b}")
    print(f"10. {activo}: {len(set(con) | set(sin))} días × {len(ESTR)} estrategias = {iguales + distintas} comparaciones;"
          f" iguales {iguales}, distintas {distintas}")
    for x in detalle[:8]:
        print("    DISTINTA:", x)
    return distintas


def main():
    fallas = sum(probar(a.upper()) for a in (sys.argv[1:] or ["SOL", "DOGE"]))
    print("RESULTADO:", "SIN FALLAS" if fallas == 0 else f"{fallas} DIFERENCIAS")


if __name__ == "__main__":
    main()
