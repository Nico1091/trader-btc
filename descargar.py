"""Descarga históricos públicos de Binance (data.binance.vision) por Tor, verificados con SHA-256.

Uso:  python -u -I descargar.py [desde AAAA-MM] [hasta AAAA-MM-DD]
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


def cliente():
    if not hasattr(_local, "c"):
        _local.c = Cliente("tor", plazo=60, reintentos=5, etiqueta=f"vision-{threading.get_ident()}")
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


def main():
    if not tor_disponible():
        print("Tor no está escuchando en 127.0.0.1:9050: no se descarga nada (sin plan B directo).")
        return 1
    desde = dt.date.fromisoformat((sys.argv[1] if len(sys.argv) > 1 else "2023-01") + "-01")
    hasta = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date.today() - dt.timedelta(days=1)
    lista = tareas(desde, hasta)
    print(f"{len(lista)} archivos de {desde} a {hasta}; {HILOS} circuitos de Tor en paralelo.")
    resumen = {}
    problemas = []
    with cf.ThreadPoolExecutor(HILOS) as ex:
        for i, (estado, destino) in enumerate(ex.map(lambda t: bajar(*t), lista), 1):
            clave = estado.split(":")[0]
            resumen[clave] = resumen.get(clave, 0) + 1
            if clave not in ("ya", "bajado"):
                problemas.append((estado, os.path.basename(destino)))
            if i % 100 == 0:
                print(f"  {i}/{len(lista)} {resumen}")
    print("Resultado:", resumen)
    with open(os.path.join(CARPETA, "datos", "descarga.json"), "w", encoding="utf-8") as f:
        json.dump({"desde": str(desde), "hasta": str(hasta), "resumen": resumen, "problemas": problemas}, f,
                  ensure_ascii=False, indent=1)
    for estado, nombre in problemas[:30]:
        print("  problema:", estado, nombre)
    return 0


if __name__ == "__main__":
    sys.exit(main())
