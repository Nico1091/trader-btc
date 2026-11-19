# Laboratorio de binarias BTC/USDT con red neuronal propia en la T95H

## Contexto

Pedido del 11/11/2026, con la precisión dada al responder: emular todo el tiempo, en papel y en tiempo real, muchísimas formas de hacer binarias sobre BTC/USDT, las pasadas y las nuevas que propongan la red neuronal y la IA, con parámetros nuevos, para ver cuál rinde más; que los resultados lleguen al Telegram del dueño; que todo quede alojado donde siga solo y se mejore solo; y una IA muy pequeña en la T95H a la que el dueño le haga peticiones, sin calentar la caja. La aplicación del teléfono va después. El método pedido tiene tres piezas: un prompt que revisa los hooks, un prompt que organiza el prompt final y una lista con chulitos que vuelva al contexto cuando este se compacte.

Se reutiliza lo que ya funciona en `C:\Users\ni109\Ingresos\binarias-papel`:

- `mesa\centro.py`: E1 a E5 y su medición en papel (entrada 60 s tarde, empate = fallo, una apuesta a la vez).
- `motor\senales.py` (`todas`), `motor\patrones_std.py`, `seleccion.json` y `cuant\c12_estudio_06nov.py`: el banco de formas pasadas.
- `cuant\validacion.py`: `wilson`, `binomial_cola`, `benjamini_hochberg`, `acierto_maximo_por_azar`, `pbo_cscv`.
- `pruebas\t33_indice.py`: la neurona del 31/10 (55,6 % a 10 min con confianza de 0,56 o más, a ciegas en 2024-26), línea base de la red nueva.
- `dispositivos\avisos.py` (`enviar`, `enviar_archivo`, Tor) y `dispositivos\arrancar.sh` (arranque con vigía que relanza).
- `C:\Users\ni109\esp32-neurona\placa\red.py`: perceptrón multicapa escrito a mano, referencia de la red.
- `PROMPT-REVISION.md` y `PLAN-TOTAL.md` v8, secciones 2, 6 y 8.

## Revisión de hooks, hecha el 11/11/2026

✅ `C:\Users\ni109\.claude\settings.json` tiene hooks en cuatro eventos: `SessionStart` (cinco órdenes: sesiones e índice, buzón de n8n, encargos, recordatorio del bloc y Serena), `SessionEnd` (tres), `Stop` (la voz) y `PreToolUse` solo para `mcp__serena__.*`. Ninguno bloquea una herramienta.

✅ `C:\Windows\System32\.claude\settings.local.json` tiene 250 permisos concedidos, ninguna negación y ningún hook. No hay configuración administrada y `Ingresos\binarias-papel` no tiene carpeta `.claude`.

✅ Lo que negó órdenes en sesiones anteriores fue el clasificador del modo automático (`autoMode`), que se configura aparte de los hooks: crear arranques de Windows, cerrar otras sesiones, `powershell -ExecutionPolicy Bypass -File` y terminar procesos del teléfono. Este plan no usa ninguna de las cuatro.

✅ `C:\Users\ni109\.claude\scripts\recordatorio_encargo.py` calla cuando el origen es `compact`: después de compactar, la lista de avance no vuelve al contexto.

✅ Frenos que no dependen de Claude: el reloj de la caja está en el 02/03/2021 y por eso Binance y Tor le fallan por certificado; la ESP32-S3 tiene 90 KB de memoria libre; los Contratos de Evento no tienen API, de modo que el laboratorio mide y no apuesta.

Cambios, cada uno con respaldo previo y prueba en seco:

- H1, memoria tras compactar: `recordatorio_encargo.py` devuelve, cuando el origen es `compact`, el título, el «SIGUIENTE PASO» y las líneas ✅ y ⬜ del AL FRENTE más reciente del bloc. Respaldo `recordatorio_encargo.py.bak-20261111`.
- H2, candado de dinero: en `autoMode.soft_deny` de `settings.json`, `"$defaults"` más dos reglas: ninguna orden, compra, cobro o traslado con dinero real, y ningún cambio a `REAL_AUTORIZADO` ni copia de la llave fuera del PC, salvo orden expresa del dueño en ese momento. Respaldo `settings.json.bak-20261111`.
- H3, solo si el clasificador niega un paso aprobado aquí: regla en `autoMode.allow` (`"$defaults"` más una línea) que cubre copiar archivos a `/data/local/tmp/laboratorio` de la caja, arrancar y parar el laboratorio y poner su reloj en hora.
- H4, solo si la sesión en segundo plano rechaza escribir fuera de un worktree: `"bgIsolation": "none"` dentro de `worktree`.

Los hooks actuales (voz, memoria, índice, Serena, encargos) se conservan: la respuesta no pidió quitar ninguno.

## Decisiones, con el dato que las sostiene

Equipo: la caja T95H, dedicada a las binarias (centinela, avisador y laboratorio). Medido hoy por ADB: Android 10, procesador ARMv8 de 4 núcleos a 1,5 GHz en modo de 32 bits, 3,2 GB de memoria libres, 21 GB de disco, 50 °C en reposo, Python 3.14.8 con numpy 2.5.4 y sqlite 3.54.1. Una pasada de 200.000 muestras por una capa de 16 neuronas tarda 0,52 s. El historial de velas de 1 min desde 2020 ya está en la caja. La ESP32-S3 sigue con el acortador de noticias: con 90 KB libres no guarda historial ni entrena.

Muchísimas formas: hasta 1.000 en vivo a la vez, con rotación diaria. Evaluar una forma en el cierre de una vela cuesta microsegundos; el tope se confirma midiendo en la caja. Con tantas formas, la mejor de un rato corto suele serlo por suerte: el tablero ordena por el límite inferior de Wilson, que pesa el acierto y el número de señales, y cada cifra lleva su n.

IA en la T95H, en dos tiempos. Primero, sin instalar nada y sin calor: las dos redes propias y una lista cerrada de peticiones por Telegram que el laboratorio atiende. Después, como prueba medida: un modelo de lenguaje de menos de 0,6 GB con llama.cpp, que traduzca la petición escrita a esas órdenes y proponga fichas. La caja ya tiene clang y whisper.cpp; whisper la llevó a 77-87 °C con cuatro hilos, de modo que el modelo correría con un hilo y solo se enciende si cumple los límites del paso 12.

Telegram: tablero que se actualiza solo, resumen cada hora, parte diario a las 6:00 y avisos cuando una forma cambia de estado. La frecuencia se cambia con una petición.

Centinela de la caja: al recuperar el reloj arrancaría con el estado del 06/11 y podría dar un SÍ que el teléfono sabe perdido. Se detiene antes y vuelve cuando reciba el estado del teléfono.

Aprobar este plan da el sí a dos cosas que la norma de no instalar exige nombrar: compilar llama.cpp (código de terceros, licencia MIT, corre solo dentro de la caja) y bajar por Tor un modelo de menos de 0,6 GB. Ambas pertenecen al paso 12 y pueden tacharse sin afectar el resto.

## Prompt 1 · Revisión de hooks y frenos (`laboratorio\PROMPT-HOOKS.md`)

```text
PROMPT DE REVISIÓN DE HOOKS Y FRENOS
Se ejecuta antes de empezar cada fase del laboratorio y cada vez que una orden sea negada.

Actúa como revisor de la configuración de Claude Code de este equipo. Tu entrega es una lista
de frenos, cada uno con su arreglo exacto. No cambies nada sin el sí del dueño en ese momento.

1. Lee ~/.claude/settings.json, C:\Windows\System32\.claude\settings.local.json y cualquier
   .claude\settings*.json de la carpeta de trabajo. Anota, por evento, cada hook: orden, matcher,
   qué hace y si puede bloquear. Anota también permissions (allow, deny, ask, defaultMode),
   autoMode (allow, soft_deny, hard_deny, environment) y worktree.
2. Toma la lista de avance del bloc y escribe, por cada paso pendiente, las órdenes que exige:
   editar archivos, adb push, adb shell, settings put, curl, schtasks.
3. Clasifica cada orden: pasa; la frena un hook; la frena una regla deny o ask; la puede negar el
   clasificador del modo automático; la frena una norma del dueño guardada en memoria; la frena
   un límite externo (equipo, red, Binance).
4. Por cada freno escribe quién lo levanta, el cambio exacto (bloque JSON, línea del guion o norma
   que el dueño tendría que levantar) y la alternativa que no necesita cambio. Se prefiere la
   alternativa.
5. Antes de escribir en un archivo de configuración: copia nombre.bak-AAAAMMDD. Después: valida el
   JSON, prueba el hook en seco con su entrada por stdin (código de salida y texto) y di si hace
   falta abrir /hooks o reiniciar la sesión.
6. Los campos y eventos se comprueban contra la referencia de configuración vigente, no de memoria.
7. Si una orden es negada durante el trabajo: copia el texto de la negación, clasifícala según el
   punto 3, avisa al dueño con el cambio propuesto y sigue con lo que no dependa de ella. No se
   reintenta la misma orden con otra forma.
8. Nunca se levanta sin orden expresa del dueño en ese momento: dinero real, llaves, instalar
   programas fuera de lo aprobado, agentes y mirar la pantalla.

Salida: por cada paso, una línea «paso · freno · arreglo»; al final, los cambios aplicados con su
prueba y los que esperan el sí del dueño.
```

## Prompt 2 · Organizador del prompt final (`laboratorio\PROMPT-ORGANIZADOR.md`)

```text
PROMPT QUE GENERA EL PROMPT FINAL DEL LABORATORIO
Se pega completo en Claude; lo que devuelve es el PROMPT FINAL. Se vuelve a ejecutar cuando
cambien el plan, los criterios o lo construido.

Actúa como jefe de investigación de binarias sobre BTC/USDT. Tu entrega es un solo documento: el
PROMPT FINAL con el que otra sesión de Claude construirá y dejará corriendo el laboratorio. No
construyas nada ni analices el mercado ahora.

Lee antes, en este orden: Desktop\obsidian\Vault\03-Proyectos\Bloc de binarias - todo en uno.md (AL FRENTE más reciente y
ENCARGOS); Ingresos\binarias-papel\PLAN-TOTAL.md (secciones 2, 6, 7c, 7d y 8); PROMPT-REVISION.md;
mesa\centro.py; motor\senales.py; cuant\validacion.py; pruebas\t33_indice.py;
dispositivos\avisos.py y arrancar.sh; laboratorio\REVISION.md si existe.

El PROMPT FINAL lleva estas partes, en este orden:
1. Propósito, en dos frases, y lo que el laboratorio no hace.
2. Reglas que no se discuten, copiadas del plan y del bloc, sin ablandarlas.
3. Estado de partida: solo datos medidos, cada uno con su fecha.
4. Archivos que se crean y se tocan, una línea por archivo, con la función existente que reutiliza.
5. Formas pasadas, gramática de las nuevas y las dos redes, con los límites de cada parámetro.
6. Criterios escritos antes de ver resultados: tramos, tamaños mínimos, vallas, rotación y qué
   significa cada estado.
7. Lo que llega a Telegram y las peticiones que el dueño puede hacer, con un ejemplo marcado como
   ejemplo.
8. Orden de trabajo con casillas ⬜ y ✅, un paso por línea, cada uno con la prueba que lo cierra.
   Instrucción expresa: marcar el paso en el bloc en cuanto se cierre y actualizar «SIGUIENTE PASO».
9. Qué se exige para decir «listo», separado del veredicto sobre las formas.
10. Frenos: ante cualquier negación, ejecutar PROMPT-HOOKS.md.
11. Lo que queda para después.
12. Trato y redacción: de usted, sin el nombre del dueño, hora de Colombia, ninguna cifra sin su n,
    registro formal.

Si un dato no está en esos archivos, escríbelo como pendiente; no lo supongas. Si dos fuentes se
contradicen, manda el bloc y se anota la contradicción. Cuando exista REVISION.md, cada hallazgo
abierto se convierte en un paso de la parte 8.
```

## Prompt 3 · Prompt final, versión 1 (`laboratorio\PROMPT-FINAL.md`)

Es el resultado de aplicar el organizador a lo leído hoy. Se consolida tras la revisión del paso 3.

```text
PROMPT FINAL · Laboratorio de binarias BTC/USDT · versión 1 (11/11/2026)

1. PROPÓSITO
Construir y dejar corriendo en la caja T95H un programa que emule en papel y en tiempo real hasta
1.000 formas de hacer binarias sobre BTCUSDT, las pasadas y las que una red neuronal propia
proponga cada hora; que guarde cada prueba y cada señal en SQLite; que informe al Telegram del
dueño cuáles rinden más y atienda sus peticiones. No apuesta, no conoce llaves y no decide el
dinero real.

2. REGLAS QUE NO SE DISCUTEN
- Solo papel. Ningún archivo del laboratorio importa conexion.py, lee llaves ni escribe en la
  carpeta centinela; de ella solo lee el historial de velas. REAL_AUTORIZADO y semaforo.json no
  se tocan.
- Solo velas cerradas; entrada al cierre del minuto siguiente (60 s tarde); empate = fallo; una
  apuesta abierta por forma.
- Las formas a favor del movimiento se emulan para comparar. Por la regla 6.2 de PLAN-TOTAL, al
  protocolo de dinero solo pasan las de devolución.
- Biblioteca estándar y numpy, que ya están en la caja. Nada se instala ni se compila antes del
  paso 12.
- Binance directo; Telegram por Tor con avisos.enviar. Ninguna IA externa. Todo lo hace esta
  sesión, sin agentes ni flujos.
- Calor: un hilo y nice 10; la búsqueda y el entrenamiento se pausan a 70 °C y vuelven a 62 °C.
  Un argumento desconocido nunca lanza trabajo pesado.
- Mismo código en el PC y en la caja; sumas en bucle o con numpy (sum() cambia entre 3.11 y 3.14)
  y tiempos con dtype=np.int64.

3. ESTADO DE PARTIDA, MEDIDO EL 11/11/2026
- Caja: Android 10, ARMv8 de 4 núcleos a 1,5 GHz en 32 bits, 3,2 GB de memoria libres, 21 GB de
  disco, 50 °C en reposo; Python 3.14.8, numpy 2.5.4, sqlite 3.54.1; 0,52 s por pasada de 200.000
  muestras. Tiene clang y whisper.cpp; no tiene llama.cpp.
- Historial en la caja: 3.595.265 velas de 1 min, del 31/12/2019 a las 19:00 al 01/11/2026 a las
  12:04 (centinela/datos/BTCUSDT_um_1m_vivo.npy).
- Reloj de la caja en el 02/03/2021: Binance y Tor fallan por certificado. Último latido, 06/11 a
  las 21:39. El relevo le toca al teléfono, que no está por ADB: su estado de hoy queda sin
  comprobar.
- quince.py y arrancar.sh de la caja son los anteriores al 07/11.
- Referencia a 15 min, 2024-sep 2026: E1 54,6 %, E2 55,1 %, E3 57,7 %, E4 54,4 %, E5 51,8 %;
  equilibrio 52,04 %. A 10 min el equilibrio es 54,05 %.

4. ARCHIVOS (PC: Ingresos\binarias-papel\laboratorio; caja: /data/local/tmp/laboratorio, 777)
- base.py: SQLite en modo WAL. Tablas velas, formas, pruebas, senales, redes, eventos, peticiones
  y salida (cola de mensajes). Copia diaria; se guardan siete.
- rasgos.py: una sola función para historia y vivo. Los diez rasgos de t33_indice.py más distancia
  al máximo y al mínimo de 20 y 50 velas, Bollinger, RSI de 5 y 15 min, cuerpo de la vela y racha
  (19 entradas).
- formas.py: formas pasadas, gramática y generador (parte 5).
- red.py: las dos redes (parte 5), con numpy; esp32-neurona\placa\red.py como referencia.
- juez.py: pruebas a ciegas, vallas y rotación (parte 6) con cuant\validacion.py.
- emulador.py: papel en vivo con la medición de mesa\centro.py; resultado con futuros y con el
  índice de precio.
- partes.py: tablero, resumen, parte diario y avisos (parte 7).
- peticiones.py: lee el chat del dueño y atiende la lista cerrada (parte 7).
- laboratorio.py: ciclo, instancia única, PARAR, guardia de calor y guardia de reloj.
- prueba_laboratorio.py y probar.sh: paridad, fuga de futuro, candado y prueba en seco.
- herramientas\traer_laboratorio.py: copia la base al PC cuando está encendido.
- Se tocan: dispositivos\arrancar.sh (una línea que llama al arranque del laboratorio y la espera
  ESPERA_ESTADO), herramientas\estado.py (edad del latido con el reloj del PC), PLAN-TOTAL.md
  (sección 7d), PROMPT-REVISION.md (sección 11) y el bloc.

5. FORMAS Y REDES
- Una forma es un disparo, sus filtros, un sentido (al revés o a favor) y un plazo de 10 o 15 min.
  Guarda su origen: pasada, red, azar, dueño o IA.
- Formas pasadas, fijas y con su regla original: E1 a E5 de mesa\centro.py; el banco de
  motor\senales.py y motor\patrones_std.py con las configuraciones de seleccion.json; las
  variantes de cuant\c12_estudio_06nov.py; la neurona de t33.
- Disparos de las nuevas: ruptura de N velas de 5 min (N de 10 a 120); cierre fuera de Bollinger
  (ventana de 10 a 60, ancho de 1,5 a 3,0); RSI de 5 o 15 min sobre U o bajo 100 − U (U de 65 a
  85); rendimiento de m minutos mayor que z volatilidades (m de 5 a 60, z de 1,0 a 3,5); posición
  en el rango de H horas (H de 1 a 24) más allá del cuantil q (de 0,85 a 0,98); y la red sola. Se
  admiten dos disparos a la vez.
- Filtros: interés abierto que no sube (0,022 %, fijo), franja horaria, volatilidad 15/240 y
  confianza de la red de mercado (de 0,52 a 0,62) a favor de la apuesta.
- Red de mercado: perceptrón de 19 entradas, 16 y 8 neuronas con tanh y salida sigmoide; una por
  plazo. Aprende con 2021-2023; de 2024 en adelante, cada mes lo predice una red ajustada solo con
  datos anteriores, con purga de un plazo. Se reajusta cada día a las 00:30. Línea base: la
  neurona de t33; si la red no la supera en 0,3 puntos en el tramo de elección, se usa la neurona
  y se informa.
- Red de búsqueda: recibe la ficha codificada y predice su margen sobre el equilibrio. Cada hora
  ordena 2.000 fichas al azar y manda a prueba las 40 mejores (origen «red») y 10 al azar (origen
  «azar», que mide si la red de búsqueda aporta). Aprende de todas las pruebas guardadas.

6. CRITERIOS, ESCRITOS ANTES DE VER RESULTADOS
- Tramos: aprende 2021-2023; elige ene-2024 a jun-2025; juzga jul-2025 a oct-2026; después, vivo.
- La ficha se guarda con su huella antes de probarse. Ningún parámetro cambia después: un cambio
  es otra forma.
- Entra a vivo la forma nueva que pasa «elige»: 300 señales o más, Wilson inferior al 95 % sobre
  el equilibrio y Benjamini-Hochberg con q = 0,05 en su tanda. Su cifra de «juzga» se calcula una
  sola vez al entrar y se muestra como «a ciegas». Las pasadas entran todas.
- En vivo, hasta 1.000 formas. El tope se confirma en el paso 6: el ciclo de cada vela de 5 min
  cierra en menos de 20 s y la caja no pasa de 62 °C.
- Estados: «en observación» hasta 100 cerradas; «prometedora» con 100 o más y 1 punto sobre el
  equilibrio; «apta en papel» con 300 o más, Wilson inferior sobre el equilibrio y «juzga» 1 punto
  o más sobre el equilibrio; «descartada» con 100 o más y Wilson superior bajo el equilibrio, o
  30 días sin llegar a 100.
- Rotación diaria: salen las descartadas y entran las admitidas del día. Las pasadas no rotan.
- El tablero ordena por Wilson inferior en vivo. El parte diario trae el acierto que el azar solo
  le daría a la mejor de N formas con ese n (acierto_maximo_por_azar) y el rendimiento por origen.
- «Apta en papel» no autoriza dinero: la forma pasa al protocolo de la sección 6 y a la orden del
  dueño.
- Cada cifra se informa a pagos de 0,80, 0,85 y 0,90 (10 min) y a compra de 0,50, 0,51 y 0,53
  (15 min).

7. TELEGRAM Y PETICIONES (texto directo, por el bot de siempre, con el prefijo «Laboratorio»)
- Tablero: un mensaje que se edita cada 5 min con las diez mejores formas en vivo.
- Resumen cada hora: las tres mejores de la hora y de hoy, con su neto.
- Parte diario a las 6:00: formas nacidas, probadas, admitidas y descartadas; resultados en vivo;
  rendimiento por origen; estado de las redes; horas de marcha, temperatura máxima y pausas.
- Aviso aparte, uno por hora como máximo: forma que queda prometedora, apta o descartada;
  laboratorio detenido o de vuelta; reloj mal; calor.
- Peticiones, solo desde el chat del dueño y con lista cerrada: mejores [hoy|semana|todo];
  forma F-n; estado; origen; pausa; sigue; tope N; cada N (minutos del resumen); probar <disparo,
  parámetros, sentido, plazo>. La caja mira el chat cada 20 s sin consumir los mensajes
  (getUpdates sin offset) y anota la petición y la respuesta.
- Ejemplo de formato, con cifras inventadas:
    Laboratorio · 11/11 14:35 · 640 formas en vivo · caja 52 °C
    1. F-0142 · red · 15 min al revés · 31 de 52 (59,6 %) · últimas 25: 16 · a ciegas 55,8 % en 1.940
    2. F-0002 · pasada · 15 min al revés · 12 de 21 (57,1 %) · a ciegas 55,1 % en 10.244
    Hoy: 1.200 formas nuevas, 31 entraron a vivo, 12 descartadas. Es papel.

8. ORDEN DE TRABAJO (marcar en el bloc al cerrar cada paso)
⬜ 0. Hooks: aplicar H1 y H2 con respaldo y prueba en seco.
⬜ 1. Caja: detener su centinela con ESPERA_ESTADO; reloj en hora con settings put global
      ntp_server o cmd alarm set-time, comprobado con date; quince.py y arrancar.sh nuevos con su
      huella; el centinela vuelve cuando reciba el estado del teléfono (pide el teléfono por USB).
⬜ 2. Escribir PROMPT-HOOKS.md, PROMPT-ORGANIZADOR.md y PROMPT-FINAL.md; sección 7d en
      PLAN-TOTAL.md; AL FRENTE y ENCARGOS en el bloc.
⬜ 3. Aplicar PROMPT-REVISION.md al plan y a este prompt; hallazgos en laboratorio\REVISION.md;
      consolidar.
⬜ 4. Construir en el PC base, rasgos, formas, juez, red, emulador, partes, peticiones y
      laboratorio.
⬜ 5. Probar en el PC: E1 a E5 idénticas a centro.py en 40 días y las demás pasadas idénticas a
      su código de origen; ninguna señal anterior a T cambia al recortar el historial en T;
      candado; 30 min en seco con datos en vivo y sin Telegram.
⬜ 6. Primera construcción de rasgos y redes en el PC; llevar todo a la caja con huellas; paridad
      PC-caja; medir el tope de formas; 30 min en seco en la caja.
⬜ 7. Arranque: línea en arrancar.sh, lanzado desde Termux para que tome el bloqueo de reposo;
      reinicio de prueba.
⬜ 8. Telegram: tablero, resumen, primer parte real, un aviso de prueba y cada petición de la
      lista, confirmados por el dueño en su teléfono.
⬜ 9. 48 horas de marcha; auditoría de un día de señales contra las velas oficiales.
⬜ 10. Revisión final contra lo construido; ajustar este prompt; informe.
⬜ 11. Consolidar: bloc, PLAN-TOTAL.md, memoria, bóveda, GitHub con sincronizar_repo.py y USB.
⬜ 12. IA pequeña en la caja: compilar llama.cpp con dos hilos y guardia de calor; bajar por Tor
      un modelo de menos de 0,6 GB de su fuente oficial; medir. Se enciende solo si, con un hilo,
      la caja no pasa de 62 °C, responde en 60 s o menos y traduce bien 45 de 50 peticiones de
      prueba a la lista cerrada. Encendida, propone fichas con origen «IA». Si no cumple, queda
      apagada y se informa con las medidas.

9. «LISTO»
Se dice solo con los pasos 5, 6, 8 y 9 cumplidos y sin preguntas de la revisión «sin comprobar».
El informe separa lo que corre del veredicto sobre las formas y del resultado del paso 12. Con
57 % de acierto real, una forma necesita unas 400 señales en vivo para quedar apta; con 55,5 %,
unas 800.

10. FRENOS
Ante cualquier negación, ejecutar PROMPT-HOOKS.md y avisar al dueño con el cambio exacto.

11. DESPUÉS
El tablero dentro de la aplicación del teléfono y una página en el Centro del PC.

12. TRATO
De usted, sin el nombre del dueño, también en Telegram. Hora de Colombia. Ninguna cifra sin su n.
```

## Lista de avance

✅ Hooks y permisos leídos.
✅ Caja medida por ADB: equipo, Python, historial, herramientas de compilar y causa de la ceguera.
✅ Placa medida.
✅ Código reutilizable y banco de formas pasadas localizados.
✅ Plan y tres prompts redactados; foco confirmado por el dueño.
⬜ Pasos 0 a 12 de la parte 8 del prompt final. La lista vive en el AL FRENTE del bloc; el hook H1 la devuelve tras cada compactación y el de inicio muestra el «SIGUIENTE PASO».

## Archivos fuera de la carpeta del laboratorio

- `C:\Users\ni109\.claude\scripts\recordatorio_encargo.py` (H1) y `C:\Users\ni109\.claude\settings.json` (H2; H3 y H4 solo si hacen falta).
- `C:\Users\ni109\Desktop\obsidian\Vault\03-Proyectos\Bloc de binarias - todo en uno.md`: AL FRENTE del 11/11 con la lista, ENCARGOS y BITÁCORA.
- `C:\Users\ni109\Ingresos\binarias-papel\PLAN-TOTAL.md` (7d), `PROMPT-REVISION.md` (11), `dispositivos\arrancar.sh`, `herramientas\estado.py`, `herramientas\traer_laboratorio.py`.
- En la caja: `/data/local/tmp/laboratorio/` (nueva), `/data/local/tmp/centinela/quince.py` y `arrancar.sh` (pendientes del 07/11) y el ajuste del servidor de hora.

## Verificación

- Hooks: `echo {"source":"compact"} | python recordatorio_encargo.py` imprime la lista; `settings.json` se valida como JSON y se comprueba la regla nueva.
- PC: `python -I laboratorio\prueba_laboratorio.py` informa paridad con `centro.py` y con el banco en 40 días, fuga de futuro y candado.
- Caja: `sh /data/local/tmp/laboratorio/probar.sh` desde Termux; `ps` muestra `python3 -I laboratorio.py`; `date` da la hora de Colombia; `python3 -I base.py --resumen` cuenta formas, pruebas y señales.
- Telegram: el tablero cambia de hora cada 5 min, el resumen llega cada hora y el parte a las 6:00; cada petición de la lista devuelve su respuesta. El dueño lo confirma en su teléfono.
- 48 horas: la tabla `eventos` no trae caídas sin relanzar, la temperatura del trabajo pesado queda bajo 70 °C y un día de señales coincide con las velas oficiales de Binance.
- Paso 12: tabla de temperatura, segundos por petición y aciertos de traducción en 50 peticiones de prueba.
