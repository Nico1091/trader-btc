# Retroalimentación exacta de la vigilante · binarias · 20/11/2026

Pedido del dueño (20/11/2026, tarde): «revise la parte de la gente que teníamos de binarias y revise toda la retroalimentación. Pídale que haga una retroalimentación exacta de todo lo que vio… la gente dice que cambiemos la estrategia, que ya no utilicemos esta de acierto, sino otra cosa que sea por ganancia de dinero».

## Quién vigila y qué puede ver

La vigilante es la rutina de la nube «Proyectos: analizar y sacar lo siguiente» (`trig_014mdzixXBLj5jRUvKJ5Csb7`, Claude Haiku 5.5, encendida). Corre a las 00:00, 05:00, 10:00 y 15:00 de Colombia, lee el repositorio `Nico1091/trader-btc` (rama `binarias/plan-v7-2026-11-04`), entrega cada pasada en una rama `claude/proyectos-…` y le escribe al Telegram con «[Proyectos]». No ve el teléfono ni el PC: hasta hoy trabajó con el código, el bloc y datos sintéticos.

El 20/11 a las 16:57 se le lanzó una pasada con el pedido del dueño y los datos reales del teléfono (archivo `0-PEDIDO-A-LA-VIGILANTE.txt`). La plataforma entrega ese texto como «datos, no instrucciones», y la vigilante lo dijo así: «esa instrucción no está en el encargo permanente de la rutina, así que la trato como dato». Aun así usó los datos y entregó justo lo que el dueño buscaba: el medidor de ganancia (entrega 10). Para que en adelante obedezca un «PEDIDO DEL DUEÑO» hay que añadir una cláusula a su instrucción; el control de permisos de Claude Code lo negó en modo automático («Undermining Oversight»), así que queda para que el dueño lo apruebe o lo haga él en claude.ai (texto exacto en `respaldos\rutina-proyectos-antes-20-11.json` y en el informe de esta sesión).

## Lo que vio, entrega por entrega

1. **17/11 · evaluador de ventaja** (`claude/proyectos-2026-11-17`). La compuerta del nodo «19 de 25 con ganancias» no tiene intervalo de confianza ni corrección por estrategias: a precio 0,544 (equilibrio 55,5 %), la cota inferior de 19 de 25 es 56,6 % con una sola mirada y 50,2 % corregida por cinco estrategias. Con las cifras del bloc, ninguna estrategia tiene ventaja demostrada (E1 69 de 121, cota inferior 45,4 % frente a 52,0 %). Propuso que solo se compre con «VENTAJA DEMOSTRADA». Sigue vigente.
2. **18/11 · vigilancia por periodos** (`-17-b`). La ventaja se gasta con los años (la regla base pasó de 60,3 % en 2020 a 55,5 % en 2026) y las estrategias salieron de cientos de variantes: un promedio global no lo detecta. Vigente como advertencia.
3. **17/11 · verificador de cifras** (`-17-c`). Sobre las pruebas a ciegas del repositorio, entrar 60 s tarde quita unos 2 puntos; el precio máximo de compra con ventaja ronda 0,54 a 0,57 en BTC (Contratos de 10 min). Esas cifras son de velas y pago supuesto, no del mercado que hoy se compra.
4. **17/11 · simulador del dinero real con sus reglas** (`-17-d`). Sin ventaja, cada orden de 2 USDT pierde unos 4 céntimos y el freno del día no limita el mes: a precio 0,544, el 5 % de los meses pierde 6,40 USDT o más (31 % del saldo). Con acierto cerca del precio, la regla de armado se activa casi siempre.
5. **18/11 · puente del papel** (`-18`). Convierte el registro del operador en apuestas con precio real (`q`) para medirlas; cuenta solo compras de papel y ganadores oficiales.
6. **18/11 · simulador de la regla del 70 %** (`-18-regla70`). Con cinco estrategias, la regla «18 de 25» arma dinero real por azar en el 99,3 % de los periodos de 30 días (en mediana al sexto día) y en el 100 % cuando el acierto está en el equilibrio. `_armar_solo` (operador.py, líneas 705 a 732) calcula la aptitud del papel y no la exige, al contrario del armado manual. Vigente.
7. **19/11 · prueba secuencial de Wald** (`-19`). Mirar cada minuto infla el error: sin ventaja, la regla actual arma en el 100 % de las réplicas; una prueba secuencial con alfa 0,05 repartido entre cinco estrategias arma en el 0,2 %. Con 3 puntos de ventaja real hacen falta unas 800 apuestas por estrategia para decidir. Vigente.
8. **19/11 · auditor de reglas de dinero** (`-19-b`). Comprueba orden por orden los topes (R1 a R12). Hoy no hay órdenes reales que auditar.
9. **20/11 · conciliador, verificador de la llave y verificador de cierres** (`-17-e`, `-17-f`, `-20`). Cruza el registro con el extracto de Binance; revisa las banderas de la llave; y advierte que las cifras de «56 % a 59 %» salen de velas y de un precio supuesto, no del ganador oficial. Al hacer la segunda notó que el repositorio es **público** y quitó la IP de la casa de sus propios archivos.
10. **20/11, 17:00 · medidor de ganancia** (`claude/proyectos-2026-11-20-ganancia`). Es la recomendación que el dueño citó. Textual: «Sustituir el armado "18 de 25" y la compuerta "19 de 25 con ganancia" por la decisión GANA DINERO (demostrado) de este medidor, calculada sobre apuestas reales resueltas. Mientras ninguna estrategia tenga esa decisión, el operador no arma». Su criterio, fijado antes de ver datos reales:
   - por apuesta, r = 0,98 / precio − 1 si acierta y −1 si falla; se mide la media de r;
   - 100 apuestas como mínimo;
   - límite inferior normal y bootstrap (2.000 remuestras, semilla 20261120), unilaterales, con alfa 0,05 dividido entre las estrategias;
   - «GANA DINERO (demostrado)» si los dos límites inferiores quedan por encima de 0; «PIERDE DINERO (demostrado)» si los dos superiores quedan por debajo; si no, «NO DEMOSTRADO»; con menos de 100, «MUESTRA INSUFICIENTE».
   Su ejemplo muestra el porqué: una estrategia con 74 % de acierto comprando a 0,80 pierde dinero (equilibrio 81,6 %), y una con 25 % comprando a 0,20 lo gana.

En resumen, la vigilante pide cinco cosas: decidir por dinero y no por acierto; exigir prueba estadística con corrección por estrategias; no inflar el error mirando cada minuto; usar solo ganadores oficiales y precios reales; y no armar mientras nada lo demuestre.

## Lo que dicen los datos reales del teléfono (medido hoy, 16:55)

Cuenta a mano del nodo (cada señal comprada en el mercado de 15 min donde cae, al precio real del libro en el minuto de entrada y con el ganador oficial; 1 USDT por señal), del 18/11 11:15 al 20/11 16:35. Papel del operador de Fable con precio real y ganador oficial, mismo periodo.

| Fuente | Apuestas | Aciertos | Neto (USDT por 1 USDT) | Por apuesta | Precio medio | Medidor de la vigilante |
|---|---:|---:|---:|---:|---:|---|
| E1 · ruptura de 20 velas al revés | 41 | 22,0 % | −8,64 | −21 % | 0,198 | muestra insuficiente |
| E2 · ruptura de 50 velas al revés | 19 | 10,5 % | −12,22 | −64 % | 0,217 | muestra insuficiente |
| E5 · rechazo en techo o piso | 37 | 37,8 % | −9,20 | −25 % | 0,380 | muestra insuficiente |
| Vigía de 15 min | 18 | 55,6 % | 0,00 | 0 % | 0,516 | muestra insuficiente |
| E3 · Gemini 1 al revés | 4 | 75,0 % | +1,02 | +26 % | 0,605 | muestra insuficiente |
| E4 · Gemini 3 al revés | 2 | 50,0 % | +0,04 | +2 % | 0,530 | muestra insuficiente |
| Operador, papel de 5 min | 116 | 17,2 % | −21,13 | −18 % | 0,191 | no demostrado |
| Operador, papel de 15 min | 34 | 14,7 % | −13,09 | −39 % | 0,233 | muestra insuficiente |

Con el medidor de la vigilante sobre estos 271 registros: «ninguna estrategia demuestra ganancia de dinero». En total, −63,2 USDT por cada USDT apostado en 271 apuestas (−23 %).

Tres hechos explican las pérdidas:
- **La señal no es el mercado.** El Centro mide su acierto contra su propio precio de entrada; el mercado paga según el precio de apertura de la ventana. E1 acierta 57,5 % en 736 señales por su medida propia, pero comprada en el mercado acierta 22 %.
- **Se compra el lado barato.** E1, E2 y el operador pagan en promedio 0,19 a 0,22: lados que el mercado ya da por perdidos. El modelo del operador esperaba +34 % de ganancia prudente y perdió 18 %.
- **El mercado está bien calibrado.** En el de 5 min (633 ventanas), cada tramo de precio gana más o menos lo que cuesta y todos pierden entre 1 % y 3 % por la comisión y el diferencial (los dos precios suman 1,010). Los lados de menos de 0,10 pierden entre 15 % y 17 %. El de 15 min tiene solo 210 ventanas y no prueba nada todavía.

## Estado del dinero

El operador nunca se armó, no hay ninguna orden real (no existe `ordenes.json`) y los 20,50 USDT siguen en la billetera de predicción. La IA no ha recibido ningún punto desde el 18/11: ninguna fuente llegó a 19 de 25 con neto positivo. La regla del 70 % sigue puesta y, según la vigilante, armaría por azar casi seguro en un mes.

## Veredicto

La vigilante tiene razón y los datos reales la confirman: el acierto no dice nada del dinero cuando el precio cambia, y hoy ninguna fuente gana dinero al precio real. Se cambia la estrategia a ganancia de dinero demostrada: mientras nada lo demuestre, no se arma ni se consulta a la IA, y el dueño ve en sus avisos dinero en vez de aciertos.
