# Agente de trading — 25 de octubre de 2026 09:03 — Efecto del lunes (P11) verificado; P10 y el filtro de P05b descartados

2026-10-25T14:18:15Z

CONCLUSIÓN
1. Encontré una segunda ventaja medida: el largo del lunes dentro del día UTC (P11, a partir de E22 de Concretum). Compra a las 00:00 UTC, stop del 3 % y cierre a las 23:59. Con velas de 1 minuto de Binance futuros de 2020 a 2026: 355 operaciones, +109 % neto con 0,05 % por lado y +73,5 % con el doble, en el percentil 99 frente a los otros días. Después de su publicación (febrero a octubre de 2026): 38 operaciones y +12,0 % (percentil 82). En ETH se repite (+105 %); en SOL no.
2. Dos ideas caen con datos. La horquilla en compresión (P10) tiene ventaja bruta real, pero de solo +0,04 % por operación, así que pierde neto (−59 % en 1.020 operaciones de prueba). Y mi propio filtro sobre las señales de P05b resta: tomé 13 de 20 a ciegas y saqué −3,58 %, frente a −1,73 % de tomarlas todas.
3. Libro CLAUDE: 40.000 pesos (0,0 %), sin operaciones cerradas porque las horquillas no se activaron en un domingo de rango 0,72 %. Dejo la horquilla de P05b hasta las 23:45 UTC y el largo del lunes P11 para las 00:00 UTC del 26/10. A ciegas acumulo 20 operaciones, 11 aciertos y +7,63 %, frente a −0,63 % del azar.

LIBRO CLAUDE
Saldo: 40.000 pesos (12,59 USDT de referencia), 0,0 %. No hay operaciones cerradas, así que todavía no hay comparación con el azar (el azar lleva 1 cerrada, −0,42 %, y 7 abiertas).
Cerradas en esta pasada, sin activarse (no cuentan como operación):
- CL-003 (largo de P05b en 81.863,57) y CL-004 (corto en 79.675,77) vencieron a las 14:00 UTC.
- De 08:15 a 14:00 UTC, los cierres de 15 m (Coinbase BTC-USD) quedaron entre 80.068,88 y 80.513,70, y el rango de 1 minuto fue de 79.973 a 80.549.
- Causa: buena lectura. La volatilidad siguió comprimida y ninguna entrada de mercado pagaba tres veces la comisión.
Decisión de las 14:10 UTC (09:10 en Colombia), con el precio en 80.265,21 (Coinbase; Kraken 80.271,0): esperar a mercado y dejar tres órdenes condicionadas.
Razones:
(1) A mercado no hay ninguna señal: la pendiente de 60 h es −0,033 %/h y range_pos está en 0,41.
(2) El rango medio de 1 h es de 0,31 %, frente a 0,49 % de los últimos 14 días. El movimiento esperado no paga tres veces la comisión (R1 y R2).
(3) Solo pongo órdenes donde hay ventaja medida: la banda de P05b y el lunes UTC.
Las órdenes:
- CL-005, largo (P05b): si una vela de 15 m cierra por encima de 81.863,57, límite de compra en 81.863,57, válido 60 minutos (creador). Confianza 4.
- CL-006, corto (P05b): si una vela de 15 m cierra por debajo de 79.675,77, límite de venta en 79.675,77. Confianza 4.
  - Para las dos: el stop es un cierre de 15 m que vuelva a la apertura de las 00:00 UTC (80.769,67), y el cierre es a las 23:59 UTC. La señal vale hasta las 23:45 UTC. Riesgo del 1,5 % (600 pesos), con un nocional de 1,11 veces el saldo.
- CL-007, largo (P11): compra a mercado en la apertura de las 00:00 UTC del lunes 26/10 (referencia Coinbase), stop del 3 % y cierre a las 23:59 UTC. Riesgo del 1,5 %, con un nocional de 0,5 veces el saldo. Confianza 5. La Reserva Federal decide el 27 y 28, así que el lunes no le afecta.
- No vigilé en vivo: ningún nivel estaba a menos del 0,69 % y no había movimiento que pagara tres veces la comisión.
- La meta de 3 operaciones al día no se cumple hoy. Forzarlas iría contra lo medido: en BTC, a minutos, la comisión se come el movimiento.
Reglas que cambiaron (ahora son 15):
- R8 cambia: la compresión anticipa movimiento, pero romper el rango no paga la comisión (P10 descartada).
- R11, nueva: en compresión, el lado lo da la pendiente de 60 h. Si su valor absoluto está por debajo de 0,02 %/h, no se opera.
- R12, nueva: corto de continuación con una pendiente de 60 h de −0,1 %/h o menos y range_pos de 0,2 o menos. Ganó 2 de 2 a ciegas.
- R13, nueva: no dar confianza 5 por la fuerza de un impulso.
- R14, nueva: no filtrar P05b por la tendencia. Se toma entera o no se toma.
- R15, nueva: el largo del lunes UTC (P11) a riesgo del 1,5 %.
- R6 queda con 2 aciertos de 4.
Calibración, con 20 operaciones a ciegas: la confianza 3 rinde +0,47 % de media (4 operaciones), la 4 +0,50 % (10) y la 5 +0,13 % (6). Por tercera sesión, mi confianza alta rinde menos. No subo el tamaño por confianza (R13).

ENTRENAMIENTO A CIEGAS
Sesión 3 (14:07 UTC):
- 20 momentos nuevos de los últimos 12 meses de Binance BTCUSDT futuros 1m, con la semilla 20261025014, sin repetir ninguno.
- Las decisiones quedaron guardadas antes de revelar (SHA-256 ecff0386…7edfd).
- Resultado: 7 operaciones, 4 aciertos y +2,99 % neto con 0,05 % por lado, frente a −0,48 % del azar (percentil 95).
Acumulado: 60 decisiones, 20 operaciones, 11 aciertos y +7,63 % neto, frente a −0,63 % del azar (percentiles 90, 62 y 95 por sesión). Es una muestra pequeña: el criterio pide 100 operaciones.
Lo que funcionó:
- Los cortos de continuación en una tendencia bajista fuerte: M05 +1,90 % (objetivo) y M13 +0,72 %.
- El corto en compresión con la pendiente de 60 h negativa: M17 +0,77 %.
Lo que falló:
- Los largos en compresión con la pendiente plana: M10 −0,42 % y M12 −0,06 %.
- Los largos de continuación de confianza 5 quedaron planos (M02 +0,09 %, M07 0,00 %).
Filtro de P05b a ciegas (tema 4):
- 20 señales llenadas de los últimos 12 meses, sacadas de 158, con el lado y el contexto pero sin fecha. SHA-256 02a2e5bb…d414.
- Tomé las alineadas con la pendiente de 60 h (13) y vetadas las demás (7).
- Resultado: las tomadas dieron −3,58 % y todas juntas −1,73 %. Las vetadas sumaban +1,85 %. Percentil 23 frente a subconjuntos al azar del mismo tamaño.
- Conclusión: filtrar P05b por la tendencia resta (R14). Coincide con P07.

PLAN
- P05b (k = 0,5): sigue como candidata principal y frágil, en papel a riesgo del 1,5 %.
  - Se toma entera: filtrarla resta (R14).
  - Propuesta para el PC de Nicolás (la decisión es suya): probarla en papel en el libro de futuros con órdenes de creador.
- P11, el largo del lunes UTC: nueva candidata en papel a riesgo del 1,5 %. Primera operación, CL-007 y ORD-006, el 26/10.
  - Es una operación por semana: no resuelve las 3 al día, pero suma ganancia esperada positiva medida.
  - Propuesta para el PC (la decisión es suya): añadirla en papel al libro de futuros, con una orden de mercado a las 00:00 UTC del lunes y cierre a las 23:59.
- P05c: sigue en papel para comparar.
- P10: descartada.
- E01 sigue en el PC tal como está.
- Criterio de dinero real (P05b): faltan 4 de 7 condiciones, las mismas de la pasada anterior:
  - costo doble: −13,2 %;
  - caída de la cuenta: 22 %, frente a un tope del 15 %;
  - papel en vivo: 0 de 60 operaciones;
  - ciegas: 20 de 100 operaciones (antes 13).
  - P11 no tiene muestra fuera de muestra suficiente: son 38 operaciones.

MERCADO
BTC-USD (Coinbase) a las 14:09 UTC: 80.265.
- 6 h: −0,04 %, con un rango de 0,72 %.
- 24 h: +0,21 %, con un rango de 2,30 % (79.107 a 80.925).
- 60 h: −1,94 %, entre 79.107 y 81.962.
- Volatilidad: el rango medio de 1 h es de 0,31 %, frente a 0,49 % de los últimos 14 días. Es compresión. La variación diaria media de 30 días es del 1,00 %.
Próximas 24 h:
- Domingo sin datos fuertes.
- La apertura de Asia es a las 23:00 UTC. Lo medido está en el día UTC del lunes, sobre todo de 12:00 a 24:00.
- La Reserva Federal decide el 27 y 28, con el anuncio del 28 a las 18:00 UTC (R4).

MARCADOR DE PAPEL
Cerradas en esta pasada: ninguna operación. No se activaron CL-003 ni CL-004.
Siguen activas, sin activarse todavía:
- ORD-004 (P05b) y ORD-005 (P05c), hasta las 23:45 UTC. ORD-005 tiene sus niveles en 82.957,47 y 78.581,87.
Testigos del azar abiertos (cortos, cierran a las 23:59 UTC). Marca a las 14:04 UTC con 80.228,07:
- AZ-002: +0,63 % bruto.
- AZ-003: +0,67 %.
- AZ-004: +0,34 %.
- AZ-005: entró en 80.287,21; +0,07 %.
- AZ-006: entró en 80.224,13; 0,00 %.
Nuevas:
- ORD-006 (P11): largo a las 00:00 UTC del 26/10, stop del 3 %, cierre a las 23:59.
- AZ-007: largo sorteado para las 18:49 UTC, testigo de P05b.
- AZ-008: largo sorteado para las 00:00 UTC del 26/10, testigo de P11.
Total: el azar lleva 1 cerrada (−0,42 %); las estrategias y el libro CLAUDE, 0. Todavía no hay comparación posible.

VERIFICACIÓN
Datos: Binance futuros USDⓈ-M BTCUSDT 1m de data.binance.vision, del 01/01/2020 al 24/10/2026. Son 3.584.160 velas en 105 archivos, con su SHA-256 correcto y sin huecos.
1. P10, la horquilla en compresión:
  - Reglas: al cierre de cada hora, si el rango medio de 1 h de las últimas 6 o 12 h está por debajo de un umbral, se pone una orden stop en el máximo y en el mínimo de las 12 h previas, válida 6 h. El stop va a la mitad del rango; el objetivo es 1,5R, 2R o el tiempo; el máximo son 6 h y el cierre, el del día UTC.
  - Rejilla de 36 variantes: umbral de 0,3, 0,4 o 0,5 %, con entrada de tomador o con límite en el nivel. Ajuste con 2020-2023 y prueba una sola vez con 2024 a 10/2026.
  - La mejor del ajuste (0,5 %, 6 h, sin objetivo, tomador) dio +1,8 % en 774 operaciones de ajuste.
  - En prueba: 1.020 operaciones, 36,3 % de aciertos, bruto +43,0 % (percentil 98 frente al azar, cuyo p95 es +37,4 %), neto con 0,10 % −59,0 %, con el doble −161 %, peor racha de 16 y caída de 65 puntos.
  - Las 36 variantes pierden en prueba. Las de límite tienen peor bruto, por selección adversa.
  - Conclusión: la ventaja bruta existe (unos 0,04 % por operación), pero es la quinta parte de la comisión. Descartada.
2. P11, el largo del lunes UTC (E22):
  - Lunes de 00:00 a 23:59 UTC con stop del 3 %:
    - 355 operaciones, 47,0 % de aciertos.
    - Bruto +144,5 %; neto con 0,10 % +109,0 %; con el doble +73,5 %.
    - Peor racha de 7 y caída de 36,4 puntos.
    - Percentil 99 frente a 500 sorteos de los otros días.
  - Antes de la publicación: 317 operaciones, +96,9 %. Después (febrero a octubre de 2026): 38 operaciones, +12,0 %, percentil 82.
  - Por año: 2020 +49,4; 2021 +13,0; 2022 −8,9; 2023 +6,8; 2024 +53,1; 2025 −19,7; 2026 +15,3.
  - Media bruta por día de la semana: lunes +0,41 %; martes +0,01; miércoles +0,28; jueves −0,12; viernes −0,02; sábado +0,02; domingo +0,03.
  - Sin stop: +118,6 %. Con la entrada a las 12:00: +0,36 % de media. De 00:00 a 12:00 no hay efecto (+0,02 %).
  - ETHUSDT (1 h, stop aproximado con el mínimo horario): 352 operaciones, +105,1 % neto, percentil 95; después de la publicación, 35 operaciones y +25,0 %. Está correlacionado con BTC.
  - SOLUSDT: 314 operaciones, −28,7 %, sin efecto.
  - Límites:
    - Hay pocas operaciones fuera de muestra real (38).
    - Mirar los 7 días de la semana es una prueba múltiple, aunque el lunes lo propuso la fuente antes de que yo mirara.
    - Pierde en 2022 y en 2025.
    - Es una sola operación por semana.
3. Filtro de Claude sobre P05b: ver ENTRENAMIENTO A CIEGAS (resta).

RECLUTADO (un subagente abrió y leyó cada página; ninguna verificada por mí con datos)
- E27, creador de mercado en Polymarket «Bitcoin Up or Down» de 5 minutos (07/10/2026): https://achillekrtf.github.io/articles/polymarket-btc-5m-market-making/ y https://raw.githubusercontent.com/achillekrtf/polymarket-mm-backtest/main/README.md
  - Los creadores reales ganan +5,5 pb a la resolución (intervalo de −9 a +20) y +42 pb con reembolsos.
  - El cotizador simulado pierde en todas las configuraciones con latencia realista. El único caso positivo usaba precios de 2,2 s después.
  - Evidencia negativa. Además, Polymarket no es una casa autorizada.
- E28, Hygentra (arXiv 2610.26324, 19/10/2026): https://arxiv.org/pdf/2610.26324
  - Cuatro agentes con modelos de lenguaje dentro de un marco de stops fijado por humanos, en perpetuos.
  - 2.627 posiciones del 12/02 al 27/08/2026 con 0,09 % ida y vuelta.
  - La flota gana +0,05 % por operación. La reversión, +0,84 % en 178 operaciones; el momentum, −0,04 % en 1.507.
  - El 82 % es simulado y todos pierden en las subidas de baja volatilidad. Que el humano ponga el marco y el modelo elija coincide con mi libro.
- E29, momentum en memecoins de Solana (arXiv 2606.08232): https://arxiv.org/pdf/2606.08232
  - 190 operaciones y +117,7 %, pero sin las 3 mejores queda en −50,6 %. Descartada.
- E30, réplica del ORB de 5 minutos en QQQ: https://paperswithbacktest.com/strategies/orb-trading-strategy
  - Sharpe de −0,84 en unos 11 meses fuera de muestra. Evidencia negativa para E11.
- E31, Concretum, «Breaking the Rules of Intraday Trading» (26/03/2026): https://concretumgroup.com/breaking-the-rules-of-intraday-trading/
  - Bandas ATR en SPY sin costos: Sharpe de 0,88 cerrando cada día y de 1,07 dejando los largos de un día para otro.
  - Es una variante de E09.
- Alpha Arena temporada 2: sin resultados publicados al 25/10 (https://www.traderank.ai/blog/alpha-arena-alternatives-2026).

COMPARACIÓN CON EL EXPEDIENTE
- Punto 3: se confirma una vez más que anticipar el movimiento no basta. P10 tiene un bruto real que no paga la comisión, igual que el modelo de movimiento del PC.
- Punto 2: la IA como filtro aportaba selectividad en junio. Aquí, con reglas de tendencia, restó. La selectividad útil no está en la pendiente de 60 h.
- P11 es la primera ventaja que no depende de la entrada de creador: resiste el doble de comisión.

ESTRATEGIAS PROPIAS
- P01, P02, P03, P04, P06 y P08: descartadas.
- P05: probada, negativa.
- P05b: candidata principal, frágil, en papel.
- P05c: en papel para comparar.
- P07: archivada.
- P09: reemplazada por P11.
- P10, la horquilla en compresión: descartada en esta pasada.
- P11, el largo del lunes UTC: probada; candidata en papel desde el 26/10.
- P11 en ETH: probada, positiva y correlacionada con BTC.

Próximo tema: 12 (otros mercados: P05b y P11 en ETH con velas de 1 minuto y en futuros de índices u oro). Después, una segunda regla de filtro de P05b basada en la volatilidad, que según E28 es lo que importa.
Telegram atendidos: 765, 766, 767 (764 va a marketing). No hubo mensajes nuevos.

CÓDIGO DE LAS PRUEBAS (Python 3, solo la biblioteca estándar; lib.py, ciegas.py y cb.py son los del correo anterior, sin cambios)

----- verif_p10.py -----
# Verificacion 25-10 14 UTC: P10 (horquilla en compresion) y P09/E22 (apertura de Asia del lunes)
# en futuros USDM BTCUSDT 1m 2020-01 a 2026-10-24 (data.binance.vision, SHA-256). Ajuste 2020-2023, prueba 2024-01 a 2026-10 una sola vez.
import lib, random, json, time, sys
random.seed(2510)
m = lib.load1m(); T, O, H, L, C = m['t'], m['o'], m['h'], m['l'], m['c']; N = len(T)
h1 = lib.agg(m, 3600)
ts = lambda s: int(time.mktime(time.strptime(s, '%Y-%m-%d'))) - time.timezone
CUT = ts('2024-01-01')
def sim(i, side, entry, stop, tgt, last):
    # desde el minuto i, posicion abierta a 'entry'; stop primero si ambos en el mismo minuto
    for j in range(i, last + 1):
        if (L[j] <= stop) if side > 0 else (H[j] >= stop): return side * (stop / entry - 1), j, 'stop'
        if tgt and ((H[j] >= tgt) if side > 0 else (L[j] <= tgt)): return side * (tgt / entry - 1), j, 'obj'
    return side * (C[last] / entry - 1), last, 'tiempo'
def p10(thr=0.004, look=8, rng=12, R=2.0, valid=6, maker=False, W=60):
    out = []; busy = 0
    HT, HH, HL, HC, I0 = h1['t'], h1['h'], h1['l'], h1['c'], h1['i0']
    for q in range(max(look, rng) + 1, len(HT) - 1):
        i = I0[q] # primer minuto de la hora q: decision al cierre de la hora q-1
        if i <= busy: continue
        if T[i] % 86400 > 17 * 3600: continue # sin nuevas despues de las 17 UTC (cierre del dia)
        if sum((HH[k] - HL[k]) / HC[k] for k in range(q - look, q)) / look >= thr: continue
        hi = max(HH[q - rng:q]); lo = min(HL[q - rng:q]); mid = (hi + lo) / 2
        endday = i - (T[i] % 86400) // 60 + 1439
        last = min(endday, N - 1); lim = min(i + valid * 60, last)
        f = None
        for j in range(i, lim):
            if H[j] > hi: f = (j, 1, max(hi, O[j])); break
            if L[j] < lo: f = (j, -1, min(lo, O[j])); break
        if not f: busy = lim; continue
        j, s, pe = f; ent_j = j
        if maker: # tras romper, limite en el nivel valido W min
            lvl = hi if s == 1 else lo; g = None
            for k in range(j + 1, min(j + 1 + W, last)):
                if (L[k] < lvl) if s == 1 else (H[k] > lvl): g = k; break
            if g is None: busy = j; continue
            ent_j = g; pe = lvl
        stop = mid; risk = abs(pe - stop) / pe
        tgt = pe * (1 + s * R * risk) if R else None
        endt = min(ent_j + valid * 60, last)
        r, x, why = sim(ent_j, s, pe, stop, tgt, endt)
        out.append({'t': T[ent_j], 's': s, 'g': r, 'risk': risk, 'hold': x - ent_j, 'why': why}); busy = x
    return out
def azar(tr, reps=200):
    res = []
    for _ in range(reps):
        tot = 0
        for x in tr:
            i = random.randrange(1440 * 30, N - 1440)
            endday = i - (T[i] % 86400) // 60 + 1439
            s = random.choice((1, -1)); pe = O[i]; stop = pe * (1 - s * x['risk']); tgt = pe * (1 + s * 2 * x['risk'])
            r, _, _ = sim(i, s, pe, stop, tgt, min(i + max(x['hold'], 1), endday)); tot += r
        res.append(tot)
    return sorted(res)
def rep(tr, c):
    return lib.stats([x['g'] - c for x in tr])
res = {}
grid = [(thr, look, R, mk) for thr in (0.003, 0.004, 0.005) for look in (6, 12) for R in (1.5, 2.0, 0) for mk in (False, True)]
for p in grid:
    tr = p10(thr=p[0], look=p[1], R=p[2], maker=p[3])
    c = 0.0007 if p[3] else 0.0010
    a = [x for x in tr if x['t'] < CUT]; b = [x for x in tr if x['t'] >= CUT]
    res[str(p)] = {'ajuste': rep(a, c), 'prueba': rep(b, c), 'bruto_aj': round(100 * sum(x['g'] for x in a), 1), 'tr': tr}
    print(p, 'ajuste', res[str(p)]['ajuste'], 'bruto', res[str(p)]['bruto_aj']); sys.stdout.flush()
best = max(grid, key=lambda p: res[str(p)]['ajuste']['neto_suma_pct'])
tr = res[str(best)]['tr']; c = 0.0007 if best[3] else 0.0010
b = [x for x in tr if x['t'] >= CUT]; a = [x for x in tr if x['t'] < CUT]
rnd = azar(b); g = sum(x['g'] for x in b)
print(json.dumps({'mejor_en_ajuste': best, 'ajuste': rep(a, c), 'prueba': rep(b, c), 'prueba_doble': rep(b, 2 * c),
    'prueba_bruto_pct': round(100 * g, 1), 'azar_prueba_bruto_media': round(100 * sum(rnd) / len(rnd), 1), 'azar_p95': round(100 * rnd[190], 1),
    'percentil': round(sum(1 for r in rnd if r < g) / 2), 'ops_por_dia_prueba': round(len(b) / ((ts('2026-10-25') - CUT) / 86400), 2),
    'salidas_prueba': {w: sum(1 for x in b if x['why'] == w) for w in ('stop', 'obj', 'tiempo')}}, ensure_ascii=False))
print('prueba de TODA la rejilla (solo para ver robustez, no para elegir):')
for p in grid: print(p, res[str(p)]['prueba']['ops'], res[str(p)]['prueba']['neto_suma_pct'])
# (sigue un bloque E22 preliminar; la version completa es verif_e22.py)

----- verif_e22.py -----
# E22 (efecto de la apertura de Asia del lunes, Concretum 30-01-2026): largo dentro del dia UTC del lunes y desde el domingo 23 UTC.
# Tramo posterior a la publicacion (2026-02-01 a 2026-10-24) = fuera de muestra real. Azar: largos de 24h en dias al azar (no lunes).
import lib, json, time, random
random.seed(22)
m = lib.load1m(); T, O, C, H, L = m['t'], m['o'], m['c'], m['h'], m['l']
h1 = lib.agg(m, 3600); idx = {t: k for k, t in enumerate(h1['t'])}
ts = lambda s: int(time.mktime(time.strptime(s, '%Y-%m-%d'))) - time.timezone
PUB = ts('2026-02-01')
def ret(t0, hrs, stop=None):
    if t0 not in idx or t0 + hrs * 3600 not in idx: return None
    i = h1['i0'][idx[t0]]; j = h1['i0'][idx[t0 + hrs * 3600]] - 1; e = O[i]
    if stop:
        for k in range(i, j + 1):
            if L[k] <= e * (1 - stop): return -stop
    return C[j] / e - 1
out = {}
for nm, wd, hr, hrs in (('dom23_a_lun23', 6, 23, 24), ('lun00_a_lun2359 (dentro del dia UTC)', 0, 0, 24), ('lun00_a_lun12', 0, 0, 12)):
    for stop in (None, 0.03):
        rs = [(t, ret(t, hrs, stop)) for t in h1['t'] if time.gmtime(t).tm_wday == wd and time.gmtime(t).tm_hour == hr]
        rs = [(t, r) for t, r in rs if r is not None]
        base = [ret(t, hrs, stop) for t in h1['t'] if time.gmtime(t).tm_hour == hr and time.gmtime(t).tm_wday != wd]
        base = [r for r in base if r is not None]
        def blk(sub):
            g = [r for _, r in sub]; n = len(g)
            if not n: return {}
            sims = sorted(sum(random.choice(base) for _ in range(n)) for _ in range(500))
            st = lib.stats([r - 0.001 for r in g])
            st.update({'bruto_pct': round(100 * sum(g), 1), 'media_pct': round(100 * sum(g) / n, 3), 'neto_doble_0.20_pct': round(100 * sum(r - 0.002 for r in g), 1),
                       'percentil_vs_otros_dias': round(sum(1 for s in sims if s < sum(g)) / 5)})
            return st
        out['%s stop=%s' % (nm, stop)] = {'todo': blk(rs), 'antes_pub_2020_2026-01': blk([x for x in rs if x[0] < PUB]), 'despues_pub_2026-02_a_10': blk([x for x in rs if x[0] >= PUB]),
                                          'media_otros_dias_pct': round(100 * sum(base) / len(base), 3)}
        print(nm, stop, json.dumps(out['%s stop=%s' % (nm, stop)], ensure_ascii=False))

----- verif_e22b.py -----
# Complemento E22: por anio (lunes 00-23:59 UTC, stop 3%) y variante lunes 12:00-23:59 UTC; tambien martes-domingo para ver si es solo el lunes.
import lib, json, time, random
m = lib.load1m(); T, O, C, L = m['t'], m['o'], m['c'], m['l']
h1 = lib.agg(m, 3600); idx = {t: k for k, t in enumerate(h1['t'])}
def ret(t0, hrs, stop):
    if t0 not in idx or t0 + hrs * 3600 not in idx: return None
    i = h1['i0'][idx[t0]]; j = h1['i0'][idx[t0 + hrs * 3600]] - 1; e = O[i]
    for k in range(i, j + 1):
        if L[k] <= e * (1 - stop): return -stop
    return C[j] / e - 1
for hr, hrs in ((0, 24), (12, 12)):
    by = {}
    for wd in range(7):
        g = [ret(t, hrs, 0.03) for t in h1['t'] if time.gmtime(t).tm_wday == wd and time.gmtime(t).tm_hour == hr]
        g = [r for r in g if r is not None]; by['dia%d' % wd] = (len(g), round(100 * sum(g) / len(g), 3))
    print('entrada %02d UTC, %dh, media bruta por dia de semana (0=lunes):' % (hr, hrs), by)
yr = {}
for t in h1['t']:
    w = time.gmtime(t)
    if w.tm_wday == 0 and w.tm_hour == 0:
        r = ret(t, 24, 0.03)
        if r is not None: yr.setdefault(w.tm_year, []).append(r - 0.001)
print('lunes 00-23:59 stop 3%, neto 0,10% por anio:', {y: (len(v), round(100 * sum(v), 1)) for y, v in yr.items()})

----- p11_alt.py -----
# P11 en ETHUSDT y SOLUSDT perpetuos (velas 1h de data.binance.vision, SHA-256): largo lunes 00-24 UTC, stop 3% (aprox. con el minimo horario), 0,05% por lado.
import zipfile, io, glob, hashlib, time, json, random
random.seed(11)
def load(sym):
    rows = {}
    for fn in sorted(glob.glob('/tmp/d/eth/%s-1h-*.zip' % sym)):
        if hashlib.sha256(open(fn, 'rb').read()).hexdigest() != open(fn + '.CHECKSUM').read().split()[0]: print('malo', fn); continue
        z = zipfile.ZipFile(fn)
        for line in io.TextIOWrapper(z.open(z.namelist()[0])):
            if line[:1].isdigit():
                r = line.split(','); rows[int(r[0]) // 1000] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]))
    return rows
PUB = int(time.mktime(time.strptime('2026-02-01', '%Y-%m-%d'))) - time.timezone
for sym in ('ETHUSDT', 'SOLUSDT'):
    R = load(sym); res = {}
    def day(t0, stop=0.03):
        if any(t0 + 3600 * k not in R for k in range(24)): return None
        e = R[t0][0]
        for k in range(24):
            if R[t0 + 3600 * k][2] <= e * (1 - stop): return -stop
        return R[t0 + 3600 * 23][3] / e - 1
    days = sorted(t for t in R if t % 86400 == 0)
    by = {}
    for t in days:
        r = day(t)
        if r is not None: by.setdefault(time.gmtime(t).tm_wday, []).append((t, r))
    mon = by[0]; others = [r for wd in range(1, 7) for _, r in by[wd]]
    def blk(s):
        g = [r for _, r in s]; n = len(g)
        sims = sorted(sum(random.choice(others) for _ in range(n)) for _ in range(500))
        return {'ops': n, 'media_bruta_pct': round(100 * sum(g) / n, 3), 'neto_0.10_pct': round(100 * sum(r - 0.001 for r in g), 1), 'neto_doble_pct': round(100 * sum(r - 0.002 for r in g), 1),
                'aciertos_pct': round(100 * sum(1 for r in g if r > 0.001) / n, 1), 'percentil_vs_otros_dias': round(sum(1 for x in sims if x < sum(g)) / 5)}
    yr = {}
    for t, r in mon: yr.setdefault(time.gmtime(t).tm_year, []).append(r - 0.001)
    print(sym, json.dumps({'todo': blk(mon), 'despues_pub': blk([x for x in mon if x[0] >= PUB]), 'media_otros_dias_pct': round(100 * sum(others) / len(others), 3),
        'media_por_dia_semana': {wd: round(100 * sum(r for _, r in by[wd]) / len(by[wd]), 3) for wd in range(7)}, 'neto_por_anio': {y: round(100 * sum(v), 1) for y, v in yr.items()}}))

----- filtro_p05b.py -----
# Tema 4: Claude como filtro de P05b a ciegas. 'mostrar N semilla': N senales de P05b (k=0,5, W=60) ya llenadas en los ultimos 12 meses
# de Binance futuros USDM 1m, con el contexto previo al llenado en % del precio de entrada (sin fecha ni precio) y el lado.
# 'revelar decisiones.json': resultado neto (0,02% entrada + 0,05% salida) de tomar todas frente a tomar solo las elegidas.
import lib, json, sys, random
m = lib.load1m(); T, O, H, L, C = m['t'], m['o'], m['h'], m['l'], m['c']; N = len(T)
d1 = lib.agg(m, 86400)
trd = [d1['h'][0] - d1['l'][0]] + [max(d1['h'][k], d1['c'][k-1]) - min(d1['l'][k], d1['c'][k-1]) for k in range(1, len(d1['t']))]
def run(k=0.5, W=60, desde=0):
    tr = []
    for q in range(15, len(d1['t'])):
        d = d1['i0'][q]
        if d < desde or d + 1439 >= N: continue
        op = O[d]; atr = sum(trd[q-14:q]) / 14; ub = op + k * atr; lb = op - k * atr
        pos = 0; done = False; ei = None
        for mk in range(15, 1440, 15):
            i = d + mk - 1; px = C[i]
            if pos and i >= ei and (pos == 1 and px < op or pos == -1 and px > op):
                tr.append({'ei': ei, 's': pos, 'g': pos * (O[i + 1] / ent - 1), 'op': op, 'atr': atr}); pos = 0
            if pos == 0 and not done and mk < 1425:
                s = 1 if px > ub else (-1 if px < lb else 0)
                if s:
                    lvl = ub if s == 1 else lb; done = True
                    for j in range(i + 1, min(i + 1 + W, d + 1439)):
                        if (L[j] < lvl) if s == 1 else (H[j] > lvl): pos = s; ei = j; ent = lvl; break
        if pos: tr.append({'ei': ei, 's': pos, 'g': pos * (C[d + 1439] / ent - 1), 'op': op, 'atr': atr})
    return tr
F = '/tmp/w/filtro_usados.json'
def slope(c):
    n = len(c); xm = (n - 1) / 2; ym = sum(c) / n; sxx = sum((k - xm) ** 2 for k in range(n))
    return sum((k - xm) * (c[k] - ym) for k in range(n)) / sxx
tr = run(desde=N - 365 * 1440)
if sys.argv[1] == 'mostrar':
    random.seed(int(sys.argv[3])); sel = random.sample(range(len(tr)), int(sys.argv[2]))
    json.dump({'total_senales_12m': len(tr), 'sel': [tr[k]['ei'] for k in sel]}, open(F, 'w'))
    for q, k in enumerate(sel):
        x = tr[k]; i = x['ei']; ref = C[i - 1]; p = lambda v: round(100 * (v / ref - 1), 2)
        hs = []
        for kk in range(60, 0, -1):
            a, b = i - 60 * kk, i - 60 * (kk - 1); hs.append((p(O[a]), p(max(H[a:b])), p(min(L[a:b])), p(C[b - 1])))
        cl = [y[3] for y in hs]; hh = max(y[1] for y in hs); ll = min(y[2] for y in hs)
        print('== S%02d lado=%s apertura_dia=%+.2f%% stop(apertura) a %.2f%% | pend60h=%+.3f%%/h pend12h=%+.3f%%/h range_pos60h=%.2f rango_med_1h(14)=%.2f%% minuto_del_dia=%d' % (
            q + 1, 'LARGO' if x['s'] > 0 else 'CORTO', p(x['op']), abs(p(x['op'])), slope(cl), slope(cl[-12:]), (0 - ll) / (hh - ll) if hh > ll else .5,
            sum(y[1] - y[2] for y in hs[-14:]) / 14, (T[i] % 86400) // 60))
        print('1h o/h/l/c (12):', ' '.join('%s/%s/%s/%s' % y for y in hs[-12:]))
        print('1m cierres(60):', ' '.join(str(p(C[j])) for j in range(i - 60, i)))
else:
    dec = json.load(open(sys.argv[2])); st = json.load(open(F)); by = {x['ei']: x for x in tr}
    allr = []; mine = []
    for d, ei in zip(dec, st['sel']):
        x = by[ei]; r = 100 * (x['g'] - 0.0007); allr.append(r)
        if d['tomar']: mine.append(r)
        print('S%02d %s %s conf %d -> %+.3f%% neto' % (d['id'], 'LARGO' if x['s'] > 0 else 'CORTO', 'TOMA' if d['tomar'] else 'veta', d['conf'], r))
    random.seed(4); sims = sorted(sum(random.sample(allr, len(mine))) for _ in range(2000)) if mine else [0]
    print('todas: %d ops, %+.2f%% (media %+.3f) | elegidas: %d ops, %+.2f%% (media %+.3f) | vetadas: %+.2f%% | percentil de la seleccion frente a subconjuntos al azar del mismo tamano: %d' % (
        len(allr), sum(allr), sum(allr) / len(allr), len(mine), sum(mine), sum(mine) / max(1, len(mine)), sum(allr) - sum(mine), sum(1 for s in sims if s < sum(mine)) / 20))
    print('senales en 12 meses:', st['total_senales_12m'])

#### REGISTRO ####
{"version":5,"actualizado":"25-10-2026 09:30 Colombia (14:30 UTC)","estrategias":[{"id":"E01","nombre":"MEZCLA 1h (retroceso alcista + corto en techo extremo + clasificador GB)","fuente":"expediente propio, junio 2026","mercado":"BTCUSDT Binance","horizonte":"1h, hasta 24 velas","entrada":"largo: pendiente 60 velas>0 y range_pos 0,35-0,65; corto: range_pos>=0,90; filtro GB 20 rasgos umbral 0,30-0,50","salida":"stop 3%, objetivo 6%, BE en 1R, max 24 velas","resultado_fuente":"864 ops, 53,6%, +248% (0,05%/lado)","verificado":"verificado 24-10-2026 con BTCUSDT 1m de data.binance.vision (01-10-2024 a 23-10-2026, SHA-256 ok, sin huecos), corte 75/25, una posicion, 0,05%/lado: reglas sin clasificador 429 ops, 47,8%, -1,7%, prueba -16,0%, costo doble -44,6%, p83 vs azar; largos +28,2%, cortos -29,9%. Clasificador sin replicar.","estado":"reglas solas sin ventaja; clasificador sin verificar; no es day trading"},{"id":"E02","nombre":"Concretum Catching Crypto Trends","fuente":"https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/ ; SSRN may-2025","mercado":"BTC","horizonte":"intradia","entrada":"sin obtener (SSRN bloquea); la pagina de Concretum no trae reglas, menciona efecto apertura Asia lunes","resultado_fuente":"Sharpe ~1,6 bruto 2018-2025","verificado":"sin verificar","estado":"sin verificar"},{"id":"E03","nombre":"Banda de ruido (Concretum SPY 2024)","mercado":"SPY; probado en BTC","entrada":"apertura 00 UTC +/- media 14 dias del mov. absoluto; revision 30 min","salida":"max(banda,VWAP); 23:59 UTC","verificado":"verificado 24-10-2026 (01-10-2024 a 23-10-2026), 0,05%/lado: x1,0 2.757 ops -283,6% p34; x1,5 1.646 ops -162,2% p54","estado":"descartada"},{"id":"E04","nombre":"Estacionalidad 21-23 UTC","fuente":"https://quantpedia.com/strategies/intraday-seasonality-in-bitcoin","verificado":"verificado 24-10-2026, 0,05%/lado: 753 ops, -40,3% (bruto +35%), prueba -24,8%, p98","estado":"descartada"},{"id":"E05","nombre":"Momentum primera/ultima media hora","fuente":"Shen, Urquhart, Wang, Financial Review 2022","verificado":"verificado 24-10-2026, 0,05%/lado (reloj): 753 ops, -85,1%","estado":"descartada (version de reloj)"},{"id":"E06","nombre":"Coinquant 5m/15m (evidencia negativa)","fuente":"https://www.coinquant.ai/blog/best-timeframe-for-crypto-trading-strategies-1-minute-to-1-month-backtested","resultado_fuente":"15m -31,36% en 138 ops; 5m -38,35% en 235","verificado":"sin verificar","estado":"evidencia"},{"id":"E07","nombre":"Turbine Kalshi 15m (evidencia negativa)","fuente":"https://www.turbinefi.com/blog/5000-strategy-backtest-kalshi-btc-15m","resultado_fuente":"102 de 4.904 rentables","verificado":"sin verificar","estado":"evidencia"},{"id":"E08","nombre":"Freqtrade BTC 5m","fuente":"https://github.com/OnChainVibe/freqtrade-strategies","verificado":"sin verificar","estado":"sin datos"},{"id":"E09","nombre":"ATR breakout (Concretum QuanTips #2)","fuente":"https://concretumgroup.com/wp-content/uploads/2026/02/Improving-Performance-with-Fast-Alphas-A-Tactical-Overlay-for-Intraday-Trend-Trading.pdf (feb-2026)","mercado":"SPY; probado en BTC","horizonte":"intradia","entrada":"cierre de 15m fuera de apertura00UTC +/- 0,5 ATR14 diario","salida":"cierre de 15m que vuelve a la apertura; 23:59 UTC","resultado_fuente":"SPY neto: CAGR>13%, Sharpe 0,87","verificado":"verificado 25-10-2026 con BTCUSDT spot 1m (01-10-2024 a 24-10-2026), corte 75/25: tomador 0,05%/lado 497 ops, 40,6%, -21,5%; prueba 124 ops -3,6% (bruto +8,8%); 0,075% -46,3%; 0,10% -71,2%; bruto p86 vs azar","estado":"candidata solo con entrada de creador (ver P05b)"},{"id":"E10","nombre":"VWAP trend 1m (Concretum)","fuente":"https://concretumgroup.com/wp-content/uploads/2026/02/Volume-Weighted-Average-Price.pdf","mercado":"QQQ","resultado_fuente":"+671%, Sharpe 2,1 con comision infima","verificado":"sin verificar","estado":"por probar con banda"},{"id":"E11","nombre":"ORB 5 min acciones en juego (Concretum)","fuente":"https://concretumgroup.com/wp-content/uploads/2026/02/A-Profitable-Day-Trading-Strategy-For-The-U.S.-Equity-Market.pdf","mercado":"acciones EE.UU.","resultado_fuente":">1.600%, Sharpe 2,81","verificado":"sin verificar","estado":"otro mercado"},{"id":"E12","nombre":"MACD D1H1 (Quantpedia 13-11-2025)","fuente":"https://quantpedia.com/how-to-design-a-simple-multi-timeframe-trend-strategy-on-bitcoin/","verificado":"verificado 24-10-2026, 0,05%/lado: 340 ops, -24,1%, prueba -1,6%, p76","estado":"descartada"},{"id":"E13","nombre":"London Signal B MNQ","fuente":"https://arxiv.org/pdf/2605.04004 (may-2026)","mercado":"MNQ","resultado_fuente":"OOS N=247, +4,09 pts netos, t=4,30","verificado":"sin verificar","estado":"otro mercado"},{"id":"E14","nombre":"Fade vela 15m flujo taker (evidencia negativa)","fuente":"arXiv 2608.21888 (ago-2026)","resultado_fuente":"ningun par de 183 rentable neto","verificado":"sin verificar","estado":"evidencia negativa"},{"id":"E15","nombre":"Turn-of-the-candle BTC","fuente":"https://pmc.ncbi.nlm.nih.gov/articles/PMC10015199/","resultado_fuente":"0,58 pb/minuto con comision 0","verificado":"sin verificar","estado":"descartada por costos"},{"id":"E-AA1","nombre":"Alpha Arena temporada 1 (Nof1)","fuente":"leido por la pasada del 24-10 18:11 (cortada)","mercado":"cripto perpetuos Hyperliquid","resultado_fuente":"18-10 a 03-11-2025, 10.000 USD/modelo: Qwen3 Max +22,3%, DeepSeek +4,9%, Claude Sonnet 4.5 -30,8%, GPT-5 -62,7%; el ganador <3 ops/dia","verificado":"cifras de la fuente, no reproducibles","estado":"evidencia: pocas y buenas"},{"id":"E16","nombre":"Cruce de EMAs con walk-forward doble fuera de muestra","fuente":"https://arxiv.org/html/2602.10785v1 (11-02-2026)","mercado":"BTC","horizonte":"60 min, siempre en mercado","resultado_fuente":"OOS 2019-2021 neto 0,1%: 90,9% anual, Sharpe 1,106 vs mantener 92,7%, 1,128","verificado":"sin verificar","estado":"no es day trading; no supera a mantener"},{"id":"E17","nombre":"XGBoost horario con filtro de costo","fuente":"https://arxiv.org/html/2606.00060v1 (19-05-2026)","mercado":"BTC-USDT 1h","entrada":"largo si prevision>0 y |r|>2x costo del cambio de posicion","resultado_fuente":"OOS 27 pliegues, 10 pb: 65,4% anual, Sharpe 1,09, DD -67,4%, 251 ops; sin filtro -64% anual; p=0,89 vs mantener","verificado":"sin verificar","estado":"idea util: filtro de costo"},{"id":"E18","nombre":"SMA 10/200 en 4h (honest-backtest)","fuente":"https://github.com/water7up/honest-backtest (12-10-2026)","resultado_fuente":"OOS desde 2024-07 neto con funding: +25,9% vs mantener +37,4%","verificado":"sin verificar","estado":"evidencia en contra; no es day trading"},{"id":"E19","nombre":"EMA 12/26 + RSI14 1h (IRL-TRADER PR 9)","fuente":"https://github.com/GabrielGauss/IRL-TRADER/pull/9 (05-10-2026)","resultado_fuente":"OOS +8,09% en 8 ops, inconcluso","verificado":"sin verificar","estado":"evidencia insuficiente"},{"id":"E20","nombre":"Agent Market Arena (LLM en vivo)","fuente":"https://arxiv.org/html/2510.11695v2 (oct-2025)","resultado_fuente":"BTC 01-08 a 30-09-2025: mejor Gemini-2.0-flash +5,02%; peor Claude-3.5-haiku -14,51%; mantener +0,66%","verificado":"sin verificar","estado":"evidencia (tema 1)"},{"id":"E21","nombre":"Alpha Arena temporada 1.5","fuente":"https://www.gncrypto.news/news/alpha-arena-season-1-5-ai-stock-trading-competition/ ; https://www.traderank.ai/blog/alpha-arena-alternatives-2026","resultado_fuente":"20-11 a 03-12-2025; gano Grok 4.20 (+12,11% o +22,38%)","verificado":"sin verificar; fuente secundaria","estado":"evidencia (tema 1)"},{"id":"E22","nombre":"Efecto apertura de Asia del lunes (Concretum, amplia E02)","fuente":"https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/ (30-01-2026, Zarattini, Pagani, Barbon)","mercado":"BTC 2018-2025","horizonte":"intradia alta frecuencia","entrada":"no publicada (ensamble de modelos de tendencia); retornos altos desde domingo ~19:00 ET (apertura de Tokio) unas 24 h; domingo por la manana EE.UU. negativo; aparece desde 2S-2020","riesgo":"volatilidad objetivo 20% anual","resultado_fuente":"Sharpe ~1,6 bruto; neto, comisiones y numero de ops no constan","verificado":"sin verificar","estado":"verificada 25-10 14 UTC dentro del dia UTC del lunes como P11: BTC 355 ops +109% neto (p99), ETH 352 ops +105% (p95), SOL sin efecto"},{"id":"E23","nombre":"Efecto del cuarto de hora (Kim y Hansen)","fuente":"https://arxiv.org/html/2607.09426v1 (10-07-2026)","mercado":"perpetuos USDT-M Binance 2021-2024","horizonte":"10 s tras :00/:15/:30/:45","entrada":"signo de prevision LASSO/logistica (12 retornos de frontera + 28 indicadores de 15 min), reajuste mensual","salida":"10 s","resultado_fuente":"OOS 2021-07 a 2024-10: ~0,5 pb bruto por op (BTC 0,375 pb, 57,1%, N=116.951); 1/20 de la ida y vuelta; los autores: no es estrategia","verificado":"sin verificar; no se puede con velas de 1m","estado":"evidencia negativa por costo"},{"id":"E24","nombre":"Banco honesto BTCUSDT futuros intradia (nattachai290/crypto-strategy)","fuente":"https://github.com/nattachai290/crypto-strategy (STATUS 01-10-2026)","mercado":"BTCUSDT USDT-M 1m + funding 2020-01 a 2026-08","horizonte":"1-4 h, plano al cierre de sesion","entrada":"a) rompimiento del rango de apertura 00 UTC en 4h; b) corto donchian(48)+tendencia htf(50,4)+ADX>20 en 15m, entrada post-only a 0,1 ATR; c) largo donchian(24)+htf+ADX en 30m; d) funding_fade: corto si funding>+0,03%, largo si <-0,03%","salida":"b) stop 2% (ATR 1,5-8), trailing 2,5 ATR desde 1,5R, 8 h; c) stop 1%, 24 h; d) stop 2 ATR, objetivo 2,5 ATR, 48 barras","resultado_fuente":"costos 0,05/0,02 + 0,02% desliz.; a) holdout 135 ops -0,112 R; b) valid 339 ops -0,120 R (rechazada); c) valid 258 ops +0,228 R, holdout -0,010 R; d) sin resultado; 0 de 18 ideas aprobadas","verificado":"sin verificar (cifras de su diario)","estado":"evidencia negativa independiente con el mismo mercado y datos"},{"id":"E25","nombre":"LiveMACE (LLM en papel en vivo, decisiones cada 4 h)","fuente":"https://arxiv.org/html/2610.09872v1 (07-10-2026)","mercado":"6 cripto (Hyperliquid) + 17 acciones","horizonte":"4 h","riesgo":"freno intradia si la cuenta cae >5% del cierre previo; orden max 20% del capital; no invertir el mismo simbolo en 60 min; guia de comision ~0,15%","resultado_fuente":"13-04 a 13-05-2026, todo junto: GPT-5.4 +5,74%, DeepSeek-V3.2 +5,77%, Qwen3-Max +4,42%, Gemini-3.1-Pro +3,50%, Grok-4.20 +3,09%; sin cifras solo cripto ni numero de ops","verificado":"sin verificar","estado":"evidencia (tema 1); reglas de riesgo reutilizables"},{"id":"E26","nombre":"Can AI Make Money in Crypto? (backtest vs dinero real)","fuente":"https://arxiv.org/html/2609.34510v1 (28-09-2026)","mercado":"10 cripto grandes","horizonte":"LLM cada 4h; ML 5m-4h","resultado_fuente":"comision 0,10% spot / 0,05% perp; backtest 2025 GATs +71,7%; papel 04-06 a 21-09-2026 XGBoost +27,5%, Qwen +37,8%; dinero real 24-08 a 21-09-2026: Qwen +3,72%, XGBoost -0,79%, TRA -14,74% vs mantener +11,63%; ninguno supera a mantener","verificado":"sin verificar","estado":"evidencia: el paso de backtest a real se come la ventaja"},{"id":"E27","nombre":"Creador de mercado en Polymarket BTC Up/Down 5 min","fuente":"https://achillekrtf.github.io/articles/polymarket-btc-5m-market-making/ (07-10-2026); https://raw.githubusercontent.com/achillekrtf/polymarket-mm-backtest/main/README.md","mercado":"binarios BTC 5 min (Polymarket)","horizonte":"5 min","reglas":"bid/ask alrededor del valor justo (spot Binance con vol de 1 s de 30 min, o EWMA); medio diferencial 0,01-0,05; 20 acciones por cotizacion, inventario max 100, hasta resolucion","resultado_declarado":"creadores reales +5,5 pb a la resolucion (IC -9 a +20), +42 pb con reembolsos; cotizador simulado pierde en todas las configuraciones con latencia realista (mejor ~-870 USD/dia); el unico positivo usa precios posteriores (fuga de 2,2 s)","estado":"evidencia negativa; sin verificar por mi; ademas Polymarket no es casa autorizada por Nicolas"},{"id":"E28","nombre":"Hygentra: capa de control para agentes LLM que siguen reglas","fuente":"https://arxiv.org/pdf/2610.26324 (19-10-2026)","mercado":"perpetuos BTC, ETH, SOL y otros; Hyperliquid","horizonte":"horas a dias","reglas":"marco humano fijo: stop inicial, objetivo, parciales, trailing, max 5 posiciones; medianas: momentum stop 0,8% 2,5x 2,9 h; rompimiento 1,0% 2,5x 4,3 h; tendencia 1,0% 2,0x 5 h; reversion 3,9% 2,0x 57 h; entradas no publicadas","resultado_declarado":"2.627 posiciones 12-02 a 27-08-2026, 0,09% ida y vuelta: flota +0,050% por op; reversion 178 ops +0,836%; momentum 1.507 ops -0,043%; el 82% simulado; todos pierden en alza de baja volatilidad; sin la caida de agosto el rompimiento queda en -4,7 pp","estado":"evidencia (tema 1 y 2): el marco de reglas lo pone el humano y la ganancia depende del regimen; sin verificar"},{"id":"E29","nombre":"Momentum en memecoins de DEX de Solana (Kamat)","fuente":"https://arxiv.org/pdf/2606.08232 (2026)","mercado":"memecoins Solana (AMM)","horizonte":"minutos","reglas":"momentum con filtros de edad, capitalizacion y horas vetadas (2, 13, 23 UTC), TP, trailing y stop por tiempo; parametros no revelados","resultado_declarado":"190 ops papel 29-03 a 12-04-2026, 40,5%, media +0,62%, mediana -3,58%, +117,7% acumulado; sin las 3 mejores -50,6%","estado":"descartada: depende de 3 operaciones; fuera de Binance"},{"id":"E30","nombre":"Replica del ORB 5 min en QQQ/TQQQ (paperswithbacktest)","fuente":"https://paperswithbacktest.com/strategies/orb-trading-strategy (sin fecha; replica Zarattini y Aziz, sep-2025)","mercado":"QQQ/TQQQ","horizonte":"intradia","resultado_declarado":"Sharpe -0,06 en 2010-2026; 0,16 dentro de muestra; -0,84 en ~11 meses fuera de muestra","estado":"evidencia negativa para E11 (otro mercado); sin verificar"},{"id":"E31","nombre":"Concretum \"Breaking the Rules of Intraday Trading\" (bandas ATR en SPY)","fuente":"https://concretumgroup.com/breaking-the-rules-of-intraday-trading/ (26-03-2026)","mercado":"SPY","horizonte":"intradia / overnight","reglas":"bandas ATR centradas en la apertura (sin multiplicador publicado), objetivo 2% de vol diaria, apalancamiento max 400%","resultado_declarado":"bruto sin costos 2006-01/2026: cierre al dia CAGR 14,1%, Sharpe 0,88, DD -25,6%; manteniendo largos overnight ~20%, ~1,07, -34,1%","estado":"variante de E09 en acciones; idea por probar en P05b: dejar correr solo los largos (no es day trading)"},{"id":"E-AA2","nombre":"Alpha Arena temporada 2","fuente":"https://www.traderank.ai/blog/alpha-arena-alternatives-2026 (10-10-2026)","estado":"sin resultados publicados al 25-10-2026; http://nof1.ai sin temporadas, http://alphaarena.ai 429"}],"estrategias_propias":[{"id":"P01","nombre":"MEZCLA 15m cierre 23:59","estado":"descartada","prueba":"24-10-2026, 0,05%/lado: 3.667 ops, -336,2%"},{"id":"P02","nombre":"Banda de ruido + modelo de movimiento (proxy)","estado":"descartada","prueba":"24-10-2026: 2.047 ops, -221,8%"},{"id":"P03","nombre":"21-23 UTC con pendiente>0","estado":"descartada","prueba":"24-10-2026: 394 ops, -28,5%"},{"id":"P04","nombre":"MEZCLA reglas cierre 23:59","estado":"descartada","prueba":"24-10-2026: 539 ops, -52,4%"},{"id":"P05","nombre":"E09 creador + overlay de retroceso 5m","estado":"probada (pasada cortada 24-10 18:11): no gano neto; definicion no registrada"},{"id":"P05b","nombre":"E09 con entrada de creador en la banda (k=0,5, W=60)","reglas":"tras cierre de 15m fuera de apertura00UTC +/- k*ATR14 diario, limite en la banda valido W min; se llena solo si el precio cruza el nivel; una senal por dia; stop: cierre de 15m que vuelve a la apertura (tomador); cierre 23:59 UTC","estado":"candidata principal, fragil; en papel desde 25-10 a medio riesgo (1,5%)","prueba":"v3 (spot 01-10-2024 a 24-10-2026): 332 ops, +20,9% con 0,02+0,05; prueba 84 ops +4,9%; doble -22,2%. v4 (25-10 08 UTC, futuros USDM 1m 2020-01 a 2026-10-24, 3.584.160 velas, SHA-256 ok, sin huecos, con funding real): k=0,5 fijo 1.012 ops, bruto +129,5%, 0,02+0,05 +57,5%, doble -13,3%, tomador 0,05x2 +27,2%; 2020-2024-09 (nunca visto) 679 ops +41,1% neto, doble -6,4%, p97 bruto vs azar; prueba previa en futuros 80 ops 0,0%; por anio neto: 2020 +34,9, 2021 +2,1, 2022 -26,5, 2023 +27,7, 2024 +11,5, 2025 -13,4, 2026 +21,1; walk-forward 24m->6m (rejilla k x W, 2022-01 a 2026-10): 598 ops OOS, 42,8%, +28,6% con 0,07%, -13,2% con 0,14%, +10,7% tomador 0,05x2, peor racha 8, caida 22,1 pts, p96 bruto; con riesgo 3% por op la caida de cuenta es 30-47%; rejilla dentada en el total con W=60 (k=0,4 -50%, 0,6 -32%, 0,65 -46%, 0,9 -37%): ventaja bruta real, neta fragil; funding medio -0,001% por op (despreciable)"},{"id":"P05c","nombre":"P05b con k=1,0 (W=60)","estado":"en papel desde 25-10 como comparacion","prueba":"v4: 2020-2024-09 221 ops +47,0% (0,07%), +31,5% doble, R medio +0,131, caida de cuenta 12,4% a riesgo 3%; 2024-10 a 2026-10 121 ops -4,5% (doble -13,0%). Mas robusta al costo, pero sin ventaja en los 2 ultimos anios; ~0,13 ops/dia"},{"id":"P06","nombre":"E09 + pendiente 60h (tomador)","estado":"descartada a 0,05%","prueba":"25-10-2026: 373 ops, -21,9%, prueba -0,8%"},{"id":"P07","nombre":"P05b + pendiente 60h","estado":"probada, peor que P05b","prueba":"25-10-2026: 221 ops +7,1%, prueba +0,2%"},{"id":"P08","nombre":"Regla de ciegas: seguir pendiente 12h>+0,1%/h con range_pos>0,6","estado":"descartada: -65,8% ajuste, -22,4% prueba con 0,05%"},{"id":"P09","nombre":"P05b + efecto apertura Asia del lunes (domingo desde 23:00 UTC)","estado":"reemplazada por P11 (el efecto esta en el dia UTC del lunes, no en el filtro de P05b)"},{"id":"P10","nombre":"Horquilla en compresion: tras 6-12 h de rango medio 1h < 0,4%, ordenes stop a ambos lados del rango de 12 h","origen":"ciegas 25-10: M07, M14, M19 (y M13 del 25-10 02 UTC) se movieron 1,7-2% en 6 h tras volatilidad baja","estado":"descartada 25-10 14 UTC","prueba":"futuros USDM 1m 2020-2026: rejilla umbral {0,3;0,4;0,5}% x ventana {6;12}h x objetivo {1,5R;2R;tiempo} x {tomador; limite en el nivel}; ajuste 2020-2023, prueba 2024-01 a 2026-10. Mejor en ajuste (0,5%, 6h, sin objetivo, tomador): ajuste 774 ops +1,8%; prueba 1.020 ops, 36,3%, bruto +43,0% (p98 frente al azar), neto 0,10% -59,0%, doble -161%, racha 16. Las 36 variantes pierden en prueba; las de limite tienen peor bruto (seleccion adversa)."},{"id":"P11","nombre":"Largo del lunes UTC (E22 dentro del dia)","reglas":"compra a mercado en la apertura de 00:00 UTC del lunes; stop 3%; cierre 23:59 UTC; riesgo 1,5%","estado":"candidata en papel desde 26-10 (CL-007, ORD-006); 1 op por semana","prueba":"25-10 14 UTC, futuros USDM 1m 2020-01 a 2026-10-24: 355 ops, 47,0%, bruto +144,5%, neto 0,10% +109,0%, doble +73,5%, racha 7, caida 36,4 pts, p99 vs otros dias; antes de la publicacion (30-01-2026) 317 ops +96,9%; despues 38 ops +12,0% (p82). Por anio neto: 2020 +49,4; 2021 +13,0; 2022 -8,9; 2023 +6,8; 2024 +53,1; 2025 -19,7; 2026 +15,3. Media bruta por dia de la semana (00-24 UTC, stop 3%): lun +0,41, mar +0,01, mie +0,28, jue -0,12, vie -0,02, sab +0,02, dom +0,03. Variante 12:00-23:59: lun +0,36. Variante 00-12 UTC sin efecto (+0,02). Domingo 23 a lunes 23: +99,7% neto."},{"id":"P11-ETH","nombre":"P11 en ETHUSDT perpetuo","estado":"probada con velas 1h: 352 ops +105,1% neto, doble +69,9%, p95; despues de pub 35 ops +25,0%; por anio 2020 +56,6, 2021 +4,1, 2022 -4,8, 2023 -22,9, 2024 +52,8, 2025 -7,9, 2026 +27,3. Correlacionado con BTC: no suma diversificacion real. SOL: 314 ops -28,7% (sin efecto). Stop aproximado con minimo horario."}],"operaciones_abiertas":[{"id":"AZ-002","tipo":"testigo de ORD-002","lado":"corto","entrada":"2026-10-25 02:30 UTC 80.737,63 Coinbase","stop":"cierre 15m >= 81.817,63","cierre_max":"23:59 UTC 25-10","marca_08:04":"80.538,92 (+0,25% bruto)","marca_14:04":"+0,63% bruto"},{"id":"AZ-003","tipo":"testigo de P05b/CL-001","lado":"corto","entrada":"2026-10-25 04:23 UTC 80.769,99 Coinbase","stop":"cierre 15m >= 81.849,99","cierre_max":"23:59 UTC 25-10","marca_08:04":"+0,29% bruto","marca_14:04":"+0,67%"},{"id":"AZ-004","tipo":"testigo libro CLAUDE","lado":"corto","entrada":"2026-10-25 06:00 UTC 80.500,47 Coinbase","stop":"cierre 15m >= 81.580,47","cierre_max":"23:59 UTC 25-10","marca_08:04":"-0,05% bruto","marca_14:04":"+0,34%"},{"id":"ORD-004","tipo":"condicionada","estrategia":"P05b sistematica (k=0,5)","activacion":"cierre 15m > 81.863,57 -> limite compra 81.863,57 60 min; cierre 15m < 79.675,77 -> limite venta 79.675,77","base":"apertura 00 UTC Coinbase 80.769,67; ATR14 diario Binance futuros 2.187,8","stop":"cierre 15m que vuelve a 80.769,67","vence":"senal hasta 23:45 UTC 25-10 (una por dia)","cierre_max":"23:59 UTC","comision":"0,02% entrada + 0,05% salida"},{"id":"ORD-005","tipo":"condicionada","estrategia":"P05c (k=1,0)","activacion":"cierre 15m > 82.957,47 -> limite compra; cierre 15m < 78.581,87 -> limite venta; 60 min","stop":"cierre 15m que vuelve a 80.769,67","vence":"23:45 UTC 25-10","cierre_max":"23:59 UTC"},{"id":"AZ-005","tipo":"testigo de ORD-004 y CL-003/004","lado":"corto (SystemRandom)","entrada":"2026-10-25 08:30 UTC, apertura del minuto en Coinbase","stop":"cierre 15m 1.094 USD en contra","cierre_max":"23:59 UTC 25-10","marca_14:04":"entrada 80.287,21; +0,07%"},{"id":"AZ-006","tipo":"testigo de ORD-005","lado":"corto (SystemRandom)","entrada":"2026-10-25 10:00 UTC, apertura del minuto en Coinbase","stop":"cierre 15m 2.188 USD en contra","cierre_max":"23:59 UTC 25-10","marca_14:04":"entrada 80.224,13; -0,00%"},{"id":"ORD-006","tipo":"condicionada por hora","estrategia":"P11","lado":"largo","activacion":"apertura 00:00 UTC 26-10 (Coinbase BTC-USD)","stop":"3%","cierre_max":"23:59 UTC 26-10","comision":"0,05% por lado"},{"id":"AZ-007","tipo":"testigo de CL-005/006 y ORD-004","lado":"largo (SystemRandom)","entrada":"2026-10-25 18:49 UTC, apertura del minuto en Coinbase","stop":"cierre 15m 1.094 USD en contra","cierre_max":"23:59 UTC 25-10"},{"id":"AZ-008","tipo":"testigo de CL-007/ORD-006","lado":"largo (SystemRandom)","entrada":"2026-10-26 00:00 UTC Coinbase","stop":"3%","cierre_max":"23:59 UTC 26-10"}],"operaciones_cerradas":[{"id":"AZ-001","estrategia":"azar (testigo E01/P04)","lado":"corto","entrada":"2026-10-24 22:53 UTC 80.508,77 Coinbase","salida":"2026-10-24 23:59 UTC 80.769,67 (fin de dia)","bruto_pct":-0.324,"neto_pct":-0.424},{"id":"ORD-001","estrategia":"E01 reglas (corto techo)","resultado":"no activada: vencio 04:55 UTC 25-10; maximo 80.925 (Coinbase) frente a 81.791,8","cuenta_como_operacion":false},{"id":"ORD-002","estrategia":"E09 tomador","resultado":"no activada hasta 04:55 UTC: cierres de 15m entre 80.390 y 80.869","cuenta_como_operacion":false},{"id":"ORD-003","estrategia":"P05b sistematica 25-10 (ventana hasta 08:00)","resultado":"no activada hasta 08:00 UTC; maximo 80.925, minimo 80.310","cuenta_como_operacion":false},{"id":"CL-001","libro":"CLAUDE","resultado":"no activada (vencio 08:00 UTC)"},{"id":"CL-002","libro":"CLAUDE","resultado":"no activada (vencio 08:00 UTC)"},{"id":"CL-003/CL-004","resultado":"no activadas: cierres de 15m entre 80.068,88 y 80.513,70 (Coinbase) de 08:15 a 14:00 UTC; vencieron 14:00 UTC","cuenta_como_operacion":false}],"marcador":{"papel":{"azar":{"operaciones":1,"aciertos":0,"neto_pct":-0.424,"abiertas":7},"E01":{"operaciones":0,"ordenes_no_activadas":1},"E09":{"operaciones":0,"ordenes_no_activadas":1},"P05b":{"operaciones":0,"ordenes_no_activadas":1},"P05c":{"operaciones":0},"CLAUDE":{"operaciones":0,"ordenes_no_activadas":4},"P11":{"operaciones":0,"abiertas":["ORD-006"]}},"backtest":{"E01_reglas":"429 ops -1,7% (p83)","P04":"539 -52,4%","P01":"3667 -336,2%","E03":"2757 -283,6%","P02":"2047 -221,8%","E04":"753 -40,3%","P03":"394 -28,5%","E05":"753 -85,1%","E09_0.05":"497 -21,5%, prueba -3,6%","E12":"340 -24,1%","P06_0.05":"373 -21,9%","P05b_v4_futuros_2020_2026":"1.012 ops +57,5% (0,07%), doble -13,3%; walk-forward 598 OOS +28,6%, doble -13,2%, p96","P05c_k1":"2020-24 221 +47,0%; 2024-26 121 -4,5%","P07":"221 +7,1%","P10":"prueba 2024-2026: 1.020 ops, bruto +43,0% (p98 vs azar), neto 0,10% -59,0%, doble -161%: descartada","P11_lunes_UTC_stop3":"355 ops 2020-2026, +109,0% neto 0,10%, doble +73,5%, p99; tras publicacion 38 ops +12,0% (p82); 2022 -8,9, 2025 -19,7","filtro_claude_P05b":"20 senales ciegas: tomadas 13 -3,58% vs todas -1,73% (p23)"}},"libro_claude":{"saldo_cop":40000,"saldo_usdt_ref":12.59,"pct":0.0,"plan_riesgo":"3% por op, 15% abierto, -15% dia, -20% semana; P05b a 1,5% mientras sea fragil","abiertas":[{"id":"CL-005","tipo":"condicionada","lado":"largo","decision_utc":"2026-10-25 14:10","precio_ref":"80.265,21 Coinbase BTC-USD (Kraken 80.271,0)","activacion":"cierre 15m > 81.863,57 -> limite compra 81.863,57 valida 60 min (creador)","stop":"cierre 15m < 80.769,67 (apertura 00 UTC)","objetivo":"ninguno; cierre 23:59 UTC","vence":"senal hasta 23:45 UTC 25-10","tamano":"riesgo 1,5% = 600 COP; stop 1,35% -> nocional 1,11x saldo","confianza":4,"estrategia":"P05b","razon":"unica con ventaja bruta sostenida 2020-2026; compresion (rango 1h 0,31% vs 0,49% de 14 dias); a mercado nada paga 3x la comision"},{"id":"CL-006","tipo":"condicionada","lado":"corto","decision_utc":"2026-10-25 14:10","activacion":"cierre 15m < 79.675,77 -> limite venta 79.675,77 valida 60 min","stop":"cierre 15m > 80.769,67","vence":"23:45 UTC 25-10","tamano":"riesgo 1,5%","confianza":4,"estrategia":"P05b","razon":"simetrica; precio a 0,69% del nivel inferior"},{"id":"CL-007","tipo":"condicionada por hora","lado":"largo","decision_utc":"2026-10-25 14:10","activacion":"compra a mercado (tomador) en la apertura del minuto 00:00 UTC del lunes 26-10 (referencia Coinbase BTC-USD)","ventana_de_activacion":"00:00-00:05 UTC","stop":"3% bajo la entrada","objetivo":"ninguno","cierre_max":"23:59 UTC 26-10","tamano":"riesgo 1,5% = 600 COP -> nocional 0,5x saldo","confianza":5,"estrategia":"P11 (E22 dentro del dia UTC)","razon":"lunes 00-23:59 UTC con stop 3%: 355 ops 2020-2026, media bruta +0,41% vs +0,03% resto de dias (p99); +12,0% neto en 38 ops tras la publicacion (p82); 2022 y 2025 perdieron: medio tamano"}],"cerradas":[],"no_activadas":["CL-001","CL-002","CL-003","CL-004"]},"diario_claude":[{"utc":"2026-10-25 02:07","precio":80861.99,"fuente":"Coinbase BTC-USD","contexto":"6h +0,47%, vol 0,42%; pend60h -0,029%/h, range_pos 0,60; domingo","decision":"esperar; CL-001 y CL-002 (P05b) hasta 08:00 UTC","confianza":5,"resultado":"no se activaron: el precio se quedo entre 80.310 y 80.925. Esperar fue correcto: 6 h con rango de 0,77%, menos que 3x la comision para una entrada de tomador con objetivo cercano","causa":"buena lectura (volatilidad baja)"},{"utc":"2026-10-25 08:12","precio":80504.06,"fuente":"Coinbase BTC-USD","contexto":"6h -0,32%, rango 0,77%, vol 0,41%; 24h -0,09%, rango 2,30%; pend60h -0,035%/h, pend12h +0,012%/h, range_pos60h 0,50; rango medio 1h 0,30% (limite de R1); domingo; FOMC 28-10","decision":"esperar; CL-003 y CL-004 (P05b) a medio riesgo hasta 14:00 UTC","razon":"(1) sin senal con ventaja a precio de mercado; (2) R1 en el limite: el movimiento esperado no paga 3x la comision; (3) la compresion suele romper (ciegas), por eso dejo la horquilla de P05b en los dos lados","confianza":4,"resultado":"pendiente"},{"hora_utc":"2026-10-25 14:00 (cierre)","ids":"CL-003/CL-004","resultado":"no activadas","por_que":"buena lectura de la baja volatilidad; rango 08:12-14:00 de 79.973 a 80.549 (0,72%)"},{"hora_utc":"2026-10-25 14:10","precio":"80.265,21 Coinbase","contexto":"domingo; 6h -0,04% rango 0,72%; 24h rango 2,30%; 60h -1,94%, pend60h -0,033%/h, range_pos 0,41; rango medio 1h 0,31% vs 0,49% de 14 dias","decision":"esperar a mercado; horquilla P05b (CL-005/006) y largo del lunes P11 (CL-007)","razon":"(1) sin senal a mercado; (2) rango 1h 0,31%: no paga 3x la comision (R1, R2); (3) ventajas medidas: banda de P05b y lunes UTC (P11, verificado hoy)","confianza":"4 (P05b), 5 (P11)","vigilancia_en_vivo":"no: ningun nivel a menos de 0,69%","resultado":"pendiente"}],"reglas_de_claude":["R1 No abrir a mercado con rango medio de 1h < 0,30%; dejar ordenes condicionadas en niveles con ventaja medida (P05b, P11).","R2 Entrar solo si el movimiento esperado supera 3 veces la comision de ida y vuelta (>=0,30% a 0,05%/lado).","R3 Preferir entrada de creador en el nivel (P05b: +28,6% en 598 ops OOS con 0,07%, +10,7% de tomador).","R4 Sin aperturas nuevas entre 17:00 y 21:00 UTC del 28-10 (FOMC 18:00 UTC); el resto del 27-28 a medio tamano.","R5 Pocas y buenas: maximo 3 entradas propias por dia; ante la duda, nada.","R6 Caida brusca (>1,5% en <3 h) en tendencia de 60h no bajista: rebote largo candidato (ciegas: 2 de 4; M07 del 25-10 14 quedo plano).","R7 No seguir la pendiente de 12h por si sola (P08 descartada).","R8 (cambia 25-10 14) La compresion anticipa movimiento, pero romper el rango de 12h solo da +0,04% bruto por op (P10: 1.020 ops en prueba, -59% neto): no operarla de forma sistematica; a ciegas, solo con el lado de R11.","R9 No vender el rebote dentro de una tendencia bajista si el 1m sube sin pausa por encima de los maximos de las ultimas horas.","R10 Tamano de P05b y P11 a 1,5% de riesgo: su caida de cuenta a 3% rompe el tope semanal del 20%.","R11 (nueva 25-10 14) En compresion, el lado lo da la pendiente de 60h; si |pend60h| < 0,02%/h, no operar (ciegas: M10 -0,42 y M12 -0,06 con pendiente ~0; M17 +0,77 con -0,057).","R12 (nueva 25-10 14) Corto de continuacion con pend60h <= -0,1%/h y range_pos60h <= 0,2 sin subida sostenida en 1m: 2 de 2 a ciegas (M05 +1,90, M13 +0,72).","R13 (nueva 25-10 14) No dar confianza 5 por la fuerza de un impulso: las de 5 rinden +0,13% de media en 6 ops frente a +0,50% de las de 4 en 10. Tamano igual por confianza hasta 30 ops.","R14 (nueva 25-10 14) No filtrar P05b por pendiente de 60h ni range_pos: a ciegas mi filtro resto (13 tomadas -3,58% vs 20 todas -1,73%, percentil 23), como P07. P05b se toma entera o no se toma.","R15 (nueva 25-10 14) Lunes UTC: largo de 00:00 a 23:59 con stop 3% (P11) a riesgo 1,5%, salvo evento fuerte ese dia."],"calibracion":{"conf3":{"ops":4,"media_pct":0.47},"conf4":{"ops":10,"media_pct":0.498},"conf5":{"ops":6,"media_pct":0.129},"nota":"20 ops a ciegas: la confianza 5 rinde menos que la 3-4 por tercera sesion (R13). Filtro P05b: 4 tomas de confianza 6, media -0,27%."},"ciegas":{"usados_epoch_utc":[1761530700,1761717180,1762347060,1764112260,1764399660,1764582600,1765215600,1765428300,1765636440,1765884240,1766140140,1766566320,1767968460,1768267680,1768354980,1769848560,1770031200,1770426840,1770842160,1771451760,1771585440,1771790280,1773168060,1773373320,1773671940,1773910560,1775322240,1775497020,1777063020,1778063160,1778157120,1778309220,1778660340,1780491360,1780882380,1781125140,1781234400,1781445420,1782679620,1783014420,1783690500,1783877940,1784101560,1784222520,1784876880,1785202800,1785592980,1785843180,1787083560,1787260500,1787601720,1788035880,1788882000,1789113180,1789264800,1789956960,1790856180,1791819000,1792237920,1792478460],"usados_formato":"epoch UTC del minuto de decision","sesiones":[{"fecha":"25-10-2026 02:10 UTC","datos":"spot BTCUSDT","semilla":20261025,"decisiones":20,"activas":6,"aciertos":4,"neto_suma_pct":3.042,"azar_media_pct":-0.334,"percentil":90},{"fecha":"25-10-2026 08:09 UTC","datos":"futuros USDM BTCUSDT","semilla":20261025008,"decisiones":20,"activas":7,"aciertos":3,"neto_suma_pct":1.603,"azar_media_pct":0.183,"percentil":62,"sha256_decisiones":"05f15a70bce49dac01a492ed4be931295287957e3f86c8e93024bf3fa6ec9b6f"},{"fecha":"25-10-2026 14:07 UTC","datos":"futuros USDM BTCUSDT","semilla":20261025014,"decisiones":20,"activas":7,"aciertos":4,"neto_suma_pct":2.989,"azar_media_pct":-0.483,"percentil":95,"sha256_decisiones":"ecff03866a133fd89485d8b48bc0a8080313972c1453e107c24ee5b34a17edfd","detalle":"M02 L +0,09 t; M05 C +1,90 obj; M07 L -0,00 t; M10 L -0,42 t; M12 L -0,06 t; M13 C +0,72 t; M17 C +0,77 t"}],"marcador":{"decisiones":60,"activas":20,"aciertos":11,"neto_suma_pct":7.634,"azar_media_pct":-0.634,"ventaja_pct":8.268,"percentiles_por_sesion":[90,62,95]},"filtro_p05b":{"sesiones":[{"fecha":"25-10-2026 14:15 UTC","semilla":2610251,"senales":20,"de_un_total_12m":158,"tomadas":13,"neto_tomadas_pct":-3.58,"neto_todas_pct":-1.73,"neto_vetadas_pct":1.85,"percentil_vs_subconjuntos_al_azar":23,"sha256":"02a2e5bbb0a76336ea9f4ff446143bad709d5a6c1f9c5d6881bb9fbf6289d414","criterio_usado":"tomar si pend60h alineada (|>=0,01|) y range_pos alineado; vetar despues del minuto 1320"}],"usados_epoch_ei":[3495676,3335266,3164670,3304250,3216544,3264357,3368385,3531094,3131939,3166950,3122581,3128628,3480997,3325769,3419160,3259392,3076785,3577816,3172536,3333722],"conclusion":"filtrar por tendencia resta; ver R14"}},"criterio_dinero_real":{"propuesto":"25-10-2026","condiciones":["Al menos 200 operaciones fuera de muestra (walk-forward) y 60 de papel en vivo en el libro CLAUDE durante 4 semanas o mas","Neto positivo con la comision real y no negativo con el doble","Superar al azar al percentil 95 o mas, en prueba y en papel","Peor racha <= 10 y caida maxima de la cuenta <= 15% con el tamano que se usara","Ciegas: 100 decisiones activas o mas con percentil >= 90","Autorizacion de Nicolas tras revisar el plan (tema 14)"],"estado_25-10_08UTC":"P05b: 598 ops OOS (cumple), neto +28,6% con 0,07% (cumple), doble -13,2% (no), p96 bruto (cumple), racha 8 (cumple), caida de cuenta 22% a 1,5% de riesgo y 30-47% a 3% (no); papel CLAUDE 0 de 60 (no); ciegas 13 de 100 activas (no). Faltan 4 de 7.","estado_25-10_14UTC":"P05b: 598 ops OOS (cumple), +28,6% con 0,07% (cumple), doble -13,2% (no), p96 (cumple), racha 8 (cumple), caida de cuenta 22% a 1,5% (no); papel CLAUDE 0 de 60 (no); ciegas 20 de 100 activas, percentiles 90/62/95 (no). Faltan 4 de 7. P11 no aplica: 1 op por semana, 38 ops fuera de muestra."},"fuentes_datos":{"abiertas_25-10":["data.binance.vision (futuros um klines 1m y fundingRate, spot)","http://api.exchange.coinbase.com","http://api.telegram.org","http://arxiv.org","http://github.com (web)","http://concretumgroup.com","http://binance.com/en/futures/trading-rules/perpetual","http://binance.com support FAQ comisiones"],"comisiones_binance":"futuros USDM usuario regular 0,02% creador / 0,05% tomador (FAQ 360033544231, actualizada 01-05-2026), 10% de descuento pagando con BNB; spot VIP0 0,10% (0,075% con BNB); BTC/FDUSD tomador normal desde 29-01-2026; financiacion cada 8 h","reglas_BTCUSDT_perpetuo":"http://binance.com/en/futures/trading-rules/perpetual (leida 25-10): cantidad minima 0,001 BTC, nocional minimo 50 USDT, paso de precio 0,10, max mercado/limite 120/1000 BTC, tope de precio limite 3%; paso de cantidad no mostrado (probable 0,001, sin confirmar)","bloqueadas":["http://api.binance.com y http://fapi.binance.com (451/restringido)","SSRN","MDPI","Elsevier","Medium","http://nof1.ai/blog (404)","api de GitHub (403)"]},"temas":{"hechos":["0 (24-10 17:48)","7 (25-10: comisiones reales y funding aplicados a E09/P05b)","1 en lo esencial (Alpha Arena T1 y T1.5, Agent Market Arena, LiveMACE, E26)","14 parcial (25-10 08: capital minimo para BTCUSDT perpetuo)","4 en parte (25-10 14: filtro a ciegas de 20 senales de P05b: resta)"],"siguiente":"12 (otros mercados: ETH y SOL con P05b y P11 en futuros de Binance) y repetir el filtro de P05b con otra regla"},"telegram_atendidos":[765,766,767],"correcciones":["v1: fuentes dadas por bloqueadas; abren desde 24-10 17:15.","v1: P04/P01/P02 dadas como prometedoras; descartadas.","v3: la pasada del 24-10 18:11 se corto sin correo; P06 '+2,03' sin comision: con 0,05% da -21,9%.","v3: E09 496 ops/-19,9% en v2; con el 24-10, 497/-21,5%.","v4: P05b en el tramo de prueba daba +4,9% (84 ops) con velas spot; con velas de futuros USDM, que es donde se operaria, da 0,0% (80 ops). Las cifras de futuros mandan.","v4: los indices de ciegas se guardan ahora como epoch UTC (conversion exacta, el archivo spot no tenia huecos).","25-10 14: R6 decia 2 de 3; con M07 de esta sesion (plano, -0,003%) queda en 2 de 4."],"lecciones":["Con 0,05% por lado ninguna de 10 variantes intradia es positiva neta; el limite es el costo.","Las reglas de la MEZCLA sin clasificador empatan; forzar cierre diario la mata.","Mas frecuencia sola no sirve; hay que bajar el costo o capturar mas movimiento por operacion.","25-10: la forma de entrar decide: E09 con limite en la banda (P05b) paga creador y mejora el precio.","25-10 08: P05b sobrevive a 2020-2024 sin tocar parametros (679 ops, +41,1% neto, p97 bruto) y a walk-forward (598 ops, +28,6%), pero la rejilla es dentada (k 0,4, 0,6, 0,65 y 0,9 pierden), 2022 y 2025 pierden, y con costo doble pierde: la ventaja bruta (~0,13% por op) es real, el margen neto es fino.","25-10 08: la financiacion de futuros es despreciable en P05b (-0,001% por op) porque nunca cruza 00:00 y rara vez 08:00/16:00 con posicion.","25-10 08: a ciegas, la compresion de volatilidad precedio movimientos de 1,7-2% en 6 h en 4 de 5 casos; quedarse fuera los perdio; la direccion no se ve: horquilla (R8, P10).","Investigacion 25-10: un banco independiente con los mismos datos (E24) rechaza 18 de 18 ideas intradia en BTC con costo realista, y E26 muestra que el paso de backtest a dinero real se come la ventaja: hay que exigir papel en vivo antes de dinero.","25-10 14: la compresion tiene ventaja bruta real (P10 p98 frente al azar en prueba) pero de solo +0,04% por op: menor que cualquier comision. Movimiento anticipado no es ganancia.","25-10 14: filtrar P05b por la tendencia de 60h resta (a ciegas y en P07): el rompimiento funciona tambien contra la tendencia; no lo toco.","25-10 14: el efecto del lunes (E22) se sostiene en 2020-2026 dentro del dia UTC y despues de su publicacion, pero con anios perdedores (2022, 2025): P11 a medio riesgo.","25-10 14: a ciegas, los cortos de continuacion en tendencia bajista fuerte ganaron (2 de 2) y los largos de confianza 5 tras impulso no: mi confianza alta esta mal calibrada."]}
#### FIN REGISTRO ####