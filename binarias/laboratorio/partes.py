"""Lo que el laboratorio manda a Telegram (11/11/2026), por Tor y con el bot de siempre, en texto directo.

- Tablero: un mensaje anclado que se edita cada 5 min con las diez mejores formas en vivo (por Wilson inferior).
- Resumen cada hora (o cada N minutos, si el dueño lo pide): las tres mejores de la hora y de hoy, con su neto.
- Parte diario a las 6:00: formas nacidas, probadas, admitidas y descartadas; resultados en vivo; rendimiento por origen;
  estado de las redes; horas de marcha, temperatura máxima y pausas; lo que el azar solo le daría a la mejor de N.
- Avisos (uno por hora como máximo): forma que queda prometedora, apta o descartada; laboratorio detenido o de vuelta;
  reloj mal; calor.
La clave del bot se lee al momento de ~/.config/binarias/telegram (línea 1: clave, línea 2: chat) y viaja a curl por la
entrada estándar, como en avisos.py. De usted, sin el nombre del dueño, hora de Colombia; cada cifra lleva su n. Es papel."""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validacion as V  # noqa: E402
from comun import EQUILIBRIO, hora, inicio_dia, log, neto, num, pct  # noqa: E402

CLAVE = os.path.expanduser("~/.config/binarias/telegram")
TOR = os.environ.get("LAB_TOR", "127.0.0.1:9050")
SECO = False
PREFIJO = "Laboratorio"
LINEAS_EXTRA = []  # funciones que devuelven una línea más para el tablero y el parte (la pérdida y la placa ESP32)


def extras():
    out = []
    for f in LINEAS_EXTRA:
        try:
            out.append(f())
        except Exception as ex:
            log(f"línea extra falló ({type(ex).__name__}: {str(ex)[:80]})")
    return out


def _clave():
    try:
        x = open(CLAVE, encoding="utf-8").read().split()
        return x[0], x[1]
    except Exception:
        return None, None


def chat():
    return _clave()[1]


def _comillas(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


def _llamar(metodo, campos=None, consulta="", tiempo=60):
    token, ch = _clave()
    if SECO or not token:
        return None
    conf = ["url = " + _comillas(f"https://api.telegram.org/bot{token}/{metodo}{consulta}")]
    for k, v in (campos or {}).items():
        conf.append("form-string = " + _comillas(f"{k}={v}"))
    usuario = f"lab{int(time.time()) % 100000}:x"  # circuito propio por llamada
    try:
        r = subprocess.run(["curl", "-s", "--max-time", str(tiempo), "--socks5-hostname", f"{usuario}@{TOR}", "-K", "-"],
                           input="\n".join(conf) + "\n", capture_output=True, text=True, timeout=tiempo + 30)
        return json.loads(r.stdout) if r.stdout.strip() else None
    except Exception as ex:
        log(f"Telegram falló en {metodo} ({type(ex).__name__})")
        return None


def enviar(texto):
    """Devuelve el número del mensaje o None."""
    r = _llamar("sendMessage", {"chat_id": chat(), "text": texto[:4000]})
    if r and r.get("ok"):
        return r["result"]["message_id"]
    if r:
        log(f"Telegram no aceptó el mensaje: {str(r)[:160]}")
    return None


def editar(mid, texto):
    """«ok», «igual» (no cambió), «falta» (el mensaje ya no existe) o None (sin red)."""
    r = _llamar("editMessageText", {"chat_id": chat(), "message_id": mid, "text": texto[:4000]})
    if r is None:
        return None
    if r.get("ok"):
        return "ok"
    d = str(r.get("description", ""))
    if "not modified" in d:
        return "igual"
    return "falta" if ("not found" in d or "can't be edited" in d) else None


def anclar(mid):
    r = _llamar("pinChatMessage", {"chat_id": chat(), "message_id": mid, "disable_notification": "true"})
    return bool(r and r.get("ok"))


def updates():
    """Mensajes pendientes del bot, sin offset para no consumir los que lean otros programas (hasta 100, 24 h)."""
    r = _llamar("getUpdates", consulta="?limit=100&timeout=0", tiempo=40)
    return r.get("result", []) if r and r.get("ok") else []


# ---------------------------------------------------------------- cifras para los textos
def cifras_vivas(con, desde=None, solo_vivas=True):
    q = ("SELECT f.id, f.origen, f.nombre, f.ficha, f.situacion, COUNT(s.id), COALESCE(SUM(s.res), 0) FROM formas f "
         "LEFT JOIN senales s ON s.forma=f.id AND s.res IN (0, 1) AND s.t>=COALESCE(f.en_vivo, 0)" +
         (" AND s.t>=?" if desde else "") + (" WHERE f.estado='viva'" if solo_vivas else " WHERE f.en_vivo IS NOT NULL") +
         " GROUP BY f.id")
    out = []
    for fid, origen, nombre, ficha, sit, n, k in con.execute(q, (int(desde),) if desde else ()):
        p = json.loads(ficha)["p"]
        jz = con.execute("SELECT n, k FROM pruebas WHERE forma=? AND tramo='juzga'", (fid,)).fetchone()
        wi = V.wilson(k, n)[0] if n else 0.0
        out.append({"id": fid, "origen": origen, "nombre": nombre, "plazo": p, "situacion": sit, "n": n, "k": k, "wi": wi,
                    "neto": (k * neto(1, p) + (n - k) * neto(0, p)), "juzga": jz})
    out.sort(key=lambda x: (x["wi"], x["n"]), reverse=True)
    return out


def linea(i, x):
    t = f"{i}. F-{x['id']:04d} · {x['origen']} · {x['nombre']}"
    t += f" · {x['k']} de {x['n']} ({pct(x['k'] / x['n'])})" if x["n"] else " · sin cerradas aún"
    if x["juzga"] and x["juzga"][0]:
        t += f" · a ciegas {pct(x['juzga'][1] / x['juzga'][0])} en {num(x['juzga'][0], 0)}"
    return t


def cabecera(con, temp):
    vivas = con.execute("SELECT COUNT(*) FROM formas WHERE estado='viva'").fetchone()[0]
    t = f"{PREFIJO} · {hora(time.time())} · {vivas} formas en vivo"
    return t + (f" · caja {num(temp, 0)} °C" if temp is not None else "")


def tablero(con, temp):
    cv = cifras_vivas(con)
    con_n = [x for x in cv if x["n"]]
    lineas = [cabecera(con, temp), "Las diez mejores en vivo (ordenadas por Wilson inferior):"]
    lineas += [linea(i + 1, x) for i, x in enumerate((con_n or cv)[:10])]
    ini = inicio_dia(time.time())
    hoy = con.execute("SELECT COUNT(*), COALESCE(SUM(res), 0) FROM senales WHERE res IN (0, 1) AND t>=?", (ini,)).fetchone()
    nac = con.execute("SELECT COUNT(*) FROM formas WHERE origen IN ('red', 'azar') AND nacida>=?", (ini,)).fetchone()[0]
    ent = con.execute("SELECT COUNT(*) FROM formas WHERE origen<>'pasada' AND en_vivo>=?", (ini,)).fetchone()[0]
    des = con.execute("SELECT COUNT(*) FROM formas WHERE estado='descartada' AND cambio>=?", (ini,)).fetchone()[0]
    lineas.append(f"Hoy: {hoy[0]} apuestas de papel cerradas ({hoy[1]} aciertos); {nac} formas nuevas probadas, {ent} entraron "
                  f"a vivo, {des} descartadas. Es papel.")
    return "\n".join(lineas + extras())


def resumen(con, desde, temp):
    ini = inicio_dia(time.time())
    lineas = [cabecera(con, temp), f"Resumen desde las {hora(desde, '%H:%M')}:"]
    for titulo, d in (("Mejores del rato", desde), ("Mejores de hoy", ini)):
        cv = [x for x in cifras_vivas(con, d) if x["n"]]
        lineas.append(titulo + ":" if cv else titulo + ": sin apuestas cerradas todavía.")
        for i, x in enumerate(cv[:3]):
            lineas.append(linea(i + 1, x) + f" · neto {num(x['neto'], 2)} apuestas")
    lineas.append("Es papel: nada de esto compra.")
    return "\n".join(lineas)


def parte_diario(con, lab):
    ahora = int(time.time())
    d0 = ahora - 86400
    nac = con.execute("SELECT COUNT(*) FROM formas WHERE origen IN ('red', 'azar') AND nacida>=?", (d0,)).fetchone()[0]
    ent = con.execute("SELECT COUNT(*) FROM formas WHERE origen<>'pasada' AND en_vivo>=?", (d0,)).fetchone()[0]
    des = con.execute("SELECT COUNT(*) FROM formas WHERE estado='descartada' AND cambio>=?", (d0,)).fetchone()[0]
    vivas = con.execute("SELECT COUNT(*) FROM formas WHERE estado='viva'").fetchone()[0]
    tot = con.execute("SELECT COUNT(*) FROM formas WHERE origen IN ('red', 'azar')").fetchone()[0]
    lineas = [f"{PREFIJO} · parte diario · {hora(ahora, '%d/%m/%Y %H:%M')}",
              f"Últimas 24 h: {nac} formas nuevas probadas en «elige», {ent} entraron a vivo, {des} descartadas. "
              f"En vivo: {vivas}. Probadas desde el inicio: {num(tot, 0)}."]
    for p in (10, 15):
        n, k = con.execute("SELECT COUNT(*), COALESCE(SUM(res), 0) FROM senales WHERE res IN (0, 1) AND plazo=? AND t>=?",
                           (p, d0)).fetchone()
        if n:
            lineas.append(f"Papel en vivo a {p} min (24 h): {k} de {n} ({pct(k / n)}); equilibrio {pct(EQUILIBRIO[p])}.")
    cv = [x for x in cifras_vivas(con) if x["n"]]
    if cv:
        lineas.append("Las cinco mejores desde que entraron:")
        lineas += [linea(i + 1, x) for i, x in enumerate(cv[:5])]
        m = cv[0]
        azar = V.acierto_maximo_por_azar(max(m["n"], 1), max(len(cv), 1), EQUILIBRIO[m["plazo"]])
        lineas.append(f"Con {len(cv)} formas midiéndose, la mejor de ellas sacaría por puro azar hasta {pct(azar)} con "
                      f"{m['n']} apuestas: por debajo de eso, no hay prueba de ventaja.")
    for origen in ("red", "azar"):
        r = con.execute("SELECT COUNT(*), AVG(p.wilson_inf - (CASE WHEN f.ficha LIKE '%\"p\": 10%' THEN ? ELSE ? END)), "
                        "SUM(CASE WHEN f.en_vivo IS NOT NULL THEN 1 ELSE 0 END) FROM formas f JOIN pruebas p ON p.forma=f.id "
                        "AND p.tramo='elige' WHERE f.origen=? AND p.n>0", (EQUILIBRIO[10], EQUILIBRIO[15], origen)).fetchone()
        if r[0]:
            lineas.append(f"Origen «{origen}»: {num(r[0], 0)} probadas; Wilson inferior medio {num(100 * (r[1] or 0), 2)} puntos "
                          f"frente al equilibrio; {r[2] or 0} entraron a vivo.")
    for p in (10, 15):
        inf = lab.motor.informe.get(p) if lab and lab.motor else None
        if inf:
            lineas.append(f"Red de mercado a {p} min: usa la {inf['usa']} (red {pct(inf['red']['acierto'])} en "
                          f"{num(inf['red']['n'], 0)}; neurona {pct(inf['neurona']['acierto'])} en {num(inf['neurona']['n'], 0)}, "
                          f"confianza ≥ 0,56 en «elige»).")
    if lab:
        lineas.append(f"Reajuste de redes: {hora(lab.motor.t)}. Marcha: {num(lab.horas_marcha(), 1)} h de las últimas 24; "
                      f"temperatura máxima {num(lab.t_max or 0, 0)} °C; pausas por calor: {lab.pausas_calor}.")
    lineas += extras()
    lineas.append("«Apta en papel» no autoriza dinero: pasa al protocolo de la sección 6 y a su orden. Es papel.")
    return "\n".join(lineas)


def ficha_texto(con, fid):
    r = con.execute("SELECT id, origen, nombre, ficha, estado, situacion, nacida, en_vivo FROM formas WHERE id=?", (fid,)).fetchone()
    if not r:
        return f"No existe la forma F-{fid:04d}."
    fid, origen, nombre, ficha, estado, sit, nacida, en_vivo = r
    p = json.loads(ficha)["p"]
    lineas = [f"{PREFIJO} · F-{fid:04d} · {nombre}", f"Origen: {origen}. Estado: {estado}" + (f" ({sit})" if sit else "") +
              f". Nació: {hora(nacida)}." + (f" En vivo desde: {hora(en_vivo)}." if en_vivo else "")]
    for tramo, n, k, wi in con.execute("SELECT tramo, n, k, wilson_inf FROM pruebas WHERE forma=? ORDER BY tramo", (fid,)):
        if n:
            lineas.append(f"{tramo}: {k} de {n} ({pct(k / n)}), Wilson inferior {pct(wi)}; equilibrio {pct(EQUILIBRIO[p])}.")
    n, k = con.execute("SELECT COUNT(*), COALESCE(SUM(res), 0) FROM senales WHERE forma=? AND res IN (0, 1) AND t>=?",
                       (fid, en_vivo or 0)).fetchone()
    ult = [x for (x,) in con.execute("SELECT res FROM senales WHERE forma=? AND res IN (0, 1) ORDER BY t DESC LIMIT 25", (fid,))]
    if n:
        lineas.append(f"En vivo: {k} de {n} ({pct(k / n)}); últimas {len(ult)}: {sum(1 for x in ult if x)} aciertos.")
    else:
        lineas.append("En vivo: sin apuestas cerradas todavía.")
    abiertas = con.execute("SELECT t, dir FROM senales WHERE forma=? AND res IS NULL ORDER BY t", (fid,)).fetchall()
    for t, d in abiertas[-3:]:
        lineas.append(f"Abierta: {hora(t, '%H:%M')} {'SUBE' if d > 0 else 'BAJA'} a {p} min.")
    return "\n".join(lineas)


def origen_texto(con):
    lineas = [f"{PREFIJO} · rendimiento por origen"]
    for origen, n, nv in con.execute("SELECT origen, COUNT(*), SUM(CASE WHEN en_vivo IS NOT NULL THEN 1 ELSE 0 END) FROM formas "
                                     "GROUP BY origen ORDER BY 2 DESC"):
        nn, kk = con.execute("SELECT COUNT(*), COALESCE(SUM(s.res), 0) FROM senales s JOIN formas f ON f.id=s.forma "
                             "WHERE f.origen=? AND s.res IN (0, 1)", (origen,)).fetchone()
        t = f"«{origen}»: {num(n, 0)} formas, {nv or 0} en vivo alguna vez"
        lineas.append(t + (f"; en vivo {kk} de {nn} ({pct(kk / nn)})." if nn else "; sin apuestas cerradas en vivo."))
    return "\n".join(lineas)


def mejores_texto(con, periodo, temp):
    ahora = int(time.time())
    desde = {"hoy": inicio_dia(ahora), "semana": ahora - 7 * 86400, "todo": None}.get(periodo)
    cv = [x for x in cifras_vivas(con, desde) if x["n"]]
    lineas = [cabecera(con, temp), f"Mejores ({periodo}):"]
    lineas += [linea(i + 1, x) for i, x in enumerate(cv[:10])] or ["Sin apuestas cerradas en ese periodo."]
    return "\n".join(lineas)
