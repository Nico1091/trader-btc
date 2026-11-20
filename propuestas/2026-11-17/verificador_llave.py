#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificador de las restricciones de una llave de Binance para la caja de binarias.

Lee solo las banderas que devuelve GET /sapi/v1/account/apiRestrictions y las compara
con la regla del bloc: la llave solo sirve para Lectura y Predicción, sin retiros, sin
transferencias, sin spot, margen, futuros ni opciones, y solo desde la IP de la caja.

No se conecta a Binance, no pide ni usa llaves y no envía órdenes. Solo lee un archivo
JSON y escribe en pantalla (y en un JSON de salida, si se pide).

Regla de seguridad: si el archivo trae algún texto largo (32 caracteres o más), podría
ser una llave. Entonces se niega a seguir, sin mostrar ese texto.

Uso:
  python verificador_llave.py restricciones.json --ip-caja 1.2.3.4 --ip-lista 1.2.3.4
  python verificador_llave.py restricciones.json --ip-caja 1.2.3.4 --ip-lista 1.2.3.4 --confirmo-prediccion
  python verificador_llave.py restricciones.json --ip-caja 1.2.3.4 --ip-lista 1.2.3.4 --json salida.json

Códigos de salida:
  0  APTA: todo cumple y la Predicción fue confirmada a mano.
  1  PENDIENTE: todo lo que se puede leer cumple; falta confirmar la Predicción.
  2  NO APTA: al menos una bandera no cumple, o la IP de la caja no está en la lista.
  3  Entrada mala: archivo ilegible, campo que falta o no es verdadero/falso, IP inválida.
"""
import argparse
import ipaddress
import json
import sys

VERSION = "1"

# Banderas que la regla exige en verdadero.
DEBEN_SER_VERDAD = {
    "enableReading": "Lectura activada (saldos, libro y mercado)",
    "ipRestrict": "Restricción por IP activada",
}

# Banderas que la regla exige en falso.
DEBEN_SER_MENTIRA = {
    "enableWithdrawals": "Retiros por API",
    "enableInternalTransfer": "Transferencias internas",
    "permitsUniversalTransfer": "Transferencia universal",
    "enableFutures": "Futuros",
    "enableMargin": "Margen",
    "enableSpotAndMarginTrading": "Spot y margen",
    "enableVanillaOptions": "Opciones",
    "enablePortfolioMarginTrading": "Margen de cartera",
    "enableFixApiTrade": "Operar por FIX",
}

CAMPOS_REQUERIDOS = list(DEBEN_SER_VERDAD) + list(DEBEN_SER_MENTIRA)
LARGO_SOSPECHOSO = 32

NOTA_PREDICCION = (
    "Predicción: este endpoint no la muestra. Confírmela a mano en la app de Binance "
    "y vuelva a correr con --confirmo-prediccion."
)


class EntradaMala(Exception):
    """Error de entrada: el programa no llega a juzgar la llave."""


def leer_restricciones(ruta):
    """Lee el JSON y devuelve un dict. Falla cerrado: cualquier problema es EntradaMala."""
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        raise EntradaMala(f"no existe el archivo: {ruta}")
    except (OSError, UnicodeDecodeError) as ex:
        raise EntradaMala(f"no se puede leer el archivo ({type(ex).__name__})")
    except json.JSONDecodeError as ex:
        raise EntradaMala(f"el archivo no es JSON válido (línea {ex.lineno})")
    if not isinstance(datos, dict):
        raise EntradaMala("el JSON debe ser un objeto con las banderas de la respuesta")
    for clave, valor in datos.items():
        if isinstance(valor, str) and len(valor) >= LARGO_SOSPECHOSO:
            # No se muestra el texto: podría ser una llave.
            raise EntradaMala(
                f"el campo «{clave}» trae un texto largo; podría ser una llave. "
                "Esta respuesta no debe contener textos así. Se detiene sin mostrarlo."
            )
    return datos


def ip_valida(texto, nombre):
    try:
        return str(ipaddress.ip_address(texto.strip()))
    except ValueError:
        raise EntradaMala(f"{nombre} no es una IP válida: «{texto}» (use una sola IP, sin /red)")


def revisar(datos, ip_caja, ips_lista, confirmo_prediccion):
    """Devuelve (veredicto, código, fallas, pendientes, cumplen)."""
    fallas, cumplen = [], []

    faltan = [c for c in CAMPOS_REQUERIDOS if c not in datos]
    if faltan:
        fallas.append(
            "faltan en la respuesta: " + ", ".join(faltan) + ". Sin ellas no se puede dar por buena la llave."
        )

    for campo, nombre in DEBEN_SER_VERDAD.items():
        if campo not in datos:
            continue
        valor = datos[campo]
        if not isinstance(valor, bool):
            raise EntradaMala(f"«{campo}» debe ser verdadero o falso")
        if valor is True:
            cumplen.append(f"{nombre}: {campo} = true")
        else:
            fallas.append(f"{nombre}: {campo} = false. Debe ser true.")

    for campo, nombre in DEBEN_SER_MENTIRA.items():
        if campo not in datos:
            continue
        valor = datos[campo]
        if not isinstance(valor, bool):
            raise EntradaMala(f"«{campo}» debe ser verdadero o falso")
        if valor is False:
            cumplen.append(f"{nombre}: {campo} = false")
        else:
            fallas.append(f"{nombre}: {campo} = true. Debe ser false.")

    if ip_caja in ips_lista:
        cumplen.append(f"IP de la caja ({ip_caja}) está en la lista que usted escribió")
    else:
        fallas.append(
            f"la IP de la caja ({ip_caja}) no está en la lista de IP que usted indicó. "
            "Con esa IP Binance rechaza las consultas (error −2015)."
        )

    pendientes = []
    if not confirmo_prediccion:
        pendientes.append(NOTA_PREDICCION)

    if fallas:
        return "NO APTA", 2, fallas, pendientes, cumplen
    if pendientes:
        return "PENDIENTE", 1, fallas, pendientes, cumplen
    return "APTA", 0, fallas, pendientes, cumplen


def construir_parser():
    p = argparse.ArgumentParser(
        description="Revisa las banderas de una llave de Binance contra la regla de la caja de binarias "
        "(solo lectura y predicción, IP fija). No se conecta a Binance."
    )
    p.add_argument("archivo", help="JSON con la respuesta de GET /sapi/v1/account/apiRestrictions")
    p.add_argument("--ip-caja", required=True, help="IP pública de salida de la caja, hoy")
    p.add_argument(
        "--ip-lista",
        required=True,
        help="IP que usted escribió en la lista de IP de la llave (separadas por coma)",
    )
    p.add_argument(
        "--confirmo-prediccion",
        action="store_true",
        help="Confirme que revisó a mano que la llave tiene Predicción y nada más",
    )
    p.add_argument("--json", dest="salida_json", help="Escribe el informe (sin valores del archivo) en este JSON")
    return p


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        datos = leer_restricciones(args.archivo)
        ip_caja = ip_valida(args.ip_caja, "--ip-caja")
        partes = [x for x in args.ip_lista.split(",") if x.strip()]
        if not partes:
            raise EntradaMala("--ip-lista está vacía")
        ips_lista = [ip_valida(x, "--ip-lista") for x in partes]
        veredicto, codigo, fallas, pendientes, cumplen = revisar(
            datos, ip_caja, ips_lista, args.confirmo_prediccion
        )
    except EntradaMala as ex:
        print(f"Verificador de llave · versión {VERSION}")
        print(f"ENTRADA MALA: {str(ex).rstrip('.')}. No se juzga la llave.")
        return 3

    print(f"Verificador de llave de Binance · versión {VERSION}")
    print(f"Banderas leídas: {len([c for c in CAMPOS_REQUERIDOS if c in datos])} de {len(CAMPOS_REQUERIDOS)} requeridas")
    print()
    for linea in cumplen:
        print(f"  OK     {linea}")
    for linea in fallas:
        print(f"  FALLA  {linea}")
    for linea in pendientes:
        print(f"  PENDIENTE  {linea}")
    print()
    print(f"VEREDICTO: {veredicto}")
    if veredicto == "APTA":
        print("La llave cumple la regla. Eso no dice nada de ventaja: solo de permisos.")
    elif veredicto == "NO APTA":
        print("No la use hasta corregirla en la app de Binance y volver a verificar.")

    if args.salida_json:
        informe = {
            "version": VERSION,
            "veredicto": veredicto,
            "codigo": codigo,
            "ip_caja": ip_caja,
            "ips_lista": ips_lista,
            "cumplen": cumplen,
            "fallas": fallas,
            "pendientes": pendientes,
        }
        with open(args.salida_json, "w", encoding="utf-8") as f:
            json.dump(informe, f, ensure_ascii=False, indent=2)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
