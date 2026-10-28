"""A4 (27/10/2026): las estrategias medidas con los costos de PU Prime y MultiBank (CFD) frente a Binance futuros.

Pedido de Nicolás (Telegram, canal Informes, 27/10 2:21 p. m.): «hacer pequeñas pruebas acorde al agente, acorde a sus
estrategias implementadas» con los brokers PU Prime («residual activo») y MultiBank («residual pasivo»).

Qué mide, sobre las operaciones de investigacion/operaciones/ops_BTC.csv (Binance futuros 1 m, 2020-2026):
1. Binance futuros: entrada de creador 0,02 % o de tomador 0,05 %, salida de tomador 0,05 %, más la financiación real de
   cada liquidación (00, 08 y 16 UTC) que encuentra la posición abierta (data.binance.vision, SHA-256 comprobado).
2. CFD con diferencial fijo en dólares (BTCUSD 18,95 USD según FXStreet y 27,5 USD según DayTrading.com, sin verificar en la
   web del broker) y swap por noche si la posición sigue abierta al cierre del servidor (21:00 UTC de abril a octubre y
   22:00 UTC de noviembre a marzo): largo −18 %/año y corto +4 %/año (ForexChurch, sin fecha: sin verificar).
3. El capital mínimo para operar cada estrategia con 2 % de riesgo con un lote mínimo de 0,01 BTC.
Uso: python -I a4_costes_brokers.py > a4_costes_brokers.txt   (desde investigacion/plan-diario/)"""
import hashlib
import io
import os
import sys
import urllib.request
import zipfile

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
OPS = os.path.join(AQUI, "..", "operaciones", "ops_BTC.csv")
CACHE = os.path.join(os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos"), "funding")
COP_POR_USDT = 3177.85
CAPITAL_USDT = 40000 / COP_POR_USDT


def bajar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "trader-btc"})
    return urllib.request.urlopen(req, timeout=60).read()


def financiacion():
    """{segundo_utc: tasa} de BTCUSDT, 2020-01 a 2026-09, con caché local comprobada por SHA-256."""
    os.makedirs(CACHE, exist_ok=True)
    fr = {}
    for y in range(2020, 2027):
        for m in range(1, 13):
            if (y, m) > (2026, 9):
                break
            nombre = f"BTCUSDT-fundingRate-{y}-{m:02d}.zip"
            ruta = os.path.join(CACHE, nombre)
            if not os.path.exists(ruta):
                url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/{nombre}"
                z = bajar(url)
                if hashlib.sha256(z).hexdigest() != bajar(url + ".CHECKSUM").decode().split()[0]:
                    raise SystemExit("SHA-256 no coincide: " + nombre)
                open(ruta, "wb").write(z)
            with zipfile.ZipFile(ruta) as f:
                for linea in f.read(f.namelist()[0]).decode().splitlines():
                    p = linea.split(",")
                    if p[0].isdigit():
                        fr[int(p[0]) // 1000] = float(p[2])
    return fr


def noches(a, b):
    """Cierres de servidor (21:00 UTC abr-oct, 22:00 UTC nov-mar) entre a y b (segundos), ambos extremos dentro."""
    n, d = 0, pd.Timestamp(a, unit="s", tz="UTC").normalize()
    while d.timestamp() <= b:
        h = 21 if 4 <= d.month <= 10 else 22
        t = d.timestamp() + h * 3600
        if a < t <= b:
            n += 1
        d += pd.Timedelta(days=1)
    return n


def main():
    t = pd.read_csv(OPS, parse_dates=["entrada", "salida"])
    for c in ("entrada", "salida"):
        if t[c].dt.tz is None:
            t[c] = t[c].dt.tz_localize("UTC")
    t = t[t.estrategia.isin(["P05c", "P11", "P05b", "N8"])].copy()
    a = t.entrada.map(lambda x: int(x.timestamp())).to_numpy()
    b = t.salida.map(lambda x: int(x.timestamp())).to_numpy()
    fr = financiacion()
    k = np.array(sorted(fr))
    v = np.array([fr[x] for x in k])
    t["fin"] = [-lado * v[(k > i) & (k <= j)].sum() * 100 for lado, i, j in zip(t.lado, a, b)]
    t["noches"] = [noches(i, j) for i, j in zip(a, b)]
    cr = t.creador.astype(bool).to_numpy()
    t["binance"] = t.bruto - np.where(cr, 0.02, 0.05) - 0.05 + t.fin
    for nombre, spread in (("cfd_19", 18.95), ("cfd_27", 27.5)):
        swap = np.where(t.lado > 0, -18.0, 4.0) / 365 * t.noches
        t[nombre] = t.bruto - spread / t.pe * 100 + swap
    t["dist"] = np.where(t.apertura.notna(), (t.pe - t.apertura).abs() / t.pe, 0.03)
    print("A4 · estrategias medidas con costos de broker CFD frente a Binance futuros (BTC, % del nocional por operación)")
    print(f"Fuente: {os.path.relpath(OPS, AQUI)}, {len(t)} operaciones · financiación: {len(k)} liquidaciones (media "
          f"{v.mean() * 100:.4f} % cada 8 h)")
    print("Diferencial CFD: 18,95 USD (FXStreet) y 27,5 USD (DayTrading.com); swap largo −18 %/año, corto +4 %/año (sin verificar)\n")
    print(f"{'estrategia':10s} {'tramo':9s} {'ops':>4s}  {'Binance':>8s}  {'CFD 18,95':>9s}  {'CFD 27,5':>9s}  {'noches med.':>11s}")
    for e in ("P05c", "P11", "P05b", "N8"):
        for tramo, sel in (("2020-23", t.entrada < pd.Timestamp("2024-01-01", tz="UTC")),
                           ("2024-26", t.entrada >= pd.Timestamp("2024-01-01", tz="UTC"))):
            s = t[(t.estrategia == e) & sel]
            print(f"{e:10s} {tramo:9s} {len(s):4d}  {s.binance.mean():+8.3f}  {s.cfd_19.mean():+9.3f}  {s.cfd_27.mean():+9.3f}"
                  f"  {s.noches.mean():11.2f}")
    print("\nCapital mínimo para 2 % de riesgo con lote mínimo de 0,01 BTC (precio de referencia 80.857 USD, marca de Binance del 27/10):")
    lote = 0.01 * 80857
    for e in ("P05c", "P11", "P05b", "N8"):
        d = t[t.estrategia == e].dist.median()
        cap = lote * d / 0.02
        apal = lote / CAPITAL_USDT
        print(f"  {e}: distancia al stop mediana {d * 100:.2f} % -> capital mínimo {cap:,.0f} USD ({cap * COP_POR_USDT:,.0f} COP);"
              f" con 40.000 COP el lote mínimo exige {apal:.0f}x y un riesgo de {apal * d * 100:.0f} % por operación")


if __name__ == "__main__":
    main()
