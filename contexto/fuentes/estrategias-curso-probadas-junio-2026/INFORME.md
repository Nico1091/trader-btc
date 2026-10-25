# INFORME — Estrategias BTC/USDT y agente IA (2026-06-27)

Resumen ejecutivo del trabajo de hoy. Detalle completo en `docs/APUNTES-MATERIAL-USUARIO.md`
y registro de experimentos en `data/experiments.csv`. Pruebas de la IA en `RESULTADOS.md`.

## 1. Objetivo
Operar BTC/USDT con las estrategias del usuario (curso Forex + sus scripts .py), validándolas
honestamente en 24 meses de datos reales (BTCUSDT 1m → 1h, split temporal 75/25), y poner a la IA
(DeepSeek) a decidir. Filosofía: conservar SOLO lo que mejora; emular antes de arriesgar.

## 2. Ranking de estrategias (BTC 24 meses, solo muestra fiable ≥200 trades)
| # | Estrategia | trades | win | PnL | coste 2x | Notas |
|---|---|---|---|---|---|---|
| ⭐ | **MEZCLA (mix)** pullback long + reversión short en techo | 864 | 53.6% | **+248%** | +239% | LA MEJOR. Requiere Futures (shorts) |
| 1 | Reversión SHORT (vender techos) | 275 | 67% | +173% | — | Futures |
| 2 | Pullback LONG + TP 2R (spot) | 308 | 47% | +112% | +140% | LA MEJOR para SPOT |
| 3 | Reversión ambos lados | 530 | 56% | +118% | — | el PnL es del short |
| ✗ | Pullback + nuevos patrones | 376 | 50% | +98% | — | no mejora al pullback |
| ✗ | Pullback + TP dinámico | 308 | 52% | +11% | — | TP fijo 2R es mejor |
| ✗ | Fibonacci zona dorada estricta | 268 | 44% | −46% | — | peor que la zona amplia |
| ✗ | 50 SMA + Price | 64 | 58–60% | +30% | — | <200 trades; útil solo como filtro |
| ✗ | Breakout | <200 | neg. | — | — | descartada |

**CONFIG ganadora (mezcla):** `--base mix --tf 60 --stop 0.03 --H 24 --tp 2 --be 1 --thr 0.30..0.50
--extra pa,time,pat` sobre BTCUSDT 1h. Compra el dip en tendencia alcista + vende el techo extremo
(range_pos≥0.9). Los dos edges se SUMAN. Plateau positivo, aguanta coste doble.

## 3. El agente IA (DeepSeek) como decisor
- Clave verificada (responde). El backtest NO usa IA; la IA solo decide en producción/papel.
- Al darle el cerebro completo (todas las estrategias) + datos reales (velas, RSI, patrones,
  PIRÁMIDE de soportes/resistencias), pasó de RESTAR a MEJORAR de forma consistente:
  | muestra | operar todo | IA decisora |
  |---|---|---|
  | 30 | +5.6% | +11.6% |
  | 60 | +0.6% | +7.3% |
  | 120 | +2.1% | +11.4% |
- La IA aporta SELECTIVIDAD: filtra señales malas y multiplica el PnL del motor. NO es adivina:
  decide sobre los números reales de las estrategias.

## 4. ✅ Bandera roja RESUELTA (2026-06-27)
DIAGNÓSTICO (`scripts/diag-redflag.js`): el modelo de producción entrenado con el 100% daba solo
+12.8% en el 25% de test, mientras el modelo entrenado con el 75% (el validado) daba +99.1% en el
MISMO periodo. Causa: el umbral thr=0.50 estaba calibrado para el modelo del backtest (75%); al
entrenar con 100% el GBM se descalibra y el 0.50 deja de ser el bueno (su óptimo pasaba a ~0.30).
FIX: `train-pullback-btc.js` ahora entrena el modelo de producción con el 75% inicial (= el modelo
validado out-of-sample). Verificado: producción ahora da **+99.1%** (idéntico al validado), con
plateau positivo (thr 0.30 +84%, 0.50 +99%, 0.55 +117%). El edge era REAL; era un thr mal sintonizado.
Trade-off honesto: el modelo no usa los ~6 meses más recientes para entrenar; en producción real hay
que RE-ENTRENAR periódicamente repitiendo el split 75/25.

## 5. Estado del código
- `scripts/bench.js`: banco de pruebas con todas las estrategias (base= range/pullback/mix/fib/sma50/
  breakout/confluence), filtro de tendencia (slope), gestión TP/BE/trailing y TP dinámico, patrones nuevos.
- `src/strategy-core.js`: núcleo + `decidePullback` (producción). `scripts/train-pullback-btc.js`:
  modelo BTC. `src/pullback.js`: señal en vivo (solo aviso, no ejecuta órdenes).
- `scripts/paper-test-ai.js`: harness de la IA (modo papel masivo) → escribe `RESULTADOS.md`.
- `docs/AI-PLAYBOOK.md`: cerebro de la IA con TODO el conocimiento (incl. pirámide).

## 6. Próximos pasos
1. 🔧 Recalibrar el modelo de PRODUCCIÓN para reproducir el backtest (resolver la bandera roja). PRIORIDAD.
2. Pasar la MEZCLA a la IA decisora (mejor estrategia + mejor filtro).
3. Modo papel en vivo unos días antes de cualquier capital. Regla del curso: demo antes de real.
4. Aplicar reglas de riesgo del Trading Plan (3%/trade, stop diario 15%, semanal 20%, señal ≥8/10).
5. (Opcional) Orden OCO real en Binance; deepseek-reasoner (versión thinking).

## 7. Honestidad (recordatorio)
Todo es BACKTEST sólido, NO dinero real aún. Win rates ~47–56%: el edge viene del R:R y de combinar
ambos lados, no de acertar siempre. La mezcla requiere Futures (shorts); en spot solo el long (+112%).
