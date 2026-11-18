# Simulador de la regla de armado automático de binarias · propuesta del 18/11/2026

## Rama y carpeta

Esta entrega va en la rama `claude/proyectos-2026-11-18-regla70`, creada desde `master`. El nombre pedido, `claude/proyectos-2026-11-17`, ya existe en el repositorio con otro trabajo, y no se ha sobrescrito. La carpeta es `propuestas/2026-11-18-regla70/` por la misma razón: `propuestas/2026-11-17/` ya tiene un `LEEME.md` de otra entrega, y dos carpetas con el mismo nombre de archivo darían conflicto al unir.

## Qué es

Un programa que responde a una pregunta concreta sobre la regla de armado automático del operador:

> Si ninguna estrategia del Centro tiene ventaja, ¿con qué frecuencia la regla «18 de 25» arma el dinero real por azar? Y si la ventaja es real, ¿cuánto tarda en armar?

Compara la regla actual con tres alternativas:

- **30 de 40**: más apuestas por ventana, mismo criterio de aciertos.
- **Wilson 200 apuestas**: arma solo si el límite inferior del intervalo de Wilson (z = 1,96) de las últimas 200 apuestas queda por encima del equilibrio, 54,05 %.
- **Wilson 400 apuestas**: lo mismo con 400 apuestas.

Usa solo la biblioteca estándar de Python (3.11 o superior). No se conecta a Binance ni a la caja, no envía órdenes, no lee ni escribe archivos del operador y no toca `binarias/operador/` ni `binarias/aprobador/`.

## Por qué se propone

Según el código de la rama `binarias/plan-v7-2026-11-04`, en `binarias/operador/operador.py`:

- Líneas 51 y 52: `REGLA_ARMAR = "ARMAR_AL_70"` y `UMBRAL_ARMAR = 18`.
- Líneas 703 a 730, `_armar_solo`: una vez por minuto mira las cinco estrategias del Centro, con sus últimas 25 apuestas cerradas. Si alguna tiene 18 aciertos o más, arma los dos mercados con dinero real.
- Línea 724: calcula la aptitud del papel (`apto`) y la guarda, pero **no la exige**. El armado manual, en `_resolver_armar` (línea 546), sí la exige: sin papel apto no arma, salvo «operador armar igual». La regla automática arma aunque el papel no sea apto.

Este simulador mide el riesgo que eso crea. Con cinco estrategias, cada una con sus propias apuestas, y ventanas que se solapan, la regla mira muchas veces el mismo tipo de dato. Con una sola ventana de 25 apuestas, la probabilidad de 18 aciertos con moneda justa es 2,2 %. Repetida en el tiempo, se vuelve casi segura.

## Archivos

| Archivo | Para qué |
|---|---|
| `simulador_regla70.py` | El simulador. Se usa desde la línea de comandos. |
| `prueba_simulador.py` | 23 pruebas: exactitud de la probabilidad, cota de Wilson, orden de la ventana deslizante con casos sin azar y la salida del programa. |
| `resultados_ejemplo.txt` | La salida del programa con los valores por defecto y 5.000 repeticiones. |
| `resultados_pruebas.txt` | La salida de las pruebas. |

## Cómo se usa

```
python simulador_regla70.py
python simulador_regla70.py --reps 5000 --dias 60
python simulador_regla70.py --reglas 18/25,wilson:300:1.96 --p 0.5405,0.56
python prueba_simulador.py
```

Opciones principales:

- `--dias`: días de la simulación (30 por defecto).
- `--reps`: repeticiones por celda (1.000 por defecto; unos 5 segundos).
- `--semilla`: la misma semilla da la misma salida.
- `--pago`: pago del contrato por cada 1 apostado (0,85 por defecto; equilibrio 54,05 %).
- `--reglas`: reglas `k/n` o `wilson:N:z`, separadas por coma.
- `--p`: aciertos verdaderos a simular; `equilibrio` es el acierto de no perder.
- `--tasas`: apuestas por día de cada una de las cinco estrategias. Por defecto, las del Centro según el bloc (sección 5, paridad con c12 en 40 días: 1.155, 585, 109, 51 y 45 señales).

## Resultados (`resultados_ejemplo.txt`)

Probabilidad de que la regla arme dinero real al menos una vez en 30 días. Entre paréntesis, la mediana del día del primer armado entre las que arman. 5.000 repeticiones por celda; el error de muestreo es de unas décimas de punto.

| Regla | Sin ventaja (50 %) | En el equilibrio (54,05 %) | Con 55 % | Con 58 % |
|---|---|---|---|---|
| **18 de 25 (actual)** | **99,3 %** (6 d) | **100,0 %** (3 d) | 100,0 % (3 d) | 100,0 % (2 d) |
| 30 de 40 | 21,7 % (16 d) | 61,0 % (13 d) | 72,1 % (12 d) | 94,1 % (8 d) |
| Wilson 200 | 4,6 % (19 d) | 49,4 % (17 d) | 66,5 % (15 d) | 97,7 % (11 d) |
| Wilson 400 | 0,5 % (18 d) | 21,2 % (22 d) | 37,6 % (22 d) | 91,1 % (16 d) |

Lectura:

- Con moneda justa, es decir, sin ventaja, la regla actual arma en el 99 % de los periodos de 30 días, en mediana a los 6 días. Es la conclusión principal.
- La regla actual arma también en el equilibrio, que es el punto en que no se gana nada, y arma antes cuanto mejor es el acierto. Eso es lo que hace peligrosa una regla que no distingue ventaja de azar.
- Wilson 400 casi no arma sin ventaja (0,5 %), pero tarda más con una ventaja real: en el 58 % arma en el 91 % de los casos, en mediana a los 16 días. Es el costo de no confundir ventaja con azar.

## Qué quedó probado

- `python prueba_simulador.py`: 23 de 23 pruebas bien (salida en `resultados_pruebas.txt`).
  - La probabilidad exacta de 18 de 25 con moneda justa es 726.206 / 2^25 = 0,0216426, y la simulación de una sola ventana coincide con ella.
  - La cota de Wilson con 25 de 25 coincide con su forma cerrada, 1 / (1 + z²/n).
  - La ventana deslizante se prueba sin azar: con 25 fallos y luego aciertos, la regla 18 de 25 arma en el cierre 43; con 17 aciertos seguidos y luego fallos, no arma.
  - Sin aciertos no arma nunca; con 0,01 apuestas al día no llega a 25 cierres y no arma.
  - La misma semilla da la misma salida.
  - Las reglas mal escritas se rechazan con código de salida 2.
- Ejecución del programa con los valores por defecto (5.000 repeticiones), salida en `resultados_ejemplo.txt`.

## Qué no quedó probado y supuestos

- **Independencia.** Cada apuesta se simula como un acierto independiente con la misma probabilidad. El mercado real agrupa los resultados: si hay dependencia, lo más probable es que aumente los armados por azar, porque las ventanas extremas se vuelven más frecuentes. No está medido.
- **Estrategias seleccionadas.** Las cinco del Centro se eligieron entre cientos de variantes. Con esa selección, el acierto pasado de las elegidas suele ser más alto que su acierto futuro. El simulador no lo modela: supone un acierto constante por estrategia. Esto no cambia la conclusión sobre la regla, porque el armado depende de los aciertos futuros, pero sí significa que las tasas de acierto del bloc no son estimaciones limpias.
- **Aptitud del papel.** La regla automática no exige `apto`. El simulador tampoco lo modela: calcula solo cuándo se cumple la regla de aciertos.
- **Orden de cierres.** Se supone que las apuestas de una estrategia cierran en el orden en que el Centro las cuenta. La evaluación se hace al cierre, no al minuto; la diferencia es de como mucho un minuto.
- **Tasas.** Las apuestas por día vienen del bloc (sección 5). No se han comprobado contra el registro del Centro en vivo.
- **Lo que hace el operador hoy.** Este trabajo no ha visto el estado del operador en la caja o en el teléfono. No se sabe si la regla ya armó desde las 11:29 del 18/11/2026, que es la última anotación del bloc.
- **La decisión COMPRAR.** La compra real también pasa por la decisión COMPRAR de la rutina (`binarias/operador/aprobacion.py`), que se apoya en el criterio de 19 de 25 del nodo. El simulador no modela esa segunda barrera; mide solo el armado.

## Lo que solo puede hacer el dueño

1. Decidir si la regla automática sigue puesta. Para quitarla: «operador parar», que desarma y quita la regla. Esta propuesta no la cambia ni la toca.
2. Si la regla sigue, elegir una de estas dos vías, en `binarias/operador/` (que esta propuesta no toca):
   - exigir `apto` en `_armar_solo`, como lo exige `_resolver_armar`;
   - cambiar `UMBRAL_ARMAR` por un criterio como Wilson 400, con el costo de tardar más en armar cuando la ventaja es real.
3. Decidir cuántas apuestas por ventana quiere para confiar en un acierto. Con 25 no alcanza para distinguir 54 % de 50 %.

Ninguna de estas decisiones se ha aplicado. El simulador sirve para compararlas antes de decidir.
