"""Velas, índice de precio e interés abierto del laboratorio (11/11/2026).

- Historia: datos\\BTCUSDT_1m.npy, copia del archivo del centinela (columnas: apertura en ms, o, h, l, c, v). El laboratorio
  no lee ni escribe en la carpeta del centinela mientras corre.
- Rejilla densa de 1 min alineada a 15 min (NaN donde falta una vela): las ventanas van por tiempo y una vela que falta
  anula la señal en lugar de inventarla. Solo velas cerradas (hora de cierre < ahora), como semaforo.velas_ohlc.
- Interés abierto: el archivo de data.binance.vision lleva la marca 5 min antes que el servicio en vivo, así que en la
  historia se usa el margen de 600 s de cuant\\c9c_interes.py y en vivo la fórmula de semaforo.cambio_interes.
- Binance va directo (como el centinela); nada de esto usa llaves."""
import calendar
import csv
import glob
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import DATOS, log  # noqa: E402

HIST = os.path.join(DATOS, "BTCUSDT_1m.npy")
INTERES_NPZ = os.path.join(DATOS, "interes.npz")
INDICE_NPZ = os.path.join(DATOS, "indice.npz")
FAPI = "https://fapi.binance.com"
CABECERA = {"User-Agent": "laboratorio-binarias"}


def bajar(ruta, intentos=3, espera=3):
    ultimo = None
    for k in range(intentos):
        try:
            req = urllib.request.Request(FAPI + ruta, headers=CABECERA)
            return json.loads(urllib.request.urlopen(req, timeout=25).read())
        except Exception as ex:  # red caída, 429, certificado: se reintenta y luego se informa
            ultimo = ex
            time.sleep(espera * (k + 1))
    raise ultimo


def hora_binance():
    return int(bajar("/fapi/v1/time")["serverTime"]) // 1000


def velas_desde(desde_s, limite=1500):
    """Velas de 1 min de futuros cerradas desde `desde_s` (apertura, en s): [(t, o, h, l, c, v)]."""
    x = bajar(f"/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit={limite}&startTime={int(desde_s) * 1000}")
    ahora = time.time() * 1000
    return [(int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in x if int(k[6]) < ahora]


def indice_desde(desde_s, limite=1500):
    x = bajar(f"/fapi/v1/indexPriceKlines?pair=BTCUSDT&interval=1m&limit={limite}&startTime={int(desde_s) * 1000}")
    ahora = time.time() * 1000
    return [(int(k[0]) // 1000, float(k[4])) for k in x if int(k[6]) < ahora]


def interes_desde(desde_s=None, limite=500):
    q = f"/futures/data/openInterestHist?symbol=BTCUSDT&period=5m&limit={limite}"
    if desde_s:
        q += f"&startTime={int(desde_s) * 1000}"
    return sorted((int(k["timestamp"]) // 1000, float(k["sumOpenInterest"])) for k in bajar(q))


def historia(desde):
    """Velas de la historia desde `desde` (s): t en int64 y o, h, l, c, v en float64."""
    a = np.load(HIST, mmap_mode="r")
    t = (np.asarray(a[:, 0]) // 1000).astype(np.int64)
    i = int(np.searchsorted(t, desde))
    b = np.array(a[i:, 1:6], dtype=np.float64)
    return t[i:].copy(), b[:, 0], b[:, 1], b[:, 2], b[:, 3], b[:, 4]


class Velas:
    """Rejilla densa de velas de 1 min desde t0 (múltiplo de 900 s) que crece en vivo."""

    def __init__(self, t, o, h, l, c, v, margen=60 * 24 * 45):
        t = np.asarray(t, dtype=np.int64)
        self.t0 = int(-(-int(t[0]) // 900) * 900)
        m = t >= self.t0
        idx = (t[m] - self.t0) // 60
        self.n = int(idx[-1]) + 1
        self.A = np.full((5, self.n + margen), np.nan)
        for k, x in enumerate((o, h, l, c, v)):
            self.A[k, idx] = np.asarray(x, dtype=np.float64)[m]
        self.I = np.full(self.n + margen, np.nan)  # cierre del índice de precio

    def _crecer(self, necesita):
        if necesita <= self.A.shape[1]:
            return
        extra = max(necesita - self.A.shape[1], 60 * 24 * 30)
        self.A = np.concatenate([self.A, np.full((5, extra), np.nan)], axis=1)
        self.I = np.concatenate([self.I, np.full(extra, np.nan)])

    def poner(self, filas):
        """Agrega velas (t, o, h, l, c, v); devuelve cuántas eran nuevas."""
        nuevas = 0
        for t, o, h, l, c, v in filas:
            i = (int(t) - self.t0) // 60
            if i < 0:
                continue
            self._crecer(i + 1)
            if self.A[3, i] != self.A[3, i]:
                nuevas += 1
            self.A[:, i] = (o, h, l, c, v)
            self.n = max(self.n, i + 1)
        return nuevas

    def poner_indice(self, filas):
        for t, c in filas:
            i = (int(t) - self.t0) // 60
            if i >= 0:
                self._crecer(i + 1)
                self.I[i] = c

    @property
    def O(self):
        return self.A[0, :self.n]

    @property
    def H(self):
        return self.A[1, :self.n]

    @property
    def L(self):
        return self.A[2, :self.n]

    @property
    def C(self):
        return self.A[3, :self.n]

    @property
    def V(self):
        return self.A[4, :self.n]

    def t_ultima(self):
        """Apertura de la última vela presente."""
        return self.t0 + 60 * (self.n - 1)

    def tiempos(self):
        return self.t0 + 60 * np.arange(self.n, dtype=np.int64)

    def recorte(self, desde, hasta=None):
        """Copia de la rejilla entre `desde` y `hasta` (aperturas en s), con t0 alineado a 15 min."""
        a = max(0, (int(-(-int(desde) // 900) * 900) - self.t0) // 60)
        b = self.n if hasta is None else min(self.n, (int(hasta) - self.t0) // 60 + 1)
        nueva = Velas.__new__(Velas)
        nueva.t0 = self.t0 + 60 * a
        nueva.n = b - a
        nueva.A = self.A[:, a:b].copy()
        nueva.I = self.I[a:b].copy()
        return nueva


class Interes:
    """Instantáneas de 5 min del interés abierto: las del archivo y las del servicio en vivo, cada una con su fórmula."""

    def __init__(self, ta=None, oa=None):
        self.ta = np.zeros(0, dtype=np.int64) if ta is None else np.asarray(ta, dtype=np.int64)
        self.oa = np.zeros(0) if oa is None else np.asarray(oa, dtype=np.float64)
        self.tv = np.zeros(0, dtype=np.int64)
        self.ov = np.zeros(0)
        self.corte = int(self.ta[-1]) + 900 if len(self.ta) else 0

    def poner_vivo(self, filas):
        if not filas:
            return
        d = {int(t): float(x) for t, x in zip(self.tv.tolist(), self.ov.tolist())}
        d.update({int(t): float(x) for t, x in filas})
        ks = sorted(d)
        self.tv = np.array(ks, dtype=np.int64)
        self.ov = np.array([d[k] for k in ks])

    @staticmethod
    def _cambio(T, ts, oi, a, b):
        out = np.full(len(T), np.nan)
        if len(ts) == 0:
            return out
        ia = np.searchsorted(ts, T - a, side="right") - 1
        ib = np.searchsorted(ts, T - b, side="right") - 1
        ok = (ia >= 0) & (ib >= 0)
        ia0, ib0 = np.maximum(ia, 0), np.maximum(ib, 0)
        ok &= ((T - a) - ts[ia0] <= 600) & ((T - b) - ts[ib0] <= 600) & (oi[ib0] > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[ok] = oi[ia0[ok]] / oi[ib0[ok]] - 1
        return out

    def cambio(self, T):
        """Cambio del interés abierto para cada decisión T (cierre de 5 min): NaN si falta el dato."""
        T = np.asarray(T, dtype=np.int64)
        out = np.full(len(T), np.nan)
        arch = T < self.corte
        if arch.any():
            out[arch] = self._cambio(T[arch], self.ta, self.oa, 600, 1500)       # c9c_interes.py, margen 600 s
        if (~arch).any():
            out[~arch] = self._cambio(T[~arch], self.tv, self.ov, 300, 1200)     # semaforo.cambio_interes
        return out


# ---------------------------------------------------------------- archivos de la historia (se arman una vez en el PC)
def armar_interes(carpeta):
    """npz con las instantáneas de 5 min de los zip diarios de métricas (columna 2 = sumOpenInterest)."""
    filas = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "BTCUSDT-metrics-*.zip"))):
        with zipfile.ZipFile(ruta) as z:
            for fila in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")):
                if len(fila) < 3 or not fila[0][:1].isdigit():
                    continue
                try:
                    t = calendar.timegm(time.strptime(fila[0][:19], "%Y-%m-%d %H:%M:%S"))
                    filas.append((t, float(fila[2])))
                except ValueError:
                    continue
    filas.sort()
    t = np.array([f[0] for f in filas], dtype=np.int64)
    oi = np.array([f[1] for f in filas], dtype=np.float64)
    t, u = np.unique(t, return_index=True)
    np.savez_compressed(INTERES_NPZ, t=t, oi=oi[u])
    return len(t)


def armar_indice(carpeta):
    """npz con el cierre de 1 min del índice de precio (zip mensuales de indexPriceKlines)."""
    filas = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "BTCUSDT-indice-1m-*.zip"))):
        with zipfile.ZipFile(ruta) as z:
            for fila in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")):
                if len(fila) < 5 or not fila[0][:1].isdigit():
                    continue
                t = int(fila[0])
                filas.append((t // 1000 if t > 10 ** 11 else t, float(fila[4])))
    filas.sort()
    t = np.array([f[0] for f in filas], dtype=np.int64)
    c = np.array([f[1] for f in filas], dtype=np.float64)
    t, u = np.unique(t, return_index=True)
    np.savez_compressed(INDICE_NPZ, t=t, c=c[u])
    return len(t)


def cargar_interes():
    if not os.path.exists(INTERES_NPZ):
        return Interes()
    z = np.load(INTERES_NPZ)
    return Interes(z["t"], z["oi"])


def cargar_indice(vel):
    if os.path.exists(INDICE_NPZ):
        z = np.load(INDICE_NPZ)
        t = z["t"].astype(np.int64)
        m = t >= vel.t0
        vel.poner_indice(zip(t[m].tolist(), z["c"][m].tolist()))


def rellenar(vel, interes=None, con=None, hasta=None):
    """Trae de Binance las velas (y el índice) que faltan desde la última hasta ahora; guarda lo nuevo en la base."""
    hasta = hasta or time.time()
    total = 0
    desde = vel.t_ultima() + 60
    while desde + 60 < hasta:
        filas = velas_desde(desde)
        if not filas:
            break
        total += vel.poner(filas)
        if con is not None:
            con.executemany("INSERT OR REPLACE INTO velas (t, o, h, l, c, v) VALUES (?, ?, ?, ?, ?, ?)", filas)
            con.commit()
        if filas[-1][0] + 60 <= desde:
            break
        desde = filas[-1][0] + 60
        if len(filas) < 1500:
            break
    # índice: desde la última vela con índice
    presentes = np.flatnonzero(vel.I[:vel.n] == vel.I[:vel.n])
    desde = vel.t0 + 60 * (int(presentes[-1]) + 1) if len(presentes) else vel.t_ultima() - 3 * 86400
    vueltas = 0
    while desde + 60 < hasta and vueltas < 40:
        vueltas += 1
        try:
            filas = indice_desde(desde)
        except Exception as ex:
            log(f"índice sin dato ({type(ex).__name__})")
            break
        if not filas:
            break
        vel.poner_indice(filas)
        if con is not None:
            con.executemany("INSERT OR REPLACE INTO indice (t, c) VALUES (?, ?)", filas)
            con.commit()
        desde = filas[-1][0] + 60
        if len(filas) < 1500:
            break
    if interes is not None:
        desde = max(int(interes.tv[-1]) + 1 if len(interes.tv) else 0, interes.corte - 3600, int(hasta) - 29 * 86400)
        vueltas = 0
        while desde < hasta - 300 and vueltas < 40:
            vueltas += 1
            try:
                filas = interes_desde(desde)
            except Exception as ex:
                log(f"interés abierto sin dato ({type(ex).__name__})")
                break
            if not filas:
                break
            interes.poner_vivo(filas)
            if con is not None:
                con.executemany("INSERT OR REPLACE INTO interes (t, oi) VALUES (?, ?)", filas)
                con.commit()
            if filas[-1][0] + 1 <= desde:
                break
            desde = filas[-1][0] + 1
            if len(filas) < 500:
                break
    return total


def desde_base(vel, interes, con):
    """Recupera lo que el laboratorio ya había guardado en vivo (velas, índice e interés)."""
    filas = con.execute("SELECT t, o, h, l, c, v FROM velas WHERE t > ? ORDER BY t", (vel.t_ultima(),)).fetchall()
    vel.poner(filas)
    vel.poner_indice(con.execute("SELECT t, c FROM indice WHERE t >= ? ORDER BY t", (vel.t0,)).fetchall())
    if interes is not None:
        interes.poner_vivo(con.execute("SELECT t, oi FROM interes ORDER BY t").fetchall())
    return len(filas)
