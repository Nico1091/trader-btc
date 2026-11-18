# Análisis · cuánto dinero separa a la rutina de la apuesta manual (18/11/2026, 15:45)

Datos del teléfono hasta las 15:37, leídos por cable: 426 mercados, 422 ganadores, 1.608 señales guardadas y libro real de las 11:06 a las 15:37. Salida completa en `resultados/analisis-18-11.txt`; se repite con `python -I analisis_paridad.py <carpeta>`. Los umbrales son los de `3-PLAN-ANALISIS.md`, sin cambios.

## A1. La cuenta del nodo no es la cuenta de su bolsillo (criterio cumplido: no sirve para decidir)

Con libro real hay 10 señales del Centro y del vigía con ganador oficial. En la muestra ampliada con precio estimado (ver A3) hay 44. Se toma el minuto de entrada y, si esa mirada se perdió, el siguiente, como hace ahora el nodo. En las dos muestras, el resultado propio de cada estrategia coincide con el del mercado en las señales alineadas, pero solo en el 86 % de las que caen a mitad de ventana. Lo que de verdad separa las dos cuentas es el precio. Las estrategias compran el lado barato en el 73 % de las señales, con un precio medio de 0,27, y la cuenta del nodo les pone 0,544 a todas.

El signo se invierte justo donde importa. E1, con libro real: el nodo cuenta −0,40 por USDT y a mano habrían sido +2,54. E3, en la muestra ampliada: −2,20 frente a +1,11. E5: −0,19 frente a +2,20. En el total, las dos cuentas pierden (−20,58 y −16,46 en 44 señales), y el acierto en el mercado es 20 %, no el 30 % de la cuenta propia. Dicho de otro modo, el nodo hoy puede mandar a la IA una estrategia que a mano pierde y callar una que a mano gana.

## A2. Un minuto de demora cuesta dinero (criterio cumplido: hace falta tope de precio)

En el mercado de 5 min, de un minuto al siguiente, el lado que termina ganando sube en promedio 0,085 y el que pierde baja 0,084. El cambio medio de un lado es 0,151, y en el 63 % de los minutos pasa de 0,10. En el de 15 min, el ganador sube 0,027 por minuto: 0,043 cuando faltan de 3 a 5 min y 0,135 en los dos últimos. Comprar un minuto tarde el lado que gana deja, por cada USDT, 0,27 menos de pago en el mercado de 5 min y 0,05 menos en el de 15.

El costo crece con el acierto. A 55 %, la demora cuesta en promedio unos 0,01 de precio por minuto en el mercado de 5 min. Al 76 % que usted exige, cuesta unos 0,04. Usted, a mano, compra en un segundo al precio que ve. La rutina tarda entre 35 s y más de 2 min, y hoy compraría al precio que haya, sin tope.

## A3. El modelo del operador estima bien el precio (criterio cumplido: se amplió la muestra)

En 828 lados con libro real, el precio de compra se aparta de la probabilidad del modelo en +0,006 de media, con un error medio absoluto de 0,033, por debajo del límite de 0,05. Por eso la muestra se amplió a las horas sin libro, marcada como estimada. Ese precio estimado sirve para el análisis, no para decidir con dinero.

## A4. El papel de Fable, que sí compra con precio, pierde con precio real

En el mercado de 5 min hizo 27 compras de papel, a un precio medio de 0,15, con 5 aciertos y un neto de −12,9 por USDT. En el de 15 min hizo 11 compras con un neto de −1,0. Compra el lado muy barato y casi nunca acierta. Sus puntos no llegan a la IA (1 de 12 y 1 de 5).

## A5. El equilibrio real no es 54,05 %

El precio de entrada de las señales del Centro con libro real tiene una mediana de 0,56 y va de 0,03 a 0,71. En la mediana, no perder exige acertar el 57,1 %, no el 54,05 % fijo que supuso la rutina de la nube. Cada señal tiene su propio equilibrio: precio ÷ 0,98.

## Conclusión

Las dos formas de apostar dan lo mismo solo si la rutina compra al mismo precio, en el mismo momento y mide su historia igual que usted. Hoy no se cumple ninguna de las tres cosas. La corrección es obligatoria y se aplica así.

1. La IA ve cuánto paga cada lado, igual que el «Ganar» de la app.
2. Su orden solo se compra al precio que vio, o hasta 0,02 más, y vale 2 min en vez de 10.
3. La cuenta de cada estrategia en el nodo se lleva como la llevaría usted: el precio real del libro en el minuto de entrada y el ganador oficial.
4. La demora baja de unos 35 s a unos 25 s.

Con libro real, ninguna fuente muestra todavía ganancia; la muestra es de cuatro horas y media. Con la cuenta corregida no llegará nada a la IA hasta que una estrategia sume 25 señales con precio real, 19 aciertos en el mercado y neto positivo. Eso es lo que usted exigiría antes de apostar a mano.
