#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escáner de secretos y datos personales en TODO el historial de un repositorio git.

Revisa cada objeto `blob` alcanzable desde cualquier rama o etiqueta, también los
archivos ya borrados, porque siguen en el historial. Solo lee: no cambia el
repositorio, no se conecta a internet y no envía nada.

Uso:
    python3 escaner_secretos.py [--repo RUTA] [--sensibles ARCHIVO] [--json SALIDA]

Niveles:
    CRITICO  forma de credencial: clave privada, token de Telegram, clave de
             Anthropic, OpenAI, GitHub o AWS, asignación de contraseña o clave
             con valor de alta entropía, o una cadena de 64 caracteres junto a
             la palabra «binance» (posible clave de Binance).
    REVISAR  dato personal o de red: IP pública, ruta de usuario de Windows,
             correo, o un texto de la lista --sensibles.

Los valores de los secretos nunca se imprimen completos: se muestran los 4
primeros y los 2 últimos caracteres. Un secreto que estuvo en un commit de un
repositorio público debe darse por comprometido aunque ya se haya borrado.

Códigos de salida: 0 sin hallazgos CRITICO, 1 con hallazgos CRITICO, 2 error.
Solo biblioteca estándar de Python 3.8 o superior.
"""

import argparse
import collections
import ipaddress
import json
import math
import re
import subprocess
import sys
import threading

TAMANO_MAX = 10 * 1024 * 1024
MARCADORES = ("xxxx", "ejemplo", "example", "placeholder", "changeme", "tu_clave",
              "tu-clave", "tu_token", "your", "fake", "sintetic", "<", "***")
CORREOS_IGNORADOS = ("noreply", "example.", "ejemplo", "localhost", "dominio.")
# «correo» cuyo final es una extensión de archivo (p. ej. curl ... text@informe.txt)
EXTENSIONES_FICHERO = {"txt", "md", "py", "pyw", "json", "csv", "cmd", "bat", "ps1", "sh",
                       "pdf", "png", "jpg", "log", "java", "js", "html", "xml", "yaml",
                       "yml", "ini", "cfg", "zip", "exe", "dll", "kt", "gradle"}
# Valores públicos conocidos que no son credenciales de nadie:
# 6A5AA1D4EAFF4E9FB37E23D68491D6F4 es el token de cliente público de la lectura en voz
# de Microsoft Edge, publicado por proyectos abiertos como edge-tts.
PUBLICOS_CONOCIDOS = {"6A5AA1D4EAFF4E9FB37E23D68491D6F4"}

# (id, nivel, expresión, grupo con el valor, requisito adicional del texto)
PATRONES = [
    ("clave_privada", "CRITICO",
     re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"), 0, None),
    ("token_telegram", "CRITICO",
     re.compile(r"(?<!\d)\d{8,10}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])"), 0, None),
    ("clave_anthropic", "CRITICO",
     re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), 0, None),
    ("clave_openai", "CRITICO",
     re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"), 0, None),
    ("token_github", "CRITICO",
     re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b"), 0, None),
    ("clave_aws", "CRITICO",
     re.compile(r"\bAKIA[0-9A-Z]{16}\b"), 0, None),
    ("asignacion_secreta", "CRITICO",
     re.compile(r"(?i)\b(?:api[_ -]?key|apikey|api[_ -]?secret|secret(?:[_ -]?key)?|token|"
                r"password|passwd|contrase[ñn]a|clave(?:[_ -]?(?:api|secreta|privada))?)"
                r"\s*[:=]\s*[\"']?([A-Za-z0-9_+/=\-]{16,})"), 1, None),
    ("posible_clave_binance", "CRITICO",
     re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{64}(?![A-Za-z0-9])"), 0,
     re.compile(r"(?i)binance")),
    ("ip_publica", "REVISAR",
     re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"), 0, None),
    ("ruta_usuario_windows", "REVISAR",
     re.compile(r"(?i)[a-z]:\\Users\\([^\\\s\"'<>|]+)"), 1, None),
    ("correo", "REVISAR",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"), 0, None),
]


def git(repo, *args, entrada=None):
    r = subprocess.run(["git", "-C", repo, *args], input=entrada,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), r.stderr.decode(errors="replace").strip()))
    return r.stdout


def entropia(texto):
    """Entropía de Shannon en bits por carácter."""
    if not texto:
        return 0.0
    n = len(texto)
    return -sum((c / n) * math.log2(c / n) for c in collections.Counter(texto).values())


def es_marcador(valor):
    """Parece un texto de ejemplo o un marcador, no una credencial real."""
    bajo = valor.lower()
    return any(m in bajo for m in MARCADORES) or len(set(valor)) <= 4


def aceptar_asignacion(valor):
    if valor in PUBLICOS_CONOCIDOS or es_marcador(valor) or len(valor) < 16:
        return False
    tiene_letra = any(c.isalpha() for c in valor)
    tiene_digito = any(c.isdigit() for c in valor)
    return tiene_letra and tiene_digito and entropia(valor) >= 3.0


def aceptar_binance(valor):
    """Las claves de la API de Binance mezclan mayúsculas, minúsculas y dígitos.
    Una cadena de solo hexadecimales de 64 caracteres suele ser un hash SHA-256."""
    return (any(c.islower() for c in valor) and any(c.isupper() for c in valor)
            and any(c.isdigit() for c in valor))


def aceptar_ip(valor):
    try:
        return ipaddress.ip_address(valor).is_global
    except ValueError:
        return False


def aceptar_correo(valor):
    bajo = valor.lower()
    if any(p in bajo for p in CORREOS_IGNORADOS):
        return False
    return bajo.rsplit(".", 1)[-1] not in EXTENSIONES_FICHERO


def enmascarar(valor):
    """Oculta un secreto: 4 primeros y 2 últimos caracteres."""
    if len(valor) < 12:
        return "*** (%d car.)" % len(valor)
    return "%s…%s (%d car.)" % (valor[:4], valor[-2:], len(valor))


ETIQUETAS = {
    "ip_publica": lambda v: v,  # las IP son de red, no secretos: se muestran enteras
    "ruta_usuario_windows": lambda v: "nombre de usuario de Windows (%d car.)" % len(v),
    "correo": lambda v: "dirección de correo (%d car.)" % len(v),
    "dato_indicado_en_lista": lambda v: "dato de la lista (%d car.)" % len(v),
}


def analizar_texto(texto, sensibles=()):
    """Devuelve los hallazgos de un texto: lista de dicts con valor real en memoria."""
    hallazgos = []

    def linea_de(pos):
        return texto.count("\n", 0, pos) + 1

    for pid, nivel, rx, grupo, requiere in PATRONES:
        if requiere is not None and not requiere.search(texto):
            continue
        for m in rx.finditer(texto):
            valor = m.group(grupo)
            if pid == "asignacion_secreta" and not aceptar_asignacion(valor):
                continue
            if pid == "posible_clave_binance" and not aceptar_binance(valor):
                continue
            if pid == "ip_publica" and not aceptar_ip(valor):
                continue
            if pid == "correo" and not aceptar_correo(valor):
                continue
            etiqueta = ETIQUETAS.get(pid, enmascarar)
            hallazgos.append({
                "id": pid, "nivel": nivel, "valor": valor, "mostrado": etiqueta(valor),
                "linea": linea_de(m.start(grupo)),
            })

    for literal in sensibles:
        pos = texto.find(literal)
        while pos != -1:
            hallazgos.append({
                "id": "dato_indicado_en_lista", "nivel": "REVISAR", "valor": literal,
                "mostrado": ETIQUETAS["dato_indicado_en_lista"](literal), "linea": linea_de(pos),
            })
            pos = texto.find(literal, pos + 1)
    return hallazgos


def listar_objetos(repo):
    """Refs, blobs alcanzables y rutas de cada blob."""
    refs = git(repo, "for-each-ref", "--format=%(refname)").decode().split()
    lineas = git(repo, "rev-list", "--objects", "--all").decode().splitlines()
    rutas = collections.defaultdict(set)
    shas = []
    for linea in lineas:
        partes = linea.split(" ", 1)
        shas.append(partes[0])
        if len(partes) == 2:
            rutas[partes[0]].add(partes[1])
    unicos = list(dict.fromkeys(shas))
    tipos = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)",
                entrada=("\n".join(unicos) + "\n").encode()).decode().splitlines()
    blobs = [t.split()[0] for t in tipos if t.split()[1] == "blob"]
    return refs, blobs, rutas


def blobs_por_flujo(repo, shas):
    """Lee el contenido de cada blob con `git cat-file --batch`, en flujo."""
    p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)

    def alimentar():
        try:
            for s in shas:
                p.stdin.write((s + "\n").encode())
            p.stdin.flush()
        except BrokenPipeError:
            pass
        finally:
            try:
                p.stdin.close()
            except BrokenPipeError:
                pass

    hilo = threading.Thread(target=alimentar, daemon=True)
    hilo.start()
    try:
        for _ in shas:
            cab = p.stdout.readline().decode().split()
            if not cab:
                break
            if cab[-1] == "missing":
                continue
            datos = p.stdout.read(int(cab[2]))
            p.stdout.read(1)
            yield cab[0], datos
    finally:
        hilo.join()
        p.wait()


def rama_principal(repo, refs):
    for candidata in ("refs/remotes/origin/master", "refs/heads/master"):
        if candidata in refs:
            return candidata
    return "HEAD"


def blobs_vigentes(repo, ref):
    out = git(repo, "ls-tree", "-r", "--full-tree", ref).decode()
    return {linea.split()[2] for linea in out.splitlines() if linea.strip()}


def escanear(repo, sensibles=(), max_rutas=5):
    refs, blobs, rutas = listar_objetos(repo)
    vigentes = blobs_vigentes(repo, rama_principal(repo, refs))
    acumulado = {}
    revisados = omitidos = 0
    for sha, datos in blobs_por_flujo(repo, blobs):
        if len(datos) > TAMANO_MAX or b"\0" in datos[:8000]:
            omitidos += 1
            continue
        revisados += 1
        texto = datos.decode("utf-8", errors="replace")
        for h in analizar_texto(texto, sensibles):
            clave = (h["id"], h["valor"])
            reg = acumulado.get(clave)
            if reg is None:
                reg = acumulado[clave] = {
                    "nivel": h["nivel"], "id": h["id"], "valor": h["mostrado"],
                    "blobs": set(), "rutas": set(), "lineas": set(),
                }
            reg["blobs"].add(sha)
            reg["rutas"].update(rutas.get(sha, ()))
            reg["lineas"].add(h["linea"])

    hallazgos = []
    for reg in acumulado.values():
        rs = sorted(reg["rutas"])
        primera = []
        for ruta in rs[:max_rutas]:
            prim = git(repo, "log", "--all", "--reverse", "--format=%h %as", "--", ruta).decode().split("\n")[0]
            primera.append({"ruta": ruta, "primer_commit": prim})
        hallazgos.append({
            "nivel": reg["nivel"], "id": reg["id"], "valor": reg["valor"],
            "rutas": rs, "numero_de_rutas": len(rs),
            "lineas": sorted(reg["lineas"])[:10],
            "vigente_en_rama_principal": any(b in vigentes for b in reg["blobs"]),
            "primera_aparicion": primera,
        })
    hallazgos.sort(key=lambda h: (h["nivel"] != "CRITICO", h["id"], h["valor"]))
    return {
        "resumen": {
            "repo": repo, "refs": len(refs), "blobs_totales": len(blobs),
            "blobs_revisados": revisados, "blobs_omitidos_binarios_o_grandes": omitidos,
            "criticos": sum(1 for h in hallazgos if h["nivel"] == "CRITICO"),
            "revisar": sum(1 for h in hallazgos if h["nivel"] == "REVISAR"),
        },
        "hallazgos": hallazgos,
    }


def informe(res):
    r = res["resumen"]
    out = ["Escáner de secretos · %s" % r["repo"],
           "Refs revisadas: %d · blobs del historial: %d · revisados: %d · omitidos (binarios o > 10 MB): %d"
           % (r["refs"], r["blobs_totales"], r["blobs_revisados"], r["blobs_omitidos_binarios_o_grandes"]),
           "Hallazgos: %d CRÍTICO, %d REVISAR" % (r["criticos"], r["revisar"]), ""]
    for h in res["hallazgos"]:
        out.append("[%s] %s · valor %s" % (h["nivel"], h["id"], h["valor"]))
        rutas = ", ".join(h["rutas"][:5]) or "(sin ruta)"
        if h["numero_de_rutas"] > 5:
            rutas += " y %d más" % (h["numero_de_rutas"] - 5)
        out.append("   rutas: %s" % rutas)
        for p in h["primera_aparicion"][:3]:
            out.append("   primer commit de %s: %s" % (p["ruta"], p["primer_commit"] or "?"))
        out.append("   en la rama principal: %s" % ("sí" if h["vigente_en_rama_principal"] else "no, solo en el historial"))
    if res["hallazgos"] and r["criticos"]:
        out += ["", "Un CRÍTICO en el historial de un repositorio público debe darse por comprometido:",
                "revocar o cambiar la clave en el proveedor. Borrar el archivo no la quita del historial."]
    return "\n".join(out)


def leer_sensibles(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Escáner de secretos en todo el historial git.")
    ap.add_argument("--repo", default=".", help="ruta del repositorio (por defecto, el actual)")
    ap.add_argument("--sensibles", help="archivo con un texto sensible por línea (opcional)")
    ap.add_argument("--json", dest="json_salida", help="guarda el resultado en JSON (sin valores completos)")
    ap.add_argument("--max-rutas", type=int, default=5)
    args = ap.parse_args(argv)
    try:
        sens = leer_sensibles(args.sensibles) if args.sensibles else []
        res = escanear(args.repo, sens, args.max_rutas)
    except (RuntimeError, OSError) as e:
        print("Error: %s" % e, file=sys.stderr)
        return 2
    print(informe(res))
    if args.json_salida:
        with open(args.json_salida, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2, default=list)
    return 1 if res["resumen"]["criticos"] else 0


if __name__ == "__main__":
    sys.exit(main())
