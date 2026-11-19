"""Pruebas del laboratorio (11/11/2026). Uso: python -I prueba_laboratorio.py [--sin-centro]

1. Paridad con el Centro: E1 a E5 en los últimos 40 días de la historia, señal por señal y resultado por resultado, contra
   la clase Centro de mesa\\centro.py (copiada sin cambios) sembrada con las mismas velas (E5 en sus últimos 5 días, como
   siembra el Centro).
2. Recorte: ninguna señal anterior a T cambia al recortar el historial en T (40 formas al azar, las pasadas y el banco).
3. Candado: ningún archivo importa conexion, nombra llaves, REAL_AUTORIZADO, órdenes de /sapi/ ni la carpeta del centinela.
4. Huella de paridad PC-caja: huella de las apuestas de 20 formas fijas y de E1 y E2 en «elige»; debe salir igual en los dos.
Sale con código 0 solo si todo pasa."""
import ast
import hashlib
import os
import random
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import numpy as np  # noqa: E402

import emulador as EM  # noqa: E402
import formas as F  # noqa: E402
import juez as J  # noqa: E402
import rasgos as RG  # noqa: E402
import velas as VL  # noqa: E402
from comun import DESDE_PRUEBAS, TRAMO  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FALLAS = []


def decir(ok, texto):
    print(("BIEN  " if ok else "FALLA ") + texto, flush=True)
    if not ok:
        FALLAS.append(texto)


def lista(ctx, s, plazo):
    B, D, R, _RI = J.apuestas(ctx, s, plazo)
    return [(int(ctx.T[b]), int(d), int(r)) for b, d, r in zip(B, D, R)]


def paridad_centro(vel):
    import centro
    centro.ARCHIVO = os.path.join(tempfile.gettempdir(), "centro_prueba_lab.json")
    fin = vel.t_ultima() + 60
    win = vel.recorte(fin - 40 * 86400)
    ctx = RG.Contexto(win, None)
    v1 = F.velas1(ctx)
    c = centro.Centro(None)
    c.ops = {k: [] for k in centro.IDS}
    c.ultimo5 = 0
    c.v1 = v1
    c.cierre = {x[0]: x[4] for x in v1}
    ahora = v1[-1][0] + 60
    c._procesar(ahora, sembrando=True)
    c._calificar()
    suyo = {k: [(int(o["t"]), int(o["dir"]), int(o["res"])) for o in c.ops[k] if o["res"] in (0, 1)] for k in centro.IDS}
    mio = {"E1": lista(ctx, F.senal(ctx, F.normalizar({"pasada": "E1", "p": 15})), 15),
           "E2": lista(ctx, F.senal(ctx, F.normalizar({"pasada": "E2", "p": 15})), 15)}
    s3, s4 = F.senal_e3_e4(ctx)
    mio["E3"], mio["E4"] = lista(ctx, s3, 15), lista(ctx, s4, 15)
    s5 = np.zeros(ctx.nb, dtype=np.int8)
    for b in np.flatnonzero(ctx.T >= ahora - centro.DIAS_E5 * 86400):
        hasta = int(ctx.T[b]) - 60
        cb = RG.Contexto(win.recorte(hasta - 500 * 60, hasta), None)
        if cb.nb and int(cb.T[-1]) == int(ctx.T[b]):
            s5[b] = F.senal_e5_ultima(cb)
    mio["E5"] = lista(ctx, s5, 15)
    for k in centro.IDS:
        a, b = suyo[k], mio[k]
        primera = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
        decir(a == b, f"paridad {k} con el Centro en 40 días: Centro {len(a)} apuestas, laboratorio {len(b)}"
              + ("" if a == b else f"; primera diferencia en {primera}: {a[primera] if primera is not None and primera < len(a) else '-'} "
                                   f"frente a {b[primera] if primera is not None and primera < len(b) else '-'}"))


def recorte(vel, interes, motor):
    fin = vel.t_ultima() + 60
    win = vel.recorte(fin - 50 * 86400)
    full = RG.Contexto(win, interes)
    corte_T = int(full.T[full.nb * 2 // 3])
    cut = RG.Contexto(win.recorte(win.t0, corte_T - 60), interes)
    if motor is not None:
        full.prob, cut.prob = motor.prob(full), motor.prob(cut)
    nb = cut.nb
    rng = random.Random(4242)
    fichas = [F.aleatoria(rng) for _ in range(40)] + [F.normalizar({"pasada": x, "p": 15}) for x in ("E1", "E2")] + \
             [F.normalizar({"pasada": "nucleo", "p": 10})]
    malas = [F.describir(f) for f in fichas if not np.array_equal(F.senal(full, f)[:nb], F.senal(cut, f))]
    decir(not malas, f"recorte en {time.strftime('%d/%m %H:%M', time.gmtime(corte_T))} UTC: 43 formas de la gramática"
          + ("" if not malas else f"; cambian: {malas[:3]}"))
    a3, a4 = F.senal_e3_e4(full)
    b3, b4 = F.senal_e3_e4(cut)
    decir(np.array_equal(a3[:nb], b3) and np.array_equal(a4[:nb], b4), "recorte: E3 y E4")
    decir(np.array_equal(F.senal_t33(full)[:nb], F.senal_t33(cut)), "recorte: neurona t33")
    A, B = F.senales_banco(full), F.senales_banco(cut)
    malas = [k for k in A if not np.array_equal(A[k][:nb], B.get(k, np.zeros(nb, np.int8)))]
    decir(not malas, f"recorte: banco ({len(A)} señales)" + ("" if not malas else f"; cambian: {malas[:5]}"))
    if motor is not None:
        ok = all(np.allclose(full.prob[p][:nb], cut.prob[p], equal_nan=True, rtol=0, atol=1e-12) for p in (10, 15))
        decir(ok, "recorte: probabilidades de la red")


def candado():
    prohibido_mod = {"conexion"}
    prohibido_txt = ("lectura.txt", "REAL_AUTORIZADO", "/sapi/", ".config/binance", "centinela/", "centinela\\")
    malas = []
    for raiz, _d, archivos in os.walk(AQUI):
        for a in archivos:
            # llevar.py es la herramienta del PC que copia una vez el historial de velas desde el centinela (solo lectura):
            # no corre en la caja. Esta prueba nombra lo prohibido para buscarlo.
            if not a.endswith(".py") or a in ("prueba_laboratorio.py", "llevar.py"):
                continue
            ruta = os.path.join(raiz, a)
            arbol = ast.parse(open(ruta, encoding="utf-8").read())
            docs = set()
            for nodo in ast.walk(arbol):
                if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and nodo.body \
                        and isinstance(nodo.body[0], ast.Expr) and isinstance(getattr(nodo.body[0], "value", None), ast.Constant):
                    docs.add(id(nodo.body[0].value))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    malas += [f"{a}: import {n.name}" for n in nodo.names if n.name.split(".")[0] in prohibido_mod]
                elif isinstance(nodo, ast.ImportFrom) and (nodo.module or "").split(".")[0] in prohibido_mod:
                    malas.append(f"{a}: from {nodo.module}")
                elif isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and id(nodo) not in docs:
                    malas += [f"{a}: «{x}»" for x in prohibido_txt if x in nodo.value]
    decir(not malas, "candado: sin conexion, llaves, REAL_AUTORIZADO, /sapi/ ni carpeta del centinela" + (f"; hallado: {malas}" if malas else ""))


def huella_paridad(ctx):
    rng = random.Random(1111)
    fichas = [F.aleatoria(rng) for _ in range(20)] + [F.normalizar({"pasada": x, "p": 15}) for x in ("E1", "E2")]
    a, b = TRAMO["elige"]
    b0 = int(np.searchsorted(ctx.T, a))
    b1 = int(np.searchsorted(ctx.T, b))
    h = hashlib.sha256()
    total = 0
    for f in fichas:
        B, D, R, RI = J.apuestas(ctx, F.senal(ctx, f), f["p"], b0, b1)
        total += len(B)
        h.update(np.asarray(ctx.T[B], dtype=np.int64).tobytes() + D.tobytes() + R.tobytes() + RI.tobytes())
    print(f"HUELLA DE PARIDAD («elige», 22 formas, {total} apuestas): {h.hexdigest()[:24]}", flush=True)
    return h.hexdigest()


def main():
    inicio = time.time()
    vel = VL.Velas(*VL.historia(DESDE_PRUEBAS))
    interes = VL.cargar_interes()
    VL.cargar_indice(vel)
    try:
        motor = EM.MotorRed()
    except (OSError, ValueError, KeyError):
        motor = None
        print("(sin redes.json: la prueba de recorte va sin probabilidades)")
    candado()
    if "--sin-centro" not in sys.argv:
        paridad_centro(vel)
    recorte(vel, interes, motor)
    ctx = RG.Contexto(vel.recorte(DESDE_PRUEBAS, TRAMO["juzga"][1] + 86400), interes)
    if motor is not None:
        ctx.prob = EM.prob_historia(ctx, motor)
    huella_paridad(ctx)
    print(f"{'TODO BIEN' if not FALLAS else str(len(FALLAS)) + ' FALLAS'} en {time.time() - inicio:.0f} s")
    return 1 if FALLAS else 0


if __name__ == "__main__":
    sys.exit(main())
