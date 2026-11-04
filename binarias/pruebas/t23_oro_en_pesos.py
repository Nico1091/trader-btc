"""T23 (29/10/2026): el oro en pesos, con las apuestas a ciegas de t18 y t19 sobre PAXGUSDT (y XAUUSDT, historia corta).

Por procedimiento (reglas; modelo a 10, 30 y 60 min): acierto por año, con el empate como fallo (como en todas las pruebas) y sin
contar los empates (Binance devuelve lo apostado en empate en sus Contratos de Evento de BTC y ETH). En pesos: 100.000 COP
durante 30 días, arrancando cada día, con el 16 % y con medio Kelly (acierto a ciegas de los 6 meses anteriores; mínimo 5 USDT).
Uso: python -I t23_oro_en_pesos.py"""
import bisect
import datetime as dt
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
PAGO, MINIMO, CAP = 0.85, 5 * 3180.0, 100000.0


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def cargar(sim):
    P = {}
    r18 = os.path.join(AQUI, f"t18_{sim}_apuestas.csv")
    if os.path.exists(r18):
        lin = open(r18, encoding="utf-8-sig").read().splitlines()[1:]
        P["reglas"] = [(x.split(";")[0], x.split(";")[5]) for x in lin]
    r19 = os.path.join(AQUI, f"t19_{sim}_apuestas.csv")
    if os.path.exists(r19):
        lin = open(r19, encoding="utf-8-sig").read().splitlines()[1:]
        for pl in ("10", "30", "60"):
            P[f"modelo {pl} min"] = [(x.split(";")[0], x.split(";")[3]) for x in lin if x.split(";")[1] == pl]
    out = {}
    for k, v in P.items():
        v.sort()
        out[k] = [(dt.datetime.strptime(f[:10], "%Y-%m-%d").toordinal(), f[:7], r) for f, r in v]
    return out


def atras(mes, k):
    y, m = int(mes[:4]), int(mes[5:])
    i = y * 12 + m - 1 - k
    return f"{i // 12}-{i % 12 + 1:02d}"


def fraccion(por_mes, mes):
    w = n = 0
    for i in range(1, 7):
        a, b = por_mes.get(atras(mes, i), (0, 0))
        w, n = w + a, n + b
    if n < 100:
        return 0.0
    p = w / n
    return max(0.0, (p * PAGO - (1 - p)) / PAGO) * 0.5


def arranques(ap, regla, empate_devuelve, dias=30):
    por_mes = {}
    for _, mes, r in ap:
        w, n = por_mes.get(mes, (0, 0))
        por_mes[mes] = (w + (r == "acierta"), n + 1)
    ds = [a[0] for a in ap]
    fr = {}
    out = []
    for d0 in range(ds[0], ds[-1] - dias + 2):
        i0, i1 = bisect.bisect_left(ds, d0), bisect.bisect_left(ds, d0 + dias)
        s = CAP
        for _, mes, r in ap[i0:i1]:
            if s < MINIMO:
                s = 0.0
                break
            if regla == "16 %":
                m = max(0.16 * s, MINIMO)
            else:
                if mes not in fr:
                    fr[mes] = fraccion(por_mes, mes)
                if fr[mes] <= 0:
                    continue
                m = max(fr[mes] * s, MINIMO)
            if r == "acierta":
                s += m * PAGO
            elif r == "falla" or not empate_devuelve:
                s -= m
        out.append(s)
    return out


def main():
    lineas = []
    p = lambda x="": (lineas.append(x), print(x, flush=True))
    p("T23 · ORO EN PESOS · apuestas a ciegas de t18 (reglas) y t19 (modelo) · pago 0,85 · desde 100.000 COP · mínimo 5 USDT\n")
    for sim in ("PAXGUSDT", "XAUUSDT"):
        P = cargar(sim)
        if not P:
            continue
        p(f"===== {sim} =====")
        for proc, ap in P.items():
            if not ap:
                p(f"{proc}: sin apuestas")
                continue
            n = len(ap)
            w = sum(1 for a in ap if a[2] == "acierta")
            e = sum(1 for a in ap if a[2] == "empate")
            dias = max(1, ap[-1][0] - ap[0][0])
            p(f"{proc}: {es(n, 0)} apuestas ({es(n / dias, 1)} al día) · {es(100 * w / n)} % con el empate como fallo · "
              f"{es(100 * w / max(1, n - e))} % sin contar empates · empates {es(100 * e / n)} %")
            años = sorted({a[1][:4] for a in ap})
            p("   por año: " + " · ".join(
                f"{y} {es(100 * sum(1 for a in ap if a[1][:4] == y and a[2] == 'acierta') / max(1, sum(1 for a in ap if a[1][:4] == y)))} % "
                f"({sum(1 for a in ap if a[1][:4] == y)})" for y in años))
            for regla in ("16 %", "medio Kelly"):
                for dev in (False, True):
                    s = sorted(arranques(ap, regla, dev))
                    if not s:
                        continue
                    arriba = sum(1 for x in s if x > CAP) / len(s)
                    quiebra = sum(1 for x in s if x < MINIMO) / len(s)
                    p(f"   30 días · {regla} · empate {'devuelve' if dev else 'pierde'}: termina arriba {es(100 * arriba)} % · "
                      f"quiebra {es(100 * quiebra)} % · mediana {es(s[len(s) // 2], 0)} ({len(s)} arranques)")
        p()
    open(os.path.join(AQUI, "t23_oro_en_pesos.txt"), "w", encoding="utf-8").write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    main()
