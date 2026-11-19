"""Pruebas de la regla del 70 % (18/11/2026, orden del dueño: «cuando esté en el 70 % o por encima, que se arme solo») con el
Binance simulado de Fable 5.2. Sin red, sin llaves reales, sin dinero. El Centro se reemplaza por una lista que la prueba controla.

Uso: python3 -I prueba_regla70.py"""
import json
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import conexion as C  # noqa: E402
import nucleo as N  # noqa: E402
import operador as O  # noqa: E402
import simulador as S  # noqa: E402

T0 = 1794930300
MODELO = {"w": [0.0] + [0.0] * 12, "mu": [0.0] * 12, "de": [1.0] * 12, "h": [1.0] * 8, "H": [1.0] * 8, "p_empate": 0.0}
FALLOS, CUENTA = [], [0]
CENTRO = {"valor": None}


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


def e(id_, k, n=25):
    return {"id": id_, "nombre": f"estrategia {id_}", "k25": k, "n25": n, "pct25": round(100 * k / n)}


class Correo:
    def __init__(self):
        self.textos = []

    def enviar(self, texto):
        self.textos.append(texto)

    def recibidos(self):
        return []

    def arrancar(self):
        pass


def montar(**permisos):
    base = tempfile.mkdtemp(prefix="regla70_")
    carpeta, llaves = os.path.join(base, "operador"), os.path.join(base, "llaves")
    os.makedirs(os.path.join(carpeta, "datos"))
    os.makedirs(llaves)
    N.DATOS = os.path.join(carpeta, "datos")
    for W in N.VENTANAS:
        with open(os.path.join(N.DATOS, f"modelo_{W}.json"), "w", encoding="utf-8") as f:
            json.dump(dict(MODELO, huella=f"regla-{W}"), f)
    with open(os.path.join(llaves, "operar.txt"), "w", encoding="utf-8") as f:
        f.write("apiKey=clave-falsa-del-simulador\nsecretKey=secreto-falso-del-simulador\n")
    C.CARPETA_LLAVES = llaves
    sim = S.Binance(T0 - 300 * 60)
    sim.sembrar(T0 - 300 * 60, T0 + 4 * 3600)
    sim.dar_llave("clave-falsa-del-simulador", "secreto-falso-del-simulador", operar=True, **permisos)
    sim.saldo["CeDeFi"] = 100.0
    sim.libro = lambda t, W, t_ini, lado: [(0.40, 1000.0)] if lado == 1 else [(0.60, 1000.0)]
    S.enchufar(C, sim)
    sim.t = T0 + 1
    correo = Correo()
    op = O.Operador(con=C, carpeta=carpeta, correo=correo, juez_en_hilo=False)
    return op, sim, correo, base


def correr(op, sim, segundos):
    fin = sim.t + segundos
    while sim.t < fin:
        op.paso()
        sim.t += op.pausa()


def poner_regla(op):
    with open(op.ruta_regla(), "w", encoding="utf-8") as f:
        f.write("regla puesta por la prueba\n")


def main():
    O.estrategias_centro = lambda plazo=5: CENTRO["valor"]       # el Centro lo controla la prueba
    op, sim, correo, base = montar()
    correr(op, sim, 120)
    ok(op._estado() == 2, "con la llave de operar que pasa, sin ARMADO: estado 2 (papel con precios reales)")

    CENTRO["valor"] = [e("E3", 20), e("E1", 8)]
    correr(op, sim, 180)
    ok(not op.ej.armado(), "sin la regla puesta no se arma, aunque una estrategia vaya en 20 de 25")

    poner_regla(op)
    CENTRO["valor"] = [e("E3", 17), e("E1", 8), e("E5", 14)]
    correr(op, sim, 180)
    ok(not op.ej.armado(), "con la regla y la mejor en 17 de 25 (68 %): no se arma")

    CENTRO["valor"] = [e("E3", 18, 20), e("E1", 8)]
    correr(op, sim, 180)
    ok(not op.ej.armado(), "18 aciertos pero con solo 20 cerradas: no se arma (hacen falta las 25)")

    CENTRO["valor"] = None
    correr(op, sim, 120)
    ok(not op.ej.armado(), "si el Centro no responde, no se arma ni se cae nada")

    n_avisos = len(correo.textos)
    CENTRO["valor"] = [e("E3", 18), e("E1", 8)]
    correr(op, sim, 120)
    a = op.ej.armado()
    ok(bool(a) and a.get("mercados") == list(N.VENTANAS), "en 18 de 25 (72 %) se arma solo, los dos mercados")
    ok(bool(a) and "regla" in a.get("por", "") and "18 de 25" in a.get("nota", ""), "el ARMADO queda firmado por su regla y con la estrategia que la cumplió")
    nuevos = correo.textos[n_avisos:]
    ok(any("Me armé solo" in x and "E3" in x and "18 de 25" in x for x in nuevos), "le avisa por Telegram que se armó solo y por qué")
    ok(op._estado() == 3, "queda en estado 3 (ARMADO: ejecuta las órdenes de la IA)")

    r = op._atender(sim.t, ["parar"], {"id": 901})
    ok(not op.ej.armado() and not os.path.exists(op.ruta_regla()) and "quitada" in (r or ""),
       "«operador parar» desarma y quita la regla")
    CENTRO["valor"] = [e("E3", 22)]
    correr(op, sim, 180)
    ok(not op.ej.armado(), "después de «operador parar» no se vuelve a armar solo, ni con 22 de 25")

    r = op._atender(sim.t, ["automatico"], {"id": 902})
    ok(os.path.exists(op.ruta_regla()) and "regla puesta" in (r or ""), "«operador automático» vuelve a poner la regla")
    correr(op, sim, 120)
    ok(bool(op.ej.armado()), "con la regla de nuevo y 22 de 25, se arma solo otra vez")
    t = op.linea_estado(sim.t)
    ok("Estado 3" in t, "el estado lo dice: armado")
    ok(not op.ej.ordenes and sim.escrituras == 0, "en todo esto ninguna orden ni escritura en Binance (sin orden de la IA no se compra)")
    shutil.rmtree(base, ignore_errors=True)

    # una llave con futuros: no se arma y lo avisa una sola vez
    op, sim, correo, base = montar(enableFutures=True)
    correr(op, sim, 120)
    poner_regla(op)
    CENTRO["valor"] = [e("E2", 19)]
    correr(op, sim, 300)
    avisos = [x for x in correo.textos if "no me armo" in x]
    ok(not op.ej.armado() and len(avisos) == 1 and "futuros" in avisos[0],
       "con una llave que trae futuros no se arma, y lo avisa una sola vez")
    shutil.rmtree(base, ignore_errors=True)

    print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
