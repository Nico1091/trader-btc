"""Pruebas del candado del aprobador (17/11/2026) con el Binance simulado de Fable 5.2. Sin red, sin llaves reales, sin dinero.

1. El candado solo (aprobacion.falta): cada caso en que NO debe haber orden real y el único en que sí.
2. El operador completo en el simulador, ARMADO en una carpeta temporal, con la llave de operar falsa del simulador:
   - sin decisiones del nodo: cero órdenes reales, cada intento queda anotado con su motivo, y el papel compra igual;
   - con «COMPRAR SUBE» vigente: compra; con «NO COMPRAR», con el otro sentido, vieja o copiada de la caja: no compra;
   - el papel (miradas y llenados) es idéntico con y sin decisiones: el candado no lo toca.
3. Antes y después: con --antes CARPETA (una copia del operador tal como lo dejó Fable, p. ej. el commit 7429f90), el mismo
   escenario con el código original y con el nuevo más la aprobación da las mismas órdenes y el mismo registro.

Uso: python3 -I prueba_aprobacion.py [--antes CARPETA_DEL_OPERADOR_ORIGINAL]
Cada escenario corre en un proceso aparte (python3 -I prueba_aprobacion.py --escenario ...), porque la conexión guarda estado."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
T0 = 1794930300                     # múltiplo de 900: abre un mercado de 15 y uno de 5
DURACION = 35 * 60
FALLOS, CUENTA = [], [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


# ---------------------------------------------------------------- 1. el candado solo
def pruebas_candado():
    sys.path.insert(0, AQUI)
    import aprobacion as A
    d = tempfile.mkdtemp(prefix="aprob_")
    r = os.path.join(d, "decisiones.jsonl")
    W, t, ahora = 15, T0, T0 + 300

    def escribir(*filas, crudo=None):
        with open(r, "w", encoding="utf-8") as f:
            for x in filas:
                f.write(json.dumps(x) + "\n")
            if crudo:
                f.write(crudo)

    def dec(decision, cuando=T0 + 70, **k):
        return {"t": cuando, "W": W, "ventana": t, "dir": 1, "decision": decision, **k}

    ok(A.falta(W, t, 1, ahora, os.path.join(d, "no-existe.jsonl")) is not None, "candado: sin archivo de decisiones, no compra")
    escribir()
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: archivo vacío, no compra")
    escribir(crudo="{esto no es json\n")
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: línea ilegible, no compra")
    escribir(dec("COMPRAR SUBE"))
    ok(A.falta(W, t, 1, ahora, r) is None, "candado: COMPRAR SUBE vigente para ese mercado y sentido: sí compra")
    ok(A.falta(W, t, -1, ahora, r) is not None, "candado: aprobado SUBE, la orden de BAJA no pasa")
    ok(A.falta(5, t, 1, ahora, r) is not None, "candado: aprobado el de 15 min, el de 5 min no pasa")
    ok(A.falta(W, t + 900, 1, ahora + 900, r) is not None, "candado: aprobada una ventana, la siguiente no pasa")
    ok(A.falta(W, t, 1, T0 + 70 + A.CADUCIDAD_S + 1, r) is not None, "candado: la aprobación vence a los 10 minutos")
    ok(A.falta(W, t, 1, t + 900, r) is not None, "candado: con la ventana cerrada no pasa")
    escribir(dec("NO COMPRAR"))
    ok("NO COMPRAR" in (A.falta(W, t, 1, ahora, r) or ""), "candado: NO COMPRAR, no compra")
    escribir(dec(None, detalle="sin respuesta de Claude"))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: sin respuesta de Claude, no compra")
    escribir(dec("COMPRAR SUBE"), dec("NO COMPRAR", T0 + 200))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: manda la última decisión (NO COMPRAR después de COMPRAR)")
    escribir(dec("NO COMPRAR"), dec("COMPRAR SUBE", T0 + 200))
    ok(A.falta(W, t, 1, ahora, r) is None, "candado: manda la última decisión (COMPRAR después de NO COMPRAR)")
    escribir(dec("COMPRAR SUBE"), dict(dec("COMPRAR BAJA", T0 + 200), dir=-1))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: puntos contrarios en la misma ventana: vale la última, no compra SUBE")
    escribir(dec("COMPRAR SUBE", copia_de="192.168.20.45"))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: una decisión copiada de la caja no autoriza al operador del teléfono")
    escribir(dec("COMPRAR SUBE", T0 + 300 + A.FUTURO_S + 60))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: decisión con hora del futuro (reloj raro), no compra")
    escribir(dict(dec("COMPRAR SUBE"), t="mañana"))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: decisión sin hora legible, no compra")
    escribir(dict(dec("COMPRAR SUBE"), dir=-1))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: decisión que no coincide con su punto, no compra")
    relleno = [dict(dec("NO COMPRAR", T0 - 86400 + i), ventana=T0 - 86400 + 900 * (i % 90)) for i in range(4000)]
    escribir(*relleno, dec("COMPRAR SUBE"))
    t1 = time.perf_counter()
    res = A.falta(W, t, 1, ahora, r)
    ms = (time.perf_counter() - t1) * 1000
    ok(res is None and os.path.getsize(r) > A.COLA_BYTES, f"candado: archivo grande ({os.path.getsize(r) // 1024} KB): lee solo la cola ({ms:.0f} ms)")
    ok(A.falta(W, t, 1, ahora, "/proc/no/existe/x.jsonl") is not None, "candado: ruta imposible, no compra (no lanza)")
    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 2. el operador entero en el simulador (proceso aparte)
MODELO = {"w": [0.0] + [0.0] * 12, "mu": [0.0] * 12, "de": [1.0] * 12, "h": [1.0] * 8, "H": [1.0] * 8, "p_empate": 0.0,
          "huella": "prueba-aprobador"}


def escenario(codigo, salida, modo):
    """Corre DURACION segundos de operador ARMADO contra el simulador y guarda lo que pasó. modo: ninguna, todas, no,
    contraria, vieja, copia (las decisiones que el «nodo» deja para cada ventana) o antes (código sin candado)."""
    sys.path.insert(0, codigo)
    import conexion as C
    import nucleo as N
    import simulador as S
    import operador as O
    base = tempfile.mkdtemp(prefix="esc_")
    carpeta, llaves, nodo = (os.path.join(base, x) for x in ("operador", "llaves", "nodo"))
    for x in (carpeta, llaves, nodo, os.path.join(carpeta, "datos")):
        os.makedirs(x, exist_ok=True)
    N.DATOS = os.path.join(carpeta, "datos")
    for W in N.VENTANAS:
        with open(os.path.join(N.DATOS, f"modelo_{W}.json"), "w", encoding="utf-8") as f:
            json.dump(dict(MODELO, huella=f"prueba-{W}"), f)
    with open(os.path.join(llaves, "operar.txt"), "w", encoding="utf-8") as f:
        f.write("apiKey=clave-falsa-del-simulador\nsecretKey=secreto-falso-del-simulador\n")
    C.CARPETA_LLAVES = llaves
    sim = S.Binance(T0 - 300 * 60)
    sim.sembrar(T0 - 300 * 60, T0 + DURACION + 7200)
    sim.dar_llave("clave-falsa-del-simulador", "secreto-falso-del-simulador", operar=True)
    sim.saldo["CeDeFi"] = 100.0
    sim.libro = lambda t, W, t_ini, lado: [(0.40, 1000.0)] if lado == 1 else [(0.60, 1000.0)]
    S.enchufar(C, sim)
    with open(os.path.join(carpeta, "ARMADO"), "w", encoding="utf-8") as f:   # solo en esta carpeta temporal de la prueba
        json.dump({"mercados": [15, 5], "por": "prueba con el simulador", "apto": {}}, f)
    ruta_dec = os.path.join(nodo, "decisiones.jsonl")
    A = getattr(sys.modules["ejecutor"], "APROBACION", None)   # el código original de Fable no lo tiene
    if A is not None:
        A.RUTAS = (ruta_dec,)
        if modo == "vieja":
            A.CADUCIDAD_S = 20      # la aprobación de t + 30 vence antes de la primera mirada (t + 60)

    class Correo:
        def __init__(self):
            self.textos = []

        def enviar(self, texto):
            self.textos.append(texto)

        def recibidos(self):
            return []

        def arrancar(self):
            pass

    correo = Correo()
    sim.t = T0 + 1
    op = O.Operador(con=C, carpeta=carpeta, correo=correo, juez_en_hilo=False)
    escritas = set()
    pasos, errores = 0, []
    while sim.t < T0 + DURACION:
        if modo not in ("ninguna", "antes"):
            for W in N.VENTANAS:
                t = int(sim.t // (60 * W)) * 60 * W
                if (W, t) in escritas or sim.t < t + 30:
                    continue
                escritas.add((W, t))
                fila = {"t": t + 30, "W": W, "ventana": t, "dir": 1, "decision": "COMPRAR SUBE", "sube": "telefono"}
                if modo == "no":
                    fila["decision"] = "NO COMPRAR"
                elif modo == "contraria":
                    fila.update(dir=-1, decision="COMPRAR BAJA")
                elif modo == "copia":
                    fila["copia_de"] = "192.168.20.45"
                with open(ruta_dec, "a", encoding="utf-8") as f:
                    f.write(json.dumps(fila) + "\n")
        try:
            op.paso()
        except Exception as ex:          # como el bucle de operador.main: anota y sigue
            errores.append(f"{type(ex).__name__}: {ex}"[:200])
            sim.t += 3
        pasos += 1
        sim.t += op.pausa()
    filas = []
    for n in sorted(os.listdir(op.registro)):
        with open(os.path.join(op.registro, n), encoding="utf-8") as f:
            filas += [json.loads(x) for x in f]
    papel = [{k: r.get(k) for k in ("tipo", "W", "t", "m", "lado", "decide", "llenado", "compra", "q", "motivo")}
             for r in filas if r.get("tipo") in ("mirada", "llenado", "resultado")]
    ordenes_reg = [{k: r.get(k) for k in ("W", "t", "m", "lado", "enviada", "motivo", "usdt", "cotizado", "estado")}
                   for r in filas if r.get("tipo") == "orden"]
    ordenes = [{k: o.get(k) for k in ("id", "W", "t", "lado", "usdt", "cotizado", "estado", "comprado", "res", "neto")}
               for o in op.ej.ordenes]
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"pasos": pasos, "papel": papel, "ordenes_reg": ordenes_reg, "ordenes": ordenes, "saldo": sim.saldo,
                   "escrituras": sim.escrituras, "avisos": len(correo.textos),
                   "estado": op._estado(), "candado": A is not None, "errores": errores[:5]}, f, ensure_ascii=False)
    shutil.rmtree(base, ignore_errors=True)


def correr(codigo, modo):
    sal = tempfile.mktemp(prefix="esc_", suffix=".json")
    t1 = time.perf_counter()
    r = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), "--escenario", codigo, sal, modo],
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-3000:])
        return None
    with open(sal, encoding="utf-8") as f:
        d = json.load(f)
    os.remove(sal)
    d["segundos"] = round(time.perf_counter() - t1, 1)
    return d


def pruebas_operador(antes):
    res = {m: correr(AQUI, m) for m in ("ninguna", "todas", "no", "contraria", "vieja", "copia")}
    if any(v is None for v in res.values()):
        ok(False, "los escenarios del simulador corrieron")
        return
    n, s = res["ninguna"], res["todas"]
    tiempos = ", ".join("%s %s s" % (m, v["segundos"]) for m, v in res.items())
    print(f"     (escenarios de {DURACION // 60} min simulados: {tiempos})")
    ok(n["estado"] == 3 and n["candado"], "el operador quedó en estado 3 (ARMADO con llave de operar) y con el candado")
    intentos = [o for o in n["ordenes_reg"] if o["enviada"] is False]
    ok(not n["ordenes"] and n["escrituras"] == 0 and n["saldo"]["CeDeFi"] == 100.0,
       "sin decisiones del nodo: cero órdenes reales y el saldo intacto")
    ok(intentos and all((o["motivo"] or "").startswith("sin aprobación de Claude") for o in intentos),
       f"sin decisiones: cada intento queda anotado con el motivo ({len(intentos)} intentos)")
    llen = [p for p in n["papel"] if p["tipo"] == "llenado" and p["compra"]]
    ok(len(llen) > 0, f"sin decisiones: el papel sigue comprando ({len(llen)} llenados)")
    ok(len(s["ordenes"]) > 0 and all(o["lado"] == 1 for o in s["ordenes"]),
       f"con COMPRAR SUBE vigente: compra de verdad ({len(s['ordenes'])} órdenes, todas SUBE)")
    ok(len({(o["W"], o["t"]) for o in s["ordenes"]}) == len(s["ordenes"]), "con aprobación: una orden por mercado, como antes")
    ok(any(o["estado"] == "FILLED" and o["res"] in (0, 1, 2) for o in s["ordenes"]), "con aprobación: hay órdenes compradas y liquidadas")
    ok(n["papel"] == s["papel"], "el papel (miradas, llenados y resultados) es idéntico con y sin decisiones")
    for m, que in (("no", "NO COMPRAR"), ("contraria", "aprobó BAJA"), ("vieja", "ya venció"),
                   ("copia", "el nodo no ha decidido")):
        r = res[m]
        mot = {o["motivo"] for o in r["ordenes_reg"] if o["enviada"] is False}
        ok(not r["ordenes"] and r["escrituras"] == 0 and any(que in x for x in mot),
           f"decisión «{m}»: no compra ({que})")
    if antes:
        a = correr(antes, "antes")
        if a is None:
            ok(False, "el escenario con el código original corrió")
            return
        ok(not a["candado"], "el código original no tiene candado (es el de Fable sin cambios)")
        ok(a["ordenes"] == s["ordenes"], f"antes y después: las mismas órdenes reales ({len(a['ordenes'])})")
        ok(a["ordenes_reg"] == s["ordenes_reg"] and a["papel"] == s["papel"], "antes y después: el mismo registro (órdenes y papel)")
        ok(a["saldo"] == s["saldo"] and a["escrituras"] == s["escrituras"], "antes y después: el mismo saldo y las mismas escrituras en Binance")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--escenario":
        escenario(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(0)
    antes = sys.argv[sys.argv.index("--antes") + 1] if "--antes" in sys.argv else None
    pruebas_candado()
    pruebas_operador(antes)
    print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
    sys.exit(1 if FALLOS else 0)
