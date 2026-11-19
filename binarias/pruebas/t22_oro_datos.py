"""T22 (29/10/2026): velas de 1 min de ORO en Binance, para repetir las pruebas a ciegas. Pedido de Nicolás: «prueba con el oro».

Binance no tiene Contratos de Evento de oro (solo BTCUSDT y ETHUSDT): esto mide si habría ventaja, no se puede apostar ahí hoy.
- PAXGUSDT de contado (oro tokenizado de Paxos, desde el 28/08/2020): la única historia larga.
- XAUUSDT perpetuo de futuros (oro físico, «TradFi», desde el 11/12/2025): el más líquido; sirve para comprobar que PAXG se
  mueve como el oro real.
Descarga directo de Binance (data.binance.vision por meses y la API para el mes en curso) a datos/oro_crudos/ (carpeta propia,
solo datos). Arma velas de 1 min sin huecos: un minuto sin operaciones queda plano con el último cierre y volumen 0.
Salida: datos/PAXGUSDT_1m.npy y datos/XAUUSDT_um_1m.npy (milisegundos, apertura, máximo, mínimo, cierre, volumen) y el resumen.
Uso: python -I t22_oro_datos.py"""
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
CRUDOS = os.path.join(DATOS, "oro_crudos")
H = {"User-Agent": "binarias-oro"}
UTC = dt.timezone.utc
FUENTES = {
    "PAXGUSDT": {"tipo": "spot", "desde": (2020, 8), "api": "https://api.binance.com/api/v3/klines", "limite": 1000,
                 "salida": os.path.join(DATOS, "PAXGUSDT_1m.npy")},
    "XAUUSDT": {"tipo": "futures/um", "desde": (2025, 12), "api": "https://fapi.binance.com/fapi/v1/klines", "limite": 1500,
                "salida": os.path.join(DATOS, "XAUUSDT_um_1m.npy")},
}


def bajar(url, intentos=4):
    for i in range(intentos):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def ms(x):
    x = int(float(x))
    return x // 1000 if x > 10 ** 14 else x  # desde 2025 el contado viene en microsegundos


def filas_csv(contenido):
    out = []
    for r in csv.reader(io.StringIO(contenido.decode("utf-8", "replace"))):
        if not r or not r[0].strip().isdigit():
            continue  # encabezado
        out.append((ms(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])))
    return out


def meses(desde, hasta):
    y, m = desde
    while (y, m) <= hasta:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def armar(sim, f):
    os.makedirs(os.path.join(CRUDOS, sim), exist_ok=True)
    hoy = dt.datetime.now(UTC)
    ultimo_mes = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
    filas, faltan = [], []
    for y, m in meses(f["desde"], ultimo_mes):
        nombre = f"{sim}-1m-{y}-{m:02d}.zip"
        ruta = os.path.join(CRUDOS, sim, nombre)
        if not os.path.exists(ruta):
            z = bajar(f"https://data.binance.vision/data/{f['tipo']}/monthly/klines/{sim}/1m/{nombre}")
            if z is None:
                faltan.append(f"{y}-{m:02d}")
                continue
            open(ruta, "wb").write(z)
        with zipfile.ZipFile(ruta) as zf:
            for n in zf.namelist():
                filas += filas_csv(zf.read(n))
    # lo que no está en archivos mensuales (el mes en curso y los meses que falten): por la API
    desde_ms = (max(r[0] for r in filas) + 60000) if filas else int(dt.datetime(*f["desde"], 1, tzinfo=UTC).timestamp() * 1000)
    if faltan and not filas:
        desde_ms = int(dt.datetime(*f["desde"], 1, tzinfo=UTC).timestamp() * 1000)
    ahora_ms = int(time.time() * 1000)
    n_api = 0
    while desde_ms < ahora_ms - 60000:
        x = json.loads(bajar(f"{f['api']}?symbol={sim}&interval=1m&startTime={desde_ms}&limit={f['limite']}") or b"[]")
        x = [k for k in x if int(k[6]) < ahora_ms]
        if not x:
            break
        filas += [(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in x]
        desde_ms = int(x[-1][0]) + 60000
        n_api += 1
        time.sleep(0.35)
    filas = sorted(dict((r[0], r) for r in filas).values())
    a = np.array(filas, dtype=float)
    t = (a[:, 0] // 60000).astype(np.int64)
    t0, t1 = int(t[0]), int(t[-1])
    n = t1 - t0 + 1
    o, h, l, c, v = (np.full(n, np.nan) for _ in range(5))
    i = t - t0
    o[i], h[i], l[i], c[i], v[i] = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    hueco = np.isnan(c)
    ult = c.copy()
    idx = np.where(~hueco, np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    ult = c[idx]
    o[hueco], h[hueco], l[hueco], c[hueco], v[hueco] = ult[hueco], ult[hueco], ult[hueco], ult[hueco], 0.0
    # int64 explícito: en Windows, numpy 1.x arma np.arange con enteros de 32 bits y minutos × 60.000 se desborda
    out = np.column_stack([(np.arange(t0, t1 + 1, dtype=np.int64) * 60000).astype(float), o, h, l, c, v])
    assert np.all(np.diff(out[:, 0]) == 60000) and 1.5e12 < out[0, 0] < 1.9e12, "marcas de tiempo inválidas"
    np.save(f["salida"], out)
    plano = float(((out[:, 2] == out[:, 3]) & ~hueco).mean())
    f10 = out[:, 4]
    k = np.arange(0, n - 10, 10)
    mov10 = f10[k + 9] - out[k, 1]
    return {"simbolo": sim, "desde": dt.datetime.fromtimestamp(t0 * 60, UTC).strftime("%Y-%m-%d %H:%M"),
            "hasta": dt.datetime.fromtimestamp(t1 * 60, UTC).strftime("%Y-%m-%d %H:%M"), "minutos": n, "rellenados": int(hueco.sum()),
            "planos_con_operaciones": round(100 * plano, 2), "sin_movimiento_a_10_min": round(100 * float((mov10 == 0).mean()), 2),
            "meses_sin_archivo": faltan, "pedidos_a_la_api": n_api}


def main():
    os.makedirs(CRUDOS, exist_ok=True)
    res = {}
    for sim, f in FUENTES.items():
        r = armar(sim, f)
        res[sim] = r
        print(f"{sim}: {r['minutos']:,} minutos del {r['desde']} al {r['hasta']} (UTC) · rellenados {r['rellenados']:,} "
              f"({100 * r['rellenados'] / r['minutos']:.1f} %) · velas planas con operaciones {r['planos_con_operaciones']} % · "
              f"10 min sin movimiento {r['sin_movimiento_a_10_min']} % · meses sin archivo {r['meses_sin_archivo'] or 'ninguno'} · "
              f"pedidos a la API {r['pedidos_a_la_api']}".replace(",", "."), flush=True)
    json.dump(res, open(os.path.join(AQUI, "t22_oro_datos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
