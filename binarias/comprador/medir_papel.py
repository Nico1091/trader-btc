"""Mide con la red las compras de papel que ya anotó mesa\\perdida_real.py (series 1 y 2): qué probabilidad tenía el lado
comprado en ese momento y qué ganancia esperada dejaba el precio real pagado. Solo lee: el archivo de la Mesa y velas públicas
de contado de Binance. No usa llaves.

Cada compra cae en una de tres clases, según con qué precio se puede medir sin engañarse:
- «al cierre»: comprada en los 5 s siguientes al cierre de un minuto; vale la vela cerrada.
- «al instante»: serie 2, que guardó el precio de contado del momento; se mide con ese precio y los segundos que faltaban
  (enmienda 1). Si faltaba menos de un minuto queda marcada: la red no aprendió con menos de un minuto.
- «sin medir»: serie 1 comprada más de 5 s después del cierre; su precio guardado era de futuros y la vela cerrada ya era vieja.

Uso: python -X utf8 medir_papel.py"""
import collections
import json
import os
import sys
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import ganancia as G  # noqa: E402

OPS = os.path.join(os.path.dirname(AQUI), "mesa", "datos", "perdida_real.json")
SALIDA = os.path.join(AQUI, "datos", "papel_anterior.json")
CONTADO = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1000&startTime="


def velas(desde, hasta):
    """Velas de contado de 1 min entre desde y hasta (s): {apertura: (o, h, l, c, v)}."""
    out, t = {}, desde
    while t < hasta:
        req = urllib.request.Request(CONTADO + str(t * 1000), headers={"User-Agent": "comprador-binarias"})
        filas = json.loads(urllib.request.urlopen(req, timeout=25).read())
        if not filas:
            break
        for k in filas:
            out[int(k[0]) // 1000] = (float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
        t = int(filas[-1][0]) // 1000 + 60
    return out


def medir(ops, V, modelo):
    filas, sin_medir = [], 0
    for o in ops:
        t = o["t"]
        mm = min(14, int((o["hora"] - t) // 60))  # minutos de la ventana ya cerrados al comprar
        atraso = o["hora"] - (t + 60 * mm)         # segundos desde el cierre de ese minuto
        resta = t + 900 - o["hora"]
        ts = [t - 60 * k for k in range(75, 0, -1)] + [t + 60 * k for k in range(mm)]
        if mm < 1 or any(x not in V for x in ts):
            sin_medir += 1
            continue
        c, h, l, v = ([V[x][i] for x in ts] for i in (3, 1, 2, 4))
        strike = float(o.get("strike") or V[t][0])
        ask, com = {o["lado"]: o["precio"]}, o.get("comision", 0.02)
        if o.get("serie", 1) == 2 and o.get("btc") and resta > 0:
            clase = "al instante" if resta >= 60 else "al instante, último minuto"
            vec = G.vector(modelo, c, h, l, v, 75, mm, strike, ts[-1], ask, com, vivo=float(o["btc"]), resta_s=resta)
        elif atraso <= 5:
            clase, vec = "al cierre", G.vector(modelo, c, h, l, v, 75, mm, strike, ts[-1], ask, com)
        else:
            sin_medir += 1
            continue
        if vec is None:
            sin_medir += 1
            continue
        d = vec["lados"][o["lado"]]
        filas.append({"t": t, "regla": o["regla"], "serie": o.get("serie", 1), "clase": clase, "m": mm, "resta_s": int(resta),
                      "z": round(vec["z"], 3), "papel": d["papel"], "precio": o["precio"], "p": round(d["p"], 5),
                      "p_prud": round(d["p_prud"], 5), "G": round(d["G"], 4), "G_prud": round(d["G_prud"], 4),
                      "limite": round(d["limite"], 2), "res": o.get("res"), "neto": o.get("neto"), "disp": o.get("disp")})
    return filas, sin_medir


def cuenta(filas):
    x = {"n": len(filas), "aciertos": sum(f["res"] == 1 for f in filas), "esperados": round(sum(f["p"] for f in filas), 2),
         "neto": round(sum(f["neto"] or 0.0 for f in filas), 2), "con_ganancia": sum(f["G"] > 0 for f in filas),
         "cumple_v1": sum(f["G_prud"] >= G.MARGEN for f in filas)}
    if filas:
        x["precio_medio"] = round(sum(f["precio"] for f in filas) / len(filas), 4)
        x["G_media"] = round(sum(f["G"] for f in filas) / len(filas), 4)
        x["G_prud_media"] = round(sum(f["G_prud"] for f in filas) / len(filas), 4)
    return x


def main():
    modelo = G.cargar()
    ops = [o for o in json.load(open(OPS, encoding="utf-8"))["ops"] if o.get("res") in (0, 1)]
    V = velas(min(o["t"] for o in ops) - 80 * 60, max(o["t"] for o in ops) + 900)
    filas, sin_medir = medir(ops, V, modelo)
    print(f"{len(filas)} de {len(ops)} compras medidas con la red {modelo['huella']}; {sin_medir} sin medir (precio viejo o de futuros)")
    grupos = collections.OrderedDict()
    for f in filas:
        grupos.setdefault(f["clase"], []).append(f)
    out = {"modelo": modelo["huella"], "sin_medir": sin_medir, "clases": {}, "tramos_precio": {}, "filas": filas}
    for clase, fs in grupos.items():
        out["clases"][clase] = x = cuenta(fs)
        print(f"{clase}: {x}")
    # por precio pagado, solo lo medible dentro del rango de la red
    validas = [f for f in filas if f["clase"] != "al instante, último minuto"]
    for nombre, lo, hi in (("0,01", 0, 0.0101), ("0,02", 0.0101, 0.0201), ("0,03 a 0,05", 0.0201, 0.0501), ("0,06 a 0,10", 0.0501, 0.1001),
                           ("más de 0,10", 0.1001, 1)):
        fs = [f for f in validas if lo < f["precio"] <= hi]
        if fs:
            out["tramos_precio"][nombre] = x = cuenta(fs)
            pm = sum(f["p"] for f in fs) / len(fs)
            print(f"precio {nombre}: n {x['n']}, probabilidad media {100 * pm:.2f} %, ganancia esperada media {100 * x['G_media']:+.0f} % "
                  f"(prudente {100 * x['G_prud_media']:+.0f} %), con ganancia esperada {x['con_ganancia']}, pasan la regla v1 {x['cumple_v1']}, "
                  f"aciertos {x['aciertos']} (esperados {x['esperados']}), neto {x['neto']:+.2f}")
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    main()
