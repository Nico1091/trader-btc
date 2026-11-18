# -*- coding: utf-8 -*-
"""Papel de la combinación frente a cada fuente sola (17/11/2026). Solo lee archivos; no compra, no llama a nadie, sin IA.

Pedido del dueño (rutina constructora, sección G): «deje cómo medir en papel la combinación contra cada uno por separado».
Todo se juzga con el ganador del mercado de Binance de esa ventana y con el precio real del libro que el operador leyó en su
mirada. Desde el 18/11/2026 (paridad con la apuesta a mano) nunca se supone un precio: lo que no tiene libro no se cuenta y
se informa aparte como «sin precio real». Neto por cada USDT puesto: acierto 0,98 / q − 1, empate 0,49 / q − 1, fallo −1.

  A. Cada estrategia del Centro sola (E1 a E5), sus señales vivas que caen en la apertura de un mercado de 15 min, compradas
     en la primera mirada del operador (minuto 1).
  B. El operador de Fable 5.2 solo: sus compras de papel (libro A, llenado honesto de 5 s), por mercado.
  C. Claude solo: cada «COMPRAR» del nodo, comprado en la primera mirada del operador después de la decisión.
  D. La combinación, que es lo que haría el real: una mirada del operador que quiere comprar un lado (su ganancia esperada
     prudente llega al margen) mientras hay un «COMPRAR» vigente de Claude para ese mercado y sentido; la primera de cada
     ventana. También cuenta las que el candado paró.
  E. Las órdenes reales ya liquidadas, si las hay.

Uso en el teléfono: python3 -I medir_combinacion.py [--dias 14] [--nodo ~/nodo] [--operador ~/operador] [--centinela ~/centinela]
Lo que la combinación debe mostrar antes de pensar en dinero: más aciertos que el equilibrio de su propio precio y neto
positivo con muestra grande, mejor que cada fuente sola. Mientras el operador no tenga una llave que lea, no hay precios
reales y no se mide nada: todo queda como «sin precio real»."""
import json
import os
import sys
import time

HOME = os.path.expanduser("~")
CADUCIDAD_S = 120          # lo mismo que operador/aprobacion.py (era 600)
UTILES = (b'"tipo": "mirada"', b'"tipo": "llenado"', b'"tipo": "resultado"', b'"tipo": "liquidaci')


def arg(nombre, defecto):
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else defecto


def neto(g, lado, q):
    if g is None:
        return None
    if g == 0:
        return 0.49 / q - 1
    return 0.98 / q - 1 if g == lado else -1.0


def leer_registro(carpeta, desde):
    ganador, miradas, llenados, reales = {}, {}, {}, []
    try:
        nombres = sorted(n for n in os.listdir(carpeta) if n.endswith(".jsonl"))
    except OSError:
        nombres = []
    for n in nombres:
        with open(os.path.join(carpeta, n), "rb") as f:
            for linea in f:
                if not any(u in linea for u in UTILES):
                    continue
                try:
                    r = json.loads(linea)
                except ValueError:
                    continue
                W, t, tipo = r.get("W"), r.get("t"), r.get("tipo")
                if W not in (5, 15) or not isinstance(t, (int, float)) or t < desde:
                    continue
                k = (W, int(t))
                if tipo == "resultado" and r.get("ganador") in (1, -1, 0):
                    if r.get("serie", "papel") == "papel" or k not in ganador:      # el oficial manda sobre las velas
                        ganador[k] = r["ganador"]
                elif tipo == "mirada":
                    lados = r.get("lados") or {}
                    miradas.setdefault(k, []).append({"m": r.get("m"), "hora": r.get("hora") or 0, "serie": r.get("serie"),
                                                      "decide": r.get("decide") or 0,
                                                      "q": {1: (lados.get("1") or {}).get("q"), -1: (lados.get("-1") or {}).get("q")}})
                elif tipo == "llenado" and r.get("compra") and not r.get("sombra") and r.get("llenado") == 5:
                    llenados.setdefault((W, int(t), r.get("lado")), r.get("q"))
                elif tipo == "liquidación" and r.get("res") in (0, 1, 2):
                    reales.append(r)
    for v in miradas.values():
        v.sort(key=lambda x: x["hora"])
    return ganador, miradas, llenados, reales


class Cuenta:
    def __init__(self, nombre, por_usdt=True):
        self.nombre, self.n, self.k, self.neto, self.reales, self.sin_ganador = nombre, 0, 0, 0.0, 0, 0
        self.sin_precio = 0
        self.por_usdt = por_usdt

    def sumar(self, g, lado, q, real):
        if not q or not real:          # sin precio real del libro no se cuenta: nunca se supone un precio
            self.sin_precio += 1
            return
        x = neto(g, lado, q)
        if x is None:
            self.sin_ganador += 1
            return
        self.n += 1
        self.k += 1 if g == lado else 0
        self.neto += x
        self.reales += 1 if real else 0

    def linea(self):
        sin = f"; sin precio real (no cuentan): {self.sin_precio}" if self.sin_precio else ""
        if not self.n:
            return (f"{self.nombre}: sin compras medidas" + (f" ({self.sin_ganador} sin ganador todavía)" if self.sin_ganador else "")
                    + sin)
        if not self.por_usdt:
            return (f"{self.nombre}: {self.n}, {self.k} aciertos ({100 * self.k / self.n:.1f} %), neto real {self.neto:+.2f} USDT"
                    ).replace(".", ",")
        return (f"{self.nombre}: {self.n} compras, {self.k} aciertos ({100 * self.k / self.n:.1f} %), neto {self.neto:+.2f} USDT "
                f"por 1 USDT cada una ({self.neto / self.n:+.3f} por compra); todas con precio real" + sin).replace(".", ",")


def precio(mir, lado, desde_hora=None):
    """El precio real del lado en la primera mirada (o la primera después de una hora dada), y si era real. Sin libro en esa
    mirada: (None, False), y la compra no se cuenta."""
    for x in mir or []:
        if desde_hora is not None and x["hora"] < desde_hora:
            continue
        q = x["q"].get(lado)
        if q:
            return q, True
        return None, False
    return None, False


def medir(dias=14, nodo=None, operador=None, centinela=None, ahora=None):
    ahora = ahora or time.time()
    desde = ahora - dias * 86400
    nodo = nodo or os.path.join(HOME, "nodo")
    operador = operador or os.path.join(HOME, "operador")
    centinela = centinela or os.path.join(HOME, "centinela")
    ganador, miradas, llenados, reales = leer_registro(os.path.join(operador, "registro"), desde)
    cuentas = []
    # A. el Centro, estrategia por estrategia
    try:
        with open(os.path.join(centinela, "datos", "centro.json"), encoding="utf-8") as f:
            cen = json.load(f).get("ops") or {}
    except (OSError, ValueError):
        cen = {}
    for e in sorted(cen):
        c = Cuenta(f"A. {e} sola")
        for o in cen[e]:
            t = int(o.get("t") or 0)
            if o.get("semilla") or t < desde or t % 900 or o.get("dir") not in (1, -1):
                continue
            q, real = precio(miradas.get((15, t)), o["dir"])
            c.sumar(ganador.get((15, t)), o["dir"], q, real)
        cuentas.append(c)
    # B. el operador solo
    for W in (15, 5):
        c = Cuenta(f"B. operador de {W} min solo (papel, libro A)")
        for (w, t, lado), q in sorted(llenados.items()):
            if w == W and q:
                c.sumar(ganador.get((w, t)), lado, q, True)
        cuentas.append(c)
    # C. Claude solo, y D. la combinación
    decs = []
    try:
        with open(os.path.join(nodo, "decisiones.jsonl"), encoding="utf-8") as f:
            for linea in f:
                try:
                    d = json.loads(linea)
                except ValueError:
                    continue
                if isinstance(d, dict) and not d.get("copia_de") and d.get("W") in (5, 15) and isinstance(d.get("t"), (int, float)) \
                        and isinstance(d.get("ventana"), int) and d["ventana"] >= desde:
                    decs.append(d)
    except OSError:
        pass
    decs.sort(key=lambda d: d["t"])
    c = Cuenta("C. Claude solo (cada COMPRAR, comprado en la mirada siguiente)")
    por_ventana = {}
    for d in decs:
        por_ventana.setdefault((d["W"], d["ventana"]), []).append(d)
        lado = {"COMPRAR SUBE": 1, "COMPRAR BAJA": -1}.get(d.get("decision"))
        if lado:
            q, real = precio(miradas.get((d["W"], d["ventana"])), lado, d["t"])
            c.sumar(ganador.get((d["W"], d["ventana"])), lado, q, real)
    cuentas.append(c)
    comb, paradas = Cuenta("D. combinación: el operador quiere comprar y Claude lo aprobó (lo que haría el real)"), 0
    for k, mir in miradas.items():
        lista = por_ventana.get(k, [])
        for x in mir:
            lado = x["decide"]
            if lado not in (1, -1) or x["serie"] != "papel":
                continue
            vig = [d for d in lista if d["t"] <= x["hora"] + 120]
            d = vig[-1] if vig else None
            if d and x["hora"] - d["t"] <= CADUCIDAD_S and d.get("decision") == {1: "COMPRAR SUBE", -1: "COMPRAR BAJA"}[lado]:
                comb.sumar(ganador.get(k), lado, x["q"].get(lado), bool(x["q"].get(lado)))
                break
            paradas += 1
    cuentas.append(comb)
    re_ = Cuenta("E. órdenes reales liquidadas", por_usdt=False)
    for r in reales:
        re_.n += 1
        re_.k += 1 if r["res"] == 1 else 0
        re_.neto += float(r.get("neto") or 0.0)
        re_.reales += 1
    cuentas.append(re_)
    texto = [f"Papel de la combinación, últimos {dias} días (hasta {time.strftime('%d/%m %H:%M', time.gmtime(ahora - 5 * 3600))}):"]
    texto += [x.linea() for x in cuentas]
    texto.append(f"Miradas del operador con compra que el candado paró por no tener un COMPRAR vigente: {paradas}.")
    texto.append("Equilibrio: acertar más que q / 0,98 en cada compra (a 0,46, 46,9 %; a 0,58, 59,2 %). Solo cuenta lo que gane "
                 "con muestra grande y precio real.")
    return texto, cuentas, paradas


if __name__ == "__main__":
    texto, _c, _p = medir(int(arg("--dias", 14)), arg("--nodo", None), arg("--operador", None), arg("--centinela", None))
    print("\n".join(texto))
