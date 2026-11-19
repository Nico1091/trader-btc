"""C3 (03/11/2026): lectura del mercado en vivo para las binarias. No decide apuestas: da contexto.

Fuentes y red (regla de Nicolás: Binance directo; todo lo demás por Tor, SOCKS 127.0.0.1:9050):
- Binance (directo): velas de 1 min con compra agresiva de los últimos 65 días, financiación, interés abierto, posición
  larga/corta de las cuentas y libro de órdenes (muros de liquidez y desequilibrio, lo que da un mapa de calor de L2).
- Deribit (por Tor): opciones de BTC y ETH. Con Black-Scholes propio se calcula la exposición gamma de los creadores de
  mercado (GEX, convención habitual: calls suman, puts restan), el gamma flip (precio donde la GEX cambia de signo), los
  muros de calls y de puts (mayor interés abierto), la exposición delta (DEX), la de vanna (VEX), el flujo de opciones de
  las últimas operaciones y el índice de volatilidad DVOL.
- CBOE y Tesoro de EE. UU. (por Tor): VIX, S&P 500 y bono de 10 años (diarios). FRED y Yahoo rechazan Tor.
- Banco Mundial (por Tor): crecimiento del PIB mundial (anual): contexto de largo plazo, sin valor para 10 min.
- Estado actual de las seis dimensiones (base.py) y régimen del HMM (c2), con el acierto que cada estado tuvo a ciegas.
Uso: python -I c3_contexto_vivo.py
"""
import datetime as dt
import json
import math
import os
import subprocess
import sys
import time
import urllib.request

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base as B  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "resultados")
COL = dt.timezone(dt.timedelta(hours=-5))
H = {"User-Agent": "binarias-contexto"}


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def binance(url, timeout=20):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout).read())


def tor(url, timeout=90):
    r = subprocess.run(["curl", "-s", "-L", "--max-time", str(timeout), "--socks5-hostname", f"ctx{int(time.time()) % 9999}:x@127.0.0.1:9050",
                        "-A", "Mozilla/5.0", url], capture_output=True, timeout=timeout + 20)
    return r.stdout.decode("utf-8", "replace")


def velas_vivas(sim, dias=65):
    fin = int(time.time() * 1000)
    ini = fin - dias * 86400 * 1000
    filas = []
    while ini < fin:
        x = binance(f"https://fapi.binance.com/fapi/v1/klines?symbol={sim}&interval=1m&startTime={ini}&limit=1500")
        if not x:
            break
        filas += [k for k in x if int(k[6]) < fin]
        ini = int(x[-1][0]) + 60000
        if len(x) < 1500:
            break
    a = np.array([[int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), float(k[9])] for k in filas])
    return a[:, 0].astype(np.int64), a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5], a[:, 6]


# ---------------------------------------------------------------- opciones
def phi(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def griegas(S, K, T, sig, tipo):
    if T <= 0 or sig <= 0:
        return 0.0, 0.0, 0.0
    d1 = (math.log(S / K) + 0.5 * sig * sig * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    gamma = phi(d1) / (S * sig * math.sqrt(T))
    nd1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
    delta = nd1 if tipo == "C" else nd1 - 1
    vanna = -phi(d1) * d2 / sig
    return gamma, delta, vanna


def opciones(moneda):
    txt = tor(f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={moneda}&kind=option")
    d = json.loads(txt)["result"]
    ahora = time.time()
    filas = []
    for x in d:
        partes = x["instrument_name"].split("-")  # BTC-28NOV26-80000-C
        venc = dt.datetime.strptime(partes[1], "%d%b%y").replace(hour=8, tzinfo=dt.timezone.utc).timestamp()
        T = (venc - ahora) / (365 * 86400)
        if T <= 0 or not x.get("mark_iv"):
            continue
        filas.append({"K": float(partes[2]), "tipo": partes[3], "T": T, "iv": x["mark_iv"] / 100, "oi": x.get("open_interest") or 0.0,
                      "S": x.get("underlying_price") or 0.0, "vol": x.get("volume") or 0.0})
    try:  # índice de contado de Deribit (el precio de cada vencimiento lleva la base de los futuros)
        S = float(json.loads(tor(f"https://www.deribit.com/api/v2/public/get_index_price?index_name={moneda.lower()}_usd"))["result"]["index_price"])
    except Exception:
        S = float(np.median([f["S"] for f in filas if f["S"]]))
    def gex_en(S_):
        g = 0.0
        for f in filas:
            ga, _, _ = griegas(S_, f["K"], f["T"], f["iv"], f["tipo"])
            g += (1 if f["tipo"] == "C" else -1) * f["oi"] * ga * S_ * S_ * 0.01
        return g
    gex = gex_en(S)
    malla = np.linspace(0.8 * S, 1.2 * S, 81)
    valores = [gex_en(s) for s in malla]
    flip = None
    for a, b, va, vb in zip(malla[:-1], malla[1:], valores[:-1], valores[1:]):
        if va == 0 or va * vb < 0:
            flip = a + (b - a) * (abs(va) / (abs(va) + abs(vb)))
            if abs(flip - S) < 0.2 * S:
                break
    dex = sum(f["oi"] * griegas(S, f["K"], f["T"], f["iv"], f["tipo"])[1] * S for f in filas)
    vex = sum((1 if f["tipo"] == "C" else -1) * f["oi"] * griegas(S, f["K"], f["T"], f["iv"], f["tipo"])[2] * S * 0.01 for f in filas)
    cerca = [f for f in filas if f["T"] < 45 / 365]
    def muro(tipo):
        oi = {}
        for f in cerca:
            if f["tipo"] == tipo:
                oi[f["K"]] = oi.get(f["K"], 0) + f["oi"]
        return max(oi.items(), key=lambda kv: kv[1]) if oi else (None, 0)
    calls = sum(f["oi"] for f in filas if f["tipo"] == "C")
    puts = sum(f["oi"] for f in filas if f["tipo"] == "P")
    vol_c = sum(f["vol"] for f in filas if f["tipo"] == "C")
    vol_p = sum(f["vol"] for f in filas if f["tipo"] == "P")
    flujo = None
    try:
        tr = json.loads(tor(f"https://www.deribit.com/api/v2/public/get_last_trades_by_currency?currency={moneda}&kind=option&count=1000"))["result"]["trades"]
        compra = sum(x["amount"] for x in tr if x["direction"] == "buy")
        venta = sum(x["amount"] for x in tr if x["direction"] == "sell")
        cc = sum(x["amount"] for x in tr if x["instrument_name"].endswith("-C"))
        pp = sum(x["amount"] for x in tr if x["instrument_name"].endswith("-P"))
        h0 = min(x["timestamp"] for x in tr) / 1000
        flujo = {"compra": compra, "venta": venta, "calls": cc, "puts": pp, "desde": h0}
    except Exception:
        pass
    dvol = None
    try:
        fin = int(time.time() * 1000)
        dv = json.loads(tor(f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={moneda}&start_timestamp={fin - 30 * 86400000}&end_timestamp={fin}&resolution=3600"))["result"]["data"]
        cierres = [x[4] for x in dv]
        dvol = (cierres[-1], float(np.mean(np.array(cierres) <= cierres[-1])))
    except Exception:
        pass
    return {"S": S, "gex": gex, "flip": flip, "dex": dex, "vex": vex, "muro_calls": muro("C"), "muro_puts": muro("P"),
            "pc_oi": puts / calls if calls else None, "pc_vol": vol_p / vol_c if vol_c else None, "flujo": flujo, "dvol": dvol, "n": len(filas)}


def fred(serie):
    txt = tor(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}")
    filas = [l.split(",") for l in txt.strip().splitlines()[1:] if l and not l.endswith(",.") and "," in l]
    filas = [(f[0], float(f[1])) for f in filas if f[1] not in (".", "")]
    return filas[-1], filas[-6] if len(filas) > 6 else filas[0]


def main():
    L = [f"C3 · lectura del mercado en vivo · {dt.datetime.now(COL):%d/%m/%Y %H:%M} (hora de Colombia) · contexto, no decide apuestas", ""]
    c1 = {}
    for sim in ("BTCUSDT", "ETHUSDT"):
        ruta = os.path.join(SALIDA, f"c1_{sim}.txt")
        c1[sim] = open(ruta, encoding="utf-8").read() if os.path.exists(ruta) else ""
    for sim in ("BTCUSDT", "ETHUSDT"):
        t, o, h, l, c, v, tb = velas_vivas(sim)
        d = B.construir(sim, verbose=False, velas=(t, o, h, l, c, v, tb), minimo=60 * 1440, sin_futuro=True)
        k = -1
        F = d["F"]
        precio = c[-1]
        cambio = lambda m: 100 * (c[-1] / c[-1 - m] - 1)
        L.append(f"{sim}: {es(precio, 2)} · 1 h {es(cambio(60), 2)} % · 4 h {es(cambio(240), 2)} % · 24 h {es(cambio(1440), 2)} % · 7 días {es(cambio(10080), 2)} % · 30 días {es(cambio(43200), 2)} %")
        L.append(f"  estado de las seis dimensiones en la última decisión ({dt.datetime.fromtimestamp(int(d['t'][k]), COL):%H:%M}):")
        for var in B.NOMBRES:
            nom = B.NOMBRES[var][int(F[var][k])]
            linea = next((x.strip() for x in c1[sim].splitlines() if x.strip().startswith(f"D{B.DIMENSION[var]} {nom} ")), "")
            dato = linea.split(":", 1)[1].strip() if linea else ""
            L.append(f"    D{B.DIMENSION[var]} {nom:<28} {dato}")
        ult = d["extra"]
        L.append(f"  impulso de 15 min: z {es(float(ult['z15'][k]), 2)} · flujo de órdenes de 15 min: {es(100 * float(ult['delta'][k]), 1)} % neto comprador · ATR frente a su mediana: {es(float(ult['razon_atr'][k]), 2)}")
        # derivados de Binance
        try:
            f = binance(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sim}")
            oi = binance(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={sim}&period=1h&limit=25")
            ls = binance(f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={sim}&period=1h&limit=1")
            dep = binance(f"https://fapi.binance.com/fapi/v1/depth?symbol={sim}&limit=1000")
            bids = np.array(dep["bids"], float)
            asks = np.array(dep["asks"], float)
            mid = (bids[0, 0] + asks[0, 0]) / 2
            b05 = bids[bids[:, 0] >= mid * 0.995, 1].sum()
            a05 = asks[asks[:, 0] <= mid * 1.005, 1].sum()
            mb = bids[np.argmax(bids[:, 1])]
            ma = asks[np.argmax(asks[:, 1])]
            o0, o1 = float(oi[0]["sumOpenInterestValue"]), float(oi[-1]["sumOpenInterestValue"])
            L.append(f"  derivados (Binance): financiación {es(100 * float(f['lastFundingRate']), 4)} % cada 8 h · interés abierto {es(o1 / 1e6, 0)} M USDT ({es(100 * (o1 / o0 - 1), 1)} % en 24 h) · "
                     f"cuentas largas/cortas {es(float(ls[0]['longShortRatio']), 2)}")
            L.append(f"  libro (L2, ±0,5 %): compras {es(b05, 1)} frente a ventas {es(a05, 1)} ({es(100 * (b05 - a05) / max(b05 + a05, 1e-9), 1)} % de desequilibrio) · "
                     f"mayor muro de compra {es(mb[0], 1)} ({es(mb[1], 1)}) · de venta {es(ma[0], 1)} ({es(ma[1], 1)})")
        except Exception as e:
            L.append(f"  derivados de Binance: no se pudieron leer ({type(e).__name__})")
        # HMM
        try:
            P = np.load(os.path.join(SALIDA, f"c2_{sim}_hmm.npy"), allow_pickle=True).item()
            from c2_regimenes import hmm_filtrar
            hr = t // 3600
            corte = np.flatnonzero(np.diff(hr)) + 1
            ini, fin = np.r_[0, corte], np.r_[corte, len(t)] - 1
            X = np.column_stack([np.log(c[fin] / o[ini]), np.log(np.maximum(np.maximum.reduceat(h, ini) / np.minimum.reduceat(l, ini), 1 + 1e-9))])
            pr = hmm_filtrar(X[:-1], P)[-1]
            L.append(f"  régimen (HMM de c2): {['calma', 'normal', 'agitado'][int(np.argmax(pr))]} ({es(100 * pr.max(), 0)} %)")
        except Exception as e:
            L.append(f"  régimen HMM: sin calcular ({type(e).__name__})")
        L.append("")
    for moneda in ("BTC", "ETH"):
        try:
            op = opciones(moneda)
            L.append(f"OPCIONES {moneda} (Deribit, {op['n']} contratos, subyacente {es(op['S'], 0)}):")
            L.append(f"  GEX {es(op['gex'] / 1e6, 1)} M USD por 1 % ({'positiva: los creadores frenan los movimientos' if op['gex'] > 0 else 'negativa: los creadores amplifican los movimientos'}) · "
                     f"gamma flip {es(op['flip'], 0) if op['flip'] else 'fuera de ±20 %'}")
            L.append(f"  muro de calls {es(op['muro_calls'][0] or 0, 0)} ({es(op['muro_calls'][1], 0)} contratos) · muro de puts {es(op['muro_puts'][0] or 0, 0)} ({es(op['muro_puts'][1], 0)}) · "
                     f"puts/calls por interés abierto {es(op['pc_oi'] or 0, 2)} y por volumen de 24 h {es(op['pc_vol'] or 0, 2)}")
            L.append(f"  DEX {es(op['dex'] / 1e6, 0)} M USD · VEX {es(op['vex'] / 1e6, 1)} M USD por punto de volatilidad")
            if op["flujo"]:
                fl = op["flujo"]
                L.append(f"  flujo de opciones (últimas 1.000 operaciones desde {dt.datetime.fromtimestamp(fl['desde'], COL):%d/%m %H:%M}): compras {es(fl['compra'], 0)} · ventas {es(fl['venta'], 0)} · calls {es(fl['calls'], 0)} · puts {es(fl['puts'], 0)}")
            if op["dvol"]:
                L.append(f"  DVOL {es(op['dvol'][0], 1)} (percentil {es(100 * op['dvol'][1], 0)} de los últimos 30 días)")
        except Exception as e:
            L.append(f"OPCIONES {moneda}: no se pudieron leer por Tor ({type(e).__name__}: {str(e)[:80]})")
    L.append("")
    L.append("MACRO Y WALL STREET (CBOE y Tesoro de EE. UU., diarios; contexto, no señal de 10 min):")
    for serie, nom in (("VIX", "VIX"), ("SPX", "S&P 500")):
        try:
            filas = [x.split(",") for x in tor(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{serie}_History.csv").strip().splitlines()[1:]]
            v1, v0 = float(filas[-1][-1]), float(filas[-6][-1])  # el cierre es la última columna
            L.append(f"  {nom}: {es(v1, 2)} al cierre del {filas[-1][0]} ({es(100 * (v1 / v0 - 1), 2)} % en 5 sesiones)")
        except Exception as e:
            L.append(f"  {nom}: sin dato ({type(e).__name__})")
    try:
        año = dt.datetime.now(COL).year
        filas = [x.split(",") for x in tor(f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{año}/all?type=daily_treasury_yield_curve&field_tdr_date_value={año}&page&_format=csv").strip().splitlines()]
        j = filas[0].index('"10 Yr"')
        L.append(f"  bono de 10 años de EE. UU.: {filas[1][j]} % el {filas[1][0]} ({filas[6][j]} % cinco sesiones antes)")
    except Exception as e:
        L.append(f"  bono de 10 años: sin dato ({type(e).__name__})")
    try:
        wb = json.loads(tor("https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=5"))[1]
        ult = next(x for x in wb if x["value"] is not None)
        L.append(f"  Banco Mundial: crecimiento del PIB mundial {es(ult['value'], 2)} % en {ult['date']} (anual: contexto de largo plazo, sin valor para binarias de 10 min a 1 día)")
    except Exception as e:
        L.append(f"  Banco Mundial: sin dato ({type(e).__name__})")
    os.makedirs(SALIDA, exist_ok=True)
    texto = "\n".join(L)
    open(os.path.join(SALIDA, "c3_contexto_vivo.txt"), "w", encoding="utf-8").write(texto + "\n")
    print(texto)


if __name__ == "__main__":
    main()
