---
name: trading-broker-y-privacidad
description: "Sus reglas del 19/10/2026 para operar: nada de brokers mexicanos, broker de pruebas de Binance, privacidad total de sus operaciones y red normal permitida hacia Binance."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f76b4f0f-3a8b-4a8e-b54b-3b26f7b8e523
  modified: 2026-10-19T17:23:36.008Z
---

Dicho por Nicolás el 19/10/2026 al pedir el agente de trading ([[trader-btc-en-curso]]):

- **Nada de brokers de México.** Varias veces le quisieron robar en plataformas mexicanas. Bitso también queda fuera.
- **Operar «en un broker hacia Binance».** El modelo y las velas son de Binance; si se cambia de casa se pierde la validación (lo recordó de lo que se le dijo el 12/09). El broker de pruebas es la red de pruebas de Binance; en futuros la antigua testnet fue retirada y la sustituye Demo Trading (`demo-fapi.binance.com`). Él creyó que el de pruebas era TradingView, pero TradingView no tiene API para que un agente opere su cuenta de papel: solo alertas por webhook a servidores de terceros, que verían sus operaciones.
- **Privacidad de sus operaciones: que nadie se entere.** Claves leídas en tiempo de ejecución, nunca mostradas ni copiadas; diario solo en local; ninguna plataforma de bots de terceros (3Commas filtró más de 100.000 claves de Binance en diciembre de 2022); ninguna IA externa recibe sus operaciones (tampoco DeepSeek ni OpenRouter).
- **Red.** Hacia Binance se permite la conexión normal («si es posible, redes normales, sin necesidad de Tor, con cuidado de que nadie esté fijándose»). Todo lo demás va por Tor.
- **Nada de ganancias falsas.** Probar todo aunque el retorno se vea alto: lo que salga muy bien queda como «sistema de posible confianza» y se compara con otro sistema y con el azar, anotándolo todo. Dinero real solo cuando se agoten las pruebas y él lo autorice.

**Why:** le han robado en brokers y su prioridad es no perder plata ni exponerse.
**How to apply:** proponer solo casas serias no mexicanas; decirle qué tercero vería algo antes de usarlo; mantener bloqueado el dinero real en el código. Ver [[proteccion-nivel-pelicula]] y [[nunca-puertas-directas]].
