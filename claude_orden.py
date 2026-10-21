"""Orden de Claude Code al agente. La escribo yo en cada turno de decisión (sin API: decido en la
sesión de Claude Code, como pidió Nicolás el 20/10); el agente la lee en el segundo siguiente.

Uso:  python -I claude_orden.py comprar --objetivo 0.25 --stop 0.20 --minutos 20 --razon "..."
      python -I claude_orden.py vender  --objetivo 0.25 --stop 0.20 --minutos 20 --razon "..."
      python -I claude_orden.py esperar --razon "..."
      python -I claude_orden.py cerrar  --razon "..."
Porcentajes en %: 0.25 = 0,25 %. El agente vuelve a validar y anota todo en diario/.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente import RUTA_ORDEN, validar_orden  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Orden de Claude Code al agente de trading (papel).")
    p.add_argument("accion", choices=("comprar", "vender", "esperar", "cerrar"))
    p.add_argument("--objetivo", type=float, help="objetivo en %% (0.25 = 0,25 %%)")
    p.add_argument("--stop", type=float, help="stop en %%")
    p.add_argument("--minutos", type=float, help="tiempo máximo del ciclo")
    p.add_argument("--razon", default="", help="por qué, en una línea")
    a = p.parse_args()
    orden = {"id": f"cc-{int(time.time() * 1000)}", "accion": a.accion, "creada": time.time(), "razon": a.razon[:300]}
    if a.accion in ("comprar", "vender"):
        orden.update({"objetivo_pct": a.objetivo, "stop_pct": a.stop, "minutos": a.minutos})
    problema = validar_orden(orden, time.time())
    if problema:
        print("Orden NO escrita:", problema)
        return 1
    temporal = RUTA_ORDEN + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(orden, f, ensure_ascii=False)
    os.replace(temporal, RUTA_ORDEN)
    print("Orden escrita:", json.dumps(orden, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
