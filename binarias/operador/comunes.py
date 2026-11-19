"""Utilidades que comparten los módulos del operador (16/11/2026): hora de Colombia, números a la colombiana y archivos."""
import datetime as dt
import json
import os

COL = dt.timezone(dt.timedelta(hours=-5))


def dia(t):
    """Día de Colombia de la hora t, como AAAAMMDD."""
    return dt.datetime.fromtimestamp(t, COL).strftime("%Y%m%d")


def hora(t, fmt="%d/%m %H:%M"):
    return dt.datetime.fromtimestamp(t, COL).strftime(fmt)


def num(x, d=2):
    """Número a la colombiana: coma decimal y punto de miles."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x, d=1):
    return num(100 * x, d) + " %"


def con_signo(x, d=2):
    return ("+" if x >= 0 else "−") + num(abs(x), d)


def sentido(lado):
    return "SUBE" if lado > 0 else "BAJA"


def leer_json(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def escribir_json(ruta, dato):
    """Escribe entero o no escribe: primero a un archivo aparte y después lo cambia de nombre."""
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dato, f, ensure_ascii=False)
    os.replace(ruta + ".tmp", ruta)


def temperatura():
    """Temperatura del procesador de la caja en °C; None donde no se pueda leer (el PC)."""
    for zona in ("/sys/class/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone1/temp"):
        try:
            with open(zona) as f:
                v = float(f.read().strip())
            return v / 1000 if v > 1000 else v
        except (OSError, ValueError):
            continue
    return None
