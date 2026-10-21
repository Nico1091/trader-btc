"""Descarga históricos públicos de Binance (data.binance.vision) por Tor, verificados con SHA-256.

Uso:  python -u -I descargar.py [conjunto] [desde AAAA-MM] [hasta AAAA-MM-DD]
      conjunto «base» (por omisión): contado 1 m desde 2023, financiación y métricas de futuros.
      conjunto «segundos»: velas de 1 s de BTCUSDT y BTCFDUSD, día por día (trading seguido).
Repetible: lo que ya está verificado no se vuelve a bajar. Un archivo cuya suma no coincide
se borra y se anota; nunca se usa un dato dudoso.
"""
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from red import Cliente, Rechazo, ErrorRed, tor_disponible  # noqa: E402

CARPETA = os.path.dirname(os.path.abspath(__file__))
CRUDOS = os.path.join(CARPETA, "datos", "crudos")
BASE = "https://data.binance.vision/data"
HILOS = 6

_local = threading.local()
# Ruta de red. Regla de Nicolás (19/10/2026): hacia Binance se permite la red normal; todo lo
# demás va por Tor. data.binance.vision es de Binance. Por Tor, los circuitos comparten el
# puente del Buscador (~0,02-0,07 MB/s en total el 20/10), y los 344 archivos de 1 s tardaban
# unas 10 horas; con --directo bajan en minutos. La suma SHA-256 se verifica igual.
RUTA = "tor"


def cliente():
    if not hasattr(_local, "c"):
        _local.c = Cliente(RUTA, plazo=60, reintentos=5, etiqueta=f"vision-{threading.get_ident()}")
    return _local.c


def meses(desde, hasta):
    a, m = desde.year, desde.month
    while (a, m) <= (hasta.year, hasta.month):
        yield a, m
        m += 1
        if m == 13:
            a, m = a + 1, 1


def dias(desde, hasta):
    d = desde
    while d <= hasta:
        yield d
        d += dt.timedelta(days=1)


def tareas_segundos(desde, hasta):
    """Velas de 1 s día por día: archivos de 2-3 MB que se reparten bien entre circuitos de Tor
    (un mensual de 80 MB por un solo circuito tardaría 20 minutos y no se puede reanudar)."""
    lista = []
    for simbolo in ("BTCUSDT", "BTCFDUSD"):
        for d in dias(desde, hasta):
            e = d.isoformat()
            lista.append((f"{BASE}/spot/daily/klines/{simbolo}/1s/{simbolo}-1s-{e}.zip",
                          os.path.join(CRUDOS, f"contado-1s-{simbolo}", f"{simbolo}-1s-{e}.zip")))
    return lista


def tareas(desde, hasta):
    """(url, destino) de todo lo que hace falta. Meses completos por mes; el mes en curso por día."""
    hoy = hasta
    mes_actual = (hoy.year, hoy.month)
    lista = []
    for a, m in meses(desde, hoy):
        etiqueta = f"{a}-{m:02d}"
        if (a, m) < mes_actual:
            lista.append((f"{BASE}/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-{etiqueta}.zip",
                          os.path.join(CRUDOS, "contado-1m", f"BTCUSDT-1m-{etiqueta}.zip")))
            lista.append((f"{BASE}/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{etiqueta}.zip",
                          os.path.join(CRUDOS, "financiacion", f"BTCUSDT-fundingRate-{etiqueta}.zip")))
    for d in dias(dt.date(*mes_actual, 1), hoy):
        e = d.isoformat()
        lista.append((f"{BASE}/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-{e}.zip",
                      os.path.join(CRUDOS, "contado-1m", f"BTCUSDT-1m-{e}.zip")))
    for d in dias(desde, hoy):
        e = d.isoformat()
        lista.append((f"{BASE}/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{e}.zip",
                      os.path.join(CRUDOS, "metricas-5m", f"BTCUSDT-metrics-{e}.zip")))
    return lista


def suma_publicada(url):
    texto = cliente().texto(url + ".CHECKSUM")
    return texto.split()[0].strip().lower()


def bajar(url, destino):
    marca = destino + ".ok"
    if os.path.exists(marca) and os.path.exists(destino):
        return "ya", destino
    try:
        esperada = suma_publicada(url)
        datos = cliente().binario(url)
    except Rechazo as e:
        if e.estado == 404:
            return "no_existe", destino
        return f"error {e.estado}", destino
    except ErrorRed as e:
        return f"error red: {e}", destino
    real = hashlib.sha256(datos).hexdigest()
    if real != esperada:
        return "SUMA_NO_COINCIDE", destino
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    temporal = destino + ".parcial"
    with open(temporal, "wb") as f:
        f.write(datos)
    os.replace(temporal, destino)
    with open(marca, "w", encoding="utf-8") as f:
        f.write(real)
    return "bajado", destino


CONJUNTOS = {
    # nombre: (constructor de tareas, mes inicial por omisión, circuitos de Tor, archivo de resultado)
    "base": (tareas, "2023-01", HILOS, "descarga.json"),
    "segundos": (tareas_segundos, "2026-05", 10, "descarga-segundos.json"),
}


def main():
    global RUTA
    args = sys.argv[1:]
    if "--directo" in args:
        args.remove("--directo")
        RUTA = "directo"
    if RUTA == "tor" and not tor_disponible():
        print("Tor no está escuchando en 127.0.0.1:9050: no se descarga nada (sin plan B directo).")
        return 1
    conjunto = args.pop(0) if args and args[0] in CONJUNTOS else "base"
    constructor, inicio, hilos, salida = CONJUNTOS[conjunto]
    desde = dt.date.fromisoformat((args[0] if args else inicio) + "-01")
    hasta = dt.date.fromisoformat(args[1]) if len(args) > 1 else dt.date.today() - dt.timedelta(days=1)
    lista = constructor(desde, hasta)
    print(f"[{conjunto}] {len(lista)} archivos de {desde} a {hasta}; {hilos} hilos en paralelo, ruta {RUTA}.")
    resumen = {}
    problemas = []
    with cf.ThreadPoolExecutor(hilos) as ex:
        for i, (estado, destino) in enumerate(ex.map(lambda t: bajar(*t), lista), 1):
            clave = estado.split(":")[0]
            resumen[clave] = resumen.get(clave, 0) + 1
            if clave not in ("ya", "bajado"):
                problemas.append((estado, os.path.basename(destino)))
            if i % 100 == 0:
                print(f"  {i}/{len(lista)} {resumen}")
    print("Resultado:", resumen)
    with open(os.path.join(CARPETA, "datos", salida), "w", encoding="utf-8") as f:
        json.dump({"conjunto": conjunto, "desde": str(desde), "hasta": str(hasta), "resumen": resumen,
                   "problemas": problemas}, f, ensure_ascii=False, indent=1)
    for estado, nombre in problemas[:30]:
        print("  problema:", estado, nombre)
    return 0


if __name__ == "__main__":
    sys.exit(main())
