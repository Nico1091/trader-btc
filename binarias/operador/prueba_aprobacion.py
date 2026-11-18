"""Pruebas del candado y de la orden de la IA (17/11/2026; desde el 18/11/2026, «la IA ordena y el script ejecuta») con el
Binance simulado de Fable 5.2. Sin red, sin llaves reales, sin dinero.

1. El candado solo (aprobacion.orden y aprobacion.falta): cada caso en que NO debe haber orden real y los que sí, en los dos
   lados (comprar = SUBE, vender = BAJA), también cuando la IA ordena el lado contrario al del punto.
2. El operador completo en el simulador, ARMADO en una carpeta temporal, con la llave de operar falsa del simulador:
   - sin órdenes de la IA: cero órdenes reales aunque el papel compre (el operador ya no compra por su cuenta);
   - con «COMPRAR SUBE» vigente: compra SUBE; con «COMPRAR BAJA» sobre un punto de SUBE: vende (compra BAJA); siempre 2 USDT,
     una por mercado; con «NO COMPRAR», vieja, copiada de la caja o sin ARMADO: nada;
   - con poco saldo, los 2 USDT pasan el 16 % y no se envía; el motivo se anota una sola vez por orden, no en cada vuelta;
   - el papel (miradas y llenados) es idéntico con y sin órdenes de la IA.

Uso: python3 -I prueba_aprobacion.py
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
    ok(A.falta(W, t, 1, ahora, r) is None, "candado: COMPRAR SUBE vigente para ese mercado: sí compra SUBE")
    ok(A.falta(W, t, -1, ahora, r) is not None, "candado: ordenado comprar (SUBE), vender (BAJA) no pasa")
    ok(A.falta(5, t, 1, ahora, r) is not None, "candado: ordenado el de 15 min, el de 5 min no pasa")
    ok(A.falta(W, t + 900, 1, ahora + 900, r) is not None, "candado: ordenada una ventana, la siguiente no pasa")
    ok(A.falta(W, t, 1, T0 + 70 + A.CADUCIDAD_S + 1, r) is not None, "candado: la orden vence a los 10 minutos")
    ok(A.falta(W, t, 1, t + 900, r) is not None, "candado: con la ventana cerrada no pasa")
    escribir(dec("NO COMPRAR"))
    ok("NO COMPRAR" in (A.falta(W, t, 1, ahora, r) or ""), "candado: NO COMPRAR (nada), no compra")
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
    escribir(dict(dec("COMPRAR SUBE"), t=True))
    ok(A.falta(W, t, 1, ahora, r) is not None, "candado: decisión con hora «verdadero» (no es número), no compra")
    # 18/11/2026: la IA elige el lado, aunque el punto traiga el otro
    escribir(dict(dec("COMPRAR SUBE"), dir=-1))
    ok(A.falta(W, t, 1, ahora, r) is None, "orden de la IA: comprar (SUBE) sobre un punto de BAJA vale tal cual")
    escribir(dec("COMPRAR BAJA"))
    lado, x = A.orden(W, t, ahora, r)
    ok(lado == -1 and isinstance(x, dict) and x["decision"] == "COMPRAR BAJA",
       "orden de la IA: vender (BAJA) sobre un punto de SUBE vale tal cual")
    ok(A.falta(W, t, -1, ahora, r) is None and A.falta(W, t, 1, ahora, r) is not None,
       "orden de la IA: con vender, el candado abre BAJA y no SUBE")
    escribir(dec("COMPRAR SUBE"))
    ok(A.orden(W, t, ahora, r)[0] == 1, "orden de la IA: comprar = SUBE (1)")
    with open(r, "a", encoding="utf-8") as f:            # el nodo agrega una orden nueva: se lee sin esperar a otra cosa
        f.write(json.dumps(dec("COMPRAR BAJA", T0 + 200)) + "\n")
    ok(A.orden(W, t, ahora, r)[0] == -1, "orden de la IA: una línea nueva en el archivo se lee al momento (la copia guardada se renueva)")
    escribir(dec("NO COMPRAR"))
    lado, x = A.orden(W, t, ahora, r)
    ok(lado is None and "nada" in x, "orden de la IA: NO COMPRAR = nada, sin lado")
    for que, filas, en in (("vencida", (dec("COMPRAR SUBE"),), T0 + 70 + A.CADUCIDAD_S + 1),
                           ("con la ventana cerrada", (dec("COMPRAR SUBE"),), t + 900),
                           ("copiada de la caja", (dec("COMPRAR SUBE", copia_de="192.168.20.45"),), ahora),
                           ("de otro mercado", (dict(dec("COMPRAR SUBE"), W=5),), ahora)):
        escribir(*filas)
        ok(A.orden(W, t, en, r)[0] is None, f"orden de la IA: {que}, no hay orden")
    relleno = [dict(dec("NO COMPRAR", T0 - 86400 + i), ventana=T0 - 86400 + 900 * (i % 90)) for i in range(4000)]
    escribir(*relleno, dec("COMPRAR SUBE"))
    t1 = time.perf_counter()
    res = A.falta(W, t, 1, ahora, r)
    ms = (time.perf_counter() - t1) * 1000
    t1 = time.perf_counter()
    for _ in range(100):
        A.orden(W, t, ahora, r)
    ms100 = (time.perf_counter() - t1) * 1000
    ok(res is None and os.path.getsize(r) > A.COLA_BYTES, f"candado: archivo grande ({os.path.getsize(r) // 1024} KB): lee solo la cola ({ms:.0f} ms)")
    ok(ms100 < 20 * max(ms, 1.0), f"candado: sin cambios en el archivo no lo relee (100 consultas en {ms100:.0f} ms)")
    ok(A.falta(W, t, 1, ahora, "/proc/no/existe/x.jsonl") is not None, "candado: ruta imposible, no compra (no lanza)")
    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 2. el operador entero en el simulador (proceso aparte)
MODELO = {"w": [0.0] + [0.0] * 12, "mu": [0.0] * 12, "de": [1.0] * 12, "h": [1.0] * 8, "H": [1.0] * 8, "p_empate": 0.0,
          "huella": "prueba-aprobador"}
MODOS = ("ninguna", "todas", "no", "contraria", "vieja", "copia", "desarmado", "poco_saldo")


def escenario(codigo, salida, modo):
    """Corre DURACION segundos de operador contra el simulador y guarda lo que pasó. modo: ninguna, todas, no, contraria,
    vieja, copia (las decisiones que el «nodo» deja para cada ventana), desarmado (sin ARMADO) o poco_saldo (10 USDT)."""
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
    sim.saldo["CeDeFi"] = 10.0 if modo == "poco_saldo" else 100.0
    sim.libro = lambda t, W, t_ini, lado: [(0.40, 1000.0)] if lado == 1 else [(0.60, 1000.0)]
    S.enchufar(C, sim)
    if modo != "desarmado":
        with open(os.path.join(carpeta, "ARMADO"), "w", encoding="utf-8") as f:   # solo en esta carpeta temporal de la prueba
            json.dump({"mercados": [15, 5], "por": "prueba con el simulador", "apto": {}}, f)
    ruta_dec = os.path.join(nodo, "decisiones.jsonl")
    A = sys.modules["ejecutor"].APROBACION
    A.RUTAS = (ruta_dec,)
    if modo == "vieja":
        A.CADUCIDAD_S = -1          # toda orden ya vencida al leerla

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
        if modo != "ninguna":
            for W in N.VENTANAS:
                t = int(sim.t // (60 * W)) * 60 * W
                if (W, t) in escritas or sim.t < t + 30:
                    continue
                escritas.add((W, t))
                fila = {"t": t + 30, "W": W, "ventana": t, "dir": 1, "decision": "COMPRAR SUBE", "sube": "telefono"}
                if modo == "no":
                    fila["decision"] = "NO COMPRAR"
                elif modo == "contraria":
                    fila["decision"] = "COMPRAR BAJA"      # la IA ordena vender sobre un punto de SUBE
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
    ordenes_reg = [{k: r.get(k) for k in ("W", "t", "m", "lado", "enviada", "motivo", "usdt", "cotizado", "estado", "origen")}
                   for r in filas if r.get("tipo") == "orden"]
    ordenes = [{k: o.get(k) for k in ("id", "W", "t", "lado", "usdt", "cotizado", "estado", "comprado", "res", "neto", "origen",
                                      "decision")} for o in op.ej.ordenes]
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"pasos": pasos, "papel": papel, "ordenes_reg": ordenes_reg, "ordenes": ordenes, "saldo": sim.saldo,
                   "escrituras": sim.escrituras, "avisos": correo.textos, "decisiones": len(escritas),
                   "estado": op._estado(), "errores": errores[:5]}, f, ensure_ascii=False)
    shutil.rmtree(base, ignore_errors=True)


def correr(codigo, modo):
    sal = tempfile.mktemp(prefix="esc_", suffix=".json")
    t1 = time.perf_counter()
    r = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), "--escenario", codigo, sal, modo],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-3000:])
        return None
    with open(sal, encoding="utf-8") as f:
        d = json.load(f)
    os.remove(sal)
    d["segundos"] = round(time.perf_counter() - t1, 1)
    return d


def pruebas_operador():
    res = {m: correr(AQUI, m) for m in MODOS}
    if any(v is None for v in res.values()):
        ok(False, "los escenarios del simulador corrieron")
        return
    n, s, c = res["ninguna"], res["todas"], res["contraria"]
    tiempos = ", ".join("%s %s s" % (m, v["segundos"]) for m, v in res.items())
    print(f"     (escenarios de {DURACION // 60} min simulados: {tiempos})")
    ok(all(not v["errores"] for v in res.values()), "ningún escenario dejó errores en el bucle del operador")
    ok(n["estado"] == 3, "el operador quedó en estado 3 (ARMADO con llave de operar)")
    ok(not n["ordenes"] and n["escrituras"] == 0 and n["saldo"]["CeDeFi"] == 100.0,
       "sin órdenes de la IA: cero órdenes reales y el saldo intacto")
    ok(not n["ordenes_reg"], "sin órdenes de la IA: no se intenta nada (ni una fila de orden)")
    llen = [p for p in n["papel"] if p["tipo"] == "llenado" and p["compra"]]
    ok(len(llen) > 0, f"sin órdenes de la IA: el papel sigue comprando ({len(llen)} llenados) y aun así no hay compra real: "
                      "el operador ya no compra por su cuenta")
    ok(len(s["ordenes"]) > 0 and all(o["lado"] == 1 and o["origen"] == "ia" and o["decision"] == "COMPRAR SUBE" for o in s["ordenes"]),
       f"con «COMPRAR SUBE»: compra SUBE de verdad ({len(s['ordenes'])} órdenes de la IA)")
    ok(all(o["usdt"] == 2.0 for o in s["ordenes"] + c["ordenes"]), "cada orden de la IA es de 2 USDT")
    ok(len({(o["W"], o["t"]) for o in s["ordenes"]}) == len(s["ordenes"]), "una orden por mercado, como antes")
    ok(any(o["estado"] == "FILLED" and o["res"] in (0, 1, 2) for o in s["ordenes"]), "hay órdenes compradas y liquidadas")
    ok(any("comprar (SUBE)" in x and "por orden de la IA" in x for x in s["avisos"]),
       "Telegram: «ORDEN REAL por orden de la IA … comprar (SUBE)»")
    ok(len(c["ordenes"]) > 0 and all(o["lado"] == -1 and o["decision"] == "COMPRAR BAJA" for o in c["ordenes"]),
       f"con «COMPRAR BAJA» sobre un punto de SUBE: vende (compra BAJA) de verdad ({len(c['ordenes'])} órdenes)")
    ok(any("vender (BAJA)" in x for x in c["avisos"]), "Telegram: la orden de vender se avisa como «vender (BAJA)»")
    ok(n["papel"] == s["papel"] == c["papel"], "el papel (miradas, llenados y resultados) es idéntico con y sin órdenes de la IA")
    no_env = [o for o in s["ordenes_reg"] if o["enviada"] is False]
    ok(len(no_env) <= s["decisiones"], f"lo que no se envía se anota una vez por orden, no en cada vuelta ({len(no_env)} filas)")
    for m, que in (("no", "NO COMPRAR (nada)"), ("vieja", "vencida"), ("copia", "copiada de la caja")):
        r = res[m]
        ok(not r["ordenes"] and r["escrituras"] == 0 and r["saldo"]["CeDeFi"] == 100.0, f"orden {que}: no compra")
    d = res["desarmado"]
    ok(d["estado"] == 2 and not d["ordenes"] and d["escrituras"] == 0, "sin ARMADO (estado 2): ninguna orden aunque la IA ordene")
    p = res["poco_saldo"]
    mot = [o["motivo"] or "" for o in p["ordenes_reg"] if o["enviada"] is False]
    ok(not p["ordenes"] and p["escrituras"] == 0 and mot and all("16 %" in x for x in mot),
       f"con 10 USDT de saldo los 2 USDT pasan el 16 %: no se envía ({len(mot)} filas, una por orden)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--escenario":
        escenario(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(0)
    pruebas_candado()
    pruebas_operador()
    print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
    sys.exit(1 if FALLOS else 0)
