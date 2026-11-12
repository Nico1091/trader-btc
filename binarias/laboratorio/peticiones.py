"""Peticiones del dueño por Telegram (11/11/2026). Solo desde su chat y con una lista cerrada; cualquier otra cosa se ignora.

  mejores [hoy|semana|todo] · forma F-12 · estado · origen · pausa · sigue · tope 500 · cada 30 · probar <...> · ayuda
Se pueden escribir con «lab» delante («lab estado»). «pausa» detiene la búsqueda y el reentrenamiento; el papel en vivo sigue.
La caja mira el chat cada 20 s con getUpdates sin offset (no consume los mensajes que lean otros programas) y anota cada
petición y su respuesta en la tabla peticiones, para responder una sola vez."""
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base  # noqa: E402
import busqueda as BQ  # noqa: E402
import formas as F  # noqa: E402
import partes as P  # noqa: E402
from comun import EQUILIBRIO, log, num, pct, temperatura  # noqa: E402

COMANDOS = ("mejores", "forma", "estado", "origen", "pausa", "sigue", "tope", "cada", "probar", "ayuda", "perdida", "placa")
AYUDA = ("Laboratorio · órdenes: «mejores hoy», «mejores semana», «mejores todo», «forma F-12», «estado», «origen», "
         "«perdida» (la tabla de comprar sobre la pérdida y cómo va en vivo), «placa» (la ESP32 y el precio real), "
         "«pausa» (detiene búsqueda y reentrenamiento; el papel sigue), «sigue», «tope 500» (formas en vivo), "
         "«cada 30» (minutos del resumen) y «probar ruptura 30 al revés 15». Disparos para probar: "
         + ", ".join(sorted(F.DISPAROS)) + ". Es papel.")


def limpiar(texto):
    t = unicodedata.normalize("NFKD", texto.strip().lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"\s+", " ", t)
    for pre in ("laboratorio ", "lab "):
        if t.startswith(pre):
            t = t[len(pre):]
    return t


def responder(lab, texto_original):
    t = limpiar(texto_original)
    palabra = t.split(" ")[0] if t else ""
    if palabra not in COMANDOS:
        return None
    con = lab.con
    arg = t[len(palabra):].strip()
    if palabra == "ayuda":
        return AYUDA
    if palabra == "mejores":
        periodo = arg if arg in ("hoy", "semana", "todo") else "hoy"
        return P.mejores_texto(con, periodo, temperatura())
    if palabra == "forma":
        m = re.search(r"(\d+)", arg)
        return P.ficha_texto(con, int(m.group(1))) if m else "Escriba «forma F-12» con el número de la forma."
    if palabra == "estado":
        return lab.estado_texto()
    if palabra == "origen":
        return P.origen_texto(con)
    if palabra == "perdida":
        import perdida as PD
        return PD.texto_tabla() + "\n" + lab.perdida.linea()
    if palabra == "placa":
        return "Laboratorio · " + lab.linea_placa()
    if palabra == "pausa":
        lab.pausa = True
        base.poner(con, "pausa", True)
        return "Laboratorio en pausa: búsqueda y reentrenamiento detenidos; el papel en vivo sigue. «sigue» lo reanuda."
    if palabra == "sigue":
        lab.pausa = False
        base.poner(con, "pausa", False)
        return "Laboratorio reanudado: vuelve la búsqueda de cada hora."
    if palabra in ("tope", "cada"):
        m = re.search(r"(\d+)", arg)
        if not m:
            return f"Escriba «{palabra}» y un número."
        v = int(m.group(1))
        if palabra == "tope":
            v = max(10, min(v, 2000))
            lab.tope = v
            base.poner(con, "tope", v)
            return f"Tope de formas en vivo: {v}."
        v = max(10, min(v, 1440))
        lab.cada = v
        base.poner(con, "cada", v)
        return f"El resumen llegará cada {v} minutos."
    if palabra == "probar":
        ficha, error = F.parsear(t)
        if error:
            return error
        fid, c, estado = BQ.probar_dueno(con, lab.ctx, ficha, lab.tope)
        lab.emu.recargar()
        if c is None:
            return f"Esa forma ya existía: F-{fid:04d}. «forma F-{fid}» trae sus cifras."
        eq = EQUILIBRIO[ficha["p"]]
        cif = f"{c['k']} de {c['n']} ({pct(c['k'] / c['n'])}), Wilson inferior {pct(c['wi'])}" if c["n"] else "sin señales"
        return (f"Laboratorio · F-{fid:04d} · {F.describir(ficha)}\n«elige» (ene-2024 a jun-2025): {cif}; equilibrio {pct(eq)}. "
                f"Valla: {estado}. Entra a vivo para medirse. Es papel.")
    return None


def atender(lab):
    """Lee los mensajes nuevos del chat del dueño y responde las órdenes de la lista. Devuelve cuántas atendió."""
    if P.SECO:
        return 0
    chat = P.chat()
    if not chat:
        return 0
    atendidas = 0
    for u in P.updates():
        uid = u.get("update_id")
        m = u.get("message") or u.get("edited_message")
        if uid is None or not m or str(m.get("chat", {}).get("id")) != str(chat):
            continue
        if m.get("date", 0) < lab.inicio - 60:
            continue
        if lab.con.execute("SELECT 1 FROM peticiones WHERE update_id=?", (uid,)).fetchone():
            continue
        texto = (m.get("text") or "").strip()
        try:
            resp = responder(lab, texto)
        except Exception as ex:
            resp = f"Laboratorio: no pude atender «{texto[:40]}» ({type(ex).__name__})."
            log(f"petición falló: {type(ex).__name__}: {str(ex)[:160]}")
        lab.con.execute("INSERT OR IGNORE INTO peticiones (update_id, t, texto, respuesta) VALUES (?, ?, ?, ?)",
                        (uid, int(m.get("date", time.time())), texto[:500], resp))
        lab.con.commit()
        if resp:
            P.enviar(resp)
            atendidas += 1
    return atendidas
