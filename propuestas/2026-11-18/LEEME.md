# Puente del registro de papel al evaluador de ventaja · propuesta del 18/11/2026

## Qué es

Un programa que toma el registro de papel que escribe el operador de binarias (`registro/AAAAMMDD.jsonl`) y deja un CSV con una fila por apuesta resuelta: `estrategia, precio, acierto, fecha`. Ese CSV es lo que lee `evaluador_ventaja.py`, la herramienta que ya está en la rama `claude/proyectos-2026-11-17`, carpeta `propuestas/2026-11-17/`.

Usa solo la biblioteca estándar de Python (3.11 o superior). No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono, no toca `binarias/operador/` ni `binarias/aprobador/`.

## Por qué se propone

El evaluador de la rama del 17/11 responde si una estrategia tiene ventaja. Pero su único dato de entrada son cifras escritas a mano. El primer dato real que hace falta es el registro de papel con precio real, y hoy pasar ese registro al evaluador exige copiar y transformar a mano. Este programa hace esa transformación con reglas fijas, las que ya están en el código del operador:

- Cuenta solo compras de papel reales (`tipo: llenado`, `compra: true`, `serie: papel`). Las miradas en sombra no se operan y salen del conteo, salvo con `--con-sombra`.
- Una apuesta por ventana. Los llenados de 5 y 15 segundos de la misma decisión no son dos apuestas independientes: cuenta el de hora más temprana.
- El precio es el campo `q`, lo pagado por el lado comprado, no el precio supuesto.
- El resultado sale de la fila `resultado` de la misma ventana. Empate cuenta como fallo, según la convención del bloc.
- Las apuestas abiertas, sin ganador oficial o en conflicto no cuentan, y se informan aparte.

## Estado de la fuente de datos

**Importante:** hoy el registro de la caja no tiene compras de papel. En la serie `papel` el operador necesita una llave de Binance que pueda leer el libro. Sin llave, la serie `sin_llave` solo mide el modelo, y sus precios son estimados, no cotizaciones reales, así que este programa no los usa. El puente está listo; le falta la fuente. Ver «Lo que solo puede hacer el dueño».

## Archivos

| Archivo | Para qué |
|---|---|
| `puente_papel.py` | El puente. Lee el registro y escribe el CSV. |
| `prueba_puente.py` | 13 pruebas. Los valores esperados se calcularon a mano sobre un caso construido a propósito. |
| `ejemplo_registro_SINTETICO.jsonl` | Registro inventado con semilla fija, en el mismo formato. **No son apuestas reales.** |
| `ejemplo_apuestas_SINTETICO.csv` | El CSV que sale de ese registro. |

## Cómo se usa

1. Copie la carpeta `registro/` de la caja (en el plan está en `/data/local/tmp/operador/registro/`) a su PC, con el método que ya usa para la caja.
2. Desde la carpeta de este proyecto:

   ```
   python puente_papel.py ruta\a\registro
   python evaluador_ventaja.py apuestas_papel.csv
   ```

   Opciones: `--salida nombre.csv`, `--con-sombra` (las miradas en sombra salen como `sombra-5min` y `sombra-15min`), `--estricto` (si hay una línea que no se puede leer, no escribe nada).

3. Para probar sin datos reales:

   ```
   python puente_papel.py --ejemplo mi_prueba.jsonl
   python puente_papel.py mi_prueba.jsonl --salida mi_prueba.csv
   python prueba_puente.py
   ```

## Cómo se lee la salida del puente

- **Registro leído**: archivos y líneas. Las líneas que no se pueden leer se cuentan y se muestran con su número. Nunca se corrigen en silencio.
- **Compras de papel**: cuántas filas de compra hay, cuántas son en sombra y cuántos llenados extra de una misma ventana se descartaron.
- **Sin contar**: abiertas (aún sin resultado), sin ganador oficial y en conflicto. Si el número de abiertas es alto, el registro aún no está completo.
- **Precio medio pagado** por estrategia: compárelo con el precio supuesto del bloc (0,51) y con el equilibrio real. En el bloc, el precio medio real medido fue 0,544, lo que sube el equilibrio a 55,5 %.

## Salida de prueba (datos sintéticos, inventados)

```
Registro leído: 1 archivo(s), 719 línea(s); no se pudieron leer 0.
Compras de papel: 399 (en sombra: 73); llenados extra de una misma ventana, no cuentan: 79.
Apuestas resueltas que se exportan: 247.
Sin contar: abiertas 0 · sin ganador oficial 0 · resultado en conflicto 0.
Empates (cuentan como fallo): 8.
  papel-15min: 67 apuestas, 33 aciertos (49.3 %), precio medio pagado 0.533.
  papel-5min: 180 apuestas, 89 aciertos (49.4 %), precio medio pagado 0.539.
CSV escrito: ejemplo_apuestas_SINTETICO.csv
```

Y el evaluador sobre ese CSV (`python evaluador_ventaja.py ejemplo_apuestas_SINTETICO.csv`):

```
estrategia       n  acierto    intervalo 95 %  equilibrio  ganancia  cota inf.  veredicto             faltan (aprox.)
papel-15min     67   49,3 %     36,1 %–62,5 %      54,3 %    -9,3 %    -33,5 %  PRUEBA INSUFICIENTE   -
papel-5min     180   49,4 %     41,2 %–57,7 %      54,8 %    -9,8 %    -24,8 %  NO DEMOSTRADA         -
TODAS          247   49,4 %     42,3 %–56,5 %      54,7 %    -9,7 %    -22,6 %  NO DEMOSTRADA         -
```

Los datos son una moneda justa con precios de 0,50 a 0,58: el resultado correcto es «sin ventaja», y lo da. Son datos inventados; no dicen nada sobre binarias reales.

## Pruebas hechas

- `python -X utf8 prueba_puente.py` (Python 3.11): 12 de 13 pasan en esta carpeta. La número 13 (el evaluador lee el CSV) se omite aquí porque el evaluador está en la otra rama; al correrla en una copia con la estructura `propuestas/2026-11-17/` y `propuestas/2026-11-18/`, pasa: **13 de 13, OK**.
- Casos cubiertos: apuesta que gana, que pierde y que empata; dos llenados de una misma ventana; ventana abierta; ventana sin ganador oficial; medición en sombra; escape (no es compra); resultado de otra serie; resultado en conflicto; compra mal formada (precio 1,2, lado 0, precio booleano); línea que no es JSON; modo estricto; fecha en hora de Colombia (a las 00:00 UTC ya es el día anterior en Colombia); CSV con las cuatro columnas del evaluador.

## Qué quedó sin probar

- **Con un registro real de la caja.** No está en la nube y hoy no tiene compras de papel. Las pruebas usan filas escritas a mano según el código del operador, no un archivo generado por el operador en marcha.
- **Si el operador cambia el formato** de sus filas, el puente debe actualizarse. El esquema se tomó del código de `binarias/operador/operador.py` y `papel.py` en la rama `binarias/plan-v7-2026-11-04` (commit `7429f90`, 17/11/2026).
- **Independencia de las apuestas.** El intervalo de Wilson supone apuestas independientes. Las apuestas de una misma hora pueden estar correlacionadas, y el intervalo real sería más ancho.
- **Comisión.** El evaluador usa 2 % por defecto, la convención del bloc. No se verificó contra una liquidación real de Binance.
- **Empates.** El operador paga la mitad de la apuesta en empate. Este puente cuenta el empate como fallo, según el bloc, así que es más severo que el pago real. Para estimar el efecto contrario, cuente aparte los empates que informa el puente.
- **Fecha.** La fecha es el día de Colombia de la apertura de la ventana (`t`), no la de la compra. Si el registro se parte entre dos días, la estadística diaria del evaluador no se usa, así que no cambia el veredicto.

## Lo que solo puede hacer el dueño

1. **Llave de solo lectura para la caja.** Es lo que pone en marcha la serie de papel con libro real. Según el plan del operador, la serie de papel usa la llave solo para leer libros; sus compras son simuladas y no mueven dinero. El plan describe una llave de Lectura y Predicción, sin permiso de operar, restringida a la IP de la casa. Para el papel no hace falta mover fondos.
2. **Copiar el registro** de la caja a su PC y correr el puente y el evaluador.
3. **Decidir** si el veredicto del evaluador entra en el nodo o en el operador. Esos cambios van en sus carpetas, no aquí.

## Rama y entrega

- Rama `claude/proyectos-2026-11-18`, carpeta `propuestas/2026-11-18/`, desde `master`. Sin PR y sin unir.
- La rama `claude/proyectos-2026-11-17` ya existía con otra entrega de hoy, así que no se sobrescribió ni se usó el mismo nombre.
