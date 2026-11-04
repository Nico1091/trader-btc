"""T11: apuesta fija de 5 USDT (15.900 COP, mínimo de Binance) desde 100.000 COP, con la secuencia real de las 4 estrategias.
Cuántos arranques (uno por cada día de 2024-26) quiebran antes de 30 días y cómo quedan a los 30."""
import importlib.util, sys
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
t7.APUESTA = 0.02
log = t7.operar(evs, t7.INI, t7.MES1, False, registrar=True)["log"]
seq = [(x["t"], x["res"]) for x in log]
FIJA = 15900.0
for pago in (0.80, 0.85, 0.90):
    quiebra = arriba = 0; finales = []
    dias = sorted({(tt - t7.HCOL) // 86400 for tt, _ in seq if tt < t7.MES0})
    for d0 in dias:
        ini = d0 * 86400 + t7.HCOL; fin = ini + 30 * 86400
        saldo, roto = 100000.0, False
        for tt, r in seq:
            if tt < ini: continue
            if tt >= fin: break
            if saldo < FIJA: roto = True; break
            saldo += FIJA * pago if r > 0 else -FIJA if r < 0 else 0
        roto = roto or saldo < FIJA
        quiebra += roto; arriba += saldo > 100000; finales.append(saldo)
    finales.sort(); n = len(finales)
    print(f"pago {pago:.2f}: {n} arranques de 30 días · quiebra (no alcanza para otra apuesta) {quiebra / n * 100:.0f} % · "
          f"termina arriba de 100 mil {arriba / n * 100:.0f} % · mediana {finales[n // 2]:,.0f} COP")
