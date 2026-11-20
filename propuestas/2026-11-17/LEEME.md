# Conciliador del dinero de binarias · propuesta del 20/11/2026

## Rama y carpeta

Esta entrega va en la rama `claude/proyectos-2026-11-17-e`, creada desde `master`. El nombre pedido, `claude/proyectos-2026-11-17`, ya existía con el evaluador de ventaja de otra sesión, y las variantes `-b`, `-c` y `-d` también tienen trabajo ajeno; no se ha sobrescrito nada. La carpeta es `propuestas/2026-11-17/`, como se pidió. No hay PR ni unión con `master`. No se ha tocado `binarias/operador/`, `binarias/aprobador/` ni `master`.

## Qué es

Un programa de solo lectura que cruza el registro del operador (`registro/AAAAMMDD.jsonl`) con el extracto de Binance que usted exporte, y avisa de lo que puede costar dinero sin que nadie lo vea:

- **Sin cierre confirmado**: una orden en estado no final («SIN CIERRE», «DUDOSA», «POR ENVIAR» o no final) con dinero en juego. Es el caso de las dos órdenes del 12/11 que quedaron como SUBMITTED sin que nadie leyera su cierre.
- **Compra sin liquidar** después de un plazo (30 minutos por defecto, medido contra la última hora del registro, no contra el reloj de la máquina).
- **Ganancia sin cobrar**: la liquidación dice que hay pago y el cobro no figura como «cobrado».
- **Cuentas que no cuadran**: neto distinto de pago menos compra, pago distinto del que corresponde al resultado, cobro anotado distinto del pago, y liquidación repetida.
- **Pago fuera de la fórmula**: el pago de una ganancia debe ser compra × 0,98 ÷ precio (la regla «Ganar» del bloc). Una diferencia mayor del 1 % sale como aviso.
- **Con extracto**: movimientos de Binance que no están en el registro, órdenes del registro que no están en el extracto, importes y cobros distintos, y caja total distinta en las dos fuentes.

## Por qué esta y no las otras

Las ramas `proyectos-2026-11-17` a `-d`, `2026-11-18`, `2026-11-18-regla70` y `2026-11-19` (`-b` incluida) ya traen evaluador de ventaja con intervalo, vigilancia por periodos, verificador de cifras, simulador del dinero real, puente del papel, prueba secuencial, simulador de la regla de armado y auditor de reglas. Todas miden si una estrategia gana, o revisan las reglas del operador. Ninguna comprueba que lo que el operador anota coincide con lo que Binance cobró o pagó. Ese es el hueco: el bloc registra ya tres situaciones de ese tipo (órdenes sin cerrar, un cobro automático sin probar con dinero real y la caja sin respuesta), y cada una significa USDT que no se ve. Es lo que puede hacerse hoy, probarse en esta sesión y no depende de que haya más datos de los que hay.

## Cómo se usa

```
python3 -I conciliador_dinero.py --registro RUTA_DEL_REGISTRO
python3 -I conciliador_dinero.py --registro RUTA_DEL_REGISTRO --extracto extracto.csv \
        --detalle detalle.json --texto mensaje.txt
```

- `--registro`: carpeta con los `AAAAMMDD.jsonl` del operador (una copia; el programa no escribe en ella).
- `--extracto`: CSV con encabezado y estas columnas (las demás se ignoran):
  `orden,importe_usdt,cobrado_usdt`. `orden` es el número de orden de Binance, el mismo que el campo `orden` del registro. Decimales con punto, o con coma si el valor va entre comillas. Una fila con más o menos columnas se rechaza: no se lee en silencio.
- `--gracia-min`: minutos antes de marcar una compra sin liquidar (30 por defecto).
- `--detalle` y `--texto`: archivos de salida. El texto es el mensaje para Telegram, con el prefijo `[Proyectos]` y menos de 3.400 caracteres.

Códigos de salida: `0` sin alertas críticas; `1` con alertas críticas; `2` error de uso o de datos (carpeta inexistente, extracto sin columnas, fila mal formada).

Ejemplo con datos **sintéticos** (la primera y la segunda orden son las del 12/11 que describe el bloc; el resto está inventado):

```
python3 -I conciliador_dinero.py --registro ejemplo_registro_SINTETICO --extracto ejemplo_extracto_SINTETICO.csv
```

Salida real de esa ejecución (código 1):

```
[Proyectos] Conciliación de binarias · 12/11/2026 18:10 a 12/11/2026 19:00 (hora de Colombia)
Compras: 4 por 16.73 USDT · liquidadas: 3 · aciertos: 2 · abiertas: 1
Neto según el registro: -1.39 USDT (-0.083 por USDT comprado)
Caja según el extracto: -9.05 USDT · según el registro: -12.05 USDT
Alertas críticas: 4 · avisos: 1
• [CRÍTICA] general: caja según el registro -12.05 USDT; según el extracto -9.05 USDT
• [CRÍTICA] A4: gana 5.65 USDT y el cobro figura «pedido»
• [CRÍTICA] ord-77: en el extracto hay 2.00 USDT pagados y 0.00 cobrados, sin fila en el registro
• [CRÍTICA] A3: estado «SIN CIERRE» sin cierre confirmado, 5.00 USDT en juego
• [aviso] ord-3: compra de 5.00 USDT del registro que no está en el extracto (revise su periodo)
```

Comprobación a mano de esa salida: compras 4,62 + 4,11 + 5,00 + 3,00 = 16,73. Neto del registro: −4,62 + 0,5735 + 2,6538 = −1,39. Caja del registro: −4,62 + 0,5735 − 5,00 − 3,00 = −12,05 (solo cuenta el cobro que figura como cobrado). Caja del extracto: −4,62 + 0,5735 − 3,00 − 2,00 = −9,05. La diferencia de −3,00 es la orden que falta en el extracto (−5,00) menos el movimiento que sobra (+2,00).

## Qué se probó

Ejecutado con `python3 -I prueba_conciliador.py`, sin dependencias fuera de la biblioteca estándar:

```
OK    t_cli_codigos_de_salida_y_salidas
OK    t_descuadres_y_pagos
OK    t_extracto_con_cobro_distinto_e_importe_distinto
OK    t_extracto_con_coma_decimal_sin_comillas_se_rechaza
OK    t_extracto_con_movimiento_no_registrado
OK    t_extracto_que_cuadra
OK    t_ganancia_sin_cobrar
OK    t_liquidacion_repetida_y_linea_ilegible
OK    t_orden_del_registro_fuera_del_extracto_es_aviso
OK    t_pago_fuera_de_formula_es_aviso
OK    t_registro_real_12_11
OK    t_sin_cierre_con_dinero
OK    t_sin_liquidar_respeta_la_gracia
OK    t_texto_telegram_cabe_en_un_mensaje

14 de 14 pruebas bien
```

Qué cubre cada grupo:

- **Caso real del 12/11** (`t_registro_real_12_11`): las dos compras del bloc (SUBE 4,62 a 0,55, perdió; BAJA 4,11 a 0,86, ganó 0,57) dan −4,05 USDT y ninguna alerta, ni crítica ni aviso. Como el neto sale del bloc y no de la prueba, esto valida también la tasa de 0,98.
- **Prueba de sensibilidad**: en una copia, al cambiar la tasa a 0,95 fallan 1 de 14 pruebas, y al quitar la alerta de ganancia sin cobrar fallan 2 de 14. Las pruebas sí detectan esos errores.
- **Que no escribe en el registro**: la prueba de línea de comandos compara los hash de los archivos antes y después.
- **Entradas dañadas**: líneas que no son JSON, liquidaciones repetidas, un CSV con coma decimal sin comillas (se rechaza), y una carpeta que no existe (código 2).
- **Límite del mensaje**: con 120 órdenes con alerta, el texto sigue dentro de 3.400 caracteres.

Los registros de cada prueba se crean en una carpeta temporal; no quedan datos en el repositorio.

## Qué no se probó

- **Con el registro real del operador.** No tengo acceso a la caja ni al teléfono. El formato de las filas (`orden leída`, `liquidación`, `cobro`, sus campos y estados) se tomó del código del ejecutor en `binarias/operador/ejecutor.py` y `operador.py`, de la rama `binarias/plan-v7-2026-11-04`. No se ha comprobado contra un archivo generado de verdad por el operador.
- **Con un extracto real de Binance.** No conozco el formato exacto que exporta la billetera de predicción. Si el extracto trae el número de orden con otro nombre o en otro formato, hay que adaptar las columnas antes de usar `--extracto`. Si el número de orden no coincide con el campo `orden` del registro, el cruce no servirá: lo primero que hay que revisar es ese número.
- **Las cifras del 12/11** están reconstruidas del texto del bloc, no tomadas del archivo del día.
- **El cobro automático con dinero real**, que el bloc tampoco tiene probado. Este programa lo vigila, pero no lo ejecuta ni lo prueba.
- **Tolerancias**: 0,01 USDT para el extracto y 1 % para la fórmula de pago son criterios míos; conviene revisarlos con datos reales.

## Lo que solo puede hacer el dueño

1. Copiar la carpeta `registro` del operador (de la caja o del teléfono) a un lugar donde se pueda ejecutar este programa.
2. Exportar el extracto de la billetera de predicción en Binance para el mismo periodo, y decir con qué columnas sale, para adaptar el formato.
3. Decidir si se corre a diario y si sus avisos llegan a Telegram.

Este programa no envía nada a ningún servicio, no usa claves ni la red, y no compra ni cobra.
