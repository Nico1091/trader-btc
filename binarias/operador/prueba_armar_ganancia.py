"""Pruebas del armado por ganancia de dinero (plan v9, 20/11/2026; orden del dueño: «que ya no utilicemos esta de acierto, sino
otra cosa que sea por ganancia de dinero»), criterio A6 de ganancia/3-PROMPT-PLAN-v9-GANANCIA.md, con el Binance simulado de
Fable 5.2. Sin red, sin llaves reales, sin dinero. ganancia.json del nodo lo escribe la prueba. Reemplaza a prueba_regla70.py.

Uso: python3 -I prueba_armar_ganancia.py"""
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
GANA = "GANA DINERO (demostrado)"
FALLOS, CUENTA = [], [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


def fuente(nombre, estado="NO DEMOSTRADO", n=120, neto=-5.0, prueba=0.3, pausa=False, mercado=15):
    alto = estado == GANA and not pausa
    return {"nombre": nombre, "estado": estado, "regla_vigilante": estado, "demostrada": estado == GANA, "pausa": pausa,
            "alto": alto, "n": n, "neto": neto, "por_usdt": neto / n, "prueba": prueba, "umbral_prueba": 160.0, "mercado": mercado}


def escribir_ganancia(base, hora, fuentes):
    os.makedirs(os.path.join(base, "nodo"), exist_ok=True)
    with open(os.path.join(base, "nodo", "ganancia.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "v9", "hora": hora, "cuando": "prueba", "fuentes": fuentes,
                   "demostradas": sorted(k for k, d in fuentes.items() if d.get("alto"))}, f)


def quitar_ganancia(base):
    r = os.path.join(base, "nodo", "ganancia.json")
    if os.path.exists(r):
        os.remove(r)


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
    base = tempfile.mkdtemp(prefix="ganancia_op_")
    carpeta, llaves = os.path.join(base, "operador"), os.path.join(base, "llaves")
    os.makedirs(os.path.join(carpeta, "datos"))
    os.makedirs(llaves)
    N.DATOS = os.path.join(carpeta, "datos")
    for W in N.VENTANAS:
        with open(os.path.join(N.DATOS, f"modelo_{W}.json"), "w", encoding="utf-8") as f:
            json.dump(dict(MODELO, huella=f"ganancia-{W}"), f)
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
    O.GANANCIA_RUTA = None
    op, sim, correo, base = montar()
    correr(op, sim, 120)
    ok(op._estado() == 2, "con la llave de operar que pasa, sin ARMADO: estado 2 (papel con precios reales)")

    pierden = {"centro|E1": fuente("E1 · ruptura de 20 velas al revés", n=41, neto=-8.64),
               "operador|operador5": fuente("operador de Fable 5.2 (5 min)", n=116, neto=-21.13, mercado=5)}
    escribir_ganancia(base, sim.t, dict(pierden, **{"centro|E3": fuente("E3 · Gemini 1 al revés", GANA, 300, 60.0, 5000.0)}))
    correr(op, sim, 180)
    ok(not op.ej.armado(), "sin la regla puesta no se arma, aunque una fuente demuestre ganancia")

    poner_regla(op)
    escribir_ganancia(base, sim.t, pierden)
    correr(op, sim, 180)
    ok(not op.ej.armado(), "con la regla y ninguna fuente que demuestre ganancia de dinero: no se arma")

    quitar_ganancia(base)
    correr(op, sim, 120)
    ok(not op.ej.armado(), "sin ganancia.json (el nodo no ha medido): no se arma ni se cae nada")

    escribir_ganancia(base, sim.t - 1000, dict(pierden, **{"centro|E3": fuente("E3 · Gemini 1 al revés", GANA, 300, 60.0, 5000.0)}))
    correr(op, sim, 120)
    ok(not op.ej.armado(), "con ganancia.json de hace más de 15 min: no se arma aunque diga que una fuente gana (falla cerrado)")

    escribir_ganancia(base, sim.t, dict(pierden, **{"centro|E3": fuente("E3 · Gemini 1 al revés", GANA, 300, 60.0, 5000.0, pausa=True)}))
    correr(op, sim, 120)
    ok(not op.ej.armado(), "una fuente demostrada pero en pausa (sus últimas 25 pierden): no se arma")

    escribir_ganancia(base, sim.t, dict(pierden, **{"centro|E3": fuente("E3 · Gemini 1 al revés", GANA, 300, 60.0, 5000.0)}))
    n_avisos = len(correo.textos)
    correr(op, sim, 120)
    a = op.ej.armado()
    ok(bool(a) and a.get("mercados") == [15], "una fuente del Centro con ganancia de dinero demostrada: se arma solo, y solo el de 15 min")
    ok(bool(a) and "plan v9" in a.get("por", "") and "E3" in a.get("nota", "") and "de 25" not in a.get("nota", ""),
       "el ARMADO queda firmado por su regla del plan v9 y con el dinero de la fuente, no con aciertos")
    nuevos = correo.textos[n_avisos:]
    ok(any("GANANCIA DE DINERO" in x and "E3" in x and "Me armé solo" in x for x in nuevos),
       "le avisa por Telegram que se armó solo, con qué fuente y su dinero")
    ok(op._estado() == 3, "queda en estado 3 (ARMADO: ejecuta las órdenes de la IA)")

    r = op._atender(sim.t, ["dinero"], {"id": 900})
    ok("E3" in r and "E1" in r and "Demuestran ganancia: centro|E3" in r and "de 25" not in r,
       "«operador dinero» muestra el dinero de cada fuente y cuál lo demuestra")

    r = op._atender(sim.t, ["parar"], {"id": 901})
    ok(not op.ej.armado() and not os.path.exists(op.ruta_regla()) and "quitada" in (r or ""), "«operador parar» desarma y quita la regla")
    correr(op, sim, 180)
    ok(not op.ej.armado(), "después de «operador parar» no se vuelve a armar solo, aunque una fuente demuestre ganancia")

    r = op._atender(sim.t, ["automatico"], {"id": 902})
    ok(os.path.exists(op.ruta_regla()) and "GANANCIA DE DINERO" in (r or "") and "18 de 25" not in (r or ""),
       "«operador automático» vuelve a poner la regla, ahora por ganancia de dinero")
    escribir_ganancia(base, sim.t, dict(pierden, **{"centro|E3": fuente("E3 · Gemini 1 al revés", GANA, 300, 60.0, 5000.0)}))
    correr(op, sim, 120)
    ok(bool(op.ej.armado()), "con la regla de nuevo y la fuente demostrada, se arma solo otra vez")
    t = op.linea_estado(sim.t)
    ok("Estado 3" in t and "18 de 25" not in op._atender(sim.t, ["ayuda"], {"id": 903}), "el estado lo dice y la ayuda ya no habla de 18 de 25")
    ok(not op.ej.ordenes and sim.escrituras == 0, "en todo esto ninguna orden ni escritura en Binance (sin orden de la IA no se compra)")
    shutil.rmtree(base, ignore_errors=True)

    # la regla vieja del 70 % es la misma orden suya: se convierte una sola vez y avisa una sola vez
    op, sim, correo, base = montar()
    correr(op, sim, 120)
    with open(os.path.join(op.carpeta, O.REGLA_VIEJA), "w", encoding="utf-8") as f:
        f.write("Regla puesta por orden del dueño el 18/11/2026 en el chat con Claude.\n")
    escribir_ganancia(base, sim.t, pierden)
    n_avisos = len(correo.textos)
    correr(op, sim, 180)
    conv = [x for x in correo.textos[n_avisos:] if "versión 4" in x]
    ok(os.path.exists(op.ruta_regla()) and not os.path.exists(os.path.join(op.carpeta, O.REGLA_VIEJA)) and len(conv) == 1
       and "ya no mira aciertos" in conv[0] and "ninguna fuente" in conv[0],
       "ARMAR_AL_70 pasa a ARMAR_POR_GANANCIA una sola vez y le avisa que ya no mira aciertos")
    ok("18/11/2026" in open(op.ruta_regla(), encoding="utf-8").read() and not op.ej.armado(),
       "la regla convertida conserva su texto de origen, y sin fuente demostrada no arma")
    escribir_ganancia(base, sim.t, dict(pierden, **{"operador|operador5": fuente("operador de Fable 5.2 (5 min)", GANA, 400, 40.0,
                                                                                  900.0, mercado=5)}))
    correr(op, sim, 120)
    ok((op.ej.armado() or {}).get("mercados") == [5], "una fuente de 5 min demostrada arma solo el mercado de 5 min")
    shutil.rmtree(base, ignore_errors=True)

    # una llave con futuros: no se arma y lo avisa una sola vez
    op, sim, correo, base = montar(enableFutures=True)
    correr(op, sim, 120)
    poner_regla(op)
    escribir_ganancia(base, sim.t, {"centro|E2": fuente("E2 · ruptura de 50 velas al revés", GANA, 300, 50.0, 2000.0)})
    for _ in range(5):
        escribir_ganancia(base, sim.t, {"centro|E2": fuente("E2 · ruptura de 50 velas al revés", GANA, 300, 50.0, 2000.0)})
        correr(op, sim, 60)
    avisos = [x for x in correo.textos if "no me armo" in x]
    ok(not op.ej.armado() and len(avisos) == 1 and "futuros" in avisos[0], "con una llave que trae futuros no se arma, y lo avisa una sola vez")
    shutil.rmtree(base, ignore_errors=True)

    print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
