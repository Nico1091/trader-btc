"""C5 (28/10/2026): la preventiva de Nicolás sobre el método de 迪亚马特: «ves que sube y apuestas para arriba».

Pedido: «crea una alerta para cuando esté subiendo mucho… o mejor aún, como preventiva: ves que sube y apuestas para arriba».
Sobre el corto de C4 (especificación principal: subida ≥ 30 % en 24 h, con giro, 5×, objetivo −5 %, 96 h, margen cruzado):
si antes del objetivo el precio sube F % sobre la entrada, se cierra el corto (tomador + deslizamiento) y se abre un LARGO a 5×
a ese mismo precio. El largo sale cuando el precio cae T % desde el máximo alcanzado después del giro, o a las 48 h.
Reglas fijadas antes de mirar: F = 10, 20 o 30 %; T = 10 o 20 %. Trato conservador de la vela del giro: si en ella el mínimo
toca el seguimiento, el largo sale ahí; en las velas siguientes, el seguimiento usa el máximo de las velas anteriores.
Financiación incluida en las dos patas. «Sin preventiva» debe dar lo mismo que la especificación principal de C4 (control).
Usa las velas que C4 dejó en caché (correr C4 antes).
Uso: python -I c5_preventiva_al_alza.py > c5_preventiva_al_alza.txt"""
import importlib.util
import os
import sys
import time

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
_esp = importlib.util.spec_from_file_location("c4", os.path.join(AQUI, "c4_vender_subidas.py"))
c4 = importlib.util.module_from_spec(_esp)
_esp.loader.exec_module(c4)
HORA, LEV = c4.HORA, c4.LEV
MAX_LARGO = 48


def cargar():
    datos = {}
    for nombre in sorted(os.listdir(c4.VELAS)):
        rf = os.path.join(c4.FIN, nombre)
        if not nombre.endswith(".npz") or not os.path.exists(rf):
            continue
        zv, zf = np.load(os.path.join(c4.VELAS, nombre)), np.load(rf)
        if len(zv["t"]) >= 48:
            datos[nombre[:-4]] = (c4.preparar((zv["t"], zv["v"])), (zf["t"], zf["v"]))
    return datos


def cobros(ft, fv, a, b):
    return float(fv[(ft > a) & (ft <= b)].sum())


def operar(sim, d, f, F, T):
    """Cortos de C4 con la preventiva; devuelve cortos y largos sueltos, en el formato de c4.copia."""
    o, h, l, c, n, t0 = d["o"], d["h"], d["l"], d["c"], d["n"], d["t0"]
    ft, fv = (f[0], f[1][:, 0]) if len(f[0]) else (np.zeros(0, np.int64), np.zeros(0))
    res, desde = [], 0
    for i in c4.senales(d, 0.30, True):
        if i < desde:
            continue
        e = float(o[i + 1])
        fin = min(i + c4.MAXH, n - 1)
        sh, sl = h[i + 1:fin + 1], l[i + 1:fin + 1]
        hueco = np.flatnonzero(np.isnan(sh))
        k_fin = int(hueco[0]) - 1 if len(hueco) else len(sh) - 1
        tp = np.flatnonzero(sl[:k_fin + 1] <= e * (1 - c4.OBJ))
        st = np.flatnonzero(sh[:k_fin + 1] >= e * (1 + F)) if F else []
        k_tp = int(tp[0]) if len(tp) else None
        k_st = int(st[0]) if len(st) else None
        a = t0 + (i + 1) * HORA
        if k_st is not None and (k_tp is None or k_st <= k_tp):  # en la misma vela, lo peor: el giro
            k = k_st
            b = t0 + (i + 1 + k) * HORA
            r = (-F - c4.COM_IN - c4.COM_MK) * 100 * LEV + cobros(ft, fv, a, b) * 100 * LEV
            res.append({"s": sim, "a": a, "b": b, "r": r, "contra": np.maximum(0.0, (sh[:k + 1] / e - 1) * 100 * LEV)})
            el, j0 = e * (1 + F), i + 1 + k
            jfin = min(j0 + MAX_LARGO, n - 1)
            mx, px, contra, j = el, None, [], j0
            for j in range(j0, jfin + 1):
                if np.isnan(h[j]):
                    j -= 1
                    px = float(c[j])
                    break
                nivel = mx * (1 - T)
                contra.append(max(0.0, (1 - l[j] / el) * 100 * LEV))
                if l[j] <= nivel:
                    px = float(min(nivel, o[j])) if j > j0 else nivel
                    break
                mx = max(mx, float(h[j]))
            if px is None:
                j = jfin
                px = float(c[j])
            bl = t0 + j * HORA
            rl = ((px / el - 1) - c4.COM_IN - c4.COM_MK) * 100 * LEV - cobros(ft, fv, b, bl) * 100 * LEV
            res.append({"s": sim, "a": b + 1, "b": bl, "r": rl, "contra": np.array(contra[1:] or [0.0]), "largo": True})
            desde = j + 1
            continue
        if k_tp is not None:
            k, r = k_tp, (c4.OBJ - c4.COM_IN - c4.COM_TP) * 100 * LEV
        else:
            k = k_fin
            r = ((1 - c[i + 1 + k] / e) - c4.COM_IN - c4.COM_MK) * 100 * LEV
        b = t0 + (i + 1 + k) * HORA
        r += cobros(ft, fv, a, b) * 100 * LEV
        res.append({"s": sim, "a": a, "b": b, "r": r, "contra": np.maximum(0.0, (sh[:k + 1] / e - 1) * 100 * LEV)})
        desde = i + 1 + k + 1
    return res


def main():
    datos = cargar()
    ultimo = max(d["t0"] + (d["n"] - 1) * HORA for d, f in datos.values())
    dias = (ultimo - c4.INICIO) / 86400000
    print(f"C5 · preventiva al alza sobre el corto de 迪亚马特 · {len(datos)} monedas de la caché de C4 · "
          f"hasta {time.strftime('%Y-%m-%d', time.gmtime(ultimo / 1000))}")
    for F, T in [(0, 0)] + [(F, T) for F in (0.10, 0.20, 0.30) for T in (0.10, 0.20)]:
        ops = [x for s, (d, f) in datos.items() for x in operar(s, d, f, F, T)]
        largos = [x for x in ops if x.get("largo")]
        cortos = [x for x in ops if not x.get("largo")]
        nombre = "SIN preventiva (control: igual a la especificación principal de C4)" if not F else \
            f"preventiva: si sube +{F * 100:.0f} %, corta y apuesta al alza; el largo sale al caer {T * 100:.0f} % desde su máximo"
        print(f"\n== {nombre} ==")
        print(f"   todo junto: {c4.linea(ops, False, dias)}")
        if largos:
            rl = np.array([x["r"] for x in largos])
            rc = np.array([x["r"] for x in cortos])
            print(f"   giros: {len(largos)} · los largos aciertan {(rl > 0).mean() * 100:.0f} % con media {rl.mean():+.1f} % del margen "
                  f"(mejor {rl.max():+.0f} %, peor {rl.min():+.0f} %) · los cortos aciertan {(rc > 0).mean() * 100:.1f} %")


if __name__ == "__main__":
    main()
