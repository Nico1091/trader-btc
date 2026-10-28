# Preregistro del plan diario (fijado el 28/10/2026, antes de descargar LINK, AVAX, LTC, DOT y TRX)

Este archivo se escribe y se sube **antes** de mirar los activos nuevos. Ninguna regla, umbral ni criterio de aquí se cambia después de ver sus resultados. Lo que no pase se queda fuera, y se dice.

## 1. Lo que se quiere probar

Salen de `a2_combinaciones.txt` y `a3_ingenieria_inversa.txt` (28/10/2026). Se eligieron mirando 2020-2023 de 7 activos, así que todavía no son evidencia independiente.

| Id | Hipótesis | Definición exacta, solo con datos anteriores a la entrada |
|---|---|---|
| H1 | N8 gana más con volatilidad alta | Opera solo si ATR14 diario / apertura del día > mediana de ese mismo cociente en los 365 días anteriores del activo |
| H2 | P11 gana más con la 1 h y el 1 d a favor | Opera solo si la última vela cerrada de 1 h y la de 1 d cierran sobre su EMA 20 (`Marco.a_favor`, como hoy) |
| H3 | P05c gana más con el contexto lejos de la SMA 50 y sin señales tardías | Opera solo si \|cierre de ayer / SMA 50 − 1\| > mediana de ese valor en los 365 días anteriores, y la señal es antes de las 17:00 UTC |
| H4 | La cartera LC* rinde más que el libro actual | P05c en todos los activos + P05b, P11 y N8 de BTC, 5 % de riesgo por operación, hasta 3 posiciones, comisión de futuros base |
| H5 | El corto de continuación R11 gana en tendencia bajista | Al cierre de cada vela de 1 h: pendiente de las 60 h ≤ −0,10 %/h y posición en el rango de 60 h ≤ 0,20 → corto a la apertura siguiente, stop 2,5 %, salida a las 6 h, tomador en las dos puntas |
| H6 | Reabrir tras la parada total no destruye la cuenta | Tras tocar la parada total: 30 días quieto y vuelta con la mitad del riesgo; la segunda parada es definitiva |

## 2. Datos nuevos

- Futuros USDⓈ-M de 1 minuto de data.binance.vision, con SHA-256: LINKUSDT, AVAXUSDT, LTCUSDT, DOTUSDT y TRXUSDT, desde que existan hasta el 27/10/2026.
- Si alguno no tiene datos desde 2021 o antes, se sustituye **antes de mirar resultados** por el siguiente de esta lista: BCHUSDT, ATOMUSDT, XLMUSDT.
- Las operaciones se generan con `investigacion/c1_operaciones.py`, sin tocar el motor.

## 3. Criterio de adopción (el mismo de `investigacion/PREREGISTRO.md`)

Una hipótesis se adopta solo si cumple las tres condiciones:
1. **En los 5 activos nuevos:** mejora la media neta con comisión doble en 4 de 5 o más, y el intervalo del 90 % (bootstrap por meses) de la media conjunta con la regla no incluye el cero.
2. **En los 7 activos ya vistos:** con la definición causal de arriba, mejora en 2020-2023 y en 2024-2026.
3. **Riesgo:** no empeora la caída máxima más de un 20 % y conserva al menos el 30 % de las operaciones.

Para H4 y H6 se compara el crecimiento por día y la caída máxima de la cartera en los 5 activos nuevos más BTC, frente al libro actual (P05c > P11 > P05b de BTC, una posición), con el mismo riesgo.

## 4. Qué NO se hace

- No se prueban variantes de umbral (365 días, 17:00 UTC, −0,10 %/h, 0,20, 2,5 %, 6 h, 30 días) después de mirar.
- No se adopta nada por ganar en un solo tramo o en un solo activo.
- Nada de esto toca dinero real: lo que pase entra al papel, en los libros de `consolidacion/plan_diario.py`, y decide Nicolás con 30 operaciones ejecutadas.
