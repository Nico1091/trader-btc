"""C2 (28/10/2026): ingeniería inversa del historial de operaciones de los líderes de copy trading de Binance, y copia en papel.

Pedido de Nicolás: «métale inversa a lo que hace el que gana 6.986 %, a todo lo que hizo, y a los tres primeros; revise su
historial de operaciones y sus metodologías, y aplíquelo usted a ver cómo nos va».

Líderes estudiados:
- los 3 primeros por ROI propio a 90 días (lo que él pidió);
- los 3 cuyos copiadores más ganaron (c1_tabla_lideres.txt), porque el ROI del líder no predice lo que gana quien copia.
Para cada uno: todo su historial público de posiciones (lead-portfolio/position-history), y de ahí qué opera, en qué lado,
con qué apalancamiento, cuánto tiempo, a qué horas, qué tanto acierta y qué hacía el mercado (con nuestras velas de 1 m de
Binance) en la hora y las 4 horas anteriores a su entrada.
COPIA EN PAPEL (histórica): cada posición del líder se copia con un margen igual a f del saldo al abrir, su mismo apalancamiento,
su mismo resultado sobre el margen (roi de la posición), menos nuestra comisión (tomador 0,05 % al entrar y al salir, sobre el
nocional) y 0,05 % de deslizamiento por llegar tarde. f = 2, 5 y 10 %. Saldo inicial 40.000 COP.
Cuidado: se eligieron porque les fue bien en este mismo periodo; la copia histórica es optimista por construcción. La prueba
de verdad es la copia hacia adelante.
Uso: python -I c2_inversa_lideres.py > c2_inversa_lideres.txt"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request
from collections import Counter

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
BASE_DATOS = os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos")
DATOS = os.path.join(BASE_DATOS, "copy")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/141.0 Safari/537.36",
     "Content-Type": "application/json", "clienttype": "web"}
API = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/"
LIDERES = [  # (id, motivo): los 10 mejores por ROI propio a 180 días (el plazo más largo de la tabla), orden de Nicolás
    ("5108371059752839168", "1.º por ROI 180 días (+40.487 %)"),
    ("5154344801714752768", "2.º por ROI 180 días (+10.252 %; 1.º a 90 días con +6.986 %)"),
    ("5137430378342777089", "3.º por ROI 180 días (+9.335 %)"),
    ("5075281354358777856", "4.º por ROI 180 días (+6.960 %)"),
    ("5218493701996013313", "5.º por ROI 180 días (+6.422 %)"),
    ("5219911688676500225", "6.º por ROI 180 días (+6.287 %)"),
    ("5240448882690502145", "7.º por ROI 180 días (+5.984 %)"),
    ("5217752912495035905", "8.º por ROI 180 días (+5.727 %)"),
    ("5126298543040831233", "9.º por ROI 180 días (+5.484 %)"),
    ("5228797161728497664", "10.º por ROI 180 días (+4.761 %)"),
]
COP = 3177.85
CAP = 40000 / COP


def post(ruta, cuerpo):
    req = urllib.request.Request(API + ruta, data=json.dumps(cuerpo).encode(), headers=H, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def get(ruta):
    return json.loads(urllib.request.urlopen(urllib.request.Request(API + ruta, headers=H), timeout=30).read())


def historial(pid):
    ruta = os.path.join(DATOS, f"historial-{pid}.json")
    if os.path.exists(ruta) and time.time() - os.path.getmtime(ruta) < 6 * 3600:
        return json.load(open(ruta, encoding="utf-8"))
    filas, n = [], 1
    while True:
        d = post("lead-portfolio/position-history", {"pageNumber": n, "pageSize": 50, "portfolioId": pid, "sort": "OPENING"})["data"]
        lst = d.get("list") or []
        filas += lst
        if not lst or len(filas) >= (d.get("total") or 0) or n > 60:
            break
        n += 1
        time.sleep(0.6)
    json.dump(filas, open(ruta, "w", encoding="utf-8"))
    return filas


def velas_1m(simbolo):
    ruta = os.path.join(BASE_DATOS, "um", f"{simbolo}_um_1m.npy")
    if not os.path.exists(ruta):
        return None
    a = np.load(ruta)
    t = (a[:, 0] // 1000).astype("int64") if a[0, 0] > 1e11 else a[:, 0].astype("int64")
    return t, a[:, 4]


def antes(vel, t_ms, minutos):
    t, c = vel
    i = np.searchsorted(t, t_ms // 1000)
    if i < minutos or i >= len(t):
        return None
    return (c[i - 1] / c[i - minutos] - 1) * 100


def copiar(pos, f):
    """Copia en papel: margen f×saldo al abrir; resultado = margen × roi − comisiones y deslizamiento sobre el nocional."""
    ev = sorted([(p["opened"], 1, k) for k, p in enumerate(pos)] + [(p["closed"], 0, k) for k, p in enumerate(pos)])
    E, pico, cm, abiertas, dia = CAP, CAP, 0.0, {}, {}
    for t, tipo, k in ev:
        p = pos[k]
        if tipo == 1:
            abiertas[k] = f * E
        elif k in abiertas:
            m = abiertas.pop(k)
            lev = float(p.get("leverage") or 1)
            g = m * float(p.get("roi") or 0) - m * lev * (0.0010 + 0.0005)
            g = max(g, -m)  # en aislado/cruzado del copiador se pierde como mucho el margen de esa copia
            E += g
            d = dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc).date()
            dia[d] = dia.get(d, 0.0) + g
            pico = max(pico, E)
            cm = max(cm, 1 - E / pico if pico > 0 else 1)
            if E <= 0.01 * CAP:
                return 0.0, 1.0, dia
    return E, cm, dia


def main():
    os.makedirs(DATOS, exist_ok=True)
    print("C2 · ingeniería inversa de 6 líderes de copy trading de Binance y su copia en papel con 40.000 COP\n")
    vel_cache = {}
    for pid, motivo in LIDERES:
        try:
            det = get(f"lead-portfolio/detail?portfolioId={pid}").get("data") or {}
        except Exception:
            det = {}
        pos = [p for p in historial(pid) if p.get("closed") and p.get("opened")]
        if not pos:
            print(f"== {pid} ({motivo}): sin historial público\n")
            continue
        nombre = det.get("nickname") or pid
        t0, t1 = min(p["opened"] for p in pos), max(p["closed"] for p in pos)
        dias = max(1, (t1 - t0) / 86400000)
        roi = np.array([float(p.get("roi") or 0) for p in pos]) * 100
        lev = [int(float(p.get("leverage") or 1)) for p in pos]
        dur = np.array([(p["closed"] - p["opened"]) / 60000 for p in pos])
        sims = Counter(p["symbol"] for p in pos)
        lados = Counter(p.get("side") for p in pos)
        horas = Counter(dt.datetime.fromtimestamp(p["opened"] / 1000, dt.timezone.utc).hour for p in pos)
        gan, per = roi[roi > 0], roi[roi < 0]
        print(f"== {nombre} ({motivo}) · {len(pos)} posiciones en {dias:.0f} días ({len(pos) / dias:.1f} al día) ==")
        print(f"   Monedas: " + ", ".join(f"{s} {n}" for s, n in sims.most_common(6)))
        print(f"   Lado: " + ", ".join(f"{k} {v}" for k, v in lados.items()) + f" · apalancamiento: mediana {np.median(lev):.0f}x, máx {max(lev)}x")
        print(f"   Duración: mediana {np.median(dur):.0f} min · p90 {np.percentile(dur, 90):.0f} min")
        print(f"   Acierto {len(gan) / len(roi) * 100:.1f} % · ganadora media {gan.mean() if len(gan) else 0:+.1f} % del margen · "
              f"perdedora media {per.mean() if len(per) else 0:+.1f} % · peor {roi.min():+.1f} % · factor de beneficio "
              f"{gan.sum() / -per.sum() if len(per) and per.sum() < 0 else float('inf'):.2f}")
        print(f"   Horas de entrada (UTC) más usadas: " + ", ".join(f"{h:02d}h {n}" for h, n in horas.most_common(5)))
        # qué hacía el mercado antes de su entrada
        mov1, mov4 = [], []
        for p in pos:
            s = p["symbol"]
            if s not in vel_cache:
                vel_cache[s] = velas_1m(s)
            v = vel_cache[s]
            if v is None:
                continue
            a1, a4 = antes(v, p["opened"], 60), antes(v, p["opened"], 240)
            if a1 is None or a4 is None:
                continue
            signo = 1 if p.get("side") == "Long" else -1
            mov1.append(signo * a1)
            mov4.append(signo * a4)
        if mov1:
            m1, m4 = np.array(mov1), np.array(mov4)
            estilo = "a favor del movimiento (seguir la tendencia)" if np.median(m4) > 0.2 else \
                     "contra el movimiento (comprar caídas o vender subidas)" if np.median(m4) < -0.2 else "sin sesgo claro"
            print(f"   Antes de entrar (en su lado, {len(m1)} posiciones con nuestras velas): 1 h {np.median(m1):+.2f} % · 4 h {np.median(m4):+.2f} % "
                  f"(mediana) -> entra {estilo}")
        print("   Copia en papel desde 40.000 COP (optimista: elegido por su pasado):")
        for f in (0.02, 0.05, 0.10):
            E, cm, dia = copiar(pos, f)
            g = (E / CAP) ** (1 / dias) - 1 if E > 0 else -1
            dias_pos = sum(1 for v in dia.values() if v > 0)
            print(f"     margen {f * 100:.0f} % por copia: {E * COP:>12,.0f} COP · {g * 100:+.2f} % al día · caída máx. {cm * 100:.0f} % · "
                  f"días ganadores {dias_pos} de {len(dia)}")
        print()


if __name__ == "__main__":
    main()
