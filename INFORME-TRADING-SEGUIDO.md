# Trading seguido de BTC: informe del 20 de octubre de 2026

## Lo que usted pidió

Operar BTC/USD de forma seguida: un ciclo tras otro, de segundos a minutos, con el agente leyendo el mercado en segundos, minutos, horas y días, una probabilidad por ciclo y pausas de seguridad por tandas de 100 a 800 ciclos, primero en prueba. El diseño del 19 de octubre operaba por días (velas de 5 minutos a 1 hora y posiciones de hasta dos días), así que se rehízo desde la base.

## Lo que quedó funcionando (comprobado en su equipo)

El agente opera en papel desde las 20:22 del 20 de octubre, sin ventana, con las velas de 1 segundo de Binance en tiempo real por conexión directa, tal como usted lo autorizó para Binance. Lo de fuera de Binance va por Tor: calendario macro de EE. UU., agenda de Trump, miedo y codicia, un índice del dólar sintético e interés abierto de Bybit, OKX y Deribit. Lleva cuatro libros en papel de 9,7 USDT cada uno: contado BTCUSDT, BTC/FDUSD con órdenes de creador, futuros BTCUSDT y un testigo que opera seguido sin ningún filtro. Gasta el 0,55 % de un núcleo y 41 MB de memoria, y va 1 a 2 segundos detrás del mercado. No tiene ningún camino de órdenes: nada sale de su dinero.

Cada segundo calcula 31 rasgos, que incluyen sus estrategias de junio (retroceso en tendencia, techo extremo, barridos con agresión vendedora), y dos probabilidades: que el precio se mueva hasta la barrera y que ese movimiento sea hacia arriba. Solo entra si la ganancia esperada, descontadas las comisiones, es positiva. Aplica su Trading Plan (3 % por operación, 15 % diario, 20 % semanal), pausa de 15 minutos tras cinco pérdidas seguidas, tanda de 100 ciclos con pausa de revisión de 30 minutos y detención si una tanda pierde más del 10 %, y no abre ciclos alrededor de datos fuertes de EE. UU. ni de discursos de Trump.

Lo que opera en vivo es exactamente lo que se probó: en cuatro repeticiones sobre tres días distintos, el código real del agente y el banco de pruebas dieron 587 ciclos idénticos en hora, lado, precios, motivo y cantidad, y las velas de 1 minuto que arma el agente coincidieron con las de Binance en los 3.236 minutos revisados.

## Lo que dicen los datos (medido en laboratorio)

Se usaron 14,86 millones de segundos de BTCUSDT y BTC/FDUSD, de mayo al 19 de octubre, verificados uno a uno con su suma SHA-256 y sin huecos. La probabilidad se entrenó con mayo a julio, se ajustó con agosto y la primera mitad de septiembre, y el tramo final (16 de septiembre al 19 de octubre) se miró una sola vez.

La dirección del precio a segundos y minutos resultó casi imposible de anticipar: la probabilidad de que suba ordena los casos apenas mejor que una moneda (AUC de 0,51 a 0,56, donde 0,50 es azar) y nunca llegó al 85 % que usted mencionó; su máximo en el tramo final fue 0,80. Lo que sí se anticipa bien es cuándo habrá movimiento (AUC de 0,74 a 0,77), pero eso no dice hacia dónde.

Operar seguido sin filtro pierde en los tres instrumentos, y la causa es la comisión: cuesta entre 0,04 % y 0,20 % por ciclo, mientras BTC, con una volatilidad diaria de 0,94 % en estos meses, se mueve de 0,05 % a 0,14 % en 5 a 30 minutos.

| Tramo final (34 días) | Operando seguido, sin filtro | Con la regla de seguridad |
|---|---|---|
| Contado BTCUSDT | −17,1 % en 100 ciclos (la tanda lo detuvo) | 0 ciclos |
| BTC/FDUSD de creador | −39,2 % en 600 ciclos | 4 ciclos, +1,2 % |
| Futuros BTCUSDT | −21,2 % en 33 ciclos (frenos diario y semanal) | 5 ciclos, +1,4 % |
| Testigo (contado, ciclos de 5 min) | −16,9 % en 100 ciclos | — |

Cien entradas al azar en contado perdieron casi lo mismo que operar siempre (−16,1 %): operando seguido, el modelo no aporta nada frente al azar. Con la regla de seguridad el agente casi no entra, y 4 o 5 ciclos en un mes no prueban ninguna ventaja. Solo BTC/FDUSD superó la validación, y por muy poco (30 ciclos, +1,0 %). Contado y futuros quedan marcados en el panel como «sin ventaja demostrada».

Hay además dos límites de su capital de 9,7 USDT. En contado, la comisión de compra se cobra en BTC y deja polvo de casi un paso entero (unos 0,82 USDT) que se arrastra a la venta siguiente. En futuros, la orden mínima es 0,001 BTC (unos 83 USDT); con su tope del 3 % solo caben stops de hasta un 0,27 %, así que cuando la volatilidad agranda la barrera, o tras unas pérdidas, la entrada no cabe (en la prueba final se omitieron así 128.078 segundos).

## Lo que falta probar

- Órdenes de verdad en la red de pruebas de Binance: falta la clave nueva en `claves-testnet.env`.
- Los frenos de contexto en un día con datos fuertes de EE. UU. (esta semana no hay ninguno de impacto alto).
- El reinicio tras más de 6 horas con el equipo apagado. El relleno de huecos cortos ya funcionó en vivo, en cada arranque.
- El arranque automático al encender el equipo, que no está puesto.

## Decisiones suyas

1. ¿Pongo el agente a arrancar solo al encender el equipo? Hoy solo corre mientras no se apague o reinicie.
2. ¿Sigue el agente midiendo en papel durante unas tandas? Lo que se vea en vivo confirmará o desmentirá lo medido.
3. La única estrategia con ventaja medida es su MEZCLA de 1 hora (junio: +248 % en 24 meses de prueba histórica, con cortos en futuros). Opera varias veces por semana, no seguido. ¿La sumo a este mismo agente como libro aparte, en papel?

## Cómo se usa

- Panel: `panel.html` en esta carpeta; se abre con el Buscador y se actualiza cada 5 segundos.
- Arrancar: `ARRANCAR AGENTE.cmd`. Parar: `PARAR AGENTE.cmd` (cierra lo abierto en papel y guarda el estado).
- No abrir ciclos nuevos: crear un archivo llamado `PAUSA`. Quitar la detención de una tanda: crear `REANUDAR`.
- Diario: carpeta `diario` (ciclos por libro, eventos, resumen por minuto y velas de 1 s grabadas).
- Rehacer el banco de pruebas: `python -u -I banco_rapido.py`. Repetir la paridad: `python -u -I pruebas/paridad_motor.py`.
