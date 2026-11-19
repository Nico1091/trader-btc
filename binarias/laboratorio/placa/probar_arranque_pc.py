"""Prueba en el PC el arranque en frío de la placa (12/11/2026): reloj en cero (año 2000), como tras un corte de corriente.

Corre el bucle real de correr() con un reloj falso, un Binance falso (hora y velas de 1 min) y sin red. Casos:
A. Arranque en frío: debe pedir la hora en la primera vuelta y cargar las 340 velas seguidas sin contar errores.
B. La hora falla el primer minuto: no debe pedir ninguna vela sin hora, debe reintentar cada 15 s y cargar al volver.
C. Tras una hora, la hora falla pero las velas no: debe seguir con la hora anterior y no dejar de traer velas.
D. La versión anterior (binarias_placa.py.antes-arranque-frio-20261112) en el caso A: se queda sin velas (el fallo del 12/11).
Uso: python -I probar_arranque_pc.py"""
import importlib.machinery
import importlib.util
import math
import os
import sys
import tempfile
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
UNIX0 = 1794462000  # hora Unix real cuando el reloj falso marca 0


class Fin(BaseException):
    pass


def precio(t):
    return 73000 + 400 * math.sin(t / 3000) + 60 * math.sin(t / 700) + 15 * math.sin(t / 97)


def vela(t):
    o, c = precio(t), precio(t + 60)
    return [t * 1000, "%.2f" % o, "%.2f" % (max(o, c) + 3), "%.2f" % (min(o, c) - 3), "%.2f" % c,
            "%.3f" % (10 + 5 * math.sin(t / 400) ** 2), (t + 60) * 1000 - 1]


def montar(ruta_modulo, nombre, falla_hora):
    """Carga el programa de la placa con el reloj, la red y la memoria falsos. falla_hora(reloj) -> True si /time falla."""
    reloj = [5]
    for n in ("machine", "network"):
        sys.modules[n] = types.ModuleType(n)
    sys.modules["network"].WLAN = lambda *a: types.SimpleNamespace(isconnected=lambda: True, active=lambda *a: None, connect=lambda: None)
    sys.modules["network"].STA_IF = 0
    sys.modules["machine"].WDT = lambda timeout=0: types.SimpleNamespace(feed=lambda: None)
    sys.modules["machine"].reset = lambda: (_ for _ in ()).throw(Fin("la placa se reinició"))
    cargador = importlib.machinery.SourceFileLoader(nombre, ruta_modulo)  # sirve también para el respaldo, que no acaba en .py
    BP = importlib.util.module_from_spec(importlib.util.spec_from_loader(nombre, cargador))
    cargador.exec_module(BP)
    BP.time = types.SimpleNamespace(time=lambda: int(reloj[0]))
    pedidos = {"hora": 0, "velas": 0, "velas_sin_hora": 0}

    def https_json(ruta, tope=30000):
        ahora = UNIX0 + reloj[0]
        if ruta.startswith("/fapi/v1/time"):
            pedidos["hora"] += 1
            if falla_hora(reloj[0]):
                raise OSError("sin respuesta")
            return {"serverTime": ahora * 1000}
        pedidos["velas"] += 1
        if not getattr(BP, "hora_ok", BP.desfase != 0):
            pedidos["velas_sin_hora"] += 1
        q = dict(p.split("=") for p in ruta.split("?")[1].split("&"))
        limite = int(q["limit"])
        viva = ahora // 60 * 60
        if "startTime" in q:
            desde = int(q["startTime"]) // 1000
            if desde < 0:  # Binance contesta desde su primera vela (2019): todas ya cerradas hace años
                desde = 1567965420
            desde = -(-desde // 60) * 60
            return [vela(t) for t in range(desde, min(desde + 60 * limite, viva + 60), 60)]
        return [vela(t) for t in range(viva - 60 * (limite - 1), viva + 60, 60)]

    class Enchufe:
        def setsockopt(self, *a):
            pass

        bind = listen = settimeout = setsockopt

        def accept(self):
            reloj[0] += 1  # la espera de 1 s del servidor de la placa
            if reloj[0] >= tope[0]:
                raise Fin()
            raise OSError("sin clientes")

    tope = [0]
    BP.https_json = https_json
    BP.socket = types.SimpleNamespace(socket=Enchufe, SOL_SOCKET=1, SO_REUSEADDR=2)
    tmp = tempfile.mkdtemp()
    BP.ARCHIVO = os.path.join(tmp, "binarias.json")
    BP.PESOS = os.path.join(AQUI, "pesos.json")
    return BP, reloj, tope, pedidos


def correr_hasta(BP, tope, segundos):
    tope[0] = segundos
    try:
        BP.correr()
    except Fin as e:
        if str(e):
            raise SystemExit("FALLA: " + str(e))


def seguidas(BP):
    return all(BP.T[i] == BP.T[i - 1] + 60 for i in range(1, len(BP.T)))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    nuevo = os.path.join(AQUI, "binarias_placa.py")
    viejo = os.path.join(AQUI, "binarias_placa.py.antes-arranque-frio-20261112")
    fallas = []

    BP, reloj, tope, ped = montar(nuevo, "placa_a", lambda r: False)
    correr_hasta(BP, tope, 200)
    atraso = UNIX0 + reloj[0] - (BP.T[-1] + 60) if len(BP.T) else None
    print(f"A. arranque en frío, 200 s: reloj {BP.hora_ok}, velas {len(BP.T)}, seguidas {seguidas(BP)}, atraso de la última "
          f"{atraso} s, errores {BP.errores_red}, pedidos de hora {ped['hora']}, velas pedidas sin hora {ped['velas_sin_hora']}")
    if not (BP.hora_ok and len(BP.T) >= 338 and seguidas(BP) and atraso is not None and atraso < 130 and BP.errores_red == 0
            and ped["velas_sin_hora"] == 0):
        fallas.append("A")
    correr_hasta(BP, tope, 1500)
    atraso = UNIX0 + reloj[0] - (BP.T[-1] + 60)
    print(f"   a los 1.500 s: velas {len(BP.T)}, seguidas {seguidas(BP)}, atraso {atraso} s, errores {BP.errores_red}, "
          f"cierres de 5 min evaluados hasta {BP.est['hecho'] - UNIX0} s, propuesta {'sí' if BP.est.get('propuesta') else 'no'}")
    if not (seguidas(BP) and atraso < 70 and BP.errores_red == 0 and BP.est["hecho"] > UNIX0 + 1100):
        fallas.append("A-1500")

    BP, reloj, tope, ped = montar(nuevo, "placa_b", lambda r: r < 60)
    correr_hasta(BP, tope, 58)
    print(f"B. hora caída el primer minuto, a los 58 s: reloj {BP.hora_ok}, velas {len(BP.T)}, errores {BP.errores_red}, "
          f"pedidos de hora {ped['hora']}, velas pedidas {ped['velas']}")
    if not (not BP.hora_ok and len(BP.T) == 0 and ped["velas"] == 0 and 3 <= ped["hora"] <= 5 and BP.errores_red == ped["hora"]):
        fallas.append("B-58")
    correr_hasta(BP, tope, 200)
    print(f"   a los 200 s: reloj {BP.hora_ok}, velas {len(BP.T)}, seguidas {seguidas(BP)}, velas pedidas sin hora {ped['velas_sin_hora']}")
    if not (BP.hora_ok and len(BP.T) >= 338 and seguidas(BP) and ped["velas_sin_hora"] == 0):
        fallas.append("B-200")

    BP, reloj, tope, ped = montar(nuevo, "placa_c", lambda r: r > 3000)
    correr_hasta(BP, tope, 4400)
    atraso = UNIX0 + reloj[0] - (BP.T[-1] + 60)
    print(f"C. la hora falla desde los 3.000 s, a los 4.400 s: velas {len(BP.T)}, seguidas {seguidas(BP)}, atraso {atraso} s, "
          f"errores {BP.errores_red} ({BP.ultimo_error}), pedidos de hora {ped['hora']}")
    if not (seguidas(BP) and atraso < 70 and 2 <= BP.errores_red <= 4 and BP.ultimo_error.startswith("hora:")):
        fallas.append("C")

    if os.path.exists(viejo):
        BP, reloj, tope, ped = montar(viejo, "placa_d", lambda r: False)
        correr_hasta(BP, tope, 3500)
        print(f"D. versión anterior, arranque en frío, a los 3.500 s: velas {len(BP.T)}, errores {BP.errores_red}, "
              f"pedidos de hora {ped['hora']}, pedidos de velas {ped['velas']} (el fallo: una hora sin velas y sin errores)")
        if len(BP.T) != 0 or BP.errores_red != 0:
            fallas.append("D: la versión anterior no reproduce el fallo")
    print("RESULTADO:", "todo bien" if not fallas else "FALLA en " + ", ".join(fallas))
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
