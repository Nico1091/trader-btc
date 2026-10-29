"""T3 (29/10/2026): las binarias que ganaron en T2, medidas como las paga un bróker y como se pueden ejecutar de verdad, y su
libro en pesos (cuadro de margen operativo).

Pedido de Nicolás: «operaciones binarias, no trading común»; «tú como agente debes operar primero y mostrarme cada resultado».
Cambios frente a T2, fijados antes de mirar:
- Empate (precio al vencer igual al de entrada) = se devuelve lo apostado, como en IQ Option; se informa cuántos hay.
- Dos entradas: LIBRO al cierre de la vela de señal (lo de T2) y REAL al cierre del minuto siguiente (el agente ve la vela,
  decide y apuesta: un minuto de retraso como máximo). El vencimiento se cuenta desde la entrada.
- Familias que pasaron T2 (señal REV: vela con cuerpo ≥ 2 × la media de los 100 previos → apuesta en contra):
  B15  BTC, vela de 15 min, vence en 15 min (sin preventiva y con CTX, EUROPA, AMERICA, VBAJA)
  T60  las 12 monedas, vela de 60 min, vence en 60 min (sin preventiva y con EUROPA, VALTA, CTX)
- Libro: 150.000 COP; apuesta fija del 1, 2, 5 o 10 % del saldo; pago 0,80, 0,85 o 0,90; varias a la vez si coinciden
  (cada una con el % del saldo del momento); parada si el saldo cae al 20 % del inicial.
- Se elige para el agente la familia y preventiva con mayor acierto REAL en la peor mitad (≥ 300 apuestas por mitad).
Salidas: t3_binarias_libro.txt, t3_cuadro.json, t3_replay.json (apuestas del último trimestre, para verlas en tiempo real)
y consolidacion/agente_binarias.json (la configuración del agente de binarias).
Uso: python -I t3_binarias_libro.py > t3_binarias_libro.txt"""
import datetime as dt
import json
import os
import re
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos"), "um")
CONS = os.path.join(AQUI, "..", "..", "consolidacion")
CORTE = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp())
ACTIVOS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "LINK", "AVAX", "LTC", "DOT", "TRX"]
COP = 3177.85
FAMILIAS = {"B15": (["BTC"], 15, ("—", "CTX", "EUROPA", "AMERICA", "VBAJA")),
            "T60": (ACTIVOS, 60, ("—", "EUROPA", "VALTA", "CTX"))}


def es(s):
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "§", s)
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", s)
    return s.replace("§", ".")


def p(s=""):
    print(es(s))


def media_previa(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    m = np.full(len(x), np.nan)
    m[n:] = (cs[n:-1] - cs[:-n - 1]) / n
    return m


def contexto_diario(t, c):
    dia = t // 86400
    ultimo = np.r_[np.flatnonzero(np.diff(dia)), len(dia) - 1]
    d, cd = dia[ultimo], c[ultimo]
    sma = np.full(len(cd), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(cd)])
    sma[50:] = (cs[50:-1] - cs[:-51]) / 50
    ctx = np.zeros(len(cd))
    ctx[1:] = np.sign(cd[:-1] - sma[1:])
    return dict(zip(d.tolist(), np.nan_to_num(ctx).tolist()))


def apuestas(activo, tf):
    """Todas las señales REV de un activo y su resultado al vencer, entrando al cierre (libro) y un minuto después (real)."""
    x = np.load(os.path.join(DATOS, f"{activo}USDT_um_1m.npy"), mmap_mode="r")
    t = (x[:, 0] // 1000).astype(np.int64)
    o1, h1, l1, c1 = (np.asarray(x[:, k]) for k in (1, 2, 3, 4))
    ctxd = contexto_diario(t, c1)
    i0 = int(np.argmax(t % (tf * 60) == 0))
    n = (len(t) - i0) // tf * tf
    T = t[i0:i0 + n].reshape(-1, tf)[:, 0]
    O = o1[i0:i0 + n].reshape(-1, tf)[:, 0]
    H = h1[i0:i0 + n].reshape(-1, tf).max(1)
    L = l1[i0:i0 + n].reshape(-1, tf).min(1)
    C = c1[i0:i0 + n].reshape(-1, tf)[:, -1]
    cuerpo = np.abs(C - O)
    fuerte = cuerpo >= 2 * media_previa(cuerpo, 100)
    rango = H - L
    m500 = media_previa(rango, 500)
    valta = media_previa(rango, 20) > m500
    j = np.flatnonzero(fuerte & ~np.isnan(m500))
    j = j[j + 1 < len(C)]
    d = -np.sign(C[j] - O[j]).astype(int)
    j, d = j[d != 0], d[d != 0]
    t_sen = T[j] + tf * 60  # cierre de la vela de señal
    k_cierre = (t_sen - t[0]) // 60 - 1  # minuto que cierra la vela (índice en las velas de 1 min)
    k_real = k_cierre + 1  # el agente entra al cierre del minuto siguiente
    ok = k_real + tf < len(c1)
    j, d, t_sen, k_cierre, k_real = j[ok], d[ok], t_sen[ok], k_cierre[ok], k_real[ok]
    pe_l, px_l = c1[k_cierre], c1[k_cierre + tf]
    pe_r, px_r = c1[k_real], c1[k_real + tf]
    hora = (t_sen % 86400) // 3600
    ctx = np.array([ctxd.get(int(v), 0.0) for v in (t_sen // 86400)])
    return {"activo": np.full(len(j), activo), "t": t_sen, "d": d, "res_l": np.sign(d * (px_l - pe_l)), "res_r": np.sign(d * (px_r - pe_r)),
            "pe_r": pe_r, "px_r": px_r, "ses": np.where(hora < 7, 0, np.where(hora < 13, 1, np.where(hora < 21, 2, 3))),
            "ctx_ok": d == ctx, "valta": valta[j]}


def filtro(b, fn):
    return {"—": np.ones(len(b["t"]), bool), "CTX": b["ctx_ok"], "EUROPA": b["ses"] == 1, "AMERICA": b["ses"] == 2,
            "VBAJA": ~b["valta"], "VALTA": b["valta"]}[fn]


def tasa(res):
    g, pe = int((res > 0).sum()), int((res < 0).sum())
    return (g / (g + pe) * 100 if g + pe else float("nan")), g + pe, int((res == 0).sum())


def libro(t, res, apuesta, pago, desde=None, hasta=None):
    """Saldo apuesta a apuesta (los empates devuelven lo apostado). Devuelve las cifras del cuadro."""
    m = np.ones(len(t), bool)
    if desde:
        m &= t >= desde
    if hasta:
        m &= t < hasta
    t, res = t[m], res[m]
    orden = np.argsort(t, kind="stable")
    t, res = t[orden], res[orden]
    cap = 150000.0
    saldo = maximo = cap
    gan = per = 0.0
    caida = 0.0
    dias = {}
    for ti, r in zip(t, res):
        if saldo <= 0.2 * cap:
            break
        s = apuesta * saldo
        g = s * pago if r > 0 else -s if r < 0 else 0.0
        gan += max(g, 0.0)
        per += max(-g, 0.0)
        saldo += g
        maximo = max(maximo, saldo)
        caida = max(caida, 1 - saldo / maximo)
        dd = int(ti // 86400)
        dias.setdefault(dd, [saldo - g, 0.0])[1] += g
    nd = max(1.0, ((hasta or t[-1]) - (desde or t[0])) / 86400) if len(t) else 1.0
    rd = [v[1] / v[0] for v in dias.values() if v[0] > 0]
    return {"apuestas": int(len(t)), "ingresos": gan, "perdidas": per, "resultado": saldo - cap,
            "margen": (saldo - cap) / gan * 100 if gan else 0.0, "saldo": saldo,
            "crec_dia": ((saldo / cap) ** (1 / nd) - 1) * 100 if saldo > 0 else -100.0, "cop_dia": (saldo - cap) / nd,
            "caida": caida * 100, "peor_dia": min(rd, default=0.0) * 100, "por_dia": len(t) / nd}


def main():
    p("T3 · BINARIAS QUE GANARON EN T2, MEDIDAS COMO LAS PAGA UN BRÓKER (empate = se devuelve) Y CON UN MINUTO DE RETRASO")
    p("acierto sin contar empates · LIBRO = entra al cierre de la vela · REAL = entra un minuto después · A = 2020-23 · B = 2024-26")
    p("para no perder: 55.6 % con pago 0,80 · 54.1 % con 0,85 · 52.6 % con 0,90\n")
    todas, elegida = {}, None
    for fam, (activos, tf, filtros) in FAMILIAS.items():
        partes = [apuestas(a, tf) for a in activos]
        b = {k: np.concatenate([x[k] for x in partes]) for k in partes[0]}
        todas[fam] = b
        for fn in filtros:
            m = filtro(b, fn)
            fila = []
            for res in ("res_l", "res_r"):
                for per in (b["t"] < CORTE, b["t"] >= CORTE):
                    fila.append(tasa(b[res][m & per]))
            (la, na, ea), (lb, nb, eb), (ra, _, _), (rb, _, _) = fila
            p(f"{fam} con {fn:7s}: LIBRO {la:5.2f} % / {lb:5.2f} % · REAL {ra:5.2f} % / {rb:5.2f} % · apuestas {na:,} / {nb:,} · "
              f"empates {(ea + eb) / (na + nb + ea + eb) * 100:.1f} %")
            if na >= 300 and nb >= 300 and (elegida is None or min(ra, rb) > elegida[2]):
                elegida = (fam, fn, min(ra, rb))
    fam, fn, peor = elegida
    b = todas[fam]
    m = filtro(b, fn)
    p(f"\nAGENTE DE BINARIAS ELEGIDO: {fam} con {fn} · acierto REAL en la peor mitad {peor:.2f} %")
    p("\nCUADRO DE MARGEN OPERATIVO · desde 150 mil COP, entrada REAL (un minuto después), toda la historia 2020-2026")
    p("ingresos = lo cobrado en aciertos · pérdidas = lo apostado en fallos · margen operativo = resultado / ingresos\n")
    p(f"{'pago':>5s} {'apuesta':>8s} {'apuestas':>9s} {'por día':>8s} {'ingresos COP':>16s} {'pérdidas COP':>16s} {'resultado COP':>17s} "
      f"{'margen op.':>10s} {'%/día':>8s} {'COP/día':>11s} {'caída máx':>9s} {'peor día':>9s}  2024-26 %/día")
    cuadro = []
    for pago in (0.80, 0.85, 0.90):
        for apuesta in (0.01, 0.02, 0.05, 0.10):
            r = libro(b["t"][m], b["res_r"][m], apuesta, pago)
            rb = libro(b["t"][m], b["res_r"][m], apuesta, pago, desde=CORTE)
            cuadro.append({"pago": pago, "apuesta": apuesta, "todo": r, "B": rb})
            p(f"{pago:5.2f} {apuesta * 100:7.0f} % {r['apuestas']:9,d} {r['por_dia']:8.1f} {r['ingresos']:16,.0f} {r['perdidas']:16,.0f} "
              f"{r['resultado']:+17,.0f} {r['margen']:+9.1f} % {r['crec_dia']:+7.3f} % {r['cop_dia']:+11,.0f} {r['caida']:8.0f} % "
              f"{r['peor_dia']:+8.1f} %  {rb['crec_dia']:+.3f} %")
    # primeros 30 días de 2024-26 desde 150 mil, para que se vea en pesos lo que daría al empezar
    p("\nEn pesos al empezar (primer mes de la prueba 2024, pago 0,85, entrada REAL):")
    for apuesta in (0.02, 0.05):
        r = libro(b["t"][m], b["res_r"][m], apuesta, 0.85, desde=CORTE, hasta=CORTE + 30 * 86400)
        p(f"   apostando el {apuesta * 100:.0f} % del saldo ({apuesta * 150000:,.0f} COP la primera): {r['apuestas']} apuestas, "
          f"150 mil → {r['saldo']:,.0f} COP en 30 días ({r['cop_dia']:+,.0f} COP al día), caída máxima {r['caida']:.0f} %")
    sel = (b["t"] >= b["t"].max() - 92 * 86400) & m
    orden = np.argsort(b["t"][sel])
    rep = [{"a": str(a), "t": int(t), "d": int(d), "res": int(r), "pe": float(pe), "px": float(px)}
           for a, t, d, r, pe, px in zip(b["activo"][sel][orden], b["t"][sel][orden], b["d"][sel][orden], b["res_r"][sel][orden],
                                         b["pe_r"][sel][orden], b["px_r"][sel][orden])]
    with open(os.path.join(AQUI, "t3_replay.json"), "w", encoding="utf-8") as f:
        json.dump({"familia": fam, "preventiva": fn, "vencimiento_min": FAMILIAS[fam][1], "apuestas": rep}, f)
    with open(os.path.join(AQUI, "t3_cuadro.json"), "w", encoding="utf-8") as f:
        json.dump(cuadro, f)
    with open(os.path.join(CONS, "agente_binarias.json"), "w", encoding="utf-8") as f:
        json.dump({"fecha": "2026-10-29", "familia": fam, "preventiva": fn, "activos": FAMILIAS[fam][0], "vela_min": FAMILIAS[fam][1],
                   "vence_min": FAMILIAS[fam][1], "senal": "REV: cuerpo ≥ 2 × media de los 100 previos; apuesta en contra",
                   "capital_cop": 150000, "apuesta": 0.02, "pago": 0.85, "acierto_real_peor_mitad": peor}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
