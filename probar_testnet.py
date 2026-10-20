"""Prueba de punta a punta en la red de pruebas de contado de Binance (dinero falso).

Uso:  python -u -I probar_testnet.py
Lee la clave de prueba desde la ruta de config.json en tiempo de ejecución; no la copia
ni la muestra. Todo queda anotado en diario/pruebas-testnet.jsonl.
"""
import json
import os
import sys
import time
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from binance import Binance, leer_claves, BOGOTA  # noqa: E402
import datetime as dt  # noqa: E402

CARPETA = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(CARPETA, "config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)
SIMBOLO = CONFIG["simbolo"]
DIARIO = os.path.join(CARPETA, "diario", "pruebas-testnet.jsonl")
os.makedirs(os.path.dirname(DIARIO), exist_ok=True)


def anotar(evento, **datos):
    fila = {"hora_colombia": dt.datetime.now(BOGOTA).isoformat(timespec="seconds"), "evento": evento}
    fila.update({k: (str(v) if isinstance(v, Decimal) else v) for k, v in datos.items()})
    with open(DIARIO, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    print(f"[{fila['hora_colombia']}] {evento}: " + ", ".join(f"{k}={v}" for k, v in datos.items()))


def desvio_pct(a, b):
    return float((Decimal(a) - Decimal(b)) / Decimal(b) * 100)


def main():
    clave, secreto = leer_claves(CONFIG["claves_testnet"])
    t = Binance("testnet_contado", clave, secreto)
    real = Binance("datos_contado")
    anotar("reloj", desfase_ms=t.sincronizar_reloj())

    f = t.filtros(SIMBOLO)
    anotar("filtros", paso_cantidad=f.paso_cantidad, cantidad_min=f.cantidad_min,
           paso_precio=f.paso_precio, nocional_min=f.nocional_min)

    saldos = t.saldos()
    anotar("saldos", BTC=saldos.get("BTC", ("0", "0"))[0], USDT=saldos.get("USDT", ("0", "0"))[0],
           activos=len(saldos))
    try:
        c = t.comisiones(SIMBOLO)
        anotar("comisiones", creador=c["standardCommission"]["maker"], tomador=c["standardCommission"]["taker"])
    except Exception as e:  # la testnet no siempre expone este punto
        anotar("comisiones_no_disponibles", detalle=str(e)[:160])

    p_test, p_real = t.precio(SIMBOLO), real.precio(SIMBOLO)
    anotar("precio", testnet=p_test, real=p_real, desvio_pct=round(desvio_pct(p_test, p_real), 4))

    # 1) validar sin crear
    q = f.cantidad(Decimal("6") / p_test, arriba=True)
    t.probar_orden(SIMBOLO, "BUY", q, p_test * Decimal("0.8"))
    anotar("orden_validada_sin_crear", cantidad=q)

    # 2) orden de creador lejos del precio: se crea, se ve y se cancela
    o = t.limite(SIMBOLO, "BUY", q, p_test * Decimal("0.8"))
    abiertas = [x["clientOrderId"] for x in t.ordenes_abiertas(SIMBOLO)]
    anotar("orden_lejana_creada", id=o["clientOrderId"], estado=o["status"],
           visible_en_abiertas=o["clientOrderId"] in abiertas)
    cancelada = t.cancelar(SIMBOLO, o["clientOrderId"])
    anotar("orden_lejana_cancelada", estado=cancelada["status"])

    # 3) compra mínima a mercado, protegida con OCO en el servidor, y salida limpia
    antes_real = real.precio(SIMBOLO)
    compra = t.mercado(SIMBOLO, "BUY", cotizado=Decimal("6"))
    despues_real = real.precio(SIMBOLO)
    llenado = sum(Decimal(x["qty"]) for x in compra["fills"])
    pagado = sum(Decimal(x["price"]) * Decimal(x["qty"]) for x in compra["fills"])
    comision = sum(Decimal(x["commission"]) for x in compra["fills"])
    medio = pagado / llenado
    referencia = (antes_real + despues_real) / 2
    anotar("compra_mercado", estado=compra["status"], btc=llenado, usdt=round(pagado, 4),
           precio_medio=round(medio, 2), precio_real=round(referencia, 2),
           desvio_vs_real_pct=round(desvio_pct(medio, referencia), 4),
           comision=comision, activo_comision=compra["fills"][0]["commissionAsset"] if compra["fills"] else "")

    neto = f.cantidad(llenado - (comision if compra["fills"] and compra["fills"][0]["commissionAsset"] == "BTC" else 0))
    oco = t.oco_venta(SIMBOLO, neto, medio * Decimal("1.01"), medio * Decimal("0.99"))
    patas = [(x["type"], x["status"]) for x in oco["orderReports"]]
    anotar("oco_protege_compra", lista=oco["listClientOrderId"], estado=oco["listOrderStatus"], patas=patas)
    t.cancelar_oco(SIMBOLO, oco["listClientOrderId"])
    anotar("oco_cancelada", lista=oco["listClientOrderId"])

    time.sleep(1)
    venta = t.mercado(SIMBOLO, "SELL", cantidad=neto)
    recibido = sum(Decimal(x["price"]) * Decimal(x["qty"]) for x in venta["fills"])
    vendido = sum(Decimal(x["qty"]) for x in venta["fills"])
    p_venta = recibido / vendido if vendido else Decimal(0)
    p_real_venta = real.precio(SIMBOLO)
    anotar("venta_mercado", estado=venta["status"], btc=vendido, usdt=round(recibido, 4),
           precio_medio=round(p_venta, 2), precio_real=p_real_venta,
           desvio_vs_real_pct=round(desvio_pct(p_venta, p_real_venta), 4))
    anotar("abiertas_al_final", cantidad=len(t.ordenes_abiertas(SIMBOLO)))


if __name__ == "__main__":
    main()
