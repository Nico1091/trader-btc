# Prompt de revisión de binarias (18/11/2026)

Úselo cuando el dueño pida «revise que todo haya quedado perfectamente». Se ejecuta con hechos, no con suposiciones: cada
criterio dice cómo comprobarse. Nada de lo que se revisa compra, arma ni toca la cuenta de Binance. Si un criterio falla, se
corrige (o se le dice al dueño si es suyo) y se vuelve a comprobar antes de dar la revisión por buena. El resultado va a
REVISION-<fecha>.md y al bloc (AL FRENTE, ENCARGOS y BITÁCORA, con hora de Colombia).

Herramientas (en app-telefono\v2, corren dentro del teléfono por adb):
- revision.sh app      (run-as co.binarias.motor)  · revision.sh termux (run-as com.termux) · en la caja, revision.sh caja
- prueba_operador.sh 1 (prueba sin fondos: solo consulta y cotiza) · directo.sh (IP de salida y Telegram directo)
- comprobar_lectura.py (en /data/local/tmp/aprobador-18-11: el teléfono lee una decisión de la rutina en GitHub)

## A. Teléfono: la app Binarias (todo vive aquí)
1. Versión 3 instalada; motor dentro (python3.14 y python3), sin el programa de Tor.
2. Corren exactamente seis programas, uno de cada uno: centinela, avisos, centro, nodo, operador y publicador. Ningún Tor.
3. Los programas salen directo: AVISOS_TOR, NODO_TOR, OPERADOR_TOR y PG_TOR vacíos.
4. Llaves en .config: binance/operar.txt; binarias/telegram, nodo, rutina, github y llamada/; publicador-github/github,
   correo-usuario y correo-clave. Archivos 600, carpetas 700.
5. Inicio automático de HyperOS permitido (MIUIOP 10008 allow); fuera del ahorro de batería; RUN_ANY_IN_BACKGROUND allow.
6. El código de la app es idéntico al del PC (huellas) en centinela, nodo, operador y publicador.
7. Depuración por wifi apagada y sin puerto de adb abierto a la red.

## B. Termux del teléfono (solo respaldo)
1. Ningún programa de binarias corriendo y ningún Tor.
2. Arranque: 20-centinela.sh apartado (.en-la-app), 10-despertar-binarias.sh presente; arrancar.sh sin Tor.

## C. La caja (respaldo)
Desde el 18/11/2026 (16:31) el dueño la tiene desconectada y todo corre en el teléfono: no se revisa, no se busca en la red
y no se le pregunta por ella mientras él no diga que la volvió a conectar. Entonces:
1. Corren centinela, avisos y nodo, uno de cada uno; su operador con PARAR; ningún Tor; arrancar.sh sin Tor.
2. Su avisos.py y nodo.py iguales a los del PC.
3. Sin llave de Binance, sin token de la rutina y sin acceso de GitHub (tiene ADB abierto en la red).

## D. Cadena de decisión
1. Rutina aprobadora activa, con las instrucciones del 18/11 (comprar, vender o nada; solo la orden) y su token.
2. Nodo del teléfono: decisor «rutina», token y GitHub listos, umbral 19 de 25 con ganancias contados a mano (precio real
   del libro y ganador oficial: paridad\5-PROMPT-CONSOLIDACION.md).
3. El teléfono lee en GitHub una decisión real de la rutina.

## E. Operador y dinero real
1. La llave pasa en Binance; permisos: restringida por IP, sin retiros, transferencias, margen ni futuros.
2. Saldo de la billetera de predicción de al menos 12,50 USDT (2 USDT dentro del 16 %).
3. Estado 2 o 3; ARMADO solo por su orden o por su regla; regla ARMAR_AL_70 puesta; 2 USDT por orden; topes del 16 %,
   freno del día, 20 al día, una por mercado.
4. Un solo operador vivo en todos los equipos (el de la app).
5. La prueba sin fondos cotiza bien y no envía nada.

## F. Red
1. El teléfono sale con la IP de la casa y Telegram responde directo (getMe); la caja también, si está conectada.

## G. Pruebas en el PC
nodo 70, rutina 36, aprobación 57, regla del 70 % 16, paridad 9 y publicador 42, todas bien (desde el 18/11, tarde).

## H. Registro
Bloc (AL FRENTE y SIGUIENTE PASO coherentes con lo comprobado), memoria y GitHub (rama binarias/plan-v7-2026-11-04) al día.

## I. Higiene
Secretos en texto plano fuera de su lugar (Descargas, temporales del teléfono) se señalan al dueño; no se borran sin su sí.
