# Plan de las binarias en Binance

> **Desde el 03/11/2026 manda el PLAN-TOTAL.md** (antes PLAN-v5.md) (unificado en BTC/USDT, centinela en la caja y el teléfono, semáforo papel → real, meta honesta de 56-57 %). Este archivo queda como historia y evidencia. El «16 %» del objetivo y de la sección 1 lo reemplazó la sección 9.

Versión 4 · 29/10/2026, 22:05 (hora de Colombia).
- Las secciones 1 a 6 se escribieron antes de ver los resultados: versión 2, con la revisión 1.
- La versión 3 ajustó la sección 3 a lo construido (revisión 2) y añadió la sección 8, con resultados y veredicto.
- La versión 4 añade la sección 9: su orden de que yo elija el tamaño, y el centinela v4 (revisión 3). En la sección 3, «16 % del saldo» queda reemplazado por lo de la sección 9.

## Objetivo

Encontrar, con pruebas que no miren el futuro, una forma de apostar en los Contratos de Evento de Binance que haga crecer 100.000 COP apostando el 16 % del saldo. Esa forma se opera en papel con un centinela que vigila el mercado, una decisión de Claude antes de cada apuesta y el toque de Nicolás en la app. El sistema solo se declara «consolidado» si cumple los criterios de la sección 6, que quedan fijados aquí.

## 1. Límites que no se discuten

- Los Contratos de Evento se apuestan solo en la app del teléfono, sin API, sobre BTCUSDT y ETHUSDT, a 10 min, 30 min, 1 h o 1 día. El pago lo fija Binance en cada apuesta y todavía no se conoce: todo se mide con 0,80, 0,85 y 0,90.
- La apuesta es el 16 % del saldo del momento, compuesto, sin stop, desde 100.000 COP. Como Binance exige al menos 5 USDT (unos 15.900 COP), se apuesta el mayor entre el 16 % y ese mínimo, y la cuenta queda quebrada cuando el saldo no lo cubre. Todas las cifras van en pesos.
- Todo va en papel. Ninguna línea de código mueve dinero; el dinero real exige que se cumplan los criterios y su orden expresa.
- Los datos se leen directo de Binance, sin claves. Nadie más ve las operaciones; los avisos van por su Telegram (bot Centro nocturno).
- Las pruebas corren con prioridad baja para no cargar el equipo.
- Ningún subagente. El operador es una sesión aparte de Claude Code, lanzada con `claude --bg`, que él pidió («configurar agentes»).

## 2. Umbrales de acierto

- Para no perder con apuestas iguales hace falta acertar 1/(1+pago): 55,6 % con 0,80, 54,1 % con 0,85 y 52,6 % con 0,90.
- Para que la cuenta crezca apostando el 16 % compuesto hace falta: 59,1 % con 0,80, 57,8 % con 0,85 y 56,4 % con 0,90.
- Distinguir 57,8 % de 54,1 % con la corrección de la sección 6 exige unas 1.100 apuestas. Por eso la prueba principal es la historia; el papel en vivo comprueba que el sistema hace lo mismo que la prueba y que no se derrumba.
- Un empate cuenta como fallo en la cifra principal y se informa aparte.

## 3. Cómo funciona

1. **Centinela** (`binarias.py` v3, sobre el bot actual). Lee de Binance las velas de 1 min de futuros de BTCUSDT y ETHUSDT (`/market/stream`), corrige la hora con la del servidor de Binance y calcula las señales con las mismas funciones que el banco de pruebas. La elección (sección 5) se rehace el primer día de cada mes con los 12 meses anteriores y queda en `seleccion.json`.
2. **Ficha previa.** A 70 s del cierre de cada vela calcula la señal con el precio de ese momento. Si una estrategia elegida va a disparar y se cumplen las condiciones obligatorias, escribe una ficha en `fichas/` con: activo, estrategia, sentido, plazo, hora límite, precio, recorrido de 5, 15 y 60 min frente a la volatilidad normal, contexto del día, señales a favor y en contra, y acierto a ciegas de esa estrategia en los últimos 12 meses.
3. **Operador Claude.** Una sesión de fondo («operador binarias», lanzada en `C:\Windows\System32` porque Claude Code no abre sesiones de fondo en carpetas sin confianza) espera las fichas con `operador.py esperar`, las lee con `operador.py pendientes` y aprueba o descarta con `operador.py decidir`, con la razón y una confianza de 0 a 1. Solo tiene permiso para `python -I …/operador.py`. El plazo es el cierre de la vela más 5 s. Solo puede descartar: nunca crea una apuesta que la regla no dio.
4. **Cierre de la vela.** El centinela recalcula con la vela cerrada. Si la señal se confirma:
   - la cuenta REGLA apuesta siempre;
   - la cuenta CLAUDE apuesta solo si el operador aprobó a tiempo;
   - la cuenta AZAR apuesta a la misma hora con sentido al azar.
   Cada apuesta guarda el precio al cierre y el de 20 s después, que es el que vería él al tocar; las cuentas se liquidan con el de 20 s. Cada apuesta de CLAUDE le llega a su Telegram con sentido, plazo y monto en USDT y en COP, como la recibiría para tocarla en la app.
5. **Cuentas.** Las tres empiezan con 100.000 COP y siguen la regla de apuesta de la sección 1. Se lleva cada apuesta con hora, sentido, plazo, monto, precios, resultado y saldo.
6. **Condiciones obligatorias**, todas a la vez. Son exactamente las del banco, para que REGLA en vivo y la prueba coincidan:
   - estrategia elegida por el procedimiento del mes, con sus filtros;
   - plazo que Binance ofrezca (10, 30 o 60 min);
   - ninguna apuesta abierta en esa cuenta;
   - menos de 16 apuestas en el día;
   - cuenta sin quebrar;
   - la aprobación de Claude, para la cuenta CLAUDE.
   La volatilidad (vela de 1 min más grande frente a la media de la hora, recorrido en σ) va en la ficha como dato para el criterio de Claude.
7. **Arranque y continuidad.** El centinela y el operador arrancan solos al iniciar sesión en Windows, si no hay otro vivo (candado de archivo para el centinela; `claude agents` para el operador). El operador usa solo Bash y Read. Si no está o no responde a tiempo, la ficha queda «sin decisión» y la cuenta CLAUDE no apuesta. El estado se guarda con reintentos y se conserva en memoria hasta poder escribirlo.
8. **Revisión diaria.** A las 6:00 el operador manda a Telegram un párrafo con las apuestas del día anterior en las tres cuentas.

## 4. Pruebas, en este orden

- **P1 · Mapa (t17).** Las 42 estrategias, solas y mezcladas, en 7 plazos y 5 preventivas, al 16 %. Elige con 2024-26 y mira un solo mes: sirve de mapa y no decide nada.
- **P2 · Reglas a ciegas (principal).** BTCUSDT de enero de 2021 a octubre de 2026 con velas de 1 min de futuros. Cada mes se elige con los 12 meses anteriores (sección 5) y se opera el siguiente sin tocar nada. Igual con ETHUSDT (sin el grupo B, que solo existe para BTC desde 2024).
- **P3 · Modelo a ciegas.** Regresión logística escrita en numpy, sin librerías nuevas, sobre cada cierre de 5 min. Rasgos calculados solo con datos anteriores: rendimientos de 1 a 240 min divididos por la volatilidad, volatilidad corta frente a larga, volumen, posición en el rango de 24 h, distancia y pendiente de medias, hora del día y las señales del grupo A. Se normaliza y se ajusta con 9 meses, el umbral de confianza se elige con los 3 siguientes y se opera el mes después. Objetivos de 10, 30 y 60 min, en BTC y en ETH.
- **P4 · Robustez** de lo que salga mejor en P2 o P3:
   - entrada 60 s tarde (velas de 1 min) y 20 s tarde (velas de 1 s, de mayo a octubre de 2026);
   - pagos de 0,80 y 0,90;
   - por años, por los tramos 2021-23 y 2024-26, y sin los 5 mejores días;
   - comparación con apostar siempre arriba y con el azar a las mismas horas;
   - coincidencia de sentido entre contado y futuros a 10, 30 y 60 min.
- **P5 · Paridad en vivo.** Cada día el centinela compara sus señales con las del banco sobre las mismas velas. Deben coincidir todas.

## 5. Selección mensual, exacta

- **Candidatos:** cada estrategia de los grupos A (sus libros), B (T95H, desde 2024), C (consolidadas) y E (agente de la nube, la E01 es la MEZCLA de junio), en sentido normal o al revés, a 10, 30 o 60 min.
- **Ajuste por candidato**, solo con la ventana de entrenamiento y con una apuesta abierta a la vez: primero el sentido y el plazo; después se prueba añadir, uno a uno, «a favor del contexto», una sesión (Asia, Europa, América) o la volatilidad (alta o baja). Un filtro se queda solo si sube el límite inferior de Wilson al 95 % con al menos 100 apuestas.
- **Elegidos:** los 3 candidatos de estrategias distintas con mayor límite inferior, siempre que ese límite supere 54,1 %. Si ninguno lo supera, ese mes no se apuesta.
- **Operación del mes siguiente:** las señales de los elegidos en orden de llegada, una apuesta abierta a la vez, como máximo 16 al día (día de Colombia), regla de apuesta de la sección 1, pago 0,85.
- **Modelo (P3):** el umbral simétrico de confianza que más hace crecer la cuenta en los 3 meses de calibración, con al menos 100 apuestas. Si ninguno la hace crecer ahí, ese mes no se apuesta.
- **Variantes de sensibilidad** (ventana de 6 o 24 meses, 1 o 5 elegidos): se informan, pero no se pueden escoger.

## 6. Criterios de consolidación

Todos deben cumplirse:

1. **Historia a ciegas** de uno de los 8 procedimientos (reglas en BTC y ETH; modelo a 10, 30 y 60 min en BTC y ETH), en el periodo completo:
   - acierto ≥ 57,8 % con pago 0,85;
   - límite inferior de Wilson al 99,375 % de una cola (95 % corregido por 8) por encima de 54,1 %, lo que exige unas 1.100 apuestas;
   - los tramos 2021-23 y 2024-26, cada uno por encima de 54,1 %;
   - en al menos el 60 % de los arranques de 30 días, 100.000 COP termina por encima de 100.000;
   - mejor que apostar siempre arriba y que el azar.
2. **Robustez:** con 60 s de retraso sigue por encima de 54,1 %; con pago 0,80 se informa aunque falle.
3. **Paridad:** coincidencia completa de señales entre el centinela y el banco durante 7 días.
4. **Papel en vivo:** al menos 100 apuestas, con un acierto que no quede significativamente por debajo del de la historia, y sin errores de operación.

Si falla el punto 1, el veredicto es «no consolidable con el 16 %». El sistema sigue en papel con el procedimiento que mejor salió a ciegas, vuelve a elegir cada mes, y el informe dice qué tendría que cambiar para que pase.

## 7. Archivos

- `PLAN.md` (este), `PROMPT-OPERADOR.md`, `PROMPT-REVISION.md` y `REVISION.md`.
- `motor/senales.py` y `motor/seleccion.py`: el único código de señales y de elección, compartido por las pruebas y el centinela.
- `pruebas/t18_reglas_a_ciegas.py`, `t19_modelo_a_ciegas.py`, `t20_robustez.py` y `t18_paridad.py`, con sus `.txt`, `.csv` y `.json`.
- `binarias.py` v3 (centinela; la v2 quedó en `binarias.v2.py`), `operador.py`, `seleccion.json`, `fichas/`, `decisiones/`, `apuestas.jsonl`, `senales_vivo.jsonl` y las cuentas en `estado.json`.
- En el escritorio: «Binarias en tiempo real» (pantalla) y «Operador de binarias» (enciende al operador si no está y muestra las cuentas).
- Arranque al iniciar Windows: `PONER ARRANQUE AUTOMATICO.cmd` y `QUITAR ARRANQUE AUTOMATICO.cmd`.

## 8. Resultados y veredicto (29/10/2026)

Pruebas a ciegas, enero de 2021 a octubre de 2026, pago 0,85, empate = fallo. Las cifras de esta sección y de la 9 usan velas hasta el 26/10/2026; los archivos de `pruebas/` ya se pusieron al día hasta el 29/10 con el recálculo mensual.

| Procedimiento | Apuestas | Al día | Acierto | 2021-23 | 2024-26 | 2026 | Límite corregido |
|---|---|---|---|---|---|---|---|
| Reglas, BTC (principal) | 16.898 | 8,0 | 58,0 % | 59,5 % | 56,2 % | 54,9 % | 57,0 % |
| Reglas, ETH | 10.995 | 5,2 | 56,6 % | 57,4 % | 56,0 % | 56,0 % | 55,4 % |
| Modelo 10 min, BTC | 19.643 | 9,5 | 57,9 % | 58,7 % | 55,9 % | 56,6 % | 57,1 % |
| Modelo 10 min, ETH | 15.127 | 7,1 | 57,5 % | 57,9 % | 56,6 % | 58,3 % | 56,4 % |
| Modelo 30 min, BTC | 13.013 | 6,2 | 57,0 % | 57,7 % | 55,2 % | 54,1 % | 55,9 % |
| Modelo 30 min, ETH | 8.848 | 4,2 | 56,6 % | 57,1 % | 55,9 % | 55,5 % | 55,2 % |
| Modelo 60 min, BTC | 10.508 | 5,5 | 56,4 % | 56,8 % | 55,6 % | 51,9 % | 55,2 % |
| Modelo 60 min, ETH | 12.302 | 5,8 | 54,8 % | 54,7 % | 55,0 % | 54,4 % | 53,7 % |

- La ventaja existe y no viene de un error: la regla que más se elige («rompimiento de 20 velas» al revés, a 10 min), escrita de nuevo y sin el banco, da 58,0 % en 47.935 apuestas. Apostar siempre arriba a las mismas horas da 50,1 % y el azar 50,0 %.
- Se está gastando: la regla cruda pasó de 60,3 % en 2020 a 55,5 % en 2026.
- Con el 16 %, 100.000 COP durante 30 días termina arriba en el 47,6 % de los arranques y quiebra en el 48,9 %. Con las mismas apuestas, al 8 % desde 200.000 COP termina arriba en el 72,5 % y quiebra en el 14,2 %.
- Veredicto con los criterios de la sección 6: **no consolidable con el 16 %**, porque falla la condición de pesos del punto 1. Los puntos 3 y 4 (paridad y papel en vivo) siguen abiertos. El sistema queda operando en papel con el procedimiento principal.

## 9. Su orden del 29/10, 21:50, y lo decidido (t21, a ciegas; revisión 3)

«Apueste el porcentaje que crea y lo que crea, sin stop loss o los que usted crea y diga.» Desde el 29/10 a las 21:51 corre el centinela v4:

- **Tamaño:** medio Kelly con el acierto a ciegas de los 6 meses anteriores, nunca menos de 5 USDT. Si ese acierto no supera el equilibrio, no se apuesta ese mes. Con 100.000 COP es siempre el mínimo (unos 15.900 COP); la fracción empieza a mandar cuando la cuenta supera unos 453.000 COP.
- **Sin stop y sin preventivas:** las probadas (parar el día tras 3 fallos o tras 3 netas perdidas) no mejoraron en 2022-23.
- **Procedimiento del mes:** cada mes, entre los 8, el de mejor historial a ciegas en los 12 meses anteriores (octubre de 2026: modelo a 10 min en ETH, 58,3 %). BTC FIJO sigue con las reglas de BTC como control.
- **Cada mes,** el centinela pone al día el banco (t18 y t19 con las velas nuevas), elige el procedimiento y, si es el modelo, lo entrena con el mismo código de t19.

A ciegas, 100.000 COP con medio Kelly (2022-26):

| Procedimiento | 30 días: termina arriba | 30 días: quiebra | 90 días: termina arriba | Un año: termina arriba |
|---|---|---|---|---|
| Por historial entre los 8 (el del mes) | 65,5 % | 32,9 % | 64,2 % | 56,1 % |
| Reglas de BTC fijas (BTC FIJO) | 61,9 % | 36,0 % | 58,3 % | 64,3 % |
| Reglas de BTC al 16 % (antes) | 47,8 % | 48,2 % | 31,6 % | 25,7 % |

Con el tamaño nuevo, el punto 1 de la sección 6 se cumple en la historia (revisión 3). Para consolidar faltan los puntos 3 y 4: 7 días de paridad en vivo y 100 apuestas en papel.

## 10. Oro (29/10/2026, 22:20; t22 y t23, revisión 4)

Su pedido: «prueba con el oro». Binance no tiene Contratos de Evento de oro, solo BTCUSDT y ETHUSDT.
- **Instrumentos:** PAXGUSDT de contado (desde el 28/08/2020) y XAUUSDT perpetuo, el oro real (desde el 11/12/2025, 1.930 millones de USDT al día).
- **PAXG como aproximación:** se mueve en el mismo sentido que XAUUSDT el 86,7 % de las veces a 10 min y el 89,3 % a 60 min.
- **Liquidez de PAXG:** el precio no se movió en el 39-40 % de los tramos de 10 min de 2022-23, y en el 3,5 % de 2026.

| Oro, a ciegas | Apuestas | Acierto | 2021 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| PAXG, reglas | 7.142 | 56,1 % | 61,3 % | 50,3 % | 54,6 % | 55,3 % |
| PAXG, modelo a 30 min | 8.236 | 59,5 % | 62,9 % | 58,3 % | 54,4 % | 53,0 % |
| PAXG, modelo a 60 min | 8.971 | 58,6 % | 64,3 % | 58,1 % | 52,6 % | 53,9 % |
| XAUUSDT (oro real), reglas | 1.671 | 53,6 % | – | – | – | 53,6 % |
| XAUUSDT, modelo a 30 min | 665 | 52,5 % | – | – | – | 52,5 % |

- La ventaja de PAXG vivió en los años en que casi no se movía; en el oro líquido de 2025-26 queda en el equilibrio o por debajo.
- Con medio Kelly, el oro real no habría apostado ni una vez en 2026: su acierto reciente nunca superó el 54,1 %.
- Al 16 %, 30 días desde 100.000 COP quiebran en el 72 % de los arranques.
- Veredicto: **el oro no se agrega**. El sistema sigue con BTC y ETH. En 2026, el modelo a 10 min en ETH dio 58,3 %.

## 11. Sistema unificado con operación diaria (29/10/2026, 22:30; escrito antes de probarlo)

Su orden: «tienes 100 % lienzo libre… escoge el mejor mercado… solidifica y unifica… recuerda que vas a operar diario… piensa bien y guarda en memoria».

**Diagnóstico del sistema actual (v4).** Elige un solo procedimiento por mes entre 8, y si su acierto reciente no pasa del equilibrio, no apuesta. Hay meses enteros quietos (el modelo a 10 min se quedó sin umbral 10 de 70 meses en BTC y 12 en ETH), lo que choca con operar a diario. Además, cada procedimiento mira un solo activo y una sola fuente de información.

**Diseño U, «unificado», que se prueba:**
- **Mercados:** BTCUSDT y ETHUSDT, los únicos con Contratos de Evento. Plazo de 10 min, el más corto de Binance y el que mejor resistió en 2026.
- **Una regresión logística por activo**, evaluada en cada cierre de 5 min, con:
  - los rasgos actuales del modelo;
  - las señales de todas las estrategias (grupos A, C y E) como rasgos;
  - lo que hace el otro activo: rendimientos de 1 a 60 min, forma de la vela, posición en el rango y rendimiento relativo;
  - el flujo de órdenes: proporción de compras agresivas (taker buy) en 1, 5, 15 y 60 min, del activo y del otro.
- **Ajuste a ciegas como t19:** 9 meses de ajuste, 3 de calibración y el mes siguiente operado.
- **Umbral por activo:** el que más hace crecer la cuenta en la calibración, entre los que dan al menos 2 apuestas al día. Si ninguno crece con esa frecuencia, el que más crezca sin ella. Si ninguno crece, ese activo no apuesta ese mes.
- **Operación conjunta:** en cada cierre se apuesta el activo con la confianza más alejada de 0,5 que pase su umbral. Una abierta a la vez y hasta 16 al día.
- **Tamaño:** medio Kelly con el acierto a ciegas de U en los 6 meses anteriores, mínimo 5 USDT. Sin stop.

**Regla de decisión, fijada ahora.** U reemplaza al procedimiento por historial (H, el de la v4) solo si, de enero de 2022 a octubre de 2026 y con medio Kelly, cumple las tres:
1. los 30 días desde 100.000 COP terminan arriba en al menos tantos arranques como con H (65,5 %);
2. su acierto en 2024-26 es al menos el de H (57,0 %);
3. el porcentaje de días con al menos una apuesta es al menos el de H.

Si falla alguna, se queda H y se toma de U solo lo que pase la misma comparación por separado. Las versiones sin flujo de órdenes, sin el otro activo y sin frecuencia mínima se informan como sensibilidad y no se pueden escoger.

**Unificar también lo demás:** una sola cuenta principal, más CLAUDE y AZAR para medir, y un solo documento de estado. Lo viejo queda en respaldo, fuera de la operación.

## 12. Contexto primero y estrategias difundidas de binarias (31/10/2026, 08:05; escrito antes de probarlo)

Su orden del 31/10: buscar las estrategias de binarias más usadas y las que más han dado, incluidas las que prometen el 98 %; revisar a los traders famosos que mencionó; y probar su método: tomar una sola vez el contexto (3 h, 5 h y 3 meses) y luego decidir cada 5 o 15 min, mirando el gráfico.

**Lo que dice la investigación (31/10):**
- Ninguna prueba independiente sostiene el 98 %. Esas cifras salen de la martingala, de contar días ganados en lugar de apuestas, de periodos escogidos o de mirar la vela que aún no cierra. Las pruebas serias de binarias quedan entre el 55 y el 65 %.
- No hay fuente fiable de nadie que gane 3 o 4 millones al día con binarias. Los más parecidos son Takashi Kotegawa («BNF», 153 millones de dólares en acciones, comprando lo que cae muy por debajo de su media de 25) y Navinder Sarao («flash crash», falsas órdenes: ilegal e imposible en los Contratos de Evento, así que se descarta).
- Los estudios sobre BTC y ETH (Wen y otros, 2022; JRFM 2026; Ledger) encuentran reversión a corto plazo dentro del día, lo mismo que ya aprovechan REV y el rompimiento al revés.
- La martingala queda fuera: en la prueba de TradingRush, cerca del 45 % de las cuentas no pudo seguir doblando.

**Estrategias nuevas (grupo N), todas a 10, 30 y 60 min y con la elección de la sección 5 (que también prueba el sentido contrario):**
1. MHI en velas de 1 min: al cerrar cada bloque de 5 min, el color de la mayoría de las velas 3, 4 y 5; la señal es la minoría. Si la elección invierte el sentido, es el «Milhão» (la mayoría).
2. MHI en velas de 5 min: lo mismo con bloques de 25 min.
3. Five flip y seven flip: 5 o 7 velas de 5 min seguidas del mismo color; la señal es el color contrario.
4. Torres gemelas: dos velas de 5 min de color contrario, con cuerpos que difieren menos del 10 % y mayores que la media de 20; la señal es el color de la segunda.
5. BNF a corto plazo: distancia del cierre de 5 min a su media de 300 velas (25 h), medida en desviaciones de la última semana; señal al cruzar ±2,5, a favor de que vuelva a la media.

**Su contexto, tomado una sola vez:** al empezar cada bloque de 3 h (0, 3, 6… UTC) se fija el signo del rendimiento de las últimas 3 h, de las últimas 5 h y de los últimos 90 días. Si los tres coinciden, el contexto es ese signo y queda fijo las 3 h siguientes; si no coinciden, es neutro. Cada estrategia nueva, más REV5, REV15 y el rompimiento de 20 velas, entra en tres versiones: sin contexto, «a favor» (la señal va con el contexto) y «en contra». Con contexto neutro, las dos últimas no dan señal.

**Regla de decisión, fijada ahora.** Por activo, se corre la elección a ciegas de la t18 (ventana de 12 meses, 3 elegidas, 2021 a octubre de 2026) con el banco actual y con el banco ampliado. El ampliado entra en producción solo si cumple las cuatro:
1. acierto de todo el periodo al menos igual al del actual;
2. acierto 2024-26 al menos igual;
3. con pago 0,85, los 30 días desde 100.000 COP terminan arriba en al menos tantos arranques como con el actual;
4. al menos tantas apuestas al día.

Si falla alguna, el banco no cambia. Se informa cuántos meses eligió la selección cada estrategia nueva y su acierto propio. Si una sola estrategia nueva lo hace bien por su cuenta pero el banco ampliado no mejora, no entra: la selección mensual es la que decide.

**El gráfico de TradingView** sirve para que él vea cada decisión; las cuentas se hacen con los números exactos de las velas de Binance, que son los mismos que dibuja el gráfico. Si la t26 adopta el contexto, el centinela lo calcula una vez por bloque de 3 h y, con cada ficha, deja una captura del gráfico de 5 min.

**Resultado de la t26 (31/10/2026, 08:20).** A ciegas, de 2021 a octubre de 2026, pago 0,85:
- BTC: banco actual 58,0 % (2024-26: 56,2 %; 30 días arriba 47,6 %; 7,96 al día). Ampliado 59,0 % (56,9 %; 55,8 %; 6,19 al día).
- ETH: banco actual 56,6 % (56,0 %; 33,4 %; 5,17 al día). Ampliado 57,6 % (56,8 %; 45,6 %; 4,02 al día).
- Cumple las condiciones 1 a 3 y falla la 4 (apuestas al día) en los dos activos. **Veredicto: el banco no cambia.**
- Lo útil: el contexto de 3 h, 5 h y 90 días mejora el rompimiento de 20 velas al revés cuando el rompimiento va en contra del contexto (59,4 % en BTC y 58,3 % en ETH, frente a 56,9 y 56,4 % a favor). Fue lo más elegido (41 y 36 meses).
- Lo que no sirve: MHI (51 a 53 %), torres gemelas (50 %) y BNF en ETH (52 %). Seven flip contra la racha da 57 % y five flip 55,5 a 55,8 %.
- El acierto propio de cada estrategia con sentido fijo es informativo y no es a ciegas.

## 13. Defensas sin stop (31/10/2026, 08:25; escrito antes de probarlo)

Su orden del 31/10: el 58 % sale «sin defensiva»; poner defensas que no sean stop: el volumen (bajo o alto), su contexto de 3 h con 2 h operando, el dólar y las noticias, y lo que hacen los mejores traders.

**Lo que se puede probar con la historia (velas de 1 min con volumen, 2021 a octubre de 2026):**
- D1 · Volumen: volumen de la última hora frente a la mediana de la misma medida en los 7 días anteriores. Bajo si es menos del 70 %, alto si pasa del 130 %. Variantes: no apostar con volumen bajo; no apostar con volumen alto.
- D2 · Su ventana: el contexto se toma al empezar cada bloque de 3 h y solo se apuesta en las 2 primeras horas del bloque.
- D3 · Movimiento extremo: no apostar si en las últimas 3 h el precio se movió más que el percentil 90 de esa medida en los 30 días anteriores (los traders de reversión, como BNF, esperan a que pase el pánico; aquí se prueba la defensa contraria: no ponerse delante de un movimiento fuera de lo normal).

**Lo que no se puede probar y por qué:** las noticias (no hay un archivo de titulares con hora para 2021-26) y el índice del dólar (no está en Binance y no hay una serie de 1 min a mano). Las noticias van en su informe de voz para que él las tenga en cuenta, sin decidir nada.

**Cómo se prueba, a ciegas:** se toma la secuencia de apuestas a ciegas de la t18 (banco actual, 12 meses, 3 elegidas) y se le aplica cada defensa. La variante de cada defensa se elige con 2021-23 y se juzga solo con 2024-26.

**Regla de decisión, fijada ahora.** Una defensa entra en producción, por activo, solo si en 2024-26 cumple las tres:
1. acierto al menos 0,5 puntos por encima del de la secuencia sin defensa;
2. con pago 0,85, los 30 días desde 100.000 COP terminan arriba en al menos tantos arranques como sin defensa;
3. al menos 4 apuestas al día (su condición de operar a diario).

Si ninguna pasa, el sistema sigue sin defensas y se dice.

**Resultado de la t27 (31/10/2026, 08:28),** juicio en 2024-26 con la variante elegida en 2021-23:
- BTC: sin defensa 56,2 % · 35,8 % de arranques arriba · 7,49 al día. «Sin volumen alto» (la elegida): 56,7 % · 42,2 % · 4,76 al día. **Entra**, justo en el límite de +0,5 puntos. D2 (2 primeras horas): 55,8 %, no entra. D3: 56,3 %, no entra.
- ETH: sin defensa 56,0 % · 29,5 % · 6,30 al día. «Sin volumen bajo» (la elegida): 56,1 % · 35,7 % · 4,70 al día, no entra. D2: 56,4 %, no entra (+0,4). D3: 55,5 %, no entra.
- Falta ponerla en el centinela, con la misma cuenta del volumen en el banco y en vivo para no romper la paridad.

## 14. Operar solo con todo a favor (31/10/2026, 08:40; escrito antes de probarlo)

Su orden del 31/10: operar solo cuando todos los indicativos apunten al mismo movimiento; tener el contexto de 1 h tomado más de 10 min antes y la vela de 5 min; mirar si la gente está comprando, el mercado especulativo y la bolsa; operar a favor o en contra según indiquen; y usar solo las estrategias que dieron resultado tanto en días negativos como positivos.

**Indicativos que se pueden probar (velas de 1 min con volumen):**
- C1 · Contexto de 1 h: signo del cierre de la última vela de 1 h cerrada al menos 10 min antes de la entrada, frente a su media exponencial de 20 velas de 1 h.
- C2 · Vela de 5 min: color de la vela de 5 min que acaba de cerrar.
- C3 · Gente comprando: parte del volumen de los últimos 15 min que fue en velas de 1 min verdes; compra si pasa del 55 %, venta si queda bajo el 45 %.
- C4 · Mercado especulativo: el otro activo (ETH para BTC, BTC para ETH) con su propio C1.
- La bolsa común (S&P 500) no se puede probar: no hay historia de 1 min a mano. No entra en la decisión.

**Estrategias robustas (R):** una apuesta de la estrategia S entra solo si, con todas las apuestas a ciegas anteriores de S, su acierto supera el 54,1 % tanto en los días en que el activo subió como en los que bajó (día de Colombia), con al menos 30 apuestas en cada clase. Solo usa apuestas ya cerradas: es a ciegas.

**Variantes:** V1 = R; V2 = C1, C3 y C4 a favor de la apuesta; V3 = V2 más C2; V4 = al menos 2 de C1, C3 y C4 a favor; V5 = R con V2; V6 = R con V4. Se aplican a la secuencia a ciegas de la t18 (banco actual). Se elige con 2021-23 la variante de mayor acierto entre las que dan al menos 1 apuesta al día, y se juzga solo con 2024-26.

**Regla de decisión, fijada ahora.** La variante elegida entra en producción, por activo, solo si en 2024-26 cumple las tres:
1. acierto al menos 1,0 punto por encima de la secuencia sin filtro (él pide bajar el margen de error);
2. con pago 0,85, los 30 días desde 100.000 COP terminan arriba en al menos tantos arranques como sin filtro;
3. al menos 1 apuesta al día en promedio (sigue operando a diario, aunque menos).

Si no pasa, no entra y se dice. El dinero real sigue esperando su orden expresa y los criterios 3 y 4 de la sección 6.

**Resultado de la t28 (31/10/2026, 08:45),** juicio en 2024-26:
- BTC: sin filtro 56,2 % (35,8 % de arranques arriba, 7,49 al día). V2 todo a favor: 51,9 % (0,13 al día). V1 robustas: 56,5 %. V6, la elegida con 2021-23: 55,7 % (46,0 %, 2,50 al día). **No entra.**
- ETH: sin filtro 56,0 % (29,5 %, 6,30 al día). V2: 44,3 %. V1: 56,2 %. V6, la elegida: 55,7 % (49,4 %, 2,17 al día). **No entra.**
- Lo que explica el resultado: las apuestas que ganan van contra el empujón inmediato. Solo coinciden con la vela de 5 min que acaba de cerrar el 6,7 % (BTC) y el 10,7 % (ETH), y con la presión compradora el 5,3 y el 6,1 %. Exigir que todo esté a favor deja fuera las apuestas buenas.

## 15. Su estrategia de las dos resistencias (31/10/2026, 08:44; escrita antes de probarla)

Lo que él hace (foto de las 08:44, BTCUSDT de 1 min): traza una línea casi horizontal en el techo del rango reciente y una diagonal que une los máximos que van bajando. Si el precio supera las dos, compra a 5-15 min; después espera la siguiente oportunidad del mismo estilo. Al revés para caídas.

**Cómo se trazan las líneas solas, en velas de 1 min:**
- Máximo de giro: vela cuyo máximo es el mayor de las 5 anteriores y las 5 siguientes. Se conoce 5 min después, no antes.
- Resistencia 1 (horizontal): el mayor cierre entre 65 y 5 min antes.
- Resistencia 2 (diagonal): la recta por los dos últimos máximos de giro ya confirmados, si el segundo es más bajo que el primero, prolongada hasta la vela actual.
- SUBE: la vela de 1 min cierra por encima de las dos y la anterior no lo estaba. BAJA: lo mismo con el menor cierre (soporte), los mínimos de giro que van subiendo y cierre por debajo de las dos.
- Entrada al abrir el minuto siguiente. Plazos de 10 y 30 min (los de Binance más cercanos a sus 5-15 min). Una apuesta abierta a la vez.

**Regla de decisión, fijada ahora.** Es una regla fija, sin nada ajustado, así que se mide en todo el periodo. Entra al banco de estrategias (y la elección mensual decide cuándo usarla) solo si, en BTC o en ETH, a 10 o a 30 min, en el sentido que él usa (a favor de la ruptura):
1. acierto 2024-26 de al menos 54,1 % con al menos 300 apuestas;
2. límite inferior de Wilson al 95 % de 2021-26 por encima de 54,1 %.

Se informa también el sentido contrario (apostar a que la ruptura falla), pero solo puede entrar si el criterio lo cumple el sentido que él usa.

**Resultado de la t29 (31/10/2026, 08:46).** Señales con las líneas trazadas solas, 2021 a octubre de 2026:
- BTC a 10 min, a favor de la ruptura (como él): 35.174 apuestas, 45,6 % (2024-26: 47,1 %). Contra la ruptura: 54,3 % (Wilson 53,8 %). A 30 min: 45,1 % y 54,8 %.
- ETH a 10 min, a favor: 35.682 apuestas, 45,4 % (2024-26: 45,8 %). Contra: 54,4 % (Wilson 53,9 %). A 30 min: 45,3 % y 54,6 %.
- **No entra.** Lo más frecuente es que la ruptura de las dos líneas falle. Apostar contra ella queda en el equilibrio y no pasa el criterio estadístico.
- Límite de la prueba: las líneas se trazan con una regla fija que imita su dibujo. Su lectura a ojo puede escoger rupturas distintas, y eso solo se puede medir anotando sus propias señales con hora.

## 16. Su señal de tocar la segunda resistencia (31/10/2026, 08:55; escrita antes de probarla)

Lo que él dijo (08:54): «si llega a tocar la segunda resistencia, eso quiere decir un posible mercado al alza, lo que reflejaría una compra». Primera resistencia: la horizontal. Segunda: la diagonal que baja.

**Señal, con las mismas líneas de la t29 (velas de 1 min):** SUBE cuando el precio ya cerró por encima de la horizontal y el máximo de la vela toca la diagonal (el máximo llega a ella y el de la vela anterior no llegaba). BAJA al revés: por debajo del soporte horizontal, el mínimo toca la diagonal de mínimos que suben. Entrada al abrir el minuto siguiente; 10 y 30 min; una abierta a la vez.

**Regla de decisión:** la misma de la sección 15. En el sentido que él usa: 2024-26 con al menos 54,1 % y 300 apuestas, y Wilson al 95 % de 2021-26 por encima de 54,1 %, en BTC o en ETH.

**Resultado de la t30 (31/10/2026, 08:57; pruebas\t30_toque_segunda.py).** Unas 7.000 señales por activo, 2021 a octubre de 2026, unas 2,8 al día:
- BTC a 10 min: comprar al tocar la segunda resistencia (como él), 45,6 % (2024-26: 46,7 %); en contra, 54,3 % (Wilson 53,1 %).
- ETH a 10 min: como él, 45,0 % (2024-26: 45,7 %); en contra, 54,9 % (Wilson 53,7 %). A 30 min, casi igual.
- **No entra.** Al tocar la diagonal, lo más frecuente es que el precio rebote hacia abajo (como el 31/10 a las 08:48: tocó 77.635 y volvió a 77.560).

## 17. Su regla de dos velas que superan la segunda línea (31/10/2026, 08:58; escrita antes de probarla)

Lo que él aclaró (08:57): para operar, el precio debe superar sus líneas dos veces: una vela verde que pasa la segunda línea y otra verde que la pasa un poco más. Si no la supera, no hay operación (como el 31/10 a las 08:48, que solo la tocó). Cómo traza sus líneas (fotos de las 08:53 y 08:56): la horizontal en el borde del rango donde el precio estuvo cerca de una hora; la diagonal desde el pico grande de la última hora y media, por encima del siguiente máximo más bajo, una hora o más después.

**Señal (velas de 1 min):** SUBE cuando dos velas verdes seguidas cierran por encima de la horizontal y de la diagonal, la segunda más arriba que la primera, y antes de ellas no se cumplía. BAJA al revés, con dos rojas por debajo del soporte y de la diagonal de mínimos. Entrada al abrir el minuto siguiente; 10 y 30 min; una abierta a la vez.

**Dos trazados de la diagonal:** «corta», con giros de 5 velas a cada lado (como la t29), y «larga», con giros de 30 velas a cada lado (los suyos, separados por una hora o más).

**Regla de decisión:** la misma de la sección 15, en el sentido que él usa, en cualquiera de los dos trazados.

**Resultado de la t31 (31/10/2026, 09:05; pruebas\t31_dos_velas.py, giro 5 y 30).** 2021 a octubre de 2026, a 10 min:
- Como él (comprar tras dos velas verdes sobre las dos líneas, y al revés para caídas): 43,0 a 43,7 %, en 23.000 a 35.000 apuestas. Pierde en todos los casos.
- En contra: BTC con líneas largas 57,0 % (Wilson 56,5 %; 2024-26: 54,7 %); ETH con líneas largas 56,2 % (55,6 %; 55,0 %); ETH con líneas cortas 56,2 % (55,5 %; 56,1 %); BTC con líneas cortas 56,2 % (55,6 %; 53,9 %).
- **No entra**, porque la regla solo admitía su sentido. Hallazgo: su confirmación de dos velas es una buena señal de que el precio se devuelve. Es la misma familia que el «rompimiento de 20 velas al revés», que ya está en el banco. Candidata para una prueba propia (sección 18, con la regla escrita antes): entrar al banco de la elección mensual en sentido contrario.

## 18. Su triángulo (31/10/2026, 09:12; escrita antes de probarla)

Lo que él vio (captura de las 09:08): el precio se mantiene dentro de sus líneas, una diagonal de máximos que bajan y otra de mínimos que suben, que se juntan unos 30 min más adelante. Pide una estrategia para ese caso, que se le avise por Telegram.

**Triángulo (velas de 1 min):** los dos últimos máximos de giro confirmados van bajando y los dos últimos mínimos de giro van subiendo; el precio cerró las últimas 10 velas entre las dos rectas. Giros de 10 y de 30 velas a cada lado (dos trazados).

**Estrategias:**
- E1 · Rebote dentro: dentro del triángulo, el máximo de la vela toca el techo → BAJA; el mínimo toca el piso → SUBE.
- E2 · Ruptura, como él: tras estar dentro, la vela cierra por encima del techo → SUBE; por debajo del piso → BAJA (se informa también al revés).

**Regla de decisión:** la de la sección 15. E1 en su sentido natural (el rebote); E2 en el sentido que él usa. Lo que pase se avisa en vivo por Telegram con su acierto; lo que no pase se le informa como contexto, con su acierto, sin decir «opere».

**Resultado de la t32 (31/10/2026, 09:15; pruebas\t32_triangulo.py).** BTC y ETH, giros de 10 y 30, 2021 a octubre de 2026: el rebote dentro del triángulo y la ruptura aciertan del 46 al 53 % en cualquier sentido (cara o sello), con 1.000 a 3.500 señales. **No entra.** El triángulo dice que se viene un movimiento, no hacia dónde. Se avisa como contexto («triángulo: sin ventaja, 50/50»), sin decir «opere».

## 19. Investigación cuantitativa y plan v5 (03/11/2026)

Pedido de Nicolás del 03/11: estudio multidimensional (temporalidad, dirección, volatilidad, liquidez y volumen, estructura, estadística), Markov y HMM, regímenes, agrupamiento, autocorrelación, anomalías, validación fuera de muestra, sobreajuste, binarias frente a futuros, footprint, Bookmap, SMC, CRT, ICT, opciones, macro y Banco Mundial; meta de 85,7 %; segunda opinión de otra IA; unificar en BTC/USDT; semáforo papel → real.

- Reglas escritas antes en cada guion de `cuant/` (C1 a C7). Elección con 2021-2023; juicio intacto en 2024 a sep-2026 y oct-2026.
- Resultado: lo único con ventaja es la reversión de corto plazo (ruptura de 20 velas de 5 min al revés: BTC 56,1 % en la prueba y 61,7 % en octubre; impulso de 15 min al revés: 54-55 %; anomalías: 54-56 %). SMC, ICT, CRT, killzones, área de valor, libro de órdenes y opciones quedan entre 49 y 52 %. El cruce de dimensiones no mejora (cartera: 52,8 %). Ninguna celda llega a 85,7 %. No hay mano caliente.
- Semáforo (C7): encender el real cuando las últimas 100 de papel van en 58 % o más suma 1 a 1,5 puntos sobre el azar; el del día anterior no sirve.
- BTC: ningún procedimiento del banco pasa hoy la valla mensual; la ruptura al revés la pasa justo en 12 meses. ETH va mejor (58,5 %).
- Segunda opinión: Nemotron 3 Super y DeepSeek v3 (por OpenRouter, por Tor) coinciden en lo central y añaden walk-forward con purga, latencia y grabar microestructura.
- Desde hoy manda el PLAN-v5.md. Detalle en `cuant/INFORME-INVESTIGACION-CUANTITATIVA-2026-11-03.md`.
