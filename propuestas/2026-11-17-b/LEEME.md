# Vigilancia de ventaja por periodos · propuesta del 18/11/2026

## Rama

Esta entrega va en la rama `claude/proyectos-2026-11-17-b`. La rama `claude/proyectos-2026-11-17` ya existía en el repositorio con otro trabajo (el evaluador de ventaja del 17/11), y no se ha sobrescrito.

## Qué es

Un programa que responde a una pregunta que el evaluador del 17/11 no contesta: **¿la ventaja de cada estrategia se mantiene en el tiempo o se está gastando?**

Parte las apuestas resueltas de cada estrategia en periodos (mes, trimestre o año) y muestra:

- en cuántos periodos el acierto supera el equilibrio;
- si el último periodo sigue por encima;
- la tendencia del acierto por periodo;
- cuántas apuestas más harían falta para decidir con el acierto medido.

Usa solo la biblioteca estándar de Python (3.11 o superior). No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono y no toca `binarias/operador/` ni `binarias/aprobador/`.

## Por qué se propone

El bloc documenta el riesgo: «la ventaja existe, pero se gasta» (la regla base pasó de 60,3 % en 2020 a 55,5 % en 2026) y las estrategias se eligieron entre cientos de variantes. Un promedio global no lo detecta. Un ejemplo de la propia prueba t29: «contra la ruptura» da 54,3 % en el conjunto, pero 55,3 % en 2021-23 y 52,9 % en 2024-26, por debajo del equilibrio.

## Archivos

| Archivo | Para qué |
|---|---|
| `vigilancia_ventaja.py` | El programa. |
| `prueba_vigilancia.py` | 24 pruebas. Los valores esperados están calculados a mano o con una fórmula aparte. |
| `LEEME.md` | Este documento. |

## Cómo se usa

El formato de entrada es un CSV con una apuesta resuelta por fila. Acepta:

- el de `evaluador_ventaja.py`: `estrategia,precio,acierto,fecha` (con `precio`, el equilibrio sale del precio);
- el de las pruebas del bloc: `fecha_hora_colombia;sentido;plazo_min;resultado` (separador `;`, con o sin BOM; resultado `acierta`, `falla` o `empate`, y el empate cuenta como fallo).

```
python vigilancia_ventaja.py apuestas.csv
python vigilancia_ventaja.py apuestas.csv --periodo mes --detalle
python vigilancia_ventaja.py apuestas.csv --grupo sentido,plazo_min
python vigilancia_ventaja.py apuestas.csv --pago 0.8130 --json resultado.json
python vigilancia_ventaja.py --ejemplo ejemplo_SINTETICO.csv
```

Reglas de lectura:

- Cualquier fila mala detiene la lectura y dice el número de línea. No corrige nada en silencio. Un precio escrito como `51` se rechaza.
- Con decimal coma en el precio, el separador debe ser `;`.
- Sin columna `estrategia`, todas las apuestas forman un grupo; use `--grupo` para separarlas.
- El equilibrio sin columna `precio` es `1 / (1 + pago)`, con `--pago` (0,85 por defecto). Con columna `precio`, es `precio medio / (1 - comisión)`, con `--comision` (0,02 por defecto).
- La corrección por varios grupos es Bonferroni, igual que en el evaluador.

### Veredictos (reglas de este programa, no del bloc)

| Veredicto | Cuándo |
|---|---|
| `PRUEBA INSUFICIENTE` | Menos de `--min-total` apuestas (100). |
| `SIN VENTAJA` | El extremo alto del intervalo corregido queda por debajo del equilibrio. |
| `INCONCLUSA` | El intervalo corregido cruza el equilibrio. |
| `VENTAJA, PERIODOS INSUFICIENTES` | El intervalo supera el equilibrio, pero hay menos de 3 periodos válidos. |
| `VENTAJA NO SOSTENIDA` | El intervalo supera el equilibrio, pero el último periodo queda debajo o menos del 75 % de los periodos válidos lo superan. |
| `SOSTENIDA` | El intervalo supera el equilibrio, el último periodo también, y al menos el 75 % de los periodos válidos lo superan. |

Los umbrales (3 periodos, 75 %) están en el código, como constantes (`MIN_PERIODOS_VALIDOS`, `FRACCION_ESTABLE`). Son criterios razonables, no comprobados; conviene discutirlos antes de usar el veredicto para decidir algo.

## Lo que salió con datos reales (pruebas del bloc, no apuestas reales)

Los CSV están en `binarias/pruebas/` de la rama `binarias/plan-v7-2026-11-04`. Son simulaciones del propio bloc, con equilibrio de 54,1 % (pago 0,85).

| Archivo | Grupos | Resultado |
|---|---|---|
| `t29_BTCUSDT_apuestas.csv` (a favor de la ruptura, como la usa el bloc) | 1 | 45,6 %. `SIN VENTAJA`; 0 de 28 trimestres sobre el equilibrio. |
| `t25_unificado_apuestas.csv` | 1 | 58,2 %, intervalo corregido 57,6 a 58,9 %. `SOSTENIDA`. Ver la advertencia de abajo. |
| `t18_BTCUSDT_apuestas.csv` | 17 (estrategias) | Una sola `SOSTENIDA`: rompimiento de 20 velas, 59,2 %, 20 de 21 trimestres sobre el equilibrio; el último, 54,7 %. Las otras 16: 7 `INCONCLUSA` y 9 `PRUEBA INSUFICIENTE` (ninguna `SIN VENTAJA` con estos datos). |

### Sensibilidad: la convención de la comisión decide el veredicto

Con `t18` y el rompimiento de 20 velas:

| Convención del equilibrio | Equilibrio | Veredicto |
|---|---|---|
| Pago 0,85 tal cual (la del bloc) | 54,05 % | `SOSTENIDA` (20 de 21) |
| Comisión 2 % sobre la ganancia (0,85 × 0,98) | 54,56 % | `SOSTENIDA` (20 de 21) |
| Comisión 2 % sobre la apuesta (la de `comprador/REGLAS-ANTES-DE-MEDIR.md`, G = p(1−c)/q − 1) | 55,16 % | `VENTAJA NO SOSTENIDA` (17 de 21; último periodo 54,7 %, bajo) |

Ese dato no lo puede resolver el programa: solo la app de Binance dice si el 0,85 ya incluye la comisión. Hasta entonces, cualquier veredicto `SOSTENIDA` de estas pruebas depende de esa suposición. Para repetir la sensibilidad: `--pago 0.8130` (punto decimal, porque `--pago` lo lee como número) da el equilibrio de 55,16 %.

## Advertencias

- **Dentro de muestra.** El programa no sabe si la regla se fijó antes de ver los datos. Una `SOSTENIDA` sobre `t18` o `t25` es un resultado sobre los mismos datos que eligieron la estrategia. Solo una regla fijada antes y medida después, en papel con precio real, vale como prueba.
- **Aproximación normal** para las apuestas necesarias. Con pocas apuestas o aciertos extremos, es aproximada.
- **Sin modelo de la pérdida de precio** (el precio se fija al apostar y varía con la volatilidad) ni de la entrada tardía de 60 s; eso lo mide el bloc por separado.
- **Sin registro de papel real todavía.** El puente del 18/11 (`claude/proyectos-2026-11-18`) lo convertirá en el formato de este programa cuando la caja tenga compras de papel con precio real.

## Probado

- `python prueba_vigilancia.py`: 24 pruebas, todas correctas. Cubren el intervalo de Wilson, la corrección por grupos, el equilibrio con y sin precio, el número de apuestas necesarias (cálculo a mano: 194), la división por periodos, la tendencia, la lectura de los dos formatos, los errores con número de línea y los cuatro veredictos con casos construidos.
- `--ejemplo`: datos sintéticos con semilla fija. Sale `SOSTENIDA`, `VENTAJA NO SOSTENIDA` y `SIN VENTAJA` para los tres perfiles diseñados. El ejemplo confirma el comportamiento; no es una validación de las estrategias.
- Ejecución sobre `t18`, `t25` y `t29` (tabla de arriba) y la sensibilidad de la comisión.

## Sin probar

- Con un registro de papel real (todavía no existe).
- Con más de un archivo a la vez o con periodos de distinta longitud dentro de un mismo grupo; el programa los trata por el calendario, sin ponderar.
- En Windows con la configuración regional de la caja; se probó en Linux con Python 3.11.

## Lo que solo puede hacer el dueño

1. Confirmar en la app de Binance si el pago de 0,85 ya descuenta la comisión del 2 %. Es lo que decide si el rompimiento de 20 velas sigue `SOSTENIDA`.
2. Decidir si una regla se fija antes de ver datos nuevos y se mide solo en papel con precio real, como exige el propio bloc.
3. Pasar el registro de papel de la caja a su PC cuando exista, para usar este programa o el puente sobre datos reales.
