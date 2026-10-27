"""Fase B1: auditoría de las velas de 1 minuto (BTC y ETH, futuros USDⓈ-M de Binance).

Comprueba, sin modificar nada: orden y duplicados, huecos (minutos que faltan), coherencia OHLC, velas sin volumen,
saltos extremos entre minutos y la cobertura por año. Uso: python3 -I b1_auditoria_datos.py"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metricas import ruta_velas  # noqa: E402

for s in ("BTCUSDT", "ETHUSDT"):
    a = np.load(ruta_velas(s))
    t = a[:, 0].astype("int64")
    o, h, l, c, v = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
    dt_ = np.diff(t)
    print(f"=== {s}: {len(t):,} velas, {pd.Timestamp(t[0], unit='ms')} a {pd.Timestamp(t[-1], unit='ms')}")
    esperadas = (t[-1] - t[0]) // 60000 + 1
    print(f"  minutos esperados {esperadas:,} · faltan {esperadas - len(t):,} · duplicados {(dt_ == 0).sum()} · "
          f"desordenados {(dt_ < 0).sum()} · no múltiplos de 60 s {(t % 60000 != 0).sum()}")
    huecos = np.flatnonzero(dt_ > 60000)
    if len(huecos):
        largos = sorted(((dt_[k] // 60000 - 1, pd.Timestamp(t[k], unit='ms')) for k in huecos), reverse=True)[:8]
        print(f"  huecos: {len(huecos)}; los más largos (minutos, desde): " + "; ".join(f"{m} ({ts:%Y-%m-%d %H:%M})" for m, ts in largos))
    malas = (h < np.maximum(o, c)) | (l > np.minimum(o, c)) | (h < l) | (np.minimum.reduce([o, h, l, c]) <= 0)
    print(f"  velas OHLC incoherentes {malas.sum()} · sin volumen {(v == 0).sum()} ({(v == 0).mean() * 100:.3f} %)")
    r = np.abs(np.diff(np.log(c))) * 100
    print(f"  salto de cierre a cierre: p99,99 {np.percentile(r, 99.99):.2f} % · máximo {r.max():.2f} % "
          f"({pd.Timestamp(t[1:][r.argmax()], unit='ms')}) · minutos con |salto| > 3 %: {(r > 3).sum()}")
    gap_ap = np.abs(o[1:] / c[:-1] - 1) * 100
    print(f"  apertura frente al cierre anterior: media {gap_ap.mean():.4f} % · > 0,5 %: {(gap_ap > 0.5).sum()}")
    anios = pd.Series(1, index=pd.to_datetime(t, unit="ms")).groupby(lambda x: x.year).size()
    print("  velas por año: " + ", ".join(f"{y}: {n:,} ({n / (366 if y % 4 == 0 else 365) / 1440 * 100:.2f} %)" for y, n in anios.items()))
