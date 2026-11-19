"""T14: mezclas de t7 y consenso (2+ estrategias en la misma vela y el mismo sentido), 100.000 COP, 16 %, 4 al día, pago 0,85, mes;
y el 28/10 con todas las estrategias a la vez."""
import importlib.util, json, sys, datetime as dt
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PR = r"C:\Users\ni109\Ingresos\binarias-papel\pruebas"
sys.path.insert(0, PR)
_e = importlib.util.spec_from_file_location("t8", PR + r"\t8_prueba_directa.py")
t8 = importlib.util.module_from_spec(_e); _e.loader.exec_module(t8); t7 = t8.t7
R = json.load(open(r"C:\Users\ni109\Ingresos\binarias-papel\t7_resultados.json", encoding="utf-8"))
CONF = {e["nombre"]: e["conf"] for e in R["estrategias"]}
t, o, h, l, c, ext = t7.cargar()
S, T5, vol5 = t7.senales(t, o, h, l, c, ext); ctxd = t7.contexto(t, c)
t7.APUESTA, t7.CAP = 0.16, 100000.0
EV = {}
for n, conf in CONF.items():
    if n in S:
        g, ts, ds = S[n]
        s = t7.preparar(t7.np.asarray(ts, dtype=t7.np.int64), t7.np.asarray(ds), t, o, c, ctxd, T5, vol5)
        EV[n] = t7.eventos(n, s, conf)
def linea(nombre, ev, racha=False):
    ev = sorted(ev)
    r = t7.operar(ev, t7.MES0, t7.MES1, racha, registrar=True)
    g = sum(1 for x in r["log"] if x["res"] > 0); p = sum(1 for x in r["log"] if x["res"] < 0)
    print(f"{nombre[:58]:58s} | {r['apuestas']:3d} ap | {g:2d}-{p:2d} | 100.000 → {r['saldo']:>9,.0f}")
print("MEZCLAS (varias estrategias, 4 apuestas al día entre todas)")
for m in R["mezclas"]:
    linea(m["nombre"], [x for n in m["estrategias"] if n in EV for x in EV[n]], "parar" in m["nombre"])
linea("las 4 que ganaron antes y en el mes (el bot)", [x for n in ("pendiente de la media 48 (Quantdemy)", "patrón doji lapida", "alineación de medias 9/21/50", "patrón harami alcista") for x in EV[n]])
linea("las 36 juntas (la primera que dé señal)", [x for v in EV.values() for x in v])
# consenso: misma vela de 5 min y mismo sentido
por_vela = defaultdict(list)
for n, v in EV.items():
    for x in v:
        if t7.MES0 - 86400 <= x[0] < t7.MES1:
            por_vela[(x[0], x[2])].append(x)
for k in (2, 3):
    linea(f"consenso: {k} o más estrategias en la misma vela y sentido", [sorted(v, key=lambda x: x[4])[0] for v in por_vela.values() if len({x[1] for x in v}) >= k])
print()
print("EL 28/10 CON TODAS LAS ESTRATEGIAS (cada una sola, hasta 4 apuestas; apuesta 16 % de 100.000 = 16.000)")
col = dt.timezone(dt.timedelta(hours=-5))
d0 = int(dt.datetime(2026, 10, 28, tzinfo=col).timestamp()); d1 = d0 + 86400
for n, v in EV.items():
    r = t7.operar(sorted(v), d0, d1, CONF[n].get("racha", False), registrar=True)
    if not r["log"]:
        continue
    pasos = " · ".join(f"{dt.datetime.fromtimestamp(x['t'], col):%H:%M} {'▲' if x['d'] > 0 else '▼'}{x['plazo']}m {x['g']:+,.0f}" for x in r["log"])
    print(f"{n[:36]:36s} | {pasos} | queda {r['saldo']:,.0f}")
