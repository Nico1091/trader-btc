# Qué es cada cosa

## Lo que se está haciendo: el agente trader de BTC

Es **un solo esfuerzo**: un agente que opera BTC con estrategias de trading, en papel, con 40.000 pesos. Tiene dos partes:

- **La rutina de la nube** (`trig_01HhTpY4sVUqaj1ui3qi7wyQ`, cada 6 horas, prompt en `PROMPT-AGENTE-TRADING-NUBE.md`). Claude decide cada operación con su juicio (libro CLAUDE), recluta y prueba estrategias, entrena a ciegas y escribe a Nicolás por correo y Telegram. Es la parte viva.
- **El agente del PC** (el código Python de este repositorio). Opera BTC «seguido», en ciclos de segundos a minutos, con cuatro libros en papel. Lo medido: a minutos la comisión se come el movimiento y pierde. Sirve de banco de pruebas y de lección.

## Aclaración importante: «arbitraje-cero-gas» no es lo que se está haciendo

Verás ese nombre en `fuentes/estrategias-curso-probadas-junio-2026/` y en la bóveda. El proyecto empezó en junio de 2026 como un bot de arbitraje sin gas en Ethereum, pero esa idea se abandonó. **Lo que vale de esa carpeta es otra cosa:** ahí se tomaron las estrategias de trading del curso de forex de Nicolás (velas, topes, retroceso en tendencia, 50 SMA, Fibonacci, gestión del riesgo) y se probaron sobre BTC y ETH con 24 meses de datos reales de Binance. Son **estrategias de trading que desarrollamos nosotros a partir del curso**, y son el antecedente directo del agente actual.

No retomes el arbitraje ni los bots de Ethereum (airdrops, préstamos flash, `CONSENSO_FINAL_ETH.md`): quedan solo como historia.

## Cronología

| Fecha | Qué pasó |
|---|---|
| Junio 2026 | Estrategias del curso probadas sobre BTC/ETH en 1 h. Gana la MEZCLA (retroceso largo + corto en techo). La IA como filtro empieza restando y luego suma. |
| 19-20/10 | Agente del PC operando seguido a minutos: pierde por comisión en todos los libros. |
| 24/10 | Rutina de trading en la nube; Claude pasa a decidir él mismo (libro CLAUDE, 40.000 pesos). |
| 25/10 | Último informe: segunda ventaja medida (largo del lunes, P11); P05b sigue como candidata frágil. |
