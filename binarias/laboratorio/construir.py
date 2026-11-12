"""Primera construcción del laboratorio en el PC (11/11/2026). Lo que sale va a la caja con su huella.

1. Archivos de la historia: interés abierto (datos\\metricas_crudos) e índice de precio (datos\\indice_crudos) en npz.
2. Los 19 rasgos de la red desde 2021 y sus etiquetas a 10 y 15 min (60 s tarde, empate fuera).
3. Red y neurona a ciegas mes a mes desde enero de 2024; se elige cuál usar en «elige» (la red debe ganar por 0,3 puntos).
4. Base nueva con las formas pasadas y sus cifras por tramo (E5 solo en vivo).
5. Primeras tandas de búsqueda (50 formas cada una, solo «elige»; «juzga» solo al entrar).
Uso: python -I construir.py [--tandas 20]"""
import hashlib
import json
import os
import shutil
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import numpy as np  # noqa: E402

import base  # noqa: E402
import busqueda as BQ  # noqa: E402
import formas as F  # noqa: E402
import juez as J  # noqa: E402
import rasgos as RG  # noqa: E402
import red as R  # noqa: E402
import velas as VL  # noqa: E402
from comun import BASE, DATOS, DESDE_RED, EQUILIBRIO, TRAMOS, hora, num, pct  # noqa: E402

PADRE = os.path.dirname(AQUI)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def decir(msg):
    print(f"{hora(time.time(), '%H:%M:%S')} {msg}", flush=True)


def huella_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    tandas = int(sys.argv[sys.argv.index("--tandas") + 1]) if "--tandas" in sys.argv else 20
    inicio = time.time()
    os.makedirs(DATOS, exist_ok=True)
    if not os.path.exists(VL.INTERES_NPZ):
        decir(f"interés abierto: {VL.armar_interes(os.path.join(PADRE, 'datos', 'metricas_crudos'))} instantáneas")
    if not os.path.exists(VL.INDICE_NPZ):
        decir(f"índice de precio: {VL.armar_indice(os.path.join(PADRE, 'datos', 'indice_crudos'))} minutos")
    shutil.copy2(os.path.join(PADRE, "pruebas", "t33_indice.json"), os.path.join(DATOS, "t33_indice.json"))

    vel = VL.Velas(*VL.historia(DESDE_RED))
    interes = VL.cargar_interes()
    VL.cargar_indice(vel)
    ctx = RG.Contexto(vel, interes)
    decir(f"velas: {vel.n} minutos desde {hora(vel.t0)}; barras de 5 min: {ctx.nb}; última: {hora(vel.t_ultima() + 60)}")

    X, ok = ctx.rasgos_red()
    y = {p: ctx.etiqueta(p) for p in (10, 15)}
    np.savez_compressed(os.path.join(DATOS, "red_X.npz"), X=X.astype(np.float32), ok=ok, y10=y[10], y15=y[15], T=ctx.T)
    decir(f"rasgos: {int(ok.sum())} barras completas de {ctx.nb}")

    redes, prob, crudo = {"t": int(time.time()), "plazos": {}}, {}, {}
    for p in (10, 15):
        p_red, p_neu, red, neu, inf = R.a_ciegas(X, ok, y[p], ctx.T, p, avisar=None)
        redes["plazos"][str(p)] = {"red": red.a_dict(), "neurona": neu.a_dict(), "informe": inf, "usa": inf["usa"]}
        prob[p] = p_red if inf["usa"] == "red" else p_neu
        crudo[f"r{p}"], crudo[f"n{p}"] = p_red, p_neu
        decir(f"plazo {p}: red {num(100 * inf['red']['acierto'])} % en {inf['red']['n']}, neurona "
              f"{num(100 * inf['neurona']['acierto'])} % en {inf['neurona']['n']} (confianza ≥ 0,56 en «elige»); usa {inf['usa']}")
    R.guardar(os.path.join(DATOS, "redes.json"), redes)
    np.savez_compressed(os.path.join(DATOS, "red_p.npz"), T=ctx.T, p10=prob[10], p15=prob[15], **crudo)
    ctx.prob = prob

    for x in (BASE, BASE + "-wal", BASE + "-shm"):
        if os.path.exists(x):
            os.replace(x, x + ".antes-" + hora(time.time(), "%Y%m%d%H%M"))
    con = base.abrir()
    for p in (10, 15):
        con.execute("INSERT INTO redes (tipo, plazo, t, datos, nota) VALUES ('mercado', ?, ?, ?, ?)",
                    (p, int(time.time()), json.dumps(redes["plazos"][str(p)]["informe"]), "construcción en el PC"))
    banco = F.senales_banco(ctx)
    s3, s4 = F.senal_e3_e4(ctx)
    t33 = F.senal_t33(ctx)
    lineas = []
    ahora = int(time.time())
    for ficha, nombre in F.pasadas(banco.keys()):
        fid = BQ.nueva_forma(con, ficha, "pasada", estado="viva", nombre=nombre)
        if fid is None:
            continue
        con.execute("UPDATE formas SET en_vivo=?, situacion='en observación', cambio=? WHERE id=?", (ahora, ahora, fid))
        q = ficha["pasada"]
        arr = (F.senal(ctx, ficha) if q in F.EQUIVALENTE else s3 if q == "E3" else s4 if q == "E4" else t33 if q == "t33"
               else banco.get(ficha.get("senal")) if q == "banco" else None)
        if arr is None:
            lineas.append(f"F-{fid:04d} {nombre}: sin historia (solo en vivo)")
            continue
        B, _D, Rr, RI = J.apuestas(ctx, arr, ficha["p"])
        cif = J.cifras(ctx, B, Rr, RI, ficha["p"])
        for tramo, c in cif.items():
            BQ.guardar_prueba(con, fid, tramo, c)
        e, j = cif["elige"], cif["juzga"]
        lineas.append(f"F-{fid:04d} {nombre}: elige {j_txt(e)} · juzga {j_txt(j)}")
    con.commit()
    decir(f"formas pasadas: {len(lineas)}")
    for k in range(tandas):
        r = BQ.tanda(con, ctx, semilla=1000 + k)
        decir(f"tanda {r['lote']}: {r['probadas']} probadas, {r['admitidas']} pasaron la valla, {r['a_vivo']} a vivo; red de búsqueda: "
              f"{'sí' if r['red'] else 'aún no'} ({r['aprendio_de']} pruebas); mejor Wilson inf. sobre el equilibrio: "
              f"{num(r['mejor_wi_sobre_eq'] or 0)} puntos; media red {fmt(r['media_red'])}, azar {fmt(r['media_azar'])}")
    rb, n = BQ.red_de_busqueda(con)
    if rb is not None:
        con.execute("INSERT INTO redes (tipo, plazo, t, datos, nota) VALUES ('busqueda', NULL, ?, ?, ?)",
                    (int(time.time()), json.dumps(rb.a_dict()), f"aprendió de {n} pruebas"))
    con.commit()
    huellas = {x: huella_archivo(os.path.join(DATOS, x))[:16] for x in sorted(os.listdir(DATOS)) if not x.endswith(".tmp")}
    informe = ["CONSTRUCCIÓN DEL LABORATORIO EN EL PC · " + hora(time.time(), "%d/%m/%Y %H:%M"),
               f"Duración: {num((time.time() - inicio) / 60)} min", "", "Redes (acierto con confianza ≥ 0,56 en «elige»):"]
    for p in (10, 15):
        inf = redes["plazos"][str(p)]["informe"]
        informe.append(f"  {p} min: red {num(100 * inf['red']['acierto'])} % en {inf['red']['n']}; neurona "
                       f"{num(100 * inf['neurona']['acierto'])} % en {inf['neurona']['n']}; se usa la {inf['usa']}")
    informe += ["", "Formas pasadas (acierto, n y Wilson inferior):"] + ["  " + x for x in lineas]
    informe += ["", base.resumen(con), "", "Huellas de datos:"] + [f"  {k}: {v}" for k, v in huellas.items()]
    open(os.path.join(DATOS, "construccion.txt"), "w", encoding="utf-8").write("\n".join(informe) + "\n")
    print("\n".join(informe))


def j_txt(c):
    if not c["n"]:
        return "sin señales"
    return f"{pct(c['k'] / c['n'])} en {c['n']} (Wilson inf. {pct(c['wi'])})"


def fmt(x):
    return "—" if x is None else num(x)


if __name__ == "__main__":
    main()
