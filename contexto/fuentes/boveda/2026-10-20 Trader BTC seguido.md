---
tags:
  - area/cripto
  - tipo/sesion
creado: 2026-10-20
estado: activo
---

# 2026-10-20 Trader BTC seguido

Proyecto: [[Trader BTC seguido]].

## Qué pidió

Retomar el trading y terminarlo, sin crear agentes. A mitad de la sesión corrigió el rumbo: «lo que te dije es que hicieras trading seguido, no en días». Su pedido literal del 19/10 (índice semántico, turno 35298) hablaba de operaciones «cada rato», «en poco tiempo», con pausas cada 100 a 800 ciclos.

## Qué se hizo

- Se descargaron las velas de 1 s de BTCUSDT y BTC/FDUSD de mayo al 19 de octubre: 344 archivos y 14,86 millones de segundos, verificados con SHA-256 y sin huecos. Por Tor tardaban unas 10 horas porque todos los circuitos comparten el puente del Buscador; por la red directa, que su regla permite hacia Binance, tardaron 3 minutos.
- Se escribió el núcleo nuevo: rasgos de segundos a días con una sola definición para el banco y el agente, la probabilidad propia (logística sin librerías, con calibración) y la regla de entrada por ganancia esperada neta de comisiones.
- Primer error propio, detectado y corregido: con barreras fijas el 80-91 % de los ciclos terminaban por tiempo, y el modelo aprendía volatilidad en vez de dirección. Se separó en dos probabilidades (movimiento y dirección), con barreras que se ajustan a la volatilidad.
- Se construyó el agente en vivo (`agente.py`) con flujos de Binance, contexto por Tor, libros en papel, frenos 3/15/20 %, tandas, auditor de llenados y panel local.
- Paridad: 587 ciclos idénticos entre el banco y el código real del agente, y 3.236 velas de 1 minuto iguales a las de Binance.
- Segundo error propio, detectado en vivo: lanzado sin ventana, el agente se atrasaba hasta 2 minutos. Se midió la causa: la API de Binance tardaba hasta 13 s y se llamaba dentro del ciclo por segundo, Windows 11 frenaba el proceso oculto, y el libro de BTCUSDT mandaba cientos de mensajes por segundo. Arreglado: hilo de fondo para la API, libro por fotos de 1 s y una llamada de sistema que quita el freno. Retraso final de 1 a 2 s.

## Hallazgos

- Operar seguido pierde por comisiones en contado, BTC/FDUSD y futuros; el testigo sin filtro perdió −16,9 % en 100 ciclos del tramo final, casi lo mismo que entrar al azar.
- La probabilidad de que suba nunca llegó a 85 % en el tramo final (máximo 0,80).
- Las rutas antiguas del WebSocket de futuros (`/ws`, `/stream`) aceptan la conexión pero ya no mandan datos; las nuevas son `/market` y `/public`.
- La agenda de Trump se mudó de factba.se a rollcall.com/factbase; el CSV de `media-cdn.factba.se` responde por Tor.
- El reloj del portátil se desfasa varios segundos frente a Binance: el agente usa la hora de cada vela.

## Después: 40.000 pesos y que siga moviéndose

Nicolás pidió seguir probando aquí («luego usaremos un plugin o lo adaptaremos para enviar las operaciones en la nube») y luego: «pon el agente a hacer pruebas suponiendo que empiezas operando con 40k pesos colombianos y déjalo ahí moviéndose por lo menos hasta que yo te diga».

- La tasa real de Binance P2P para comprar USDT con 40.000 pesos fue de 3.177,85 COP por USDT (mediana de 20 avisos), así que cada libro empieza con 12,59 USDT y no con los 9,7 del 19/10, que venían de una tasa vieja. Ir y volver por P2P cuesta cerca del 1 %.
- Banco y modelos rehechos con ese capital: la conclusión no cambia (seguido pierde en todos los instrumentos).
- Probado en vivo: pausa, corte de golpe con un ciclo abierto (al volver lo cierra con «REINICIO»), arranque y parada con los accesos. Pruebas automáticas nuevas de huecos, apagones, estado guardado y frenos de calendario y agenda de Trump: 39 en verde.
- Arranque con Windows puesto (con accesos para quitarlo y ponerlo) y candado de una sola instancia. Corre desde las 21:05.
- Para la nube: Binance bloquea las conexiones desde EE. UU. (error 451), también desde servidores en la nube de esa región.

## Pendiente

Sumar la MEZCLA de 1 hora como libro aparte, decidir cómo irá a la nube y la clave de la red de pruebas. El agente no se detiene hasta que él lo diga.
