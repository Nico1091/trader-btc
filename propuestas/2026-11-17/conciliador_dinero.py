#!/usr/bin/env python3
"""Conciliador del dinero de binarias (propuesta del 20/11/2026).

Lee el registro del operador (registro/AAAAMMDD.jsonl) y, si se le indica,
un extracto CSV que usted exporta de Binance. Busca lo que hoy puede costar
dinero sin que nadie lo vea: órdenes sin cierre confirmado, compras sin
liquidar, ganancias sin cobrar, cuentas que no cuadran y movimientos que no
aparecen en el registro.

Solo lee archivos. No usa la red, no escribe en el registro y no envía órdenes.

Uso:
  python3 -I conciliador_dinero.py --registro CARPETA [--extracto CSV]
                                   [--gracia-min 30] [--detalle JSON] [--texto TXT]

Códigos de salida: 0 sin alertas críticas; 1 con alertas críticas; 2 error de uso o de datos.

Formato del extracto (CSV, con encabezado; columnas extra se ignoran):
  orden,importe_usdt,cobrado_usdt[,fecha,lado,precio,resultado]
  - orden: el número de orden de Binance (el mismo que el campo «orden» del registro)
  - importe_usdt: lo que se pagó por la orden
  - cobrado_usdt: lo que Binance abonó por esa orden (0 si perdió o no se cobró)
  Decimales con punto o coma. Sin separador de miles.
"""

import argparse
import csv
import datetime as dt
import glob
import json
import os
import sys

FEE = 0.98                                   # «Ganar» = 0,98 ÷ precio (bloc de binarias, sección 2)
ZONA = dt.timezone(dt.timedelta(hours=-5))   # hora de Colombia, sin cambio de hora
SIN_CIERRE = ("POR ENVIAR", "DUDOSA", "SIN CIERRE")
TOL = 0.0001                                 # diferencias de redondeo entre cifras internas
TOL_EXTRACTO = 0.01                          # el extracto viene redondeado a céntimos
TOL_FORMULA = 0.01                           # 1 % entre el pago anotado y 0,98 ÷ precio
MAX_TEXTO = 3400                             # un mensaje de Telegram cabe bien en 3.500 caracteres
COLUMNAS_EXTRACTO = ("orden", "importe_usdt", "cobrado_usdt")


class ErrorDatos(Exception):
    """Entrada que no se puede leer: la carpeta, el CSV o sus columnas."""


def num(texto):
    """Número con punto o coma decimal; vacío cuenta como 0."""
    t = (texto or "0").strip().replace(",", ".")
    return float(t or 0)


def hora_col(t):
    return dt.datetime.fromtimestamp(float(t), ZONA).strftime("%d/%m/%Y %H:%M")


def leer_registro(carpeta):
    """Devuelve (filas, líneas_ilegibles) de todos los AAAAMMDD.jsonl de la carpeta."""
    if not os.path.isdir(carpeta):
        raise ErrorDatos(f"no existe la carpeta del registro: {carpeta}")
    archivos = sorted(glob.glob(os.path.join(carpeta, "*.jsonl")))
    if not archivos:
        raise ErrorDatos("la carpeta del registro no tiene archivos .jsonl")
    filas, ilegibles = [], []
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        with open(ruta, encoding="utf-8") as f:
            for n, linea in enumerate(f, 1):
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    fila = json.loads(linea)
                    if not isinstance(fila, dict):
                        raise ValueError("no es un objeto")
                except ValueError as ex:
                    ilegibles.append(f"{nombre}:{n} ({ex})")
                    continue
                fila["_origen"] = f"{nombre}:{n}"
                filas.append(fila)
    return filas, ilegibles


def leer_extracto(ruta):
    """Devuelve la lista de movimientos del extracto de Binance."""
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            lector = csv.DictReader(f)
            faltan = [c for c in COLUMNAS_EXTRACTO if c not in (lector.fieldnames or [])]
            if faltan:
                raise ErrorDatos("el extracto no tiene las columnas: " + ", ".join(faltan))
            movimientos = []
            for n, r in enumerate(lector, 2):
                if None in r or any(v is None for v in r.values()):
                    raise ErrorDatos(f"línea {n} del extracto no tiene las mismas columnas que el encabezado "
                                     "(¿un decimal con coma sin comillas? Use punto o ponga el valor entre comillas)")
                try:
                    movimientos.append({
                        "orden": (r["orden"] or "").strip(),
                        "importe": num(r["importe_usdt"]),
                        "cobrado": num(r["cobrado_usdt"]),
                    })
                except ValueError as ex:
                    raise ErrorDatos(f"línea {n} del extracto no se lee: {ex}")
    except OSError as ex:
        raise ErrorDatos(f"no se puede abrir el extracto: {ex}")
    return movimientos


def agrupar(filas):
    """Une las filas del registro por id de orden, con su tipo."""
    ordenes = {}
    for fila in filas:
        oid = fila.get("id")
        if oid is None:
            continue
        g = ordenes.setdefault(str(oid), {"id": str(oid), "lecturas": [], "liquidaciones": [], "cobros": []})
        tipo = fila.get("tipo")
        if tipo == "orden leída":
            g["lecturas"].append(fila)
        elif tipo == "liquidación":
            g["liquidaciones"].append(fila)
        elif tipo == "cobro":
            g["cobros"].append(fila)
    return ordenes


def resumir(g):
    """Estado final de una orden a partir de sus filas."""
    lect = g["lecturas"][-1] if g["lecturas"] else {}
    liq = g["liquidaciones"][-1] if g["liquidaciones"] else None
    cobro = g["cobros"][-1] if g["cobros"] else None
    comprado = float((liq or lect).get("comprado") or 0)
    return {
        "id": g["id"],
        "orden": lect.get("orden") or (liq or {}).get("orden"),
        "estado": lect.get("estado"),
        "final": lect.get("final"),
        "comprado": comprado,
        "precio": lect.get("precio"),
        "contratos": float(lect.get("contratos") or 0),
        "hora_compra": lect.get("hora"),
        "liquidada": liq is not None,
        "duplicadas": max(0, len(g["liquidaciones"]) - 1),
        "res": liq.get("res") if liq else None,
        "pago": float(liq.get("pago") or 0) if liq else 0.0,
        "neto": float(liq.get("neto") or 0) if liq else 0.0,
        "cobro": cobro.get("estado") if cobro else None,
        "monto_cobrado": float(cobro.get("monto") or 0) if cobro else 0.0,
    }


def alertas_orden(o, ahora_ref, gracia_s):
    """Revisa una orden del registro sin mirar nada más que sus propias filas y el reloj de referencia."""
    out = []

    def alerta(nivel, codigo, texto):
        out.append({"nivel": nivel, "codigo": codigo, "orden": o["id"], "texto": texto})

    comprado = o["comprado"]
    dinero = comprado > TOL

    if o["estado"] is not None and (o["estado"] in SIN_CIERRE or o["final"] is False):
        extra = f", {comprado:.2f} USDT en juego" if dinero else ""
        alerta("critica" if dinero else "aviso", "sin_cierre",
               f"estado «{o['estado']}» sin cierre confirmado{extra}")

    if dinero and not o["liquidada"] and o["final"] is not False and o["hora_compra"] is not None \
            and ahora_ref - float(o["hora_compra"]) > gracia_s:
        alerta("critica", "sin_liquidar",
               f"compra de {comprado:.2f} USDT sin liquidar {int(gracia_s // 60)} min después de cerrarse")

    if o["duplicadas"]:
        alerta("critica", "liquidacion_repetida",
               f"{o['duplicadas'] + 1} liquidaciones para la misma orden (puede contar dos veces)")

    if dinero and not o["orden"]:
        alerta("aviso", "sin_id_de_orden", "la orden no tiene número de Binance: no se puede cruzar con el extracto")

    if o["liquidada"]:
        if abs(o["neto"] - (o["pago"] - comprado)) > TOL:
            alerta("critica", "descuadre_neto",
                   f"neto {o['neto']:+.4f} no es pago {o['pago']:.4f} menos compra {comprado:.4f}")
        esperado = {1: o["contratos"], 2: o["contratos"] / 2, 0: 0.0, -1: 0.0}.get(o["res"])
        if esperado is None:
            alerta("critica", "resultado_desconocido", f"resultado {o['res']!r} no conocido")
        elif abs(o["pago"] - esperado) > TOL:
            alerta("critica", "pago_no_cuadra",
                   f"pago {o['pago']:.4f} con resultado {o['res']}; debía ser {esperado:.4f}")
        if o["res"] == 1 and dinero and o["precio"]:
            precio = float(o["precio"])
            if precio > 0:
                formula = comprado * FEE / precio
                if formula > 0 and abs(o["contratos"] - formula) / formula > TOL_FORMULA:
                    alerta("aviso", "pago_fuera_de_formula",
                           f"pago {o['contratos']:.4f} frente a {formula:.4f} (0,98 ÷ precio)")
        if o["pago"] > TOL and o["cobro"] != "cobrado":
            alerta("critica", "ganancia_sin_cobrar",
                   f"gana {o['pago']:.2f} USDT y el cobro figura «{o['cobro'] or 'sin intento'}»")
        if o["cobro"] == "cobrado" and abs(o["monto_cobrado"] - o["pago"]) > TOL_EXTRACTO:
            alerta("critica", "cobro_no_cuadra",
                   f"cobro anotado {o['monto_cobrado']:.2f} frente a pago {o['pago']:.2f}")
    return out


def cruzar(ordenes, extracto):
    """Compara el registro con el extracto de Binance. Devuelve (alertas, cifras de caja)."""
    alertas = []

    def alerta(nivel, codigo, orden, texto):
        alertas.append({"nivel": nivel, "codigo": codigo, "orden": orden, "texto": texto})

    por_orden = {o["orden"]: o for o in ordenes.values() if o["orden"]}
    vistos = set()
    for m in extracto:
        vistos.add(m["orden"])
        o = por_orden.get(m["orden"])
        if o is None:
            alerta("critica", "movimiento_no_registrado", m["orden"],
                   f"en el extracto hay {m['importe']:.2f} USDT pagados y {m['cobrado']:.2f} cobrados, sin fila en el registro")
            continue
        if abs(o["comprado"] - m["importe"]) > TOL_EXTRACTO:
            alerta("critica", "importe_distinto", m["orden"],
                   f"registro {o['comprado']:.2f} frente a extracto {m['importe']:.2f} USDT")
        cobro_reg = o["pago"] if o["cobro"] == "cobrado" else 0.0
        if abs(cobro_reg - m["cobrado"]) > TOL_EXTRACTO:
            alerta("critica", "cobro_distinto", m["orden"],
                   f"cobro en el registro {cobro_reg:.2f} frente a extracto {m['cobrado']:.2f} USDT")

    for o in ordenes.values():
        if o["comprado"] > TOL and o["orden"] and o["orden"] not in vistos:
            alerta("aviso", "no_aparece_en_extracto", o["orden"],
                   f"compra de {o['comprado']:.2f} USDT del registro que no está en el extracto (revise su periodo)")

    caja_registro = sum(((o["pago"] if o["cobro"] == "cobrado" else 0.0) - o["comprado"])
                        for o in ordenes.values() if o["comprado"] > TOL)
    caja_extracto = sum(m["cobrado"] - m["importe"] for m in extracto)
    if abs(caja_registro - caja_extracto) > TOL_EXTRACTO:
        alerta("critica", "caja_no_cuadra", "general",
               f"caja según el registro {caja_registro:+.2f} USDT; según el extracto {caja_extracto:+.2f} USDT")
    return alertas, {"caja_registro": caja_registro, "caja_extracto": caja_extracto,
                     "movimientos": len(extracto)}


def resumen(ordenes, filas, ilegibles, ahora_ref):
    compradas = [o for o in ordenes.values() if o["comprado"] > TOL]
    liquidadas = [o for o in compradas if o["liquidada"]]
    usdt = sum(o["comprado"] for o in compradas)
    neto = sum(o["neto"] for o in liquidadas)
    precios = [float(o["precio"]) for o in compradas if o["precio"]]
    horas = [float(f["hora"]) for f in filas if isinstance(f.get("hora"), (int, float))]
    return {
        "periodo": {"desde": hora_col(min(horas)) if horas else None, "hasta": hora_col(max(horas)) if horas else None},
        "ordenes": len(ordenes),
        "compradas": len(compradas),
        "usdt_comprados": round(usdt, 4),
        "liquidadas": len(liquidadas),
        "aciertos": sum(1 for o in liquidadas if o["res"] == 1),
        "abiertas": len(compradas) - len(liquidadas),
        "neto_registro": round(neto, 4),
        "neto_por_usdt": round(neto / usdt, 4) if usdt > TOL else None,
        "precio_medio": round(sum(precios) / len(precios), 4) if precios else None,
        "lineas_ilegibles": ilegibles,
        "ahora_ref": ahora_ref,
    }


def texto_telegram(res, alertas, cruce):
    criticas = [a for a in alertas if a["nivel"] == "critica"]
    avisos = [a for a in alertas if a["nivel"] == "aviso"]
    p = res["periodo"]
    lineas = [
        f"[Proyectos] Conciliación de binarias · {p['desde'] or '?'} a {p['hasta'] or '?'} (hora de Colombia)",
        f"Compras: {res['compradas']} por {res['usdt_comprados']:.2f} USDT · liquidadas: {res['liquidadas']} · "
        f"aciertos: {res['aciertos']} · abiertas: {res['abiertas']}",
        f"Neto según el registro: {res['neto_registro']:+.2f} USDT"
        + (f" ({res['neto_por_usdt']:+.3f} por USDT comprado)" if res["neto_por_usdt"] is not None else ""),
    ]
    if cruce is not None:
        lineas.append(f"Caja según el extracto: {cruce['caja_extracto']:+.2f} USDT · según el registro: "
                      f"{cruce['caja_registro']:+.2f} USDT")
    lineas.append(f"Alertas críticas: {len(criticas)} · avisos: {len(avisos)}")
    if not alertas:
        lineas.append("Sin alertas: el registro cuadra con sus propias reglas.")
    for a in (criticas + avisos)[:25]:
        etiqueta = "CRÍTICA" if a["nivel"] == "critica" else "aviso"
        lineas.append(f"• [{etiqueta}] {a['orden']}: {a['texto']}")
    resto = len(criticas) + len(avisos) - 25
    if resto > 0:
        lineas.append(f"… y {resto} más en el detalle.")
    texto = "\n".join(lineas)
    if len(texto) > MAX_TEXTO:
        texto = texto[:MAX_TEXTO - 40].rstrip() + "\n… (texto recortado; vea el detalle)"
    return texto


def conciliar(carpeta, extracto_ruta=None, gracia_min=30.0):
    """Función principal, reutilizable: devuelve (resultado, alertas, cruce, texto)."""
    filas, ilegibles = leer_registro(carpeta)
    horas = [float(f["hora"]) for f in filas if isinstance(f.get("hora"), (int, float))]
    ahora_ref = max(horas) if horas else 0.0
    ordenes = agrupar(filas)
    resumidas = {k: resumir(g) for k, g in ordenes.items()}

    alertas = []
    for o in resumidas.values():
        alertas.extend(alertas_orden(o, ahora_ref, gracia_min * 60))
    for linea in ilegibles:
        alertas.append({"nivel": "aviso", "codigo": "linea_ilegible", "orden": "-",
                        "texto": f"línea que no se lee en el registro: {linea}"})

    cruce = None
    if extracto_ruta:
        movimientos = leer_extracto(extracto_ruta)
        extra, cruce = cruzar(resumidas, movimientos)
        alertas.extend(extra)

    res = resumen(resumidas, filas, ilegibles, ahora_ref)
    if cruce is not None:
        res["extracto"] = {"movimientos": cruce["movimientos"],
                           "caja_extracto": round(cruce["caja_extracto"], 4),
                           "caja_registro": round(cruce["caja_registro"], 4)}
    orden_nivel = {"critica": 0, "aviso": 1}
    alertas.sort(key=lambda a: (orden_nivel[a["nivel"]], a["codigo"], a["orden"]))
    return res, alertas, cruce, texto_telegram(res, alertas, cruce), resumidas


def main(argv=None):
    p = argparse.ArgumentParser(description="Conciliador del dinero de binarias (solo lectura).")
    p.add_argument("--registro", required=True, help="carpeta con los AAAAMMDD.jsonl del operador")
    p.add_argument("--extracto", help="CSV de Binance con orden, importe_usdt y cobrado_usdt")
    p.add_argument("--gracia-min", type=float, default=30.0,
                   help="minutos que puede tardar una liquidación antes de marcarse (30 por defecto)")
    p.add_argument("--detalle", help="archivo JSON donde guardar el detalle completo")
    p.add_argument("--texto", help="archivo de texto con el mensaje para Telegram")
    a = p.parse_args(argv)
    try:
        res, alertas, cruce, texto, ordenes = conciliar(a.registro, a.extracto, a.gracia_min)
    except ErrorDatos as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 2

    if a.detalle:
        with open(a.detalle, "w", encoding="utf-8") as f:
            json.dump({"resumen": res, "alertas": alertas, "ordenes": ordenes}, f, ensure_ascii=False, indent=2)
    if a.texto:
        with open(a.texto, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
    print(texto)
    return 1 if any(x["nivel"] == "critica" for x in alertas) else 0


if __name__ == "__main__":
    sys.exit(main())
