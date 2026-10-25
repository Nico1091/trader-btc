# Prueba propia en papel: lunes 26 y martes 27 de octubre de 2026

Escritas el **domingo 25/10/2026 a las 16:20 UTC** (11:20 en Colombia), antes de conocer el resultado. BTC-USD en Coinbase: 80.501. Solo papel. Precio de referencia: Coinbase BTC-USD, porque la API de Binance da 451 desde la nube. Las cierra `consolidacion/t6_ordenes.py cerrar <fecha>` con velas de 1 minuto.

Cuenta: 40.000 pesos (12,59 USDT a 3.177,85 COP/USDT). Plan de riesgo de la tarea 4: 1,5 % por operación (600 pesos), una posición a la vez, tope diario de −1.200 pesos y semanal de −2.400. Contado, solo largos y sin apalancamiento. Los cortos se anotan en papel y en porcentaje, como referencia de futuros, sin tamaño en pesos.

ATR14 diario estimado ahora: 2.153 USD (con el domingo sin cerrar). El definitivo se calcula a las 00:00 UTC con `t6_ordenes.py niveles <fecha>`. Las bandas se fijan entonces con la apertura real.

## Lunes 26/10

| Id | Estrategia | Entrada | Stop | Salida | Tamaño | Razón |
|---|---|---|---|---|---|---|
| PP-1 | P11 / N1 (largo del lunes UTC) | Compra a mercado en la apertura de las 00:00 UTC | 3 % bajo la entrada (≈78.085 si abre en 80.500) | 23:59 UTC | Nocional 6,29 USDT (20.000 pesos): riesgo 600 pesos | Única ventaja que resiste el doble de comisión en futuros: 353 ops, +104,6 % neto, +69,3 % con el doble, positiva en el ajuste y en la prueba (tarea 3). Es la misma operación que CL-007 de la rutina. |
| PP-2 | P05b k = 0,5 con veto de velas de 1 h | Primer cierre de 15 m fuera de apertura ± 0,5·ATR (≈ ±1.077) hasta las 23:45. Límite de creador en la banda, válido 60 min | Cierre de 15 m que vuelve a la apertura | 23:59 UTC | Si es largo: nocional = 600 pesos ÷ distancia al stop, con tope en el saldo | Mejor versión de P05b en la tarea 3: 689 ops, +87,8 % neto, +39,6 % con el doble, percentil 99/96. Se veta si en las 3 últimas velas de 1 h cerradas hay un patrón de lado contrario. |
| PP-3 | P05c k = 1,0, solo largo (N2c) | Primer cierre de 15 m sobre apertura + 1,0·ATR (≈ +2.153). Límite en la banda, 60 min | Cierre de 15 m que vuelve a la apertura | 23:59 UTC | Igual que PP-2 | En contado: 170 ops, +44,8 % neto y +10,8 % con el doble; muestra débil (menos de 200 ops). Unas 0,5 operaciones por semana: lo normal es que no se active. |
| AZ-P1 | Testigo al azar | Corto a mercado a las 15:41 UTC (sorteo de SystemRandom a las 16:20 UTC del 25/10) | 3 % en contra | 23:59 UTC | Igual que PP-1 | Contra qué se compara. |

Si se activan a la vez PP-1 y PP-2 en el mismo lado, solo se cuenta una posición en pesos (la primera). Las otras se anotan en porcentaje.

## Martes 27/10

| Id | Estrategia | Reglas | Tamaño |
|---|---|---|---|
| PP-4 | P05b k = 0,5 con veto 1 h | Las mismas de PP-2, con la apertura y el ATR del martes | **Medio riesgo (300 pesos)**: la Reserva Federal decide el 27 y el 28, y la regla R4 de la rutina baja el tamaño esos días |
| PP-5 | P05c k = 1,0, solo largo | Las mismas de PP-3 | Medio riesgo |
| AZ-P2 | Testigo al azar | Largo a mercado a las 11:15 UTC (sorteo de las 16:20 UTC del 25/10), stop 3 %, cierre 23:59 | Medio riesgo |

El martes no hay P11: es una sola operación por semana.

## Añadidas el 25/10 a las 16:32 UTC (antes del resultado): versiones «solo cuando debe»

Salen de la tarea 8 de `CONSOLIDACION-TRADING.md`: operar solo cuando las velas y el mercado confirman la señal. Se cierran con el mismo script.

| Id | Días | Regla | Tamaño |
|---|---|---|---|
| PP-1f | Lunes 26 | PP-1 **solo si** el cierre diario del domingo (Coinbase) está sobre su SMA 50. A las 16:30 UTC del domingo, el precio (80.547) estaba bajo la SMA 50 (81.812): si sigue así, **no opera**. | Igual que PP-1 |
| PP-6 | Lunes 26 y martes 27 | P05b k = 0,5 **solo largo**: primer cierre de 15 m sobre apertura + 0,5·ATR, y **solo si** en las 3 últimas velas de 1 h cerradas hay un patrón alcista del curso. Límite en la banda, 60 min; stop con un cierre de 15 m que vuelve a la apertura; salida a las 23:59 UTC. | 600 pesos de riesgo el lunes; 300 el martes (Reserva Federal) |

## Qué no hago y por qué

- No pongo más órdenes para llegar a tres al día. Lo medido dice que más frecuencia pierde por comisión (tarea 4).
- No opero la MEZCLA aunque ganara 3 de 3 la semana pasada. En 1.610 operaciones pierde −107 % neto, y una semana buena no lo cambia.

## Resultado

_(Se completa al cerrar con velas de 1 minuto. Si esta sesión ya no sigue viva, lo cierra la rutina en su pasada siguiente con el mismo script.)_
