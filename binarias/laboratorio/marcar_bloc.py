"""Marca un paso del laboratorio en el bloc de binarias (11/11/2026): cambia su ⬜ por ✅ con el texto dado y la hora de
Colombia, actualiza SIGUIENTE PASO del AL FRENTE más reciente y agrega una línea a la BITÁCORA.
Uso: python -I marcar_bloc.py <número> "<texto del paso hecho>" "<siguiente paso>" "<línea de bitácora>" """
import datetime as dt
import re
import sys

BLOC = r"C:\Users\ni109\Desktop\BLOC BINARIAS - TODO EN UNO.txt"
COL = dt.timezone(dt.timedelta(hours=-5))


def main():
    numero, hecho, siguiente, bitacora = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    ahora = dt.datetime.now(COL)
    texto = open(BLOC, encoding="utf-8").read()
    inicio = texto.find("AL FRENTE (")
    fin = texto.find("\nAL FRENTE (", inicio + 1)
    bloque = texto[inicio:fin]
    patron = re.compile(r"^(⬜|✅) " + re.escape(numero) + r"\. .*$", re.MULTILINE)
    if not patron.search(bloque):
        raise SystemExit(f"no encontré el paso {numero} en el AL FRENTE más reciente")
    bloque = patron.sub(lambda m: f"✅ {numero}. {hecho} ({ahora:%H:%M}).", bloque, count=1)
    if siguiente:
        bloque = re.sub(r"^SIGUIENTE PASO:.*$", lambda m: "SIGUIENTE PASO: " + siguiente, bloque, count=1, flags=re.MULTILINE)
    texto = texto[:inicio] + bloque + texto[fin:]
    if bitacora:
        texto = texto.rstrip("\n") + f"\n- {ahora:%d/%m/%Y %H:%M}. {bitacora}\n"
    with open(BLOC, "w", encoding="utf-8", newline="") as f:
        f.write(texto)
    print(f"paso {numero} marcado a las {ahora:%H:%M}")


if __name__ == "__main__":
    main()
