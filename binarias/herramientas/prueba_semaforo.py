"""Prueba en seco del semáforo, de punta a punta, en una carpeta aislada y sin mandar nada a Telegram (04/11/2026).

Sale del arnés de la noche del 04/11 (prueba_v32.py y prueba_v33b.py, que vivían en una carpeta temporal). Copia los .py
de dispositivos/ a herramientas/prueba_semaforo_tmp/, parte de un semaforo.json real (el de la caja o el del teléfono),
fuerza una señal BAJA en la decisión anterior con las velas reales de Binance y muestra lo que se habría mandado.
Opciones:
  --real   crea REAL_AUTORIZADO en la carpeta de prueba (para ver el camino del dinero real)
  --76     siembra 30 aciertos de papel antes de la señal (para que se cumpla su 76 %)
  --oi     simula interés abierto que no sube (para que el SÍ no dependa del dato del momento)
Uso: python -I prueba_semaforo.py RUTA_A_SEMAFORO.json [--real] [--76] [--oi]
"""
import datetime as dt
import glob
import json
import os
import shutil
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
DISP = os.path.join(os.path.dirname(AQUI), "dispositivos")
CAJA = os.path.join(AQUI, "prueba_semaforo_tmp")
args = sys.argv[1:]
if not args or not os.path.exists(args[0]):
    print(__doc__)
    sys.exit(1)
shutil.rmtree(CAJA, ignore_errors=True)
os.makedirs(CAJA)
for f in glob.glob(os.path.join(DISP, "*.py")):
    shutil.copy(f, CAJA)
COL = dt.timezone(dt.timedelta(hours=-5))
t_dec = int(time.time() // 600 * 600) - 600          # la decisión anterior, con sus velas ya publicadas
falso_ahora = t_dec + 4
hoy = dt.datetime.fromtimestamp(falso_ahora, COL).strftime("%Y-%m-%d")
e = json.load(open(args[0], encoding="utf-8"))
e["apuestas"] = [a for a in e["apuestas"] if a["t"] < t_dec - 1800 - 600 * 31]
if "--76" in args:
    for k in range(30, 0, -1):
        e["apuestas"].append({"t": t_dec - 1800 - 600 * k, "dir": 1, "entrada": 1.0, "salida": 2.0, "res": 1, "semilla": True})
e["apuestas"].append({"t": t_dec - 1800, "dir": 1, "entrada": 1.0, "salida": 2.0, "res": 1, "semilla": True})  # acierto de hoy
e["apuestas"].append({"t": t_dec - 1200, "dir": 1, "aviso": 0, "entrada": None, "salida": None, "res": None, "si": True,
                      "real": False, "neto_previo": 0.85, "doi": -0.0003, "filtro_oi": True})   # SÍ abierto que debe cerrar
e["hoy"] = {"dia": hoy, "perdio": False}
e.pop("resumen_enviado", None)
json.dump(e, open(os.path.join(CAJA, "semaforo.json"), "w", encoding="utf-8"))
if "--real" in args:
    open(os.path.join(CAJA, "REAL_AUTORIZADO"), "w").close()

sys.path.insert(0, CAJA)
import avisos  # noqa: E402
import semaforo  # noqa: E402

envios = []


def falso_enviar(texto):
    envios.append(("texto", texto))
    return True


def falso_archivo(ruta, texto="", metodo="sendDocument", campo="document", chat=None):
    destino = os.path.join(CAJA, f"enviado_{len(envios)}_{os.path.basename(ruta)}")
    shutil.copy(ruta, destino)
    envios.append((metodo, destino, texto, chat))
    return True


avisos.enviar = falso_enviar
avisos.enviar_archivo = falso_archivo
avisos.canal = lambda: None


class Reloj:
    def time(self):
        return falso_ahora

    def sleep(self, s):
        open(os.path.join(CAJA, "PARAR"), "w").close()


semaforo.time = Reloj()
semaforo.sembrar = lambda est: 0          # sin rehacer 9 días de papel en la prueba
semaforo.senal = lambda v1, td: -1         # señal forzada: BAJA
if "--oi" in args:
    semaforo.cambio_interes = lambda td: -0.0005
semaforo.main()
for x in envios:
    print("·", x[0], "|", (x[2] if len(x) > 2 else x[1])[:600].replace("\n", " ⏎ "))
    if len(x) > 2:
        print("   archivo:", x[1])
print("registro del semáforo:")
print(open(os.path.join(CAJA, "semaforo.log"), encoding="utf-8").read()[-700:])
