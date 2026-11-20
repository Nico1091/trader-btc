# Verificador de cierres de las binarias · propuesta del 20/11/2026

## Qué es

Un programa que responde a una pregunta concreta: **¿el ganador que calcula el operador con velas de contado coincide con el ganador oficial de Binance en las mismas ventanas?**

El operador liquida algunas compras de papel con una regla propia sobre velas (apertura del primer minuto contra cierre del último; `_ganador_velas` en `papel.py`). Las cifras de acierto de «56 % a 59 %» del bloc salen de esas velas y de un precio supuesto. Si la regla de velas no coincide con el ganador oficial, esas cifras no miden lo que dicen, y ninguna decisión que se tome con ellas (armar, comprar, el Centro) tiene base. Este programa mide esa coincidencia.

Usa solo la biblioteca estándar de Python (3.8 o superior). Las velas son públicas: no necesita llaves. No escribe en el registro, no se conecta a la caja ni al teléfono, no envía órdenes y no toca `binarias/operador/` ni `binarias/aprobador/`.

## Por qué esta y no otra

Las propuestas anteriores miden si una ventaja es real, cuánta muestra hace falta o si el operador cumple sus reglas de dinero. Todas suponen que los ganadores del registro son correctos. Esta comprueba esa suposición, que es la base de todas las demás cifras. Es la única que puede invalidar lo que ya se ha medido sin que nadie lo note.

## Criterio (fijado antes de ver ningún registro real)

Constantes en `verificar_cierres.py`:

- Mínimo de 200 ventanas oficiales con velas para dar veredicto. Menos: «muestra insuficiente».
- Si el límite superior al 95 % de la discordancia es **2 % o menos**: «las velas sirven».
- Si el límite inferior al 95 % es **5 % o más**: «las velas no sirven».
- Entre ambos: «indeciso».

Discordancia = ventanas en que el ganador de velas no es el oficial, sobre las ventanas comparadas. Intervalo de Wilson al 95 %.

## Archivos

| Archivo | Para qué |
|---|---|
| `verificar_cierres.py` | El verificador. Se usa desde la línea de comandos. |
| `prueba_verificar_cierres.py` | 27 pruebas automáticas. Con `--generar` escribe el registro de ejemplo. |
| `velas_BTCUSDT_1m_2026-11-18.csv` | **Velas reales y públicas** de BTCUSDT, 1.440 minutos del 18/11/2026 (UTC), bajadas de `data-api.binance.vision`. |
| `ejemplo_registro_SINTETICO.jsonl` | Registro **inventado**: 384 ventanas sobre las velas reales, con 40 ganadores oficiales dados la vuelta a propósito. Sirve para ver que el programa las cuenta. |
| `salida_ejemplo.txt`, `salida_ejemplo.json` | Salida real de ejecutar el verificador sobre ese ejemplo. |

## Cómo se usa

1. Copie a un lugar con Python el registro de papel del operador: `registro/AAAAMMDD.jsonl`. Contiene las filas de cada mirada, llenado y resultado. **No lo suba a GitHub**: es su registro operativo.

2. Ejecute con velas guardadas o bajándolas:

   ```
   python verificar_cierres.py --registro registro/ --velas velas.csv
   python verificar_cierres.py --registro registro/ --descargar 2026-11-17 2026-11-19 --guardar velas.csv
   python verificar_cierres.py --registro registro/ --velas velas.csv --json resultado.json
   ```

   `--descargar` usa días UTC: incluye el primero y excluye el segundo.

3. Códigos de salida: `0` las velas sirven · `1` no sirven, indeciso o muestra insuficiente · `2` error de uso.

Filas que el programa lee del registro: `tipo: "resultado"` con `serie`, `fuente` (`oficial` o `velas`), `W` (5 o 15), `t` (inicio de la ventana en segundos Unix) y `ganador` (1, -1, 0 o nulo). Las demás filas se ignoran. Las filas malas se cuentan y se muestran; no se descartan en silencio. Una ventana con dos ganadores distintos en el registro se deja fuera y se cuenta como conflicto. Una ventana cuyo inicio no cae en múltiplo de su duración se cuenta como desalineada y no se compara.

## Lo que se probó

- **27 pruebas, todas bien** (`python3 prueba_verificar_cierres.py`): la regla de velas (sube, baja, empate, minuto que falta), el intervalo de Wilson (0 de 100 da 0 a 3,70 %), la lectura del registro con filas malas y conflictos, la paginación de la descarga, el día completo (288 ventanas de 5 min y 96 de 15), 40 discordancias inyectadas que el programa cuenta exactas, los tres veredictos y los códigos de salida.
- **Descarga en vivo**: el día 18/11 bajó completo (1.440 minutos, sin huecos) y el CSV que salió es idéntico al archivo incluido.
- **Línea de comandos**: la salida de `salida_ejemplo.txt` se generó ejecutando el programa tal cual.
- **Dato real del 18/11 con la regla de velas** (no es un veredicto, solo lo que sale del día):
  - 5 minutos: 288 ventanas, 133 suben, 155 bajan, 0 empates.
  - 15 minutos: 96 ventanas, 37 suben, 59 bajan, 0 empates.
  - El día cerró a la baja (de unos 64.947 a unos 62.348 USDT). Un solo día no dice nada del sesgo de la regla.

## Lo que quedó sin probar

- **No se comparó con ningún ganador oficial real.** Aquí no hay registro de la caja ni ganadores de Binance para esas ventanas. El 10,4 % de discordancia del ejemplo (40 de 384) es inventado; el programa solo demuestra que cuenta bien.
- **La regla de velas es una copia.** Se transcribió de `papel.py` tal como estaba en la rama `binarias/plan-v7-2026-11-04` a 20/11/2026. Si el operador cambia, este programa debe cambiar con él.
- **El formato del registro se supone** a partir de `papel.py` y de la propuesta del 18/11 (`puente_papel.py`). No se ha visto un registro real de la caja.
- **La regla oficial de Binance no se conoce.** Si el precio de referencia de Binance es distinto de las velas de contado (otro instante, otra fuente), la discordancia será real y este programa la medirá, pero no dirá cuál de las dos reglas es la correcta.
- **Las filas oficiales dependen de la llave.** El operador solo escribe `fuente: oficial` cuando puede leer el resultado. Si el registro no tiene esas filas, el veredicto será «muestra insuficiente» y no es un fallo del programa.
- **No corrige nada.** Si el veredicto es «no sirven», el siguiente paso es volver a medir las series de velas con ganadores oficiales, no ajustar las cifras ya escritas.

## Lo que solo puede hacer el dueño

1. Copiar a un PC el registro de papel de la caja (`/data/local/tmp/operador/registro/` o la copia del bloc) y ejecutar:
   `python verificar_cierres.py --registro <carpeta del registro> --descargar AAAA-MM-DD AAAA-MM-DD`
   con los días en que la caja tuvo la llave que lee resultados.
2. Leer el veredicto. Si dice «las velas no sirven» o «indeciso», las cifras de acierto medidas con velas no deben usarse para armar ni para comprar hasta que se vuelvan a medir con ganadores oficiales.
3. Decidir si se lleva este verificador a la caja. Este paquete no se ha instalado en ningún equipo ni en la app.
