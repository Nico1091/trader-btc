"""T15: el consenso (k o más estrategias, misma vela y sentido) en 2020-23 (fuera de la elección), 2024-26 (donde se ajustaron) y el mes."""
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
print("velas desde", dt.datetime.utcfromtimestamp(int(t[0])).date(), "hasta", dt.datetime.utcfromtimestamp(int(t[-1])).date())
S, T5, vol5 = t7.senales(t, o, h, l, c, ext); ctxd = t7.contexto(t, c)
por_vela = defaultdict(list)
for n, conf in CONF.items():
    if n in S:
        g, ts, ds = S[n]
        s = t7.preparar(t7.np.asarray(ts, dtype=t7.np.int64), t7.np.asarray(ds), t, o, c, ctxd, T5, vol5)
        for x in t7.eventos(n, s, conf):
            por_vela[(x[0], x[2])].append(x)
t7.CAP = 100000.0
P = {"2020-23": (int(t[0]) + 86400 * 60, t7.INI), "2024-26": (t7.INI, t7.MES0), "el mes": (t7.MES0, t7.MES1)}
for k in (3, 4):
    ev = sorted(sorted(v, key=lambda x: x[4])[0] for v in por_vela.values() if len({x[1] for x in v}) >= k)
    for ap in (0.02, 0.16):
        t7.APUESTA = ap
        for per, (a, b) in P.items():
            r = t7.operar(ev, a, b, False, registrar=True)
            g = sum(1 for x in r["log"] if x["res"] > 0); p = sum(1 for x in r["log"] if x["res"] < 0)
            nd = max(1, (b - a) / 86400)
            print(f"consenso {k}+ · apuesta {ap * 100:2.0f} % · {per:7s}: {r['apuestas']:4d} apuestas ({r['apuestas'] / nd:.2f} al día) · {g}-{p} · acierto {r['acierto']:.1f} % · 100.000 → {r['saldo']:,.0f}")
