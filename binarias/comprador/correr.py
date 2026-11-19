"""Corre el papel del comprador sin abrir la Mesa (12/11/2026). Sin ventana, sin botones y sin avisos: solo lee y anota.

Hace lo mismo que el bucle de la Mesa para el papel: busca el mercado de 15 min en curso, lee el libro y llama al comprador
por ganancia esperada (comprador.py) y a las tres reglas anteriores (mesa\\perdida_real.py, serie 2), que además mandan el
resumen a la placa cada minuto. Usa la conexión de la Mesa y de ella solo las lecturas.

Un candado (puerto 8799) deja un solo dueño del papel: si la Mesa está abierta y lo tiene, este programa espera y lo toma
cuando ella se cierre; si este lo tiene, la Mesa no lleva papel.

Uso: pythonw -X utf8 correr.py        Parar: crear el archivo PARAR en esta carpeta."""
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
MESA = os.path.join(os.path.dirname(AQUI), "mesa")
sys.path.insert(0, MESA)
import conexion as C  # noqa: E402
import perdida_real as PR  # noqa: E402

sys.path.append(AQUI)
import comprador as CP  # noqa: E402

PARAR = os.path.join(AQUI, "PARAR")
REGISTRO = os.path.join(AQUI, "datos", "comprador.log")
ULTIMOS_S = 200  # en los últimos 200 s el libro se lee cada 2 s, como en la Mesa (ahí compra «a lo último» la serie 2)


def log(msg):
    try:
        with open(REGISTRO, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def mercado(ahora, m):
    """El mercado de la ventana en curso, releído cada 10 s mientras Binance no traiga la apertura o no figure abierto."""
    t = int(ahora // 900 * 900)
    if not m or m.get("t") != t:
        m = C.mercado_15m(t)
        if m is None:
            return None
        m["ask"], m["bid"] = {}, {}
    if (not m.get("strike") or not m.get("abierto")) and ahora - m.get("releido", 0) >= 10:
        m["releido"] = ahora
        x = C._leer_mercado(m["topic"])
        for k in ("strike", "abierto", "precio", "estado", "tokens", "marketId", "comision_bps"):
            m[k] = x.get(k) or m.get(k)
    return m


def main():
    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    if os.path.exists(PARAR):
        os.remove(PARAR)
    cp = CP.Comprador(C, log)
    pr = PR.PerdidaReal(log)
    m, errores, t_libro, t_mercado = None, 0, 0.0, 0.0
    log("papel del comprador en marcha" + ("" if cp.activo else " (en espera: la Mesa lleva el papel)"))
    while not os.path.exists(PARAR):
        try:
            ahora = C.ahora()
            if cp.activo:
                if not m or m.get("t") != int(ahora // 900 * 900) or not m.get("strike") or not m.get("abierto"):
                    if ahora - t_mercado >= 3:  # sin mercado publicado todavía: no se pregunta más de una vez cada 3 s
                        t_mercado = ahora
                        m = mercado(ahora, m)
                if m and m.get("t") == int(ahora // 900 * 900):
                    cp.paso(C.ahora(), m)  # primero el comprador: su lectura del cierre del minuto sirve también a la serie 2
                    ahora = C.ahora()
                    if 900 - ahora % 900 <= ULTIMOS_S and ahora - max(t_libro, m.get("libro_t", 0)) >= 2:
                        t_libro = ahora
                        C.leer_libros(m)
                    pr.extra = cp.corto()
                    pr.paso(C.ahora(), m)
                else:
                    cp.paso(ahora, None)  # sin mercado igual liquida lo pendiente
                    pr.paso(ahora, None)
            else:
                cp.paso(ahora, None)      # solo vuelve a pedir el candado
            errores = 0
        except Exception as ex:
            errores += 1
            if errores in (1, 10) or errores % 100 == 0:
                log(f"sin lectura ({type(ex).__name__}: {str(ex)[:140]})")
            time.sleep(10)
        time.sleep(1)
    log("PARAR: salgo")


if __name__ == "__main__":
    if sys.stdout is None or sys.stderr is None:  # con pythonw no hay consola
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    main()
