# Mesa de binarias · contexto y desarrollo

Versión del 04/11/2026, 19:40 (hora de Colombia). Manda `PLAN-TOTAL.md` v8, secciones 7b y 7c. Sin claves: la llave vive solo en el PC, en `~/.config/binance/lectura.txt`.

## Qué es

Pedido de Nicolás: que todo se reduzca a oprimir comprar o vender, conectado, y que el programa analice solo, sin IA. Opera las binarias «BTC Up or Down» de 15 min de Binance Wallet con Predict.fun, por la API oficial `/sapi/v1/w3w/wallet/prediction`. Los Contratos de Evento a 10 min no tienen API y siguen midiéndose aparte. No es trading común: es apuesta por tiempo, sube o baja al vencer. En Colombia no está regulado.

## Piezas

En el PC, carpeta `mesa/`, puerto 127.0.0.1:8795:
- `mesa.py`: motor y servidor; toda orden nace de un toque suyo y se revisa aquí.
- `reglas.py`: decide NO, ATENTO, ESPERE, COMPRE o VENDA. Funciones puras.
- `borrador.py`: papel en vivo con los precios reales del libro a los 5, 30 y 60 s, liquidado con el ganador oficial.
- `analista.py`: escribe el análisis y los precios que disparan la señal. Sin IA.
- `conexion.py`: Binance. Solo compra en predicción y cobra; no toca retiros, margen ni futuros.
- `mesa.html`: pantalla. Borrador a la izquierda, velas con cinco líneas, flechas, etiqueta COMPRA o VENDE, marcas + y − de tres velas, estocástico, RSI y botones.
- `abrir_mesa.pyw`: abre Chrome. Edge no sirve porque su blindaje lo redirige al Buscador.
- `prueba_mesa.py`: pruebas con Binance simulada.

En la caja T95H y el teléfono, carpeta `dispositivos/`, 24/7 y con arranque por Termux:Boot:
- `quince.py`, hilo de `avisos.py`: papel por velas, porcentaje de aciertos, voz, fotos de líneas, latido y aviso de detenciones. En el teléfono, página de lectura en 127.0.0.1:8796.
- `llamada.py`, solo en el teléfono: timbra con la app Llamada Claude v5, por el canal de alarma.
- `audio/`: notas de voz fijas.

## Reglas

- Porcentaje de aciertos: últimas 25 cerradas. 68 %: «se está aproximando». 75 %: «ya llegó», con llamada. Debajo de 75 % tras haberlo alcanzado: «no opere».
- Aviso COMPRE o VENDA: SÍ (borrador de hoy sumando, ningún SÍ perdido, interés abierto que no sube), 75 %, 25 cerradas con precio real, compra hasta 0,53 y menos de 75 s desde la señal.
- Botones: siempre disponibles por orden suya. Topes que no se saltan: doble toque, 16 % del saldo, una orden por mercado de 15 min y precio hasta 0,90. Ningún programa ni agente oprime por él.
- Jamás apalancamiento.

## Lo medido

- P19 (`cuant/c10_prediccion.py`): 15 min, entrada 60 s tarde, 56,0 % en 2024-sep 2026 (9.490 señales). En octubre de 2026, 52,3 %.
- P20 (`cuant/c11_fallas.py`): ningún filtro entra. Tras caer más de 1 % en una hora, SUBE acierta 53,1 %: se avisa, no se filtra.
- Comisión real: sale de las acciones. Fallar cuesta 1 justo y el equilibrio es precio / 0,98; a 0,51, 52,04 %.
- El libro cambia en segundos: a los 94 s de un mercado, «Up» ya valía 0,16. Sin borrador con precios reales no hay prueba de la ventaja.

## Estado al 04/11/2026, 19:40

Probado: cuenta de predicción creada, cotización desde spot, señal idéntica a `semaforo.py`, cinco líneas idénticas a la caja y a Pulso, voz y foto en Telegram real, llamada real contestada.

Primera orden real (06/11, 12:39, 2,31 USDT a 0,05): Binance la dejó en FAILED a los 15 ms, con 0 comprado y el saldo intacto. Desde el 06/11 la Mesa consulta cómo quedó cada orden en `/order/history` y solo dice «Comprada» si Binance confirma lo comprado. Causa sin probar: el pago desde spot o el precio de 0,05 con FOK; la cotización con `fundTransferAmount` da -9000 y con MPC exige saldo en la billetera de predicción.

Sin probar: una orden que Binance ejecute de verdad y el cobro (`batch-redeem`). Siguen en 0 las operaciones del borrador con precio real.

## Trampas

- Lo que hizo «detenerse» a los equipos: el teléfono se apagó por batería (`getprop sys.boot.reason`) y el resto fue silencio sin señales.
- La caja: bloqueo de reposo y Termux:Boot; quien crea archivos en su carpeta necesita 666 o carpetas 777.
- El avisador se reinicia matando `python3 -I avisos.py` con `run-as com.termux kill`; su vigía lo relanza a los 30 s.
- Al reiniciar la Mesa cambia su ficha: la ventana se recarga sola.
- Firma: `urlencode` con `quote`, no con `quote_plus`.
- `lectura.txt` trae el secreto primero; `conexion.py` distingue por la etiqueta.
- Parar la Mesa: crear `PARAR` en esta carpeta.
