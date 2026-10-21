# Trading seguido de BTC: informe del 20 de octubre de 2026

## Lo que usted pidió

Operar BTC/USD de forma seguida: un ciclo tras otro, de segundos a minutos, con el agente leyendo el mercado en segundos, minutos, horas y días, una probabilidad por ciclo y pausas de seguridad por tandas de 100 a 800 ciclos, primero en prueba. El diseño del 19 de octubre operaba por días (velas de 5 minutos a 1 hora y posiciones de hasta dos días), así que se rehízo desde la base.

## Lo que quedó funcionando (comprobado en su equipo)

Por su orden de las 20:40, el agente prueba como si empezara con 40.000 pesos colombianos y queda moviéndose hasta que usted diga. Esos pesos equivalen a 12,59 USDT con la tasa real de Binance P2P (3.177,85 COP por USDT, mediana de 20 avisos de compra con Nequi, Bancolombia, Daviplata y otros), y cada libro arranca con esa cantidad; el panel muestra también el valor en pesos. Corre desde las 21:05 del 20 de octubre, sin ventana, y arranca solo al encender Windows.

Usa las velas de 1 segundo de Binance en tiempo real por conexión directa, tal como usted lo autorizó para Binance. Lo de fuera de Binance va por Tor: calendario macro de EE. UU., agenda de Trump, miedo y codicia, un índice del dólar sintético e interés abierto de Bybit, OKX y Deribit. Lleva cuatro libros en papel: contado BTCUSDT, BTC/FDUSD con órdenes de creador, futuros BTCUSDT y un testigo que opera seguido sin ningún filtro. Gasta el 0,55 % de un núcleo y 42 MB de memoria, y va 1 segundo detrás del mercado. No tiene ningún camino de órdenes: nada sale de su dinero.

Se probó en vivo lo que podía fallar con el uso diario. Al pausarlo, los libros dejaron de entrar durante los 30 segundos de la pausa. Al cortarlo de golpe con un ciclo abierto, volvió a arrancar, cerró ese ciclo a mercado y siguió con sus conteos. Los accesos para arrancarlo, pararlo y quitar o poner el arranque con Windows funcionan, y un candado impide que corran dos agentes a la vez. Los huecos en los datos, los apagones largos y los frenos por datos de EE. UU. y discursos de Trump (con la hora de Nueva York en verano e invierno) tienen pruebas automáticas: 39 en verde.

Cada segundo calcula 31 rasgos, que incluyen sus estrategias de junio (retroceso en tendencia, techo extremo, barridos con agresión vendedora), y dos probabilidades: que el precio se mueva hasta la barrera y que ese movimiento sea hacia arriba. Solo entra si la ganancia esperada, descontadas las comisiones, es positiva. Aplica su Trading Plan (3 % por operación, 15 % diario, 20 % semanal), pausa de 15 minutos tras cinco pérdidas seguidas, tanda de 100 ciclos con pausa de revisión de 30 minutos y detención si una tanda pierde más del 10 %, y no abre ciclos alrededor de datos fuertes de EE. UU. ni de discursos de Trump.

Lo que opera en vivo es exactamente lo que se probó: en cinco repeticiones sobre cuatro días distintos, el código real del agente y el banco de pruebas dieron 704 ciclos idénticos en hora, lado, precios, motivo y cantidad, y las velas de 1 minuto que arma el agente coincidieron con las de Binance en los 3.595 minutos revisados.

## Lo que dicen los datos (medido en laboratorio)

Se usaron 14,86 millones de segundos de BTCUSDT y BTC/FDUSD, de mayo al 19 de octubre, verificados uno a uno con su suma SHA-256 y sin huecos. La probabilidad se entrenó con mayo a julio, se ajustó con agosto y la primera mitad de septiembre, y el tramo final (16 de septiembre al 19 de octubre) se miró una sola vez.

La dirección del precio a segundos y minutos resultó casi imposible de anticipar: la probabilidad de que suba ordena los casos apenas mejor que una moneda (AUC de 0,51 a 0,56, donde 0,50 es azar) y nunca llegó al 85 % que usted mencionó; su máximo en el tramo final fue 0,80. Lo que sí se anticipa bien es cuándo habrá movimiento (AUC de 0,74 a 0,77), pero eso no dice hacia dónde.

Operar seguido sin filtro pierde en los tres instrumentos, y la causa es la comisión: cuesta entre 0,04 % y 0,20 % por ciclo, mientras BTC, con una volatilidad diaria de 0,94 % en estos meses, se mueve de 0,05 % a 0,14 % en 5 a 30 minutos.

| Tramo final (34 días), 40.000 COP por libro | Operando seguido, sin filtro | Con la regla de seguridad |
|---|---|---|
| Contado BTCUSDT | −17,8 % en 100 ciclos (la tanda lo detuvo) | 0 ciclos |
| BTC/FDUSD de creador | −39,6 % en 600 ciclos | 4 ciclos, +1,2 % |
| Futuros BTCUSDT | −37,6 % en 49 ciclos | 0 ciclos |
| Testigo (contado, ciclos de 5 min) | −17,6 % en 100 ciclos | — |

Cien entradas al azar en contado perdieron casi lo mismo que operar siempre (−16,7 %): operando seguido, el modelo no aporta nada frente al azar. Con la regla de seguridad el agente casi no entra, y 4 ciclos en un mes no prueban ninguna ventaja. Solo BTC/FDUSD superó la validación, y por muy poco (30 ciclos, +1,1 %). Contado y futuros quedan marcados en el panel como «sin ventaja demostrada»; en futuros, con 12,59 USDT ya cabe una barrera de 0,15 % y en validación ganó 2,5 %, pero en solo 10 ciclos.

Pasar a pesos tiene además su propio costo: hoy un USDT se compra en P2P a unos 3.178 pesos y se vende a unos 3.147, así que ir y volver cuesta cerca del 1 % aparte de las comisiones del trading.

Hay además dos límites de un capital tan pequeño. En contado, la comisión de compra se cobra en BTC y deja polvo de casi un paso entero (unos 0,82 USDT) que se arrastra a la venta siguiente. En futuros, la orden mínima es 0,001 BTC (unos 83 USDT); con su tope del 3 % de 12,59 USDT solo caben stops de hasta un 0,37 %, así que cuando la volatilidad agranda la barrera, o tras unas pérdidas, la entrada no cabe.

## Lo que falta probar

- Órdenes de verdad en la red de pruebas de Binance: falta la clave nueva en `claves-testnet.env`.
- Los frenos de contexto en vivo, en un día con datos fuertes de EE. UU.: esta semana no hay ninguno de impacto alto. En laboratorio ya están probados.
- Un reinicio real del equipo con el arranque automático puesto, y un apagado de más de 6 horas (este último probado en laboratorio).

## Para la nube, más adelante

Binance rechaza con el error 451 («ubicación restringida») las conexiones desde EE. UU., también desde servidores en la nube de esas regiones, así que el agente tendrá que ir en un servidor fuera de EE. UU. Además, su regla del 19 de octubre dice que ninguna plataforma ni IA de terceros vea sus operaciones: conviene decidir eso antes de montarlo allá. El código no necesita librerías y se puede llevar tal cual a cualquier servidor con Python.

## Decisiones suyas

1. La única estrategia con ventaja medida es su MEZCLA de 1 hora (junio: +248 % en 24 meses de prueba histórica, con cortos en futuros). Opera varias veces por semana, no seguido. ¿La sumo a este mismo agente como libro aparte, en papel?
2. Para la nube: ¿en qué servidor y con qué plataforma, sabiendo lo del error 451 y su regla de privacidad?

## Cómo se usa

- Panel: `panel.html` en esta carpeta; se abre con el Buscador y se actualiza cada 5 segundos.
- Arrancar: `ARRANCAR AGENTE.cmd`. Parar: `PARAR AGENTE.cmd` (cierra lo abierto en papel y guarda el estado).
- Arranque con Windows: puesto. Se quita con `QUITAR ARRANQUE AUTOMATICO.cmd` y se vuelve a poner con `PONER ARRANQUE AUTOMATICO.cmd`.
- Capital de la prueba: `config.json` (pesos, tasa P2P y USDT).
- No abrir ciclos nuevos: crear un archivo llamado `PAUSA`. Quitar la detención de una tanda: crear `REANUDAR`.
- Diario: carpeta `diario` (ciclos por libro, eventos, resumen por minuto y velas de 1 s grabadas).
- Rehacer el banco de pruebas: `python -u -I banco_rapido.py`. Repetir la paridad: `python -u -I pruebas/paridad_motor.py`.
