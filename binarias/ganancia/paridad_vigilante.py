# -*- coding: utf-8 -*-
"""Paridad del plan v9 con la vigilante (criterio A2, 20/11/2026): el estado de dinero que calcula el nodo para cada fuente
frente a la decisión del medidor de la vigilante (vigilante/medidor_ganancia.py), con los mismos datos reales.

Uso: python -I paridad_vigilante.py <dinero.json> [carpeta del registro del operador] [ganancia.json]
- dinero.json: la libreta del nodo (en el teléfono, home/nodo/dinero.json).
- registro: si la libreta todavía no trae el papel del operador (antes del plan v9), se toma de aquí.
- ganancia.json: si se da, se comprueba además que lo escrito por el nodo coincide con lo calculado aquí.
Solo lee. Sale con 0 si todo coincide."""
import glob
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
# el nodo de al lado (la copia que se prueba) manda sobre el del equipo; el medidor de la vigilante, en su carpeta
NODO = next((d for d in (os.path.join(AQUI, "..", "nodo"), os.path.join(os.path.expanduser("~"), "nodo"))
             if os.path.exists(os.path.join(d, "nodo.py"))), None)
sys.path.insert(0, os.path.join(AQUI, "vigilante"))
if NODO:
    sys.path.insert(0, NODO)
import nodo as N  # noqa: E402
import medidor_ganancia as V  # noqa: E402


def papel_operador(carpeta):
    llen, gan = {}, {}
    for f in sorted(glob.glob(os.path.join(carpeta, "*.jsonl"))):
        for linea in open(f, encoding="utf-8"):
            try:
                r = json.loads(linea)
            except ValueError:
                continue
            if r.get("tipo") == "llenado" and r.get("compra") and not r.get("sombra") and r.get("llenado") == 5 \
                    and r.get("lado") in (1, -1):
                llen.setdefault((r["W"], int(r["t"]), r["lado"]), r)
            elif r.get("tipo") == "resultado" and r.get("serie", "papel") == "papel" and r.get("ganador") in (1, -1, 0):
                gan[(r["W"], int(r["t"]))] = r["ganador"]
    out = {}
    for (W, t, lado), r in sorted(llen.items(), key=lambda kv: kv[0][1]):
        g = gan.get((W, t))
        if g in (1, -1, 0) and N._real(r.get("q")):
            out.setdefault(f"operador|operador{W}", []).append({"t": t, "dir": lado, "v": t, "q": r["q"], "g": g, "W": W})
    return out


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    libreta = (N.leer_json(argv[0], {}) or {}).get("estrategias") or {}
    if len(argv) > 1 and os.path.isdir(argv[1]):
        for k, v in papel_operador(argv[1]).items():
            libreta.setdefault(k, v)
    escrito = N.leer_json(argv[2], None) if len(argv) > 2 else None
    bien = True
    print(f"{'fuente':22s} {'n':>4s} {'neto':>8s} {'prueba':>9s}  {'nodo (regla de la vigilante)':30s} {'vigilante':30s} estado v9")
    for k in sorted(libreta):
        W = N.MERCADO_FUENTE.get(k, 15)
        d = N.ganancia_de(libreta[k], W)
        pares = []
        for _v, r, _a, _c, q in N.retornos(libreta[k], W):
            pares.append((min(max(q, 0.01), 0.99), 1 if r > 0 else 0))
        v = V.evaluar(pares, k=N.K_FUENTES, alfa=N.ALFA, minimo=N.MINIMO) if pares else {"decision": V.ETIQUETAS["poca"]}
        igual = d["regla_vigilante"] == v["decision"]
        bien &= igual
        if escrito is not None:
            e = (escrito.get("fuentes") or {}).get(k)
            mismo = bool(e) and e.get("estado") == d["estado"] and e.get("n") == d["n"] and abs((e.get("neto") or 0) - d["neto"]) < 1e-6
            bien &= mismo
        print(f"{k:22s} {d['n']:4d} {d['neto']:+8.2f} {d['prueba']:9.4f}  {d['regla_vigilante']:30s} {v['decision']:30s} "
              f"{d['estado']}{'' if igual else '  ← DISTINTO'}"
              + ("" if escrito is None else ("  (ganancia.json igual)" if mismo else "  ← ganancia.json DISTINTO")))
    dem = [k for k in libreta if N.ganancia_de(libreta[k], N.MERCADO_FUENTE.get(k, 15))["alto"]]
    print("Demuestran ganancia de dinero:", ", ".join(dem) if dem else "ninguna")
    print("PARIDAD BIEN" if bien else "PARIDAD CON DIFERENCIAS")
    return 0 if bien else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
