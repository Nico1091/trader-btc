"""Pruebas del sistema consolidado (27/10/2026). Si algo falla, lo dice con detalle.

1. Patrones de vela en Python puro idénticos a lib.patrones (toda la historia de 1 h).
2. Motor en vivo (sistema.py) idéntico al simulador (consolidado.py) con las MISMAS velas de Binance:
   cada operación de cada estrategia (lado, entrada, precio, salida, precio de salida), día por día.
3. Sin mirar el futuro: cada señal recalculada con los datos cortados en el instante de la señal da lo mismo.
4. Coinbase (fuente en vivo) frente a Binance: coincidencia de señales en los últimos días.
Uso: python3 -I pruebas_sistema.py [rápido]"""
import datetime as dt
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import consolidado as C  # noqa: E402  (construye las operaciones del simulador con el motor corregido)
import patrones_std  # noqa: E402
import sistema as S  # noqa: E402
from lib import remuestrear, patrones  # noqa: E402

RAPIDO = "rápido" in sys.argv
fallas = []

# ---------------------------------------------------------------- 1. patrones
h = remuestrear(C.m1, 60)
ref, _ = patrones(h)
mio = patrones_std.patrones(h.o.tolist(), h.h.tolist(), h.l.tolist(), h.c.tolist())
dif = {k: int((ref[k].to_numpy() != np.array(mio[k])).sum()) for k in patrones_std.LADO}
print(f"1. Patrones: {len(h):,} velas de 1 h, {sum(int(ref[k].sum()) for k in patrones_std.LADO):,} patrones; diferencias: "
      f"{sum(dif.values())}")
if sum(dif.values()):
    fallas.append(f"patrones distintos: { {k: v for k, v in dif.items() if v} }")

# ---------------------------------------------------------------- 2. motor en vivo = simulador
ref_ops = {
    "P05b": C.BASES["PRINCIPAL P05b por régimen"][0],
    "P11": C.BASES["PRINCIPAL P11 con contexto"][0],
    "P05c": [o for o in C.BASES["PRINCIPAL P05c largo con contexto"][0] if C.CONF15["todos 3 de 3"](o["senal"], o["lado"])],
    "N9": C.BASES["PRUEBA N9 Asia-Londres"][0],
    "N8": C.BASES["PRUEBA N8 miércoles con contexto"][0],
}
ref_ops["P05b+pat"] = [o for o in ref_ops["P05b"] if o["lado"] > 0 and C.H1.patron(o["senal"], 1)]
por_dia = {}
for nb, ops in ref_ops.items():
    for o in ops:
        por_dia.setdefault((o["entrada"].date(), nb), []).append(o)

fuente = S.Npy(os.environ.get("DATOS_BTC", "/home/user/datos-btc/BTCUSDT_um_1m.npy"))
ultimo = C.V.t[-1].date()
dias = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range((ultimo - dt.date(2026, 1, 1)).days + 1)]
r = random.Random(27)
dias += sorted(r.sample([dt.date(2020, 6, 1) + dt.timedelta(days=i) for i in range((dt.date(2025, 12, 31) - dt.date(2020, 6, 1)).days)], 120))
if RAPIDO:
    dias = dias[-40:]
t0 = time.time()
iguales = distintas = 0
detalle = []
senales_para_3 = []
for d in dias:
    D = S.Dia(fuente, d)
    ops, notas = D.todo()
    vivo = {}
    for o in ops:
        if o["estrategia"] != "AZAR":
            vivo.setdefault(o["estrategia"], []).append(o)
    for nb in ref_ops:
        a = por_dia.get((d, nb), [])
        b = vivo.get(nb, [])
        ok = len(a) == len(b) and all(
            x["lado"] == y["lado"] and int(x["entrada"].timestamp()) == y["entrada"] and abs(x["pe"] - y["pe"]) < 1e-6
            and int(x["salida"].timestamp()) == y["salida"] and abs(x["px"] - y["px"]) < 1e-6 for x, y in zip(a, b))
        if ok:
            iguales += 1
        else:
            distintas += 1
            detalle.append(f"{d} {nb}: simulador {[(x['lado'], str(x['entrada']), round(x['pe'], 2), str(x['salida']), round(x['px'], 2)) for x in a]} "
                           f"vs vivo {[(y['lado'], dt.datetime.fromtimestamp(y['entrada'], S.UTC).strftime('%H:%M'), round(y['pe'], 2), dt.datetime.fromtimestamp(y['salida'], S.UTC).strftime('%H:%M'), round(y['px'], 2)) for y in b]}")
        for y in b:
            if y["estrategia"] in ("P05b", "P05c", "N9"):
                senales_para_3.append((d, y))
print(f"2. Motor en vivo = simulador: {len(dias)} días × {len(ref_ops)} estrategias = {iguales + distintas} comparaciones; "
      f"iguales {iguales}, distintas {distintas} ({time.time() - t0:.0f} s)")
for x in detalle[:15]:
    print("   DISTINTA:", x)
if distintas:
    fallas.append(f"{distintas} comparaciones distintas entre el motor en vivo y el simulador")

# ---------------------------------------------------------------- 3. sin mirar el futuro
mal = 0
for d, y in senales_para_3[:80]:
    D = S.Dia(fuente, d, ahora=y["senal"])  # solo lo que existía en el instante de la señal
    _, notas = D.todo()
    clave = {"P05b": "P05b: SEÑAL", "P05c": "P05c: SEÑAL", "N9": "N9: SEÑAL"}[y["estrategia"]]
    if y["estrategia"] == "N9":
        vio = any(n.startswith("N9: señal") or n.startswith("N9: SEÑAL") for n in notas)
    else:
        vio = any(clave.split(":")[0] + ": señal" in n or clave in n for n in notas)
    D_full = S.Dia(fuente, d)
    conf_ok = True
    if y["estrategia"] == "P05b":
        conf_ok = (D.e1h(y["senal"], y["lado"]), D.e4h(y["senal"], y["lado"]), D.patron1h(y["senal"], y["lado"])) == \
                  (D_full.e1h(y["senal"], y["lado"]), D_full.e4h(y["senal"], y["lado"]), D_full.patron1h(y["senal"], y["lado"]))
    if not vio or not conf_ok:
        mal += 1
        print(f"   FUTURO: {d} {y['estrategia']} señal {dt.datetime.fromtimestamp(y['senal'], S.UTC):%H:%M} vista={vio} confirmaciones iguales={conf_ok}")
print(f"3. Sin mirar el futuro: {min(80, len(senales_para_3))} señales recalculadas con los datos cortados en su instante; con diferencias: {mal}")
if mal:
    fallas.append(f"{mal} señales cambian al cortar los datos en su instante")

# ---------------------------------------------------------------- 4. Coinbase frente a Binance
if not RAPIDO:
    cb = S.Coinbase()
    n = coinc = 0
    for i in range(20):
        d = ultimo - dt.timedelta(days=i)
        try:
            a = S.Dia(fuente, d).todo()[0]
            b = S.Dia(cb, d).todo()[0]
        except S.LecturaInsuficiente as e:
            print(f"   {d}: lectura insuficiente ({e})")
            continue
        sa = sorted((o["estrategia"], o["lado"]) for o in a if o["estrategia"] != "AZAR")
        sb_ = sorted((o["estrategia"], o["lado"]) for o in b if o["estrategia"] != "AZAR")
        n += 1
        coinc += sa == sb_
        if sa != sb_:
            print(f"   {d}: Binance {sa} · Coinbase {sb_}")
    print(f"4. Coinbase frente a Binance: {coinc} de {n} días con las mismas operaciones (diferencias = precio distinto entre casas, no falla del motor)")

print("\nRESULTADO:", "SIN FALLAS" if not fallas else "FALLAS: " + " | ".join(fallas))
