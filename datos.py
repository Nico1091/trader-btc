"""Carga de históricos verificados: velas de 1 minuto y de 1 segundo, agregación a marcos mayores y métricas.

Solo se leen archivos con su marca .ok (suma SHA-256 verificada al bajarlos). Huecos y
duplicados se cuentan y se informan; nada se rellena inventando precios.
"""
import array
import csv
import datetime as dt
import glob
import hashlib
import io
import json
import os
import zipfile

CARPETA = os.path.dirname(os.path.abspath(__file__))
CRUDOS = os.path.join(CARPETA, "datos", "crudos")
CACHE = os.path.join(CARPETA, "datos", "cache")
MIN = 60_000


class Velas:
    """Columnas paralelas. t = apertura en ms UTC."""

    CAMPOS = ("t", "o", "h", "l", "c", "v", "tb", "n", "i0", "i1")

    def __init__(self):
        self.t = array.array("q")
        self.o = array.array("d")
        self.h = array.array("d")
        self.l = array.array("d")
        self.c = array.array("d")
        self.v = array.array("d")
        self.tb = array.array("d")          # volumen comprador agresor (taker buy base)
        self.n = array.array("d")           # número de operaciones de la vela
        self.i0 = array.array("q")          # primer índice de 1m de la vela (marcos mayores)
        self.i1 = array.array("q")          # último índice de 1m de la vela
        self.calidad = {}

    def __len__(self):
        return len(self.t)


def _archivos_verificados(subcarpeta):
    rutas = sorted(glob.glob(os.path.join(CRUDOS, subcarpeta, "*.zip")))
    return [r for r in rutas if os.path.exists(r + ".ok")]


def _ordenar_klines(rutas, intervalo="1m"):
    """Mensuales primero por mes, luego diarios; un día ya cubierto por su mes se omite."""
    mensuales = {}
    diarios = []
    for r in rutas:
        nombre = os.path.basename(r)[:-4]
        fecha = nombre.split(f"-{intervalo}-")[1]
        if len(fecha) == 7:
            mensuales[fecha] = r
        else:
            diarios.append((fecha, r))
    orden = [mensuales[k] for k in sorted(mensuales)]
    orden += [r for f, r in sorted(diarios) if f[:7] not in mensuales]
    return orden


def _huella(rutas):
    h = hashlib.sha256()
    for r in rutas:
        with open(r + ".ok", encoding="utf-8") as f:
            h.update(f.read().encode())
    return h.hexdigest()


_GUARDADOS = ("t", "o", "h", "l", "c", "v", "tb", "n")
_ANCHO = {"1s": 1000, "1m": MIN}


def cargar_1m(subcarpeta="contado-1m"):
    return cargar_velas(subcarpeta, "1m")


def cargar_velas(subcarpeta, intervalo="1m"):
    """Velas de `intervalo` («1s» o «1m») desde los archivos verificados, con caché binaria."""
    ancho = _ANCHO[intervalo]
    rutas = _ordenar_klines(_archivos_verificados(subcarpeta), intervalo)
    if not rutas:
        raise FileNotFoundError(f"no hay archivos verificados en datos/crudos/{subcarpeta}")
    huella = _huella(rutas)
    os.makedirs(CACHE, exist_ok=True)
    meta_ruta = os.path.join(CACHE, f"{subcarpeta}.json")
    velas = Velas()
    if os.path.exists(meta_ruta):
        with open(meta_ruta, encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("huella") == huella and tuple(meta.get("campos", ())) == _GUARDADOS:
            n = meta["n"]
            for campo in _GUARDADOS:
                arr = getattr(velas, campo)
                with open(os.path.join(CACHE, f"{subcarpeta}.{campo}.bin"), "rb") as f:
                    arr.fromfile(f, n)
            velas.calidad = meta["calidad"]
            return velas
    ultimo = -1
    duplicados = 0
    huecos = 0
    minutos_faltantes = 0
    for r in rutas:
        with zipfile.ZipFile(r) as z:
            nombre = z.namelist()[0]
            with z.open(nombre) as f:
                for fila in csv.reader(io.TextIOWrapper(f, encoding="utf-8")):
                    if not fila or not fila[0][:1].isdigit():
                        continue                      # cabecera
                    t = int(fila[0])
                    if t > 10 ** 14:                  # desde 2025 Binance publica microsegundos
                        t //= 1000
                    if t <= ultimo:
                        duplicados += 1
                        continue
                    if ultimo >= 0 and t - ultimo > ancho:
                        huecos += 1
                        minutos_faltantes += (t - ultimo) // ancho - 1
                    ultimo = t
                    velas.t.append(t)
                    velas.o.append(float(fila[1]))
                    velas.h.append(float(fila[2]))
                    velas.l.append(float(fila[3]))
                    velas.c.append(float(fila[4]))
                    velas.v.append(float(fila[5]))
                    velas.n.append(float(fila[8]))
                    velas.tb.append(float(fila[9]))
    velas.calidad = {
        "archivos": len(rutas), "velas": len(velas.t), "duplicados_descartados": duplicados,
        "huecos": huecos, ("minutos_faltantes" if intervalo == "1m" else "velas_faltantes"): minutos_faltantes,
        "desde_utc": dt.datetime.fromtimestamp(velas.t[0] / 1000, dt.timezone.utc).isoformat(),
        "hasta_utc": dt.datetime.fromtimestamp(velas.t[-1] / 1000, dt.timezone.utc).isoformat(),
    }
    for campo in _GUARDADOS:
        with open(os.path.join(CACHE, f"{subcarpeta}.{campo}.bin"), "wb") as f:
            getattr(velas, campo).tofile(f)
    with open(meta_ruta, "w", encoding="utf-8") as f:
        json.dump({"huella": huella, "n": len(velas.t), "campos": list(_GUARDADOS), "calidad": velas.calidad},
                  f, indent=1)
    return velas


def recortar(v, desde_ms, hasta_ms):
    """Copia de las velas con t en [desde_ms, hasta_ms)."""
    import bisect
    a = bisect.bisect_left(v.t, desde_ms)
    b = bisect.bisect_left(v.t, hasta_ms)
    out = Velas()
    for campo in _GUARDADOS:
        origen = getattr(v, campo)
        if len(origen) == len(v.t):
            getattr(out, campo).extend(origen[a:b])
    out.calidad = dict(v.calidad, recorte=[desde_ms, hasta_ms])
    return out


def agregar(v1, minutos):
    """Velas de `minutos` alineadas a múltiplos UTC. Guarda el tramo de 1m de cada una."""
    ancho = minutos * MIN
    out = Velas()
    n = len(v1)
    i = 0
    incompletas = 0
    while i < n:
        bloque = v1.t[i] // ancho
        j = i
        h, l, vol, tb, nn = v1.h[i], v1.l[i], 0.0, 0.0, 0.0
        tiene_n = len(v1.n) == n
        while j < n and v1.t[j] // ancho == bloque:
            if v1.h[j] > h:
                h = v1.h[j]
            if v1.l[j] < l:
                l = v1.l[j]
            vol += v1.v[j]
            tb += v1.tb[j]
            if tiene_n:
                nn += v1.n[j]
            j += 1
        if j - i < minutos:
            incompletas += 1
        out.t.append(bloque * ancho)
        out.o.append(v1.o[i])
        out.h.append(h)
        out.l.append(l)
        out.c.append(v1.c[j - 1])
        out.v.append(vol)
        out.tb.append(tb)
        out.n.append(nn)
        out.i0.append(i)
        out.i1.append(j - 1)
        i = j
    out.calidad = {"minutos": minutos, "velas": len(out), "incompletas": incompletas}
    return out


class Metricas:
    """Métricas de futuros cada 5 minutos: interés abierto, largos/cortos y flujo agresor."""

    def __init__(self):
        self.t = array.array("q")
        self.oi = array.array("d")           # interés abierto en BTC
        self.oi_usd = array.array("d")
        self.lsr_top = array.array("d")      # cuentas top: largos/cortos
        self.lsr = array.array("d")          # todas las cuentas: largos/cortos
        self.taker = array.array("d")        # volumen agresor comprador/vendedor

    def __len__(self):
        return len(self.t)


def cargar_metricas():
    m = Metricas()
    ultimo = -1
    for r in _archivos_verificados("metricas-5m"):
        with zipfile.ZipFile(r) as z:
            with z.open(z.namelist()[0]) as f:
                for fila in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                    try:
                        t = int(dt.datetime.strptime(fila["create_time"], "%Y-%m-%d %H:%M:%S")
                                .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
                        fila_ok = (float(fila["sum_open_interest"]), float(fila["sum_open_interest_value"]),
                                   float(fila["count_toptrader_long_short_ratio"] or "nan"),
                                   float(fila["count_long_short_ratio"] or "nan"),
                                   float(fila["sum_taker_long_short_vol_ratio"] or "nan"))
                    except (KeyError, ValueError):
                        continue
                    if t <= ultimo:
                        continue
                    ultimo = t
                    m.t.append(t)
                    m.oi.append(fila_ok[0])
                    m.oi_usd.append(fila_ok[1])
                    m.lsr_top.append(fila_ok[2])
                    m.lsr.append(fila_ok[3])
                    m.taker.append(fila_ok[4])
    return m


def cargar_financiacion():
    t, tasa = array.array("q"), array.array("d")
    for r in _archivos_verificados("financiacion"):
        with zipfile.ZipFile(r) as z:
            with z.open(z.namelist()[0]) as f:
                for fila in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                    try:
                        t.append(int(fila["calc_time"]))
                        tasa.append(float(fila["last_funding_rate"]))
                    except (KeyError, ValueError):
                        continue
    orden = sorted(range(len(t)), key=lambda k: t[k])
    return array.array("q", (t[k] for k in orden)), array.array("d", (tasa[k] for k in orden))
