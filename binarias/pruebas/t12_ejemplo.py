"""T12: apuesta por apuesta, primeros días reales del mes (29/09 en adelante), 16 % del saldo, pago 0,85, desde 100.000 COP."""
import importlib.util, sys, datetime as dt
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PR = r"C:\Users\ni109\Ingresos\binarias-papel\pruebas"
sys.path.insert(0, PR)
_e = importlib.util.spec_from_file_location("t8", PR + r"\t8_prueba_directa.py")
t8 = importlib.util.module_from_spec(_e); _e.loader.exec_module(t8); t7 = t8.t7
t, o, h, l, c, ext = t7.cargar()
S, T5, vol5 = t7.senales(t, o, h, l, c, ext); ctxd = t7.contexto(t, c)
evs = []
for est, conf in t8.PLANES["Ganó en los dos · las cuatro juntas"]:
    g, ts, ds = S[est]
    s = t7.preparar(t7.np.asarray(ts, dtype=t7.np.int64), t7.np.asarray(ds), t, o, c, ctxd, T5, vol5)
    evs += t7.eventos(est, s, conf)
evs.sort()
t7.APUESTA, t7.CAP = 0.16, 100000.0
log = t7.operar(evs, t7.MES0, t7.MES1, False, registrar=True)["log"]
col = dt.timezone(dt.timedelta(hours=-5))
for x in log[:16]:
    h = dt.datetime.fromtimestamp(x["t"], col).strftime("%d/%m %H:%M")
    lado = "sube" if x["d"] > 0 else "baja"
    res = "acierta" if x["res"] > 0 else "falla" if x["res"] < 0 else "empate"
    print(f"{h} | {x['estrategia'][:28]:28s} | {lado} | {x['plazo']:2d} min | apuesta {x['monto']:>7,.0f} | {res:7s} | {x['g']:>+8,.0f} | saldo {x['saldo']:>8,.0f}")
