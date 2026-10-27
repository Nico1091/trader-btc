# Guía de decisión de Claude, versión 3 (27/10/2026, tras la investigación cuantitativa)

Esta versión reemplaza a las anteriores. Claude decide cada operación. Los programas leen datos, calculan, controlan el riesgo y cierran con velas reales. Todo es papel hasta que Nicolás apruebe otra cosa.

**Qué cambió respecto de la v2:**
- Las etiquetas de las estrategias ahora dicen lo que los datos sostienen. Se probaron en 5 activos que nunca se habían mirado (`investigacion/INFORME-INVESTIGACION-QUANT.md`).
- Los topes de riesgo están en el código.
- Una operación solo cuenta como ejecutada si su orden se registró a tiempo.
- Se miden dos «sombras»: el stop duro y la regla de tendencia.

**Cifras de referencia:**
- Velas de 1 minuto de futuros de Binance de 2020 a 2026. Ajuste 2020-2023, prueba 2024-2026.
- Comisión real y repetida con el doble.
- Los % de las tablas son **sumas** del % neto de cada operación con el 100 % del nocional. No son rentabilidad de la cuenta.

## 1. Antes de decidir (unos 3 segundos)

1. Correr `python3 -I consolidacion/lectura_mercado.py /tmp/lectura`. Da:
   - el **estado de riesgo** de la cuenta en pesos;
   - el resumen de los 5 tiempos con sus 5 fotos;
   - el contexto y los niveles de hoy;
   - las señales de los dos libros (motor `sistema.py`, idéntico al simulador en **14.022 de 14.022** días × estrategia de todo el historial);
   - la confirmación de los otros tiempos.
2. Si el riesgo dice **BLOQUEADA** o **PARADA TOTAL**, no se abre nada en la cuenta en pesos. El papel en % se sigue midiendo.
3. Mirar las 5 fotos:

   | Foto | Qué mirar |
   |---|---|
   | 3 meses y 1 día | La tendencia de fondo |
   | 16 horas | La estructura de hoy |
   | 3 horas y 5 min | El momento y el riesgo inmediato |

4. Si la lectura dice «NO OPERAR, lectura insuficiente», no se opera.
5. Anotar en el diario una línea por tiempo y la decisión, antes del resultado.
6. **Si se decide operar una señal, registrar la orden ANTES del llenado:**
   `python3 -I consolidacion/sistema.py orden <ESTRATEGIA> "razón"`.
   - Sirve también como orden condicionada para más tarde. Por ejemplo, el domingo a las 20:00 UTC: `orden P11 "compra a la apertura del lunes si el contexto es alcista"`. Cuenta para el día siguiente si se registró desde las 00:00 UTC del día anterior; para otro día se usa `orden P11 --dia AAAA-MM-DD "…"`.
   - Sin orden registrada a tiempo, la operación queda como «NO EJECUTADA» y no cuenta en el papel real.
   - Una orden de P05b cubre también su pieza en pesos (P05b+pat).

## 2. Qué se opera, y con cuánta confianza

**Contexto** = cierre diario de ayer frente a la media de sus 50 últimos cierres (SMA 50). Decide el lado: con contexto alcista solo largos; con contexto bajista, solo los cortos indicados.

**Medido el 27/10:**
- El contexto es la fuente principal de la ventaja. Estar todo el día del lado del contexto, sin señal, gana casi lo mismo que P05b.
- Las cinco estrategias son en buena parte la misma apuesta: los días en que coinciden, su resultado se mueve con una correlación de 0,75 a 0,96. **No sumar el riesgo de varias como si fueran independientes.**

### Libro PRINCIPAL (papel en futuros, en %)

| Estrategia | Regla | Horario UTC | BTC 2020-23 / 2024-26 | **En 5 activos nunca mirados** (SOL, BNB, XRP, DOGE, ADA) | Estado |
|---|---|---|---|---|---|
| **P05c** | Como P05b con 1,0·ATR14, solo largo, con contexto alcista **y 1 h, 4 h y 1 día sobre su EMA 20** | Señal 00:00-21:00 | +35 % / +29 % | **Positiva en 5 de 5** (la única que generaliza) | La de más respaldo, pero el beneficio llega en pocas operaciones: unas 1,1 al mes |
| **P11** | Lunes 00:00, largo, solo con contexto alcista; stop 3 %, salida 23:59 | Lunes | +43 % / +51 % | Positiva en 1 de 5 | **Propia de BTC.** Se mantiene en BTC; sin sus 5 mejores operaciones, 2020-23 queda en −16 % |
| **P05b por régimen** | Primer cierre de 15 m fuera de apertura ± 0,5·ATR14; opera solo si ese primer rompimiento va en el lado del contexto. Límite en la banda 60 min; stop con un cierre de 15 m que vuelve a la apertura; salida 23:59 | Señal 00:00-21:00 | +74 % / +29 % | Positiva en 3 de 5; IC con cero | **Propia de BTC, parámetro frágil**: k = 0,5 es un pico (0,4 y 0,6 pierden en 2020-22). No se le cambian parámetros |

### Cuenta de 40.000 pesos (contado BTCUSDT, solo largos, sin apalancamiento)

Lleva las piezas que aguantan el contado con comisión doble en los dos tramos: **P11 con contexto, P05c y P05b largo con patrón alcista en las 3 últimas velas de 1 h**.

Resultado con las restricciones reales del contado (paso de 0,00001 BTC, mínimo de 5 USDT, comisión con BNB) y 2 % de riesgo:

| Escenario | 2020-23 | 2024-26 | Caída máxima |
|---|---|---|---|
| Comisión con BNB | +13,3 %/año | +15,2 %/año | 12 % |
| Comisión doble | +8,6 %/año | +10,0 %/año | 17,5 % |

En pesos son **unos 5.000 a 6.000 COP al año**. Pasar de pesos a USDT y volver cuesta otro ~1 % (P2P).

### Libro PRUEBA (papel, en %, aparte, con su propia posición)

| Estrategia | Regla | Horario UTC | BTC 2020-23 / 2024-26 | En 5 activos nunca mirados | Estado |
|---|---|---|---|---|---|
| **N9** Asia-Londres | Rango de 00:00-06:59 roto por un cierre de 15 m en el lado del contexto; límite 60 min; stop con un cierre de 15 m de vuelta al punto medio; salida 23:59 | 07:00-13:00 | +106 % / +22 % (con el doble, 2024-26 casi 0) | Positiva en 2 de 5 | **No generaliza.** Sigue en prueba |
| **N8** miércoles | Miércoles 00:00, largo, solo con contexto alcista; stop 3 %, salida 23:59 | Miércoles | +49 % / +39 % | Positiva en 2 de 5 | **No generaliza.** El stop del 3 % se queda: sin stop, la media sube pero la peor operación pierde entre −19 y −38 % en altcoins |

**Ascenso:** una estrategia de PRUEBA pasa a PRINCIPAL con **30 operaciones EJECUTADAS** de papel (no teóricas) que ganen neto y superen al azar.

## 3. Los otros tiempos confirman «un poquito» (medido, sin RSI)

| Confirmación | Efecto medido | Uso |
|---|---|---|
| 1 h o 4 h sobre su EMA 20, en P05b | Neutra | Se mira, no se exige |
| Los 3 tiempos mayores (1 h, 4 h, 1 día) | Mejora P05c | **Exigida en P05c** |
| Los 3 tiempos mayores en P05b o N9 | Empeora: se entra tarde | No se exige |
| Patrón del curso en las 3 últimas velas de 1 h | Mejora los largos de P05b en contado (muestra pequeña: 61 operaciones) | **Exigido para llevar P05b a pesos** |
| Semana anterior a favor, en P11 y N8 | Empeora | No se usa |

## 4. Riesgo (ahora en el código: `consolidacion/riesgo.py`)

- **2 % por operación** (800 pesos). El nocional sale de la distancia al stop conocida al entrar, con tope en el saldo y mínimo de 5 USDT. Una posición a la vez.
- **Topes**, que el programa calcula solo:
  - −4 % en el día: se para el día.
  - −8 % en la semana: se para la semana.
  - **−20 % desde el máximo: parada total y vuelta a papel puro.** Lo abierto se cierra a mercado y solo Nicolás decide reabrir.
- **¿Por qué no menos?** Con 12,59 USDT, el mínimo de 5 USDT impide el 0,25 %, el 0,5 % y el 1 %: no caben el 100 %, el 96 % y el 78 % de las operaciones.
- **¿Por qué no más?** Con 2,5 %, la probabilidad de tocar el −20 % en 2 años pasa del 0,5 % al 2,9 % (Monte Carlo).
- **El riesgo real es mayor que el planeado.**
  - El stop de P05b y P05c es un cierre de 15 minutos, no una orden de stop: las pérdidas por stop fueron 1,4 veces lo planeado, y en el peor caso un 2,8 % del saldo con 2 % de riesgo.
  - En el libro de futuros, la peor operación de P05b perdió −15,6 % (13/03/2020).
  - La sombra «stop duro» de `sistema.py cerrar` mide hacia adelante si conviene protegerse con un stop real.
- **El libro de futuros no se puede ejecutar con 40.000 pesos:** la orden mínima es 0,001 BTC (unos 81 USDT), así que es solo papel en %.

## 5. Cuándo NO operar

- Lectura incompleta, o riesgo **BLOQUEADA** o **PARADA TOTAL**.
- **Contra el contexto:** largos de P05b, P05c, P11 o N8 con contexto bajista; cortos con contexto alcista.
- Si el primer rompimiento del día fue hacia el lado contrario: P05b ya no opera ese día.
- Señales de P05b o P05c después de las 21:00 UTC, y de N9 fuera de 07:00-13:00.
- P05c sin los 3 tiempos mayores a favor.
- **Para cumplir una cuota.**
  - Con señal salen unas 19 operaciones al mes sumando los libros de papel, y de 3 a 4 en la cuenta en pesos.
  - **300 operaciones al mes no tienen ventaja:** el mismo mecanismo en sesiones de 1 a 8 horas da ~0 bruto por operación en 5 activos, y la comisión costaría entre el 45 % y el 60 % del capital al mes.
- **Descartado con datos:**
  - MEZCLA, patrones de vela como entrada, RSI, retroceso a la EMA 20, 50 SMA + precio, ruptura del máximo o mínimo de ayer, N3.
  - Cortos de P05c y del lunes, exigir que todos los tiempos vayan a favor en P05b.
  - Trading de minutos (AUC de 0,51 a 0,56).
  - Cambiar los parámetros de P05b, P05c, N9 o P11: 263 variantes por activo en 7 activos, y ninguna cumplió la regla de adopción. Lo que se elige en BTC no mejora en los demás activos más que tirando una moneda.

## 6. Después de cada día

1. Correr `python3 -I consolidacion/sistema.py cerrar AAAA-MM-DD > papel/AAAA-MM-DD.txt`.
   - Cierra cada libro con las 1.440 velas de 1 minuto.
   - Separa lo **teórico** (todas las señales) de lo **EJECUTADO** (solo con orden registrada a tiempo).
   - Lo compara con el testigo al azar.
   - Da las sombras: stop duro y tendencia «largo si el cierre de ayer > SMA 50».
   - Guarda en `papel/libro.jsonl` y actualiza el estado de riesgo.
2. Antes de cambiar una regla, correr `python3 -I consolidacion/pruebas_sistema.py`. Debe terminar en «SIN FALLAS»: patrones, paridad en todo el historial, sin mirar el futuro, Coinbase frente a Binance, topes de riesgo, ejecución y sombras.
3. Ningún cambio de regla se adopta por un backtest nuevo sin pasar por fuera de muestra. La regla de adopción está en `investigacion/PREREGISTRO.md`.
