# Operativa de las binarias (lo que el agente sabe antes de operar)

Versión del 04/11/2026, 13:13 (hora de Colombia). Manda el PLAN-TOTAL.md (v7, congruente: solo devolución, solo BTC, real solo en las señales SÍ y con su 76 %); la evidencia está en `INFORME-TOTAL.md`. Pulso la lee antes de cada lectura del mercado de 15 min y cita su versión; el agente de Claude (`PROMPT-OPERADOR.md`) la lee al empezar.

## Qué se opera

- Contratos de Evento de Binance, unificado en BTCUSDT desde el 03/11 (orden de Nicolás). ETH se sigue midiendo en silencio. Plazo de 10 min.
- Para no perder con pago 0,85 hay que acertar 54,1 % (con 0,80, 55,6 %). Lo que quede por debajo pierde dinero.
- Todo en papel hasta su orden expresa (archivo `REAL_AUTORIZADO` en la caja y el teléfono). En real, la apuesta la toca él a mano (Binance prohíbe bots en los Contratos de Evento) y sin apalancamiento.
- Binance liquida con su índice de precio, no con el último precio de futuros: desde el 04/11 cada apuesta guarda los dos resultados.

## Mesa de binarias y vigía de 15 min (04/11, 18:30)

- Además de lo anterior, el PC tiene la Mesa (`mesa/`): binarias de 15 min de Binance Wallet con API oficial, con botones que él oprime. El programa analiza solo, sin IA. La caja y el teléfono corren `quince.py`: porcentaje de aciertos de las últimas 25, notas de voz a 68 % y 75 %, y fotos de las líneas cuando el mercado reacciona. Ver PLAN-TOTAL.md, 7c.

## Dónde está el centinela

- Corre en la caja T95H (principal) y en su teléfono (respaldo), 24/7. El PC ya no lo ejecuta: Pulso no ve su estado y no debe decir «centinela caído» por eso.
- Las apuestas en papel de BTC y el SÍ o NO de cada señal le llegan por Telegram desde la caja (o desde el teléfono si la caja no responde). Desde el 04/11 cada SÍ o NO llega como foto con las cinco líneas, cada SÍ cerrado trae su comprobante en PDF con enlaces a las velas oficiales de Binance y a las 00:15 llega el resumen del papel del día anterior.
- Si la caja deja de latir 10 min, el teléfono avisa que toma el relevo y, cuando ella vuelve, que calla (desde el 04/11; la noche del 03 al 04 se durmió sin aviso).
- Ningún agente opera solo, ni aquí ni en la nube: los Contratos de Evento no tienen API (comprobado otra vez el 04/11 en la documentación oficial de Binance) y Binance prohíbe los bots. Tampoco con la sesión de su cuenta: la puerta interna de la app, copiada en GitHub, viola los términos y arriesga la cuenta con su saldo (en octubre de 2025 Binance cerró más de 600 cuentas por herramientas no autorizadas). El agente decide, avisa y audita; el toque es de él.

## SÍ o NO (su regla desde el 04/11)

- En cada señal del núcleo: «SÍ OPERAR» si el papel de hoy va sumando (neto mayor que 0, con apuestas ya cerradas y entrada 60 s tarde), ningún SÍ ha perdido hoy y el interés abierto de futuros no subió en los 15 min previos; si no, «NO OPERAR (solo papel)» con el motivo. El día empieza en NO.
- Real solo con su 76 % (orden del 04/11): el SÍ pasa a real si 19 de las últimas 25 apuestas de papel del núcleo acertaron; si no, «Espere». Probado (P17): enciende pocas veces y no acierta más que el SÍ solo.
- La primera pérdida de un SÍ lo apaga hasta el día siguiente. Jamás apalancamiento. Tope por apuesta: 16 % del saldo (5 USDT necesitan 31,25 USDT o más).
- Solo velas cerradas: la decisión espera el cierre de la vela de 5 min. Una vela de confirmación extra se probó (P16) y baja el acierto.
- Medido (C9, 2024-sep 2026): el SÍ acierta 55,5 % con 1,8 apuestas al día; el núcleo, 54,4 %. Caída máxima de 0,45 M COP frente a 1,79 M de apostar siempre.

## El toque (lo único que hace él)

- Cuando llega «SÍ OPERAR · REAL»: en la app, Futuros → Contratos de Evento → BTCUSDT → 10 min → el sentido del aviso (SUBE o BAJA) → 5 USDT. Cuanto antes: cada minuto de demora cuesta cerca de 1,7 puntos.
- Antes de tocar, mire el pago que ofrece la app: por debajo de 0,85, no entre.
- Para tocar en segundos: un tono propio para el chat del bot en Telegram y la app abierta en la pantalla de Contratos de Evento.
- P1: anotar el pago y los segundos de demora de 20 apuestas, para recalcular el equilibrio.

## Lo que funciona (a ciegas, 2021 a octubre de 2026)

1. Apostar a que el precio se devuelve:
   - ruptura de 20 velas de 5 min, al revés (el núcleo): BTC entrando 60 s tarde 54,4 % en 2024-26 y 60,7 % en octubre de 2026 (al cierre, 56,1 %): tocar en segundos;
   - caída o subida de 15 min mayor que una desviación, al revés: 54-55 %;
   - movimiento extremo de 10 min (z ≥ 4), al revés: 54-56 %;
   - tres tramos de 10 min iguales, al revés: 53,8 %.
2. Las «Apuesta en papel» de las cuentas REGLA y BTC FIJO (el centinela v4 y su sistema del mes) son medición: no se tocan en real. El real solo sale del SÍ.

## Defensas que sí sirven

- «NO OPERAR» de la caja: no tocar nada en real.
- Pago que ofrece la app por debajo de 0,85: no entrar (con 0,80 hace falta acertar 55,6 %).
- El volumen alto solo sirve como defensa en las reglas del banco (t27); sobre el SÍ no ayuda (P3b, −0,46 puntos).

## Lo que NO funciona (no usar para decidir)

- La meta de 85,7 %: ningún estado de mercado la alcanza a 10 min.
- SMC, ICT y CRT a 10 min: FVG, order blocks, AMD, área de valor, premium y discount, OTE, SMT, killzones, silver bullet, CRT de 1 h y 4 h (49-52 %).
- Cruzar todas las dimensiones: las mejores combinaciones caen de 65-68 % a 53-62 % y la cartera de todas pierde (52,8 %).
- La «mano caliente»: tras acertar se acierta igual o menos que tras fallar. Operar más «cuando hay suerte» no da ventaja por apuesta.
- Probados el 04/11 (C9), sin ventaja: flujo informado o VPIN, régimen por autocorrelación, horas del día y metaetiquetado (de −1,2 a +0,5 puntos, ninguno significativo).
- Operar solo con todo a favor; seguir la ruptura de sus líneas; el toque de la segunda resistencia; MHI; torres gemelas; martingala; las estrategias «del 98 %»; el triángulo (anuncia movimiento, no sentido).
- Noticias, Wall Street y Banco Mundial como pronóstico de 10 min: son contexto.

## Contexto que el agente menciona sin decidir con él

- Sus cinco líneas en 1 min (Pulso cada 5 min y la foto de cada SÍ o NO, idénticas píxel a píxel): techo y piso sobre sus máximos y mínimos (azul), techo y piso cortos desde el inicio de la última caída o subida (ámbar) y la recta de la mitad (violeta). Probadas como filtro del SÍ (P18): no suman (+0,30 puntos sin diferencia con el azar y peores en los otros tramos). Son para mirar.
- Su opinión en Centro nocturno: se cita y se compara con el precio.
- Libro de órdenes a ±1 % (52 %), flujo de órdenes (52 %, al revés), opciones de BTC (GEX positiva frena los movimientos; gamma flip; muros de calls y puts), DVOL, VIX, S&P 500 y bono de 10 años: contexto.
- El índice de estabilidad (t33): con confianza de 56 % o más acertó 55,6 % a ciegas en 2024-26.

## Cómo decide el agente cada 15 min

1. Recuerda que el centinela vive en la caja y el teléfono; no lo da por caído porque el PC no lo vea.
2. Mide el precio de la última hora y de 15 min, compradores contra vendedores y el volumen de BTC frente a su semana.
3. Dice un solo veredicto: solo cuenta el «SÍ OPERAR» de la caja (o del teléfono, si la caja cae), con su 76 % para el real, tope del 16 % y sin apalancamiento; sin SÍ, no se toca nada. Mira el latido de la caja en la red de la casa para decir si vigila.
4. Lo demás (sus cinco líneas, el índice de estabilidad, el estocástico, las noticias y su opinión) es contexto: se menciona sin decidir con ello. La CANDIDATA y el DISPARO se retiraron el 04/11: sugerían apostar fuera del SÍ.
