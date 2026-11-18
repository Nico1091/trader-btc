# -*- coding: utf-8 -*-
"""Análisis de paridad (18/11/2026): cuánto dinero separa a la rutina de la apuesta manual. Plan: 3-PLAN-ANALISIS.md.

Uso:  python -I analisis_paridad.py CARPETA
CARPETA tiene lo copiado del teléfono: los registros diarios del operador (*registro*.jsonl o registro/*.jsonl), el Centro
(*centro.json) y el vigía (*quince.json). Solo lee; el informe sale por la salida estándar. Solo biblioteca estándar; las
sumas van en bucle (en 3.12 sum() cambió su manera de sumar flotantes)."""
import glob
import json
import os
import sys
import time

PAGO = 0.98           # el acierto paga 1 por contrato menos el 2 % de comisión (lo mismo que la app: «Ganar» = 0,98 / precio)
PRECIO_NODO = 0.544   # el precio que el nodo supone hoy para las señales sin precio (nodo.py:101)


def hc(t):
    return time.strftime("%d/%m %H:%M", time.gmtime(t - 5 * 3600))


def leer_json(r, defecto=None):
    try:
        with open(r, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def suma(xs):
    s = 0.0
    for x in xs:
        s += x
    return s


def media(xs):
    xs = list(xs)
    return suma(xs) / len(xs) if xs else None


def neto(q, ganador, lado):
    """Neto por USDT comprando `lado` a `q`: lo mismo que haría usted con el botón."""
    if ganador == lado:
        return PAGO / q - 1
    if ganador == 0:
        return PAGO / 2 / q - 1
    return -1.0


def neto_nodo(res):
    """La cuenta de hoy del nodo: 0,544 fijo y el resultado propio de la estrategia (empate = medio pago)."""
    if res == 1:
        return PAGO / PRECIO_NODO - 1
    if res == 0.5:
        return PAGO / 2 / PRECIO_NODO - 1
    return -1.0


def leer_registros(carpeta):
    rutas = sorted(set(glob.glob(os.path.join(carpeta, "*registro*.jsonl")) + glob.glob(os.path.join(carpeta, "registro", "*.jsonl"))))
    precios, ganador, llenados = {}, {}, []
    for r in rutas:
        with open(r, encoding="utf-8") as f:
            for linea in f:
                try:
                    x = json.loads(linea)
                except ValueError:
                    continue
                tipo = x.get("tipo")
                if tipo == "mirada":
                    L = x.get("lados") or {}
                    a, b = L.get("1") or {}, L.get("-1") or {}
                    nuevo = {"h": x.get("hora"), "serie": x.get("serie"), 1: a.get("q"), -1: b.get("q"),
                             "p1": a.get("p"), "p-1": b.get("p"), "resta": x.get("resta_s")}
                    d = precios.setdefault((x.get("W"), x.get("t")), {})
                    viejo = d.get(x.get("m"))
                    if not viejo or viejo["serie"] != "papel" or nuevo["serie"] == "papel":
                        d[x.get("m")] = nuevo
                elif tipo == "resultado":
                    k, g = (x.get("W"), x.get("t")), x.get("ganador")
                    if g in (1, -1, 0) and (x.get("fuente") == "oficial" or k not in ganador):
                        ganador[k] = g
                elif tipo == "llenado" and x.get("compra") and not x.get("sombra") and x.get("lado") in (1, -1):
                    llenados.append(x)
    return rutas, precios, ganador, llenados


def leer_senales(carpeta):
    out = []
    for r in glob.glob(os.path.join(carpeta, "*centro.json")):
        for e, ops in sorted(((leer_json(r, {}) or {}).get("ops") or {}).items()):
            for o in ops:
                out.append(("centro", e, o))
    for r in glob.glob(os.path.join(carpeta, "*quince.json")):
        for o in (leer_json(r, {}) or {}).get("ops") or []:
            out.append(("quince", "quince", o))
    return out


def lado_precio(P, lado, estimar=None):
    """(precio, tipo): el real del libro; si no hay y se pide, el estimado con el modelo; si no, (None, None)."""
    if not P:
        return None, None
    q = P.get(lado)
    if P.get("serie") == "papel" and isinstance(q, (int, float)) and 0 < q < 1:
        return float(q), "real"
    p = P.get("p1" if lado == 1 else "p-1")
    if estimar and isinstance(p, (int, float)):
        return min(0.99, max(0.01, p + estimar(p))), "estimado"
    return None, None


def cruzar(senales, precios, ganador, estimar=None):
    filas = []
    for fuente, est, o in senales:
        t, d, res = o.get("t"), o.get("dir"), o.get("res")
        if not isinstance(t, int) or d not in (1, -1) or res not in (0, 1, 0.5):
            continue
        v = t - t % 900
        m_sig = (t - v) // 60
        g = ganador.get((15, v))
        if g is None:
            continue
        # el Centro entra 60 s tarde (la misma demora que la rutina): el minuto de la señal más uno; si esa mirada se perdió,
        # el siguiente (la misma regla que la Libreta del nodo)
        q = tipo = None
        for m_e in (m_sig + 1, m_sig + 2):
            q, tipo = lado_precio(precios.get((15, v), {}).get(m_e), d)
            if q is None and estimar:
                q, tipo = lado_precio(precios.get((15, v), {}).get(m_e), d, estimar)
            if q is not None:
                break
        if q is None:
            continue
        q_ya, _ = lado_precio(precios.get((15, v), {}).get(m_sig), d) if m_sig >= 1 else (None, None)
        filas.append({"fuente": fuente, "est": est, "t": t, "dir": d, "m_sig": m_sig, "m_e": m_e, "q": q, "tipo": tipo,
                      "q_ya": q_ya, "res": res, "g": g, "gana_mercado": 1 if g == d else 0,
                      "coincide": (1 if (res == 1) == (g == d) else 0), "n_nodo": neto_nodo(res), "n_manual": neto(q, g, d),
                      "n_ya": neto(q_ya, g, d) if q_ya else None, "alineada": m_sig == 0, "semilla": bool(o.get("semilla"))})
    return filas


def informe_a1(filas, titulo):
    print(f"\n== {titulo}: {len(filas)} señales con precio y ganador oficial")
    if not filas:
        return
    grupos = {}
    for f in filas:
        grupos.setdefault(f["est"], []).append(f)
    grupos["TODAS"] = filas
    for est, fs in sorted(grupos.items(), key=lambda kv: (kv[0] == "TODAS", kv[0])):
        n = len(fs)
        al = [f for f in fs if f["alineada"]]
        print(f"{est:7s} n={n:3d} (alineadas {len(al)}) · acierto propio {suma(f['res'] == 1 for f in fs) / n:.0%} · "
              f"acierto en el mercado {suma(f['gana_mercado'] for f in fs) / n:.0%} · coinciden {suma(f['coincide'] for f in fs) / n:.0%} · "
              f"lado barato {suma(f['q'] < 0.5 for f in fs) / n:.0%} · precio medio {media(f['q'] for f in fs):.3f}")
        print(f"        neto por USDT: cuenta del nodo {suma(f['n_nodo'] for f in fs):+.2f} ({media(f['n_nodo'] for f in fs):+.3f} por señal) · "
              f"cuenta manual {suma(f['n_manual'] for f in fs):+.2f} ({media(f['n_manual'] for f in fs):+.3f} por señal) · "
              f"distinto signo en {int(suma((f['n_nodo'] > 0) != (f['n_manual'] > 0) for f in fs))} de {n}")
        if al:
            na = [f for f in fs if not f["alineada"]]
            print(f"        coinciden: alineadas {suma(f['coincide'] for f in al) / len(al):.0%}"
                  + (f", a mitad de ventana {suma(f['coincide'] for f in na) / len(na):.0%}" if na else ""))
        ya = [f for f in fs if f["n_ya"] is not None]
        if ya:
            print(f"        a mitad de ventana, comprar al dar la señal frente a 60 s después: {suma(f['n_ya'] for f in ya):+.2f} "
                  f"frente a {suma(f['n_manual'] for f in ya):+.2f} ({len(ya)} señales)")


def detalle(filas):
    print("\nDetalle (hora de Colombia · estrategia · lado · minuto de entrada · precio · acierto propio · ganador · neto nodo · neto manual):")
    for f in sorted(filas, key=lambda f: f["t"]):
        print(f"  {hc(f['t'])} {f['est']:6s} {'SUBE' if f['dir'] == 1 else 'BAJA'} m{f['m_e']:<2d} {f['q']:.2f}{'*' if f['tipo'] == 'estimado' else ' '} "
              f"propio {'sí' if f['res'] == 1 else 'no'} · mercado {'SUBE' if f['g'] == 1 else ('BAJA' if f['g'] == -1 else 'empate')} · "
              f"{f['n_nodo']:+.2f} · {f['n_manual']:+.2f}")


def a2_demora(precios, ganador):
    print("\n== A2, costo de un minuto de demora (lado que terminó ganando frente al que perdió)")
    por = {}
    for (W, t), ms in precios.items():
        g = ganador.get((W, t))
        if g not in (1, -1):
            continue
        for m in sorted(ms):
            a, b = ms.get(m), ms.get(m + 1)
            if not a or not b or a["serie"] != "papel" or b["serie"] != "papel":
                continue
            for lado in (1, -1):
                q0, q1 = a.get(lado), b.get(lado)
                if not (isinstance(q0, (int, float)) and isinstance(q1, (int, float)) and 0 < q0 < 1 and 0 < q1 < 1):
                    continue
                falta = W - m
                tramo = "faltan 1-2 min" if falta <= 2 else ("faltan 3-5 min" if falta <= 5 else "faltan 6-14 min")
                for k in ((W, "todos"), (W, tramo)):
                    por.setdefault(k, {"gana": [], "pierde": [], "pago": []})
                    por[k]["gana" if lado == g else "pierde"].append(q1 - q0)
                    if lado == g:
                        por[k]["pago"].append(PAGO / q0 - PAGO / q1)
    for k in sorted(por, key=lambda k: (k[0], k[1] != "todos", k[1])):
        x = por[k]
        absd = [abs(d) for d in x["gana"] + x["pierde"]]
        print(f"  {k[0]:2d} min · {k[1]:15s} · pares {len(x['gana']):3d} · el que gana sube {media(x['gana']):+.3f} · "
              f"el que pierde {media(x['pierde']):+.3f} · |cambio| medio {media(absd):.3f}, más de 0,05 en {suma(d > 0.05 for d in absd) / len(absd):.0%}, "
              f"más de 0,10 en {suma(d > 0.10 for d in absd) / len(absd):.0%} · pago perdido por USDT del que gana {media(x['pago']):+.3f}")


def a3_calibracion(precios):
    print("\n== A3, precio real de compra frente a la probabilidad del modelo del operador")
    tramos = ((0, 0.1), (0.1, 0.3), (0.3, 0.7), (0.7, 0.9), (0.9, 1.01))
    difs = {tr: [] for tr in tramos}
    todas = []
    for ms in precios.values():
        for P in ms.values():
            if P["serie"] != "papel":
                continue
            for lado, clave in ((1, "p1"), (-1, "p-1")):
                q, p = P.get(lado), P.get(clave)
                if isinstance(q, (int, float)) and isinstance(p, (int, float)) and 0 < q < 1:
                    todas.append(q - p)
                    for tr in tramos:
                        if tr[0] <= p < tr[1]:
                            difs[tr].append(q - p)
    if not todas:
        print("  sin miradas con libro")
        return None, None
    mae = media(abs(d) for d in todas)
    print(f"  {len(todas)} lados · diferencia media {media(todas):+.3f} · error medio absoluto {mae:.3f}")
    medias = {}
    for tr, ds in difs.items():
        if ds:
            medias[tr] = media(ds)
            print(f"  probabilidad {tr[0]:.1f}-{min(tr[1], 1):.1f}: {len(ds):4d} lados · diferencia media {medias[tr]:+.3f} · "
                  f"error medio absoluto {media(abs(d) for d in ds):.3f}")

    def estimar(p):
        for tr, mm in medias.items():
            if tr[0] <= p < tr[1]:
                return mm
        return media(todas)
    return mae, estimar


def a4_papel(llenados, ganador):
    print("\n== A4, compras de papel del operador con el ganador oficial")
    por = {}
    for x in llenados:
        g = ganador.get((x["W"], x["t"]))
        q = x.get("q")
        if g is None or not isinstance(q, (int, float)) or not 0 < q < 1:
            continue
        por.setdefault((x["W"], x.get("llenado")), []).append((neto(q, g, x["lado"]), g == x["lado"], q))
    for k in sorted(por):
        v = por[k]
        print(f"  {k[0]:2d} min, llenado a {k[1]} s: {len(v)} compras · aciertos {int(suma(a for _, a, _ in v))} · precio medio {media(q for _, _, q in v):.3f} · "
              f"neto {suma(n for n, _, _ in v):+.2f} por USDT ({media(n for n, _, _ in v):+.3f} por compra)")


def a5_equilibrio(filas):
    qs = sorted(f["q"] for f in filas if f["fuente"] == "centro")
    if not qs:
        return
    def cuantil(c):
        return qs[min(len(qs) - 1, int(c * len(qs)))]
    print(f"\n== A5, precio de entrada de las señales del Centro con libro real ({len(qs)}): mediana {cuantil(0.5):.2f}, "
          f"10 % {cuantil(0.1):.2f}, 90 % {cuantil(0.9):.2f}; acierto mínimo para no perder {cuantil(0.5) / PAGO:.1%} en la mediana "
          f"(la rutina de la nube supuso 54,05 % fijo)")


def main(carpeta):
    rutas, precios, ganador, llenados = leer_registros(carpeta)
    senales = leer_senales(carpeta)
    con_libro = [P["h"] for ms in precios.values() for P in ms.values() if P["serie"] == "papel" and P.get("h")]
    print(f"Registros: {', '.join(os.path.basename(r) for r in rutas)} · mercados {len(precios)} · ganadores {len(ganador)} · "
          f"señales {len(senales)} · libro real de {hc(min(con_libro)) if con_libro else '—'} a {hc(max(con_libro)) if con_libro else '—'}")
    filas = cruzar(senales, precios, ganador)
    informe_a1(filas, "A1, cuenta del nodo frente a cuenta manual (solo libro real)")
    detalle(filas)
    a2_demora(precios, ganador)
    mae, estimar = a3_calibracion(precios)
    if mae is not None and mae <= 0.05:
        largas = cruzar(senales, precios, ganador, estimar)
        informe_a1(largas, "A3, muestra larga (precio real o estimado con el modelo, marcado con *)")
    elif mae is not None:
        print(f"  error medio absoluto {mae:.3f} > 0,05: no se amplía la muestra con precios estimados (criterio A3)")
    a4_papel(llenados, ganador)
    a5_equilibrio(filas)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
