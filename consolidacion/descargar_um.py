"""Descarga velas de 1 minuto de BTCUSDT perpetuo (futuros USDⓈ-M) de data.binance.vision,
comprueba el SHA-256 de cada archivo y las guarda en un solo .npy (tiempo, o, h, l, c, v)."""
import hashlib, io, os, sys, zipfile, urllib.request, datetime as dt
import numpy as np

BASE = "https://data.binance.vision/data/futures/um"
DEST = sys.argv[1] if len(sys.argv) > 1 else "/home/user/datos-btc"
SIMBOLO = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"

def bajar(url):
    for i in range(5):
        try:
            return urllib.request.urlopen(url, timeout=120).read()
        except Exception as e:
            err = e
    raise err

def archivo(url):
    z = bajar(url)
    suma = bajar(url + ".CHECKSUM").decode().split()[0]
    if hashlib.sha256(z).hexdigest() != suma:
        raise SystemExit("SHA-256 no coincide: " + url)
    with zipfile.ZipFile(io.BytesIO(z)) as f:
        txt = f.read(f.namelist()[0]).decode()
    filas = [l.split(",") for l in txt.splitlines() if l and l[0].isdigit()]
    return np.array([[float(x) for x in r[:6]] for r in filas])

def main():
    os.makedirs(DEST, exist_ok=True)
    partes, urls = [], []
    m = dt.date(2020, 1, 1)
    while m < dt.date(2026, 10, 1):
        urls.append(f"{BASE}/monthly/klines/{SIMBOLO}/1m/{SIMBOLO}-1m-{m:%Y-%m}.zip")
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    d = dt.date(2026, 10, 1)
    hoy = dt.datetime.now(dt.timezone.utc).date()
    while d < hoy:
        urls.append(f"{BASE}/daily/klines/{SIMBOLO}/1m/{SIMBOLO}-1m-{d:%Y-%m-%d}.zip")
        d += dt.timedelta(days=1)
    for u in urls:
        try:
            partes.append(archivo(u))
        except urllib.error.HTTPError as e:
            print("falta", u, e.code, flush=True)
            continue
        print("ok", u.rsplit("/", 1)[1], len(partes[-1]), flush=True)
    a = np.concatenate(partes)
    a = a[np.argsort(a[:, 0], kind="stable")]
    a = a[np.concatenate([[True], np.diff(a[:, 0]) > 0])]
    huecos = int((np.diff(a[:, 0]) != 60000).sum())
    np.save(os.path.join(DEST, f"{SIMBOLO}_um_1m.npy"), a)
    print("velas", len(a), "desde", dt.datetime.utcfromtimestamp(a[0, 0] / 1000),
          "hasta", dt.datetime.utcfromtimestamp(a[-1, 0] / 1000), "huecos", huecos, "archivos", len(partes))

if __name__ == "__main__":
    main()
