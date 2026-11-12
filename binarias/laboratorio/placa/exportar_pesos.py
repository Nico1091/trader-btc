"""Arma pesos.json para la ESP32 a partir de las redes vigentes del laboratorio (11/11/2026): a cada plazo, el modelo que el
laboratorio eligió en «elige» (a 10 min la red, a 15 min la neurona), con su media y su desviación. Si existe la tabla de la
pérdida (datos/perdida.json), va también, para que la placa diga el precio máximo de cada situación.
Uso: python -I exportar_pesos.py [salida.json]"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(AQUI)
sys.path.insert(0, LAB)


def redondear(x, cifras=8):
    if isinstance(x, list):
        return [redondear(v, cifras) for v in x]
    return float(f"{x:.{cifras}g}")


def pesos_placa(motor):
    d = {"t": int(motor.t)}
    for p in (10, 15):
        if motor.usa[p] == "red":
            m = motor.red[p]
            d[str(p)] = {"tipo": "red", "W": [redondear(w.tolist()) for w in m.W], "b": [redondear(b.tolist()) for b in m.b],
                         "mu": redondear(m.mu.tolist()), "de": redondear(m.de.tolist())}
        else:
            n = motor.neu[p]
            d[str(p)] = {"tipo": "neurona", "w": redondear(n.w.tolist()), "mu": redondear(n.mu.tolist()),
                         "de": redondear(n.de.tolist())}
    ruta = os.path.join(LAB, "datos", "perdida.json")
    if os.path.exists(ruta):
        d["perdida"] = json.load(open(ruta, encoding="utf-8"))
    return d


def main():
    import emulador as EM
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "pesos.json")
    d = pesos_placa(EM.MotorRed())
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(d, f, separators=(",", ":"))
    print(f"{salida}: {os.path.getsize(salida)} bytes; modelos " + ", ".join(f"{p} min {d[str(p)]['tipo']}" for p in (10, 15)))


if __name__ == "__main__":
    main()
