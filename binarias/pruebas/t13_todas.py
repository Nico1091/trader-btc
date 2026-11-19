"""T13: cada una de las 36 estrategias por separado y las mezclas, con 100.000 COP, 16 % por apuesta, 4 al día, pago 0,85, mes 29/09-28/10."""
import importlib.util, json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PR = r"C:\Users\ni109\Ingresos\binarias-papel\pruebas"
sys.path.insert(0, PR)
_e = importlib.util.spec_from_file_location("t8", PR + r"\t8_prueba_directa.py")
t8 = importlib.util.module_from_spec(_e); _e.loader.exec_module(t8); t7 = t8.t7
R = json.load(open(r"C:\Users\ni109\Ingresos\binarias-papel\t7_resultados.json", encoding="utf-8"))
t, o, h, l, c, ext = t7.cargar()
S, T5, vol5 = t7.senales(t, o, h, l, c, ext); ctxd = t7.contexto(t, c)
t7.APUESTA, t7.CAP = 0.16, 100000.0
cache = {}
def evs_de(nombre, conf):
    g, ts, ds = S[nombre]
    if nombre not in cache:
        cache[nombre] = t7.preparar(t7.np.asarray(ts, dtype=t7.np.int64), t7.np.asarray(ds), t, o, c, ctxd, T5, vol5)
    return t7.eventos(nombre, cache[nombre], conf)
filas = []
for e in R["estrategias"]:
    if e["nombre"] not in S:
        print("sin señales cargadas:", e["nombre"]); continue
    ev = evs_de(e["nombre"], e["conf"]); ev.sort()
    r = t7.operar(ev, t7.MES0, t7.MES1, e["conf"].get("racha", False), registrar=True)
    g = sum(1 for x in r["log"] if x["res"] > 0); p = sum(1 for x in r["log"] if x["res"] < 0)
    cob = sum(x["g"] for x in r["log"] if x["g"] > 0); per = -sum(x["g"] for x in r["log"] if x["g"] < 0)
    filas.append((r["saldo"], e["grupo"], e["nombre"], e["desc"], r["apuestas"], g, p, cob, per))
filas.sort(reverse=True)
print("ESTRATEGIA POR ESTRATEGIA (cada una sola) · saldo, apuestas, aciertos-fallos, cobrado en aciertos, perdido en fallos")
for s, gr, n, d, a, g, p, cob, per in filas:
    print(f"{gr} | {n[:40]:40s} | {d[:52]:52s} | {a:3d} ap | {g:2d}-{p:2d} | +{cob:>8,.0f} | -{per:>8,.0f} | {s:>9,.0f}")
print()
print("MEZCLAS:", json.dumps([{k: v for k, v in m.items() if k in ('nombre', 'desc', 'miembros', 'estrategias')} for m in R.get("mezclas", [])], ensure_ascii=False)[:1500])
