# Comprador por ganancia esperada · reglas escritas antes de medir

Escritas el 12/11/2026 a las 19:00, hora de Colombia, antes de correr la evaluación de la red y antes de anotar una sola compra de papel con estas reglas. No se cambian mirando resultados. Si una regla resulta mal planteada, se escribe otra con fecha y hora, y la serie de papel empieza de cero.

## Qué se mide

Mercado: «BTC Up or Down» de 15 min de Binance Wallet con Predict.fun. Abre y liquida con el precio de contado de Binance. Comisión c = 2 %, que sale de los contratos. El precio se mueve de 0,01 en 0,01. El empate reparte 50-50.

Ganancia esperada de comprar un lado al precio q con probabilidad p de ganar, por cada USDT:

    G = p × (1 − c) / q − 1

A q = 0,01 un USDT compra 98 contratos y el acierto deja 97 USDT netos. Esa compra solo conviene si p pasa de 1,02 %. La regla general: el precio debe quedar por debajo de 0,98 × p.

Vector de ganancia: en cada minuto cerrado de la ventana (1 a 14) y para cada lado (sube y baja), la probabilidad de la red, la probabilidad prudente, el precio real de compra, los contratos que hay a ese precio y las dos ganancias esperadas (con la probabilidad de la red y con la prudente).

## R1. Probabilidad

La red de la pérdida (laboratorio\perdida_red.py) cubre hoy los minutos 10 a 14. Se extiende a los minutos 1 a 14 con los mismos doce rasgos y el mismo ajuste (regresión logística con penalización), aprendiendo solo con 2021-2023. La probabilidad del lado que va ganando es 1 − p − p_empate.

Se compara a ciegas con cuatro referencias: la fórmula normal Φ(−|z|), la tabla por minuto y tamaño de |z| aprendida en 2021-2023, una logística con solo tres rasgos (|z|, |z|² y minutos que faltan) y un perceptrón 12-16-8. Medida: pérdida logarítmica en «elige» (ene-2024 a jun-2025). Se usa el perceptrón solo si mejora a la logística en más de 0,5 % relativo en «elige»; si no, la logística, que corre igual en la placa. «Juzga» (jul-2025 a oct-2026) se calcula una sola vez para el modelo elegido.

## R2. Probabilidad prudente

La red se equivoca distinto según la época. Por cada tramo de probabilidad predicha (0-0,5 %, 0,5-1 %, 1-2 %, 2-5 %, 5-10 %, 10-20 %, 20-50 %) se calcula, trimestre por trimestre, el cociente entre lo que ocurrió y lo que la red predijo.

- Lado perdedor: p_prudente = p × h, con h el cociente del peor trimestre (el más bajo), nunca mayor que 1.
- Lado ganador: p_prudente = 1 − p × H − p_empate, con H el cociente más alto, nunca menor que 1.

En la prueba a ciegas, h y H salen solo de «elige» y la regla se juzga una vez en «juzga». En vivo se usan los de «elige» y «juzga» juntos (once trimestres).

También se prueba, con la regla ya escrita, si recalibrar la red cada mes con los 90 días anteriores (dos números: desplazamiento y pendiente del logit) estrecha esos cocientes. Entra solo si el peor trimestre mejora en «elige».

## R3. Regla de compra en papel (comprador v1)

1. Mirada al cierre de cada minuto 1 a 14, con velas de contado ya cerradas y un libro leído después de ese cierre (hasta 20 s de espera; si no llega, la mirada se pierde).
2. Se calcula el vector de ganancia de los dos lados. No importa si es sube o baja.
3. Se compra el lado cuya ganancia esperada prudente llegue a 0,10 o más (10 % por USDT), con precio entre 0,01 y 0,90 y con 10 s o más para el cierre.
4. Llenado honesto: se decide con el libro de la mirada, pero se anota el precio del primer libro leído 5 s o más después. Si para entonces el precio ya no cumple el límite (q ≤ 0,98 × p_prudente / 1,10), no hay compra y queda anotado «se escapó». Se lleva en paralelo la misma cuenta con 15 s, que es lo que tarda su doble toque.
5. Una compra por ventana: la primera mirada que cumpla.
6. Libro A: 1 USDT fijo por compra. Libro B: una cuarta parte del Kelly calculado con la probabilidad prudente, con tope del 16 % del saldo de papel, sin pasar de los contratos que el libro ofrece a ese precio y sin apalancamiento; si da menos de 2 USDT (el mínimo de la Mesa) no compra y lo anota. Saldo inicial de papel del libro B: 46 USDT.
7. Se liquida con el ganador oficial del mercado. Sin ganador en dos horas, no cuenta.

Las tres reglas anteriores de mesa\perdida_real.py («a lo último», «temprana» y «red al final») siguen anotándose como serie 2, sin cambios, para comparar.

## R4. Celdas

Cada compra cae en una celda: papel del lado (perdedor o ganador), minuto (1-5, 6-10, 11-14) y precio (hasta 0,02; 0,03-0,05; 0,06-0,10; 0,11-0,30; 0,31-0,70; 0,71-0,90). La política dice qué celdas están encendidas. Todas arrancan encendidas en papel.

## R5. Apagado de una celda

Con 50 compras o más en la celda, se apaga si los aciertos quedan por debajo del percentil 1 de lo que predice la probabilidad prudente (binomial de Poisson). Una celda apagada sigue midiéndose «en sombra» y vuelve con 100 compras en sombra cuyo neto sea positivo.

## R6. Cuándo el comprador queda «apto»

Todas a la vez:

1. 300 compras de papel o más con llenado honesto de 5 s y 30 aciertos o más.
2. Neto positivo en el libro A y en el libro B, y percentil 5 del neto del libro A mayor que cero al remuestrear por ventanas (10.000 remuestras, semilla fija).
3. La misma cuenta con 15 s de llenado también da neto positivo.
4. Aciertos dentro de lo que predice la red: la cuenta real no se aparta más de dos desviaciones de la suma de probabilidades.
5. Ningún acierto aporta más de la cuarta parte del neto.
6. 14 días de calendario o más, y el auditor rehace todas las compras desde el vector grabado sin una sola diferencia.

«Apto» no autoriza dinero. Autoriza a proponerle al dueño el toque real, con los topes de la Mesa. El toque es suyo.

## R7. Lo que el agente de la nube puede y no puede

Puede: auditar, medir, apagar y volver a encender celdas con R5, subir el margen de R3, bajar el tope del libro B, proponer una regla nueva escrita con fecha antes de medirla y declarar «apto» o «no apto» con R6.

No puede: mandar órdenes, pedir o guardar llaves, bajar el margen de 0,10, quitar el llenado honesto, cambiar R6, mezclar series ni borrar compras perdidas. La Mesa recorta cualquier política que se salga de estos límites y lo deja anotado.

## R8. Varianza que se acepta de antemano

Con probabilidades de 2 a 5 % lo normal es perder decenas de veces seguidas aunque la ganancia esperada sea positiva. Por eso el juicio va por R6 y no por una racha, y el libro B apuesta poco.

## Precisiones puestas en el código antes de correr la evaluación (12/11/2026, 19:02)

- En R2 no cuentan los trimestres con menos de 20 aciertos esperados en el tramo. Un tramo sin ningún trimestre válido usa h = 0,5 y H = 2 (le tocó al tramo de 0 a 0,5 %).
- Un trimestre con menos de dos meses de datos se une al anterior (octubre de 2026 va con el tercer trimestre).

## Enmienda 1 (12/11/2026, 19:10; antes de la primera compra de papel con estas reglas)

Motivo: al medir con la red las 84 compras de papel de las series 1 y 2 (medir_papel.py), las hechas entre 20 y 50 s después del cierre de un minuto salían con ganancias esperadas imposibles, porque la red miraba la vela cerrada y el precio ya había cruzado la apertura. Esas cifras son de las reglas anteriores; el comprador v1 no ha anotado nada.

- R3.1 queda así: la mirada se hace en los 5 s siguientes al cierre de cada minuto 1 a 14 (antes: hasta 20 s). En ese instante se leen el libro y el precio de contado del momento. Si no se logra en 5 s, la mirada se pierde.
- La probabilidad se calcula con las velas cerradas, pero lo atrasado (|z|), su cuadrado, su logaritmo y el tiempo que falta se recalculan con el precio de contado del instante y los segundos que quedan. Se anotan las dos probabilidades, la de la vela cerrada y la del instante. Decide la del instante.
- Lo demás no cambia. Por R1 quedó la logística de doce rasgos.

## Enmienda 2 (16/11/2026, 14:05; antes de entrenar el modelo de 5 min, antes de su primera mirada y antes de cualquier orden automática)

Motivo: pedido suyo del 16/11/2026 de llevar el comprador a la caja T95H, con plazos de 5, 10 y 15 minutos, y de que las compras y los cobros se hagan solos. Detalle en `operador\PLAN-AUTOMATICO.md`. Nada de lo escrito arriba cambia para el mercado de 15 minutos.

Mercado de 5 minutos («BTC Up or Down» de 5 min, `btc-updown-5m-…`):

- Valen R1 a R6 con estos cambios: la ventana dura 5 minutos; las miradas son al cierre de los minutos 1 a 4; el movimiento se normaliza con la raíz de los minutos que faltan (5 − m); las celdas de R4 usan los tramos de minuto 1-2 y 3-4.
- Modelo: la logística de doce rasgos, la familia que R1 eligió para 15 minutos, aprendida solo con 2021-2023 sobre ventanas de 5 minutos. No se repite la comparación con el perceptrón. La probabilidad prudente (R2) sale de sus propios cocientes por trimestre, con las mismas precisiones del 12/11.
- Serie de papel propia, que empieza de cero. R6 se cumple por separado en cada mercado: que uno quede apto no dice nada del otro.
- Si el modelo de 5 minutos no mejora a la fórmula normal en «elige», se dice y la serie corre igual en papel, marcada como «modelo sin ventaja sobre la normal».

Plazos: cada compra anota los minutos que faltaban. «15 minutos» es la mirada con 13 o 14 minutos por delante en el mercado de 15; «10 minutos», con 9 a 11; «5 minutos», con 4 a 6 en el de 15 o cualquier mirada del de 5. Son etiquetas para informar; la regla de compra es una sola.

Medición sin llave: mientras la caja no tenga una llave que lea, anota en cada mirada la probabilidad del modelo y el precio límite de cada lado, con la apertura de contado como referencia, y después el ganador según las velas de contado. Esa serie mide solo si el modelo acierta lo que dice (R6.4); no hay compras de papel sin precio real.

Órdenes reales automáticas (lo que cambia frente a R6 y R7, por su pedido del 16/11):

- El real lo ejecuta el programa de la caja, sin IA, con la misma regla R3 y el importe del libro B calculado sobre el saldo real de la billetera de predicción. Antes de enviar pide la cotización: si el precio medio cotizado no deja la ganancia esperada prudente en el margen, no envía.
- Exige tres cosas a la vez: una llave propia de la caja con Lectura y Predicción y nada más; saldo en la billetera de predicción; y el archivo `ARMADO`, creado solo por orden suya. Si el comprador de ese mercado todavía no es apto por R6, el operador se lo dice antes de armar; armar igual es decisión suya y queda anotada.
- Una orden por mercado. Freno del día: lo perdido en el día de Colombia no pasa del 16 % del saldo con que empezó el día. Tope de 20 órdenes reales por día.
- Una orden es «comprada» solo si Binance lo confirma; todo estado que no sea final se relee hasta que lo sea, también tras un reinicio (el 12/11 dos órdenes quedaron en «SUBMITTED» sin releer).
- Cobro: el operador reclama lo ganado de los mercados liquidados y lo anota. Hasta el primer cobro real comprobado figura como sin probar.
- Lo que sigue prohibido: bajar el margen de 0,10, quitar el llenado honesto del papel, mezclar series, borrar pérdidas, apalancar, usar en la caja la llave del PC y tocar la app de Binance o los Contratos de Evento con programas.
