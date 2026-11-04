"""Semáforo papel → real para BTCUSDT, v3.3 (04/11/2026). Desde la v3.3, su regla del 76 % (P17): el SÍ solo pasa a real
si además las últimas 25 apuestas de papel del núcleo ya cerradas acertaron 19 o más; si no, el aviso le recuerda esperar.
Probada en C9e: el real se enciende pocas veces (81 apuestas en 2024-sep 2026) y no acierta más que el SÍ solo.
Desde el 04/11 a las 13:10, la foto de cada SÍ o NO lleva las cinco líneas (graficas.cinco_lineas, idéntica a Pulso) y el
SÍ real trae los pasos exactos del toque en la app; el toque es suyo (los Contratos de Evento no tienen API).
Antes, v3.2 (04/11/2026): su regla «el real solo cuando el papel de hoy esté sumando»,
con el filtro del interés abierto (P15). Desde la v3.2, cada SÍ o NO llega como foto con las seis líneas (graficas.py,
idéntica a Pulso píxel a píxel), cada SÍ cerrado trae su comprobante en PDF con enlaces a las velas oficiales de Binance
y a las 00:15 llega el resumen del papel del día anterior (comprobantes.py). Si existe ~/.config/binarias/canal, los SÍ y
NO también se publican en el canal para la gente.
Corre en la caja T95H y en el teléfono, como hilo del avisador (avisos.py).

Su regla (03/11, 23:58): «no es que sean solo en días verdes, solo en días que esté sumando directamente en nuestras
operaciones, esté sí o sí sumando, generando dinero». Probada a ciegas en C9 (cuant/c9_mejoras.py; la variante D1 se
eligió en 2021-2023): en 2024-sep 2026 acierta 54,8 % frente a 54,4 % del núcleo, con 2,1 apuestas al día y caída máxima de
0,46 M COP frente a 1,79 M de apostar siempre. No sube el acierto: recorta el riesgo.
- Señal de papel (núcleo): «ruptura al revés» en BTC. En cada decisión de 10 min, si la última vela de 5 min cierra por
  encima del máximo de las 20 anteriores, BAJA; si cierra por debajo del mínimo, SUBE. Binaria de 10 min, entrada 60 s
  tarde, empate = fallo.
- SÍ OPERAR: el neto del papel de hoy (día de Colombia; +0,85 por acierto, −1 por fallo, solo apuestas ya cerradas) es
  mayor que 0, ningún SÍ ha perdido hoy y el interés abierto de futuros no sube (P14b/P15: cambio en 15 min de hasta
  +0,022 %, con la instantánea publicada 5 min antes de la decisión, que Binance publica unos 105 s después de su hora).
  Si no, NO OPERAR (solo papel), con el motivo. La primera pérdida de un SÍ lo apaga hasta mañana.
  C9c y P15: en 2024-sep 2026 el SÍ acierta 55,5 % con 1,8 apuestas al día (su regla sola, 54,8 %; el núcleo, 54,4 %);
  con interés abierto que sube, la devolución da 53,3 %. Sin el dato del interés abierto, la señal va como NO.
- Dinero real: solo si existe el archivo REAL_AUTORIZADO en esta carpeta, que se crea con su orden expresa. Sin él, el SÍ
  queda en papel (espejo del real) y el mensaje lo dice. 5 USDT, sin apalancamiento. Ningún código apuesta: él toca.
- Cada apuesta guarda también el resultado con el índice de precio, que es con el que Binance liquida los Contratos de
  Evento (C9b: en 2024-sep 2026 cambia el 3,8 % de los resultados). Solo se registra; decide la medida validada.
Uso: python3 -I semaforo.py · Parar: crear PARAR.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import avisos  # noqa: E402

try:  # sin gráficas ni comprobantes, el semáforo sigue avisando con texto
    import comprobantes  # noqa: E402
    import graficas  # noqa: E402
except Exception:
    comprobantes = graficas = None

ESTADO = os.path.join(AQUI, "semaforo.json")
REGISTRO = os.path.join(AQUI, "semaforo.log")
PARAR = os.path.join(AQUI, "PARAR")
AUTORIZADO = os.path.join(AQUI, "REAL_AUTORIZADO")
GRAFICA = os.path.join(AQUI, "grafica_ultima.png")
COMPROB = os.path.join(AQUI, "comprobantes")
FAPI = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m"
FIDX = "https://fapi.binance.com/fapi/v1/indexPriceKlines?pair=BTCUSDT&interval=1m"
FOI = "https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=5m&limit=12"
VENTANA_76, MIN_76 = 25, 19  # su regla del 76 % (P17): 19 de las últimas 25 de papel
UMBRAL_OI = 0.00022  # mediana de dic 2021-2023 con el margen de P14b (cuant/c9c_interes.py, margen 600 s en el archivo)
H = {"User-Agent": "binarias-semaforo"}
VENTANA, PLAZO, PAGO = 100, 600, 0.85
RETRASO = 60  # el papel se mide entrando 60 s tarde, como él toca a mano (congruente con el banco)
COL = dt.timezone(dt.timedelta(hours=-5))


def log(msg):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now(COL):%Y-%m-%d %H:%M:%S} {msg}\n")


def leer():
    try:
        return json.load(open(ESTADO, encoding="utf-8"))
    except Exception:
        return {"apuestas": []}


def guardar(e):
    tmp = ESTADO + ".tmp"
    json.dump(e, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, ESTADO)


def _bajar(url):
    x = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=20).read())
    ahora = time.time() * 1000
    return [(int(k[0]) // 1000, float(k[2]), float(k[3]), float(k[4])) for k in x if int(k[6]) < ahora]  # (t, alto, bajo, cierre)


def velas(desde_ms=None, limite=1500):
    return _bajar(FAPI + f"&limit={limite}" + (f"&startTime={desde_ms}" if desde_ms else ""))


def velas_ohlc(limite=170):
    """Velas de 1 min de futuros con apertura, para la gráfica: (t, apertura, máximo, mínimo, cierre)."""
    x = json.loads(urllib.request.urlopen(urllib.request.Request(FAPI + f"&limit={limite}", headers=H), timeout=20).read())
    ahora = time.time() * 1000
    return [(int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4])) for k in x if int(k[6]) < ahora]


def velas_indice(limite=60):
    return _bajar(FIDX + f"&limit={limite}")


def cambio_interes(t_dec):
    """Cambio del interés abierto en 15 min: instantánea más reciente con hora <= t_dec - 300 frente a la de <= t_dec - 1200."""
    x = json.loads(urllib.request.urlopen(urllib.request.Request(FOI, headers=H), timeout=15).read())
    pts = sorted((int(k["timestamp"]) // 1000, float(k["sumOpenInterest"])) for k in x)
    a = [p for p in pts if p[0] <= t_dec - 300]
    b = [p for p in pts if p[0] <= t_dec - 1200]
    if not a or not b or t_dec - 300 - a[-1][0] > 600 or t_dec - 1200 - b[-1][0] > 600 or b[-1][1] <= 0:
        return None
    return a[-1][1] / b[-1][1] - 1


def historial(dias):
    out, desde = [], int((time.time() - dias * 86400) * 1000)
    while True:
        x = velas(desde)
        if not x:
            break
        out += x
        desde = (x[-1][0] + 60) * 1000
        if len(x) < 1400:
            break
    vistos, limpio = set(), []
    for v in out:
        if v[0] not in vistos:
            vistos.add(v[0])
            limpio.append(v)
    return limpio


def senal(v1, t_dec):
    """Ruptura al revés en la decisión t_dec (fin de la vela de 1 min que cierra en múltiplo de 600 s)."""
    por5 = {}
    for t, hi, lo, c in v1:
        if t + 60 > t_dec:
            continue
        k = t // 300
        a = por5.setdefault(k, [0, -1e18, 1e18, 0.0, 0])
        a[1], a[2], a[3], a[4] = max(a[1], hi), min(a[2], lo), c, a[4] + 1
    llaves = sorted(k for k, a in por5.items() if a[4] == 5)
    if len(llaves) < 21 or (llaves[-1] + 1) * 300 != t_dec:
        return 0
    ult = por5[llaves[-1]]
    prev = [por5[k] for k in llaves[-21:-1]]
    if ult[3] > max(p[1] for p in prev):
        return -1
    if ult[3] < min(p[2] for p in prev):
        return 1
    return 0


def cierre_en(v1, t_fin):
    for t, hi, lo, c in v1:
        if t + 60 == t_fin:
            return c
    return None


def sembrar(e):
    """Con las velas de los últimos 9 días, rehace las apuestas de papel (también las de hoy, si se reinicia a media jornada)."""
    v1 = historial(9)
    hechas = {a["t"] for a in e["apuestas"]}
    nuevas = 0
    for i, (t, hi, lo, c) in enumerate(v1):
        t_dec = t + 60
        if t_dec % 600 or t_dec in hechas:
            continue
        s = senal(v1[max(0, i - 130):i + 1], t_dec)
        if not s:
            continue
        ent = cierre_en(v1, t_dec + RETRASO)
        sal = cierre_en(v1, t_dec + RETRASO + PLAZO)
        if ent is None or sal is None:
            continue
        res = 1 if (sal - ent) * s > 0 else 0
        e["apuestas"].append({"t": t_dec, "dir": s, "entrada": ent, "salida": sal, "res": res, "semilla": True})
        nuevas += 1
    e["apuestas"].sort(key=lambda a: a["t"])
    return nuevas


def acierto_reciente(e, antes_de):
    cerradas = [a for a in e["apuestas"] if a.get("res") is not None and a["t"] + RETRASO + PLAZO <= antes_de]
    ult = cerradas[-VENTANA:]
    return (sum(a["res"] for a in ult) / len(ult) if ult else 0.0), len(ult)


def papel_de_hoy(e, ini_dia, ahora):
    """Neto del papel del núcleo en el día de Colombia, solo con apuestas ya cerradas: (neto, aciertos, cerradas)."""
    hoy = [a for a in e["apuestas"] if a["t"] >= ini_dia and a.get("res") is not None and a["t"] + RETRASO + PLAZO <= ahora]
    return sum(PAGO if a["res"] else -1.0 for a in hoy), sum(a["res"] for a in hoy), len(hoy)


def papel_reciente(e, ahora):
    """Aciertos de las últimas 25 apuestas de papel del núcleo ya cerradas: (aciertos, cerradas)."""
    cerradas = [a for a in e["apuestas"] if a.get("res") is not None and a["t"] + RETRASO + PLAZO <= ahora]
    ult = cerradas[-VENTANA_76:]
    return sum(a["res"] for a in ult), len(ult)


def autorizado():
    return os.path.exists(AUTORIZADO)


def sentido(d):
    return "SUBE" if d == 1 else "BAJA"


def unidades(x):
    return f"{x:+.2f}".replace(".", ",")


def avisar(texto):
    if avisos.ROL == "telefono" and avisos.caja_late():
        log("la caja late: ella avisa")
        return True
    return avisos.enviar(texto)


def avisar_archivo(ruta, texto, metodo, campo, texto_canal=None):
    """Foto o PDF a su Telegram; el teléfono calla si la caja late. Con texto_canal, también al canal para la gente."""
    if avisos.ROL == "telefono" and avisos.caja_late():
        log("la caja late: ella avisa")
        return True
    ok = avisos.enviar_archivo(ruta, texto, metodo, campo)
    c = avisos.canal() if texto_canal else None
    if c:
        avisos.enviar_archivo(ruta, texto_canal, metodo, campo, chat=c)
    return ok


def main():
    e = leer()
    if e.get("medida") != "60s":  # el registro viejo medía al cierre: se rehace con la medida nueva
        e["apuestas"], e["medida"] = [], "60s"
    n = sembrar(e)
    guardar(e)
    log(f"semáforo v3.3 (su regla + interés abierto + su 76 % para el real, con fotos y comprobantes) en marcha · rol {avisos.ROL} · {len(e['apuestas'])} apuestas de papel ({n} sembradas) · real autorizado: {autorizado()}")
    while not os.path.exists(PARAR):
        try:
            ahora = time.time()
            hoy = dt.datetime.fromtimestamp(ahora, COL).strftime("%Y-%m-%d")
            ini_dia = dt.datetime.strptime(hoy, "%Y-%m-%d").replace(tzinfo=COL).timestamp()
            # 1) cambio de día: el SÍ arranca apagado (papel en 0) y se le recuerda la regla
            if e.get("hoy", {}).get("dia") != hoy:
                acc, n_ult = acierto_reciente(e, ini_dia)
                e["hoy"] = {"dia": hoy, "perdio": False}
                guardar(e)
                txt = (f"Binarias BTC, {hoy} [{avisos.ETIQUETA}]: cada señal llega con SÍ o NO. SÍ solo cuando el papel de hoy "
                       f"vaya sumando y el interés abierto no esté subiendo; la primera pérdida del SÍ lo apaga hasta mañana. "
                       f"El real, solo con el papel reciente en 76 % o más ({MIN_76} de las últimas {VENTANA_76}); nunca apalancamiento. "
                       + ("Dinero real autorizado: 5 USDT, sin apalancamiento." if autorizado() else "Sigue en papel: el dinero real espera su orden.")
                       + f" Últimas {n_ult} de papel: {acc * 100:.1f} %.".replace(".", ",", 1))
                avisar(txt)
                log(txt)
            # 1b) a las 00:15, el resumen del papel del día anterior (ya cerradas sus últimas apuestas)
            ayer = (dt.datetime.fromtimestamp(ahora, COL) - dt.timedelta(days=1)).strftime("%Y-%m-%d")
            if comprobantes and ahora - ini_dia >= 900 and e.get("resumen_enviado") != ayer:
                e["resumen_enviado"] = ayer
                guardar(e)
                try:
                    del_dia = [a for a in e["apuestas"] if ini_dia - 86400 <= a["t"] < ini_dia]
                    cerr = [a for a in del_dia if a.get("res") is not None]
                    if cerr:
                        os.makedirs(COMPROB, exist_ok=True)
                        ruta = os.path.join(COMPROB, f"{ayer}_resumen.pdf")
                        dia_txt = dt.datetime.strptime(ayer, "%Y-%m-%d").strftime("%d/%m/%Y")
                        with open(ruta, "wb") as f:
                            f.write(comprobantes.resumen_dia(del_dia, dia_txt, avisos.ETIQUETA, RETRASO, PLAZO))
                        neto_d = sum(PAGO if a["res"] else -1.0 for a in cerr)
                        avisar_archivo(ruta, f"Resumen del papel del {dia_txt} [{avisos.ETIQUETA}]: {len(cerr)} señales, {sum(a['res'] for a in cerr)} acertadas, "
                                             f"neto {unidades(neto_d)} apuestas. Cada fila abre en Binance su vela de entrada.", "sendDocument", "document")
                except Exception as ex:
                    log(f"resumen no enviado ({type(ex).__name__}: {ex})")
            # 2) decisiones cada 10 min (se espera 3 s tras el cierre de la vela)
            t_dec = int(ahora // 600 * 600)
            if ahora - t_dec >= 3 and not any(a["t"] == t_dec for a in e["apuestas"]) and e.get("ultima_revisada") != t_dec:
                v1 = velas(limite=160)
                e["ultima_revisada"] = t_dec
                s = senal(v1, t_dec) if v1 and v1[-1][0] + 60 == t_dec else 0
                if s:
                    entrada = v1[-1][3]  # precio del aviso; la medida de papel toma el cierre 60 s después
                    neto, k, n_hoy = papel_de_hoy(e, ini_dia, ahora)
                    perdio = bool(e.get("hoy", {}).get("perdio"))
                    try:
                        doi = cambio_interes(t_dec)
                    except Exception as ex:
                        doi = None
                        log(f"interés abierto sin dato ({type(ex).__name__})")
                    oi_ok = doi is not None and doi <= UMBRAL_OI
                    si = neto > 0 and not perdio and oi_ok
                    k25, n25 = papel_reciente(e, ahora)
                    racha_ok = n25 >= VENTANA_76 and k25 >= MIN_76
                    real = si and autorizado() and racha_ok
                    e["apuestas"].append({"t": t_dec, "dir": s, "aviso": entrada, "entrada": None, "salida": None, "res": None,
                                          "si": si, "real": real, "neto_previo": round(neto, 2),
                                          "doi": None if doi is None else round(doi, 6), "filtro_oi": oi_ok,
                                          "reciente": f"{k25}/{n25}"})
                    oi_txt = "sin dato del interés abierto" if doi is None else (
                        f"interés abierto {doi * 100:+.3f} % en 15 min ({'no sube' if oi_ok else 'sube: la devolución falla más'})".replace(".", ","))
                    vence = dt.datetime.fromtimestamp(t_dec + PLAZO, COL).strftime("%H:%M")
                    if si:
                        if real:
                            cola = (f"Toque ya en la app: Futuros → Contratos de Evento → BTCUSDT → 10 min → {sentido(s)} → 5 USDT "
                                    "(tope del 16 % del saldo), sin apalancamiento.")
                        elif not autorizado():
                            cola = "En papel: el dinero real espera su orden."
                        else:
                            cola = (f"En papel: el real espera su 76 % (papel reciente {k25} de {n25}; hacen falta {MIN_76} de {VENTANA_76}). "
                                    "Espere; sin apalancamiento.")
                        txt = (f"SÍ OPERAR{' · REAL' if real else ''} [{avisos.ETIQUETA}] · BTC {sentido(s)} a 10 min · precio {avisos.precio(entrada)} · vence {vence} · "
                               f"papel de hoy {unidades(neto)} ({k} de {n_hoy} acertadas) · {oi_txt}. " + cola)
                    else:
                        motivos = []
                        if perdio:
                            motivos.append("el SÍ ya perdió hoy")
                        elif neto <= 0:
                            motivos.append(f"el papel de hoy va {unidades(neto)} ({k} de {n_hoy} acertadas)")
                        if not oi_ok:
                            motivos.append(oi_txt)
                        txt = f"NO OPERAR [{avisos.ETIQUETA}] · BTC {sentido(s)} a 10 min solo en papel · {' y '.join(motivos)}. Espere."
                    enviado = False
                    if graficas:
                        try:
                            vg = [x for x in velas_ohlc(170) if x[0] + 60 <= t_dec][-150:]
                            s5 = graficas.cinco_lineas(vg)
                            if s5:
                                with open(GRAFICA, "wb") as f:
                                    f.write(graficas.grafica(vg, s5))
                                pie = txt + "\nSus cinco líneas en 1 min (futuros): " + graficas.lectura(vg, s5) + "."
                                canal_txt = (("SÍ OPERAR" if si else "NO OPERAR") + f" · BTC {sentido(s)} a 10 min · vence {vence}"
                                             + ("" if si else ", solo en papel") + ". Señal: ruptura de 20 velas de 5 min al revés.")
                                enviado = avisar_archivo(GRAFICA, pie, "sendPhoto", "photo", canal_txt)
                        except Exception as ex:
                            log(f"gráfica no enviada ({type(ex).__name__}: {ex})")
                    if not enviado:
                        avisar(txt)
                    log(f"señal {sentido(s)} a las {dt.datetime.fromtimestamp(t_dec, COL):%H:%M} · {'SÍ' if si else 'NO'} · real {real} · papel de hoy {neto:+.2f} · interés abierto {doi}")
                guardar(e)
            # 3) cierres
            abiertas = [a for a in e["apuestas"] if a.get("res") is None and a["t"] + RETRASO + PLAZO + 3 <= ahora]
            if abiertas:
                v1 = velas(limite=60)
                try:
                    vi = velas_indice(60)
                except Exception:
                    vi = []
                for a in abiertas:
                    ent = cierre_en(v1, a["t"] + RETRASO)
                    sal = cierre_en(v1, a["t"] + RETRASO + PLAZO)
                    if ent is None or sal is None:
                        if ahora - a["t"] > 3600:
                            a["res"] = 0
                            a["salida"] = None
                        continue
                    a["entrada"], a["salida"], a["res"] = ent, sal, 1 if (sal - ent) * a["dir"] > 0 else 0
                    ie, isal = cierre_en(vi, a["t"] + RETRASO), cierre_en(vi, a["t"] + RETRASO + PLAZO)
                    if ie is not None and isal is not None:
                        a["res_indice"] = 1 if (isal - ie) * a["dir"] > 0 else 0
                        a["indice_entrada"], a["indice_salida"] = ie, isal
                    if a.get("si"):
                        msg = (f"Resultado del SÍ [{avisos.ETIQUETA}]: {'ACIERTO' if a['res'] else 'FALLO'} · BTC {sentido(a['dir'])} "
                               f"{avisos.precio(a['entrada'])} → {avisos.precio(sal)}"
                               + ("" if a.get("real") else " (en papel)") + ".")
                        mismo_dia = dt.datetime.fromtimestamp(a["t"], COL).strftime("%Y-%m-%d") == e.get("hoy", {}).get("dia")
                        if not a["res"] and mismo_dia and not e["hoy"].get("perdio"):
                            e["hoy"]["perdio"] = True
                            msg += " Primera pérdida del SÍ: queda apagado hasta mañana; sigue el papel."
                        doc = False
                        if comprobantes:
                            try:
                                os.makedirs(COMPROB, exist_ok=True)
                                ruta = os.path.join(COMPROB, dt.datetime.fromtimestamp(a["t"], COL).strftime("%Y-%m-%d_%H%M") + "_SI.pdf")
                                with open(ruta, "wb") as f:
                                    f.write(comprobantes.comprobante(a, avisos.ETIQUETA, RETRASO, PLAZO))
                                doc = avisar_archivo(ruta, msg + " Comprobante adjunto: sus enlaces abren en Binance las velas oficiales de ese minuto.",
                                                     "sendDocument", "document")
                            except Exception as ex:
                                log(f"comprobante no enviado ({type(ex).__name__}: {ex})")
                        if not doc:
                            avisar(msg)
                    log(f"cierre {dt.datetime.fromtimestamp(a['t'], COL):%H:%M}: {'acierto' if a['res'] else 'fallo'}"
                        f" · índice {a.get('res_indice', '–')} · {'SÍ' if a.get('si') else 'papel'}")
                e["apuestas"] = e["apuestas"][-3000:]
                guardar(e)
        except Exception as ex:
            log(f"error: {type(ex).__name__}: {ex}")
            time.sleep(10)
        time.sleep(2)
    log("PARAR: salgo")


if __name__ == "__main__":
    main()
