"""Base del laboratorio (11/11/2026): SQLite en modo WAL, con copia diaria (se guardan siete).

Tablas: formas, pruebas (cifras en historia por tramo), senales (apuestas de papel en vivo), redes, eventos, peticiones,
salida (cola de mensajes a Telegram), velas, indice e interes (lo que llega en vivo) y estado.
Uso: python -I base.py --resumen"""
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import BASE, RESPALDOS, hora, log  # noqa: E402

ESQUEMA = """
CREATE TABLE IF NOT EXISTS formas (id INTEGER PRIMARY KEY, huella TEXT UNIQUE NOT NULL, ficha TEXT NOT NULL, origen TEXT NOT NULL,
  nombre TEXT, nacida INTEGER NOT NULL, lote INTEGER, estado TEXT NOT NULL, en_vivo INTEGER, situacion TEXT, cambio INTEGER,
  familia TEXT);
CREATE INDEX IF NOT EXISTS formas_estado ON formas (estado, familia);
CREATE TABLE IF NOT EXISTS pruebas (forma INTEGER NOT NULL, tramo TEXT NOT NULL, n INTEGER, k INTEGER, wilson_inf REAL,
  wilson_sup REAL, p REAL, n_i INTEGER, k_i INTEGER, t INTEGER, PRIMARY KEY (forma, tramo));
CREATE TABLE IF NOT EXISTS senales (id INTEGER PRIMARY KEY, forma INTEGER NOT NULL, t INTEGER NOT NULL, dir INTEGER NOT NULL,
  plazo INTEGER NOT NULL, p_red REAL, entrada REAL, salida REAL, res INTEGER, entrada_i REAL, salida_i REAL, res_i INTEGER,
  semilla INTEGER DEFAULT 0, UNIQUE (forma, t));
CREATE INDEX IF NOT EXISTS senales_t ON senales (t);
CREATE INDEX IF NOT EXISTS senales_forma ON senales (forma, t);
CREATE TABLE IF NOT EXISTS redes (id INTEGER PRIMARY KEY, tipo TEXT NOT NULL, plazo INTEGER, t INTEGER NOT NULL, datos TEXT NOT NULL,
  nota TEXT);
CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY, t INTEGER NOT NULL, tipo TEXT NOT NULL, texto TEXT);
CREATE TABLE IF NOT EXISTS peticiones (update_id INTEGER PRIMARY KEY, t INTEGER, texto TEXT, respuesta TEXT);
CREATE TABLE IF NOT EXISTS salida (id INTEGER PRIMARY KEY, t INTEGER NOT NULL, tipo TEXT NOT NULL, texto TEXT NOT NULL,
  enviado INTEGER DEFAULT 0, mensaje INTEGER);
CREATE TABLE IF NOT EXISTS velas (t INTEGER PRIMARY KEY, o REAL, h REAL, l REAL, c REAL, v REAL);
CREATE TABLE IF NOT EXISTS indice (t INTEGER PRIMARY KEY, c REAL);
CREATE TABLE IF NOT EXISTS interes (t INTEGER PRIMARY KEY, oi REAL);
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT);
"""


def abrir(ruta=BASE):
    con = sqlite3.connect(ruta, timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(ESQUEMA)
    return con


def leer(con, clave, defecto=None):
    r = con.execute("SELECT valor FROM estado WHERE clave=?", (clave,)).fetchone()
    return defecto if r is None else json.loads(r[0])


def poner(con, clave, valor):
    con.execute("INSERT INTO estado (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
                (clave, json.dumps(valor, ensure_ascii=False)))
    con.commit()


def evento(con, tipo, texto):
    con.execute("INSERT INTO eventos (t, tipo, texto) VALUES (?, ?, ?)", (int(time.time()), tipo, texto))
    con.commit()
    log(f"[{tipo}] {texto}")


def encolar(con, tipo, texto):
    con.execute("INSERT INTO salida (t, tipo, texto) VALUES (?, ?, ?)", (int(time.time()), tipo, texto))
    con.commit()


def respaldo(con, guardar=7):
    """Copia del día con la API de copia de SQLite (sirve con la base abierta); deja las `guardar` más nuevas."""
    os.makedirs(RESPALDOS, exist_ok=True)
    destino = os.path.join(RESPALDOS, f"lab-{hora(time.time(), '%Y%m%d')}.db")
    otra = sqlite3.connect(destino)
    with otra:
        con.backup(otra)
    otra.close()
    viejas = sorted(x for x in os.listdir(RESPALDOS) if x.startswith("lab-") and x.endswith(".db"))
    for x in viejas[:-guardar]:
        try:
            os.remove(os.path.join(RESPALDOS, x))
        except OSError:
            pass
    return destino


def resumen(con):
    out = []
    for tabla in ("formas", "pruebas", "senales", "redes", "eventos", "peticiones", "salida", "velas", "indice", "interes"):
        out.append(f"{tabla}: {con.execute(f'SELECT COUNT(*) FROM {tabla}').fetchone()[0]}")
    for estado, n in con.execute("SELECT estado, COUNT(*) FROM formas GROUP BY estado ORDER BY 2 DESC"):
        out.append(f"  formas {estado}: {n}")
    for origen, n in con.execute("SELECT origen, COUNT(*) FROM formas GROUP BY origen ORDER BY 2 DESC"):
        out.append(f"  origen {origen}: {n}")
    r = con.execute("SELECT COUNT(*), SUM(res) FROM senales WHERE res IS NOT NULL").fetchone()
    out.append(f"apuestas cerradas en vivo: {r[0]}, aciertos: {r[1] or 0}")
    u = con.execute("SELECT MAX(t) FROM velas").fetchone()[0]
    if u:
        out.append(f"última vela guardada: {hora(u + 60)} (hora de Colombia, cierre)")
    for t, tipo, texto in con.execute("SELECT t, tipo, texto FROM eventos ORDER BY id DESC LIMIT 5"):
        out.append(f"evento {hora(t)} [{tipo}] {texto[:120]}")
    return "\n".join(out)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = abrir()
    if "--copia" in sys.argv:
        destino = sys.argv[sys.argv.index("--copia") + 1]
        otra = sqlite3.connect(destino)
        with otra:
            c.backup(otra)
        otra.close()
        print(f"copia en {destino}")
    else:
        print(resumen(c) if "--resumen" in sys.argv else "Uso: python -I base.py --resumen | --copia RUTA")
