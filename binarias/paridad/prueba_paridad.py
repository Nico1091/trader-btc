# -*- coding: utf-8 -*-
"""Prueba de paridad (18/11/2026): la cuenta a mano del nodo (nodo.py, Libreta y cuenta) da, señal por señal, lo mismo que
analisis_paridad.py con los mismos datos, y lo mismo que pagaría la app con el botón (0,98 / precio).

Uso:  python -I prueba_paridad.py                 (datos sintéticos)
      python -I prueba_paridad.py CARPETA         (además, los datos reales copiados del teléfono a CARPETA)
Solo lee; trabaja en carpetas temporales. Sin red."""
import glob
import json
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "nodo"))
import analisis_paridad as AP  # noqa: E402
import nodo as N  # noqa: E402

N.Libreta.REVISAR = 100000   # 20/11/2026: los datos de la prueba llegan de golpe (días enteros); en el equipo llegan de a una
N.AVISOS_DINERO = False

FALLOS, CUENTA = [], [0]


def ok(cond, que):
    CUENTA[0] += 1
    print(("OK   " if cond else "FALLO") + " " + que, flush=True)
    if not cond:
        FALLOS.append(que)


def equipo(raiz):
    c = {"rol": "telefono", "centinela": os.path.join(raiz, "centinela"), "operador": os.path.join(raiz, "operador"),
         "carpeta": os.path.join(raiz, "nodo"), "umbral": 19}
    for d in (os.path.join(c["centinela"], "datos"), os.path.join(c["operador"], "registro"), c["carpeta"]):
        os.makedirs(d, exist_ok=True)
    return c


def comparar(carpeta_datos, c, titulo, fu=None):
    """Corre los dos caminos con los mismos datos y compara cada señal con precio real y ganador oficial."""
    _r, precios, ganador, _l = AP.leer_registros(carpeta_datos)
    filas = AP.cruzar(AP.leer_senales(carpeta_datos), precios, ganador)
    analisis = {(f["est"], f["t"], f["dir"]): f for f in filas}
    fu = fu or N.Fuentes(c)
    resumenes = {(f, e): r for f, e, _W, r in fu.leer()}
    nodo = {}
    for k, lista in fu.libreta.por.items():
        fuente, est = k.split("|", 1)
        if fuente not in ("centro", "quince"):   # plan v9 (20/11): la libreta lleva también el papel del operador; aquí no
            continue
        for e in lista:
            nodo[(est, e["t"], e["dir"])] = e
    iguales = [k for k in analisis if k in nodo and abs(analisis[k]["q"] - nodo[k]["q"]) < 1e-12 and analisis[k]["g"] == nodo[k]["g"]
               and abs(analisis[k]["n_manual"] - AP.neto(nodo[k]["q"], nodo[k]["g"], nodo[k]["dir"])) < 1e-12]
    solo_a = sorted(set(analisis) - set(nodo))
    solo_n = sorted(set(nodo) - set(analisis))
    ok(analisis and len(iguales) == len(analisis) == len(nodo),
       f"{titulo}: {len(iguales)} de {len(analisis)} señales con el mismo precio, ganador y neto en el nodo y en el análisis"
       + (f" (solo en el análisis {solo_a[:3]}, solo en el nodo {solo_n[:3]})" if solo_a or solo_n else ""))
    # las cifras del punto (cuenta de las últimas 25) salen de esas mismas entradas
    bien = True
    for (fuente, est), r in resumenes.items():
        if fuente not in ("centro", "quince"):
            continue
        mias = sorted((f for f in filas if f["est"] == est), key=lambda f: f["t"])[-N.VENTANA:]
        neto = 0.0
        for f in mias:
            neto += f["n_manual"]
        if r["de"] != len(mias) or abs(r["neto"] - round(neto, 3)) > 1e-9:
            bien = False
            print(f"     {est}: nodo {r['de']} y {r['neto']}, análisis {len(mias)} y {round(neto, 3)}")
    ok(bien, f"{titulo}: la cuenta de cada estrategia en el nodo (últimas 25, neto a mano) es la del análisis")
    return fu


# ---------------------------------------------------------------- 1. datos sintéticos
base = tempfile.mkdtemp(prefix="paridad_")
c = equipo(base)
V0 = 1795017600                       # 18/11/2026 10:00 de Colombia, múltiplo de 900
reg, ops_e1, ops_q = [], [], []
for i in range(30):
    v = V0 + 900 * i
    g = (1, -1, 0)[i % 3]            # sube, baja y un empate cada tres mercados
    reg.append({"W": 15, "tipo": "resultado", "serie": "papel", "t": v, "ganador": g, "fuente": "oficial"})
    for m in range(1, 15):
        if i % 5 == 0 and m == 6:
            continue                 # una mirada perdida: se usa la del minuto siguiente
        reg.append({"W": 15, "tipo": "mirada", "serie": "papel", "t": v, "m": m, "hora": v + 60 * m,
                    "lados": {"1": {"q": round(0.05 + 0.06 * ((i + m) % 15), 2)}, "-1": {"q": round(0.95 - 0.06 * ((i + m) % 15), 2)}}})
    d = 1 if i % 2 else -1
    ops_e1.append({"t": v + 300, "dir": d, "res": 1 if g == d else 0})           # E1 a mitad de ventana (minuto 5)
    ops_q.append({"t": v, "dir": -d, "res": 1 if g == -d else (0.5 if g == 0 else 0)})   # vigía en la apertura
ops_e1.append({"t": V0 + 900 * 30 + 300, "dir": 1, "res": None})
reg.append({"W": 15, "tipo": "mirada", "serie": "sin_llave", "t": V0 - 900, "m": 6, "hora": V0 - 500,
            "lados": {"1": {"p": 0.5, "q": None}, "-1": {"p": 0.5, "q": None}}})
with open(os.path.join(c["operador"], "registro", "20261118.jsonl"), "w", encoding="utf-8") as f:
    for x in reg:
        f.write(json.dumps(x) + "\n")
N.escribir_json(os.path.join(c["centinela"], "datos", "centro.json"), {"ops": {"E1": ops_e1}})
N.escribir_json(os.path.join(c["centinela"], "quince.json"), {"ops": ops_q})
datos = os.path.join(base, "datos")
os.makedirs(datos)
shutil.copy(os.path.join(c["operador"], "registro", "20261118.jsonl"), os.path.join(datos, "operador_registro_20261118.jsonl"))
shutil.copy(os.path.join(c["centinela"], "datos", "centro.json"), os.path.join(datos, "centinela_datos_centro.json"))
shutil.copy(os.path.join(c["centinela"], "quince.json"), os.path.join(datos, "centinela_quince.json"))
fu = comparar(datos, c, "sintéticos")
e1 = fu.libreta.entradas("centro", "E1")
ok(any(e["m"] == 7 for e in e1) and all(e["m"] in (6, 7) for e in e1),
   "libreta: entra en el minuto de la señal más uno (6) y, si esa mirada se perdió, en el siguiente (7)")
ok(any(e["g"] == 0 for e in fu.libreta.entradas("quince", "quince")), "libreta: el empate del mercado queda como empate (medio pago)")
ok(os.path.exists(os.path.join(c["carpeta"], "dinero.json")) and N.Libreta(os.path.join(c["carpeta"], "dinero.json")).por == fu.libreta.por,
   "libreta: queda en dinero.json y se lee igual al arrancar de nuevo")
ok(N.cuenta([{"dir": 1, "g": 1, "q": 0.46}])["neto"] == round(0.98 / 0.46 - 1, 3) == 1.13
   and N.cuenta([{"dir": -1, "g": -1, "q": 0.58}])["neto"] == round(0.98 / 0.58 - 1, 3) == 0.69,
   "app: Up a 0,46 paga 2,13 y Down a 0,58 paga 1,69 por USDT, igual que las fotos de las 15:18")
lb = N.Libreta(os.path.join(base, "otra.json"))
lb.MAXIMO = 10
lb.apuntar("centro", "E1", ops_e1, fu.libros, fu.ganadores)
ok(len(lb.entradas("centro", "E1")) == 10 and lb.entradas("centro", "E1")[-1]["t"] == ops_e1[-2]["t"],
   "libreta: guarda solo las últimas MAXIMO de cada estrategia, en orden")
shutil.rmtree(base, ignore_errors=True)

# ---------------------------------------------------------------- 2. datos reales del teléfono (si se dan)
if len(sys.argv) > 1:
    real = sys.argv[1]
    base = tempfile.mkdtemp(prefix="paridad_real_")
    c = equipo(base)
    for patron, destino in (("*centro.json", os.path.join(c["centinela"], "datos", "centro.json")),
                            ("*quince.json", os.path.join(c["centinela"], "quince.json"))):
        hallados = glob.glob(os.path.join(real, patron))
        if hallados:
            shutil.copy(hallados[0], destino)
    # 20/11/2026: el registro se entrega día por día, como llega en el equipo; de golpe, el nodo poda de su memoria los libros
    # más viejos (600 ventanas) antes de apuntarlos, y con más de dos días de datos se perdían los primeros
    fu = N.Fuentes(c)
    for r in sorted(glob.glob(os.path.join(real, "*registro*.jsonl"))):
        shutil.copy(r, os.path.join(c["operador"], "registro", os.path.basename(r).rsplit("_", 1)[-1]))
        fu.leer()
    comparar(real, c, "datos reales del teléfono", fu)
    # 20/11/2026, plan v9: de golpe (como al arrancar el nodo con tres días de registro) la libreta queda igual que día por día
    base2 = tempfile.mkdtemp(prefix="paridad_golpe_")
    c2 = equipo(base2)
    for patron, destino in (("*centro.json", os.path.join(c2["centinela"], "datos", "centro.json")),
                            ("*quince.json", os.path.join(c2["centinela"], "quince.json"))):
        hallados = glob.glob(os.path.join(real, patron))
        if hallados:
            shutil.copy(hallados[0], destino)
    for r in sorted(glob.glob(os.path.join(real, "*registro*.jsonl"))):
        shutil.copy(r, os.path.join(c2["operador"], "registro", os.path.basename(r).rsplit("_", 1)[-1]))
    fu2 = N.Fuentes(c2)
    fu2.leer()
    cuentas = {k: (len(v), len(fu2.libreta.por.get(k, []))) for k, v in fu.libreta.por.items()}
    ok(cuentas and all(a == b for a, b in cuentas.values()) and any(k.startswith("operador|") for k in cuentas),
       "plan v9: con tres días de golpe la libreta guarda lo mismo que día por día, también el papel del operador "
       + ", ".join(f"{k} {a}" + ("" if a == b else f" ≠ {b}") for k, (a, b) in sorted(cuentas.items())))
    shutil.rmtree(base2, ignore_errors=True)
    shutil.rmtree(base, ignore_errors=True)

print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLO(S)'}: {CUENTA[0] - len(FALLOS)} de {CUENTA[0]}")
sys.exit(1 if FALLOS else 0)
