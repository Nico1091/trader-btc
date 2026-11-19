# Plan de análisis · cuánto dinero separa a la rutina de la apuesta manual (18/11/2026)

## Datos

Del teléfono, leídos por cable sin tocar nada: los registros del operador del 17 y el 18/11 (miradas de cada minuto con el libro real de los dos lados desde las 11:06 del 18/11, y sin libro, con la probabilidad del modelo, antes de esa hora), los ganadores oficiales de cada mercado, las compras de papel, las señales del Centro (E1 a E5) y las del vigía de 15 min. El guion es `analisis_paridad.py`; repite todo con `python -I analisis_paridad.py <carpeta de datos>`.

La muestra con libro real es corta: unas cuatro horas y media. Lo que salga de ella mide mecanismos, no la ventaja de largo plazo de ninguna estrategia.

## Medidas y criterios, fijados antes de calcular

A1. Cuenta del nodo frente a cuenta manual, señal por señal. Para cada señal del Centro y del vigía con libro real se calculan dos netos por USDT: el que usa hoy el nodo (0,544 y el resultado propio de la estrategia) y el que tendría usted comprando a mano ese lado, en ese mercado, al precio real del minuto de entrada y con el ganador oficial. También se cuenta en cuántas señales coincide el resultado propio con el del mercado y cuántas compran el lado barato (precio menor de 0,50). Criterio: si los dos netos difieren en signo o en más de 0,30 por USDT de promedio por señal, la cuenta actual no sirve para decidir con dinero.

A2. Costo de la demora. En cada mercado con libro se compara el precio de un lado con el del minuto siguiente, separando el lado que terminó ganando del que perdió, y por minutos que faltan. Criterio: si el lado ganador sube en promedio más de 0,02 por minuto, una orden que llega un minuto tarde cuesta dinero aunque la idea sea buena, y la compra necesita un tope de precio.

A3. Precio estimado para ampliar la muestra. Se mide la diferencia entre el precio real de compra y la probabilidad del modelo del operador en las miradas con libro. Criterio: si el error medio absoluto queda en 0,05 o menos, se estima el precio de las horas sin libro como probabilidad más esa diferencia y se repite A1 en la muestra larga, marcada como estimada; si pasa de 0,05, no se amplía.

A4. Papel del operador. Neto real de sus compras de papel con llenado a 5 s y a 15 s, con el ganador oficial. Sirve para ver si el operador, que sí compra con precio, gana con precio real.

A5. Equilibrio real. Distribución del precio de entrada de las señales del Centro y del acierto mínimo que exige (precio ÷ 0,98), frente al 54,05 % que supuso la rutina de la nube.

## Qué decide el análisis

Si A1 y A2 cumplen su criterio de falla, la corrección de la aplicación es obligatoria y tiene tres partes: la IA ve lo que paga cada lado; su orden solo se compra al precio que vio, con una tolerancia de 0,02; y la cuenta de cada estrategia en el nodo se lleva como la llevaría usted, con el precio real y el ganador oficial. Lo que no se cumpla queda dicho en `4-ANALISIS.md` sin ajustar los umbrales después de ver los resultados.
