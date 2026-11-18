# Aprobador de binarias · avance

Rama `claude/aprobador-binarias-2026-11-17`, salida de `binarias/plan-v7-2026-11-04` en 7429f90. La rutina constructora corre el 17/11/2026 a las 12:42 y a las 17:42 (hora de Colombia). El plan, la opinión y los costos están en `PLAN-APROBADOR.md`.

## Marca de trabajo

- Sesión de las 12:42: TERMINADA el 17/11 a las 13:30 (ver `TERMINADO.md`). Si usted es la corrida de las 17:42 y ve esta rama con `TERMINADO.md`, termine en una línea, sin escribir a Telegram.

## Pasos

- [x] 1. Leído el bloc (AL FRENTE del 17/11, secciones 5 y 6), el nodo, el operador de Fable 5.2, el Centro, el vigía y las reglas. Llamada a Claude revisada contra la documentación oficial (API de mensajes, precios y caché).
- [x] 2. Candado del operador (`operador/aprobacion.py` y una línea en `ejecutor.py`). Pruebas con el simulador de Fable: 36 de 36 en 3.11 y 3.13; el código de 7429f90 frente al nuevo con aprobación da las mismas órdenes, registro y saldo.
- [x] 3. Nodo: lectura incremental, mercado y ventana por punto, vector del operador en el paquete, puntos en contra, llamada a Claude revisada (salida JSON forzada, caché de 1 h, esfuerzo bajo, costo), fallas cerradas. 65 de 65 pruebas en 3.11 y 3.13, también contra un servidor falso de la API de mensajes con curl de verdad.
- [x] 4. `nodo/CONTEXTO-NODO.md` con lo esencial del bloc y de las reglas de Fable (unos 1.900 tokens, en caché).
- [x] 5. Medición en papel de la combinación frente a cada fuente sola: `nodo/medir_combinacion.py` (va con el nodo porque lee los archivos del teléfono).
- [x] 6. Costos: una revisión del nodo medida (`nodo/medir_nodo.py`); una consulta a Claude estimada con los precios oficiales (sin clave no se pudo medir; el nodo anota el uso real de cada consulta).
- [x] 7. `PLAN-APROBADOR.md`.
- [x] 8. Informe a Telegram (texto) y `TERMINADO.md`. Subir la rama a GitHub: BLOQUEADO (403, ver abajo); resuelto a las 15:47 con /web-setup.
- [x] 9. Llevado por la sesión del PC (17/11): teléfono a las 18:10 (nodo central y candado del operador) y caja a las 18:12 (solo el nodo; su operador sigue con PARAR). Detalle abajo, en «Llevado al teléfono y a la caja».
- [x] 10. Sin claves de la API (orden del dueño, 17/11, 18:30: «no tengo plata»): el que decide es la rutina aprobadora `trig_01Ep7i969sChfFw4Mb3eN4qM` (repo privado `Nico1091/binarias-aprobador`, creada a las 16:29). Detalle abajo, en «Decisor rutina».

## Decisor rutina y la ganancia antes que el acierto (17/11/2026, 19:00)

- Orden del dueño (18:40): el teléfono junta los puntos del Centro y del operador y se los manda directo a la rutina; antes se revisa que el acierto vaya con ganancias y no con pérdidas («la idea es siempre ganar»); si la rutina aprueba, se compra solo.
- `nodo.py`: cada estrategia lleva el neto de sus últimas 25 al precio que se paga (el del libro del operador; sin libro, 0,544), su precio medio y su acierto de equilibrio (precio / 0,98). Un punto es alto solo con 19 de 25 o más Y con ganancias. Con `"decisor": "rutina"` en `config.json`, los grupos listos van en un solo disparo a `/fire` de la rutina (token en `~/.config/binarias/rutina`, tope de 25 por hora) y la decisión se lee en `decisiones/<id>.json` de binarias-aprobador (acceso de GitHub en `~/.config/binarias/github`); se anota igual que antes en `decisiones.jsonl`, donde la lee el candado. El id lleva la hora del disparo y cuatro letras al azar. Sin token, sin acceso, sin respuesta en 6 min, ventana cerrada, decisión ilegible o del otro sentido: no se compra.
- `CONTEXTO-NODO.md` (y `CONTEXTO.md` de binarias-aprobador, idénticos, commit b2c6d71): la regla de la ganancia al frente del criterio.
- Pruebas: `nodo/prueba_rutina.py` 27 de 27 (rutina y GitHub falsos en 127.0.0.1, el candado de verdad) y `prueba_nodo.py` 65 de 65, en el PC (3.11), el teléfono y la caja (3.14.8). Instalado en el teléfono y la caja a las 19:00 con `aprobador/rutina.sh` (copias `.antes-rutina-17-11`; `rutina.sh volver` deshace).
- Ruta directa por orden del dueño (18:20): `"rutas_claude": ["directa"]` (`aprobador/ruta_directa.sh`).
- Falta, del dueño: el token de disparo de la rutina (claude.ai, «Generate token»; gasta su plan, no dinero) y el acceso de GitHub del teléfono para leer las decisiones (copiar la credencial del PC necesita su autorización expresa). Mientras falten, el nodo no compra.

## Llevado al teléfono y a la caja (17/11/2026, sesión del PC)

- Antes de tocar lo que corría, las pruebas en una carpeta aparte de cada equipo (Python 3.14.8): `prueba_nodo.py` 65 de 65 y `prueba_aprobacion.py --antes` 36 de 36 contra el operador que corría (huellas de 7429f90). Guion: `probar.sh`.
- La primera corrida del nodo en el teléfono falló («señal nueva con 20 de 25»): `Fuentes._resumenes` daba por igual un archivo con la misma hora y el mismo tamaño, y en el teléfono dos escrituras seguidas comparten el tic del reloj del núcleo (189 de 200 pares medidos; el inodo cambia siempre, porque el Centro y el vigía reescriben con `os.replace`). Corregido: la marca es `(st_ino, st_mtime_ns, st_size)`. Tres corridas más, 65 de 65; en la marcha real el Centro escribe una vez por minuto, así que no se perdían señales, pero la prueba quedaba a la suerte. Huella nueva de `nodo/nodo.py`: 6912c5435be5f4b6 (la tabla de abajo dice a4f578e3f59a3f7f, la de antes de la corrección).
- Pasos 1 a 7 con `instalar.sh` (copiar, arrancar, comprobar): parados en 3 s; copias `.antes-aprobador-17-11`; 8 de 8 huellas; «nodo arrancó: rol telefono (central) … Claude claude-opus-5-5 (esfuerzo low, rutas directa, tor)»; el operador sigue en el estado 1 («Real: desarmado y sin órdenes»). Centinela, Centro, avisos y publicador sin tocar.
- Paso 8 (`medir_nodo.py` en el teléfono): primera vuelta 177 ms; vuelta sin cambios 0,1 ms y 0 KB leídos; con el Centro reescrito 77 ms; con miradas nuevas del operador 0,5 ms; promedio 12,8 ms de procesador por revisión, unos 110 s al día.
- Paso 9 (caja): las mismas pruebas, 65 de 65 y 36 de 36; nodo nuevo con 5 de 5 huellas, «rol caja (respaldo)». Latido del teléfono comprobado tras el reinicio de la caja (no hace de central).
- Para volver atrás en cada equipo: `run-as com.termux sh /data/local/tmp/aprobador-17-11/instalar.sh volver` (en la caja, con `/data/local/tmp` al final).
- Hallazgo 6 (se suma a los de abajo): con la clave puesta, el nodo llamará a Claude primero directo, con la IP de la casa, y por Tor solo si no conecta. El dueño tiene la regla de no exponer su IP; si lo quiere solo por Tor, basta `"rutas_claude": ["tor"]` en `config.json` del nodo (Anthropic puede rechazar algunas salidas de Tor). Lo decide él.

## Bloqueo: GitHub no deja escribir

A las 12:55 del 17/11 el push de la rama respondió 403 y crear la rama por la API respondió 404: la cuenta de GitHub conectada a Claude puede leer `Nico1091/trader-btc` pero no escribir. Se avisó al dueño por Telegram y por notificación a las 13:00; a las 13:20 seguía igual. Solo él puede arreglarlo: en claude.ai/connect-github conectar la cuenta dueña del repositorio o dar a la app Claude permiso de escritura (Contents) sobre el repositorio.

El 403 lo responde GitHub mismo (trae su identificador de petición), no el proxy de la sesión. Mientras no se arregle, la rama vive solo en la sesión de la nube de las 12:42, que reintenta el push sola hasta las 17:15. Se preparó también un parche de git que se aplica limpio sobre 7429f90 y deja el mismo árbol, pero no se envió por Telegram: el dueño pidió nada de archivos allí.

## Pasos exactos para que la sesión del PC lo suba al teléfono

Archivos de la rama y su huella (primeros 16 caracteres de sha256):

| Archivo de la rama | Va a | Huella |
|---|---|---|
| `binarias/operador/aprobacion.py` (nuevo) | `~/operador/aprobacion.py` | 581538e3829064eb |
| `binarias/operador/ejecutor.py` (una línea nueva) | `~/operador/ejecutor.py` | 0b5448b9bbbea250 |
| `binarias/operador/prueba_aprobacion.py` (nuevo) | `~/operador/prueba_aprobacion.py` | 3b7dfb28360a0110 |
| `binarias/nodo/nodo.py` | `~/nodo/nodo.py` | a4f578e3f59a3f7f |
| `binarias/nodo/CONTEXTO-NODO.md` | `~/nodo/CONTEXTO-NODO.md` | eb81f9ce4a688c3a |
| `binarias/nodo/prueba_nodo.py` | `~/nodo/prueba_nodo.py` | 4d7b7176642ec21b |
| `binarias/nodo/medir_combinacion.py` (nuevo) | `~/nodo/medir_combinacion.py` | 623ada75069a849c |
| `binarias/nodo/medir_nodo.py` (nuevo) | `~/nodo/medir_nodo.py` | 9ad3761cfcb1d5ee |

En el teléfono (Termux), en este orden:

1. Parar el nodo y el operador: `touch ~/nodo/PARAR ~/operador/PARAR` y esperar a que `pgrep -f "python3 -I nodo.py"` y `pgrep -f "python3 -I operador.py"` no muestren nada (hasta un minuto).
2. Copia de lo que corre: `cp ~/nodo/nodo.py ~/nodo/nodo.py.antes-aprobador-17-11`, `cp ~/nodo/CONTEXTO-NODO.md ~/nodo/CONTEXTO-NODO.md.antes-aprobador-17-11`, `cp ~/nodo/prueba_nodo.py ~/nodo/prueba_nodo.py.antes-aprobador-17-11` y `cp ~/operador/ejecutor.py ~/operador/ejecutor.py.antes-aprobador-17-11`.
3. Copiar los archivos de la tabla. Importante: `aprobacion.py` y `ejecutor.py` van juntos; `ejecutor.py` solo no arranca (le falta el candado) y el operador quedaría caído, sin papel.
4. Comparar huellas: `sha256sum ~/operador/aprobacion.py ~/operador/ejecutor.py ~/nodo/*.py ~/nodo/CONTEXTO-NODO.md` contra la rama.
5. Pruebas en el teléfono: `cd ~/nodo && python3 -I prueba_nodo.py` (65 de 65; usa curl y los puertos 18801 y 18802 de 127.0.0.1) y `cd ~/operador && python3 -I prueba_aprobacion.py` (32 de 32; con `--antes CARPETA` y una copia del operador de 7429f90, 36 de 36). Necesita `simulador.py` en `~/operador` (es de Fable y está en la rama).
6. Arrancar: `sh ~/nodo/arrancar_nodo.sh` (borra su PARAR solo) y `rm -f ~/operador/PARAR && sh ~/operador/arrancar_operador.sh`.
7. Comprobar: `tail -3 ~/nodo/nodo.log` debe decir «nodo arrancó: rol telefono (central) … Claude claude-opus-5-5 (esfuerzo low, rutas directa, tor)»; `python3 -I ~/operador/operador.py estado` debe seguir en el estado 1 sin errores.
8. Medir en el teléfono mismo: `python3 -I ~/nodo/medir_nodo.py` y anotar las cifras en el bloc.
9. En la caja (respaldo): copiar los mismos archivos del nodo a `/data/local/tmp/nodo/` y reiniciarlo igual. Su operador sigue con PARAR: NO borrarlo. Si algún día se quita, copiar antes `aprobacion.py` y `ejecutor.py` también allí. Nunca dos operadores armados.
10. Anotar en el bloc un AL FRENTE con esto (esta rutina no tocó el bloc, porque la copia que manda es la del PC).

Para volver atrás: parar, copiar de vuelta los `.antes-aprobador-17-11` y arrancar.

## Lo que solo puede hacer el dueño

GitHub (arriba), la clave de la API de Claude con saldo y límite de gasto, la llave de Binance propia del teléfono (Lectura y Predicción, IP de la casa), fondos en la billetera de predicción y «operador armar». Detalle en `PLAN-APROBADOR.md`, sección 9.

## Hallazgos (anotados sin corregir el código de Fable 5.2)

1. En la rama no están `operador/prueba_operador.py` ni `operador/llevar_operador.py`, que el plan de Fable nombra (sección 9). Sus pruebas propias no se pudieron correr; se usaron su simulador (`operador/simulador.py`) y pruebas nuevas, incluida la comparación con su código original. Si la sesión del PC las tiene, conviene subirlas a la rama y correrlas con el `ejecutor.py` nuevo.
2. `operador/nucleo.py` suma flotantes con `sum()` (rasgos y `sigma60`). Desde Python 3.12 `sum()` de flotantes compensa el redondeo, así que el teléfono (3.14) y un equipo con 3.11 pueden diferir en la última cifra (del orden de 1e-16). No cambia decisiones ni la paridad de 1e-9 de su criterio 1, pero una auditoría bit a bit entre equipos con versiones distintas podría ver diferencias mínimas. No se tocó.
3. Las pruebas del comprador (`comprador/prueba_comprador.py`) piden numpy por `laboratorio/perdida_red.py`; aquí no hay numpy (y no se agregan dependencias), así que no corrieron. El comprador no se tocó.
4. Fuera del código de Fable: curl se salta Tor sin avisar si el equipo tiene una lista de excepciones de proxy (`no_proxy`) que incluya el destino. Se corrigió en el nodo (`--noproxy ""` en la ruta de Tor y en su Telegram). `avisos.py`, `centro_tel.py` y `operador/mensajes.py` usan Tor igual que antes; en el teléfono no hay `no_proxy`, así que hoy no pasa, pero conviene saberlo.
5. `puntos.jsonl` y `decisiones.jsonl` del nodo crecen sin límite (unos 150 KB al día entre los dos): sin prisa, rotarlos cada mes.
