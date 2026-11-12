"""Deja el GitHub igual a lo que corre, con una sola orden (04/11/2026).

Refleja en la rama binarias/plan-v7-2026-11-04 de github.com/Nico1091/trader-btc (privado) lo vigente de:
- C:\\Users\\ni109\\Ingresos\\binarias-papel  →  binarias/
- C:\\Users\\ni109\\Ingresos\\pulso-btc       →  binarias/pulso/
- el bloc del Escritorio y las notas de sesión de la bóveda  →  binarias/BLOC-BINARIAS-TODO-EN-UNO.txt y binarias/sesiones/
Pone al día lo que el repositorio ya guarda y suma lo nuevo solo de carpetas permitidas (herramientas, cuant, dispositivos,
historia, guía, sesiones). Nunca sube datos, estados, registros, comprobantes, binarios ni claves: antes del commit barre
el texto en busca de claves y, si encuentra una, no sube nada. Trabaja en su propio árbol, .claude/worktrees/binarias-v7
del repositorio, y nunca toca master: unir la rama a master lo decide Nicolás.
Uso: python -I sincronizar_repo.py "mensaje del commit" [--sin-push]
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = Path(r"C:\Users\ni109\Ingresos\trader-btc")
RAMA = "binarias/plan-v7-2026-11-04"
ARBOL = REPO / ".claude" / "worktrees" / "binarias-v7"
B = Path(r"C:\Users\ni109\Ingresos\binarias-papel")
P = Path(r"C:\Users\ni109\Ingresos\pulso-btc")
BLOC = Path(r"C:\Users\ni109\Desktop\BLOC BINARIAS - TODO EN UNO.txt")
SES = Path(r"C:\Users\ni109\Desktop\obsidian\Vault\01-Sesiones")
SESIONES = {"2026-11-03.md": "2026-11-03 Binarias v5 en BTC.md",
            "2026-11-04.md": "2026-11-04 Binarias v7 su regla SI o NO.md",
            "2026-11-04-tarde.md": "2026-11-04 Binarias cinco lineas y consolidacion.md",
            "2026-11-04-mesa.md": "2026-11-04 Binarias plan del boton comprar o vender.md",
            "2026-11-11-laboratorio.md": "2026-11-11 Laboratorio de binarias con red neuronal.md"}
NUEVOS_ARRIBA = ["PROMPT-AGENTE-NUBE-BINARIAS.md"]
# 11/11/2026: el laboratorio sube solo su código, guiones y documentos; nunca su base, su historial ni sus datos.
NUEVAS_CARPETAS = [("herramientas", (".py",)), ("herramientas/fixtures_lineas", (".csv",)), ("cuant", (".py",)),
                   ("cuant/resultados", (".txt",)), ("dispositivos", (".py", ".sh")), ("historia", (".md", ".py")),
                   ("guia", (".html", ".txt")), ("mesa", (".py", ".pyw", ".html", ".md")),
                   ("laboratorio", (".py", ".sh", ".md")), ("laboratorio/motor", (".py",))]
NUEVOS_PULSO = ["caja-prueba.sh"]
NUNCA = re.compile(r"(^|/)(estado\.json|apuestas\.jsonl|senales_vivo\.jsonl|semaforo\.json|avisados\.json|REAL_AUTORIZADO|PARAR"
                   r"|.*\.(log|npy|npz|pid|zip|pdf|png|nrc|apk|so|env))$|(^|/)(__pycache__|datos|respaldos|comprobantes|salida"
                   r"|auditor_cache|prueba_semaforo_tmp|audio|lib|obj|assets)/")
CLAVES = [re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),                                   # clave de bot de Telegram
          re.compile(r"\b(?=[A-Za-z0-9]{64}\b)(?=[A-Za-z0-9]*[A-Z])(?=[A-Za-z0-9]*[a-z])[A-Za-z0-9]{64}\b"),  # clave de Binance
          re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
          re.compile(r"(?i)(api[_-]?key|secret|password|contraseña)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]")]


def git(*a, ok=True):
    r = subprocess.run(["git", "-C", str(ARBOL), *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ok and r.returncode:
        raise SystemExit(f"git {' '.join(a)} falló: {(r.stderr or r.stdout).strip()[-400:]}")
    return r.stdout


def preparar():
    if not ARBOL.exists():
        r = subprocess.run(["git", "-C", str(REPO), "worktree", "add", str(ARBOL), RAMA], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            raise SystemExit("no se pudo crear el árbol de trabajo: " + (r.stderr or r.stdout)[-400:])
    git("fetch", "-q", "origin", RAMA)
    git("merge", "--ff-only", f"origin/{RAMA}")
    rama = git("branch", "--show-current").strip()
    if rama != RAMA:
        raise SystemExit(f"el árbol está en «{rama}», no en {RAMA}: no sigo")


def fuente(rel):
    """Origen vigente de binarias/<rel>, o None si no tiene (por ejemplo, el README propio del repositorio)."""
    if rel == "BLOC-BINARIAS-TODO-EN-UNO.txt":
        return BLOC
    if rel.startswith("sesiones/"):
        nombre = SESIONES.get(rel.split("/", 1)[1])
        return SES / nombre if nombre else None
    if rel.startswith("pulso/"):
        return P / rel.split("/", 1)[1]
    for c in (B / rel, B / "guia" / Path(rel).name if rel.endswith("GUIA-PARA-LA-GENTE.md") else None,
              B / Path(rel).name if rel.startswith("historia/") else None):
        if c is not None and c.exists():
            return c
    return None


def copiar(src, dst, cambios):
    if dst.exists() and dst.read_bytes() == src.read_bytes():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    cambios.append(str(dst.relative_to(ARBOL)).replace("\\", "/"))


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__)
        return 1
    mensaje = args[0]
    preparar()
    seguidos = [x for x in git("ls-files", "binarias").splitlines() if x]
    cambios, sin_fuente = [], []
    for ruta in seguidos:
        rel = ruta.split("/", 1)[1]
        src = fuente(rel)
        if src is None or not src.exists():
            sin_fuente.append(rel)
            continue
        copiar(src, ARBOL / ruta, cambios)
    vistos = set(seguidos)
    candidatos = [(B / n, f"binarias/{n}") for n in NUEVOS_ARRIBA]
    for carpeta, exts in NUEVAS_CARPETAS:
        for src in sorted((B / carpeta).glob("*")):
            if src.is_file() and src.suffix in exts:
                candidatos.append((src, f"binarias/{carpeta}/{src.name}"))
    candidatos += [(SES / v, f"binarias/sesiones/{k}") for k, v in SESIONES.items()]
    candidatos += [(P / n, f"binarias/pulso/{n}") for n in NUEVOS_PULSO]
    for src, ruta in candidatos:
        if ruta in vistos or not src.exists() or NUNCA.search(ruta):
            continue
        copiar(src, ARBOL / ruta, cambios)
    extra = [r for r in ("README.md", "binarias/README.md") if git("status", "--porcelain", "--", r).strip()]
    if cambios or extra:
        git("add", "--", *cambios, *extra)
    reales = [x for x in git("diff", "--cached", "--name-only").splitlines() if x]  # git normaliza los saltos de línea
    if not reales:
        print("El GitHub ya está igual a lo que corre: nada que subir.")
        return 0
    for ruta in reales:
        texto = (ARBOL / ruta).read_text(encoding="utf-8", errors="replace") if (ARBOL / ruta).exists() else ""
        for patron in CLAVES:
            if patron.search(texto):
                git("reset", "-q")
                raise SystemExit(f"POSIBLE CLAVE en {ruta}: no se sube nada. Revíselo a mano.")
    git("commit", "-q", "-m", mensaje + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    print(f"commit {git('rev-parse', '--short', 'HEAD').strip()} con {len(reales)} archivos:")
    for c in reales:
        print("  ", c)
    if sin_fuente:
        print("sin origen fuera del repositorio (se dejan como están):", ", ".join(sin_fuente))
    if "--sin-push" not in args:
        git("push", "-q", "origin", RAMA)
        print(f"subido a origin/{RAMA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
