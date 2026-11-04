"""Descarga la profundidad del libro de futuros de Binance (bookDepth: fotos cada 30 s a ±0,2/1/2/3/4/5 %), 2023 a hoy.
Fuente pública y gratuita: data.binance.vision (directo: su regla permite la conexión normal con Binance).
Comprueba cada zip con su CHECKSUM (SHA-256). Reanudable: salta lo ya bajado y verificado.
Uso: python -I bajar_bookdepth.py [BTCUSDT ETHUSDT]"""
import concurrent.futures as cf
import datetime as dt
import hashlib
import os
import sys
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(os.path.dirname(AQUI), "datos", "bookdepth")
BASE = "https://data.binance.vision/data/futures/um/daily/bookDepth/{s}/{s}-bookDepth-{d}.zip"
H = {"User-Agent": "binarias-investigacion"}


def bajar(sim, dia):
    ruta = os.path.join(DEST, sim, f"{sim}-bookDepth-{dia}.zip")
    if os.path.exists(ruta) and os.path.exists(ruta + ".ok"):
        return "ya"
    url = BASE.format(s=sim, d=dia)
    for intento in range(4):
        try:
            datos = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read()
            suma = urllib.request.urlopen(urllib.request.Request(url + ".CHECKSUM", headers=H), timeout=60).read().decode().split()[0]
            if hashlib.sha256(datos).hexdigest() != suma:
                raise ValueError("suma distinta")
            with open(ruta, "wb") as f:
                f.write(datos)
            open(ruta + ".ok", "w").close()
            return "bajado"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "no existe"
            time.sleep(2 * (intento + 1))
        except Exception:
            time.sleep(2 * (intento + 1))
    return "falló"


def main():
    sims = sys.argv[1:] or ["BTCUSDT", "ETHUSDT"]
    hoy = dt.date.today()
    for sim in sims:
        os.makedirs(os.path.join(DEST, sim), exist_ok=True)
        dias = [(dt.date(2023, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range((hoy - dt.date(2023, 1, 1)).days)]
        cuenta = {}
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for r in ex.map(lambda d: bajar(sim, d), dias):
                cuenta[r] = cuenta.get(r, 0) + 1
        print(sim, cuenta, flush=True)


if __name__ == "__main__":
    main()
