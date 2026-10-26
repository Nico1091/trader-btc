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


class LecturaInsuficiente(Exception):
    pass


def lectura(arr, gran, minimo, que):
    """Antes de operar: exige al menos `minimo` velas de `gran` segundos, seguidas y sin huecos.
    Si no las hay, no se opera (se lanza LecturaInsuficiente)."""
    n = len(arr)
    huecos = int((np.diff(arr[:, 0]) != gran).sum()) if n > 1 else 0
    print(f"  lectura {que}: {n} velas de {gran // 60 if gran >= 60 else gran} min, huecos {huecos} (mínimo {minimo})")
    if n < minimo or huecos:
        raise LecturaInsuficiente(f"{que}: {n} velas y {huecos} huecos; hacen falta {minimo} seguidas")
    return arr


def niveles(dia):
    d0 = dt.datetime.combine(dia, dt.time(), dt.timezone.utc)
    dd = velas(86400, d0 - dt.timedelta(days=16), d0)
    dd = lectura(dd[dd[:, 0] < d0.timestamp()][-15:], 86400, 15, "diarias para el ATR14")
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
    h = velas(3600, t_senal - dt.timedelta(hours=72), t_senal)
    h = lectura(h[h[:, 0] + 3600 <= t_senal.timestamp()], 3600, 60, "de 1 h para los patrones")  # solo velas cerradas
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
    lectura(m, 60, 1440, "de 1 min del día (para cerrar)")
    t, lo, hi, op, cl = m[:, 0], m[:, 1], m[:, 2], m[:, 3], m[:, 4]
    print(f"{dia}: apertura {ap:,.2f}, ATR14 {atr:,.2f}, minutos {len(m)}")
    res = []
    # PP-1 (P11 / N1): largo en la apertura, stop 3 %, cierre 23:59 UTC. Solo lunes.
    if dia.weekday() == 0:
        st = ap * 0.97
        k = np.flatnonzero(lo <= st)
        px, mot = (st, "stop") if len(k) else (cl[-1], "tiempo")
        res.append(("PP-1 P11", 1, ap, px, mot, 0.05, 0.05))
    c15 = cl[14::15]
    t15 = t[14::15] + 60
    # PP-1f: PP-1 solo si el cierre diario de ayer está sobre su SMA 50 (consolidación, tarea 8)
    if dia.weekday() == 0:
        dd = velas(86400, d0 - dt.timedelta(days=60), d0)
        dd = lectura(dd[dd[:, 0] < d0.timestamp()][-50:], 86400, 50, "diarias para la SMA 50")
        sma = dd[:, 4].mean()
        print(f"PP-1f: cierre de ayer {dd[-1, 4]:,.2f} vs SMA 50 {sma:,.2f} -> "
              + ("opera igual que PP-1" if dd[-1, 4] > sma else "NO opera (tendencia diaria en contra)"))
    # PP-6: P05b k = 0,5 solo largo, confirmado por un patrón alcista en las 3 últimas velas de 1 h cerradas
    up6 = ap + 0.5 * atr
    j6 = next((i for i, x in enumerate(c15[:95]) if x > up6 or x < ap - 0.5 * atr), None)
    if j6 is None or c15[j6] < up6:
        print("PP-6 P05b largo confirmado: sin señal larga" + ("" if j6 is None else " (la primera señal fue corta)"))
    else:
        ts6 = dt.datetime.fromtimestamp(t15[j6], dt.timezone.utc)
        if not veto_1h(ts6, -1):  # veto_1h(t, -1) devuelve los patrones ALCISTAS de las 3 últimas velas de 1 h
            print(f"PP-6 P05b largo confirmado: señal a las {ts6:%H:%M} sin vela alcista de 1 h -> no opera")
        else:
            i0 = int(np.searchsorted(t, t15[j6]))
            f6 = next((i for i in range(i0, min(i0 + 60, len(t))) if lo[i] < up6), None)
            if f6 is None:
                print(f"PP-6: señal a las {ts6:%H:%M} sin llenar en 60 min")
            else:
                px, mot = cl[-1], "tiempo"
                for i in range(len(c15)):
                    if t15[i] > t[f6] + 60 and c15[i] <= ap:
                        px, mot = c15[i], "stop"; break
                res.append(("PP-6 P05b largo confirmado", 1, up6, px, mot, 0.02, 0.05))
    # PP-7: P05b k = 0,5 por régimen (tarea 10). Con el cierre de ayer bajo la SMA 50 solo vale el corto y con el cierre
    # sobre ella, solo el largo. Escrita el 26/10 a las 14:30 UTC: el lunes solo cuentan señales posteriores a esa hora.
    dd7 = velas(86400, d0 - dt.timedelta(days=60), d0)
    dd7 = lectura(dd7[dd7[:, 0] < d0.timestamp()][-50:], 86400, 50, "diarias para el régimen de PP-7")
    lado7 = 1 if dd7[-1, 4] > dd7[:, 4].mean() else -1
    desde7 = (d0 + dt.timedelta(hours=14, minutes=30)).timestamp() if str(dia) == "2026-10-26" else d0.timestamp()
    nivel7 = ap + 0.5 * atr if lado7 > 0 else ap - 0.5 * atr
    j7 = next((i for i, x in enumerate(c15[:95]) if t15[i] > desde7 and ((lado7 > 0 and x > nivel7) or (lado7 < 0 and x < nivel7))), None)
    if j7 is None:
        print(f"PP-7 P05b por régimen ({'largo' if lado7 > 0 else 'corto'}, nivel {nivel7:,.2f}): sin señal")
    else:
        i0 = int(np.searchsorted(t, t15[j7]))
        f7 = next((i for i in range(i0, min(i0 + 60, len(t))) if (lado7 > 0 and lo[i] < nivel7) or (lado7 < 0 and hi[i] > nivel7)), None)
        if f7 is None:
            print("PP-7: señal sin llenar en 60 min")
        else:
            px, mot = cl[-1], "tiempo"
            for i in range(len(c15)):
                if t15[i] > t[f7] + 60 and ((lado7 > 0 and c15[i] <= ap) or (lado7 < 0 and c15[i] >= ap)):
                    px, mot = c15[i], "stop"; break
            res.append(("PP-7 P05b por régimen", lado7, nivel7, px, mot, 0.02, 0.05))
    # PP-2 (P05b + veto 1h) y PP-3 (P05c largo): primer cierre de 15 m fuera de la banda hasta las 23:45
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
        try:
            cerrar(dia)
        except LecturaInsuficiente as e:
            print("NO SE OPERA NI SE CIERRA: lectura insuficiente ->", e)
