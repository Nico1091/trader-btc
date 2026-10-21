"""Banco de pruebas del trading seguido: ¿hay ventaja operando ciclos de segundos a minutos?

Uso:  python -u -I banco_rapido.py [--prueba]
      --prueba: 20 días, para comprobar la tubería de punta a punta en pocos minutos.

Qué hace, en orden:
1. Lee las velas de 1 s de BTCUSDT y BTC/FDUSD (mayo a octubre de 2026) y el contexto de
   minutos, horas y días (velas de 1 min desde 2023, interés abierto y financiación).
2. Toma un punto de decisión por minuto, calcula los rasgos y, para cada configuración de
   barrera (se ajusta a la volatilidad de la última hora), mira hacia dónde se movió primero.
3. Entrena dos probabilidades en desarrollo: H, que el precio llegue a una barrera en el tiempo
   (movimiento), y D, que si llega sea la de arriba (dirección). Las recalibra en validación.
4. Calcula H, D y la barrera en cada segundo de validación y del tramo final.
5. Simula los tres libros (contado, BTC/FDUSD de creador y futuros) segundo a segundo: entra
   solo si la ganancia esperada después de comisiones supera un margen; elige configuración y
   margen en validación.
6. Mira el tramo final una sola vez: libro elegido, «operar siempre» y 40 libros al azar.
Salidas: datos/banco-rapido.json, modelos/trading-seguido.json
"""
import array
import datetime as dt
import json
import math
import os
import statistics
import sys
import time
from operator import mul

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import datos  # noqa: E402
import probabilidad as pb  # noqa: E402
import rapido as rp  # noqa: E402

CARPETA = os.path.dirname(os.path.abspath(__file__))
UTC = dt.timezone.utc
DIA = 86_400_000


def ms(fecha):
    return int(dt.datetime.fromisoformat(fecha).replace(tzinfo=UTC).timestamp() * 1000)


TRAMOS = {"desarrollo": (ms("2026-05-01"), ms("2026-08-01")),
          "validacion": (ms("2026-08-01"), ms("2026-09-16")),
          "final": (ms("2026-09-16"), ms("2026-10-20"))}
TRAMOS_PRUEBA = {"desarrollo": (ms("2026-08-01"), ms("2026-08-11")),
                 "validacion": (ms("2026-08-11"), ms("2026-08-16")),
                 "final": (ms("2026-08-16"), ms("2026-08-21"))}
# (segundos máximos del ciclo, k desvíos, barrera mínima)
CONFIGS = ((300, 1.0, 0.0010), (900, 1.0, 0.0015), (1800, 1.0, 0.0025), (1800, 1.5, 0.0040))
MARGENES = (0.0, 0.0002, 0.0005)                  # ganancia esperada mínima por ciclo: 0, 2 y 5 pb
SEMILLAS = 40
PASO_ENTRENO = 60                                 # un punto de decisión por minuto para entrenar
NOMBRES = list(rp.RASGOS) + ["ln_barrera"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def alinear(v_a, v_b):
    """Recorta las dos series al tramo común y comprueba que coincidan segundo a segundo."""
    desde = max(v_a.t[0], v_b.t[0])
    hasta = min(v_a.t[-1], v_b.t[-1]) + 1000
    a, b = datos.recortar(v_a, desde, hasta), datos.recortar(v_b, desde, hasta)
    if len(a.t) != len(b.t) or any(a.t[k] != b.t[k] for k in range(0, len(a.t), 997)) or a.t[-1] != b.t[-1]:
        raise ValueError("BTCUSDT y BTCFDUSD no coinciden segundo a segundo")
    return a, b


def estadisticos(X):
    media, desvio = [], []
    for k in range(len(X[0])):
        vals = [x[k] for x in X if x[k] == x[k]]
        m = math.fsum(vals) / len(vals) if vals else 0.0
        s = math.sqrt(math.fsum((v - m) ** 2 for v in vals) / max(len(vals) - 1, 1)) if vals else 1.0
        media.append(m)
        desvio.append(s if s > 1e-12 else 1.0)
    return media, desvio


def z_de(x, media, desvio, r=5.0):
    out = []
    for v, m, s in zip(x, media, desvio):
        if v != v:
            out.append(0.0)
        else:
            q = (v - m) / s
            out.append(r if q > r else (-r if q < -r else q))
    return out


def p_de(modelo, z):
    a, b = modelo.platt
    return pb.sigmoide(a + b * (modelo.beta[0] + sum(map(mul, modelo.beta[1:], z))))


def main():
    prueba = "--prueba" in sys.argv
    tramos = TRAMOS_PRUEBA if prueba else TRAMOS
    inicio = time.time()
    log("Cargando velas de 1 s…")
    v_usdt = datos.cargar_velas("contado-1s-BTCUSDT", "1s")
    v_fd = datos.cargar_velas("contado-1s-BTCFDUSD", "1s")
    log("BTCUSDT 1 s:", json.dumps(v_usdt.calidad, ensure_ascii=False))
    log("BTCFDUSD 1 s:", json.dumps(v_fd.calidad, ensure_ascii=False))
    desde_total = tramos["desarrollo"][0] - 2 * 3_600_000
    hasta_total = tramos["final"][1]
    v_usdt, v_fd = alinear(datos.recortar(v_usdt, desde_total, hasta_total),
                           datos.recortar(v_fd, desde_total, hasta_total))
    log(f"Tramo común: {len(v_usdt.t):,} segundos")
    v1m = datos.cargar_1m("contado-1m")
    ctx = rp.Contexto(datos.recortar(v1m, desde_total - 30 * DIA, hasta_total + DIA),
                      datos.cargar_metricas(), datos.cargar_financiacion(completar=True))
    s = rp.Serie(v_usdt)
    sf = rp.Serie(v_fd, rasgos=False)
    t = s.t
    log(f"Series listas en {time.time() - inicio:.0f} s")

    # ---------------- puntos de entrenamiento, rasgos y hacia dónde se movió primero
    tope = max(c[0] for c in CONFIGS)
    puntos, X = {}, {}
    for nombre, (a, b) in tramos.items():
        i0 = max(s.indice(a), rp.VENTANA_MIN)
        i1 = s.indice(b) - 1
        puntos[nombre] = list(range(i0, i1 - tope, PASO_ENTRENO))      # purga: la etiqueta no cruza de tramo
        X[nombre] = [rp.rasgos_segundo(s, i, ctx.en(t[i] + 1000)) for i in puntos[nombre]]
        log(f"Rasgos {nombre}: {len(puntos[nombre]):,} puntos")

    modelos, medidas = {}, {}
    for cfg in CONFIGS:
        segundos, k, minima = cfg
        XL, R = {}, {}
        for nombre in tramos:
            filas, res = [], []
            for i, x in zip(puntos[nombre], X[nombre]):
                b = rp.barrera_de(x[rp.I_VOL3600], segundos, k, minima)
                filas.append(x + [math.log(b * 100)])
                res.append(rp.primer_toque(s, i + 1, b, segundos))
            XL[nombre], R[nombre] = filas, res
        media, desvio = estadisticos(XL["desarrollo"])
        dev = R["desarrollo"]
        log(f"Config {cfg}: en desarrollo sube primero {sum(1 for r in dev if r > 0) / len(dev) * 100:.1f} %, "
            f"baja primero {sum(1 for r in dev if r < 0) / len(dev) * 100:.1f} %, sin tocar {sum(1 for r in dev if r == 0) / len(dev) * 100:.1f} %")
        # H: movimiento (todas las decisiones); D: dirección (solo las que tocaron una barrera)
        H = pb.Logistica(NOMBRES, l2=10.0)
        H.media, H.desvio = media, desvio
        H.ajustar(XL["desarrollo"], [1 if r != 0 else 0 for r in dev], estandarizar=False)
        H.recalibrar(XL["validacion"], [1 if r != 0 else 0 for r in R["validacion"]])
        D = pb.Logistica(NOMBRES, l2=10.0)
        D.media, D.desvio = media, desvio
        dev_t = [(x, r) for x, r in zip(XL["desarrollo"], dev) if r != 0]
        D.ajustar([x for x, _ in dev_t], [1 if r > 0 else 0 for _, r in dev_t], estandarizar=False)
        val_t = [(x, r) for x, r in zip(XL["validacion"], R["validacion"]) if r != 0]
        d_val_cruda = [D.prob_cruda(x) for x, _ in val_t]
        D.recalibrar([x for x, _ in val_t], [1 if r > 0 else 0 for _, r in val_t])
        fin_t = [(x, r) for x, r in zip(XL["final"], R["final"]) if r != 0]
        y_fin_d = [1 if r > 0 else 0 for _, r in fin_t]
        d_fin = [D.prob(x) for x, _ in fin_t]
        y_fin_h = [1 if r != 0 else 0 for r in R["final"]]
        h_fin = [H.prob(x) for x in XL["final"]]
        sube_fin = sum(y_fin_d) / len(y_fin_d) if y_fin_d else None
        clave = f"{segundos}s|k{k}|min{minima}"
        medidas[clave] = {
            "segundos": segundos, "k": k, "barrera_minima_pct": minima * 100,
            "barrera_mediana_pct_final": round(statistics.median(math.exp(x[-1]) for x in XL["final"]), 4),
            "toca_alguna_final": round(sum(y_fin_h) / len(y_fin_h), 4),
            "movimiento_auc_final": round(pb.auc(h_fin, y_fin_h), 4),
            "direccion_sube_base_final": round(sube_fin, 4) if sube_fin is not None else None,
            "direccion_auc_val": round(pb.auc(d_val_cruda, [1 if r > 0 else 0 for _, r in val_t]), 4) if val_t else None,
            "direccion_auc_final": round(pb.auc(d_fin, y_fin_d), 4) if fin_t else None,
            "direccion_brier_final": round(pb.brier(d_fin, y_fin_d), 5) if fin_t else None,
            "direccion_brier_base": round(sube_fin * (1 - sube_fin), 5) if sube_fin is not None else None,
            "direccion_fiabilidad_final": pb.fiabilidad(d_fin, y_fin_d) if fin_t else [],
            "direccion_max_final": round(max(d_fin), 4) if d_fin else None,
            "direccion_min_final": round(min(d_fin), 4) if d_fin else None,
            "casos_d_mayor_085": sum(1 for p in d_fin if p >= 0.85),
            "platt_d": [round(v, 4) for v in D.platt], "platt_h": [round(v, 4) for v in H.platt],
            "pesos_direccion": D.importancia()[:8], "pesos_movimiento": H.importancia()[:6]}
        modelos[cfg] = (H, D, media, desvio)
        m = medidas[clave]
        log(f"  movimiento AUC final {m['movimiento_auc_final']}; dirección AUC val {m['direccion_auc_val']} "
            f"final {m['direccion_auc_final']}; D entre {m['direccion_min_final']} y {m['direccion_max_final']}; "
            f"casos D≥0,85: {m['casos_d_mayor_085']}")

    # ---------------- H, D y barrera en cada segundo de validación y final
    i_a = s.indice(tramos["validacion"][0])
    i_b = min(s.indice(tramos["final"][1]), s.largo - 1)
    ARR = {cfg: (array.array("d"), array.array("d"), array.array("d")) for cfg in CONFIGS}
    log(f"Probabilidades segundo a segundo: {i_b - i_a:,} segundos…")
    for i in range(i_a, i_b):
        x = rp.rasgos_segundo(s, i, ctx.en(t[i] + 1000))
        for cfg in CONFIGS:
            B, Hs, Ds = ARR[cfg]
            if x is None:
                B.append(math.nan)
                Hs.append(math.nan)
                Ds.append(math.nan)
                continue
            segundos, k, minima = cfg
            H, D, media, desvio = modelos[cfg]
            b = rp.barrera_de(x[rp.I_VOL3600], segundos, k, minima)
            z = z_de(x + [math.log(b * 100)], media, desvio)
            B.append(b)
            Hs.append(p_de(H, z))
            Ds.append(p_de(D, z))
    log(f"Probabilidades listas ({time.time() - inicio:.0f} s)")

    # ---------------- libros en validación: elegir configuración y margen por instrumento
    with open(os.path.join(CARPETA, "config.json"), encoding="utf-8") as f:
        capital = float(json.load(f).get("capital_usdt", 9.7))      # 40.000 COP a la tasa P2P guardada
    log(f"Capital por libro: {capital} USDT")
    gestion = rp.Gestion(capital=capital, tanda=rp.tanda_por_capital(capital))
    resultados = {"validacion": {}, "final": {}}
    elegidos = {}
    dias_val = (tramos["validacion"][1] - tramos["validacion"][0]) / DIA
    dias_fin = (tramos["final"][1] - tramos["final"][0]) / DIA
    v_desde, v_hasta = s.indice(tramos["validacion"][0]), s.indice(tramos["validacion"][1])
    f_desde, f_hasta = s.indice(tramos["final"][0]), min(s.indice(tramos["final"][1]), s.largo - 1)
    for clave_inst, inst in rp.INSTRUMENTOS.items():
        s_ej = sf if clave_inst == "fdusd" else s
        candidatos = []
        for cfg in CONFIGS:
            B, Hs, Ds = ARR[cfg]
            for margen in MARGENES:
                dec = rp.decisor_ev(B, Hs, Ds, i_a, inst, margen)
                lib, pf = rp.simular_libro(s, s_ej, v_desde, v_hasta, dec, inst, gestion, cfg[0])
                r = rp.resumen_libro(lib, pf, dias_val)
                r.update({"config": list(cfg), "margen": margen})
                resultados["validacion"][f"{clave_inst}|{cfg}|{margen}"] = r
                log(f"[val] {clave_inst} {cfg} margen {margen * 1e4:.0f} pb: ciclos {r['ciclos']}, "
                    f"acierto {r.get('acierto_pct')}, retorno {r['retorno_pct']} %")
                candidatos.append((r["retorno_pct"], r["ciclos"], cfg, margen))
        # Válida: al menos 30 ciclos y sin pérdida en validación. Si ninguna lo es, el libro queda
        # marcado «sin ventaja demostrada» y sigue en papel con la mejor de al menos 5 ciclos.
        validas = [c for c in candidatos if c[1] >= 30 and c[0] >= 0]
        if validas:
            r_, n_, cfg, margen = max(validas, key=lambda c: c[0])
            valido = True
        else:
            con_ciclos = [c for c in candidatos if c[1] >= 5] or candidatos
            r_, n_, cfg, margen = max(con_ciclos, key=lambda c: c[0])
            valido = False
        elegidos[clave_inst] = (r_, cfg, margen, valido, n_)
        log(f"Elegido {clave_inst}: {cfg} margen {margen * 1e4:.0f} pb ({n_} ciclos, {r_} % en validación) "
            f"{'VÁLIDO' if valido else 'SIN VENTAJA DEMOSTRADA'}")

    # ---------------- tramo final: se mira una vez
    # Testigo: «seguido sin filtro» en contado con ciclos de hasta 5 minutos: así se vería operar seguido.
    cfg_t = CONFIGS[0]
    B, Hs, Ds = ARR[cfg_t]
    testigo, pft = rp.simular_libro(s, s, f_desde, f_hasta, rp.decisor_ev(B, Hs, Ds, i_a, rp.INSTRUMENTOS["contado"], 0, True),
                                    rp.INSTRUMENTOS["contado"], gestion, cfg_t[0])
    resultados["final"]["testigo_seguido"] = {"instrumento": rp.INSTRUMENTOS["contado"].nombre, "config": list(cfg_t),
                                              "operar_siempre": rp.resumen_libro(testigo, pft, dias_fin)}
    log(f"[final] testigo seguido {cfg_t}: {resultados['final']['testigo_seguido']['operar_siempre']['ciclos']} ciclos, "
        f"{resultados['final']['testigo_seguido']['operar_siempre']['retorno_pct']} %")
    for clave_inst, inst in rp.INSTRUMENTOS.items():
        s_ej = sf if clave_inst == "fdusd" else s
        _, cfg, margen, valido, _ = elegidos[clave_inst]
        B, Hs, Ds = ARR[cfg]
        lib, pf = rp.simular_libro(s, s_ej, f_desde, f_hasta, rp.decisor_ev(B, Hs, Ds, i_a, inst, margen),
                                   inst, gestion, cfg[0])
        r = rp.resumen_libro(lib, pf, dias_fin)
        siempre, pf2 = rp.simular_libro(s, s_ej, f_desde, f_hasta, rp.decisor_ev(B, Hs, Ds, i_a, inst, 0, True),
                                        inst, gestion, cfg[0])
        r_siempre = rp.resumen_libro(siempre, pf2, dias_fin)
        azar = []
        n_azar = r["ciclos"] if r["ciclos"] else r_siempre["ciclos"]
        dur = (r.get("duracion_media_s") or r_siempre.get("duracion_media_s") or cfg[0])
        if n_azar:
            tasa = n_azar / max(f_hasta - f_desde - n_azar * dur, 1)
            for semilla in range(SEMILLAS):
                la, pfa = rp.simular_libro(s, s_ej, f_desde, f_hasta, rp.decisor_azar(semilla, tasa, B, i_a, inst.corto),
                                           inst, gestion, cfg[0])
                azar.append(rp.resumen_libro(la, pfa, dias_fin))
        rets = sorted(a["retorno_pct"] for a in azar)
        resultados["final"][clave_inst] = {
            "instrumento": inst.nombre, "config": list(cfg), "margen": margen, "valido_en_validacion": valido,
            "con_seguridad": r,
            "operar_siempre": r_siempre,
            "azar": {"libros": len(azar), "retorno_mediana": statistics.median(rets) if rets else None,
                     "retorno_p10": rets[int(len(rets) * 0.1)] if rets else None,
                     "retorno_p90": rets[int(len(rets) * 0.9)] if rets else None,
                     "ciclos_mediana": statistics.median(a["ciclos"] for a in azar) if azar else None,
                     "percentil_del_sistema": round(sum(1 for x in rets if x < r["retorno_pct"]) / len(rets) * 100, 1)
                     if rets and r["ciclos"] else None}}
        log(f"[final] {clave_inst} {cfg} margen {margen * 1e4:.0f} pb: con seguridad {r['ciclos']} ciclos, "
            f"{r['retorno_pct']} %; operar siempre {r_siempre['ciclos']} ciclos, {r_siempre['retorno_pct']} %; "
            f"azar mediana {resultados['final'][clave_inst]['azar']['retorno_mediana']}")

    # ---------------- guardar
    os.makedirs(os.path.join(CARPETA, "modelos"), exist_ok=True)
    os.makedirs(os.path.join(CARPETA, "datos"), exist_ok=True)
    sufijo = "-prueba" if prueba else ""
    generado = dt.datetime.now(rp.BOGOTA).isoformat(timespec="seconds")
    with open(os.path.join(CARPETA, "modelos", f"trading-seguido{sufijo}.json"), "w", encoding="utf-8") as f:
        json.dump({"generado": generado, "tramos": {k: [v[0], v[1]] for k, v in tramos.items()},
                   "rasgos": NOMBRES,
                   "instrumentos": {k: {"config": list(e[1]), "margen": e[2], "valido": e[3],
                                        "validacion": {"retorno_pct": e[0], "ciclos": e[4]}}
                                    for k, e in elegidos.items()},
                   "testigo": {"instrumento": "contado", "config": list(CONFIGS[0])},
                   "modelos": {f"{c[0]}|{c[1]}|{c[2]}": {"config": list(c), "movimiento": H.a_dict(),
                                                         "direccion": D.a_dict()}
                               for c, (H, D, _, _) in modelos.items()}},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(CARPETA, "datos", f"banco-rapido{sufijo}.json"), "w", encoding="utf-8") as f:
        json.dump({"generado": generado, "prueba": prueba,
                   "calidad": {"BTCUSDT_1s": v_usdt.calidad, "BTCFDUSD_1s": v_fd.calidad},
                   "probabilidad": medidas, "libros": resultados}, f, ensure_ascii=False, indent=1, default=str)
    log(f"Listo en {time.time() - inicio:.0f} s.")


if __name__ == "__main__":
    main()
