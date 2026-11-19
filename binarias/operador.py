"""Puente entre el centinela (binarias.py) y la sesión de Claude Code que decide las apuestas (PROMPT-OPERADOR.md).
Solo biblioteca estándar. Se ejecuta siempre desde esta carpeta: python -I operador.py <orden>

Órdenes:
  estado                       latido del centinela, cuentas y elección del mes
  esperar                      espera hasta que haya fichas nuevas, toque el informe de las 6:00 o el centinela se caiga
  pendientes                   muestra las fichas sin decisión que aún están en plazo
  decidir <id> aprobar|descartar --confianza X --razon "..."
  informe                      resumen del día anterior (6:00 a 6:00) para el párrafo de Telegram
  telegram "texto"             manda el texto a su Telegram
  arrancar                     lanza la sesión de fondo del operador si no hay otra viva
  ficha-prueba                 deja una ficha de ensayo con 90 s de plazo (no apuesta nada)"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
FICHAS, DECISIONES = os.path.join(AQUI, "fichas"), os.path.join(AQUI, "decisiones")
ESTADO, APUESTAS, SELECCION = (os.path.join(AQUI, x) for x in ("estado.json", "apuestas.jsonl", "seleccion.json"))
LATIDO, PROMPT = os.path.join(AQUI, "operador.latido"), os.path.join(AQUI, "PROMPT-OPERADOR.md")
TG = os.path.join(os.path.dirname(AQUI), "tg_pc.py")
COL = dt.timezone(dt.timedelta(hours=-5))
NOMBRE = "operador binarias"
TASA = 3180.0
# El operador corre en C:\Windows\System32 (carpeta ya confiable para sesiones de fondo) y llama con la ruta completa.
ORDEN = "python -I " + os.path.join(AQUI, "operador.py").replace(os.sep, "/")
CARPETA_SESION = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")


def leer(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defecto


def escribir(ruta, datos):
    tmp = f"{ruta}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    for i in range(10):
        try:
            os.replace(tmp, ruta)
            return
        except PermissionError:
            time.sleep(0.1 * (i + 1))


def latir(accion):
    try:
        escribir(LATIDO, {"t": time.time(), "accion": accion})
    except Exception:
        pass


def ahora():
    """Hora del servidor de Binance, con el desfase que mide el centinela."""
    return time.time() + float(leer(ESTADO, {}).get("desfase", 0.0) or 0.0)


def hora(ts, f="%H:%M:%S"):
    return dt.datetime.fromtimestamp(ts, COL).strftime(f)


def cop(x, signo=False):
    t = f"{x:+,.0f}" if signo else f"{x:,.0f}"
    return "0" if abs(x) < 0.5 else t.replace(",", ".")


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def texto_ficha(f):
    p = f["propuesta"]
    resto = max(0, int(f["limite"] - ahora()))
    m = f.get("mercado", {})
    mov = " · ".join(f"{k} {num(v['pct'], 3)} % ({num(v['sigmas'])} σ)" for k, v in m.items() if isinstance(v, dict))
    otros = "; ".join(f"{x['estrategia']} {x['sentido']} {x['plazo_min']} min" for x in f.get("otras_elegidas", [])) or "ninguna"
    todas = f.get("todas_las_estrategias_en_esta_vela", {})
    cu = f.get("cuenta_CLAUDE", {})
    return "\n".join([
        f"FICHA {f['id']}{' (ENSAYO)' if f.get('ensayo') else ''} · {f.get('simbolo', '')} · vela que cierra {f['cierre']} · decidir antes de {f['limite_txt']} (quedan {resto} s)",
        f"Propuesta: {p['sentido']} {p['plazo_min']} min · {cop(p['monto_cop'])} COP ({num(p['monto_usdt'])} USDT) · {p['estrategia']} · {p.get('detalle', '')}",
        f"Procedimiento del mes: {f.get('procedimiento', '')} · {f.get('historial_del_procedimiento', '')}",
        f"Otras elegidas en esta vela: {otros}",
        f"Todas las estrategias en esta vela: {todas.get('sube', 0)} dicen sube y {todas.get('baja', 0)} dicen baja",
        f"Contexto del día: {f.get('contexto_del_dia')}",
        f"Mercado: {mov}",
        f"Volatilidad 15 min / 4 h: {num(m.get('volatilidad 15 min / 4 h', 0))} · vela de 1 min más grande de las últimas 5 / media de la hora: "
        f"{num(m.get('vela de 1 min más grande de las últimas 5 / media de la hora', 0))}",
        f"Precio {f.get('precio')} (dato de hace {num(f.get('edad_precio_s', 0), 1)} s)",
        f"Cuenta CLAUDE: {cop(cu.get('saldo_cop', 0))} COP · {cu.get('apuestas_hoy', 0)} apuestas hoy · {cu.get('aciertos', 0)} aciertos y {cu.get('fallos', 0)} fallos en total",
        f"Decida con: {ORDEN} decidir {f['id']} aprobar|descartar --confianza 0.xx --razon \"...\""])


def fichas_abiertas():
    """Fichas sin decisión y dentro del plazo. Sin marcas compartidas: un proceso viejo de `esperar` no puede tapar al nuevo."""
    out = []
    if not os.path.isdir(FICHAS):
        return out
    t = ahora()
    for fn in sorted(os.listdir(FICHAS)):
        if not fn.endswith(".json"):
            continue
        if os.path.exists(os.path.join(DECISIONES, fn)):
            continue
        f = leer(os.path.join(FICHAS, fn))
        if f and f.get("limite", 0) >= t:
            out.append(f)
    return out


def esperar():
    os.makedirs(FICHAS, exist_ok=True)
    os.makedirs(DECISIONES, exist_ok=True)
    t_lat = 0
    while True:
        if time.time() - t_lat > 30:
            latir("esperando fichas")
            t_lat = time.time()
        abiertas = fichas_abiertas()
        if abiertas:
            print(f"{len(abiertas)} FICHA(S) POR DECIDIR. Véalas con: {ORDEN} pendientes")
            return
        hc = dt.datetime.now(COL)
        if 6 <= hc.hour < 12 and not os.path.exists(os.path.join(DECISIONES, f"informe-{hc:%Y-%m-%d}.hecho")):
            print(f"INFORME: ya son las 6:00 en Colombia. Ejecute {ORDEN} informe y mande el párrafo con telegram.")
            return
        lat = leer(ESTADO, {}).get("latido", 0)
        marca = os.path.join(DECISIONES, "centinela-caido.aviso")
        if time.time() - lat > 300:
            if not os.path.exists(marca):
                open(marca, "w").close()
                print(f"CENTINELA CAÍDO: no late desde las {hora(lat)}. Avise una vez por telegram y vuelva a esperar.")
                return
        elif os.path.exists(marca):
            os.remove(marca)
        time.sleep(0.5)


def pendientes():
    """Lo que el operador tiene que atender ahora: fichas dentro del plazo, el informe de las 6:00 o el centinela caído."""
    fs = fichas_abiertas()
    latir("leyendo fichas")
    for f in fs:
        print(texto_ficha(f) + "\n")
    if fs:
        return
    print("No hay fichas por decidir dentro del plazo.")
    hc = dt.datetime.now(COL)
    if 6 <= hc.hour < 12 and not os.path.exists(os.path.join(DECISIONES, f"informe-{hc:%Y-%m-%d}.hecho")):
        print(f"INFORME pendiente: ejecute {ORDEN} informe y mande el párrafo con {ORDEN} telegram \"...\"")
    lat = leer(ESTADO, {}).get("latido", 0)
    if time.time() - lat > 300:
        print(f"CENTINELA CAÍDO: no late desde las {hora(lat)}. Si no lo ha avisado, avise una vez con {ORDEN} telegram \"...\"")


def decidir(args):
    if len(args) < 2 or args[1] not in ("aprobar", "descartar"):
        print("Uso: decidir <id> aprobar|descartar --confianza X --razon \"...\"")
        return 2
    fid, accion = args[0], args[1]
    conf, razon = None, ""
    if "--confianza" in args:
        try:
            conf = float(args[args.index("--confianza") + 1].replace(",", "."))
        except (ValueError, IndexError):
            conf = None
    if "--razon" in args:
        razon = " ".join(args[args.index("--razon") + 1:])[:300]
    f = leer(os.path.join(FICHAS, fid + ".json"))
    if not f:
        print(f"No existe la ficha {fid}.")
        return 1
    t = ahora()
    os.makedirs(DECISIONES, exist_ok=True)
    escribir(os.path.join(DECISIONES, fid + ".json"), {"id": fid, "decision": accion, "confianza": conf, "razon": razon, "t": round(t, 2)})
    latir(f"decidió {accion}")
    print(("TARDE: llegó " + num(t - f["limite"], 1) + " s después del límite; queda «tarde» y no se apuesta.") if t > f["limite"]
          else f"Decisión guardada: {accion} con {num(f['limite'] - t, 1)} s de margen.")
    return 0


def estado():
    e = leer(ESTADO, {})
    latir("revisó el estado")
    if not e:
        print("No hay estado del centinela.")
        return
    print(f"Centinela: latido hace {round(time.time() - e.get('latido', 0))} s · {e.get('motivo', '')}")
    for k, c in e.get("cuentas", {}).items():
        n = c["aciertos"] + c["fallos"] + c["empates"]
        print(f"   {k}: {cop(c['saldo'])} COP · {n} apuestas · {c['aciertos']} aciertos{' · quebrada' if c.get('quebrada') else ''}")
    s = leer(SELECCION, {})
    p = s.get("procedimiento")
    print(f"   Procedimiento de {s.get('mes')}: " + (f"{p['nombre']} ({p['aciertos']}/{p['apuestas']} a ciegas en 12 meses; apuesta "
                                                    f"{num(100 * p['fraccion'])} % del saldo, mínimo 5 USDT)" if p else "ninguno"))
    for sim in ("BTCUSDT", "ETHUSDT"):
        print(f"   Reglas del mes {sim}: " + ("; ".join(x["nombre"] for x in s.get("reglas", {}).get(sim, [])) or "ninguna"))
    print(f"   Fichas por decidir ahora: {len(fichas_abiertas())}")


def informe():
    hc = dt.datetime.now(COL)
    fin = int(dt.datetime(hc.year, hc.month, hc.day, 6, tzinfo=COL).timestamp())
    ini = fin - 86400
    filas = []
    if os.path.exists(APUESTAS):
        for ln in open(APUESTAS, encoding="utf-8"):
            x = json.loads(ln)
            if ini <= x["t"] < fin:
                filas.append(x)
    e = leer(ESTADO, {})
    print(f"Informe del {hora(ini, '%d/%m %H:%M')} al {hora(fin, '%d/%m %H:%M')} (hora de Colombia)")
    for k in ("REGLA", "CLAUDE", "AZAR", "BTC FIJO"):
        fk = [x for x in filas if x["cuenta"] == k]
        w = sum(1 for x in fk if x["res"] > 0)
        g = sum(x["ganancia"] for x in fk)
        saldo = e.get("cuentas", {}).get(k, {}).get("saldo", 0)
        print(f"   {k}: {len(fk)} apuestas, {w} aciertos{f' ({100 * w / len(fk):.1f} %)' if fk else ''}, resultado {cop(g, True)} COP, saldo actual {cop(saldo)} COP")
    regla = {x["t"]: x for x in filas if x["cuenta"] == "REGLA"}
    cuentas = {"aprobada": 0, "descartada": 0, "sin decisión": 0, "tarde": 0, "otra": 0}
    desc_ok = desc_n = 0
    for fn in os.listdir(FICHAS) if os.path.isdir(FICHAS) else []:
        if not fn.endswith(".json") or fn.startswith("PRUEBA"):
            continue
        f = leer(os.path.join(FICHAS, fn), {})
        B = f.get("limite", 0) - 5
        if not ini <= B < fin:
            continue
        d = leer(os.path.join(DECISIONES, fn), None)
        if not d:
            cuentas["sin decisión"] += 1
        elif d["t"] > f["limite"]:
            cuentas["tarde"] += 1
        elif d["decision"] == "aprobar":
            cuentas["aprobada"] += 1
        else:
            cuentas["descartada"] += 1
            if B in regla:
                desc_n += 1
                desc_ok += regla[B]["res"] <= 0
    print("   Fichas: " + ", ".join(f"{v} {k}" for k, v in cuentas.items() if v))
    if desc_n:
        print(f"   De las {desc_n} descartadas que la REGLA sí apostó, la regla falló {desc_ok}: descartarlas {'ayudó' if desc_ok * 2 > desc_n else 'no ayudó'}.")
    os.makedirs(DECISIONES, exist_ok=True)
    open(os.path.join(DECISIONES, f"informe-{hc:%Y-%m-%d}.hecho"), "w").close()
    latir("hizo el informe")


def telegram(texto):
    if not os.path.exists(TG):
        print("No está tg_pc.py: no se puede mandar.")
        return 1
    os.makedirs(os.path.join(AQUI, "alertas"), exist_ok=True)
    ruta = os.path.join(AQUI, "alertas", f"op-{int(time.time() * 1000)}.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("[Claude · operador de binarias]\n" + texto)
    r = subprocess.run([sys.executable, "-I", TG, ruta], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    ok = "ok" in (r.stdout or "")
    if ok:
        os.remove(ruta)
    print("Mandado." if ok else "No se confirmó el envío: " + (r.stdout or r.stderr).strip()[-200:])
    latir("mandó un mensaje")
    return 0 if ok else 1


def arrancar():
    exe = shutil.which("claude") or os.path.expanduser(r"~\.local\bin\claude.exe")
    sin_ventana = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run([exe, "agents", "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                           creationflags=sin_ventana)
        vivos = [a for a in json.loads(r.stdout or "[]") if a.get("name") == NOMBRE]
    except Exception as ex:
        print(f"No se pudo listar las sesiones ({type(ex).__name__}); no lanzo otra por si ya hay una.")
        return 1
    lat = leer(LATIDO, {}).get("t", 0)
    if vivos and time.time() - lat < 180:
        print(f"Ya hay un operador vivo: {vivos[0].get('id')} ({vivos[0].get('state')}), visto hace {round(time.time() - lat)} s.")
        return 0
    for a in vivos:  # listada pero sin latido (por ejemplo, tras reiniciar el equipo): se cierra y se lanza otra
        subprocess.run([exe, "stop", a["id"]], capture_output=True, text=True, timeout=60, creationflags=sin_ventana)
        print(f"Cerré la sesión {a['id']}, que no daba señales desde hace {round(time.time() - lat)} s.")
    prompt = open(PROMPT, encoding="utf-8").read().replace("python -I operador.py", ORDEN)
    cmd = [exe, "Empiece el ciclo de trabajo de sus instrucciones de operador.", "--bg", "-n", NOMBRE,
           "--permission-mode", "dontAsk", "--tools", "Bash", "--allowedTools", f"Bash({ORDEN} *)",
           "--strict-mcp-config", "--effort", "medium", "--append-system-prompt", prompt]
    r = subprocess.run(cmd, cwd=CARPETA_SESION, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                       creationflags=sin_ventana)
    print((r.stdout or "").strip()[-400:] or (r.stderr or "").strip()[-400:])
    return r.returncode


def ficha_prueba():
    t = ahora()
    f = {"id": f"PRUEBA-{int(t)}", "ensayo": True, "simbolo": "BTCUSDT", "cierre": hora(t + 85), "limite": t + 90, "limite_txt": hora(t + 90),
         "creada": round(t, 1), "precio": 0, "edad_precio_s": 0,
         "procedimiento": "ensayo", "historial_del_procedimiento": "",
         "propuesta": {"sentido": "SUBE", "plazo_min": 10, "estrategia": "ENSAYO (no se apuesta)", "detalle": "",
                       "monto_cop": 15900, "monto_usdt": 5.0},
         "otras_elegidas": [], "todas_las_estrategias_en_esta_vela": {"sube": 0, "baja": 0}, "contexto_del_dia": "ensayo",
         "mercado": {}, "cuenta_CLAUDE": {}}
    os.makedirs(FICHAS, exist_ok=True)
    escribir(os.path.join(FICHAS, f["id"] + ".json"), f)
    print(f"Ficha de ensayo {f['id']} con límite {f['limite_txt']}.")


def main():
    a = sys.argv[1:]
    orden = a[0] if a else ""
    if orden == "esperar":
        esperar()
    elif orden == "pendientes":
        pendientes()
    elif orden == "decidir":
        return decidir(a[1:])
    elif orden == "estado":
        estado()
    elif orden == "informe":
        informe()
    elif orden == "telegram":
        return telegram(" ".join(a[1:]))
    elif orden == "arrancar":
        return arrancar()
    elif orden == "ficha-prueba":
        ficha_prueba()
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
