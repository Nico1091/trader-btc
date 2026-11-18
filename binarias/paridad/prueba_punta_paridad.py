# -*- coding: utf-8 -*-
"""Prueba de punta a punta de la rutina aprobadora con el formato de la paridad (18/11/2026, tarde).
El teléfono, como la app Binarias, dispara la rutina con UN punto de prueba que trae lo nuevo (cuenta a mano, y del operador
el precio real de cada lado, lo que paga por USDT, el equilibrio y hasta cuánto se compra), con los precios de las fotos de
las 15:18 (SUBE a 0,46, BAJA a 0,58). Lee la decisión en GitHub con la misma función del nodo. No pasa por puntos.jsonl ni
por decisiones.jsonl: la decisión no puede abrir ninguna compra.
Uso en el teléfono (como la app): python3 -I prueba_punta_paridad.py   (con HOME en la casa de la app)"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "nodo"))
import nodo as N  # noqa: E402

c = N.config()
ahora = time.time()
ident = "prueba-paridad-" + time.strftime("%H%M%S", time.gmtime(ahora + N.COL))
W = 15
ventana = (int(ahora) // (W * 60) + 1) * W * 60
vector = {"m": 1, "serie": "papel", "hora": ahora, "resta_s": 840.0, "z": 0.02, "decide": 0, "motivo": "prueba",
          "lados": {"1": {"papel": "ganador", "p": 0.47, "p_prud": 0.45, "q": 0.46, "G_prud": -0.04, "limite": 0.41},
                    "-1": {"papel": "perdedor", "p": 0.53, "p_prud": 0.51, "q": 0.58, "G_prud": -0.14, "limite": 0.46}}}
entradas = [{"dir": 1, "q": 0.5, "g": 1 if i < 19 else -1} for i in range(25)]
punto = dict({"fuente": "centro", "estrategia": "E3", "nombre": N.NOMBRES["E3"], "equipo": "telefono", "alto": True,
              "racha": 2, "fondo": 57.0, "vivo": [12, 18], "minuto": 0, "alineado": True, "t": ahora,
              "aciertos_propios": 19, "de_propios": 25}, **N.cuenta(entradas))
paq = N.paquete((W, ventana, 1), [punto], [], vector)
paq["prueba"] = "PRUEBA DE PUNTA A PUNTA del 18/11/2026 (paridad): el nodo no la registra y no se compra nada"
ok, enlace, error = N.disparar_rutina(c, [{"id": ident, "paquete": paq}])
print(json.dumps({"id": ident, "disparo": ok, "sesion_o_motivo": enlace, "error": error}, ensure_ascii=False), flush=True)
d = None
if ok:
    t0 = time.time()
    while time.time() - t0 < 240:
        d = N.decision_de_rutina(c, ident)
        if d:
            break
        time.sleep(3)
    print(json.dumps({"segundos": round(time.time() - t0, 1), "decision": d}, ensure_ascii=False))
print("paquete enviado (lado SUBE):", json.dumps(paq["operador"]["lados"]["SUBE"], ensure_ascii=False))
