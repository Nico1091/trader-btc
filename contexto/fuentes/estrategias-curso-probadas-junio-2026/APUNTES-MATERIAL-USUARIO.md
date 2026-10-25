# APUNTES — Material de trading del usuario (analizado 2026-06-27)

Análisis de TODO el material que el usuario descargó/tiene, para alimentar el bot.
Objetivo declarado del usuario: operar **SOLO BTC/USDT**, swing/day trading.
Filosofía del proyecto (no cambia): emular ANTES de arriesgar; conservar solo lo que mejora
la métrica en split temporal; la IA (DeepSeek) es gate de decisión, NUNCA ejecuta real.

---

## 1) Scripts Python del usuario (curso Quantdemy, `python-binance`, Binance Spot REAL)

Ubicación: `C:\Users\ni109\Downloads\*.py` (BTCUSDT, RVNUSDT, GXSUSDT, MANAUSDT).
Son bots de **ejecución real** en Binance Spot. Solo COMPRAN (long), salen con orden **OCO**.

### Estrategia A — Tendencia por pendiente de MA (BTCUSDT.py, RVNUSDT.py)
- TF 15m. Calcula MA48 (cierre) y, sobre una serie de MAs, ajusta una recta con `np.polyfit`.
  Si la **pendiente > 0** => tendencia alcista.
- Entra (market buy) si tendencia alcista Y precio > MA48*0.995.
- Salida **OCO**: TP = +1% (`*1.01`), SL = -1% (`*0.99` / stopLimit `*0.985/0.994`).
- No re-compra si hay orden abierta.

### Estrategia B — Alineación de medias (GXSUSDT.py, MANAUSDT.py)
- TF 5m. Calcula MA5, MA10, MA20.
- Entra si **precio > MA5 > MA10 > MA20** (medias apiladas alcistas = momentum limpio).
- Salida **OCO**: TP = +1%, SL = -1% a -1.5%.
- Maneja balance real para dimensionar la venta y evitar errores LOT_SIZE / MIN_NOTIONAL.

### Lo RESCATABLE (técnicas a portar al bot)
1. **Orden OCO** (One-Cancels-Other): TP y SL atómicos en el exchange. Es la forma correcta de
   materializar el stop-loss + take-profit de las estrategias del curso Forex. (Para fase real.)
2. **Filtro de tendencia por pendiente de MA (`polyfit`)**: objetivo y barato. Útil como gate
   de "solo operar a favor de la tendencia mayor" (coincide con la Trend Following del curso).
3. **Alineación MA5>MA10>MA20** como confirmación de momentum.

### CRÍTICAS HONESTAS (no copiar tal cual)
- ⚠️ **R:R ≈ 1:1 (o peor)**: TP +1% / SL -1%. El propio curso Forex del usuario exige **R:R ≥ 1:1.5**
  (ideal 1:5). Con R:R 1:1 y comisiones, el edge se evapora. ESTO HAY QUE CAMBIARLO.
- ⚠️ **Solo long**: en cripto bajista te quedas sin operar o comprando caídas.
- ⚠️ **Sin position sizing por % de riesgo**: cantidad fija hardcodeada. El curso exige 1-3% por trade.
- ⚠️ Bugs ya anotados por el usuario en los .py (ma20, filters, identación). Son ejemplos de clase, no producción.
- ⚠️ TF 5m/15m: nuestro propio backtest demostró que 1m/30m NO tienen edge robusto; **1h sí**.
  Migrar la lógica a 1h (day trading) o 4h (swing), no a 5m.

---

## 2) Estrategias del curso Forex (carpeta `Downloads\revisar\`)

Ver también `forex-strategies-to-implement` en memoria. Resumen accionable:

### 50 SMA + PRICE
Patrón (doble/triple techo-suelo o H&S) → vela cruza y **cierra** al otro lado de la SMA50 sin
tocarla con el cuerpo → entrada. Re-entrada en retroceso que apoya en SMA50 + patrón de
continuación en nivel Fibonacci. SL al otro lado de SMA50 y S/R. **TP a 2R**. Breakeven a 1R.

### TREND FOLLOWING
Tendencia mayor en TF alto (1M/1W/1D/4H) → líneas de tendencia + zonas S/R → Fibonacci, entrar
solo en retroceso **50-60%** que cierra con patrón de vela en zona de confluencia. Entradas en
15M/1H/4H. SL bajo/sobre S/R previo. **TP a 3R**. Breakeven a 0.8-1R, trailing tras 2R.

### NÚCLEO (Risk & Money Management) — LO MÁS VALIOSO
- R:R mínimo **1:1.5** (ideal hasta 1:5). Predefinido SIEMPRE antes de entrar.
- Riesgo fijo **1-3%** del capital por trade. Position sizing = (capital × %riesgo) / (SL en pips/%).
- Stop-loss SIEMPRE. Breakeven al alcanzar ~1R. Trailing tras 2R.
- Mentalidad "casino": ganar es tener **expectativa positiva** sobre MUCHOS trades + disciplina.
- Proceso obligatorio: **Backtest 1-2 años → Demo 1-6 meses → Real**. (= nuestra metodología.)
- Checklist de entrada: solo operar con score ≥ 80% de criterios cumplidos.

---

## 3) Wtrader (PDFs) — referencia rápida
- **Estilos por timeframe**: Scalping 1-5m · Day Trading 15m-1h · Swing 4h-1d-1w · Posicional 1d-1w-1mn.
  Confirma: para "unas horas" = Day Trading en **1h** (justo donde nuestro bot tiene edge).
- **Mejores pares**: EUR/USD, USD/JPY, GBP/USD, AUD/USD, USD/CHF. → Forex, NO aplican a BTC. Ignorar.

## 4) Pendientes de revisar (grandes, baja prioridad para BTC spot ahora)
- `NT+EBook.pdf` (24MB, NavigationTrading): trading de **opciones** (call/put, spreads, griegas).
  No aplica a BTC/USDT spot. Útil solo si algún día se opera opciones. Ya hay apuntes en skill `trading-playbook`.
- `RL.zip` (105MB): posible Reinforcement Learning. Revisar si trae datasets/modelos aprovechables.
- `MT5_Python_Connector_Quantdemy_2023.zip`: conector MetaTrader5. Para Forex, no para Binance/BTC.

---

## 5) SÍNTESIS — qué incorporar al bot (BTC/USDT, 1h)

Estado actual del bot: estrategia ganadora = TOPES(1h) + confirm1 + STOP 3% + GBM thr0.45, validada
en ETH (+59% 24m). Falta validar en BTC y sumar las ideas del usuario.

Plan de incorporación (cada una se EMULA y solo se queda si mejora expectancy en BTC 24m):
1. **Línea base en BTC**: correr la estrategia ganadora actual sobre BTCUSDC-1m → 1h. (punto de partida)
2. **Filtro de tendencia (polyfit / SMA50 slope)**: operar topes/continuación SOLO a favor de la
   tendencia mayor. Hipótesis: sube win rate, reduce trades malos.
3. **R:R explícito 2R/3R + breakeven + trailing**: hoy el bot usa stop fijo y horizonte H; añadir
   gestión TP/BE/trailing al simulador para reflejar las reglas del curso.
4. **Alineación MA5>MA10>MA20** como feature/confirmación de momentum (probar como veto, no como amontonamiento).
5. **Fibonacci 50-60% retroceso** como zona de entrada (codificable).
6. (Fase real, futuro) **Orden OCO** en Binance para materializar TP/SL — copiado de los .py del usuario.

REGLA DE ORO (lección ya aprendida en PROGRESO.md): unificar NO es amontonar señales; es usar
confluencia para VETAR trades malos. Cada añadido se mide solo; si no mejora, se descarta.

---

## 6) HALLAZGOS al leer TODO el curso (35 docs completos, 2026-06-27)

### 6.1) Trading Plan del usuario (Trading+plan.xlsx) — REGLAS DE RIESGO CONCRETAS = ORO
Estas son LAS reglas del usuario. Codificables como guardrails duros del bot/journal:
- Riesgo máx **por trade = 3%**.
- Riesgo máx total en cuenta a la vez = **15%**.
- Pérdida diaria máxima permitida = **15%** (al alcanzarla: parar el día).
- Pérdida semanal máxima = **20%**.
- Calidad mínima de señal de entrada = **8/10** (checklist; solo operar señales ≥8).
- Retiros: cada 2 semanas de trading rentable, retirar **50%** de las ganancias.
- (Forex usaba sesiones London/NY/Sydney y "all major pairs"; en BTC = 24/7, no aplica sesión,
  pero la "hora UTC" ya es feature del bot y se puede medir si ciertas horas tienen edge.)

### 6.2) Trading Journal (Trading+Journal.xlsx)
Columnas: Date, B/S, Pair, Lot, Entry, SL, TP, **RR**, P/L, Balance. Nota: "Trend Following, 8|10".
=> Confirma: su estrategia principal es **Trend Following** con umbral de calidad **8/10**.
El bot ya tiene un journal (data/ai-journal.csv); alinear columnas con este formato.

### 6.3) Patrones de vela — qué tiene el bot y qué FALTA añadir
YA implementados en strategy-core/bench: hammer, shooting star, harami, morning/evening star,
piercing, dark cloud, breakout.
FALTAN (del curso, candidatos a probar como veto de confluencia, NO amontonar):
- **Engulfing** (alcista/bajista) — vela que envuelve por completo el cuerpo anterior. Potente.
- **Tweezer top/bottom** — dos máximos/mínimos casi iguales = reversión.
- **Three white soldiers / three black crows** — 3 velas crecientes del mismo color (≈ confirm del bot).
- **Doji** (long-legged, gravestone, dragonfly, four-price) — indecisión/reversión.
- **Spinning top** — indecisión.

### 6.4) Chart patterns (Technical+Analysis+-+Chart+Patterns)
Double/triple tops-bottoms, H&S e inverso, triángulos (simétrico/asc/desc), wedges, channels.
- El bot aproxima **double tops/bottoms** con `range_pos` (topes). ✔
- H&S, triángulos, wedges = discrecionales/difíciles de automatizar bien. Baja prioridad.

### 6.5) Indicadores (Indicators.pptx) — consejo que VALIDA nuestro enfoque
- 4 tipos: Trend (MA, MACD, Parabolic SAR, ADX), Volumen (OBV, MFI, ROC), Volatilidad
  (Bollinger, ATR), Momentum/Osciladores (RSI, Estocástico, CCI).
- ⚠️ Regla del curso: NO amontonar; usar **2-4** de categorías DISTINTAS (Trend+Momentum, etc.).
  Coincide 1:1 con la lección del bot. Candidatos a sumar como features: **ATR** (para stop dinámico),
  **MACD** (tendencia), **Bollinger** (volatilidad/topes). El bot ya tiene RSI y volatilidad.

### 6.6) Análisis fundamental (varios docs) — contexto, NO codificable ahora
Todo el bloque (NFP, CPI, GDP, FOMC, tasas, PMI, PPI) es de Forex. En cripto importan FOMC/CPI
(mueven BTC) pero requieren feed de calendario económico. Fuera de alcance del bot actual.
Idea futura: gate que evite operar minutos alrededor de releases macro de alto impacto.

### 6.7) Psicología (Trading+Psychology.pptx) — por qué el bot existe
Errores del trader perdedor: subir lote tras ganar, revancha tras perder, no usar stop, cerrar
ganancias muy pronto, cambiar de estrategia tras rachas. => El bot ELIMINA estos errores: reglas
en código, riesgo fijo, stop obligatorio, journal. La psicología es ~50% del éxito; automatizar la
disciplina ES la ventaja. (Refuerza no tocar las reglas tras una racha mala.)

---

## 7) PRÓXIMO PASO DE CONFIGURACIÓN (donde nos quedamos)
Línea base BTC ya corrida (exp `btc_base`): mejor thr0.50 → 214 trades, win 59.3%, +46% test.
HALLAZGO: en BTC el edge está en los **SHORT** (win 66-84%); los LONG son break-even.
⚠️ TENSIÓN CLAVE: el usuario quiere SPOT (solo long). El edge de reversión está en short
(necesita Futures/Margin = más riesgo). Decidir con el usuario: (a) Futures para shorts, o
(b) reconstruir un edge LONG (filtro de tendencia + retroceso Fibonacci, estilo Trend Following).
Siguiente experimento pendiente: aislar shorts (`--side short`) y luego probar filtro de tendencia.

### 7.1) RESULTADOS de la búsqueda de edge LONG en BTC (2026-06-27) — HONESTO
Se implementó el filtro de tendencia `--trend 1` (pendiente polyfit de la ventana, estilo .py del usuario).
Experimentos (BTCUSDC ~1 año, test ~0.25 año, stop 3%, H8, 20 features):
- `btc_long` (reversión, solo long): PnL negativo / break-even, <200 trades. SIN edge.
- `btc_long_break` (breakout long): PÉSIMO, PnL -25% a -30%, win 20-35%. Falsos rompimientos.
- `btc_long_cont` (continuación): win alto pero 1-11 trades = espejismo. Muestra inútil.
- `btc_long_trend` (dip en tendencia alcista): 1-12 trades, break-even. Muy restrictivo, no concluyente.
- `btc_trend_both` (ambos lados + tendencia): ~break-even; los pocos trades positivos son SHORT.

CONCLUSIÓN HONESTA: con ~1 año de BTC y esta mecánica (1 sola ventana, sin multi-timeframe),
NO aparece un edge LONG robusto con muestra ≥200. El ÚNICO edge robusto en BTC sigue siendo el
SHORT por reversión en topes (btc_base: shorts win 66-69%, ~200 trades). Forzar long = nadar
contra corriente. NO se implementa edge long sin datos/mecánica que lo respalden (filosofía del bot).

OPCIONES REALES (a decidir con el usuario):
(a) Conseguir 24 meses de BTC + Trend Following multi-timeframe (tendencia en TF alto, entrada en
    TF bajo) — esfuerzo alto, SIN garantía de edge.
(b) Aceptar que el edge es SHORT → Binance Futures con tamaño mínimo y stop estricto (más riesgo).
(c) Operar donde el edge YA está validado: ETH topes 1h (+59% 24m). El usuario quería BTC, pero
    el bot ya tiene una estrategia ganadora probada en ETH.

### 7.2) ✅ ÉXITO — EDGE LONG VALIDADO en BTC (Trend Following / pullback) (2026-06-27)
Se eligió la opción (a). Se descargaron 24 meses de **BTCUSDT** (1.05M velas 1m, 0 descartes) y se
implementó el modo `--base pullback` (comprar el retroceso Fibonacci [0.35-0.65] del rango A FAVOR
de la tendencia, pendiente polyfit de la ventana). GANADOR:

- **btc_pullback_long_24m** (coste 0.0005): thr 0.45 → **358 trades, win 50.8%, PnL +65.9%**,
  +0.184%/trade. Plateau positivo thr 0.30-0.55.
- **Estrés coste 2x** (0.001): thr 0.45 → **282 trades, win 54.6%, PnL +71.8%**, +0.255%/trade. AGUANTA.

Cumple las 4 validaciones del bot: 24m (incl. bear), plateau, muestra ≥200, estrés de coste. EDGE REAL.
Config ganadora: `--tf 60 --base pullback --side long --trend implícito(slope) --stop 0.03 --H 8
--extra pa,time,pat --thr 0.45` sobre BTCUSDT 1h.

NOTAS honestas:
- Win rate ~51-55% es MODESTO; el edge viene del R favorable (pnl/trade pequeño pero positivo).
  Funciona EN AGREGADO sobre muchos trades, NO trade a trade. Disciplina = todo.
- thr bajos (0.30-0.35) NO aguantan coste 2x → usar thr 0.45.
- Sigue siendo BACKTEST. Falta: portar `pullback` a producción (strategy-core.js/swing.js) y
  MODO PAPEL en vivo unos días ANTES de dinero real (regla del curso: demo 1-6 meses).

### 7.3) ✅✅ REFINAMIENTO con GESTIÓN DE SALIDA (2026-06-27) — casi DUPLICA el resultado
Se implementó en bench.js la gestión de salida del curso del usuario: `--tp` (R múltiplos), `--be`
(breakeven), `--trail` (trailing), simulada vela a vela con `fut[]` (convención conservadora:
peor caso intra-vela). Hallazgo: con H=8 (8h) la gestión avanzada casi no actúa (BTC no se mueve
6-9% en 8h). El edge del pullback vive en ~1 DÍA; a 2 días (H=48) se diluye y da negativo.

**CONFIG GANADORA FINAL:** `--tf 60 --base pullback --side long --stop 0.03 --H 24 --tp 2 --be 1 --thr 0.50`
sobre BTCUSDT 1h (24 meses):
- Coste 0.0005: **+112.7% PnL, win 47.1%, 308 trades**, +0.366%/trade. Plateau positivo todos los thr.
- Estrés coste 2x (0.001): **+140.4% PnL, win 48.0%, 229 trades**, +0.613%/trade. AGUANTA (mejora).

Confirma la intuición del usuario: faltaba la gestión de salida. Win rate ~47-48% pero R favorable
(TP 2R + breakeven + dejar correr 1 día) = el edge viene del tamaño de las ganancias, no de la
frecuencia. Exactamente lo que enseña su Risk Management.

NOTA sobre DeepSeek: el backtest NO usa IA (es 100% cuantitativo). DeepSeek solo actúa en producción
(src/ai-advisor.js, gate confirmar/vetar). Modelo por defecto = deepseek-chat. Para la versión
"thinking" = deepseek-reasoner (poner DEEPSEEK_MODEL=deepseek-reasoner en .env), PERO reasoner no
soporta response_format JSON ni temperature → habría que ajustar ai-advisor.js antes de usarlo.

PRÓXIMOS PASOS:
1. [HECHO] Portado a producción: `strategy-core.js` (slope + `decidePullback`, ETH intacto),
   `scripts/train-pullback-btc.js` (→ `data/btc-pullback-model.json`, 120 árboles, H=24, thr 0.50),
   `src/pullback.js` (señal en vivo BTC, SOLO LONG, modo aviso, NO ejecuta órdenes). Probado OK.
2. [HECHO] Modelo de producción BTC entrenado (H=24).
3. [PENDIENTE] Modo papel: correr `src/pullback.js` periódicamente y registrar señales+resultado
   unos días (regla del curso: demo antes de real). Falta loop/cron + journal de resultados.
4. [PENDIENTE] Aplicar reglas de riesgo del Trading Plan (3%/trade, stop diario 15%, semanal 20%,
   señal ≥8/10) como guardrails antes del paso a real.
5. [PENDIENTE/Opcional] Orden OCO en Binance (copiar de los .py) para el paso a real, con confirmación.
6. [PENDIENTE/Opcional] Ajustar ai-advisor.js para soportar deepseek-reasoner (versión thinking).

### 7.4) HARNESS DE PRUEBAS DEL AGENTE IA (2026-06-27) — el usuario quiere que opere la IA
Se verificó que DeepSeek RESPONDE (clave OK, deepseek-chat, ~4s). Se arregló el prompt del gate:
antes describía la estrategia VIEJA (reversión/topes) → la IA juzgaba mal el pullback (vetaba
range_pos 0.45 por "no es suelo"). Ahora el gate recibe `ctx.strategyDesc` + `ctx.slope`.
Nuevo `scripts/paper-test-ai.js`: pone a la IA a decidir sobre N señales históricas reales de
pullback (out-of-sample), simula el trade (stop/TP2R/BE) y ACUMULA en `RESULTADOS.md` (memoria),
comparando "operar TODO" vs "solo lo que aprobó la IA".

Hallazgos (muestra 30):
- IA original (2º pase ultra-escéptico): operó 2/30, win 0%, PnL -6.1% → RESTABA fuerte.
- Tras recalibrar el 2º pase (confiar en el edge validado, vetar solo ante riesgo concreto):
  operó 4/30, win 50%, PnL +4.0% (+1.0%/trade vs +0.19% del motor). Más selectiva, menos riesgo.

CONCLUSIÓN honesta: el EDGE vive en el MOTOR cuantitativo (+112% 24m). La IA NO lo supera en PnL
total; aporta SELECTIVIDAD/seguridad (menos trades, mejor PnL/trade). Arquitectura recomendada:
motor genera señal + IA filtra (calibrada). "Solo IA" rinde menos que el motor, pero con menos riesgo.
Corrida de 60 señales lanzada para estadística robusta (resultados acumulados en RESULTADOS.md).

### 7.5) RANKING DE ESTRATEGIAS en BTC 24m (gestión H24 + TP2R + BE1) — comparación limpia (split temporal)
Solo cuentan las que llegan a ≥200 trades (muestra fiable). PnL = suma log en el 25% de test.
| # | estrategia | mejor thr | trades | win | PnL | PnL/trade | nota |
|---|---|---|---|---|---|---|---|
| 1 | **Reversión SHORT (topes)** | 0.30 | 275 | 66.9% | **+173%** | +0.63% | LA MEJOR, pero SHORT = Futures (no spot) |
| 2 | Reversión BOTH | 0.40 | 530 | 55.7% | +118% | +0.22% | el PnL viene del short; el long resta (-32%) |
| 3 | **Pullback LONG** | 0.50 | 308 | 47.1% | +112% | +0.37% | LA MEJOR para SPOT (solo long) |
| 4 | Confluencia | — | <200 | — | bajo | — | no fiable (poca muestra) |
| 5 | Breakout | — | <200 | negativo | — | — | DESCARTADA (falsos rompimientos) |

CONCLUSIÓN: el edge MÁS FUERTE de BTC es VENDER los techos (reversión short, +173%, win 67%) —
consistente con btc_base. Para SPOT (solo comprar), la mejor es PULLBACK LONG (+112%).

### 7.6) 🚩 BANDERA ROJA — discrepancia backtest vs modo papel (INVESTIGAR antes de confiar)
El harness de IA mostró que "operar TODO" en el periodo reciente dio solo +0.6% (win 36.7%),
cuando el bench del MISMO periodo (pullback thr 0.50) promete +112%. Causa probable: el modelo de
PRODUCCIÓN se entrenó con el 100% de los datos, mientras el bench entrena 75% y evalúa el 25% no
visto; el thr 0.50 fue optimizado para el modelo del bench, NO para el de producción → selecciona
trades distintos (peores). LECCIÓN: el +112% del bench NO está reproducido en producción todavía.
ANTES de confiar / dinero real: re-validar el modelo de producción (entrenar 75%, medir 25% real,
recalibrar thr para ESE modelo). El modo papel hizo su trabajo: destapó que la implementación no
equivale al backtest.

### 7.7) IA DECISOR ÚNICO con cerebro completo (2026-06-27) — el usuario lo pidió
Se reescribió `docs/AI-PLAYBOOK.md` con TODO el conocimiento (pullback, reversión short, candlestick,
chart patterns, S/R, supply/demand, Fibonacci, trend following multi-TF, indicadores, PIRÁMIDE,
gestión de riesgo) y un sesgo EQUILIBRADO (operar con confluencia, no "esperar siempre"). Se enriqueció
el ctx pasado a la IA (rsi, patrones de vela, distancias a topes, R:R) en ai-advisor.js y paper-test-ai.js.
Resultado (30 señales): la IA pasó de RESTAR (-10.8%) a MEJORAR: operó 29/30, win 41.4%, +8.0% vs
+5.6% del motor. Matiz: ahora es PERMISIVA (opera casi todo, filtra poco) — el equilibrio fino aún
requiere calibración. El edge base sigue siendo del motor; la IA lo respeta y mejora marginalmente.
NOTA: persiste la bandera roja 7.6 (modelo de producción da +5.6% en este periodo, no el +112% del bench).

### 7.8) IA + VELAS + PIRÁMIDE S/R (2026-06-27) — el mejor resultado de la IA
A petición del usuario se enriqueció el ctx con: resumen de las últimas velas (color+tamaño), y la
PIRÁMIDE de soportes/resistencias (pivotes/swing highs-lows de la ventana, niveles % sobre/bajo el
precio). Funciones `srLevels()` y `candleSummary()` en paper-test-ai.js; el prompt del gate los muestra.
Resultado (30 señales): IA operó 24/30, win 45.8%, **PnL +11.6% vs +5.6% del motor** (casi el doble,
mejor win rate). AHORA SÍ FILTRA FINO (rechaza 6 malas). Evolución de la IA hoy: miedosa -6.1% →
recalibrada +4% → cerebro completo +8% (permisiva) → +velas+S/R +11.6% (filtra bien). Confirmando con 60.
PENDIENTE real (cuello de botella): la bandera roja 7.6 — el modelo de producción rinde +5.6% (no +112%)
en el periodo reciente; la IA lo duplica (+11.6%) pero el motor base debe re-validarse/recalibrarse.

### 7.9) ⭐ MEZCLA congruente (base=mix) — LA MEJOR estrategia (2026-06-27, idea del usuario)
Probadas e implementadas Fibonacci real, SMA50, TP dinámico y patrones nuevos (envolvente, 3 soldados,
tweezer, doji): NINGUNA superó al pullback solo (fib -46%, sma50 <200 trades, tp dinámico +11%,
patrones +98%). PERO mezclar las DOS mejores SÍ funcionó.
`base=mix` "compra barato/vende caro" (congruente): pullback LONG (dip en tendencia alcista) +
reversión SHORT en techo extremo (range_pos≥0.9, cualquier tendencia). Los dos edges se SUMAN:
- Coste 0.0005: thr 0.30 → 864 trades, win 53.6%, **+248%** (LONG +75% + SHORT +173%); thr 0.50 → +216%.
- Coste 2x: thr 0.50 → 393 trades, win 56.5%, **+239%**. Plateau positivo en TODOS los thr. AGUANTA.
NOTA: la 1ª versión "short solo en downtrend" falló (short operó 2 trades) porque en BTC vender techos
funciona en cualquier tendencia, no solo en bajadas. ⚠️ REQUIERE FUTURES (incluye shorts); en spot
solo el long (+112%). Sigue aplicando la bandera roja 7.6 (recalibrar modelo de producción).
CONFIG: `--base mix --tf 60 --stop 0.03 --H 24 --tp 2 --be 1 --thr 0.30..0.50 --extra pa,time,pat`.

### 7.10) ✅ BANDERA ROJA 7.6 RESUELTA (2026-06-27)
`scripts/diag-redflag.js` comparó, en el MISMO 25% de test: modelo 75% (validado) = +99.1% vs modelo
de producción 100% = +12.8%. Causa: el thr 0.50 estaba calibrado para el modelo 75%; entrenar con
100% descalibra el GBM (su óptimo pasaba a ~thr 0.30). FIX en `train-pullback-btc.js`: entrenar el
modelo de producción con el 75% inicial (= el validado). Verificado: producción ahora da +99.1%
(idéntico al backtest), plateau positivo (thr 0.30 +84%, 0.50 +99%, 0.55 +117%). El edge era REAL.
Trade-off: el modelo no entrena con los ~6 meses recientes; re-entrenar periódicamente repitiendo el split.
