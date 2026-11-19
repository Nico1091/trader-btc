# Auditor de reglas de dinero del operador de binarias

Propuesta del 19/11/2026 (rama `claude/proyectos-2026-11-19-b`). Elaborada por la rutina de proyectos, sin tocar `binarias/operador/` ni `binarias/aprobador/` ni `master`.

## Qué es

Un programa de solo lectura que toma el libro de dinero real del operador (`datos/ordenes.json`, el archivo que escribe el ejecutor) y comprueba, orden por orden, que se cumplieron las reglas de dinero que el bloc y el código dicen que se cumplen. Escribe un resumen y un veredicto: CUMPLE o NO CUMPLE.

No consulta Binance, no compra, no vende, no escribe nada junto al archivo y no necesita llaves ni conexión. Usa solo la biblioteca estándar de Python (3.8 o superior; sirve el 3.11 del PC y el 3.14 de los equipos).

## Por qué esta y no otra

Las binarias ya tienen varias herramientas estadísticas (evaluador de ventaja, vigilancia por periodos, puente del papel, simulador de la regla del 70 %, prueba secuencial). Ninguna comprueba lo más básico: que el operador **obedeció** sus propias reglas de dinero en las órdenes reales. El bloc deja casos de órdenes que nadie leyó después de enviarlas, y el dinero real ya se mueve con 20,50 USDT. Un fallo de un tope o del freno es la pérdida que más duele y la que menos se ve.

## Cómo se usa

Copie el archivo `datos/ordenes.json` de la carpeta del operador a un lugar donde pueda ejecutar Python. Es un archivo con importes reales: **no lo suba a la nube ni a GitHub**.

```
python3 auditor_reglas_dinero.py ordenes.json
python3 auditor_reglas_dinero.py ordenes.json --ahora 1763480000   # fija la hora de revisión (segundos Unix)
```

- Código de salida `0`: cumple. `1`: hay infracciones. `2`: el archivo no se puede leer.
- Ruta habitual: en la caja, `/data/local/tmp/operador/datos/ordenes.json`. En el teléfono, dentro de la carpeta del operador de la app; la ruta exacta debe confirmarse en el equipo.

Para correr las pruebas: `python3 prueba_auditor.py`. Para volver a generar los dos ejemplos sintéticos: `python3 prueba_auditor.py --generar`.

## Qué comprueba

| Regla | Qué exige | Origen en el código |
|---|---|---|
| R1 | Importe de al menos 2 USDT | `MIN_USDT` |
| R2 | Orden de hasta el 16 % del saldo al decidir | `TOPE_SALDO` |
| R3 | Orden de la IA de 2 USDT (desde el 18/11/2026) | `IMPORTE_IA` |
| R4 | Como mucho 20 órdenes por día | `TOPE_ORDENES_DIA` |
| R5 | Una orden por mercado y, como mucho, dos intentos (las rechazadas limpias no cuentan) | `INTENTOS_MERCADO` |
| R6 | Freno del día: lo perdido en el peor caso más la orden nueva no pasa del 16 % del saldo inicial del día | `FRENO_DIA`, `perdido_hoy` |
| R7 | Precio cotizado entre 0,01 y 0,90 | `PRECIO_MIN`, `PRECIO_MAX` |
| R8 | Precio de la IA como mucho 0,02 por encima del que vio | `TOLERANCIA_IA` |
| R9 | Cuentas: pago según el resultado (acierto = contratos, empate = mitad, fallo = 0), neto = pago − comprado, contratos = comprado × 0,98 ÷ precio (tolerancia del 5 %, como el código) | `_liquidar`, `_aplicar` |
| R10 | Todo pago queda registrado como cobrado. «SIN COBRAR» y los cobros pendientes salen como avisos | `_cobrar` |
| R11 | Solo avisos: órdenes sin aclarar, sin cierre a las 24 h, comprada sin resultado a las 48 h, sin ganador oficial | `SIN_CIERRE_S`, `SIN_RESULTADO_S` |
| R12 | Integridad: id único, mercado de 5 o 15 min, día coherente con la hora de envío (Colombia) | `dia()` |

Cada infracción sale con su id de orden y la cifra que la causa. Las órdenes sin dato en un campo se cuentan aparte («sin dato en n orden(es)»); no se tratan como cero.

## Cómo se probó

`prueba_auditor.py` construye libros sintéticos (importes inventados) y, para cada regla, inyecta una infracción concreta. Exige que el auditor marque **exactamente** esa regla, ni más ni menos.

Salida real del 19/11/2026, con Python 3.11:

```
[bien] libro limpio cumple todo
[bien] R1 importe de 1,50 USDT
[bien] R2 importe de 2 USDT con saldo de 10
[bien] R3 orden de la IA de 2,5 USDT
[bien] R4 vigésima primera orden del día
[bien] R5 segunda orden en el mismo mercado
[bien] rechazada no cuenta para R5 (la siguiente sí es válida)
[bien] R6 freno: pérdida abierta más nueva orden pasa el 16 % de 20
[bien] R7 precio cotizado de 0,95
[bien] R8 IA paga 0,06 por encima de lo que vio
[bien] R9 neto que no cuadra
[bien] R9 contratos lejos del precio
[bien] R10 pago sin registro de cobro
[bien] R10 pago sin cobrar (solo aviso)
[bien] R11 orden por enviar sin aclarar (solo aviso)
[bien] R11 orden sin cierre a las 24 h (solo aviso)
[bien] R12 id repetido
[bien] R12 mercado de 7 minutos
[bien] R12 día que no coincide con la hora
[bien] resumen del libro limpio: {'ordenes': 4, 'dias': 1, 'compradas': 4, 'comprado': 8.0, 'aciertos': 1, 'empates': 0, 'fallos': 2, 'sin_ganador': 0, 'abiertas': 1, 'neto': -2.08, 'cobrado': 3.92, 'sin_cobrar': 0.0}

20 de 20 pruebas bien
[bien] CLI sobre el libro limpio: código 0 (esperado 0)
[bien] CLI sobre el libro infracciones: código 1 (esperado 1)
[bien] CLI con archivo inexistente: código 2 (esperado 2)

TODO BIEN
```

Comprobación de que las pruebas muerden: se sustituyó el freno por una versión que no cuenta lo perdido de órdenes anteriores, y la prueba de R6 dejó de detectar la infracción (salió vacía, en lugar de R6). Es decir, una regresión que deje de contar pérdidas en el freno sí se vería. Lo que esta comprobación no cubre es un mutante que solo ignore las órdenes abiertas: el caso de R6 usa una orden ya cerrada, así que esa variante no se detecta todavía.

Salida sobre el ejemplo con infracciones (`ejemplo_libro_con_infracciones_SINTETICO.json`, hora fijada con `--ahora`), abreviada:

```
  R3   ... INCUMPLE (1)
  R5   ... INCUMPLE (1)
  R6   ... INCUMPLE (2)
  R9   ... INCUMPLE (1)
  [R3] 15-1795017600-5: orden de la IA de 2.50 USDT; debe ser 2
  [R5] 15-1795018500-7: segunda orden en un mercado que ya tenía una
  [R6] 15-1795018500-6: en el día 20261118, lo perdido en el peor caso (6.58) más 2.00 USDT pasa el 16 % de 46.00 (7.36)
  [R6] 15-1795018500-7: en el día 20261118, lo perdido en el peor caso (8.58) más 2.00 USDT pasa el 16 % de 46.00 (7.36)
  [R9] 15-1795018500-6: neto 9.0000 distinto de pago - comprado (1.9200)
VEREDICTO: NO CUMPLE. 5 infracción(es) en el libro. Revíselas antes de seguir.
```

Salida completa de ambos ejemplos: ejecutar los comandos de arriba sobre los dos JSON de esta carpeta.

## Qué NO quedó probado

- **Con datos reales.** La nube no tiene el libro real del operador (está en la caja y en el teléfono). Nada de lo anterior prueba que el libro real cumpla o incumpla: solo que el auditor detecta bien las infracciones que se le inyectan.
- **Formas antiguas del libro.** Las órdenes anteriores al 18/11 usan el dimensionado de Kelly y no tienen los campos `origen` ni `visto`. El auditor lo tolera (R3 y R8 solo miran las órdenes de la IA), pero no se probó con un libro de esas fechas.
- **Campos ausentes.** Si una orden no trae `cotizado`, `saldo` o `comision`, la regla correspondiente cuenta un «sin dato» en vez de juzgarla. Un libro lleno de «sin dato» no es un libro limpio.
- **Órdenes que se cierran después de la siguiente.** El libro guarda solo el estado final de cada orden. Para R6 el auditor cuenta lo comprado de las órdenes ya cerradas y el importe entero de las abiertas; en el caso raro de una orden que se cerró después de la siguiente, puede subestimar el riesgo de ese momento. Nunca lo sobrestima.
- **Lo que no está en el libro.** No verifica la armada (`ARMADO`), los permisos de la llave, el saldo real frente a Binance ni los cobros frente a la app. Tampoco verifica que el código del operador sea el que corre en el equipo.
- **Rentabilidad.** No dice si el operador gana. Cumplir las reglas no es ventaja: para eso hace falta muestra suficiente y precios reales.

## Lo que solo puede hacer el dueño

1. Copiar `datos/ordenes.json` de la caja o del teléfono y correr el auditor en su PC.
2. Decidir si quiere que el auditor corra cada día (por ejemplo, con el arranque de la caja) y dónde deja el resultado.
3. Revisar cualquier infracción antes de seguir operando con dinero real.

## Archivos

- `auditor_reglas_dinero.py`: el auditor (378 líneas, solo biblioteca estándar).
- `prueba_auditor.py`: 20 pruebas más las pruebas de línea de órdenes; `--generar` escribe los ejemplos.
- `ejemplo_libro_SINTETICO.json`: libro limpio inventado.
- `ejemplo_libro_con_infracciones_SINTETICO.json`: libro inventado con cuatro infracciones inyectadas.
- `LEEME.md`: este archivo.
