"""Precio real propio para la caja y el teléfono (11/11/2026, orden suya: que no dependan del PC ni del centinela).

Corre solo, con su propia llave de SOLO LECTURA en ~/.config/binance/lectura.txt (la de operar no sale del PC). Cada 2 a 5 s
lee el mercado de 15 min en curso y el libro de los dos lados en Predict.fun, igual que la Mesa, y aplica la misma regla de
perdida_real.py (a lo último, temprana y la red al final, con velas de contado y hora de Binance), liquidando con el ganador
oficial. Deja el resumen en datos/precio.json, que el laboratorio lee sin tocar llaves. Si la llave no está, espera y lo
revisa cada minuto. Solo consulta: su copia de conexion.py no trae las funciones de comprar, y con una llave de solo lectura
Binance rechazaría cualquier compra.
Uso: python3 -I precio_vivo.py     Parar: crear PARAR en esta carpeta."""
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ.setdefault("PRECIO_PLACA", "")  # en la caja y el teléfono no se le manda a la placa: cada equipo lleva lo suyo
os.environ.setdefault("PRECIO_FUENTE", "caja")
import conexion as C  # noqa: E402
import perdida_real as PR  # noqa: E402

PARAR = os.path.join(AQUI, "PARAR")
ESTADO = os.path.join(AQUI, "datos", "precio.json")
REGISTRO = os.path.join(AQUI, "precio.log")


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def escribir(estado):
    with open(ESTADO + ".tmp", "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, default=str)
    os.replace(ESTADO + ".tmp", ESTADO)


def main():
    os.makedirs(os.path.join(AQUI, "datos"), exist_ok=True)
    pr = PR.PerdidaReal(log)
    m, sin_llave, errores = None, 0.0, 0
    log("precio propio en marcha")
    while not os.path.exists(PARAR):
        if not os.path.exists(C.CLAVES):
            if time.time() - sin_llave > 3600:
                log("falta la llave de solo lectura en ~/.config/binance/lectura.txt: espero")
                sin_llave = time.time()
                escribir({"hora": int(time.time()), "falta_llave": True, "mercado": None, "resumen": pr.resumen()})
            time.sleep(60)
            continue
        ahora = C.ahora()  # hora de Binance, no la del equipo
        try:
            t = int(ahora // 900 * 900)
            if not m or m.get("t") != t:
                m = C.mercado_15m(t)
            if m:
                if (not m.get("strike") or not m.get("abierto")) and ahora - m.get("releido", 0) >= 10:
                    m["releido"] = ahora  # Binance aún no traía la apertura o el mercado no figuraba abierto: se vuelve a leer
                    x = C._leer_mercado(m["topic"])
                    for k in ("strike", "abierto", "precio", "estado", "tokens", "marketId", "comision_bps"):
                        m[k] = x.get(k) or m.get(k)
                C.leer_libros(m)
            pr.paso(ahora, m)
            escribir({"hora": int(ahora), "mercado": {k: m.get(k) for k in ("t", "strike", "ask", "bid", "abierto")} if m else None,
                      "resumen": pr.resumen()})
            errores = 0
        except Exception as ex:
            errores += 1
            if errores in (1, 10) or errores % 100 == 0:
                log(f"sin precio ({type(ex).__name__}: {str(ex)[:120]})")
            time.sleep(10)
        time.sleep(2 if 900 - ahora % 900 <= 200 else 5)
    log("PARAR: salgo")


if __name__ == "__main__":
    main()
