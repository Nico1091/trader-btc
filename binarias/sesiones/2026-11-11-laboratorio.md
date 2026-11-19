---
tags: [binarias, sesion, laboratorio]
creado: 2026-11-11
estado: en-curso
---

# Binarias: laboratorio de formas con red neuronal en la caja

Sesión desde las 19:36 de Colombia. Pedido: ejecutar el plan del laboratorio aprobado a las 11:39 (la sesión de la mañana se cortó por el límite de uso antes de empezar). Lo hice yo directamente, sin agentes ni flujos, como manda la norma del 22/10 aunque ultracode estuviera encendido.

**Qué es.** Un programa en la caja T95H que emula en papel y en tiempo real cientos de formas de binarias sobre BTCUSDT: las pasadas (E1 a E5 del Centro, el núcleo del semáforo, la neurona t33 y las 40 señales del banco, a 10 y 15 min) y las que propone cada hora una red de búsqueda. Base SQLite, partes a Telegram, peticiones por el mismo chat. No apuesta, no conoce llaves y no decide el dinero real. Plan: `binarias-papel\laboratorio\PLAN-LABORATORIO.md`; prompt final y revisión en la misma carpeta; sección 7d del `PLAN-TOTAL.md`; lista con chulitos en el AL FRENTE del bloc.

**Lo que salió.** Paridad exacta con la propia clase Centro en 40 días (E1 a E5, señal y resultado) y paridad exacta entre el PC y la caja (misma huella en 72.093 apuestas y las mismas probabilidades de la red). En la caja, 1.000 formas vivas se evalúan en 1,6 s por cierre de 5 min a 53 °C. La red de mercado gana a la neurona a 10 min (55,2 % frente a 54,6 % con confianza de 0,56 en «elige») y pierde a 15 min, donde se usa la neurona.

**Hallazgo importante.** Las mejores formas nuevas de «elige» caen a cerca de 54 % a ciegas: «RSI de 15 min sobre 82 + ruptura de 56 velas, al revés» dio 64,3 % en «elige» y 54,2 % en «juzga». No es fuga de información: es la maldición del ganador entre cientos de variantes. A 15 min la valla resultó blanda porque la devolución tiene 2 a 3 puntos reales sobre el equilibrio de 52,04 %, así que se puso un tope de 12 vivas por familia. Por eso el tablero muestra siempre la cifra a ciegas junto a la de vivo.

**Caja.** Volvió a la red con el reloj en hora. Su centinela corría desde las 14:35 con el papel rehecho y sin las marcas de SÍ del teléfono; se detuvo a las 19:42 con ESPERA_ESTADO (sale solo, sin matar procesos) hasta copiarle el estado del teléfono. Tiene ya el `quince.py` del 07/11 y el `arrancar.sh` que arranca el laboratorio.

**Falta:** arrancar el laboratorio de verdad tras las marchas en seco, el reinicio de prueba, que él confirme en Telegram el tablero y las peticiones, 48 horas de marcha con auditoría, consolidar en GitHub y la USB, y la IA pequeña (paso 12). De él: conectar el teléfono por USB.

**Placa ESP32.** A las 20:45 pidió que la placa hiciera lo que él quiere y que siguiera aunque la desconectara. Quedó dedicada a binarias con su programa guardado en la memoria (arranca sola, reconecta el WiFi, perro guardián): corre la misma red del laboratorio y la pérdida, con velas que pide a Binance, y las dos pruebas contra el laboratorio dieron igualdad exacta. El acortador de noticias quedó guardado pero apagado; el bot usa su propio resumen.

**Comprar sobre la pérdida.** Su idea: comprar el lado que va perdiendo cuando paga más, y con el precio real. La tabla a ciegas muestra que el perdedor gana casi en proporción a lo atrasado (minuto 14 con |z| de 3 o más: 0,3 %), así que comprarlo a 0,01 solo deja ganancia si la app lo vende por debajo de esa frecuencia. El precio real solo se lee con su llave, que no sale del PC: la Mesa anota el papel con el libro real de Predict.fun y lo manda a la placa y a la caja. Primera ventana (21:00 a 21:15): BAJA a 0,01 a 159 s del cierre; ganó «sube» y las cuatro compras de papel perdieron 1 USDT cada una.

**Cierre (21:20).** Caja reiniciada de prueba: Tor y el laboratorio volvieron solos a los 84 s. Todo en GitHub (rama binarias/plan-v7-2026-11-04). Falta: su confirmación en Telegram (paso 8), las 48 horas (paso 9), la revisión final, la USB y la IA pequeña.

Relacionado: [[Binarias en papel]], [[Mesa de binarias]].
