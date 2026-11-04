"""Auditor del papel con los archivos oficiales de Binance (04/11/2026).

Rehace un día de Colombia del núcleo y del SÍ o NO con las velas de 1 min de futuros y el interés abierto que Binance
publica en data.binance.vision (los mismos datos con que se probó el plan), usando las funciones del propio semáforo
(dispositivos/semaforo.py: senal, cierre_en y sus constantes). Sirve para dos cosas:
- comprobar, señal por señal, que la caja anotó lo mismo (--semaforo RUTA_A_semaforo.json);
- que el agente de la nube, que no puede usar la API de Binance (responde 451 a los servidores de EE. UU.), revise el papel
  con datos oficiales y le escriba el resultado.
Binance publica cada archivo diario al terminar el día UTC; un día de Colombia acaba a las 05:00 UTC del siguiente, así que
sin fecha se audita el último día de Colombia que ya tiene todos sus archivos.
El interés abierto del archivo está marcado 5 min antes que el del servicio en vivo (medido el 02/11): por eso aquí se mira
con 600 s y 1.500 s de margen, que equivalen a los 300 s y 1.200 s que usa la caja (P14b).
Uso: python -I auditor_dia.py [AAAA-MM-DD] [--semaforo RUTA] [--cache CARPETA] [--corto]
"""
import csv
import datetime as dt
import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
for _c in (os.path.join(os.path.dirname(AQUI), "dispositivos"), AQUI):
    if os.path.exists(os.path.join(_c, "semaforo.py")):
        sys.path.insert(0, _c)
        break
import semaforo as S  # noqa: E402

COL = dt.timezone(dt.timedelta(hours=-5))
URL = "https://data.binance.vision/data/futures/um/daily/{tipo}/BTCUSDT/{sub}BTCUSDT-{nombre}-{dia}.zip"


def bajar(tipo, dia, cache):
    """Filas del CSV diario (klines de 1 min o metrics) de un día UTC; None si Binance aún no lo publicó."""
    nombre, sub = ("1m", "1m/") if tipo == "klines" else ("metrics", "")
    ruta = os.path.join(cache, f"BTCUSDT-{nombre}-{dia}.zip")
    if not os.path.exists(ruta):
        url = URL.format(tipo=tipo, sub=sub, nombre=nombre, dia=dia)
        try:
            datos = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "binarias-auditor"}), timeout=90).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        with open(ruta + ".tmp", "wb") as f:
            f.write(datos)
        os.replace(ruta + ".tmp", ruta)
    with zipfile.ZipFile(ruta) as z:
        return list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")))


def velas_y_interes(dia_col, cache):
    """Velas (t, máximo, mínimo, cierre) e interés abierto [(t, valor)] para el día de Colombia; None si falta un archivo."""
    utc = [dia_col, dia_col + dt.timedelta(days=1)]
    v1, oi = {}, {}
    for d in utc:
        k = bajar("klines", d.isoformat(), cache)
        m = bajar("metrics", d.isoformat(), cache)
        if k is None or m is None:
            return None
        for r in k:
            if r and r[0][:1].isdigit():
                v1[int(r[0]) // 1000] = (int(r[0]) // 1000, float(r[2]), float(r[3]), float(r[4]))
        for r in m:
            if len(r) > 2 and r[0][:1].isdigit():
                t = int(dt.datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
                oi[t] = float(r[2])
    return [v1[t] for t in sorted(v1)], sorted(oi.items())


def cambio_interes(oi, t_dec):
    """Como semaforo.cambio_interes, con el margen del archivo: instantánea <= t_dec − 600 frente a la de <= t_dec − 1.500."""
    a = [p for p in oi if p[0] <= t_dec - 600]
    b = [p for p in oi if p[0] <= t_dec - 1500]
    if not a or not b or t_dec - 600 - a[-1][0] > 600 or t_dec - 1500 - b[-1][0] > 600 or b[-1][1] <= 0:
        return None
    return a[-1][1] / b[-1][1] - 1


def auditar(dia_col, cache):
    datos = velas_y_interes(dia_col, cache)
    if datos is None:
        return None
    v1, oi = datos
    ini = int(dt.datetime(dia_col.year, dia_col.month, dia_col.day, tzinfo=COL).timestamp())
    apuestas, sin_cerrar = [], 0
    j = 0
    for t_dec in range(ini, ini + 86400, 600):
        while j < len(v1) and v1[j][0] + 60 <= t_dec:
            j += 1
        s = S.senal(v1[max(0, j - 131):j], t_dec)
        if not s:
            continue
        ent = S.cierre_en(v1, t_dec + S.RETRASO)
        sal = S.cierre_en(v1, t_dec + S.RETRASO + S.PLAZO)
        if ent is None or sal is None:
            sin_cerrar += 1
            continue
        cerradas = [a for a in apuestas if a["t"] + S.RETRASO + S.PLAZO <= t_dec + 4]
        neto = 0.0
        for a in cerradas:
            neto += S.PAGO if a["res"] else -1.0
        perdio = any(a["si"] and a["res"] == 0 for a in cerradas)
        doi = cambio_interes(oi, t_dec)
        oi_ok = doi is not None and doi <= S.UMBRAL_OI
        apuestas.append({"t": t_dec, "dir": s, "entrada": ent, "salida": sal, "res": 1 if (sal - ent) * s > 0 else 0,
                         "si": neto > 0 and not perdio and oi_ok, "neto_previo": round(neto, 2), "doi": doi})
    return apuestas, sin_cerrar


def comparar(apuestas, ruta, dia_col):
    e = json.load(open(ruta, encoding="utf-8"))
    ini = dt.datetime(dia_col.year, dia_col.month, dia_col.day, tzinfo=COL).timestamp()
    caja = {a["t"]: a for a in e.get("apuestas", []) if ini <= a["t"] < ini + 86400 and a.get("res") is not None}
    mias = {a["t"]: a for a in apuestas}
    iguales = [t for t in mias if t in caja and caja[t]["dir"] == mias[t]["dir"] and caja[t]["res"] == mias[t]["res"]]
    distintos = [t for t in mias if t in caja and t not in iguales]
    faltan = [t for t in mias if t not in caja]
    sobran = [t for t in caja if t not in mias]
    con_si = [t for t in iguales if "si" in caja[t]]
    si_igual = [t for t in con_si if bool(caja[t]["si"]) == mias[t]["si"]]
    return {"iguales": len(iguales), "distintos": distintos, "faltan_en_caja": faltan, "sobran_en_caja": sobran,
            "si_revisados": len(con_si), "si_iguales": len(si_igual), "si_distintos": [t for t in con_si if t not in si_igual]}


def hora(t):
    return dt.datetime.fromtimestamp(t, COL).strftime("%H:%M")


def main():
    args = sys.argv[1:]
    cache = args[args.index("--cache") + 1] if "--cache" in args else os.path.join(AQUI, "auditor_cache")
    os.makedirs(cache, exist_ok=True)
    fechas = [a for a in args if len(a) == 10 and a[4] == "-"]
    hoy = dt.datetime.now(COL).date()
    candidatos = [dt.date.fromisoformat(fechas[0])] if fechas else [hoy - dt.timedelta(days=k) for k in (1, 2, 3)]
    for dia in candidatos:
        r = auditar(dia, cache)
        if r is not None:
            break
    else:
        print("Binance todavía no publica los archivos de esos días.")
        return 1
    apuestas, sin_cerrar = r
    gan = sum(a["res"] for a in apuestas)
    neto = 0.0
    for a in apuestas:
        neto += S.PAGO if a["res"] else -1.0
    si = [a for a in apuestas if a["si"]]
    tasa = f"{100 * gan / max(len(apuestas), 1):.1f}".replace(".", ",")
    neto_txt = f"{neto:+.2f}".replace(".", ",")
    txt = (f"Auditoría con los datos oficiales de Binance, {dia:%d/%m/%Y} (día de Colombia): {len(apuestas)} señales del núcleo, "
           f"{gan} acertadas ({tasa} %), neto {neto_txt} apuestas en papel. "
           f"SÍ del día: {len(si)}" + (": " + ", ".join(f"{hora(a['t'])} {'acierto' if a['res'] else 'fallo'}" for a in si) if si else "") + ".")
    if "--semaforo" in args:
        c = comparar(apuestas, args[args.index("--semaforo") + 1], dia)
        txt += (f" Frente a la caja: {c['iguales']} señales iguales, {len(c['distintos'])} con otro resultado, "
                f"{len(c['faltan_en_caja'])} que la caja no tiene y {len(c['sobran_en_caja'])} que solo tiene la caja; "
                f"SÍ o NO revisados {c['si_revisados']}, iguales {c['si_iguales']}.")
        if "--corto" not in args:
            for nombre in ("distintos", "faltan_en_caja", "sobran_en_caja", "si_distintos"):
                if c[nombre]:
                    print(f"  {nombre}: " + ", ".join(hora(t) for t in c[nombre]))
    if sin_cerrar:
        txt += f" ({sin_cerrar} señales sin cerrar en los archivos.)"
    print(txt)
    if "--corto" not in args:
        for a in apuestas:
            oi_txt = "sin dato" if a["doi"] is None else f"{100 * a['doi']:+.3f} %".replace(".", ",")
            previo = f"{a['neto_previo']:+.2f}".replace(".", ",")
            print(f"  {hora(a['t'])} {S.sentido(a['dir'])} · {'acierto' if a['res'] else 'fallo'} · papel previo {previo} · "
                  f"interés abierto {oi_txt} · {'SÍ' if a['si'] else 'NO'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
