# Prompt de desarrollo · Plan v9 · por ganancia de dinero

## 0. Encabezado

Plan v9 de las binarias, 20/11/2026, escrito a las 17:40 de Colombia con el meta-prompt (`2-META-PROMPT.md`) sobre la retroalimentación exacta (`1-RETROALIMENTACION-EXACTA.md`). Reemplaza la regla de acierto del plan v8 (18 de 25 para armarse solo; 19 de 25 con neto positivo para pasarle un punto a la IA). Pedido del dueño: «la gente dice que cambiemos la estrategia, que ya no utilicemos esta de acierto, sino otra cosa que sea por ganancia de dinero. Y pues yo estoy de acuerdo… hagámosle caso, porque él vigiló los datos».

## 1. Objetivo

Que ninguna pieza de las binarias decida por porcentaje de aciertos. El operador se arma solo, y el nodo le pasa puntos a la IA, únicamente cuando una fuente demuestra GANANCIA DE DINERO al precio real pagado y con el ganador oficial. Mientras ninguna lo demuestre, no hay dinero real en juego. Lo que el dueño ve en Telegram pasa a ser dinero, no aciertos.

## 2. Contexto verificado (teléfono, 20/11/2026, 16:55)

- Cuenta a mano del nodo (`nodo/dinero.json`), 18/11 11:15 a 20/11 16:35, 1 USDT por señal: E1 41 apuestas y −8,64; E2 19 y −12,22; E5 37 y −9,20; vigía 18 y 0,00; E3 4 y +1,02; E4 2 y +0,04.
- Papel del operador (`operador/registro/*.jsonl`): 5 min 116 compras y −21,13 (el modelo esperaba +34 %); 15 min 34 y −13,09.
- Medidor de la vigilante sobre esos 271 registros: «ninguna estrategia demuestra ganancia de dinero».
- Mercado de 5 min bien calibrado: cada tramo de precio pierde entre 1 % y 3 % por la comisión y el diferencial; por debajo de 0,10 se pierde entre 15 % y 17 %.
- Operador versión 3, estado 2 (papel con precios reales), nunca armado, sin órdenes reales, regla `ARMAR_AL_70` puesta. Billetera de predicción: 20,50 USDT. Código del teléfono igual al del PC (ocho huellas).
- Código que se toca: `nodo/nodo.py` (`cuenta`, `Libreta`, `Fuentes.leer`, `puntos_nuevos` línea 546, `paquete`, `mensaje`, `main`); `operador/operador.py` (`REGLA_ARMAR`, `UMBRAL_ARMAR`, `estrategias_centro`, `_atender`, `linea_estado`, `_armar_solo` líneas 705 a 732, `AYUDA`); `mesa/centro.py` (`_avisar_senal`, `_avisar_resultado`, `_niveles`, `_foto`), copia igual en `laboratorio/centro.py` y en el teléfono.

## 3. Retroalimentación que se acata

- Vigilante, 20/11 (`claude/proyectos-2026-11-20-ganancia`): «Sustituir el armado "18 de 25" y la compuerta "19 de 25 con ganancia" por la decisión GANA DINERO (demostrado)… Mientras ninguna estrategia tenga esa decisión, el operador no arma». Se acata con su criterio exacto: 100 apuestas como mínimo y límites inferiores normal y bootstrap (2.000 remuestras, semilla 20261120) por encima de 0, con alfa 0,05 dividido entre las fuentes.
- Vigilante, 19/11 (`-19`): mirar cada minuto infla el error. Se acata con una prueba que vale aunque se mire siempre (la cuenta de prueba, sección 5).
- Vigilante, 18/11 (`-18-regla70`): 18 de 25 arma por azar el 99,3 % de los meses. Se acata: la regla de armarse solo deja de mirar aciertos.
- Vigilante, 20/11 (`-20`): solo ganadores oficiales. Se acata: la cuenta a mano solo usa el ganador oficial de cada mercado.
- No se acata ahora: exigir la aptitud R6 del operador en el armado automático (`-18-regla70`). Queda superada por la prueba de dinero de cada fuente, que es la recomendación más reciente de la propia vigilante; R6 sigue mandando en el armado manual.

## 4. Reglas inviolables del dueño

- 2 USDT por orden; 16 % del saldo por orden; freno del día; 20 órdenes al día; una por mercado; sin ARMADO no hay orden real.
- Nunca apalancamiento, préstamos, margen ni futuros, tampoco como arreglo de un fallo.
- Todo corre dentro de la app Binarias del teléfono, sin depender del PC.
- Todo sale por la IP de la casa; nada por Tor.
- La IA solo ordena comprar, vender o nada; el script ejecuta. Claude nunca arma ni escribe «operador armar» por el dueño; solo vale la regla de armarse solo que él puso, y «operador parar» manda sobre ella.
- La caja T95H no se revisa (está con la ESP32). Nada de claves nuevas de la API de Claude. Ningún nombre ni clave en lo que se sube a GitHub (el repositorio `trader-btc` es público).

## 5. Diseño

GANANCIA DE DINERO de una fuente (E1 a E5, vigía, operador de 5 y de 15 min), sobre su cuenta a mano:
- Por apuesta, al precio real pagado q y con el ganador oficial: r = 0,98 / q − 1 si acierta, 0,49 / q − 1 si empata, −1 si falla.
- Una apuesta por ventana y fuente: si una fuente tiene varias entradas en la misma ventana, cuentan como una (la media de sus r), porque comparten resultado.
- Se cuenta toda la historia guardada de la fuente (hasta 5.000 por fuente), no solo las últimas 25.

Estados, con k = 8 fuentes y alfa = 0,05 (0,00625 por fuente):
- MUESTRA INSUFICIENTE: menos de 100 apuestas.
- GANA DINERO (demostrado): las cuatro cosas a la vez. (1) 100 apuestas o más. (2) Límite inferior normal de la media de r mayor que 0, con z de 0,00625 unilateral (2,50). (3) Límite inferior bootstrap mayor que 0 (2.000 remuestras, semilla 20261120). (4) Cuenta de prueba de 160 o más. Las tres primeras son la regla de la vigilante del 20/11; la cuarta es su advertencia del 19/11 llevada a dinero.
- PIERDE DINERO (demostrado): los límites superiores normal y bootstrap, los dos por debajo de 0.
- NO DEMOSTRADO: lo demás.
- Protección: aunque esté demostrada, si las últimas 25 apuestas de esa fuente suman dinero negativo queda «en pausa» y no cuenta.

Cuenta de prueba: una cuenta imaginaria que empieza en 1 y en cada apuesta de la fuente se multiplica por (1 + f·r), promediada entre cuatro fracciones fijas f de 0,02, 0,05, 0,10 y 0,20. Si la fuente no gana dinero, la probabilidad de que esa cuenta llegue alguna vez a 160 es menor que 1 entre 160 (desigualdad de Ville). Con ocho fuentes, la probabilidad de un armado por azar queda por debajo del 5 %, aunque se mire cada minuto para siempre. Es la versión en dinero de la prueba secuencial de la vigilante.

Dónde vive: el nodo lo calcula (ya tiene la cuenta a mano) y escribe `nodo/ganancia.json` cuando algo cambia o cada 5 min. El operador y el Centro solo lo leen. Si el archivo falta o tiene más de 15 min, nadie arma (falla cerrado).

Alternativas descartadas: seguir con 18 de 25 (arma por azar); Wilson sobre el acierto (sigue siendo acierto y no ve el precio); solo la regla fija de la vigilante sin la cuenta de prueba (mirando cada minuto, un acierto nulo termina pasando por azar); un tope a las ganancias de los lados baratos (castigaría una ventaja real barata).

## 6. Cambios

C1. Nodo (`nodo/nodo.py`, versión «v9 · 20/11/2026 (por ganancia)»):
- `Libreta.MAXIMO` de 200 a 5.000. Las compras de papel del operador también se apuntan en la libreta (`operador|operador5` y `operador|operador15`), para que sobrevivan a los reinicios.
- Funciones nuevas: `retornos`, `cuenta_de_prueba`, `limites` y `ganancia_de`, con las constantes de la sección 5.
- Un punto es ALTO solo si su fuente está en GANA DINERO (demostrado) y no en pausa. Reemplaza «19 de 25 con ganancias» (línea 546).
- `ganancia.json` con cada fuente: apuestas, aciertos, neto, por USDT, precio medio, límites, cuenta de prueba, últimas 25, estado y hoy.
- El paquete para la IA y el aviso de Telegram llevan el estado de dinero de cada punto. Al arrancar manda un resumen por fuente; después avisa solo cuando una fuente entra o sale de GANA DINERO (demostrado) o entra en PIERDE DINERO (demostrado).

C2. Operador (`operador/operador.py`, versión «4 · 20/11/2026 (se arma por ganancia de dinero; ordena la IA, al precio que vio)»):
- Regla `ARMAR_POR_GANANCIA`. Si encuentra `ARMAR_AL_70`, es la misma orden suya de armarse solo: la renombra y le avisa una vez que ya no mira aciertos.
- `_armar_solo`: una vez por minuto lee `ganancia.json`; arma solo el mercado de la fuente demostrada (15 min para el Centro, el vigía y el operador de 15; 5 min para el de 5), con la llave y la billetera bien. Sin archivo fresco, no arma.
- Textos: ayuda, estado y «operador automático» hablan de ganancia de dinero, no de 18 de 25. Orden nueva «operador dinero»: la tabla de dinero de cada fuente.
- «operador parar» quita las dos reglas y desarma, como hoy.

C3. Centro (`mesa/centro.py`, igual en `laboratorio/` y en el teléfono):
- Con `ganancia.json` presente: cada señal y cada resultado muestran la línea de dinero de esa estrategia en vez de «k de 25»; se quita «APTA (82 %)»; dejan de salir los avisos de 75 % y 82 % (los de dinero los manda el nodo). Sin el archivo (la Mesa del PC), queda como estaba.
- La línea de «su regla» (SÍ o NO del 03/11) se queda tal cual: es su regla y no decide nada.

C4. Rutina aprobadora (claude.ai): bloque «GANANCIA DEMOSTRADA (20/11/2026)» que explica los campos nuevos del paquete. No cambia su forma de responder. Si el control de permisos lo niega, queda para el dueño.

C5. `PLAN-TOTAL.md`: la regla del v9 escrita en la sección 7b antes de instalar.

C6. Laboratorio de la ESP32: no se cambia hoy. Fase 2: medir contra el precio de apertura de la ventana y contra el precio del libro, con la misma regla de dinero.

## 7. Criterios de aceptación

- A1. Matemática: r de acierto, empate y fallo exactos; cuenta de prueba igual a una cuenta hecha a mano en tres casos; límites iguales a los del medidor de la vigilante (diferencia menor que 1e-9) con el mismo registro y la misma semilla.
- A2. Paridad con la vigilante: con los 271 registros reales, los estados de `ganancia.json` coinciden fuente por fuente con su medidor (el mismo «MUESTRA INSUFICIENTE» o «NO DEMOSTRADO»), y ninguna fuente queda demostrada.
- A3. Una fuente con 19 de 25 (y aun 25 de 25) sin dinero demostrado NO es punto alto y no dispara la rutina.
- A4. Una fuente sintética con ventaja real (300 apuestas a 0,50 que aciertan 70 %) queda GANA DINERO (demostrado), es punto alto y dispara la rutina; si sus últimas 25 pierden, queda en pausa y no dispara.
- A5. Sin ventaja (moneda justa al precio), en 200 simulaciones de 1.000 apuestas por cada una de las 8 fuentes, el armado por azar sale en el 5 % o menos.
- A6. Operador: con `ganancia.json` sin fuentes demostradas, no arma; con una de 15 min demostrada, arma solo el de 15 y avisa; con el archivo viejo (más de 15 min) o ausente, no arma; «operador parar» quita la regla; `ARMAR_AL_70` se convierte en `ARMAR_POR_GANANCIA` una sola vez.
- A7. Centro: con `ganancia.json`, el aviso de una señal no dice «de 25» y sí dice el neto en dinero; sin el archivo, el aviso queda igual que antes.
- A8. Todas las pruebas que ya existían siguen bien (nodo, rutina, aprobación, regla y paridad), ajustando solo las que medían el «alto» por acierto.
- A9. En el teléfono, después de instalar: los seis programas vivos, `ganancia.json` escrito y con los mismos estados que en el PC, sin ARMADO, y el operador «versión 4».
- A10. Nada de esto envía órdenes, toca la llave o cambia los topes de dinero.

## 8. Pruebas

En el PC: `prueba_ganancia.py` (A1 a A5) y las de siempre (`prueba_nodo.py`, `prueba_rutina.py`, `prueba_aprobacion.py`, `prueba_regla70.py` convertida en `prueba_armar_ganancia.py`, `prueba_paridad.py`). En el teléfono, con el motor de la app, en una carpeta aparte: las mismas. Paridad con la vigilante: su `medidor_ganancia.py` sobre la exportación real, frente a `ganancia.json`.

## 9. Instalación, respaldo y reversa

`app-telefono\v2\ganancia.sh probar|instalar|comprobar|volver` (como `paridad.sh`): copia de lo de antes con la marca `.antes-ganancia-20-11`; para el operador y el nodo con su PARAR, pone lo nuevo y deja que la app los relance; el Centro se cambia con su propio PARAR. Volver: `run-as co.binarias.motor sh /data/local/tmp/ganancia-20-11/ganancia.sh volver`. La rutina aprobadora tiene su copia en `respaldos\rutina-aprobadora-antes-ganancia-20-11.json`.

## 10. Lo que NO se hace

No se arma a mano ni se crea ARMADO. No se toca la llave ni la billetera. No se cambian el importe ni los topes. No se quita la regla de armarse solo: se cambia su criterio. No se toca la caja ni la ESP32. No se borra nada. No se sube nada a master ni datos del teléfono a GitHub.

## 11. Registro

Bloc de Obsidian: AL FRENTE nuevo (v9), ENCARGOS y BITÁCORA con hora de Colombia, y la línea «SIGUIENTE PASO». Bóveda: nota «Binarias - plan v9 por ganancia». Memoria: `binarias-bloc-unico` puesta al día y `binarias-plan-v9-ganancia`. GitHub: `sincronizar_repo.py` a la rama `binarias/plan-v7-2026-11-04`.

## 12. Informe final

Hecho y probado (con cifras de las pruebas); lo no probado; lo que solo puede hacer el dueño; veredicto en tres líneas. «Listo» solo si A1 a A10 se cumplen; si no, «no consolidable» aunque todo corra.
