# Verificador de cifras de binarias sobre las pruebas reales · propuesta del 17/11/2026

## Qué es

Un programa que recalcula, desde los archivos de pruebas a ciegas de `binarias/pruebas/` (las `*_apuestas.csv`), las cifras con las que se decide la estrategia de binarias. Para cada archivo calcula:

- el acierto, con intervalo de confianza del 95 % (Wilson); un empate cuenta como fallo, como dice el bloc;
- el acierto si la entrada llega 60 s tarde, cuando el archivo trae esa columna;
- el equilibrio para cada precio de compra supuesto (precio / 0,98);
- el valor esperado por USDT apostado;
- el **precio máximo de compra** que aún da ventaja, con el centro y con el límite inferior del intervalo.

Usa solo la biblioteca estándar de Python (3.8 o superior). No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono y no escribe fuera del archivo que se le pida con `--json`.

## Por qué esta y no otra

Las propuestas anteriores de binarias de esta rutina ya cubren la ventaja con precio (`claude/proyectos-2026-11-17`), la vigilancia por periodos (`claude/proyectos-2026-11-17-b`), el puente del papel (18/11), el simulador de la regla del 70 % (18/11), la prueba secuencial (19/11) y el auditor de reglas de dinero (`claude/proyectos-2026-11-19-b`). Revisé los LEEME de las de 17/11, 19/11 y 19/11-b: trabajan con datos sintéticos o con la regla del operador.

Ninguna recalcula las cifras que el bloc usa para decidir, sobre las pruebas reales que están en el repositorio. Esta propuesta hace eso, y lo hace sobre el punto que más pesa en la decisión: el precio al que se compra y el retraso de la entrada. El bloc ya dice que entrar 60 s tarde quita unos 2 puntos de acierto; aquí se comprueba con los archivos, y se convierte en un precio máximo de compra.

## Cómo se usa

```
python3 verificador_cifras.py CARPETA_O_ARCHIVOS...
python3 verificador_cifras.py binarias/pruebas --precio 0.50 0.544 0.55 0.60 --json resultados.json
```

- `CARPETA_O_ARCHIVOS`: una carpeta (lee todas las `*_apuestas.csv`) o archivos concretos.
- `--precio`: precios de compra a evaluar, entre 0 y 1. Por defecto 0,50, 0,544, 0,55 y 0,60. El 0,544 es el precio medio a los 30 s que anota el bloc (AL FRENTE del 18/11, 15:45).
- `--cobro`: cobro por USDT si acierta, sin el precio. Por defecto 0,98, la convención del bloc («Ganar» = 0,98 ÷ precio).
- `--json`: escribe los mismos resultados en JSON.

Códigos de salida: `0` correcto; `2` algún archivo no se puede leer o trae valores que no entiende (no se ignoran en silencio).

Pruebas: `python3 prueba_verificador.py` (21 pruebas, salida en `salida_pruebas.txt`).

## Resultados sobre las pruebas reales

Salida completa en `salida_real_pruebas_binarias.txt`. Resumen de las pruebas que más pesan:

| Archivo | Apuestas | Acierto | IC 95 % | Entrada 60 s tarde | Precio máximo (centro / IC, 60 s) |
|---|---:|---:|---|---:|---|
| t18 BTCUSDT | 16.961 | 57,95 % | 57,21–58,69 | 56,45 % | 0,568 / 0,561 (0,546) |
| t19 BTCUSDT | 43.164 | 57,28 % | 56,82–57,75 | 55,82 % | 0,561 / 0,557 (0,542) |
| t25 unificado | 23.049 | 58,25 % | 57,61–58,88 | 55,99 % | 0,571 / 0,565 (0,542) |
| t18 ETHUSDT | 11.070 | 56,60 % | 55,68–57,52 | 55,31 % | 0,555 / 0,546 (0,533) |
| t19 ETHUSDT | 36.370 | 56,36 % | 55,85–56,87 | 55,00 % | 0,552 / 0,547 (0,534) |
| t19 PAXGUSDT (oro) | 21.368 | 58,71 % | 58,05–59,37 | 56,54 % | 0,575 / 0,569 (0,548) |
| t18 XAUUSDT (oro) | 1.671 | 53,62 % | 51,22–56,00 | 54,28 % | 0,525 / 0,502 (0,508) |
| t29, t30, t31 (varias variantes) | 7.000–35.700 | 42,9–45,6 % | | no tienen la columna | 0,41–0,45 |

Valor esperado por USDT a precio 0,544 (equilibrio 55,51 %), centro y con entrada 60 s tarde:

- t18 BTCUSDT: +4,40 % y **+1,69 %** (ventaja demostrada en ambos casos).
- t19 BTCUSDT: +3,20 % y +0,57 % (con 60 s tarde, sin decidir).
- t25 unificado: +4,93 % y +0,86 % (con 60 s tarde, sin decidir).
- t18 ETHUSDT: +1,97 % y −0,36 % (sin decidir).
- Oro (PAXG y XAU): ventaja demostrada en PAXG con 60 s tarde (+1,85 %), pero el oro no existe en los Contratos de Evento de Binance según el bloc.

Lo que dicen estos números, en orden de peso:

1. **El precio de compra decide.** Con entrada 60 s tarde, la ventaja de BTC y ETH se queda en torno al límite de 0,53–0,55. El precio medio que anota el bloc (0,544) cae justo ahí: en el caso de BTC, aproximadamente la mitad de las compras quedarían por encima del tope.
2. **El tope que conviene es fijo, no «lo que vio más 0,02».** El operador compra hasta 0,02 por encima del precio que vio (bloc, AL FRENTE del 18/11, 16:01). Si ese precio visto es 0,52, el tope efectivo sube a 0,54, justo en el límite. Un tope absoluto cerca de 0,54 para BTC y ETH sería más claro. **Esto es una propuesta de cambio: no se ha tocado `binarias/operador/`.**
3. **Retraso de la entrada.** El bloc anota que el operador entra unos 25 s después de la señal. La columna de 60 s tarde es un proxy más duro, así que la realidad debe estar entre el dato sin retraso y el de 60 s.
4. **Las cifras del bloc no se reproducen exactas.** El bloc dice «58,0 % en 16.898 apuestas» para las reglas de BTC. El archivo t18 BTCUSDT trae 16.961 apuestas y 57,95 %. No se ha podido identificar de qué archivo sale la cifra del bloc. Diferencia pequeña, pero conviene saberlo.
5. **Estas pruebas no son el precio real del mercado.** Las pruebas de la carpeta asumen un precio y no traen el precio que tenía el mercado en el momento de comprar. El bloc anota que, con precio real en papel, ninguna fuente ha ganado todavía. Este verificador no contradice eso: calcula lo que las pruebas dicen, a precios supuestos.
6. **Las variantes de 45 % no son una estrategia.** t29, t30 y t31 aciertan entre 42,9 % y 45,6 %. Su complementario (cambiar acierto por fallo) quedaría en torno a 54 %, por debajo del equilibrio a 0,544. No lo tomo como estrategia; solo lo anoto.

## Qué no se ha probado

- **No hay precio real por apuesta en las pruebas.** Los precios que usa el verificador son supuestos (de 0,50 a 0,60). El 0,544 viene del análisis de papel del bloc, no de esta prueba.
- **El retraso de 60 s es un proxy.** El retraso real del operador (unos 25 s, según el bloc) no está en los datos; no se ha podido interpolar.
- **No corrige por selección.** Las estrategias de las pruebas se eligieron entre cientos de variantes. El intervalo de cada archivo no cuenta eso. Para la corrección por cantidad de estrategias sirve el evaluador de la propuesta del 17/11 (`claude/proyectos-2026-11-17`); no se ha integrado aquí.
- **El cobro 0,98 es el que dice el bloc.** No está comprobado contra la app de Binance.
- **Los empates cuentan como fallo.** Es la regla del bloc. En t19 PAXG son 1.599 de 21.368 (7,5 %), y cambiar la regla moverá esas cifras.
- **Las pruebas del repositorio no están en esta rama.** La salida se generó con una copia de `binarias/pruebas/` del branch `binarias/plan-v7-2026-11-04`. Para repetirla, copie esos archivos a una carpeta y use la orden de arriba.

## Archivos

| Archivo | Para qué |
|---|---|
| `verificador_cifras.py` | El verificador. Se usa desde la línea de comandos. |
| `prueba_verificador.py` | 21 pruebas con archivos temporales y valores conocidos. |
| `salida_pruebas.txt` | Salida de las 21 pruebas (todas correctas). |
| `salida_real_pruebas_binarias.txt` | Salida sobre los 17 archivos reales de `binarias/pruebas/`. Solo totales; no hay datos personales. |

## Lo que solo puede decidir el dueño

- Si el tope de compra en el operador pasa a ser un valor fijo (propuesta: cerca de 0,54 para BTC y ETH, con 60 s tarde en la prueba). Es un cambio en `binarias/operador/`, que no se ha tocado.
- Si se conserva la entrada 60 s tarde como escenario de referencia para decidir.
- Si el papel con precio real sigue siendo el criterio final. Ninguna cifra de esta propuesta sustituye a ese papel.
