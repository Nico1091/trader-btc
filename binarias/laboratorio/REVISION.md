# Revisión del laboratorio con PROMPT-REVISION.md

Revisión del 11/11/2026, 19:55 (hora de Colombia), sobre PLAN-LABORATORIO.md y PROMPT-FINAL.md versión 1, antes de escribir código. Cada hallazgo trae la prueba que lo sostiene y el cambio que obliga. Lo que no se pudo comprobar queda como «sin comprobar». Los cambios ya están incorporados en el código del laboratorio; esta revisión se repite en el paso 10 contra lo construido.

## 1. Información del futuro

1.1. La neurona t33 se midió con entrada inmediata (`o[j+1]` contra `c[j+10]`, pruebas\t33_indice.py, línea 67), mientras que el Centro y el laboratorio miden con entrada 60 s tarde (`cierre[T]` contra `cierre[T+plazo]`, mesa\centro.py, líneas 348 y 349). Comparar la red nueva con los 55,6 % de t33 mezclaría dos medidas. Cambio: la línea base se reajusta dentro del laboratorio con los mismos diez rasgos, la misma etiqueta de 60 s tarde y las mismas ventanas mensuales que la red. La neurona original del 31/10, con sus pesos de t33_indice.json, queda además como forma pasada.

1.2. El RSI de Wilder y las medias exponenciales tienen memoria infinita: su valor depende de dónde empiece la serie. En vivo se calculan sobre una ventana de días y en la historia sobre años, de modo que la misma vela daría cifras distintas y la prueba de recorte fallaría. Cambio: la gramática de formas nuevas usa el RSI de Cutler (medias simples de 14 subidas y bajadas) y desviaciones con ventanas deslizantes, nunca sumas acumuladas. E3 y E4 conservan el código del Centro, que también trabaja con 30 días, y por eso su paridad se prueba contra el Centro y no contra la historia larga.

1.3. El interés abierto del archivo de data.binance.vision lleva una marca 5 min anterior a la del servicio en vivo (memoria binarias-bloc-unico, P14b). Cambio: en la historia se usa el margen de 600 s de cuant\c9c_interes.py (líneas 87 a 92) y en vivo la fórmula del semáforo (instantáneas con hora ≤ T − 300 s y ≤ T − 1200 s, dispositivos\semaforo.py, líneas 105 a 113), con el mismo umbral de 0,022 %.

1.4. La red se normaliza con la media y la desviación de su propia ventana de ajuste, y cada mes desde enero de 2024 la predice una red ajustada solo con apuestas cuya salida terminó antes del primer minuto del mes (purga de un plazo más 60 s).

## 2. Elegir mirando el resultado

2.1. La red de búsqueda aprende solo de la cifra de «elige». La de «juzga» se calcula una vez, al entrar la forma a vivo, y nunca vuelve a la red ni a la selección.

2.2. Con unas 1.200 formas probadas al día, alguna pasará por suerte aunque Benjamini-Hochberg se aplique en cada tanda de 50. Cambio: el parte diario trae el acierto que el azar solo le daría a la mejor de N formas con ese n (`acierto_maximo_por_azar`) y el rendimiento por origen, que separa lo que aporta la red («red») de lo que sale al azar («azar»).

2.3. Corregido a las 20:15 con la primera construcción. Estimé la valla con el equilibrio de 10 min (54,05 %), donde sí es dura. A 15 min el equilibrio es 52,04 % y las familias de devolución tienen allí una ventaja real de 2 a 3 puntos (E1: 54,4 % en «elige» con 10.055 y 54,8 % a ciegas con 9.006), así que pasan con facilidad: entraron 613 de 950 formas probadas en 20 tandas.

2.4. Hallazgo de la primera construcción (11/11, 20:12): la red de búsqueda converge en variantes casi iguales de lo que funcionó, y las más afortunadas de «elige» regresan a su nivel en «juzga». Ejemplo: «RSI de 15 min sobre 82 + ruptura de 56 velas, al revés, 15 min» dio 64,3 % en «elige» (n = 496) y 54,2 % a ciegas (n = 491); las doce mejores del primer intento, todas entre 61 y 64,5 % en «elige», quedaron entre 49,2 y 55,7 % a ciegas. No hay información del futuro: es selección. Cambios: (a) como mucho 12 formas vivas por familia (mismos disparos, filtros, sentido y plazo); las demás esperan cupo y entran en la rotación diaria, las de mejor «elige» primero; (b) el tablero y los partes muestran siempre la cifra a ciegas junto a la de vivo, y ninguna cifra de «elige» se presenta como resultado.

## 3. Precio y momento de entrada

3.1. Los Contratos de Evento liquidan con el índice de precio de Binance (con él, el núcleo de 2024-26 queda en 54,1 %). Cambio: cada apuesta se mide con el cierre de futuros y, cuando hay dato, también con el índice (en vivo con indexPriceKlines; en la historia con los 34 meses de datos\indice_crudos, desde enero de 2024).

3.2. A 15 min, el mercado de Predict.fun liquida con su propio oráculo, que no se ha comprobado. Sin comprobar: se mide con futuros y se anota el riesgo.

## 4. Cuentas

4.1. El laboratorio no lleva saldo: mide aciertos y neto por apuesta a pagos de 0,80, 0,85 y 0,90 (10 min) y a precios de 0,50, 0,51 y 0,53 con 2 % de comisión (15 min). Tope del 16 %, mínimo de 5 USDT y jamás apalancamiento siguen siendo reglas del dinero real, que el laboratorio no toca.

4.2. Una apuesta abierta por forma, como `_libre` del Centro: la siguiente desde T + 60 s + plazo. Diferencia anotada: el Centro bloquea también con una apuesta cuya vela de entrada faltó («hueco»); el laboratorio no la cuenta ni bloquea con ella. Solo cambia algo alrededor de huecos de datos.

## 5. Tamaño y dependencia

5.1. Cada cifra va con su n. Con 57 % real, una forma necesita unas 400 señales en vivo para quedar apta; con 55,5 %, unas 800; a una o dos señales al día, eso son meses.

5.2. Las formas se solapan entre sí (varias pueden apostar a la vez) y no son independientes. El cálculo de «mejor de N por azar» las trata como independientes: exagera la suerte posible y por eso es prudente.

## 6. Regímenes

6.1. La primera versión no separa por años ni por régimen en el parte. Pendiente para la versión 2: por año y alcista frente a bajista en las formas aptas.

## 7. Paridad

7.1. E1 a E4 se calculan con las funciones del Centro, copiadas sin cambios (centro.py y graficas.py con su huella), y la prueba compara 40 días señal por señal. E5 (cinco líneas en cada vela) es demasiado lento para la historia en la caja: queda solo en vivo, con su cifra de largo plazo del Centro (51,8 % en 14.023).

7.2. Las formas de la gramática se prueban con el mismo código en el PC y en la caja; la paridad se comprueba con una huella de las apuestas de 20 formas fijas en «elige».

7.3. El núcleo del semáforo (ruptura de 20 velas al revés en las marcas de 10 min) se emula con la regla de una apuesta abierta; el papel del semáforo no la tiene y su cifra puede diferir un poco. Anotado.

7.4. Del banco de motor\senales.py entran todas sus señales, con su sentido y a 10 y 15 min. Las configuraciones de seleccion.json (zona, sesión y volatilidad) quedan para la versión 2: sin comprobar su definición exacta, no se copian.

## 8. Operación

8.1. Caja apagada: el laboratorio no mide nada y no hay relevo en el teléfono; al volver rellena las velas que faltan y sigue. Telegram caído: los mensajes esperan en la tabla `salida` y se reintentan; los avisos de más de dos horas se descartan. Reloj desfasado más de 30 s frente a Binance: pausa y aviso. Dos laboratorios a la vez: imposible, el segundo no consigue el puerto 127.0.0.1:8798 y sale. Calor: búsqueda y entrenamiento se pausan a 70 °C y vuelven a 62 °C.

8.2. Telegram guarda 24 h de mensajes sin confirmar y getUpdates devuelve como mucho 100. Leyendo sin offset (para no consumir mensajes que lean otros programas), si en un día se acumulan más de 100, las peticiones nuevas no se verían. Riesgo anotado; el laboratorio responde cada petición una sola vez por su número.

8.3. El laboratorio y el centinela comparten la caja: el laboratorio corre con nice 10 y un hilo; no lee ni escribe en la carpeta del centinela (copia una vez el historial de velas a su carpeta).

8.4. Hoy el centinela de la caja está detenido con ESPERA_ESTADO hasta copiarle el estado del teléfono. El laboratorio no depende de él.

## 9. Reglas

Papel solamente; ningún archivo importa conexion.py, lee llaves ni toca REAL_AUTORIZADO (lo comprueba prueba_laboratorio.py); Binance directo y Telegram por Tor; sin IA externa; sin agentes; nada se instala antes del paso 12; hora de Colombia; de usted y sin su nombre; registro formal.

## 10. Veredicto

Esta revisión es previa: no hay resultados todavía. «Listo» se dirá solo con los pasos 5, 6, 8 y 9 cumplidos y sin preguntas «sin comprobar» que afecten a lo que corre. Quedan sin comprobar: 3.2 (oráculo de 15 min) y 7.4 (configuraciones de seleccion.json), que no afectan a lo que corre.
