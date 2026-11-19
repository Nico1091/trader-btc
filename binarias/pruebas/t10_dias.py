"""T10 (29/10/2026): día por día, cuántos días gana y cuántos pierde con 100.000 COP, según el % apostado.
Mismas 4 estrategias y reglas que T8/T9 (4 binarias al día, pago 0,85). Solo lee; no toca nada del bot."""
import importlib.util
import math
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PR = r"C:\Users\ni109\Ingresos\binarias-papel\pruebas"
sys.path.insert(0, PR)
_e = importlib.util.spec_from_file_location("t8", PR + r"\t8_prueba_directa.py")
t8 = importlib.util.module_from_spec(_e)
_e.loader.exec_module(t8)
t7 = t8.t7


def main():
    t, o, h, l, c, ext = t7.cargar()
    S, T5, vol5 = t7.senales(t, o, h, l, c, ext)
    ctxd = t7.contexto(t, c)
    evs = []
    for est, conf in t8.PLANES["Ganó en los dos · las cuatro juntas"]:
        g, ts, ds = S[est]
        s = t7.preparar(t7.np.asarray(ts, dtype=t7.np.int64), t7.np.asarray(ds), t, o, c, ctxd, T5, vol5)
        evs += t7.eventos(est, s, conf)
    evs.sort()
    t7.CAP = 100000.0
    for per, (a, b) in (("2024-26", (t7.INI, t7.MES0)), ("mes 29/09-28/10", (t7.MES0, t7.MES1))):
        print(f"== {per} ==")
        for ap in (0.02, 0.05, 0.08, 0.16):
            t7.APUESTA = ap
            r = t7.operar(evs, a, b, False, registrar=True)
            dias, saldo = {}, 100000.0
            for x in r["log"]:
                d = (x["t"] - t7.HCOL) // 86400
                ini, gan, per_, n = dias.get(d, (saldo, 0, 0, 0))
                dias[d] = (ini, gan + (x["res"] > 0), per_ + (x["res"] < 0), n + 1)
                saldo = x["saldo"]
            # resultado de cada día en % del saldo con que empezó
            fin = {}
            saldo = 100000.0
            for x in r["log"]:
                fin[(x["t"] - t7.HCOL) // 86400] = x["saldo"]
            pct = [(fin[d] / dias[d][0] - 1) * 100 for d in sorted(dias)]
            pos = sum(1 for v in pct if v > 0.001)
            neg = sum(1 for v in pct if v < -0.001)
            cuatro = sum(1 for d in dias if dias[d][1] == 4)
            geo = math.exp(sum(math.log(1 + v / 100) for v in pct) / len(pct)) - 1
            print(f"  {ap * 100:3.0f} %: {len(pct)} días con apuesta · ganó {pos} ({pos / len(pct) * 100:.0f} %) · perdió {neg} · "
                  f"4 de 4 aciertos: {cuatro} días · mejor día {max(pct):+.1f} % · peor día {min(pct):+.1f} % · "
                  f"día promedio {sum(pct) / len(pct):+.2f} % · día típico (compuesto) {geo * 100:+.2f} % · "
                  f"100 mil → {r['saldo']:,.0f}")
        print()


if __name__ == "__main__":
    main()
