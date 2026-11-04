"""T24a (29/10/2026): velas de 1 min de futuros de BTCUSDT y ETHUSDT con el volumen de compras agresivas (taker buy).

Para el modelo unificado (PLAN.md, sección 11). Baja directo de Binance (data.binance.vision por meses y la API para lo que
falta) a datos/fut_crudos/<SÍMBOLO>/ (carpeta propia, solo datos) y arma datos/<SÍMBOLO>_um_1m_tb.npy con 7 columnas:
milisegundos, apertura, máximo, mínimo, cierre, volumen y volumen de compras agresivas. Sin huecos: un minuto que falte queda
plano con el último cierre y volumen 0. Comprueba que los precios coincidan con trader-btc/datos/um/<SÍMBOLO>_um_1m.npy.
Uso: python -I t24_datos_flujo.py"""
import csv
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(os.path.dirname(AQUI), "datos")
CRUDOS = os.path.join(DATOS, "fut_crudos")
UM = r"C:\Users\ni109\Ingresos\trader-btc\datos\um\{}_um_1m.npy"
H = {"User-Agent": "binarias-flujo"}
UTC = dt.timezone.utc


def bajar(url, intentos=4):
    for i in range(intentos):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=90).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def filas_csv(contenido):
    out = []
    for r in csv.reader(io.StringIO(contenido.decode("utf-8", "replace"))):
        if not r or not r[0].strip().isdigit():
            continue
        t = int(r[0])
        t = t // 1000 if t > 10 ** 14 else t
        out.append((t, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[9])))
    return out


def armar(sim):
    os.makedirs(os.path.join(CRUDOS, sim), exist_ok=True)
    hoy = dt.datetime.now(UTC)
    ult = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
    filas, y, m = [], 2020, 1
    while (y, m) <= ult:
        nombre = f"{sim}-1m-{y}-{m:02d}.zip"
        ruta = os.path.join(CRUDOS, sim, nombre)
        if not os.path.exists(ruta):
            z = bajar(f"https://data.binance.vision/data/futures/um/monthly/klines/{sim}/1m/{nombre}")
            if z is None:
                print(f"   falta {nombre}", flush=True)
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
                continue
            open(ruta, "wb").write(z)
        with zipfile.ZipFile(ruta) as zf:
            for n in zf.namelist():
                filas += filas_csv(zf.read(n))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    desde = max(r[0] for r in filas) + 60000
    ahora = int(time.time() * 1000)
    while desde < ahora - 60000:
        x = json.loads(bajar(f"https://fapi.binance.com/fapi/v1/klines?symbol={sim}&interval=1m&startTime={desde}&limit=1500") or b"[]")
        x = [k for k in x if int(k[6]) < ahora]
        if not x:
            break
        filas += [(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), float(k[9])) for k in x]
        desde = int(x[-1][0]) + 60000
        time.sleep(0.35)
    filas = sorted(dict((r[0], r) for r in filas).values())
    a = np.array(filas, dtype=float)
    t = (a[:, 0] // 60000).astype(np.int64)
    t0, t1 = int(t[0]), int(t[-1])
    n = t1 - t0 + 1
    M = np.full((n, 6), np.nan)
    M[t - t0] = a[:, 1:7]
    hueco = np.isnan(M[:, 3])
    idx = np.where(~hueco, np.arange(n, dtype=np.int64), 0)
    np.maximum.accumulate(idx, out=idx)
    ultc = M[idx, 3]
    for j in range(4):
        M[hueco, j] = ultc[hueco]
    M[hueco, 4:] = 0.0
    out = np.column_stack([(np.arange(t0, t1 + 1, dtype=np.int64) * 60000).astype(float), M])
    assert np.all(np.diff(out[:, 0]) == 60000) and 1.5e12 < out[0, 0] < 1.9e12, "marcas de tiempo inválidas"
    np.save(os.path.join(DATOS, f"{sim}_um_1m_tb.npy"), out)
    ref = np.load(UM.format(sim), mmap_mode="r")
    i = np.searchsorted(out[:, 0], ref[:, 0])
    ok = (i < len(out)) & (out[np.minimum(i, len(out) - 1), 0] == ref[:, 0])
    igual = float(np.mean(np.all(np.isclose(out[i[ok], 1:6], ref[ok, 1:6], rtol=1e-9, atol=1e-9), axis=1)))
    return {"desde": dt.datetime.fromtimestamp(t0 * 60, UTC).strftime("%Y-%m-%d %H:%M"), "hasta": dt.datetime.fromtimestamp(t1 * 60, UTC).strftime("%Y-%m-%d %H:%M"),
            "minutos": n, "rellenados": int(hueco.sum()), "coincide_con_trader_btc": round(100 * igual, 4),
            "taker_sobre_volumen": round(float(np.nansum(out[:, 6]) / max(1.0, np.nansum(out[:, 5]))), 4)}


def main():
    res = {}
    for sim in ("BTCUSDT", "ETHUSDT"):
        r = armar(sim)
        res[sim] = r
        print(f"{sim}: {r['minutos']:,} minutos del {r['desde']} al {r['hasta']} (UTC) · rellenados {r['rellenados']:,} · "
              f"precios iguales a los de trader-btc en {r['coincide_con_trader_btc']} % · compras agresivas / volumen {r['taker_sobre_volumen']}".replace(",", "."),
              flush=True)
    json.dump(res, open(os.path.join(AQUI, "t24_datos_flujo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
