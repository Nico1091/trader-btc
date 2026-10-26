# Guía de decisión de Claude: qué mirar, cuándo operar y cuándo no

Pedida por Nicolás el 26/10/2026. Claude decide cada operación. Los programas solo leen datos, resumen y cierran con velas reales. Todo es papel hasta que Nicolás apruebe otra cosa.

## 1. Antes de decidir: lectura en tiempo real con fotos

1. Correr `python3 -I consolidacion/lectura_mercado.py /tmp/lectura`. Tarda unos 2 segundos. Si dice «INCOMPLETA», **no operar**.
2. Leer `resumen.txt` y **mirar las 5 fotos**:

   | Foto | Qué mirar en ella |
   |---|---|
   | 3 meses (velas diarias) | La tendencia de fondo y si el precio está sobre o bajo su media de 20 |
   | 1 día (velas de 1 h) | Máximos y mínimos: ¿suben o bajan? |
   | 16 horas (velas de 15 min) | La estructura de hoy y dónde están los rechazos |
   | 3 horas (velas de 5 min) | El impulso actual y si hay un rebote o una caída fuerte en curso |
   | 5 min (última hora) | El riesgo inmediato: velas enormes, mechas de rechazo, volatilidad muy por encima de su media |

3. Anotar en el diario una línea por tiempo y cómo pesó en la decisión.

## 2. Estrategias con datos positivos (las únicas que se operan)

Medidas con 3,58 millones de velas de 1 minuto de Binance (2020-2026), ajuste 2020-2023 y prueba 2024-2026, con comisión y con el doble. Detalle en `CONSOLIDACION-TRADING.md`.

| Estrategia | Cuándo vale | Cifras |
|---|---|---|
| **P05b por régimen** | Contexto alcista: largo si un cierre de 15 m supera apertura 00:00 UTC + 0,5·ATR14. Contexto bajista: corto si un cierre de 15 m baja de apertura − 0,5·ATR14. Límite en la banda (60 min), stop con un cierre de 15 m que vuelve a la apertura, salida a las 23:59 UTC | 545 ops, +108 % neto, +70 % con el doble; 5 de 7 años positivos |
| **P11 con contexto** | Lunes 00:00 UTC, largo, solo si el cierre del domingo está sobre la SMA 50. Stop 3 %, salida a las 23:59 | 186 ops, +94 % neto, +75 % con el doble |
| P05c largo | Contexto alcista, rompimiento de apertura + 1,0·ATR14 | 170 ops, +67 %, +55 % con el doble (muestra débil) |
| Vela alcista de 1 h como confirmación de P05b largo | Opcional, solo en contexto alcista | Mejora en mi prueba (pct 99,9); la rutina midió percentil 38 en el ajuste: sin aclarar |

**Contexto** = cierre diario de ayer frente a su SMA 50. Es el único filtro de contexto que mejora en los dos tramos.

## 2b. Dos libros (pedido de Nicolás del 26/10)

Siempre con señal: sin señal de su regla, no hay operación en ningún libro.

- **Libro PRINCIPAL:** P05b por régimen, P11 con contexto y P05c largo. Se opera con el tamaño del plan.
- **Libro PRUEBA:** estrategias nuevas que se toman o se descartan con datos. Se opera en papel y en porcentaje, separado, para no mezclar resultados.
  - **N8, miércoles con contexto alcista:** 193 operaciones, +88 % neto y +69 % con el doble. El miércoles salió de mirar los 7 días: puede ser casualidad.
  - **N9, rango de Asia roto en Londres en el lado del contexto:** 829 operaciones, +160 % neto, pero solo +17,6 % en 2024-2026 (−9 % con el doble). Frágil.
  - **P05b largo con patrón alcista de vela de 1 h:** la rutina y esta sesión la midieron distinto (percentil 38 frente a 88): se prueba en vivo.
- **Descartadas el 26/10 antes del papel:** N4 (retroceso a la EMA 20), N5 (RSI + patrón), N6 (50 SMA + precio) y N7 (rompe el máximo o mínimo de ayer). Todas pierden en 2020-2026.
- **Ascenso y descenso:** una estrategia de PRUEBA pasa a PRINCIPAL con 30 operaciones de papel o más que ganen neto y superen al azar. Se descarta si con 30 no lo logra.
- `lectura_mercado.py` muestra en la sección «SEÑALES DE HOY» el estado de las 6 estrategias.

## 2c. Horarios: cada libro aparte, cada contexto en su lado (tarea 13, 26/10)

Horas en UTC; en Colombia son 5 horas menos.

| Libro | Estrategia | Lado según el contexto | Horario de señal | Salida |
|---|---|---|---|---|
| PRINCIPAL | P11 | Solo largo, con contexto alcista | Lunes 00:00 (19:00 del domingo en Colombia) | 23:59 o stop 3 % |
| PRINCIPAL | P05b por régimen | Largo con contexto alcista, corto con bajista | 00:00-21:00 (19:00-16:00 en Colombia) | 23:59 o stop |
| PRINCIPAL | P05c | Solo largo, con contexto alcista | 00:00-21:00 | 23:59 o stop |
| PRUEBA | N9 Asia-Londres | El del contexto | **07:00-13:00** (02:00-08:00 en Colombia) | 23:59 o stop |
| PRUEBA | N8 | Solo largo, con contexto alcista | Miércoles 00:00 | 23:59 o stop 3 % |
| PRUEBA | P05b largo + vela 1 h | Solo largo, con contexto alcista | 00:00-21:00 | 23:59 o stop |

**Por qué estas horas** (media neta por operación, 2020-2023 / 2024-2026):
- **P05b y P05c, 21:00 a 24:00:** P05b gana +0,04 / +0,04 % y P05c pierde (−0,43 / −0,12 %). Por eso no se toman señales después de las 21:00.
- **N9 en Londres (07-13):** +0,37 / +0,11 %. En Nueva York (13-21) pasó a −0,07 % en 2024-2026, así que su ventana se cierra a las 13:00. Ese corte se eligió viendo los dos tramos, así que hay que confirmarlo en el papel.

**Reglas de separación:**
- Cada libro tiene **su propia posición**, como máximo una a la vez, y su propio marcador contra el azar. Los resultados no se mezclan.
- **Riesgo total:** como máximo una posición en pesos (libro PRINCIPAL, 1,5 %). El libro PRUEBA va en papel y en porcentaje hasta que una estrategia ascienda.
- Si los dos libros tienen señal a la vez, se toman las dos en papel, cada una en su libro.
- **El contexto manda en los dos libros:** con el cierre de ayer bajo su SMA 50, ningún largo de P05b, P05c, P11 ni N8; el único corto permitido es el de P05b y el de N9 en su ventana.

## 3. Cuándo NO operar (medido, no opinión)

- **Lectura incompleta** o con huecos.
- **Largos con contexto bajista** (P05b, P11): el lunes 26/10, PP-1 sin filtro iba en −0,47 % mientras PP-1f, con el filtro, no entró.
- **Cortos sin contexto bajista, y los cortos de P05c y del lunes**: pierden aun con contexto.
- **Exigir que todos los tiempos vayan a favor para entrar**: entra tarde; P05b largo pasa de +21,6 % a −1,1 % en la prueba.
- **A mercado sin señal**: con el rango medio de 1 h bajo 0,30 %, el movimiento esperado no paga tres veces la comisión (reglas R1 y R2 de la rutina).
- **Persiguiendo un rebote o una caída fuerte** en 3 h o en 5 min contra el contexto diario.
- **Anuncio de la Reserva Federal**: sin aperturas de 17:00 a 21:00 UTC el 28/10, y medio riesgo el 27 y el 28.
- **Con los topes tocados**: −3 % en el día, −6 % en la semana o −10 % desde el máximo.
- **Para cumplir una cuota.** Lo sostenible es de 1 a 2,5 operaciones por semana.
- **La MEZCLA, los patrones de vela como entrada y el retroceso N3**: descartados con datos.

## 4. Tamaño

1,5 % de riesgo por operación (600 pesos). Una posición a la vez y máximo 2 entradas por día. En pesos, solo largos de contado. Los cortos van en papel y en porcentaje: con 40.000 pesos, la orden mínima de futuros arriesgaría del 8 al 19 % de la cuenta.

## 5. Después de cada operación

Cerrar con velas reales de 1 minuto. Comparar con el testigo al azar. Anotar por qué ganó o perdió. Revisar las reglas solo con datos (elegir en el ajuste y mirar la prueba una vez).
