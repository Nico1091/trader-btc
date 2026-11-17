# Agente aprobador de las binarias · plan

Escrito el 17/11/2026 por la rutina constructora (Claude Opus 5.5, esfuerzo máximo), hora de Colombia. Rama `claude/aprobador-binarias-2026-11-17`, salida de `binarias/plan-v7-2026-11-04` en 7429f90. Manda la sección H de la rutina: se construyó encima del nodo y del operador que ya corren en el teléfono, sin rehacerlos.

## 1. Cómo funciona, en corto

```
 Centro de estrategias (E1 a E5)  ─┐
 Vigía de 15 min (teléfono, caja)  ├─►  NODO del teléfono  ──►  ¿algún punto ALTO (19 de sus últimas 25)?
 Operador de Fable 5.2 (su papel) ─┘    (sin IA, cada 10 s)          │ no: queda anotado, no se consulta
                                                                      │ sí: espera 20 s a los demás puntos y hasta 90 s
                                                                      ▼    la mirada del operador de ese mercado
                                         Claude Opus 5.5 (API de mensajes): COMPRAR SUBE · COMPRAR BAJA · NO COMPRAR
                                                                      │
                                         decisiones.jsonl del teléfono (mercado, ventana, sentido, decisión, costo)
                                                                      │
 Operador de Fable 5.2 ─ en cada mirada con compra ─► sus frenos ─► CANDADO NUEVO: ¿hay un COMPRAR vigente de Claude
                                                                     para este mercado y este sentido? ─► cotización ─► orden
```

- Lo repetitivo (cada 10 s el nodo; cada minuto el operador) es código sin IA en el teléfono: cero tokens.
- A Claude solo van los grupos con algún punto alto, sin tope de consultas.
- Claude no inventa compras ni fija importes: aprueba o no el sentido de un punto. El operador sigue decidiendo el precio y el importe con sus reglas; el candado solo puede impedir una orden, nunca provocarla.
- Falla cerrado en todos los caminos: sin clave de Claude, sin respuesta, error, respuesta ilegible o cortada, negativa de Claude, el sentido contrario al punto, decisión vencida (10 min), otra ventana, otro mercado, decisión copiada de la caja, nodo caído o archivo ilegible = no hay orden real.

## 2. Las reglas de Fable 5.2 y cómo se respetan

Fuentes: `operador/PLAN-AUTOMATICO.md`, `comprador/REGLAS-ANTES-DE-MEDIR.md` (R1 a R8 y enmiendas 1 y 2), `operador/*.py` y el bloc. Ninguna se cambió. El único cambio en su código es una línea en `ejecutor.py` que agrega un freno más al final de los suyos (sección 3).

| # | Regla de Fable 5.2 | Dónde vive | Cómo queda |
|---|---|---|---|
| 1 | Mirada al cierre de cada minuto 1 a W − 1, en los 5 s siguientes; si no se logra, se pierde (R3.1, enmienda 1) | `papel.py` | Igual. El papel es idéntico con y sin decisiones de Claude (probado). |
| 2 | Probabilidad: logística de doce rasgos aprendida con 2021-2023 (R1) | `nucleo.py`, `entrenar.py` | Igual. |
| 3 | Probabilidad prudente: peor trimestre a ciegas por tramo (R2) | `nucleo.prudente` | Igual. |
| 4 | Ganancia esperada G = p × 0,98 / q − 1; comisión del 2 % | `nucleo.ganancia` | Igual. Claude la ve en el paquete. |
| 5 | Compra el lado con ganancia esperada prudente ≥ 0,10; precio entre 0,01 y 0,90; 10 s o más para el cierre (R3.3) | `nucleo.decidir` | Igual. El margen solo se puede subir. |
| 6 | Llenado honesto: precio leído 5 s después (y 15 s en paralelo); si ya no cumple, «se escapó» (R3.4) | `papel._llenar` | Igual. El nodo ya no cuenta las escapadas como compras (era un error del nodo, no de Fable). |
| 7 | Una compra por ventana en papel; una orden por mercado en real; segundo envío solo tras un rechazo claro | `papel`, `ejecutor._frenos` | Igual (probado: una orden por mercado con aprobación). |
| 8 | Libro A 1 USDT fijo; libro B un cuarto del Kelly prudente, tope 16 % del saldo, sin pasar el libro, mínimo 2 USDT (R3.6, enmienda 2) | `nucleo.importe_b`, `ejecutor.intentar` | Igual. Claude no toca importes. |
| 9 | Celdas, apagado en sombra y «apto» (R4, R5, R6) | `juez_op.py` | Igual. «Apto» sigue sin autorizar dinero. |
| 10 | Lo que el agente de la nube no puede: mandar órdenes, pedir llaves, bajar el margen, quitar el llenado honesto, mezclar series, borrar pérdidas (R7) | reglas | Respetado: esta rutina no mandó órdenes, no pidió llaves y no armó nada. |
| 11 | Varianza aceptada de antemano; el juicio va por R6, no por rachas (R8) | reglas | Respetado; ver la opinión de la sección 7 sobre el umbral de 19 de 25. |
| 12 | Mercado de 5 min con modelo y serie propios; plazos como etiquetas; medición sin llave (enmienda 2) | `nucleo`, `papel` | Igual. El nodo lleva una serie del operador por mercado (antes las mezclaba). |
| 13 | Llave propia del equipo con Lectura y Predicción y nada más, restringida por IP | `ejecutor.revisar_llave` | Igual. |
| 14 | Cotización real antes de enviar: si ya no deja el margen, no envía | `ejecutor.intentar` | Igual; el candado va antes, así no se piden cotizaciones sin aprobación. |
| 15 | Freno del día: lo perdido en el día de Colombia (con lo abierto) no pasa del 16 % del saldo inicial; tope de 20 órdenes al día | `ejecutor.cupo_hoy`, `_frenos` | Igual (probado en el simulador). |
| 16 | «Comprada» solo si Binance lo confirma; relectura hasta estado final, también tras un reinicio | `ejecutor.paso` | Igual. |
| 17 | Cobro de lo ganado, como mucho tres pedidos; si no, aviso al dueño | `ejecutor._cobrar` | Igual (sigue sin probar con dinero real, como dijo Fable). |
| 18 | −2015: vuelve al estado 1 y avisa la IP | `operador._avisar_llave_mala` | Igual. |
| 19 | Tres estados: sin llave, papel con precios reales, ARMADO | `operador._estado` | Igual. El candado solo actúa en el estado 3. |
| 20 | ARMADO solo por orden del dueño («operador armar», «armar igual» si no es apto); PARAR y «operador parar» desarman | `operador`, `ejecutor.armar` | Igual. Esta rutina no creó ARMADO (solo en carpetas temporales de las pruebas). |
| 21 | Un solo operador por equipo (puerto 8794) | `operador.tomar_candado` | Igual. Además: nunca dos operadores armados (el de la caja sigue con PARAR). |
| 22 | Hora de Binance sobre el reloj monótono; con reloj dudoso no mira ni compra | `conexion` | Igual. |
| 23 | No decide con IA; no toca la app ni los Contratos de Evento; no usa la llave del PC; no apalanca | todo | El operador sigue sin IA: Claude decide fuera de él y el operador solo lee un archivo. |
| 24 | Todo queda en el registro, en estado.json, en operador.log y en el parte diario | `operador` | Igual; cada intento parado por el candado queda anotado con su motivo. |

## 3. El cambio en el código de Fable, exacto

`operador/ejecutor.py` (huella de antes 846ad82222d7f6d1, de después 0b5448b9bbbea250):

- línea 28: `import aprobacion as APROBACION`
- línea 222: `motivo = self._frenos(ahora, m, W) or APROBACION.falta(W, m["t"], lado, ahora)`
- dos líneas de explicación en su lista del candado (punto 7).

`operador/aprobacion.py` es nuevo: lee la cola de `~/nodo/decisiones.jsonl` (o `/data/local/tmp/nodo/decisiones.jsonl` en la caja) y devuelve `None` solo si la última decisión de este equipo para ese mercado y esa ventana dice COMPRAR en el mismo sentido, tiene menos de 10 minutos y la ventana sigue abierta. Nunca lanza errores: cualquier rareza es un motivo para no comprar.

Pruebas (`operador/prueba_aprobacion.py`, 36 de 36 en Python 3.11 y 3.13):

- 20 casos del candado solo: sin archivo, vacío, ilegible, NO COMPRAR, sin respuesta, el otro sentido, el otro mercado, la otra ventana, vencida, ventana cerrada, la última manda, puntos contrarios, copiada de la caja, hora del futuro, sin hora, archivo de 336 KB (lee solo la cola, 7 ms).
- El operador entero en el simulador de Fable, ARMADO en una carpeta temporal, 35 minutos simulados: sin decisiones, cero órdenes y saldo intacto con 60 intentos anotados; con «COMPRAR SUBE», 10 órdenes, una por mercado, compradas y liquidadas; con NO COMPRAR, el otro sentido, vencida o copiada de la caja, cero órdenes; el papel idéntico en todos los casos.
- Antes y después: el código de Fable tal como estaba en 7429f90 y el nuevo con la aprobación dan las mismas 10 órdenes, el mismo registro, el mismo saldo y las mismas escrituras en Binance.
- Las pruebas propias de Fable (`prueba_operador.py`) no están en la rama (AVANCE, hallazgo 1). Las del comprador piden numpy (`laboratorio/perdida_red.py`) y no corren aquí; el comprador no se tocó.

## 4. El nodo y la llamada a Claude

Revisada el 17/11 contra la documentación oficial de la API de mensajes (la de la herramienta de Claude y las páginas de precios y de caché):

- `POST https://api.anthropic.com/v1/messages` con `x-api-key`, `anthropic-version: 2026-10-21` (la versión vigente; nada del pedido cambia con ella) y `content-type: application/json`. La clave viaja a curl por la entrada estándar, nunca en la línea de órdenes ni en los registros.
- Modelo `claude-opus-5-5`. En Opus 5.5 el pensamiento no se puede apagar (enviar `thinking` desactivado da error 400), así que se controla con `output_config.effort: "low"` y `max_tokens: 2048`. El nodo anterior pedía 300: con el pensamiento siempre encendido, la respuesta podía quedar cortada y no comprar nunca.
- Salida forzada en JSON con un esquema (`decision` ∈ {COMPRAR SUBE, COMPRAR BAJA, NO COMPRAR}, `motivo`): elimina las respuestas ilegibles. Si aun así llega texto, se lee el formato de dos líneas; si no, NO COMPRAR.
- Contexto fijo (`CONTEXTO-NODO.md`, unos 1.900 tokens) en caché de 1 hora (`cache_control: {type: ephemeral, ttl: 1h}`). El mínimo para guardar en caché en Opus 5.5 es 512 tokens: el contexto anterior estaba al borde; el nuevo pasa con holgura.
- `stop_reason: refusal` o `max_tokens` = NO COMPRAR. Errores 401, 402, 403 o 404 = sin decisión y aviso aparte a Telegram (como mucho cada 6 h). 429, 500, 529: un reintento a los 5 s; si sigue, sin decisión.
- No se activó el respaldo automático de modelo que ofrece la API ante una negativa: haría decidir a otro modelo y el dueño ordenó que decida Opus 5.5. Una negativa cuenta como NO COMPRAR.
- Rutas: primero directa desde la casa; si no conecta (DNS, conexión, TLS), por Tor. Con Tor, Anthropic puede rechazar salidas de países no admitidos; la ruta directa es la normal. Se agregó `--noproxy ""` a la ruta de Tor: sin eso, una lista de excepciones de proxy del equipo puede hacer que curl se salte Tor sin avisar (se comprobó aquí).
- Si Claude propone el sentido contrario al punto, queda NO COMPRAR (nunca compra lo que nadie propuso).
- Cada decisión guarda: mercado (W), ventana, sentido, decisión, motivo, puntos, puntos en contra, tokens (entrada, caché escrita, caché leída, salida), costo en dólares, segundos y ruta. `estado.json` lleva el gasto del día.

Lo que el nodo arregló de sí mismo (no era código de Fable): contaba como compras las escapadas del papel y las órdenes paradas; mezclaba los mercados de 5 y de 15 min del operador cuando abrían a la misma hora; dejaba «abierta» una señal empatada del vigía; agrupaba por minuto de la señal (un punto de 5 min y uno de 15 podían ir juntos); releía tres días de registro del operador cada 10 s; escribía `estado.json` cada 10 s.

## 5. Costos

### Una revisión del nodo (medido, `nodo/medir_nodo.py`)

Con archivos del tamaño real (centro.json de 1,46 MB, quince.json de 22 KB, tres días de registro del operador, 6,6 MB), en el PC de la nube con Python 3.13:

| Revisión | Procesador | Leído |
|---|---|---|
| Al arrancar (una vez) | 50 ms | 7,8 MB del disco |
| Sin cambios (5 de cada 6) | 0,0 ms | 0 KB |
| El Centro reescribió su archivo (1 por minuto) | 22 ms | 1,4 MB del disco |
| Dos miradas nuevas del operador | 0,1 ms | 1,8 KB |
| Media de un minuto típico | 3,7 ms | unos 240 KB del disco, nada por la red |

El nodo anterior gastaba unos 160 ms de procesador en cada revisión con los mismos archivos (releía 7,8 MB cada 10 s): unas 40 veces más. En el teléfono las cifras serán de 3 a 5 veces mayores que en el PC; quedan muy por debajo del tope de 2 s. El nodo no consulta la red en sus revisiones (las velas las leen el Centro y el operador): 0 KB de red, por debajo del tope de 50 KB. Para medir en el teléfono mismo: `python3 -I medir_nodo.py` en `~/nodo`.

### Una consulta a Claude (estimada con los precios oficiales; sin clave no se pudo medir)

Precios de Opus 5.5 por millón de tokens: entrada 4 USD, escritura de caché de 1 h 8 USD (de 5 min, 5 USD), lectura de caché 0,20 USD, salida 20 USD (el pensamiento se cobra como salida). Tamaños: contexto unos 1.800 a 2.100 tokens; pedido con dos puntos, uno en contra y el vector del operador, unos 400 tokens (más el esquema); salida con esfuerzo bajo, unos 100 a 400 tokens.

| Caso | Costo por consulta |
|---|---|
| Con el contexto ya en caché (consultas a menos de 1 h una de otra) | unos 0,8 centavos de dólar (0,4 a 1,2) |
| Primera de la hora (escribe la caché de 1 h) | unos 2,4 centavos |
| Segundos | unos 4 a 10 s por la ruta directa; más por Tor |

| Consultas | Al día | Al mes |
|---|---|---|
| 20 al día, sueltas (cada una escribe la caché) | 0,48 USD | 14 USD |
| 100 al día, en rachas | 1 USD | 29 USD |
| 360 al día (15 por hora, todo el día) | 3 USD (hasta unos 6 si piensa más) | 90 USD (hasta unos 170) |

Lo más probable es la primera fila: «alto» (19 de 25) es raro (sección 7). Las cifras reales quedan en cada fila de `decisiones.jsonl` desde la primera consulta: compárelas con esta tabla la primera semana. Conviene fijar en la consola de Anthropic un límite de gasto mensual.

### ¿Esto o una rutina en la nube que decida por API?

Esto. Una rutina programada abre una sesión entera de Claude Code (contenedor, clon del repositorio, decenas de miles de tokens de instrucciones) por cada vez: del orden de 0,5 a 2 USD por corrida con Opus, no puede dispararse en segundos por cada punto, y desde la nube no se llega al teléfono (está en la red de la casa). La llamada directa desde el teléfono cuesta alrededor de un centavo, tarda segundos y no depende de GitHub ni de contenedores. La rutina sirve para construir y revisar, no para decidir cada punto.

## 6. Batería y calor del teléfono

- El nodo pasó de unos 160 ms de procesador cada 10 s a una media de 3,7 ms, y de leer 7,8 MB cada 10 s a leer solo lo nuevo. Corre con `nice -n 5`.
- `estado.json` del nodo se escribe solo si cambió (antes, cada 10 s): menos escrituras en la memoria del teléfono.
- Telegram y Claude solo con puntos altos, fallas que piden al dueño o cambios. Nada se consulta por la red en las revisiones del nodo.
- El laboratorio (600 formas) sigue en la caja; en el teléfono no corre nada pesado nuevo.
- Recomendado en el teléfono (lo hace el dueño o la sesión del PC): `termux-wake-lock` en el arranque y quitar a Termux de la optimización de batería de Android, para que Android no duerma los programas. Si Android los duerme igual, no se compra (falla cerrado): el operador no mira y el candado no encuentra decisiones vigentes.

## 7. Opinión, con cifras

1. **El Centro elige bien el sentido, pero no alcanza para el margen de Fable por sí solo.** A precio real de 0,544 hace falta acertar 55,5 % para no perder. A ciegas: E1 54,8 %, E2 55,6 %, E3 57,5 %. En vivo: E1 57 % (121 apuestas), E2 55,4 % (74). Con E1 al 57 % y precio 0,544 la ganancia esperada es +2,7 % por USDT; con su cifra a ciegas, −1,3 %. El operador exige +10 % prudente: con las probabilidades del Centro eso pide precios de 0,48 (E1), 0,49 (E2) o 0,51 (E3) o menos (q ≤ 0,98 × p / 1,10, bajado a 0,01). Al abrir la ventana el precio medio medido fue 0,544: casi nunca pasa.
2. **Dónde sí se complementan.** Cuando, después de la señal del Centro, el precio se va en contra de su sentido, ese lado se abarata y queda «perdedor»; el modelo de Fable puede encontrarle ganancia esperada prudente de 10 % o más. Esa es la compra que la combinación hace: el Centro y Claude ponen el sentido de devolución; el operador, el precio y el importe. Por eso el candado deja vivir la aprobación hasta 10 minutos dentro de su ventana.
3. **El umbral de 19 de 25 es casi todo azar.** Con un acierto real de 57 %, 19 o más de 25 salen por azar el 4 % del tiempo (con 55 %, el 2,6 %). No hay prueba de que una racha alta prediga la siguiente apuesta. Se mantiene porque es la orden del dueño y porque filtra cuántas consultas van a Claude; el contexto le dice a Claude que pese más el fondo, lo vivo y lo medido a ciegas que la racha. El medidor de la sección 8 dirá si los puntos altos aciertan más que todos los puntos.
4. **Para el operador, «aciertos» no es la medida.** Compra por precio: un lado a 0,20 que acierta 3 de 10 veces gana dinero. Su serie de 25 se lee distinto, y su juez R6 (300 compras, neto positivo con remuestreo, 14 días) sigue siendo lo que dice si sirve.
5. **Lo esperable.** Pocas compras reales: hace falta que coincidan una fuente alta, la aprobación de Claude y un precio mal puesto. Puede pasar días sin comprar, como Fable advirtió. Hoy no hay ventaja demostrada con precios reales: lo más probable si se arma antes de que el papel lo muestre es perder despacio por la comisión.
6. **Recomendación.** No armar hasta que, con una llave que lea, el medidor muestre la combinación (D) con neto positivo y mejor que cada fuente sola, con muestra grande (como R6: 300 compras de papel y 14 días). Mientras tanto Claude decide igual sobre los puntos altos y todo queda medido.

## 8. Cómo medir en papel la combinación frente a cada uno

`nodo/medir_combinacion.py`, en el teléfono: `python3 -I ~/nodo/medir_combinacion.py --dias 14`. Lee el registro del operador, `centro.json` y `decisiones.jsonl` y da, con el ganador oficial de cada mercado y el precio real de la mirada del operador (o 0,544 si no hay libro, y lo dice):

- A. cada estrategia del Centro sola (señales vivas alineadas con un mercado de 15 min);
- B. el operador solo (su papel, libro A);
- C. Claude solo (cada COMPRAR, comprado en la mirada siguiente);
- D. la combinación, lo que haría el real (el operador quiere comprar ese lado y hay un COMPRAR vigente), y cuántas compras paró el candado;
- E. las órdenes reales ya liquidadas.

Criterio: D debe acertar más que el equilibrio de su propio precio y ganar con muestra grande, y ganarle a A, B y C. Hasta que el operador tenga una llave que lea no hay libro: D queda vacía y A y C se miden con precio supuesto.

## 9. Lo que solo puede hacer el dueño

1. **GitHub.** La sesión de la nube no pudo subir esta rama (403: la cuenta de GitHub conectada a Claude lee el repositorio pero no escribe). En claude.ai/connect-github, conectar la cuenta dueña del repositorio o dar a la app Claude permiso de escritura (Contents) en Nico1091/trader-btc.
2. **Clave de la API de Claude.** En la consola de Anthropic (platform.claude.com), crear una clave de API y cargar saldo: la suscripción de claude.ai no paga la API. Fijar un límite de gasto mensual. Guardarla en el teléfono en `~/.config/binarias/claude` (una línea, permisos 600). En la caja solo si quiere que el respaldo también consulte.
3. **Llave de Binance del teléfono.** En la app de Binance, Gestión de API: una llave nueva solo para el teléfono, con Lectura y Predicción y nada más, restringida a la IP de la casa. Guardarla en el teléfono en `~/.config/binance/operar.txt` (`apiKey=…` y `secretKey=…`, una por línea). El operador la prueba solo, hace la prueba sin fondos y la manda a su Telegram. Si la IP de la casa cambia, Binance la rechaza (−2015) y el operador vuelve a medir sin precios y le avisa la IP nueva.
4. **Fondos.** Pasar a la billetera de predicción solo lo que esté dispuesto a arriesgar.
5. **Armar.** Escribir «operador armar» en su Telegram cuando el papel lo justifique (sección 7.6). Si el operador dice que no es apto y aun así quiere, «operador armar igual». «operador parar» desarma. Nunca armar el operador de la caja.

## 10. Riesgos, de frente

- No hay ventaja demostrada con precios reales.
- Claude cuesta dinero en cada punto alto y puede equivocarse; por eso solo puede impedir compras y lo demás lo deciden las reglas de Fable.
- La API de Claude puede rechazar salidas por Tor de países no admitidos; la ruta directa es la normal.
- Si el teléfono duerme, se apaga o pierde la red, no se compra; lo ya comprado se liquida solo en Binance y se cobra cuando el operador vuelva.
- El cobro por API sigue sin probar con dinero real.
