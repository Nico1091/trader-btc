#!/usr/bin/env python3
"""Pruebas del auditor de reglas de dinero (propuesta del 19/11/2026).

Cada caso inyecta una infracción concreta en un libro sintético y exige que el auditor marque
exactamente esa regla (ni más ni menos). Los datos son inventados: no hay importes ni cuentas reales.

Uso:
    python3 prueba_auditor.py              # corre las pruebas
    python3 prueba_auditor.py --generar    # escribe los dos ejemplos SINTÉTICOS junto a este archivo
"""
import datetime as dt
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import auditor_reglas_dinero as A  # noqa: E402


def epoca(y, mo, d, hh, mm):
    return dt.datetime(y, mo, d, hh, mm, tzinfo=A.COL).timestamp()


T0 = int(epoca(2026, 11, 18, 10, 0))   # 10:00 de Colombia: inicio de un cuarto de hora (múltiplo de 900 s)


def orden(i, t, usdt=2.0, saldo=46.0, W=15, precio=0.5, res=None, comprado=None, estado="ENVIADA",
          origen=None, visto=None, cot=None, espera=60, res_en=1000, con_cobro=True, final=True):
    """Una orden como la escribe el ejecutor: cuentas calculadas igual que en el código (comisión 2 %)."""
    if estado == "RECHAZADA":
        comprado, final = 0.0, True
    elif comprado is None:
        comprado = usdt
    he = t + espera
    contratos = round(comprado * 0.98 / precio, 4) if comprado > 0 else 0.0
    o = {"id": f"{W}-{t}-{i}", "dia": A.dia_de(he), "W": W, "t": t, "usdt": usdt, "saldo": saldo, "comision": 0.02,
         "cotizado": precio if cot is None else cot, "precio": precio if comprado > 0 else None, "estado": estado,
         "final": final, "orden": f"ord-{i}", "comprado": comprado, "contratos": contratos, "res": None,
         "pago": None, "neto": None, "hora": he - 1, "hora_envio": he, "saldo_inicial_dia": saldo}
    if origen:
        o.update(origen=origen, visto=precio if visto is None else visto)
    if res is not None:
        pago = {1: contratos, 2: round(contratos / 2, 4), 0: 0.0}[res]
        o.update(res=res, pago=round(pago, 4), neto=round(pago - comprado, 4), hora_res=he + res_en)
        if pago > 0 and con_cobro:
            o["cobro"] = {"estado": "COBRADO", "hora": he + res_en + 60}
    return o


def libro(ordenes, saldo_inicial=46.0):
    dias = {}
    for o in ordenes:
        dias.setdefault(o["dia"], {"saldo_inicial": saldo_inicial, "fijo": True})
    return {"ordenes": ordenes, "dias": dias}


def libro_limpio():
    """Un día de cuatro órdenes: pérdida, acierto, pérdida y una abierta. Cumple todas las reglas."""
    return [
        orden(1, T0, res=0),
        orden(2, T0 + 900, res=1, precio=0.5),
        orden(3, T0 + 1800, res=0),
        orden(4, T0 + 2700),                       # comprada, todavía sin resultado
    ]


AHORA_LIMPIO = T0 + 5000


def caso_limpio():
    return libro(libro_limpio()), AHORA_LIMPIO, set(), set()


def casos():
    C = []

    def add(nombre, datos, ahora, inf, avi=()):
        C.append((nombre, datos, ahora, set(inf), set(avi)))

    add("libro limpio cumple todo", libro(libro_limpio()), AHORA_LIMPIO, set())
    add("R1 importe de 1,50 USDT", libro([orden(1, T0, usdt=1.5, res=0)]), T0 + 5000, {"R1"})
    add("R2 importe de 2 USDT con saldo de 10", libro([orden(1, T0, saldo=10, res=0)]), T0 + 5000, {"R2"})
    add("R3 orden de la IA de 2,5 USDT",
        libro([orden(1, T0, usdt=2.5, origen="ia", visto=0.5, res=0)]), T0 + 5000, {"R3"})
    add("R4 vigésima primera orden del día",
        libro([orden(i, T0 + 900 * i, saldo=1000) for i in range(1, 22)], saldo_inicial=1000),
        T0 + 900 * 30, {"R4"})
    add("R5 segunda orden en el mismo mercado",
        libro([orden(1, T0, res=1), orden(2, T0, res=0)]), T0 + 5000, {"R5"})
    add("rechazada no cuenta para R5 (la siguiente sí es válida)",
        libro([orden(1, T0, estado="RECHAZADA"), orden(2, T0, res=1)]), T0 + 5000, set())
    add("R6 freno: pérdida abierta más nueva orden pasa el 16 % de 20",
        libro([orden(1, T0, saldo=20, res=0), orden(2, T0 + 900, saldo=20)], saldo_inicial=20),
        T0 + 5000, {"R6"})
    add("R7 precio cotizado de 0,95", libro([orden(1, T0, precio=0.95, res=0)]), T0 + 5000, {"R7"})
    add("R8 IA paga 0,06 por encima de lo que vio",
        libro([orden(1, T0, precio=0.56, visto=0.50, origen="ia", res=0)]), T0 + 5000, {"R8"})
    o = orden(1, T0, res=1)
    o["neto"] = 5.0
    add("R9 neto que no cuadra", libro([o]), T0 + 5000, {"R9"})
    o = orden(1, T0, res=1)
    o["contratos"], o["pago"], o["neto"] = 6.0, 6.0, 4.0
    add("R9 contratos lejos del precio", libro([o]), T0 + 5000, {"R9"})
    o = orden(1, T0, res=1)
    del o["cobro"]
    add("R10 pago sin registro de cobro", libro([o]), T0 + 5000, {"R10"})
    o = orden(1, T0, res=1)
    o["cobro"] = {"estado": "SIN COBRAR", "motivo": "prueba"}
    add("R10 pago sin cobrar (solo aviso)", libro([o]), T0 + 5000, set(), {"R10"})
    o = orden(1, T0, comprado=0.0, estado="POR ENVIAR", final=False)
    add("R11 orden por enviar sin aclarar (solo aviso)", libro([o]), T0 + 5000, set(), {"R11"})
    o = orden(1, T0, final=False)
    add("R11 orden sin cierre a las 24 h (solo aviso)", libro([o]), T0 + 200000, set(), {"R11"})
    o2 = orden(2, T0 + 900)
    o2["id"] = orden(1, T0)["id"]
    add("R12 id repetido", libro([orden(1, T0), o2]), T0 + 5000, {"R12"})
    add("R12 mercado de 7 minutos", libro([orden(1, T0, W=7, res=0)]), T0 + 5000, {"R12"})
    o = orden(1, T0, res=0)
    o["dia"] = "20991231"
    add("R12 día que no coincide con la hora", libro([o]), T0 + 5000, {"R12"})
    return C


def pasar(datos, ahora):
    a = A.Auditoria(datos, ahora)
    a.revisar()
    return a


def correr_pruebas():
    fallos = 0
    total = 0
    for nombre, datos, ahora, esp_inf, esp_avi in casos():
        total += 1
        a = pasar(datos, ahora)
        inf = {r for r, v in a.inf.items() if v}
        avi = {r for r, v in a.avi.items() if v}
        ok = inf == esp_inf and avi == esp_avi
        fallos += not ok
        marca = "bien" if ok else "MAL"
        print(f"[{marca}] {nombre}")
        if not ok:
            print(f"        esperado infracciones {sorted(esp_inf)} avisos {sorted(esp_avi)}")
            print(f"        obtenido   infracciones {sorted(inf)} avisos {sorted(avi)}")
    # libro limpio: además, el resumen tiene que salir como se calcula a mano
    datos = libro(libro_limpio())
    a = pasar(datos, AHORA_LIMPIO)
    r = a.resumen()
    total += 1
    cuadra = (r["ordenes"] == 4 and r["compradas"] == 4 and abs(r["comprado"] - 8.0) < 1e-9 and r["aciertos"] == 1
              and r["fallos"] == 2 and r["abiertas"] == 1 and abs(r["neto"] - (-2 - 2 + 1.92)) < 1e-6
              and abs(r["cobrado"] - 3.92) < 1e-6)
    fallos += not cuadra
    print(f"[{'bien' if cuadra else 'MAL'}] resumen del libro limpio: {r}")
    print(f"\n{total - fallos} de {total} pruebas bien" + ("" if not fallos else f"; {fallos} MAL"))
    return fallos


def correr_cli():
    """El programa por línea de órdenes: código 0 si cumple, 1 si incumple, 2 si el archivo no se lee."""
    rutas = {
        "limpio": os.path.join(AQUI, "ejemplo_libro_SINTETICO.json"),
        "infracciones": os.path.join(AQUI, "ejemplo_libro_con_infracciones_SINTETICO.json"),
    }
    esperados = {"limpio": 0, "infracciones": 1}
    fallos = 0
    for clave, codigo in esperados.items():
        if not os.path.exists(rutas[clave]):
            print(f"[MAL] falta el ejemplo {clave}; ejecute con --generar")
            fallos += 1
            continue
        p = subprocess.run([sys.executable, os.path.join(AQUI, "auditor_reglas_dinero.py"), rutas[clave],
                            "--ahora", str(AHORA_LIMPIO)], capture_output=True, text=True)
        ok = p.returncode == codigo
        fallos += not ok
        print(f"[{'bien' if ok else 'MAL'}] CLI sobre el libro {clave}: código {p.returncode} (esperado {codigo})")
    p = subprocess.run([sys.executable, os.path.join(AQUI, "auditor_reglas_dinero.py"), "NO_EXISTE.json"],
                       capture_output=True, text=True)
    ok = p.returncode == 2
    fallos += not ok
    print(f"[{'bien' if ok else 'MAL'}] CLI con archivo inexistente: código {p.returncode} (esperado 2)")
    return fallos


def generar():
    limpio = libro(libro_limpio())
    with open(os.path.join(AQUI, "ejemplo_libro_SINTETICO.json"), "w", encoding="utf-8") as f:
        json.dump(limpio, f, ensure_ascii=False, indent=1)
    extra = libro_limpio() + [
        orden(5, T0 + 3600, origen="ia", usdt=2.5, visto=0.5, res=0),             # R3: la IA no pide 2 USDT
        orden(6, T0 + 4500, res=1),
    ]
    extra[-1]["neto"] = 9.0                                                       # R9: neto que no cuadra
    extra.append(orden(7, T0 + 4500, res=0))                                      # R5: segunda orden en ese mercado
    with open(os.path.join(AQUI, "ejemplo_libro_con_infracciones_SINTETICO.json"), "w", encoding="utf-8") as f:
        json.dump(libro(extra), f, ensure_ascii=False, indent=1)
    print("ejemplos SINTÉTICOS escritos: ejemplo_libro_SINTETICO.json y ejemplo_libro_con_infracciones_SINTETICO.json")


if __name__ == "__main__":
    if "--generar" in sys.argv:
        generar()
        sys.exit(0)
    f1 = correr_pruebas()
    print()
    f2 = correr_cli()
    total_fallos = f1 + f2
    print("\nTODO BIEN" if total_fallos == 0 else f"\nHAY {total_fallos} FALLO(S)")
    sys.exit(1 if total_fallos else 0)
