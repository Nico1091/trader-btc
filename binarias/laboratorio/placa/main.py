# Arranque de la ESP32-S3 (11/11/2026): la placa queda dedicada a las binarias en papel (binarias_placa.py).
# El acortador de noticias sigue guardado en la placa (acortador.py, acortar.bin); para volver a él basta con cambiar
# este archivo por:  import acortador; acortador.servir()
# Si algo falla al arrancar, el error queda en fallo.txt y la placa se reinicia sola a los 15 s: sigue aunque la
# desconecten y la vuelvan a conectar.
import time

import machine

try:
    import binarias_placa
    binarias_placa.correr()
except Exception as e:
    import sys
    try:
        with open("fallo.txt", "w") as f:
            sys.print_exception(e, f)
    except Exception:
        pass
    time.sleep(15)
    machine.reset()
