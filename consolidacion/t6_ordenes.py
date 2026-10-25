"""Tarea 6: prueba propia en papel para el lunes 26 y el martes 27 de octubre de 2026.

Uso:
  python3 -I t6_ordenes.py niveles 2026-10-26   -> calcula la apertura 00:00 UTC, el ATR14 y las bandas
  python3 -I t6_ordenes.py cerrar  2026-10-26   -> cierra las órdenes de ese día con velas de 1 minuto

Referencia de precio: Coinbase BTC-USD (la API de Binance da 451 desde la nube). ATR14: velas diarias de
Coinbase de los 14 días previos. Reglas escritas en ORDENES-PRUEBA-PROPIA.md antes del resultado."""
import json, sys, urllib.request, datetime as dt
import numpy as np

API = "https://api.exchange.coinbase.com/products/BTC-USD/candles"


def velas(gran, ini, fin):
    out, t = [], ini
    paso = dt.timedelta(seconds=gran * 300)
    while t < fin:
        u = f"{API}?granularity={gran}&start={t:%Y-%m-%dT%H:%M:%SZ}&end={min(t + paso, fin):%Y-%m-%dT%H:%M:%SZ}"
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "papel"}), timeout=30)
        out += json.loads(r.read())
        t += paso
    d = {}
    for x in out:
        d[x[0]] = x  # [t, low, high, open, close, vol]
    return np.array([d[k] for k in sorted(d)], float)


def niveles(dia):
    d0 = dt.datetime.combine(dia, dt.time(), dt.timezone.utc)
    dd = velas(86400, d0 - dt.timedelta(days=16), d0)
    dd = dd[dd[:, 0] < d0.timestamp()][-15:]
    h, l, c = dd[:, 2], dd[:, 1], dd[:, 4]
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    atr = tr[-14:].mean()
    m = velas(60, d0, d0 + dt.timedelta(minutes=5))
    ap = m[0, 3]
    return ap, atr


def veto_1h(t_senal, lado):
    """Veto de la tarea 3: patrón de vela de 1 h de lado contrario en las 3 últimas velas cerradas."""
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    import pandas as pd
    from lib import patrones
    h = velas(3600, t_senal - dt.timedelta(hours=40), t_senal)
    df = pd.DataFrame(h[:, [3, 2, 1, 4]], columns=list("ohlc"))
    pat, lado_p = patrones(df)
    ult = pat.iloc[-3:]
    contr = [k for k, s in lado_p.items() if s == -lado and ult[k].any()]
    return contr


def cerrar(dia):
    ap, atr = niveles(dia)
    d0 = dt.datetime.combine(dia, dt.time(), dt.timezone.utc)
    m = velas(60, d0, d0 + dt.timedelta(days=1))
    m = m[m[:, 0] < (d0 + dt.timedelta(days=1)).timestamp()]
    t, lo, hi, op, cl = m[:, 0], m[:, 1], m[:, 2], m[:, 3], m[:, 4]
    print(f"{dia}: apertura {ap:,.2f}, ATR14 {atr:,.2f}, minutos {len(m)}")
    res = []
    # PP-1 (P11 / N1): largo en la apertura, stop 3 %, cierre 23:59 UTC. Solo lunes.
    if dia.weekday() == 0:
        st = ap * 0.97
        k = np.flatnonzero(lo <= st)
        px, mot = (st, "stop") if len(k) else (cl[-1], "tiempo")
        res.append(("PP-1 P11", 1, ap, px, mot, 0.05, 0.05))
    # PP-2 (P05b + veto 1h) y PP-3 (P05c largo): primer cierre de 15 m fuera de la banda hasta las 23:45
    c15 = cl[14::15]
    t15 = t[14::15] + 60
    for nombre, kk, solo_largo, veto in (("PP-2 P05b+veto", 0.5, False, True), ("PP-3 P05c largo", 1.0, True, False)):
        up, dn = ap + kk * atr, ap - kk * atr
        j = next((i for i, x in enumerate(c15[:95]) if x > up or (x < dn and not solo_largo) or (solo_largo and x < dn)), None)
        if j is None:
            print(f"{nombre}: sin señal (banda {dn:,.2f} - {up:,.2f})"); continue
        lado = 1 if c15[j] > up else -1
        if solo_largo and lado < 0:
            print(f"{nombre}: primera señal corta; la versión solo largo no opera"); continue
        ts = dt.datetime.fromtimestamp(t15[j], dt.timezone.utc)
        if veto:
            contr = veto_1h(ts, lado)
            if contr:
                print(f"{nombre}: señal {'larga' if lado > 0 else 'corta'} a las {ts:%H:%M} VETADA por {contr}"); continue
        nivel = up if lado > 0 else dn
        i0 = int(np.searchsorted(t, t15[j]))
        ventana = range(i0, min(i0 + 60, len(t)))
        f = next((i for i in ventana if (lado > 0 and lo[i] < nivel) or (lado < 0 and hi[i] > nivel)), None)
        if f is None:
            print(f"{nombre}: señal a las {ts:%H:%M} sin llenar en 60 min"); continue
        px, mot = cl[-1], "tiempo"
        for i in range(len(c15)):
            if t15[i] > t[f] + 60 and ((lado > 0 and c15[i] <= ap) or (lado < 0 and c15[i] >= ap)):
                px, mot = c15[i], "stop"; break
        res.append((nombre, lado, nivel, px, mot, 0.02, 0.05))
    # Testigo al azar sorteado el 25/10 16:20 UTC (ORDENES-PRUEBA-PROPIA.md): hora y lado; stop 3 %, cierre 23:59
    azar = {"2026-10-26": ("AZ-P1", 15 * 60 + 41, -1), "2026-10-27": ("AZ-P2", 11 * 60 + 15, 1)}
    if str(dia) in azar:
        nombre, minuto, lado = azar[str(dia)]
        pe = op[minuto]
        st = pe * (1 - lado * 0.03)
        k = np.flatnonzero(lo[minuto:] <= st) if lado > 0 else np.flatnonzero(hi[minuto:] >= st)
        px, mot = (st, "stop") if len(k) else (cl[-1], "tiempo")
        res.append((nombre, lado, pe, px, mot, 0.05, 0.05))
    for nombre, lado, pe, px, mot, ce, cs in res:
        b = lado * (px / pe - 1) * 100
        print(f"{nombre}: {'LARGO' if lado > 0 else 'CORTO'} {pe:,.2f} -> {px:,.2f} ({mot}) bruto {b:+.3f} % "
              f"neto {b - ce - cs:+.3f} % (contado 0,10/lado: {b - 0.20:+.3f} %)")


if __name__ == "__main__":
    accion, dia = sys.argv[1], dt.date.fromisoformat(sys.argv[2])
    if accion == "niveles":
        ap, atr = niveles(dia)
        print(f"apertura {ap:,.2f} ATR14 {atr:,.2f}; P05b {ap - 0.5 * atr:,.2f} / {ap + 0.5 * atr:,.2f}; "
              f"P05c {ap - atr:,.2f} / {ap + atr:,.2f}; stop P11 {ap * 0.97:,.2f}")
    else:
        cerrar(dia)
