"""Probabilidad por ciclo: regresión logística propia, sin librerías.

Responde a «¿qué tan seguro es que este ciclo toque el objetivo antes que el stop?».
Se entrena con el tramo de desarrollo, se recalibra y se mide en validación, y el tramo
final se mira una sola vez. Una probabilidad solo sirve si es honesta: cuando dice 60 %,
en la historia tiene que haber acertado cerca del 60 % de las veces; eso lo comprueba la
tabla de fiabilidad. La probabilidad mínima para operar no se elige a ojo: sale de las
comisiones de cada instrumento (minima_para_ganar).
"""
import json
import math
from operator import mul

NAN = float("nan")


def sigmoide(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def logit(p):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


def _resolver(A, b):
    """Sistema lineal por eliminación de Gauss con pivoteo parcial."""
    n = len(b)
    M = [fila[:] + [b[i]] for i, fila in enumerate(A)]
    for k in range(n):
        p = max(range(k, n), key=lambda r: abs(M[r][k]))
        if abs(M[p][k]) < 1e-12:
            raise ValueError("sistema singular")
        M[k], M[p] = M[p], M[k]
        fila_k = M[k]
        for r in range(k + 1, n):
            f = M[r][k] / fila_k[k]
            if f:
                fila_r = M[r]
                for c in range(k, n + 1):
                    fila_r[c] -= f * fila_k[c]
    x = [0.0] * n
    for k in range(n - 1, -1, -1):
        x[k] = (M[k][n] - sum(M[k][c] * x[c] for c in range(k + 1, n))) / M[k][k]
    return x


class Logistica:
    """Logística con penalización L2, rasgos estandarizados y recortados a ±5 desvíos.

    Un NaN (dato que faltaba en ese instante) cuenta como la media del entrenamiento.
    Opcional: recalibración de Platt (a + b·logit p) ajustada en validación.
    """

    def __init__(self, nombres, l2=1.0, recorte=5.0):
        self.nombres = list(nombres)
        self.l2 = l2
        self.recorte = recorte
        self.media = self.desvio = self.beta = None
        self.platt = (0.0, 1.0)
        self.iteraciones = 0

    # ---------- preparación ----------
    def _columnas(self, X):
        """Columnas estandarizadas (listas), con la columna de unos delante."""
        n = len(X)
        cols = [[1.0] * n]
        r = self.recorte
        for k in range(len(self.nombres)):
            m, s = self.media[k], self.desvio[k]
            col = []
            for x in X:
                v = x[k]
                if v != v:
                    col.append(0.0)
                else:
                    z = (v - m) / s
                    col.append(r if z > r else (-r if z < -r else z))
            cols.append(col)
        return cols

    def ajustar(self, X, y, iter_max=40, tol=1e-7, estandarizar=True):
        d = len(self.nombres)
        if estandarizar or self.media is None:
            self.media, self.desvio = [], []
            for k in range(d):
                vals = [x[k] for x in X if x[k] == x[k]]
                m = math.fsum(vals) / len(vals) if vals else 0.0
                var = math.fsum((v - m) ** 2 for v in vals) / max(len(vals) - 1, 1) if vals else 1.0
                s = math.sqrt(var)
                self.media.append(m)
                self.desvio.append(s if s > 1e-12 else 1.0)
        cols = self._columnas(X)
        n, D = len(y), d + 1
        yf = [float(v) for v in y]
        base = min(max(math.fsum(yf) / n, 1e-6), 1 - 1e-6)
        beta = [math.log(base / (1 - base))] + [0.0] * d
        for it in range(iter_max):
            eta = [beta[0]] * n
            for a in range(1, D):
                if beta[a]:
                    ba = beta[a]
                    eta = [e + ba * z for e, z in zip(eta, cols[a])]
            p = [sigmoide(e) for e in eta]
            w = [q * (1 - q) for q in p]
            r = [yi - q for yi, q in zip(yf, p)]
            g = [sum(map(mul, r, cols[a])) for a in range(D)]
            H = [[0.0] * D for _ in range(D)]
            for a in range(D):
                wa = list(map(mul, w, cols[a]))
                for b in range(a, D):
                    H[a][b] = H[b][a] = sum(map(mul, wa, cols[b]))
            for a in range(1, D):                    # el intercepto no se penaliza
                H[a][a] += self.l2
                g[a] -= self.l2 * beta[a]
            paso = _resolver(H, g)
            beta = [b + s for b, s in zip(beta, paso)]
            if max(abs(s) for s in paso) < tol:
                break
        self.beta = beta
        self.iteraciones = it + 1
        return self

    # ---------- uso ----------
    def margen(self, x):
        b = self.beta
        eta = b[0]
        r = self.recorte
        for k, v in enumerate(x):
            if v == v:
                z = (v - self.media[k]) / self.desvio[k]
                eta += b[k + 1] * (r if z > r else (-r if z < -r else z))
        return eta

    def prob_cruda(self, x):
        return sigmoide(self.margen(x))

    def prob(self, x):
        a, b = self.platt
        return sigmoide(a + b * self.margen(x))

    def recalibrar(self, X, y):
        """Platt en validación: corrige el exceso o defecto de confianza sin tocar el orden."""
        m = [self.margen(x) for x in X]
        uno = Logistica(["margen"], l2=1e-6, recorte=1e9)
        uno.media, uno.desvio = [0.0], [1.0]
        uno.ajustar([[v] for v in m], y, estandarizar=False)
        self.platt = (uno.beta[0], uno.beta[1])
        return self

    def importancia(self):
        """Peso de cada rasgo (en desvíos estándar), de mayor a menor efecto."""
        return sorted(((n, round(b, 4)) for n, b in zip(self.nombres, self.beta[1:])), key=lambda x: -abs(x[1]))

    def a_dict(self):
        return {"nombres": self.nombres, "l2": self.l2, "recorte": self.recorte, "media": self.media,
                "desvio": self.desvio, "beta": self.beta, "platt": list(self.platt), "iteraciones": self.iteraciones}

    @classmethod
    def desde_dict(cls, d):
        m = cls(d["nombres"], d["l2"], d["recorte"])
        m.media, m.desvio, m.beta = d["media"], d["desvio"], d["beta"]
        m.platt = tuple(d.get("platt", (0.0, 1.0)))
        m.iteraciones = d.get("iteraciones", 0)
        return m

    def guardar(self, ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(self.a_dict(), f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- medidas de honestidad
def brier(p, y):
    return math.fsum((pi - yi) ** 2 for pi, yi in zip(p, y)) / len(p)


def log_perdida(p, y):
    return -math.fsum(math.log(min(max(pi if yi else 1 - pi, 1e-12), 1.0)) for pi, yi in zip(p, y)) / len(p)


def auc(p, y):
    """Área bajo la curva ROC por rangos (Mann-Whitney), con empates promediados."""
    orden = sorted(range(len(p)), key=lambda k: p[k])
    rangos = [0.0] * len(p)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and p[orden[j + 1]] == p[orden[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            rangos[orden[k]] = r
        i = j + 1
    pos = sum(1 for v in y if v)
    neg = len(y) - pos
    if pos == 0 or neg == 0:
        return NAN
    suma = math.fsum(r for r, v in zip(rangos, y) if v)
    return (suma - pos * (pos + 1) / 2) / (pos * neg)


def fiabilidad(p, y, cortes=(0.0, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 0.85, 1.0001)):
    """Por tramo de probabilidad dicha: cuántos casos, media dicha y acierto real."""
    filas = []
    for a, b in zip(cortes, cortes[1:]):
        idx = [k for k, v in enumerate(p) if a <= v < b]
        if idx:
            filas.append({"desde": a, "hasta": min(b, 1.0), "casos": len(idx),
                          "dicha": round(math.fsum(p[k] for k in idx) / len(idx), 4),
                          "real": round(sum(y[k] for k in idx) / len(idx), 4)})
    return filas


def minima_para_ganar(objetivo, stop, costo_gana, costo_pierde):
    """Probabilidad por debajo de la cual el ciclo pierde dinero en promedio (todo en fracción).

    Gana: objetivo - costo_gana.  Pierde: stop + costo_pierde.
    EV = p·(objetivo - costo_gana) - (1 - p)·(stop + costo_pierde) = 0.
    """
    return (stop + costo_pierde) / (objetivo - costo_gana + stop + costo_pierde)
