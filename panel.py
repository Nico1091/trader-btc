"""Panel local del agente: una página HTML que se rehace cada 5 segundos y se recarga sola.

Solo vive en el equipo (regla de privacidad): no carga nada de internet, ni fuentes ni scripts.
Sin líneas separadoras: se separa con espacio y fondos suaves.
"""
import datetime as dt
import html
import os

BOGOTA = dt.timezone(dt.timedelta(hours=-5))

ESTILO = """
:root{--fondo:#f6f5f2;--tarjeta:#ffffff;--suave:#efede8;--texto:#22211f;--tenue:#6b6862;
--sube:#1f7a4d;--baja:#b3361f;--aviso:#9a6a00;--acento:#2b4c7e}
@media (prefers-color-scheme:dark){:root{--fondo:#161615;--tarjeta:#1f1f1d;--suave:#2a2a27;
--texto:#ecebe7;--tenue:#a29f97;--sube:#5cc28f;--baja:#ef7d65;--aviso:#e0b44c;--acento:#8fb0e3}}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--texto);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 48px}
h1{font-size:22px;margin:0 0 4px;font-weight:650;letter-spacing:-.01em}
h2{font-size:16px;margin:0 0 12px;font-weight:650}
.sub{color:var(--tenue);margin:0 0 24px}
.fila{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;margin-bottom:22px}
.tarjeta{background:var(--tarjeta);border-radius:14px;padding:18px 20px;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.grande{font-size:28px;font-weight:650;font-variant-numeric:tabular-nums}
.num{font-variant-numeric:tabular-nums}
.par{display:flex;justify-content:space-between;gap:12px;padding:3px 0}
.par span:first-child{color:var(--tenue)}
.sube{color:var(--sube)}.baja{color:var(--baja)}.aviso{color:var(--aviso)}
.etiqueta{display:inline-block;padding:2px 10px;border-radius:999px;background:var(--suave);font-size:13px}
.barra{height:8px;border-radius:99px;background:var(--suave);overflow:hidden;margin:6px 0 2px}
.barra i{display:block;height:100%;background:var(--acento)}
table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:6px 8px;text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--tenue);font-weight:550}
td:first-child,th:first-child{text-align:left}
tbody tr:nth-child(odd){background:var(--suave)}
.tabla{overflow-x:auto}
.nota{color:var(--tenue);font-size:13px;margin-top:10px}
"""


def _e(x):
    return html.escape(str(x))


def _hora(t_ms):
    if not t_ms:
        return "—"
    return dt.datetime.fromtimestamp(t_ms / 1000, BOGOTA).strftime("%d/%m %H:%M:%S")


def _pct(x, signo=True):
    if x is None:
        return "—"
    clase = "sube" if x > 0 else ("baja" if x < 0 else "")
    return f'<span class="{clase}">{x:+.2f} %</span>' if signo else f"{x:.1f} %"


def _pesos(x):
    return f"{x:,.0f}".replace(",", ".")


def _libro(clave, nombre, d, dec, capital_inicial, tanda, precio, tasa=None):
    capital = d["efectivo"]
    ultimos = [c for c in d.get("ultimos", []) if not c.get("relleno")]
    valor = capital + (d.get("polvo", 0) * precio if precio else 0)
    en_pesos = f'<div class="par"><span>En pesos (tasa del inicio)</span><span class="num">{_pesos(valor * tasa)} COP</span></div>' \
        if tasa else ""
    cambio = (valor / capital_inicial - 1) * 100
    ganadas = sum(1 for c in ultimos if c.get("ganancia_usdt", 0) > 0)
    acierto = f"{ganadas / len(ultimos) * 100:.0f} % de los últimos {len(ultimos)}" if ultimos else "—"
    en_tanda = d["ciclos"] % tanda
    nombre = d.get("nombre") or nombre
    aviso = ""
    if d.get("siempre"):
        aviso = '<p class="nota">Testigo: entra en cada segundo libre, sin filtro de seguridad. Muestra qué pasa operando seguido.</p>'
    elif d.get("valido") is False:
        aviso = '<p class="nota aviso">Sin ventaja demostrada en validación: queda en papel para medir.</p>'
    partes = [f'<div class="tarjeta"><h2>{_e(nombre)}</h2>{aviso}',
              f'<div class="grande">{valor:.4f} USDT</div>', en_pesos,
              f'<div class="par"><span>Desde el inicio</span><span>{_pct(cambio)}</span></div>',
              f'<div class="par"><span>Ciclos cerrados</span><span class="num">{d["ciclos"]}</span></div>',
              f'<div class="par"><span>Acierto</span><span>{acierto}</span></div>',
              f'<div class="par"><span>Tanda</span><span class="num">{en_tanda} de {tanda} ciclos</span></div>',
              f'<div class="barra"><i style="width:{en_tanda / tanda * 100:.1f}%"></i></div>']
    if d.get("detenido"):
        partes.append(f'<p class="aviso">Detenido: {_e(d["detenido"])}. Cree el archivo REANUDAR para seguir.</p>')
    pos = d.get("posicion")
    if pos:
        lado = "compra" if pos["largo"] else "venta en corto"
        partes.append(f'<div class="par"><span>Ciclo abierto</span><span class="etiqueta">{lado}</span></div>'
                      f'<div class="par"><span>Entrada · objetivo · stop</span><span class="num">'
                      f'{pos["entrada"]:.2f} · {pos["tp"]:.2f} · {pos["sl"]:.2f}</span></div>')
    else:
        partes.append('<div class="par"><span>Ciclo abierto</span><span>ninguno</span></div>')
    if dec:
        sube = dec.get("prob_sube")
        mov = dec.get("prob_mov")
        el = dec.get("esperanza_largo")
        ec = dec.get("esperanza_corto")
        partes.append(f'<div class="par"><span>Probabilidad de que suba</span><span class="num">{sube * 100:.1f} %</span></div>'
                      if sube is not None else "")
        partes.append(f'<div class="par"><span>Probabilidad de movimiento</span><span class="num">{mov * 100:.1f} %</span></div>'
                      if mov is not None else "")
        partes.append(f'<div class="par"><span>Barrera (objetivo = stop)</span><span class="num">{dec["barrera"] * 100:.3f} %</span></div>')
        esperanza = f'{el * 1e4:+.1f} pb' if el is not None else "—"
        if ec is not None:
            esperanza += f' · corto {ec * 1e4:+.1f} pb'
        partes.append(f'<div class="par"><span>Ganancia esperada por ciclo</span><span class="num">{esperanza}</span></div>')
    bloqueos = d.get("bloqueos") or {}
    if bloqueos:
        texto = ", ".join(f"{_e(k)} {v}" for k, v in sorted(bloqueos.items(), key=lambda x: -x[1])[:3])
        partes.append(f'<p class="nota">Segundos frenados: {texto}</p>')
    partes.append("</div>")
    return "".join(partes)


def escribir(ruta, estado, instrumentos, capital_inicial):
    libros = estado.get("libros", {})
    decisiones = estado.get("decision", {})
    tanda = 100
    try:
        from rapido import tanda_por_capital
        tanda = tanda_por_capital(capital_inicial)
    except ImportError:
        pass
    salud = estado.get("salud", {})
    ctx = estado.get("contexto", {})
    precio = estado.get("precio")
    titulo = "Pausa: no abre ciclos nuevos" if estado.get("pausa") else "Operando en papel, ciclo tras ciclo"
    cap = estado.get("capital") or {}
    tasa = cap.get("tasa_cop_por_usdt")
    base = (f' · cada libro empezó con {_pesos(cap["cop"])} COP = {cap["usdt"]:.2f} USDT '
            f'({_pesos(tasa)} COP por USDT en Binance P2P)') if tasa and cap.get("cop") else ""
    cab = (f'<h1>Agente de trading seguido</h1><p class="sub">{titulo} · mercado {_e(estado.get("hora_mercado") or "—")} '
           f'· BTC {precio:,.2f} USDT{base}</p>' if precio else '<h1>Agente de trading seguido</h1><p class="sub">Calentando…</p>')
    tarjetas = "".join(_libro(k, libros[k].get("nombre") or k, libros[k], decisiones.get(k), capital_inicial, tanda, precio,
                              tasa) for k in libros)
    # contexto
    filas = []
    fg = ctx.get("miedo_codicia")
    if fg:
        filas.append(f'<div class="par"><span>Miedo y codicia</span><span>{fg["valor"]} ({_e(fg["clase"])})</span></div>')
    if ctx.get("dolar_sintetico"):
        filas.append(f'<div class="par"><span>Dólar sintético</span><span class="num">{ctx["dolar_sintetico"]}</span></div>')
    fut = estado.get("futuros") or {}
    if fut.get("financiacion") is not None:
        filas.append(f'<div class="par"><span>Financiación de futuros (8 h)</span><span class="num">{fut["financiacion"] * 100:.4f} %</span></div>')
    liq = estado.get("liquidaciones_5min_btc")
    if liq:
        filas.append(f'<div class="par"><span>Liquidado en 5 min (largos · cortos)</span><span class="num">{liq[0]:.3f} · {liq[1]:.3f} BTC</span></div>')
    if ctx.get("interes_abierto_otras_total_btc"):
        filas.append(f'<div class="par"><span>Interés abierto en Bybit, OKX y Deribit</span>'
                     f'<span class="num">{ctx["interes_abierto_otras_total_btc"]:,} BTC</span></div>')
    pf = estado.get("proximo_freno")
    if pf:
        filas.append(f'<div class="par"><span>Próximo freno</span><span>{_e(pf["motivo"][:70])}</span></div>'
                     f'<div class="par"><span>Desde · hasta</span><span>{_hora(pf["desde_ms"])} · {_hora(pf["hasta_ms"])}</span></div>')
    errores = ctx.get("errores") or {}
    if errores:
        filas.append(f'<p class="nota">Fuentes sin respuesta por Tor: {_e(", ".join(errores))}</p>')
    edad = (dt.datetime.now().timestamp() * 1000 - salud.get("ultimo_mensaje_ms", 0)) / 1000 if salud.get("ultimo_mensaje_ms") else None
    sal = [f'<div class="par"><span>Flujo de contado</span><span>{_e(salud.get("ws_contado"))}</span></div>',
           f'<div class="par"><span>Flujo de futuros</span><span>{_e(salud.get("ws_futuros"))}</span></div>',
           f'<div class="par"><span>Último mensaje</span><span class="num">{"hace %.0f s" % edad if edad is not None else "—"}</span></div>',
           f'<div class="par"><span>Segundos procesados · rellenados</span><span class="num">{salud.get("segundos_procesados", 0):,} · {salud.get("segundos_rellenados", 0):,}</span></div>',
           f'<div class="par"><span>Reconexiones</span><span class="num">{salud.get("reconexiones", 0)}</span></div>',
           f'<div class="par"><span>Encendido desde</span><span>{_e((salud.get("encendido_desde") or "")[:19].replace("T", " "))}</span></div>']
    lados = {"largo": "compra", "corto": "corto"}
    ciclos = []
    for clave, d in libros.items():
        for c in d.get("ultimos", []):
            if not c.get("relleno"):
                ciclos.append((c.get("t_salida", 0), clave, c))
    ciclos.sort(reverse=True)
    filas_ciclos = "".join(
        f'<tr><td>{_hora(t)}</td><td>{_e((libros[k].get("nombre") or k).split(" (")[0])}</td><td>{lados.get(c.get("lado"), "")}</td>'
        f'<td>{_e(c.get("motivo"))}</td><td>{c.get("entrada", 0):.2f}</td><td>{c.get("salida", 0):.2f}</td>'
        f'<td class="{"sube" if c.get("ganancia_usdt", 0) > 0 else "baja"}">{c.get("ganancia_usdt", 0):+.4f}</td></tr>'
        for t, k, c in ciclos[:14])
    tabla = (f'<div class="tarjeta tabla"><h2>Últimos ciclos</h2><table><thead><tr><th>Salida</th><th>Libro</th>'
             f'<th>Lado</th><th>Motivo</th><th>Entrada</th><th>Salida</th><th>USDT</th></tr></thead>'
             f'<tbody>{filas_ciclos or "<tr><td colspan=7>Todavía no hay ciclos cerrados.</td></tr>"}</tbody></table></div>')
    pie = ('<p class="nota">Todo es papel: no se envía ninguna orden. Archivos en esta carpeta: PAUSA (no abre ciclos), '
           'PARAR (cierra y apaga), REANUDAR (quita la detención de una tanda). Diario completo en la carpeta diario.</p>')
    pagina = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">'
              f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>Agente de trading seguido</title>'
              f'<style>{ESTILO}</style></head><body><main>{cab}<div class="fila">{tarjetas}</div>'
              f'<div class="fila"><div class="tarjeta"><h2>Mercado y contexto</h2>{"".join(filas) or "<p class=nota>Cargando por Tor…</p>"}</div>'
              f'<div class="tarjeta"><h2>Salud del agente</h2>{"".join(sal)}</div></div>{tabla}{pie}</main></body></html>')
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        f.write(pagina)
    os.replace(temporal, ruta)
