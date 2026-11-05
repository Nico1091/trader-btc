"""Arnés de la Mesa de binarias (04/11/2026): las reglas que mandan sobre la pantalla, el agente y los botones.

Funciones puras, sin red ni archivos, para poder probarlas. Mismo orden de su semáforo v3.3, llevado a los mercados de 15 min
que pasaron la P19 (PLAN-TOTAL.md, 7b):
- SÍ: el borrador de hoy va sumando, ningún SÍ perdió hoy y el interés abierto no subió.
- Aviso COMPRE o VENDA: además el 75 % de aciertos en las últimas 25, 25 cerradas con precio real del libro, billetera, saldo,
  precio de compra hasta el tope y dentro de la ventana de toque.
Orden suya del 04/11: los botones están siempre disponibles. Esto aconseja; lo que frena una orden son los topes de mesa.py.
"""
import datetime as dt

COL = dt.timezone(dt.timedelta(hours=-5))
CFG = {
    "precio_max_manual": 0.90,  # botón sin señal: por encima de esto paga casi nada
    "ask_max": 0.53,            # comprar más caro que esto se come la ventaja (0,53 × 1,02 = 54,06 % de equilibrio)
    "ventana_toque": 75,        # segundos tras la señal; después el precio ya cambió
    "reciente_ventana": 25,     # porcentaje de aciertos sobre las últimas 25 cerradas
    "umbral_pct": 75,           # su regla: 75 % de aciertos para el dinero real (19 de 25)
    "min_precio_real": 25,      # P19: sin borrador con precios reales del libro no hay real
    "umbral_oi": 0.00022,       # igual que semaforo.UMBRAL_OI
    "pct_defecto": 5,
    "pct_tope": 16,             # su tope por apuesta
    "min_usdt": 2.0,            # la API pide unos 1,5 USDT; su mínimo de antes en porcentaje del saldo
    "comision": 0.02,           # feeRateBps del mercado
    "deslizamiento_bps": 200,
    "fuente_fondos": "CEX",
}


def ini_dia(ahora):
    d = dt.datetime.fromtimestamp(ahora, COL)
    return dt.datetime(d.year, d.month, d.day, tzinfo=COL).timestamp()


def neto_op(res, ask, cfg=CFG):
    """Ganancia por unidad apostada comprando a `ask`, con la comisión encima. res: 1, 0,5 (empate) o 0."""
    return res / ask - (1 + cfg["comision"])


def resumen(ops, ahora, cfg=CFG):
    """Cómo va el borrador con las operaciones ya cerradas antes de `ahora`."""
    hoy0 = ini_dia(ahora)
    cerr = [o for o in ops if o.get("res") is not None and o.get("neto") is not None and o["t"] + 900 <= ahora]
    hoy = [o for o in cerr if o["t"] >= hoy0]
    neto = 0.0
    for o in hoy:  # bucle explícito: sum() suma distinto desde la 3.12
        neto += o["neto"]
    ult = [o for o in ops if o.get("res") is not None and o["t"] + 900 <= ahora][-cfg["reciente_ventana"]:]  # igual que quince.py
    k25 = len([o for o in ult if o["res"] == 1])
    return {"neto": round(neto, 4), "aciertos": len([o for o in hoy if o["res"] == 1]), "n": len(hoy),
            "pct_hoy": round(100 * len([o for o in hoy if o["res"] == 1]) / len(hoy)) if hoy else 0,
            "pct25": round(100 * k25 / len(ult)) if ult else 0,
            "perdio": any(o.get("si") and o["res"] == 0 for o in hoy), "k25": k25, "n25": len(ult),
            "rehechas_hoy": len([o for o in hoy if o.get("semilla")]),
            "con_precio_real": len([o for o in cerr if not o.get("semilla")])}


def marcar_si(neto, perdio, doi, cfg=CFG):
    return bool(neto > 0 and not perdio and doi is not None and doi <= cfg["umbral_oi"])


def importe(saldo, pct, cfg=CFG):
    """USDT a apostar: porcentaje del saldo, con su tope; None si el mínimo no cabe dentro del tope."""
    pct = min(max(float(pct), 0.0), float(cfg["pct_tope"]))
    tope = saldo * cfg["pct_tope"] / 100
    x = max(saldo * pct / 100, cfg["min_usdt"])
    return None if x > tope else int(x * 100) / 100


def evaluar(ops, ahora, mercado, cfg=CFG, billetera=False, saldo=0.0, pct=None):
    """El estado de la mesa. nivel: NO, ATENTO, ESPERE, COMPRE o VENDA."""
    r = resumen(ops, ahora, cfg)
    dando = r["neto"] > 0 and not r["perdio"]
    abierta = next((o for o in reversed(ops) if o.get("res") is None and 0 <= ahora - o["t"] <= cfg["ventana_toque"]), None)
    motivo_no = "un SÍ ya perdió hoy" if r["perdio"] else (
        f"el borrador de hoy va {r['neto']:+.2f}, con {r['pct_hoy']} % de aciertos".replace(".", ",") if r["n"] else "el borrador de hoy aún no suma")
    salida = {"resumen": r, "dando": dando, "sentido": 0, "boton": False, "faltan": [], "t": None, "usdt": None}
    if not abierta:
        if dando:
            nota = f" ({r['rehechas_hoy']} de {r['n']} rehechas con velas, a precio supuesto)" if r["rehechas_hoy"] else ""
            return {**salida, "nivel": "ATENTO", "titulo": "ATENTO · EL BORRADOR ESTÁ DANDO",
                    "detalle": f"Va {r['neto']:+.2f} hoy{nota}. El programa analiza; espere la señal.".replace(".", ",", 1)}
        return {**salida, "nivel": "NO", "titulo": "NO OPERE", "detalle": f"No se están dando resultados: {motivo_no}."}
    d = abierta["dir"]
    sent = "SUBE" if d == 1 else "BAJA"
    salida.update(sentido=d, t=abierta["t"])
    if not abierta.get("si"):
        motivos = [motivo_no] if not dando else []
        if abierta.get("doi") is None:
            motivos.append("sin dato del interés abierto")
        elif abierta["doi"] > cfg["umbral_oi"]:
            motivos.append("el interés abierto subió")
        return {**salida, "nivel": "NO", "titulo": f"NO OPERE · {sent} SOLO EN BORRADOR", "detalle": "Señal sin SÍ: " + " y ".join(motivos or ["no cumple"]) + "."}
    faltan = []
    if r["n25"] < cfg["reciente_ventana"] or 100 * r["k25"] / r["n25"] < cfg["umbral_pct"]:
        faltan.append(f"aciertos en {r['pct25']} % y pide {cfg['umbral_pct']} %")
    if r["con_precio_real"] < cfg["min_precio_real"]:
        faltan.append(f"borrador con precios reales: {r['con_precio_real']} de {cfg['min_precio_real']}")
    if not billetera:
        faltan.append("crear la cuenta de predicción en la app")
    ask = ((mercado or {}).get("ask") or {}).get(d)
    if ask is None:
        faltan.append("precio del mercado")
    elif ask > cfg["ask_max"]:
        faltan.append(f"precio {ask:.2f}, tope {cfg['ask_max']:.2f}".replace(".", ","))
    usdt = importe(saldo, cfg["pct_defecto"] if pct is None else pct, cfg)
    if usdt is None:
        faltan.append(f"saldo: {saldo:.2f} USDT no alcanza con el tope del {cfg['pct_tope']} %".replace(".", ",", 1))
    if faltan:
        return {**salida, "nivel": "ESPERE", "titulo": f"SÍ EN BORRADOR · {sent} · ESPERE", "detalle": "Falta: " + "; ".join(faltan) + ".", "faltan": faltan}
    accion = "COMPRE" if d == 1 else "VENDA"
    return {**salida, "nivel": accion, "titulo": f"{accion} · {sent} A 15 MIN", "detalle": f"Precio {ask:.2f}, apuesta de {usdt:.2f} USDT.".replace(".", ","),
            "boton": True, "usdt": usdt}
