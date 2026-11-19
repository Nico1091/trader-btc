"""Prueba del vigía de 15 min sin mandar nada a Telegram: avisos simulados y velas reales. Uso: python -I prueba_quince.py"""
import os
import sys
import tempfile

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dispositivos")
sys.path.insert(0, D)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import quince as Q  # noqa: E402
import semaforo as S  # noqa: E402

tmp = tempfile.mkdtemp()
Q.ESTADO, Q.REGISTRO, Q.FOTO = (os.path.join(tmp, x) for x in ("q.json", "q.log", "f.png"))
sal = []
S.avisar = lambda t: (sal.append(("texto", t)), True)[1]
S.avisar_archivo = lambda r, t, m, c, tc=None: (sal.append((m, os.path.basename(r), t)), True)[1]
fallos = 0


def ver(n, c):
    global fallos
    print(("bien " if c else "FALLA") + " · " + n)
    fallos += 0 if c else 1


def serie(k, n=25):
    return {"ops": [{"t": i, "dir": 1, "res": 1 if i < k else 0} for i in range(n)]}


ver("19 de 25 son 76 %", Q.porcentaje(serie(19))[0] == 76)
e = serie(17)
e["nivel"] = 0
Q.alertas(e)
ver("subir a 68 %: voz de aproximando", sal and sal[-1][0] == "sendVoice" and sal[-1][1] == "aproximando.mp3")
sal.clear()
Q.alertas(e)
ver("mismo nivel: no repite", not sal)
e = serie(19)
e["nivel"] = 1
Q.alertas(e)
ver("llegar a 76 %: voz de listo", sal and sal[-1][1] == "listo.mp3")
e = serie(16)
e["nivel"] = 2
sal.clear()
Q.alertas(e)
ver("bajar del 75 %: voz de no opere", sal and sal[-1][1] == "bajo.mp3")
e = serie(19)
sal.clear()
Q.alertas(e)
ver("al encender ya arriba (19 de 25): avisa YA LLEGÓ", bool(sal) and sal[-1][1] == "listo.mp3" and "19 de 25" in sal[-1][2] and e["nivel"] == 2)
sal.clear()
Q.alertas(e)
ver("sigue arriba: no repite en cada vuelta", not sal)
for k, archivo in ((22, "listo.mp3"), (18, "aproximando.mp3"), (10, None)):
    e = serie(k)
    sal.clear()
    Q.alertas(e)
    ver(f"al encender con {k} de 25: {archivo or 'callado'}", (bool(sal) and sal[-1][1] == archivo and f"{k} de 25" in sal[-1][2]) if archivo else not sal)
e = {"ops": [{"t": i, "dir": 1, "res": 0 if i < 20 else 1} for i in range(25)]}
ver("racha: 5 aciertos, los 5 seguidos al final", Q.aciertos(e) == (5, 5))
print("velas y líneas reales…")
e = {"ops": []}
n = Q.sembrar(e)
print(f"sembradas {n}; aciertos {Q.porcentaje(e)}")
v, s5 = Q.lineas()
ver("150 velas y cinco líneas", len(v) == 150 and s5)
png = Q.graficas.grafica_con_franja(v, s5, "RECHAZO EN EL PISO 80411", 2)
ver("foto con franja", png[:4] == b"\x89PNG" and len(png) > 1000)
r = list(v)
ultima = r[-1]
piso = s5["piso"].en(len(v) - 1)
r[-1] = (ultima[0], piso + 50, piso + 60, piso - 10, piso + 40)
ver("vela que toca el piso y cierra arriba: rechazo", (Q.reaccion(r, s5) or ("",))[0].startswith("RECHAZO EN EL PISO"))
r[-1] = (ultima[0], piso + 10, piso + 20, piso - 80, piso - 50)
ver("cierre debajo del piso: ruptura", (Q.reaccion(r, s5) or ("",))[0].startswith("RUPTURA DEL PISO"))
print("FALLOS:", fallos)
sys.exit(1 if fallos else 0)
