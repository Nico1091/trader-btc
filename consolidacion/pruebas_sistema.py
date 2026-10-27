"""Pruebas del sistema consolidado (27/10/2026). Si algo falla, lo dice con detalle.

1. Patrones de vela en Python puro idénticos a lib.patrones (toda la historia de 1 h).
2. Motor en vivo (sistema.py) idéntico al simulador (consolidado.py) con las MISMAS velas de Binance:
   cada operación de cada estrategia (lado, entrada, precio, salida, precio de salida), día por día.
3. Sin mirar el futuro: cada señal recalculada con los datos cortados en el instante de la señal da lo mismo.
4. Coinbase (fuente en vivo) frente a Binance: coincidencia de señales en los últimos días.
5. Topes de riesgo (riesgo.py): día, semana, parada total, mínimo de 5 USDT y cierre idempotente, con un libro sintético.
6. Registro de ejecución: una operación cuenta como ejecutada solo con una orden registrada antes del llenado.
7. Sombra con stop duro: el motor en vivo sale igual que un cálculo independiente con numpy sobre las mismas velas.
Desde el 27/10 la prueba 2 recorre TODO el historial (antes, 417 días: el 17 %). «rápido»: solo los últimos 40 días.
Uso: python3 -I pruebas_sistema.py [rápido]"""
import datetime as dt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import consolidado as C  # noqa: E402  (construye las operaciones del simulador con el motor corregido)
import patrones_std  # noqa: E402
import sistema as S  # noqa: E402
from lib import remuestrear, patrones  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):  # Windows: con la salida por tubería usa cp1252, sin «−»
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
inicio = dt.date(2020, 6, 1)  # el motor en vivo pide 130 días previos de velas diarias
dias = [inicio + dt.timedelta(days=i) for i in range((ultimo - inicio).days + 1)]
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

# ---------------------------------------------------------------- 5. topes de riesgo (libro sintético)
import tempfile  # noqa: E402
import riesgo as R  # noqa: E402

os.environ["TRADER_PAPEL"] = tempfile.mkdtemp(prefix="papel-prueba-")
T0 = int(dt.datetime(2026, 11, 2, tzinfo=S.UTC).timestamp())  # lunes


def op_sint(estr, k_min, bruto, dist=0.03, pe=80000.0, pesos=True):
    e = T0 + k_min * 60
    return {"libro": "PRINCIPAL", "estrategia": estr, "lado": 1, "senal": e, "entrada": e, "salida": e + 600, "pe": pe,
            "px": pe * (1 + bruto / 100), "bruto": bruto, "neto": bruto - 0.07, "motivo": "stop" if bruto < 0 else "tiempo",
            "pesos": pesos}


mal5 = []
dia0 = dt.date(2026, 11, 2)
# a) dos pérdidas del 3 % con 2 % de riesgo (nocional ~66 % del saldo): ~−4 % del día -> bloqueada hoy
ops = [op_sint("P11", 0, -3.0), op_sint("P05c", 30, -3.0), op_sint("P05b+pat", 60, +2.0)]
for o in ops:
    R.registrar_orden(o["estrategia"], dia0, "prueba", t=o["entrada"] - 60)
R.guardar_dia(dia0, ops, {"P11": 0.03, "P05c": 0.03, "P05b+pat": 0.03})
ej, te = R.estado(ahora=dt.datetime(2026, 11, 2, 12, tzinfo=S.UTC))
if not (ej["operaciones"] == 2 and ej["bloqueo"] and "HOY" in ej["bloqueo"] and any(m == "tope del día" for _, m in ej["omitidas"])):
    mal5.append(f"tope del día: {ej['operaciones']} ops, bloqueo {ej['bloqueo']}, omitidas {[m for _, m in ej['omitidas']]}")
# b) al día siguiente se puede volver a operar
ej, _ = R.estado(ahora=dt.datetime(2026, 11, 3, 1, tzinfo=S.UTC))
if ej["bloqueo"] and "HOY" in ej["bloqueo"]:
    mal5.append("el tope del día no se levanta al día siguiente")
# c) cerrar el mismo día dos veces no duplica
R.guardar_dia(dia0, ops, {"P11": 0.03, "P05c": 0.03, "P05b+pat": 0.03})
if len(R._leer("libro.jsonl")) != 3:
    mal5.append(f"cierre no idempotente: {len(R._leer('libro.jsonl'))} líneas")
# d) parada total: pérdidas repetidas en días distintos hasta −20 % desde el máximo
for k in range(1, 12):
    d = dia0 + dt.timedelta(days=7 * k)  # una por semana, para no tocar los topes de día ni de semana
    o = op_sint("P11", 7 * 1440 * k, -3.0)
    R.registrar_orden("P11", d, "prueba", t=o["entrada"] - 60)
    R.guardar_dia(d, [o], {"P11": 0.03})
ej, _ = R.estado(ahora=dt.datetime(2027, 3, 1, tzinfo=S.UTC))
if not (ej["bloqueo"] and "PARADA TOTAL" in ej["bloqueo"] and ej["caida_pct"] >= 20):
    mal5.append(f"parada total: caída {ej['caida_pct']:.1f} %, bloqueo {ej['bloqueo']}")
# e) mínimo de 5 USDT: con una distancia al stop del 20 %, 2 % de riesgo da 1,26 USDT -> no cabe
os.environ["TRADER_PAPEL"] = tempfile.mkdtemp(prefix="papel-prueba-")
o = op_sint("P05c", 0, +1.0)
R.registrar_orden("P05c", dia0, "prueba", t=o["entrada"] - 60)
R.guardar_dia(dia0, [o], {"P05c": 0.20})
ej, _ = R.estado(ahora=dt.datetime(2026, 11, 2, 12, tzinfo=S.UTC))
if ej["operaciones"] != 0 or not any("no cabe" in m for _, m in ej["omitidas"]):
    mal5.append("el mínimo de 5 USDT no se respeta")
print(f"5. Topes de riesgo: {5 - len(mal5)} de 5 casos bien")
for x in mal5:
    print("   FALLA:", x)
if mal5:
    fallas.append(f"{len(mal5)} casos de riesgo mal")

# ---------------------------------------------------------------- 6. registro de ejecución
os.environ["TRADER_PAPEL"] = tempfile.mkdtemp(prefix="papel-prueba-")
o = op_sint("P05b+pat", 120, +1.0)
casos = [("sin orden", None, False), ("orden antes del llenado", o["entrada"] - 1, True),
         ("orden después del llenado", o["entrada"] + 60, False), ("orden de P05b cubre P05b+pat", o["entrada"] - 600, True),
         ("condicionada de la víspera (domingo 20:00 para el lunes)", T0 - 4 * 3600, True),
         ("orden de hace 3 días", T0 - 3 * 86400, False)]
mal6 = []
for nombre, t, esperado in casos:
    os.environ["TRADER_PAPEL"] = tempfile.mkdtemp(prefix="papel-prueba-")
    if t is not None:
        dia_orden = dt.datetime.fromtimestamp(t, S.UTC).date()  # el día en que se escribió, como hace el comando
        R.registrar_orden("P05b" if "cubre" in nombre else "P05b+pat", dia_orden, nombre, t=t)
    if R.ejecutada(o, dia0) != esperado:
        mal6.append(nombre)
if R.ejecutada({"estrategia": "AZAR", "entrada": 0}, dia0) is not None:
    mal6.append("AZAR debe medirse siempre")
print(f"6. Registro de ejecución: {7 - len(mal6)} de 7 casos bien")
if mal6:
    fallas.append("ejecución mal: " + ", ".join(mal6))

# ---------------------------------------------------------------- 7. sombra con stop duro (numpy independiente)
V = C.V
mal7 = n7 = 0
for d, y in senales_para_3[:300]:
    if y["estrategia"] != "P05b":
        continue
    D = S.Dia(fuente, d)
    i_e = (y["entrada"] - D.d0) // 60
    t_s, px, _ = D.salida_stop_duro(i_e, D.ap, y["lado"])
    ie = int(V.t.searchsorted(dt.datetime.fromtimestamp(y["entrada"], S.UTC)))
    ifin = int(V.t.searchsorted(dt.datetime.fromtimestamp(D.d0 + 86340, S.UTC)))
    seg = slice(ie + 1, ifin + 1)
    k = np.flatnonzero(V.l[seg] <= D.ap) if y["lado"] > 0 else np.flatnonzero(V.h[seg] >= D.ap)
    if len(k):
        j = ie + 1 + k[0]
        ref_px = min(V.o[j], D.ap) if y["lado"] > 0 else max(V.o[j], D.ap)
    else:
        ref_px = V.c[ifin]
    n7 += 1
    mal7 += abs(ref_px - px) > 1e-6
print(f"7. Sombra con stop duro: {n7} operaciones de P05b comparadas con numpy; distintas {mal7}")
if mal7:
    fallas.append(f"{mal7} sombras de stop duro distintas")

print("\nRESULTADO:", "SIN FALLAS" if not fallas else "FALLAS: " + " | ".join(fallas))
