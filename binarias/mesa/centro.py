"""Centro de estrategias de la Mesa (07/11/2026). Solo biblioteca estándar y sin IA.

Pedido del dueño del 06 y 07/11: ver BTC en tiempo real con las cinco estrategias de PROMPT-CINCO-ESTRATEGIAS.md corriendo en
paralelo, cada una con sus indicadores y lo que está haciendo, y con las variables estadísticas que sí pasaron las pruebas.
- Reglas idénticas a cuant/c12_estudio_06nov.py (P21 y P22). prueba_centro.py las compara señal por señal con ese código en numpy.
- Papel: entrada al cierre del minuto que sigue a la vela (60 s tarde), salida 15 min después, empate = fallo y una apuesta a la
  vez por estrategia. Así se midieron las cifras de largo plazo, y por eso se pueden comparar.
- Filtro del 82 %: 21 de las últimas 25 de esa estrategia. Se mira en cada vuelta, no solo cuando cambia.
- Variables: interés abierto que no sube (P14b, la única que pasó con margen honesto), papel de hoy sumando sin ningún SÍ
  perdido (su regla del 03/11), caída fuerte en la última hora (P20: se avisa, no se filtra) y la probabilidad de que la
  racha de las últimas 25 salga por azar con el acierto de fondo de esa estrategia.
Nada de esto compra: los botones siguen en la Mesa y el toque es del dueño.
"""
import datetime as dt
import json
import math
import os
import threading
import time

import graficas

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
ARCHIVO = os.path.join(DATOS, "centro.json")
COL = dt.timezone(dt.timedelta(hours=-5))
PLAZO, VENTANA, FILTRO = 900, 25, 21          # 21 de 25 = 84 %, lo primero que pasa el 82 %
PRECIO_REF, COMISION = 0.51, 0.02
EQUILIBRIO = PRECIO_REF / (1 - COMISION)      # 52,04 %
UMBRAL_OI = 0.00022                           # igual que semaforo.UMBRAL_OI y reglas.CFG
DIAS_HISTORIA, DIAS_E5 = 30, 5                # E5 calcula sus líneas en cada cierre de 5 min: se siembra con menos días
NAN = float("nan")

ESTRATEGIAS = (
    {"id": "E1", "nombre": "Ruptura de 20 velas, al revés", "marco": "5 min", "largo": 54.6, "n_largo": 18503, "wilson": 53.8, "oct": 56.5,
     "nota": "el núcleo de la Mesa y de la caja"},
    {"id": "E2", "nombre": "Ruptura de 50 velas, al revés", "marco": "5 min", "largo": 55.1, "n_largo": 10244, "wilson": 54.2, "oct": 59.3,
     "nota": "la misma idea con un canal más largo"},
    {"id": "E3", "nombre": "Compresión de Bollinger, al revés", "marco": "15 min", "largo": 57.7, "n_largo": 2488, "wilson": 55.7, "oct": 55.6,
     "nota": "Gemini 1 al revés; idea posterior a ver los datos"},
    {"id": "E4", "nombre": "EMA 50 y MACD, al revés", "marco": "15 min", "largo": 54.4, "n_largo": 1081, "wilson": 51.4, "oct": 53.8,
     "nota": "Gemini 3 al revés; poco más de una al día"},
    {"id": "E5", "nombre": "Rechazo en techo o piso azules", "marco": "5 min", "largo": 51.8, "n_largo": 14023, "wilson": 51.0, "oct": 54.3,
     "nota": "sus cinco líneas; no pasó P21, solo se mide"},
)
IDS = tuple(e["id"] for e in ESTRATEGIAS)


# ---------------------------------------------------------------- cálculo puro (lo que compara prueba_centro.py)
def agrupar(v1, seg):
    """Velas completas de `seg` segundos alineadas al reloj: (cierre, apertura, máximo, mínimo, último). Igual que c12.agrupar."""
    paso, out, g = seg // 60, [], None
    for x in v1:
        k = x[0] // seg
        if g is None or k != g[0]:
            if g is not None and g[5] == paso:
                out.append(((g[0] + 1) * seg, g[1], g[2], g[3], g[4]))
            g = [k, x[1], x[2], x[3], x[4], 1]
        else:
            g[2] = max(g[2], x[2])
            g[3] = min(g[3], x[3])
            g[4] = x[4]
            g[5] += 1
    if g is not None and g[5] == paso:
        out.append(((g[0] + 1) * seg, g[1], g[2], g[3], g[4]))
    return out


def ruptura(v5, j, n):
    """E1 (n=20) y E2 (n=50): la vela j cierra fuera del máximo o mínimo de las n anteriores y se apuesta al revés."""
    if j < n:
        return 0
    mx = max(x[2] for x in v5[j - n:j])
    mn = min(x[3] for x in v5[j - n:j])
    c = v5[j][4]
    return -1 if c > mx else (1 if c < mn else 0)


def _ema(x, n):
    a, out = 2 / (n + 1), [x[0]]
    for v in x[1:]:
        out.append(a * v + (1 - a) * out[-1])
    return out


def _rsi(c, n=14):
    """El mismo RSI de c12: medias de Wilder sembradas con las 14 primeras diferencias."""
    d = [0.0] + [c[i] - c[i - 1] for i in range(1, len(c))]
    su, ba = [max(x, 0.0) for x in d], [max(-x, 0.0) for x in d]
    out = [50.0] * len(c)
    if len(c) <= n:
        return out
    a = b = 0.0
    for i in range(1, n + 1):
        a += su[i]
        b += ba[i]
    a, b = a / n, b / n
    for i in range(n + 1, len(c)):
        a, b = (a * (n - 1) + su[i]) / n, (b * (n - 1) + ba[i]) / n
        out[i] = 100.0 if b == 0 else 100 - 100 / (1 + a / b)
    return out


def _cuantil(x, q):
    """Cuantil con interpolación lineal, como np.quantile por defecto."""
    s = sorted(x)
    p = q * (len(s) - 1)
    i = int(math.floor(p))
    return s[i] if i + 1 >= len(s) else s[i] + (s[i + 1] - s[i]) * (p - i)


def indicadores15(v15, desde=0):
    """Indicadores de E3 y E4 sobre velas de 15 min. `desde` evita calcular el cuantil donde no hace falta."""
    n = len(v15)
    O = [x[1] for x in v15]
    H = [x[2] for x in v15]
    L = [x[3] for x in v15]
    C = [x[4] for x in v15]
    sma, up, lo, ancho = [NAN] * n, [NAN] * n, [NAN] * n, [NAN] * n
    for i in range(19, n):
        w = C[i - 19:i + 1]
        m = 0.0
        for v in w:
            m += v
        m /= 20
        var = 0.0
        for v in w:
            var += (v - m) ** 2
        de = math.sqrt(var / 20)
        sma[i], up[i], lo[i] = m, m + 2 * de, m - 2 * de
        ancho[i] = (up[i] - lo[i]) / m
    q20, min5 = [NAN] * n, [NAN] * n
    for i in range(max(114, desde - 1), n):
        q20[i] = _cuantil(ancho[i - 95:i + 1], 0.20)
    for i in range(24, n):
        min5[i] = min(ancho[i - 5:i])
    R = _rsi(C) if n else []
    e50 = _ema(C, 50) if n else []
    macd = [a - b for a, b in zip(_ema(C, 12), _ema(C, 26))] if n else []
    sen = _ema(macd, 9) if n else []
    sobre = [NAN] * n
    for i in range(19, n):
        sobre[i] = len([1 for k in range(i - 19, i + 1) if C[k] > e50[k]]) / 20
    return {"O": O, "H": H, "L": L, "C": C, "sma": sma, "up": up, "lo": lo, "ancho": ancho, "q20": q20, "min5": min5,
            "rsi": R, "e50": e50, "macd": macd, "sen": sen, "sobre": sobre}


def e3_e4(ind, i):
    """(E3, E4) en la vela de 15 min i: Gemini 1 y Gemini 3 de c12, apostando al revés."""
    O, H, L, C = ind["O"], ind["H"], ind["L"], ind["C"]
    s3 = s4 = 0
    if i >= 1:
        comp = ind["min5"][i] <= ind["q20"][i - 1]  # NaN compara falso, igual que numpy
        rango = H[i] - L[i]
        fuerte = rango > 0 and abs(C[i] - O[i]) / rango >= 0.6
        R = ind["rsi"][i]
        if comp and C[i] > ind["up"][i] and C[i] > O[i] and fuerte and R >= 55:
            s3 = -1
        elif comp and C[i] < ind["lo"][i] and C[i] < O[i] and fuerte and R <= 45:
            s3 = 1
        e50, m, s = ind["e50"], ind["macd"], ind["sen"]
        sube = i >= 5 and e50[i] > e50[i - 5]
        sobre = ind["sobre"][i]
        cu = m[i] > s[i] and m[i - 1] <= s[i - 1]
        cd = m[i] < s[i] and m[i - 1] >= s[i - 1]
        if i >= 2:
            if sobre >= 0.8 and sube and min(L[i - 2:i + 1]) <= e50[i] * 1.001 and cu and C[i] > e50[i]:
                s4 = -1
            elif sobre <= 0.2 and not sube and max(H[i - 2:i + 1]) >= e50[i] * 0.999 and cd and C[i] < e50[i]:
                s4 = 1
    return s3, s4


def e5(v1, i):
    """E5 en el minuto i (el último de una vela de 5 min): rechazo en el techo azul → BAJA; en el piso azul → SUBE."""
    if i < 149:
        return 0, None
    r = graficas.cinco_lineas(v1[i - 149:i + 1])
    if not r:
        return 0, None
    c0, c9, h0, l0 = v1[i][4], v1[i - 1][4], v1[i][2], v1[i][3]
    s = 0
    ya, antes = r["techo"].en(149), r["techo"].en(148)
    if not (c0 > ya and c9 <= antes) and h0 >= ya and c0 < ya:
        s -= 1
    ya, antes = r["piso"].en(149), r["piso"].en(148)
    if not (c0 < ya and c9 >= antes) and l0 <= ya and c0 > ya:
        s += 1
    return s, r  # techo y piso a la vez se anulan


def verdes(v, tol=0.0002):
    """Sus dos líneas verdes del 06/11, leídas con la regla N3 de c12 (solo para mirar: N3 no dio ventaja).
    Techo verde: tres máximos locales (±3 velas de 1 min) separados 5 min o más, a 0,02 % del mismo nivel y sin cierre por encima.
    Piso verde: lo mismo en mínimos. Verde de la mitad: entre los dos; si falta uno, entre el que hay y el extremo opuesto."""
    n = len(v)
    H, L, C = [x[2] for x in v], [x[3] for x in v], [x[4] for x in v]

    def nivel(Y, signo):
        idx = [i for i in range(3, n - 3) if Y[i] == (max(Y[i - 3:i + 4]) if signo == 1 else min(Y[i - 3:i + 4]))]
        mejor = None
        for i in idx:
            y = Y[i]
            toques, prev = [], None
            for a in idx:
                if a <= i and abs(Y[a] / y - 1) <= tol and (prev is None or a - prev >= 5):
                    toques.append(a)
                    prev = a
            if len(toques) >= 3:
                tope = y * (1 + signo * tol)
                if (max(C[toques[0]:]) <= tope) if signo == 1 else (min(C[toques[0]:]) >= tope):
                    if mejor is None or signo * y >= signo * mejor[0]:  # el máximo exacto: el nivel más alto (o el más bajo abajo)
                        mejor = (y, toques)
        return mejor

    t0, out = v[0][0], {}
    arriba, abajo = nivel(H, 1), nivel(L, -1)
    for clave, r in (("verde_techo", arriba), ("verde_piso", abajo)):
        if r:
            out[clave] = [t0 + 60 * r[1][0] + 30, round(r[0], 2), t0 + 60 * (n + 19) + 30, round(r[0], 2), len(r[1])]
    if arriba or abajo:
        y1 = arriba[0] if arriba else max(H)
        y2 = abajo[0] if abajo else min(L)
        m = (y1 + y2) / 2
        out["verde_mitad"] = [t0 + 30, round(m, 2), t0 + 60 * (n + 19) + 30, round(m, 2), 0]
    return out


def neto(res):
    return res * (1 - COMISION) / PRECIO_REF - 1


def wilson(k, n, z=1.96):
    if not n:
        return 0.0
    p = k / n
    c = (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)
    return 100 * c


def cola(k, n, p):
    """Probabilidad de sacar k o más aciertos en n con acierto de fondo p: qué tan fácil es que la racha sea azar."""
    t = 0.0
    for j in range(k, n + 1):
        t += math.comb(n, j) * p ** j * (1 - p) ** (n - j)
    return t


def hora(t):
    return dt.datetime.fromtimestamp(t, COL).strftime("%H:%M")


def ini_dia(t):
    d = dt.datetime.fromtimestamp(t, COL)
    return dt.datetime(d.year, d.month, d.day, tzinfo=COL).timestamp()


# ---------------------------------------------------------------- el centro en vivo
class Centro:
    def __init__(self, conexion):
        self.C = conexion
        self.cand = threading.Lock()
        self.v1, self.cierre = [], {}
        self.ops = {k: [] for k in IDS}
        self.ultimo5 = 0
        self.listo, self.error, self.foto = False, None, {"listo": False}
        self.doi, self.t_doi = None, 0.0
        self.aptas_prev = set()
        os.makedirs(DATOS, exist_ok=True)
        try:
            with open(ARCHIVO, encoding="utf-8") as f:
                d = json.load(f)
            self.ops = {k: d["ops"].get(k, []) for k in IDS}
            self.ultimo5 = int(d.get("ultimo5", 0))
        except (OSError, ValueError, KeyError):
            pass

    def _guardar(self):
        tmp = ARCHIVO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ops": {k: v[-2000:] for k, v in self.ops.items()}, "ultimo5": self.ultimo5}, f, ensure_ascii=False)
        os.replace(tmp, ARCHIVO)

    def sembrar(self):
        """Trae 30 días de velas de 1 min y rehace con ellas lo que no vio en vivo. Corre en su propio hilo al arrancar."""
        try:
            v = self.C.historial(DIAS_HISTORIA)
            with self.cand:
                self.v1 = [tuple(x[:5]) for x in v]
                self.cierre = {x[0]: x[4] for x in self.v1}
                n = self._procesar(time.time(), sembrando=True)
                self._calificar()
                self._guardar()
                self.listo = True
            return n
        except Exception as ex:
            self.error = f"sin historia: {type(ex).__name__}: {str(ex)[:100]}"
            return 0

    def _procesar(self, ahora, sembrando=False):
        """Evalúa las cinco en cada cierre de 5 min nuevo. Devuelve las señales abiertas."""
        v5 = agrupar(self.v1, 300)
        nuevos = [j for j, x in enumerate(v5) if x[0] > self.ultimo5]
        if not nuevos:
            return []
        v15 = agrupar(self.v1, 900)
        pos15 = {x[0]: i for i, x in enumerate(v15)}
        primero15 = min((pos15.get(v5[j][0], len(v15)) for j in nuevos), default=len(v15))
        ind = indicadores15(v15, desde=primero15)
        idx1 = {x[0]: i for i, x in enumerate(self.v1)}
        abiertas = []
        for j in nuevos:
            T = v5[j][0]
            senales = {"E1": ruptura(v5, j, 20), "E2": ruptura(v5, j, 50)}
            i1 = idx1.get(T - 60)
            if i1 is not None and (not sembrando or T >= ahora - DIAS_E5 * 86400):
                senales["E5"] = e5(self.v1, i1)[0]
            if T in pos15:
                senales["E3"], senales["E4"] = e3_e4(ind, pos15[T])
            for k, s in senales.items():
                if s and self._libre(k, T):
                    op = {"t": T, "dir": s, "base": None, "res": None, "semilla": sembrando, "si": None, "doi": None}
                    self.ops[k].append(op)
                    abiertas.append((k, op))
            self.ultimo5 = T
        return abiertas

    def _libre(self, k, T):
        """Una apuesta a la vez por estrategia, como sin_solape de c12: la siguiente desde T + 60 + 900."""
        u = self.ops[k]
        return not u or T >= u[-1]["t"] + 60 + PLAZO

    def _calificar(self):
        for k in IDS:
            for o in self.ops[k]:
                if o["res"] is not None:
                    continue
                if o["base"] is None:
                    o["base"] = self.cierre.get(o["t"])
                b = self.cierre.get(o["t"] + PLAZO)
                if o["base"] is not None and b is not None:
                    m = (b - o["base"]) * o["dir"]
                    o["res"] = 1 if m > 0 else 0  # empate = fallo, como gana_tarde
                elif o["base"] is None and self.v1 and self.v1[-1][0] > o["t"] + 3 * PLAZO:
                    o["res"] = "hueco"  # sin vela de entrada: no se inventa
        for k in IDS:
            self.ops[k] = [o for o in self.ops[k] if o["res"] != "hueco"]

    # ------------------------------------------------------------ por cada vuelta de la Mesa
    def actualizar(self, cerradas, viva, ahora=None):
        """Recibe las velas que ya trae la Mesa (cada 2 s). Devuelve los eventos para traer la ventana al frente."""
        if not self.listo:
            return []
        ahora = ahora or time.time()
        eventos = []
        with self.cand:
            ult = self.v1[-1][0] if self.v1 else 0
            nuevas = [tuple(x[:5]) for x in cerradas if x[0] > ult]
            if nuevas:
                self.v1 += nuevas
                for x in nuevas:
                    self.cierre[x[0]] = x[4]
                corte = ahora - (DIAS_HISTORIA + 1) * 86400
                if self.v1[0][0] < corte:
                    self.v1 = [x for x in self.v1 if x[0] >= corte]
                    self.cierre = {x[0]: x[4] for x in self.v1}
                abiertas = self._procesar(ahora)
                self._calificar()
                for k, op in abiertas:
                    self._marcar_si(k, op, ahora)
                    eventos.append(("señal", k, op))
                self._guardar()
            self.foto = self._foto(viva, ahora)
            aptas = {e["id"] for e in self.foto["estrategias"] if e["apta"]}
            for k in aptas - self.aptas_prev:
                eventos.append(("apta", k, None))
            self.aptas_prev = aptas
        return eventos

    def _interes(self, T):
        if self.t_doi != T:
            try:
                self.doi = self.C.cambio_interes(T)
            except Exception:
                self.doi = None
            self.t_doi = T
        return self.doi

    def _marcar_si(self, k, op, ahora):
        """Su regla del 03/11 llevada a cada estrategia: su papel de hoy sumando, ningún SÍ perdido hoy e interés abierto que no sube."""
        r = self._resumen(k, op["t"])
        doi = self._interes(op["t"] - op["t"] % 300)
        op["doi"] = None if doi is None else round(doi, 6)
        op["si"] = bool(r["neto_hoy"] > 0 and not r["perdio"] and doi is not None and doi <= UMBRAL_OI)

    def _resumen(self, k, ahora):
        ops = self.ops[k]
        cerr = [o for o in ops if o["res"] is not None and o["t"] + PLAZO + 60 <= ahora]
        u = cerr[-VENTANA:]
        k25 = len([o for o in u if o["res"] == 1])
        racha = 0
        for o in reversed(cerr):
            if o["res"] != 1:
                break
            racha += 1
        hoy0 = ini_dia(ahora)
        hoy = [o for o in cerr if o["t"] >= hoy0]
        nh = 0.0
        for o in hoy:
            nh += neto(o["res"])
        vivas = [o for o in cerr if not o.get("semilla")]
        kt = len([o for o in cerr if o["res"] == 1])
        return {"k25": k25, "n25": len(u), "racha": racha, "neto_hoy": round(nh, 2), "hoy": len(hoy),
                "aciertos_hoy": len([o for o in hoy if o["res"] == 1]), "perdio": any(o.get("si") and o["res"] == 0 for o in hoy),
                "kt": kt, "nt": len(cerr), "vivas": len(vivas), "puntos": [o["res"] for o in u]}

    # ------------------------------------------------------------ lo que ve la pantalla
    def _foto(self, viva, ahora):
        v1 = self.v1
        if len(v1) < 300:
            return {"listo": False}
        precio = viva[4] if viva else v1[-1][4]
        v5 = agrupar(v1, 300)
        v15 = agrupar(v1, 900)
        ind = indicadores15(v15, desde=len(v15) - 40)
        n15 = len(v15)
        lin = graficas.cinco_lineas(v1[-150:])
        hace1h = self.cierre.get(v1[-1][0] - 3600)
        cambio1h = (precio / hace1h - 1) * 100 if hace1h else None
        # vela de 5 min en formación, con la viva
        t5 = int(ahora // 300 * 300)
        parcial = [x for x in v1 if x[0] >= t5] + ([tuple(viva[:5])] if viva and viva[0] >= t5 else [])
        forma5 = (t5 + 300, parcial[0][1], max(x[2] for x in parcial), min(x[3] for x in parcial), parcial[-1][4]) if parcial else None
        t15 = int(ahora // 900 * 900)
        parc15 = [x for x in v1 if x[0] >= t15] + ([tuple(viva[:5])] if viva and viva[0] >= t15 else [])
        forma15 = (t15 + 900, parc15[0][1], max(x[2] for x in parc15), min(x[3] for x in parc15), parc15[-1][4]) if parc15 else None
        doi = self._interes(t5)
        est = []
        for e in ESTRATEGIAS:
            k = e["id"]
            r = self._resumen(k, ahora)
            abierta = next((o for o in reversed(self.ops[k]) if o["res"] is None), None)
            apta = r["n25"] >= VENTANA and r["k25"] >= FILTRO
            p = e["largo"] / 100
            azar = cola(r["k25"], r["n25"], p) if r["n25"] else None
            detalle = self._detalle(k, v5, ind, n15, lin, forma5, forma15, precio, ahora)
            ab = None
            if abierta:
                va = None if abierta["base"] is None else (precio - abierta["base"]) * abierta["dir"]
                ab = {"t": abierta["t"], "dir": abierta["dir"], "base": abierta["base"], "si": abierta.get("si"), "doi": abierta.get("doi"),
                      "entra": abierta["t"] + 60, "vence": abierta["t"] + 60 + PLAZO, "va": None if va is None else round(va, 2),
                      "mesa": abierta["t"] % 900 == 0}
            est.append({**e, **r, "pct25": round(100 * r["k25"] / r["n25"]) if r["n25"] else 0,
                        "pct_total": round(100 * r["kt"] / r["nt"], 1) if r["nt"] else 0, "wilson_vivo": round(wilson(r["kt"], r["nt"]), 1),
                        "apta": apta, "azar": azar, "abierta": ab, **detalle})
        marcas = []
        t_ini = v5[-96][0] - 300 if len(v5) >= 96 else 0
        for k in IDS:
            for o in self.ops[k]:
                if o["t"] >= t_ini:
                    marcas.append({"id": k, "t": o["t"], "dir": o["dir"], "res": o["res"], "base": o["base"]})
        ult = sorted(({"id": k, **{c: o[c] for c in ("t", "dir", "res", "base", "si", "semilla")}} for k in IDS for o in self.ops[k][-12:]),
                     key=lambda x: -x["t"])[:24]
        grafica = {
            "velas": [list(x) for x in v5[-96:]] + ([list(forma5)] if forma5 else []),
            "canal20": [[x[0]] + list(self._canal(v5, j, 20)) for j, x in enumerate(v5) if j >= len(v5) - 96],
            "canal50": [[x[0]] + list(self._canal(v5, j, 50)) for j, x in enumerate(v5) if j >= len(v5) - 96],
            "boll": [[v15[i][0], ind["up"][i], ind["sma"][i], ind["lo"][i], ind["e50"][i], ind["rsi"][i], ind["macd"][i], ind["sen"][i]]
                     for i in range(max(0, n15 - 34), n15)],
            "lineas": self._lineas_tiempo(lin, v1[-150:]),
            "verdes": verdes(v1[-150:]),
            "marcas": marcas,
        }
        return {"listo": True, "ahora": ahora, "hora": dt.datetime.fromtimestamp(ahora, COL).strftime("%H:%M:%S"), "precio": precio,
                "cambio1h": None if cambio1h is None else round(cambio1h, 2), "caida_fuerte": cambio1h is not None and cambio1h <= -1,
                "doi": None if doi is None else round(doi * 100, 3), "oi_no_sube": doi is not None and doi <= UMBRAL_OI,
                "equilibrio": round(100 * EQUILIBRIO, 2), "filtro": FILTRO, "ventana": VENTANA, "estrategias": est,
                "ultimas": ult, "grafica": grafica, "error": self.error}

    @staticmethod
    def _canal(v5, j, n):
        if j < n:
            return (None, None)
        return (max(x[2] for x in v5[j - n:j]), min(x[3] for x in v5[j - n:j]))

    @staticmethod
    def _lineas_tiempo(lin, v):
        if not lin:
            return {}
        t0, out = v[0][0], {}
        for clave in ("techo", "piso", "techo_c", "piso_c", "mitad"):
            r, d = lin[clave], lin["desde"][clave]
            a, b = r.en(d), r.en(len(v) + 19)
            if math.isfinite(a) and math.isfinite(b):
                out[clave] = [t0 + 60 * d + 30, round(a, 2), t0 + 60 * (len(v) + 19) + 30, round(b, 2)]
        return out

    def _detalle(self, k, v5, ind, n15, lin, forma5, forma15, precio, ahora):
        """Lo que está haciendo cada una ahora: sus indicadores, qué falta y a qué precio dispararía."""
        f = lambda x: f"{x:,.0f}".replace(",", ".")  # noqa: E731
        d = lambda x: f"{(x / precio - 1) * 100:+.2f} %".replace(".", ",")  # noqa: E731
        cierra5 = hora(forma5[0]) if forma5 else "–"
        cierra15 = hora(forma15[0]) if forma15 else "–"
        if k in ("E1", "E2"):
            n = 20 if k == "E1" else 50
            mx, mn = self._canal(v5 + ([forma5] if forma5 else []), len(v5), n)
            if mx is None:
                return {"indicadores": [], "que_hace": "Juntando velas.", "lista": []}
            return {"indicadores": [["techo del canal", f(mx), d(mx)], ["piso del canal", f(mn), d(mn)], ["precio", f(precio), ""]],
                    "que_hace": f"Mira la vela de 5 min que cierra a las {cierra5}: si cierra encima de {f(mx)} apuesta BAJA; si cierra debajo de {f(mn)}, SUBE.",
                    "lista": [["cierre encima del techo", precio > mx], ["cierre debajo del piso", precio < mn]]}
        if k == "E3":
            i = n15 - 1
            if i < 115:
                return {"indicadores": [], "que_hace": "Juntando velas de 15 min.", "lista": []}
            comp_sig = min(ind["ancho"][i - 4:i + 1]) <= ind["q20"][i]  # la vela en curso sale comprimida si esto se cumple
            o = forma15[1] if forma15 else precio
            rango = (forma15[2] - forma15[3]) if forma15 else 0
            cuerpo = abs(precio - o) / rango * 100 if rango > 0 else 0
            up, lo, R = ind["up"][i], ind["lo"][i], ind["rsi"][i]
            return {"indicadores": [["banda superior", f(up), d(up)], ["banda inferior", f(lo), d(lo)],
                                    ["ancho de banda", f"{ind['ancho'][i] * 100:.2f} %".replace(".", ","), f"umbral {ind['q20'][i] * 100:.2f} %".replace(".", ",")],
                                    ["RSI 14", f"{R:.0f}", ""], ["cuerpo de la vela", f"{cuerpo:.0f} %", "pide 60 %"]],
                    "que_hace": (f"Bandas {'COMPRIMIDAS' if comp_sig else 'abiertas'}. Si la vela de 15 min de las {cierra15} cierra encima de la banda "
                                 f"con cuerpo de 60 % y RSI 55 o más, apuesta BAJA; debajo con RSI 45 o menos, SUBE."),
                    "lista": [["compresión", comp_sig], ["fuera de banda", precio > up or precio < lo], ["cuerpo de 60 %", cuerpo >= 60],
                              ["RSI extremo", R >= 55 or R <= 45]]}
        if k == "E4":
            i = n15 - 1
            if i < 30:
                return {"indicadores": [], "que_hace": "Juntando velas de 15 min.", "lista": []}
            e50, m, s = ind["e50"][i], ind["macd"][i], ind["sen"][i]
            sube = ind["e50"][i] > ind["e50"][i - 5]
            sobre = ind["sobre"][i] * 100
            tend = "alcista" if sobre >= 80 and sube else ("bajista" if sobre <= 20 and not sube else "sin tendencia clara")
            return {"indicadores": [["EMA 50", f(e50), d(e50)], ["velas sobre la EMA", f"{sobre:.0f} %", "pide 80 % o 20 %"],
                                    ["MACD", f"{m:+.1f}".replace(".", ","), f"señal {s:+.1f}".replace(".", ",")]],
                    "que_hace": (f"{('Tendencia ' + tend) if tend != 'sin tendencia clara' else 'Sin tendencia clara'}. Dispara cuando el MACD cruza su señal a favor de la tendencia tras tocar la EMA 50, "
                                 f"y apuesta al revés. Próximo cierre: {cierra15}."),
                    "lista": [["tendencia", tend != "sin tendencia clara"], ["toque de la EMA", abs(precio / e50 - 1) <= 0.002],
                              ["MACD a punto de cruzar", abs(m - s) <= max(abs(m), 1) * 0.15]]}
        if not lin:
            return {"indicadores": [], "que_hace": "Calculando sus líneas.", "lista": []}
        te, pi = lin["techo"].en(149), lin["piso"].en(149)
        vd = verdes(self.v1[-150:])
        extra = [[f"verde de {x[4]} toques " + ("arriba" if k == "verde_techo" else "abajo"), f(x[1]), d(x[1])] for k, x in vd.items() if k != "verde_mitad"]
        if "verde_mitad" in vd:
            extra.append(["verde de la mitad", f(vd["verde_mitad"][1]), ""])
        return {"indicadores": [["techo azul", f(te), d(te)], ["piso azul", f(pi), d(pi)], ["mitad", f(lin["mitad"].en(149)), ""]] + extra,
                "que_hace": f"Si la vela de 1 min de las {hora(forma5[0] - 60) if forma5 else '–'} toca el techo y cierra abajo, apuesta BAJA; si toca el piso y cierra arriba, SUBE.",
                "lista": [["cerca del techo", abs(precio / te - 1) <= 0.0015], ["cerca del piso", abs(precio / pi - 1) <= 0.0015]]}
