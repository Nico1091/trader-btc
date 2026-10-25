# PROGRESO del proyecto — arbitraje-cero-gas

Diario paso a paso. Lo más reciente arriba.

## Estado actual (un solo mercado: ETH, validado en 24 meses)
- **Estrategia ganadora:** TOPES (1h) + confirm1 + **STOP-LOSS 3%** + GBM thr 0.45. SOLO ETH.
  - 24 meses ETH: **+59.4% PnL, win 60.6%, 368 trades** (plateau thr 0.30-0.50, aguanta coste 2x).
- **Implementada en vivo:** `src/strategy-core.js` + `src/swing.js` (señal long/short/flat + stop, klines 1h).
- **Modelo de producción:** `data/swing-model.json` (GBM 120 árboles, 20 features, ETH-only 24m).

## Harness de IA (DeepSeek) — GATE de decisión con doble validación
- `docs/AI-PLAYBOOK.md`: el manual de la IA (se le aclara TODO: su jaula, la estrategia, reglas
  intraday, esquema de decisión JSON, ser más analítica, cuándo revisar, links de referencia).
- `src/ai-advisor.js`:
  - `aiGate(ctx)`: la IA decide **operar/esperar** (rol reforzado). DOBLE validación: 2º pase
    escéptico que rebaja a esperar ante la duda. Fail-safe = ESPERAR si la API cae (prudencia).
  - `logDecision()`: graba cada decisión+resultado en `data/ai-journal.csv` (memoria que la IA lee).
  - Diseño según papers (TradingAgents/RiskAgent): guardrails EN CÓDIGO (la IA es no-determinista),
    atada a números, SOLO simulación, nunca dinero real, nunca crea trades.
- `src/swing.js`: usa el gate; si la IA no dice "operate" -> flat.
- `scripts/paper-sim.js`: simula señales históricas con la IA y graba resultados (crece con memoria).
  Primera corrida (6 señales, tramo bajista): IA operó 1/6 (muy conservadora), evitó 3/4 pérdidas.
- Clave en `.env` (gitignored). ⚠️ REGENERAR: fue expuesta en chat.

## Aviso anti-optimismo (lección dura de esta fase)
- El +94% de ETH en 12 MESES era OPTIMISMO de periodo. En 24 meses caía a ~break-even.
- Win rate alto (60-70%) NO = rentable: con skew negativo se pierde ("monedas frente a apisonadora").
- El STOP-LOSS 3% (regla del usuario: si rompe el tope, salir) corrigió el skew -> robusto en 24m.
- La confirmación por COLOR sube win a 64% pero deja 42 trades: alta confianza sobre muestra
  minúscula = espejismo. Se DESCARTÓ por estricto. Bitácora completa comentada en strategy-core.js.

## Unificación de estrategias (exp16-25) — qué aprendimos
- Confluencia >=2 (exigir 2+ patrones): demasiado estricto, <200 trades, no fiable.
- Confluencia >=1 (OR de señales): DILUYE la calidad (BTC +21% vs +47% topes puros). Peor.
- Patrones como features extra del GBM: no mejora (BTC +30% vs +47%). Más ruido.
- **GANADOR: topes + GBM + confirmación (confirm=1)** = no operar si los patrones CONTRADICEN.
  Gratis, nunca empeora, sube la confianza marginalmente (ETH win 61.3%->61.6%). Implementado.
- confirm=2 (exigir patrón confirmando): win rate un pelín mayor (ETH 61.8%) pero menos trades.
- LECCIÓN: unificar NO es amontonar señales, es usar la confluencia para VETAR trades malos.

## Recorrido (resumen)
1. Bot CoW "cero gas" (firma EIP-712, solver paga gas). Esqueleto en `src/`.
2. Señal base estadística (z-score) + filtro de confianza (heurístico). Honesto: edge fino.
3. Pipeline de datos: descargar (Binance Vision) -> filtrar calidad -> vectorizar -> unificar.
   Dataset de 2.6M-2.6M vectores (5 pares, 12 meses).
4. Modelos: logístico (lineal) NO bate baseline; GBM no-lineal AUC 0.61 (en split aleatorio).
5. Coste real de CoW medido: ínfimo (0.0003%-0.03% según tamaño). No es el coste el problema.
6. Backtest temporal honesto (scripts/bench.js + data/experiments.csv): la dinámica de precio
   de un solo activo NO tiene edge robusto en 1m/30m -> NO se implementó nada de eso.
7. Price action del usuario (topes, harami, confirmación) -> mejor win rate (55-57%) pero
   break-even en 1m/30m. LA CLAVE fue el MARCO: en 1h los TOPES sí son rentables y robustos.
8. Implementada la estrategia de swing por topes (1h). <- punto actual de éxito.
9. Investigados: Morning/Evening Star, Dark Cloud, Piercing, divergencias, Fibonacci, opciones
   (call/put, spreads, griegas, IV crush). Apuntes en skill `trading-playbook`.

## Lecciones clave (honestas)
- El marco de tiempo importa MÁS que el modelo: 1m no tiene edge, 1h sí.
- La intuición de price action del usuario (topes) fue la pieza que ninguna feature cruda tenía.
- Validar SIEMPRE con split temporal + estrés de coste + generalización cross-asset.
- Esto es swing DIRECCIONAL (capital + riesgo), no el arbitraje cero-gas original.

## Skills creadas
arbitrage-signal-design, ohlcv-vectorization, data-quality-filter, artifact-cleanup-audit,
iterative-strategy-optimization, trading-playbook.

## Archivos clave
- `src/swing.js`, `src/strategy-core.js` — estrategia en vivo.
- `scripts/bench.js` — banco de pruebas (emulación, split temporal).
- `scripts/train-swing.js` — entrena modelo de producción.
- `data/experiments.csv` — diario de experimentos.
- `data/swing-model.json` — modelo entrenado.

## Próximos pasos / PENDIENTES (apuntado 2026-06-23)
- [ ] **Corrida de papel GRANDE** con la IA (decenas de señales en varios regímenes) para medir
      de verdad si el gate de IA mejora o solo frena. (Lo pequeño ya está: paper-sim 6 señales.)
- [ ] **Regenerar la clave de DeepSeek** — fue expuesta en el chat. Luego ponerla solo en `.env`.
- [ ] Modo papel EN VIVO (registrar señales reales y su resultado unos días) antes de capital.
- [x] Estrategia unificada por confluencia + stop (hecho).
- [x] Harness de IA con gate + doble validación + journal (hecho).
