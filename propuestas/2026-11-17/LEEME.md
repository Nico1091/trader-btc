# Simulador del dinero real de binarias con sus reglas · propuesta del 17/11/2026

## Rama y carpeta

Esta entrega va en la rama `claude/proyectos-2026-11-17-d`, creada desde `master`. El nombre pedido, `claude/proyectos-2026-11-17`, ya existe en el repositorio con el evaluador de ventaja de otra sesión, y no se ha sobrescrito. Las variantes `-b` y `-c` también existen con otro trabajo. La carpeta es `propuestas/2026-11-17/`, como se pidió. Las otras ramas que tienen esa misma carpeta traen otros archivos: no conviene unirlas sin revisar los nombres.

## Qué es

Un programa que responde a una pregunta que ninguna propuesta anterior contesta:

> Con las reglas que ya están instaladas en el operador (armado 18 de 25, compuerta 19 de 25 con ganancia, orden de 2 USDT, tope del 16 % por orden, freno del 16 % por día, 20 órdenes al día), ¿cuánto dinero real se pone en riesgo, cuántas órdenes se hacen y cuánto se pierde o se gana en un mes, según la ventaja que tengan las señales?

Las propuestas anteriores miden si hay ventaja (evaluador, prueba secuencial, verificador de cifras), si el armado es azar (simulador de la regla 70 %) o si el operador cumplió sus reglas (auditor de dinero). Esta mide las consecuencias en USDT de esas reglas cuando no hay ventaja, cuando hay poca y cuando hay bastante.

Usa solo la biblioteca estándar de Python (3.11 o superior). No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono, no toca `binarias/operador/` ni `binarias/aprobador/` y no escribe archivos salvo que se pida con `--json`.

## Archivos

| Archivo | Para qué |
|---|---|
| `simulador_dinero_real.py` | El simulador. Se usa desde la línea de comandos. |
| `prueba_simulador_dinero.py` | 33 pruebas. Los valores esperados están calculados a mano o con una fórmula aparte. |
| `salida_pruebas.txt` | Salida real de las pruebas en esta entrega. |
| `salida_simulacion.txt` | Salida real con las reglas de hoy, sin tope total. |
| `salida_tope_25.txt` y `salida_tope_10.txt` | Lo mismo con un tope total de 25 % y de 10 % del saldo inicial (opción que no existe hoy). |
| `salida_sensibilidad.txt` | Cambio de resultados según el número de señales al día (5, 16 y 50). |

## Cómo se usa

```
python3 prueba_simulador_dinero.py                       # las 33 pruebas
python3 simulador_dinero_real.py                         # tabla con las reglas de hoy (unos 10 s)
python3 simulador_dinero_real.py --tope-total 0.25       # lo mismo con un tope total del 25 %
python3 simulador_dinero_real.py --precio 0.544 --ventaja "0;0.02;0.04" --senales-dia 5
python3 simulador_dinero_real.py --json resultados.json  # guarda todos los escenarios
```

- `--ventaja`: puntos de acierto por encima del precio pagado. Con `0`, el mercado es justo. Por defecto `0;0,02;0,04`. Las listas van separadas por punto y coma, porque la coma es decimal (`0,46;0,544`).
- `--precio`: precio pagado por el lado comprado. Por defecto `0,46;0,544;0,58`, los que se han visto en la caja.
- `--saldo` (20,50), `--dias` (30), `--senales-dia` (16), `--reps` (1000), `--semilla` (2026).
- `--aprobacion` y `--llenado`: fracción de puntos que la IA aprueba y de órdenes que se llenan al precio visto. Por defecto 1, que es el caso más expuesto.
- `--tope-total`: no compra más si el saldo baja esa fracción del inicial. Por defecto 0 (sin tope), como hoy.

## Qué dice (resultados de `salida_simulacion.txt`, 1000 réplicas, 30 días, 16 señales al día)

El acierto de cada escenario es el precio más la ventaja. «Órdenes» son las órdenes medias del mes. «P(pérdida)» es la probabilidad de terminar el mes con menos dinero del que se empezó.

| ventaja | precio | acierto | EV por orden | P(armado) | órdenes | pnl medio | pnl P5 | P(pérdida) |
|---|---|---|---|---|---|---|---|---|
| 0 (mercado justo) | 0,46 | 46 % | −0,04 | 44 % | 0,75 | −0,08 | −2,00 | 11 % |
| 0 (mercado justo) | 0,544 | 54,4 % | −0,04 | 95 % | 6,86 | −0,07 | −6,40 | 48 % |
| 0 (mercado justo) | 0,58 | 58 % | −0,04 | 100 % | 14,31 | −0,32 | −8,48 | 59 % |
| 2 puntos | 0,544 | 56,4 % | +0,03 | 99 % | 10,52 | +0,55 | −7,59 | 51 % |
| 4 puntos | 0,544 | 58,4 % | +0,10 | 100 % | 16,08 | +2,04 | −8,38 | 50 % |

Lecturas que se sostienen con estas cifras:

1. **Sin ventaja, la esperanza es negativa.** Con el mercado justo cada orden de 2 USDT pierde unos 4 céntimos (la comisión del 2 %). No hay ningún precio en el que el azar gane.
2. **El riesgo por orden es pequeño, pero el del mes no está limitado por el freno.** El freno del 16 % frena un día, no el mes. Con precio 0,544 y sin ventaja, el 5 % de los meses pierde 6,40 USDT o más (un 31 % del saldo). Con precio 0,58, pierde 8,48 USDT (un 41 %).
3. **La regla de armado se activa casi siempre si el acierto está cerca del precio.** Con precio 0,544 se arma en el 95 % de los meses, y con 0,58 en el 100 %, aunque no haya ventaja. Lo que mide es una racha de 18 de 25, no una ventaja. La cifra de referencia es que con moneda justa esa racha ocurre el 2,16 % de las veces por cada 25 señales, pero el operador repite la prueba con cinco estrategias cada vez que cierra una señal.
4. **Incluso con cuatro puntos de ventaja, la mitad de los meses terminan en pérdida.** La ganancia media es de 2 USDT al mes sobre 20,50, pero como el número de órdenes es pequeño y el freno corta los días, el resultado es muy variable. Según el bloc, ninguna estrategia gana todavía con precio real, así que la ventaja de 4 puntos es un supuesto, no un dato.

### Tope total (opción que hoy no existe)

| escenario | sin tope: pnl medio / P5 | tope 25 %: pnl medio / P5 | tope 10 %: pnl medio / P5 |
|---|---|---|---|
| mercado justo, 0,58 | −0,32 / −8,48 | −0,23 / −6,48 | −0,12 / −4,00 |
| +4 puntos, 0,544 | +2,04 / −8,38 | +1,95 / −6,40 | +1,63 / −4,00 |

El tope protege la cola, a costa de un poco de ganancia media. Es una decisión de criterio que corresponde al dueño. Este programa no cambia el operador.

### Sensibilidad al número de señales (`salida_sensibilidad.txt`, precio 0,544)

- Con 5 señales al día, el armado ocurre en el 38 % de los meses sin ventaja y en el 61 % con 4 puntos. Hay menos órdenes y el resultado se acerca a cero.
- Con 50 señales al día, el armado ocurre siempre, hay unas 22 órdenes al mes sin ventaja y la pérdida del 5 % peor sube a unos 9,2 USDT.
- El signo no cambia con el número de señales: sin ventaja la esperanza es negativa, con 4 puntos es positiva.

## Supuestos (cada uno cambia el resultado y se puede cambiar por línea de comando o en el código)

- **Constantes del operador.** Se copiaron de la rama `binarias/plan-v7-2026-11-04` (citas con archivo y línea en el código): `COMISION = 0.02` (`nucleo.py:19`), `TOPE_SALDO = 0.16` (`nucleo.py:24`), `FRENO_DIA = 0.16` (`ejecutor.py:43`), `IMPORTE_IA = 2.0` (`ejecutor.py:56`), `TOPE_ORDENES_DIA = 20` (`ejecutor.py:42`), `UMBRAL_ARMAR = 18` (`operador.py:52`). El umbral 19 de 25 con ganancia viene del `AVANCE.md` de la rama del aprobador, no de una línea de código revisada.
- **Freno del día como lo calcula el código.** Lo perdido de hoy es la pérdida neta liquidada más lo abierto, entero (`ejecutor.perdido_hoy`). Con 20,50 USDT, una orden abierta deja 1,28 USDT de cupo, así que una sola pérdida apaga el día, como dice el bloc.
- **Una orden abierta a la vez en la práctica.** No hay una regla separada por mercado en el simulador: el freno del 16 % ya impide dos órdenes abiertas con 20,50 USDT.
- **Señales por día.** Se toman 16 al día en total, repartidas por igual entre cinco estrategias. El bloc dice «unas 16 al día» para el núcleo (300 apuestas, hacia el 22/11). No se midió con el Centro, y por eso hay una sensibilidad.
- **Mercados de 5 y 15 minutos**, a partes iguales. El de 10 minutos no tiene API (dato del bloc).
- **La IA aprueba todo lo que pasa la compuerta y la orden se llena siempre al precio visto.** Es el caso más expuesto. Si la IA rechaza, o si el precio se mueve más de 0,02 antes de la compra, hay menos órdenes y el riesgo baja.
- **Pago 0,98 ÷ precio**, la convención del bloc. El pago real lo lee el dueño en la app y no se ha verificado.
- **Señales independientes entre estrategias.** En la práctica están correlacionadas, y la correlación suele aumentar la probabilidad de armado por azar.
- **Mercado justo = el acierto iguala el precio.** Es la hipótesis nula más honesta: si el precio es la probabilidad del mercado, nadie gana sin información. Usar 50 % de acierto con precio 0,46 no es azar: es una ventaja de 4 puntos, y por eso el escenario base no lo usa.

## Qué se probó

- **33 pruebas** (`salida_pruebas.txt`, 33 de 33 bien):
  - Economía: el cobro 0,98 ÷ precio con el ejemplo del bloc (2,13 con 0,46), el equilibrio, el valor esperado de 0,6 con 0,5 (0,176, a mano), el valor esperado cero en el equilibrio, el mercado justo que pierde 0,02 con cualquier precio, la cola binomial 726206 / 2^25 y una simulación de Monte Carlo de 200 000 apuestas que coincide con la fórmula.
  - Compuerta y armado: 19 de 25 es el mínimo, el precio alto la anula, 18 de 25 arma, 17 no, y 24 cerradas no cuentan.
  - Frenos, comprobados uno a uno con el código del ejecutor: cupo de 3,28 USDT, una orden abierta bloquea otra, una pérdida apaga el día, una ganancia restaura el cupo, el día nuevo reinicia, el tope de 20 órdenes, el tope del 16 % por orden con saldo bajo y el armado previo.
  - Réplicas: misma semilla da el mismo resultado; sin aprobación de la IA no hay órdenes; el pnl cuadra con aciertos y fallos; el freno no se rompe en 300 réplicas con órdenes; el tope total detiene las compras y cambia el resultado frente a no tenerlo.
  - Interfaz: la línea de comandos corre, rechaza números malos y rechaza precios fuera de rango.
- **Un error corregido durante la entrega.** La primera versión tomaba «acierto 50 %» como hipótesis nula para todos los precios. Con precio 0,46 eso era una ventaja de 4 puntos, y daba resultados engañosos. Se cambió a «ventaja sobre el precio», con 0 como mercado justo, y las pruebas lo cubren.
- **Un error de la propia prueba corregido.** La prueba del tope usaba un escenario sin armado y quedaba vacía. Ahora usa un escenario donde sí hay armado y pérdidas, y compara con y sin tope.

## Qué no quedó probado

- **No se midió la frecuencia real de señales del Centro**: se usa 16 al día, del bloc, y la sensibilidad muestra cuánto cambia.
- **No se midió el acierto real de cada estrategia con precio real.** El bloc dice que hoy ninguna lo ha demostrado. Por eso el simulador trabaja con ventajas, no con una estrategia concreta.
- **No se midió el llenado real ni la comisión real.** Se asume 0,98 ÷ precio y llenado al precio visto.
- **No se simulan los fallos de cobro** (`batch-redeem`) ni las órdenes sin aclarar, que el ejecutor maneja aparte.
- **No se simula el reintento de 15 segundos** de una orden de la IA que un freno detuvo. Eso puede añadir compras en la misma ventana.
- **No se simula el índice de liquidación de Binance**, que puede diferir de la vela de cierre.
- **No se leyó ni se usó ninguna llave, ni se conectó a Binance o a la caja.** Todo son números del bloc y del código.

## Lo que solo puede decidir el dueño

- Si la regla `ARMAR_AL_70` debe seguir encendida. Según estas cifras, con acierto cerca del precio se arma casi siempre, y el armado no significa ventaja.
- Si conviene un tope total (10 % o 25 % del saldo inicial). Es un cambio en el operador, que este proyecto no toca. Aquí solo se mide su efecto.
- Cuánto saldo real se quiere arriesgar, y con qué pérdida se acepta parar.
- El pago real de cada mercado, que solo puede leer en la app.
