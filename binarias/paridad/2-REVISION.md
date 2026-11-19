# Revisión · la rutina frente a la apuesta manual (18/11/2026, 15:35)

Hecha sobre el código del PC, que es idéntico al de la app Binarias del teléfono (huellas comprobadas el 18/11), sobre el registro real del teléfono leído por cable y sobre las instrucciones vigentes de la rutina aprobadora (`trig_01Ep7i969sChfFw4Mb3eN4qM`, leídas hoy a las 15:30). Nada se tocó durante la revisión. Los números de línea son los del código revisado, que quedó copiado en `respaldos/antes-paridad-18-11`; lo corregido después está en `5-PROMPT-CONSOLIDACION.md`.

## Lo que la revisión confirma primero

El libro que lee el operador es el mismo que muestra la app. En el mercado de 5 min de las 15:15, el operador anotó SUBE a 0,61 y BAJA a 0,40 a las 15:18:01, y SUBE a 0,41 y BAJA a 0,58 a las 15:19:01. Entre esas dos lecturas, sus fotos (15:18:43 a 15:18:50) muestran Up a 0,46–0,48 y Down a 0,58. La comisión también es la misma: «Ganar» de la app es 0,98 ÷ precio, igual que en el nodo, el papel y el ejecutor. El mercado de las fotos lo ganó BAJA; el papel del operador compró BAJA a 0,55 a las 15:19:16.

## Veredictos

R1, fórmula del pago: pasa en el teléfono y falla en la nube. Nodo (`nodo.py:100`), papel y ejecutor (`ejecutor.py:443`) usan 0,98 ÷ precio. El simulador de la rutina de proyectos (rama `claude/proyectos-2026-11-18-regla70`) usa un pago fijo de 0,85, que equivale a comprar siempre a 0,53. Consecuencia: sus cifras de dinero no son las de este mercado.

R2, precio de la cuenta: falla. A toda señal del Centro y del vigía el nodo le pone 0,544 (`nodo.py:101`, `nodo.py:239-241`), porque esas señales no traen precio. El punto de E1 de las 15:25 lo muestra: `"precio_supuesto": 25` de 25. En un mismo minuto un lado puede costar 0,05 o 0,95; con 0,544 fijo, la cuenta premia y castiga al azar.

R3, resultado de la cuenta: falla. El Centro mide 15 min desde su vela (entra 60 s tarde) y el nodo manda la señal al mercado de 15 min que la contiene (`nodo.py:244-252`). Solo una de cada tres señales cae en la apertura de un mercado; las otras dos caen en el minuto 5 o 10, donde el mercado se decide contra un precio inicial que la estrategia no miró. Ejemplo: E1 dio SUBE a las 15:25 («entra 15:26, vence 15:41»), pero lo que se compraría es el mercado de 15:15 a 15:30. Su «18 de 25» no es el acierto de lo que se compra.

R4, precio de ejecución: falla, y es lo que más dinero cuesta. Desde el 18/11 la orden de la IA se ejecuta «tal cual» (instrucciones vigentes de la rutina) a cualquier precio entre 0,01 y 0,90 (`ejecutor.py:390`). La decisión que deja el nodo no guarda el precio que la IA vio (`nodo.py:859-863`) y el ejecutor no lo compara. En el mercado de las fotos, SUBE pasó de 0,61 a 0,41 en un minuto: según hacia dónde se mueva, una orden pensada a uno de esos precios se llena al otro, y a 0,41 un acierto paga 2,39 por USDT, mientras que a 0,61 paga 1,61.

R5, demora y vigencia: falla. Entre la señal y la compra se suman 20 s de espera para juntar puntos (`nodo.py:72`), hasta 90 s por la mirada del operador (`nodo.py:73`), los 10 a 16 s de la rutina y lecturas de GitHub cada 10 s (`nodo.py:111`): entre unos 35 s y más de 2 min. La orden vale 10 min (`aprobacion.py:21`, `nodo.py:77`) y se reintenta cada 15 s (`ejecutor.py:52`): en un mercado de 5 min se puede comprar con la mitad del mercado ya jugada y otro precio. Usted, a mano, compra en un segundo al precio que ve.

R6, lo que ve la IA: pasa a medias. Cuando el operador ya miró ese mercado, el paquete trae precio, probabilidad y ganancia esperada de cada lado (`nodo.py:706-715`); no trae lo que paga por USDT y, si el operador no miró, llega sin precio. Las instrucciones vigentes le dicen que su orden «se ejecuta tal cual» y que «el operador ya no la vuelve a revisar»: nada la obliga a decidir por lo que paga. El `CONTEXTO.md` de main todavía dice «Usted decide el sentido; el operador, el precio y el importe», que dejó de ser cierto el 18/11.

R7, comisión y deslizamiento: pasa. Comisión de 2 % en la API y en la app; deslizamiento de 2 % en la API (`ejecutor.py:35`) contra 10 % «Automático» en la app: la API es más estricta, no más cara.

R8, red, hora y reinicios: falla leve. Hoy el registro del operador anota 11 rechazos −1021 (hora fuera de la ventana de 10 s): tres de madrugada al probar la llave y ocho entre las 12:07 y las 14:02. Nada reintenta en el acto: se espera la vuelta siguiente. Además, Android cerró la app a las 12:27, 13:05, 15:10 y 15:32 por «SwipeUpClean» (limpiar las apps recientes); en cada cierre el operador tarda unos 27 s en volver a mirar precios. Lo primero se corrige en el código; lo segundo, bloqueando la app en Recientes.

R9, regla de armado: informa. `_armar_solo` (`operador.py:703-730`) arma con 18 de 25 de la medida propia del Centro, sin precio ni resultado del mercado. Por sí sola no compra (toda compra pasa por la IA), pero el simulador de la nube muestra que, sin ventaja, se cumple por azar en el 99 % de los periodos de 30 días.

R10, mensajes: falla leve. En el teléfono, el aviso de arranque dice «Operador en marcha en la caja» (`operador.py:326`).

## Respuesta a su pregunta

Las dos deberían dar lo mismo, y la causa de que no lo hagan está en cuatro puntos, de mayor a menor peso en dinero.

1. La rutina compra a un precio que usted no aceptaría: sin tope, hasta 0,90 y hasta 10 min después de decidir (R4 y R5).
2. Decide con información de hace 40 s o más, cuando en los últimos minutos el precio de un lado cambia 0,10 o 0,20 por minuto (R5).
3. Elige qué estrategias van a la IA con una cuenta que no es dinero: un precio supuesto de 0,544 y un acierto que no es el del mercado donde se compra (R2 y R3).
4. La rutina de la nube mide con un pago fijo de 0,85 (R1).

Una aclaración evita un error de lectura: el «Ganar +2,13» de la app es lo que paga si acierta, no lo que se gana en promedio. Up a 0,46 paga más porque el mercado le da menos probabilidad de acertar. Si el precio es justo, Up a 0,46 y Down a 0,58 tienen el mismo promedio: −2 % por la comisión. Solo se gana comprando cuando la probabilidad real supera el equilibrio, que es precio ÷ 0,98. Eso vale igual para usted y para la rutina, siempre que la rutina compre al mismo precio y en el mismo momento.
