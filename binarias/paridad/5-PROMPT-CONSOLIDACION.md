# Prompt de consolidación · la rutina debe ganar lo mismo que la apuesta manual (18/11/2026)

Reemplaza a `PROMPT-MEJORA-REGLA70-18-11.md`. Lo usa quien trabaje en las binarias: una sesión de Claude Code o la rutina de proyectos de la nube. Se apoya en `1-PLAN-REVISION.md`, `2-REVISION.md`, `3-PLAN-ANALISIS.md` y `4-ANALISIS.md` de esta carpeta.

## Lo que se sabe y no se discute

En el mercado «BTC Up or Down» de Binance, comprar un lado a precio q paga 0,98 ÷ q por USDT si acierta (el «Ganar» de la app) y nada si falla. Ese pago no es ganancia: a precio justo, todos los lados pierden en promedio el 2 % de la comisión. Solo se gana cuando la probabilidad real de un lado supera su equilibrio, q ÷ 0,98. Una compra a mano y una de la rutina, iguales en mercado, lado, precio y momento, ganan exactamente lo mismo. Si la rutina gana menos, la causa está en el precio, la demora o la cuenta, nunca en el mercado.

El 18/11 la rutina ganaba menos por cuatro causas medidas. Compraba sin tope de precio y hasta 10 min después de decidir. Decidía con información de 35 s a más de 2 min atrás, cuando en el mercado de 5 min el lado ganador sube 0,085 por minuto. Mandaba a la IA estrategias elegidas con un precio supuesto de 0,544 y un resultado que no era el del mercado comprado (signo invertido en E1, E3 y E5). Y la rutina de la nube medía con un pago fijo de 0,85.

## Reglas de paridad (invariantes de la aplicación)

P1. Toda cuenta de dinero usa 0,98 ÷ precio real, con el empate a medio pago. Nunca un pago fijo ni un precio supuesto.

P2. La historia de cada estrategia se lleva como la llevaría el dueño a mano. Se toma el lado de la señal en el mercado donde se compraría (15 min para el Centro y el vigía), al precio real del libro en el minuto de entrada (el de la señal más uno; si esa mirada se perdió, el siguiente), con el ganador oficial. La medida propia de la estrategia se conserva solo para mirar.

P3. Un punto es alto solo si su historia a mano tiene 25 señales, 19 aciertos o más y neto positivo. Sin eso no se consulta a la IA.

P4. La IA recibe de los dos lados el precio real, lo que paga por USDT y el equilibrio. Sin precio real no se la consulta.

P5. La orden de la IA se compra solo si el precio cotizado no pasa en más de 0,02 el que ella vio para ese lado. Vale 2 min y nunca más allá del cierre. Si no trae precio, no se compra.

P6. Entre la señal y la orden pasan unos 25 s: 8 s para juntar puntos y lecturas de la decisión cada 3 s.

P7. Siguen intactos los topes del dueño: 2 USDT por orden, 16 % del saldo, freno del día, 20 al día, una por mercado, ARMADO, PARAR, regla del 70 % para armarse y nunca apalancamiento ni préstamos.

## Cambios que lo cumplen (hechos el 18/11/2026; copias de lo anterior en `respaldos/antes-paridad-18-11`)

- `nodo/nodo.py`: lleva la cuenta a mano (P2 y P3) en la clase `Libreta`, guardada en `dinero.json`, y la reconstruye desde los registros del operador al arrancar. Las miradas con libro se leen aunque sean viejas. `resumen` deja la medida propia en `aciertos_propios` y `de_propios`, y `cuenta` saca el dinero sin suponer nunca un precio (`PRECIO_MEDIDO` se quitó). `vector_corto` añade `paga`, `equilibrio` y `compra_hasta` por lado. La decisión guarda `precios`, `precios_m` y `precios_hora` de la mirada que vio la IA. Sin precio real no se consulta a la IA: queda «sin_precio» y no se gasta una corrida (P4). Un punto alto de un nodo sin cuenta a mano (la caja con el código de antes) no cuenta como alto. Cambian `ESPERA_JUNTAR` a 8, `VUELTA` a 5 (2 mientras hay algo pendiente), `MIRAR_DECISION` a 3 y `CADUCIDAD_S` a 120. El aviso de Telegram muestra la cuenta a mano, lo que paga cada lado y el tope.
- `nodo/medir_combinacion.py`: sin precio real no cuenta (se informa «sin precio real»); vigencia de 120 s.
- `operador/aprobacion.py`: `CADUCIDAD_S` pasa a 120.
- `operador/ejecutor.py`: `precio_visto` y `ejecutar_ia` exigen el precio visto y aplican `TOLERANCIA_IA = 0,02` (P5). Si cotiza más caro, vuelve a cotizar cada 15 s mientras la orden siga vigente. El aviso dice a cuánto la vio la IA y cuánto paga si acierta.
- `operador/conexion.py`: `_firmado`, ante un −1021, vuelve a medir la hora de Binance y repite una sola vez.
- `operador/operador.py`: versión «3 · 18/11/2026 (ordena la IA, al precio que vio)»; el aviso de arranque dice el equipo verdadero.
- Rutina aprobadora (`trig_01Ep7i969sChfFw4Mb3eN4qM`): se le añadió el bloque PRECIO Y CUENTA (P4 y P5) el 18/11 a las 16:02. Copia de antes: `respaldos/rutina-aprobadora-antes-paridad-18-11.json`. El token, el modelo, el esfuerzo, el entorno y el repositorio son los mismos.
- Herramientas: `paridad/analisis_paridad.py` (el análisis), `paridad/prueba_paridad.py` (paridad nodo frente al análisis), `paridad/prueba_punta_paridad.py` (disparo de prueba desde el teléfono) y `app-telefono/v2/paridad.sh` (probar, instalar, comprobar y volver, como la app).

## Pruebas de aceptación (todas deben pasar antes de decir «listo»)

1. Las suites que existían siguen bien en el PC (Python 3.11) y con el motor de la app (3.14.8). Se corrigieron solo donde exigían lo que esta consolidación quita: precio supuesto, órdenes de 10 min y órdenes sin precio. Resultado del 18/11: nodo 70 de 70, rutina 36 de 36, aprobación 57 de 57, regla del 70 % 16 de 16.
2. Pruebas nuevas de paridad: la cuenta a mano del nodo da, señal por señal, lo mismo que `analisis_paridad.py` con los mismos datos. Una orden vista a q nunca se compra por encima de q + 0,02. Una orden sin precio visto nunca se compra. Una orden de más de 120 s no se compra. Sin precio real no se dispara la rutina. Un −1021 se repite una sola vez. Resultado: paridad 9 de 9, con los datos reales del teléfono incluidos (10 de 10 señales iguales), y los casos de precio y de −1021 dentro de la suite de aprobación.
3. En el teléfono: copia de lo anterior, instalación sin armar nada, programas de vuelta y diez minutos de registro sin errores. El nodo anuncia la cuenta a mano y el operador sigue en estado 2. Resultado: instalado a las 16:01; el operador, versión 3 en estado 2 y sin ARMADO; el nodo, con la cuenta a mano. Disparo de prueba a las 16:03: la rutina con las instrucciones nuevas respondió «NO COMPRAR» en unos 31 s y el teléfono la leyó.
4. Se revisa este prompt contra lo que de verdad quedó y se corrige lo que no coincida. Hecho el 18/11 a las 16:05: este texto es el que corresponde a lo instalado.

## Para la rutina de proyectos de la nube

Si se le pide rehacer el simulador de la regla del 70 % (rama `claude/proyectos-2026-11-18-regla70`), debe quitar el pago fijo de 0,85 y usar P1 con precios reales: los del registro del operador, que el dueño puede subir a la rama, o el modelo del operador, que se aparta del precio real 0,033 en promedio. También debe separar la medida propia de la estrategia de su historia a mano. No toca `binarias/operador/` ni `binarias/nodo/`, no envía órdenes y no sube a main.
