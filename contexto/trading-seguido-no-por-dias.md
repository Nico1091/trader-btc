---
name: trading-seguido-no-por-dias
description: "Corrección de Nicolás del 20/10/2026: su trading es «seguido» (ciclos de segundos a minutos, uno tras otro), no por días ni por meses; el diseño del 19/10 con velas de 5 min a 1 h era un error."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 1d1ac955-ddb8-47e8-8886-dfd8032a34f9
  modified: 2026-10-21T00:59:03.712Z
---

El 20/10/2026, al retomar el trader, Nicolás corrigió: «estás equivocado, lo que te dije es que hicieras trading seguido, no en días; revisa bien lo que te dije, contextualízate bien». Su pedido literal del 19/10 (índice semántico, turno 35298) ya lo decía: «cada operación estás haciendo cada rato», «en poco tiempo», «operaciones en corto», pausas cada 100 a 800 ciclos, riesgo en segundos, minutos, horas y días.

**Why:** el 19/10 se diseñó con velas de 5 min a 1 h, máximo 12 operaciones al día y posiciones de hasta dos días, y se llamó «intradía». Para él eso sigue siendo trading por días. «Seguido» significa un ciclo tras otro, de segundos a minutos, con el agente siempre encendido.

**How to apply:**
- Cuando hable de su trading, entender ciclos de segundos a minutos; las horas, días y semanas son contexto de lectura, no el horizonte de la operación.
- «Ciclo» es una operación completa (entrada y salida); «tanda» son 100 a 800 ciclos con pausa de revisión.
- Decirle de frente lo que miden los datos: con comisiones de 0,02 a 0,10 % por lado y BTC tranquilo, operar seguido pierde (ver [[trader-btc-en-curso]]); no maquillarlo ni volver en silencio a horizontes largos sin preguntarle.
- Antes de rediseñar, releer su pedido literal en el índice semántico, no el resumen de la memoria.
