# Evaluador de ventaja para las binarias · propuesta del 17/11/2026

## Qué es

Un programa que responde una sola pregunta sobre las apuestas de binarias ya resueltas: ¿el acierto de cada estrategia supera el equilibrio por más de lo que explica el azar?

Usa solo la biblioteca estándar de Python (3.11 o superior). No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono y no escribe en ningún otro lado. Solo lee un archivo y escribe en pantalla (y en JSON, si se pide).

Por qué se propone: el criterio que hoy decide las compras del nodo (19 de 25 aciertos con ganancia en la ventana) no tiene intervalo de confianza ni corrección por la cantidad de estrategias que se miran. Con 25 apuestas, un acierto de 76 % parece ganancia y puede ser azar. Este evaluador pone esa cuenta por escrito, con la misma convención del bloc (equilibrio = precio / 0,98).

## Archivos

| Archivo | Para qué |
|---|---|
| `evaluador_ventaja.py` | El evaluador. Se usa desde la línea de comandos. |
| `prueba_evaluador.py` | 27 pruebas. Con `--ejemplo` escribe el archivo de ejemplo. |
| `ejemplo_SINTETICO.csv` | Datos inventados con semilla fija. **No son apuestas reales**: sirven para ver la salida. |

## Cómo se usa

1. Prepare un archivo con una apuesta resuelta por línea. CSV con encabezado:

   ```
   estrategia,precio,acierto,fecha
   E1,0.51,1,2026-11-10
   E1,0.52,0,2026-11-10
   ```

   - `estrategia`: código o nombre (E1, E2…).
   - `precio`: lo pagado por el lado comprado, entre 0 y 1. Se acepta `0,51` o `0.51`. Un `51` se rechaza.
   - `acierto`: `1` si acertó, `0` si falló. En empate, `0`.
   - `fecha`: opcional, solo se muestra.

   También acepta JSONL (`.jsonl`), con las mismas claves.

2. Ejecute:

   ```
   python evaluador_ventaja.py apuestas.csv
   python evaluador_ventaja.py apuestas.csv --min 100 --comision 0.02 --json resultado.json
   ```

3. Pruebe primero con el ejemplo sintético:

   ```
   python prueba_evaluador.py
   python evaluador_ventaja.py ejemplo_SINTETICO.csv
   ```

Cualquier fila mala detiene la lectura y dice la línea. No corrige nada en silencio.

## Cómo se lee la salida

- **Equilibrio**: el acierto mínimo para no perder con ese precio y esa comisión.
- **Intervalo 95 %**: el rango donde está el acierto real con los datos que hay (intervalo de Wilson, con corrección por la cantidad de estrategias).
- **Ganancia y cota inferior**: la ganancia esperada por USDT con el acierto medido, y con el extremo bajo del intervalo.
- **Veredicto**:
  - `PRUEBA INSUFICIENTE`: menos de `--min` apuestas. No dice nada de la estrategia.
  - `VENTAJA DEMOSTRADA`: la cota inferior supera el equilibrio.
  - `SIN VENTAJA`: la cota superior queda bajo el equilibrio.
  - `NO DEMOSTRADA`: el intervalo cruza el equilibrio. Puede ser azar.
- **Faltan**: cuántas apuestas más harían falta si el acierto se mantiene. Es aproximado.

La corrección por estrategias (Bonferroni) es deliberada: se miran varias y se elige la mejor. Con cinco estrategias, cada una se prueba con el nivel de 99,0 % en dos colas (z = 2,58), no con 95 %.

## Lo que muestra sobre las cifras que ya están en el bloc

Estas cuentas usan cifras publicadas en el bloc (17/11, 09:27) y el precio supuesto de 0,51. No son datos nuevos ni son del papel de la caja:

| Estrategia (en vivo) | Aciertos | Acierto | Equilibrio (0,51) | Cota inferior, corregida por 5 | Veredicto |
|---|---|---|---|---|---|
| E1 | 69 de 121 | 57,0 % | 52,0 % | 45,4 % | NO DEMOSTRADA |
| E2 | 41 de 74 | 55,4 % | 52,0 % | 40,7 % | NO DEMOSTRADA |
| E3 | 12 de 18 | 66,7 % | 52,0 % | 37,3 % | PRUEBA INSUFICIENTE |
| E5 | 49 de 91 | 53,8 % | 52,0 % | 40,6 % | NO DEMOSTRADA |

Lectura: con las cifras publicadas, ninguna estrategia tiene ventaja demostrada. La de mejor acierto aparente (E3) tiene apenas 18 apuestas.

La regla del nodo (19 de 25 a precio 0,544; equilibrio 55,5 %):

- Con z = 1,96 (una sola mirada), la cota inferior es 56,6 %. Pasa el equilibrio por poco.
- Con la corrección de cinco estrategias, la cota inferior baja a 50,2 %. No prueba nada.

Conclusión para la regla: ni con una sola mirada se puede asegurar la ventaja con 25 apuestas, y el nodo mira cada minuto y varias estrategias a la vez. La regla queda débil.

## Qué quedó sin probar

- **Con datos reales de la caja o del papel**: no se corrió sobre el registro de apuestas de papel de la caja, porque no está en la nube. Solo se probó con datos sintéticos y con las cifras del bloc.
- **Comisión de 2 %**: es la convención del bloc (0,98 / precio − 1). No se verificó contra la liquidación real de Binance. Con `--comision` se puede cambiar.
- **Independencia**: el intervalo de Wilson supone apuestas independientes. Si las apuestas de un mismo día están correladas (racha, mismo movimiento de mercado), el intervalo real es más ancho y el veredicto de «VENTAJA DEMOSTRADA» sería optimista.
- **Montos iguales**: la ganancia por USDT supone la misma cantidad en cada apuesta. El comprador usa montos distintos; eso cambia la ganancia en pesos, no el veredicto de acierto.
- **Corrección por estrategias**: Bonferroni es conservador. Si se mira una estrategia elegida antes de ver datos, la corrección sobra. Se dejó así porque el bloc dice que las estrategias salen de cientos de variantes.
- **No está conectado** a `binarias/nodo/` ni a `binarias/operador/`. Eso lo decide usted: propone reemplazar el criterio «19 de 25 con ganancias» por el veredicto de este evaluador, y que una compra solo se permita con `VENTAJA DEMOSTRADA` sobre el papel. No se tocó ningún archivo de `binarias/`.

## Lo que solo puede hacer el dueño

- Decidir si este veredicto entra en el nodo o en el operador. Esos cambios van en su carpeta, no aquí.
- Exportar el registro del papel de la caja a CSV (estrategia, precio, acierto) y correr el evaluador sobre ese archivo. Ese es el primer dato real que hace falta.
- Confirmar la comisión real de la app de Binance para una apuesta resuelta.

## Rama y entrega

Rama `claude/proyectos-2026-11-17`, carpeta `propuestas/2026-11-17/`. Sin PR y sin unir a `master`.
