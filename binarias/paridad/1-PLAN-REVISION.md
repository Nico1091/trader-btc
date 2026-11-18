# Plan de revisión · la rutina frente a la apuesta manual (18/11/2026)

## La pregunta

Una compra hecha a mano en la app y una compra hecha por la rutina, en el mismo mercado «BTC Up or Down», en el mismo momento y por el mismo lado, deben pagar exactamente lo mismo: si aciertan, 0,98 ÷ precio por cada USDT; si fallan, nada. Así lo confirman las tres fotos de las 15:18 (Up a 0,46 paga 2,13; Up a 0,48 paga 2,04; Down a 0,58 paga 1,69). Esta revisión busca cada punto del sistema en que la rutina cuenta, elige o paga algo distinto de lo que usted obtendría con el botón.

## Criterios, fijados antes de mirar resultados

R1. Fórmula del pago. Pasa si el nodo, el papel, el ejecutor y la rutina de la nube usan 0,98 ÷ precio. Falla cualquier pago fijo.

R2. Precio con que se lleva la cuenta de cada estrategia. Pasa si es el precio real del libro en el momento de la señal. Falla si es un precio supuesto.

R3. Resultado con que se lleva la cuenta. Pasa si es el ganador oficial del mercado donde se compraría. Falla si es una medida propia de la estrategia que no coincide con ese mercado.

R4. Precio de ejecución de una orden de la IA. Pasa si nunca se paga más que el precio que la IA vio, con una tolerancia pequeña. Falla si se compra a cualquier precio.

R5. Demora y vigencia. Pasa si entre la señal y la compra pasa menos de un minuto y la orden no vale más allá de lo que tarda el precio en cambiar. Falla si la orden puede ejecutarse minutos después.

R6. Lo que ve la IA. Pasa si recibe, de los dos lados, el precio y lo que paga por USDT. Falla si puede ordenar sin precio.

R7. Comisión y deslizamiento. Pasa si la comisión es la de la app (2 %) y el deslizamiento de la API no es peor que el de la app.

R8. Fallas de red y de hora (−1021) y reinicios. Pasa si no hacen perder ni retrasar una orden válida.

R9. Regla de armado (18 de 25). Se informa si mide dinero o solo aciertos; la decisión de cambiarla es suya.

R10. Mensajes. Pasa si cada aviso dice el equipo y la cifra verdaderos.

## Cómo se comprueba

Cada punto se contesta con la línea de código que lo decide, con el registro real del teléfono (la app Binarias, leída por cable y sin tocar nada) o con las instrucciones vigentes de la rutina. El resultado queda en `2-REVISION.md`: veredicto, evidencia y consecuencia en dinero.
