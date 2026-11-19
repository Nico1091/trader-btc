# Prueba secuencial de ventaja para las binarias · propuesta del 19/11/2026

## Rama y carpeta

Esta entrega va en la rama `claude/proyectos-2026-11-19`, creada desde `master`. El nombre pedido, `claude/proyectos-2026-11-17`, ya existe en el repositorio con el evaluador del 17/11, y no se ha sobrescrito. Tampoco se usó `propuestas/2026-11-17/`, que ya ocupa esa entrega; la carpeta lleva la fecha de hoy.

## Qué es

Un programa que responde a una pregunta concreta: **¿cuándo se puede declarar ventaja de una estrategia si la cuenta se mira después de cada apuesta?**

Usa una prueba secuencial de Wald (razón de verosimilitud). Para cada estrategia suma, apuesta a apuesta, cuánto apoyan los datos la hipótesis «acierta 3 puntos por encima del equilibrio» frente a «no hay ventaja», y se detiene en cuanto cruza un límite. Con esta regla, la probabilidad de declarar ventaja por azar queda por debajo de `--alfa` aunque se mire después de cada apuesta. Con cinco estrategias, `alfa` se reparte entre ellas (corrección de Bonferroni).

Solo usa la biblioteca estándar de Python (3.11 o superior). No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono y no toca `binarias/operador/` ni `binarias/aprobador/`.

## Por qué se propone

- La regla que arma el operador (18 aciertos en 25, en cualquiera de las cinco estrategias, una vez por minuto; `binarias/operador/operador.py`, `REGLA_ARMAR` línea 51, `UMBRAL_ARMAR` línea 52, `_armar_solo` desde la línea 705) mira los mismos datos muchas veces. Sin ninguna ventaja, la simulación de abajo la ve armar en el 100 % de las réplicas.
- La propuesta de `claude/proyectos-2026-11-18-regla70` simula esa regla y compara alternativas de tamaño fijo (30 de 40, Wilson de 200 y de 400 apuestas). Esta añade lo que faltaba: un criterio que sirve para mirar en cada apuesta sin inflar el error.
- Responde a la pregunta práctica: cuántas apuestas hacen falta por estrategia. Con 25 apuestas, ninguna estrategia puede decidirse.

## Archivos

| Archivo | Para qué |
|---|---|
| `secuencial_ventaja.py` | La prueba. Se usa desde la línea de comandos. |
| `prueba_secuencial.py` | 24 pruebas automáticas. |
| `ejemplo_SINTETICO.csv` | Datos inventados con semilla fija. **No son apuestas reales.** |
| `salida_ejemplo.txt`, `salida_simulacion.txt`, `simulacion_resultados.json`, `salida_pruebas.txt` | Salidas reales de las ejecuciones de esta entrega. |

## Cómo se usa

El formato del archivo es el mismo del evaluador del 17/11: una apuesta resuelta por línea, en orden cronológico.

```
estrategia,precio,acierto,fecha
E1,0.51,1,2026-11-10
E1,"0,52",0,2026-11-10
```

- `precio`: lo pagado por el lado comprado, entre 0 y 1. Con coma decimal, debe ir entre comillas en un CSV. Un `51` se rechaza y dice la línea.
- `acierto`: `1` si acertó, `0` si falló.
- También acepta JSONL (`.jsonl`) con las mismas claves.

```
python secuencial_ventaja.py apuestas.csv
python secuencial_ventaja.py apuestas.csv --delta 0.05 --alfa 0.05 --json resultado.json
python secuencial_ventaja.py --simular
python secuencial_ventaja.py --ejemplo ejemplo_SINTETICO.csv
python prueba_secuencial.py
```

Pago: se supone 0,98 por USDT, es decir, el equilibrio de una apuesta a precio `p` es `p / 0,98`, la misma convención del bloc. Si el pago real de Binance es otro, se pasa con `--comision`.

## Cómo se lee la salida

- **Límite para declarar VENTAJA**: `ln(K / alfa)`. Con cinco estrategias y alfa 0,05, vale 4,61 (razón de 100 a 1).
- **Límite para descartar**: `ln(beta)`, −1,61 con beta 0,20. Si se cruza, la ventaja de `--delta` queda descartada con una probabilidad de error de beta.
- **Estado**:
  - `VENTAJA`: la razón cruzó el límite superior. Es la única señal con garantía de error.
  - `SIN VENTAJA`: cruzó el límite inferior. No hay ventaja del tamaño de `--delta`.
  - `ABIERTA`: faltan datos. La columna «Faltan» dice cuántas apuestas harían falta si la ventaja real fuera exactamente `--delta`.

## Simulación: esta regla contra la de hoy

Parámetros: 500 réplicas, 5 estrategias independientes, 1000 apuestas por estrategia, semilla 1, ventaja a detectar 3 puntos, precios entre 0,45 y 0,55. Las dos reglas ven las mismas apuestas.

| Ventaja real | Regla actual (18 de 25): arma | Mediana (apuestas) | Prueba secuencial: arma | Mediana (apuestas) |
|---|---|---|---|---|
| Ninguna | 100,0 % | 53 | 0,2 % | 829 |
| +3 puntos | 100,0 % | 35 | 44,4 % | 783 |
| +5 puntos | 100,0 % | 31 | 96,2 % | 629 |
| +10 puntos | 100,0 % | 25 | 100,0 % | 322 |

«Arma» es la proporción de réplicas en las que la regla arma en alguna estrategia dentro del horizonte.

Lectura:

- Sin ventaja, la regla actual arma siempre; la prueba secuencial arma en el 0,2 %, por debajo del límite teórico de 5 %.
- Con una ventaja real de 3 puntos, la prueba secuencial necesita casi mil apuestas por estrategia para decidir en menos de la mitad de los casos. Es la cifra que conviene tener presente antes de cualquier armado.
- La regla actual no distingue una ventaja de 10 puntos de la ausencia de ventaja: arma igual en todos los casos.

## Ejemplo con datos sintéticos

`python secuencial_ventaja.py ejemplo_SINTETICO.csv`, con 60 apuestas por estrategia (datos inventados, E4 con 5 puntos de ventaja):

- Todas las estrategias quedan `ABIERTA`.
- E3 acierta el 65 % y su log-razón es 0,93, lejos del límite de 4,61. Faltan unas 2.000 apuestas aproximadas para decidir.

Esto no dice nada del bot real: solo muestra la salida.

## Pruebas

24 pruebas, todas bien (`salida_pruebas.txt`). Comprueban el equilibrio, la esperanza del incremento sin ventaja (no es positiva), los límites con una y con cinco estrategias, la lectura de errores (con número de línea), el cruce exacto del límite, la regla actual frente a la prueba sin ventaja, y la repetibilidad con semilla fija.

## Lo que no se probó

- **No se probó con apuestas reales.** El registro vive en el teléfono y en el PC, y no está en la nube. Los datos de ejemplo son inventados.
- **Independencia.** La simulación supone estrategias independientes. En el mercado real no lo son: las cinco miran el mismo BTC y apuestan sobre los mismos ciclos. La garantía de error sí se mantiene, porque la cota de Bonferroni no exige independencia; lo que falla es que el número de réplicas que arman sea exacto.
- **Requisito de la garantía.** Vale si, dado todo lo anterior, la probabilidad de acierto de cada apuesta no supera su equilibrio. Si el pago real difiere de 0,98 ÷ precio, la garantía se refiere a otro equilibrio.
- **Orden de las apuestas.** Se supone cronológico en el archivo; si no lo está, el resultado no sirve.
- **Precios.** La simulación cubre precios de 0,45 a 0,55, el rango típico del bloc. Los extremos no se simularon.

## Lo que solo puede decidir el dueño

- Si quiere sustituir la regla 18 de 25 del operador por esta prueba. Eso toca `binarias/operador/`, que no se modificó. Cambio propuesto: en `_armar_solo` (línea 705), reemplazar el umbral de `UMBRAL_ARMAR` por el límite superior de esta prueba, por estrategia, con alfa 0,05 repartido entre las cinco y delta 0,03, leyendo el registro propio de cada estrategia. Convendría además exigir el papel apto, como ya hace el armado manual.
- Confirmar el pago real por apuesta (0,98 ÷ precio) con una apuesta del propio registro.
- Aceptar que, con el volumen actual, ninguna estrategia podrá decidirse en semanas.

## Qué sigue

- Cuando haya un registro exportado de apuestas reales, ejecutar `python secuencial_ventaja.py registro.csv` y revisar la columna «Faltan».
- Si se quiere una garantía para la vigilancia continua, fijar K (número de estrategias) antes de empezar: el código reparte alfa según las estrategias que aparecen en el archivo.
