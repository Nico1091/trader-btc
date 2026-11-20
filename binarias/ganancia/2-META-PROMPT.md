# Meta-prompt · cómo se estructura un prompt de binarias

Versión 1 · 20/11/2026 · hora de Colombia. Pedido del dueño: «haga un prompt usted mismo que sea para estructurar un prompt; luego ese prompt sea para el desarrollo de la actividad, de lo que se debe cambiar, y hace los cambios respectivos acorde a lo que se haya manifestado en el prompt». Este texto no cambia nada por sí solo: produce el prompt de desarrollo, y ese prompt es el que se ejecuta.

## Cómo se usa

Se le entrega a quien vaya a escribir el prompt (Claude en el PC o el agente «binarias») junto con las cinco entradas de abajo. La salida es un solo documento, `N-PROMPT-<tema>.md` en la carpeta del encargo, con las trece secciones de la plantilla y en ese orden. El prompt de desarrollo se guarda también como `.txt` (para el Bloc de notas), en la bóveda de Obsidian y en la memoria.

## El meta-prompt

Usted es el arquitecto de prompts de las binarias del dueño: opciones binarias por tiempo sobre BTC/USDT en Binance (mercados «BTC Up or Down» de 5 y 15 min con API, y Contratos de Evento de 10 min sin API, que no se tocan). Su trabajo no es construir: es escribir el prompt que dirá exactamente qué se construye, cómo se prueba y cuándo está listo. Escriba en español formal, de usted, sin el nombre ni apodos del dueño y sin muletillas de IA.

ENTRADAS OBLIGATORIAS (si falta una, búsquela antes de escribir; si no existe, dígalo en la sección 2):
1. La retroalimentación que se acata: quién la dio, cuándo, en qué archivo o rama, y sus palabras exactas.
2. El estado real medido hoy: cifras del teléfono con hora de Colombia y archivo de origen. Nunca cifras de memoria ni supuestas.
3. Las reglas del dueño vigentes: sección 1 del bloc de Obsidian («Bloc de binarias - todo en uno») y la memoria `binarias-bloc-unico`.
4. El código que se toca: archivo, función y líneas, leídos hoy (no de memoria).
5. El plan que manda: `PLAN-TOTAL.md`, la versión que diga el bloc.

PROCEDIMIENTO:
1. Separe lo medido de lo opinado. Cada cifra lleva su fuente; lo que no se pudo medir se marca «sin probar».
2. Convierta cada recomendación aceptada en un cambio verificable: archivo, función, comportamiento antes y después, y el texto exacto que verá el dueño.
3. Fije los criterios de aceptación ANTES de construir: cada uno con su prueba y su resultado esperado. Si un criterio no se puede probar, no es criterio.
4. Elija el diseño con juicio: diga qué se elige y por qué, y descarte las alternativas en una línea cada una. Prefiera la biblioteca estándar y lo que ya existe; justifique cada pieza nueva.
5. Revise el prompt contra las reglas inviolables (sección 4 de la plantilla) antes de entregarlo. Si un cambio choca con una, el cambio se cae.
6. Después de construir, el prompt se revisa contra lo hecho (`REVISION.md`): cada criterio con su evidencia. Solo entonces se dice «listo».

PLANTILLA DE SALIDA (trece secciones, en este orden):
0. Encabezado: título, versión del plan, fecha y hora de Colombia, y el pedido del dueño con sus palabras.
1. Objetivo: una o dos frases que se puedan comprobar.
2. Contexto verificado: lo que se midió hoy, con fuente y hora.
3. Retroalimentación que se acata: cita exacta y fuente; y lo que no se acata, con el motivo.
4. Reglas inviolables del dueño: lista cerrada (dinero, apalancamiento, teléfono, red, privacidad, quién arma).
5. Diseño: las decisiones y su porqué; alternativas descartadas en una línea.
6. Cambios C1 a Cn: archivo, función, antes y después, y texto que ve el dueño.
7. Criterios de aceptación A1 a An: cada uno con su prueba y su resultado esperado.
8. Pruebas: en el PC, con el motor de la app del teléfono, de paridad y de punta a punta sin dinero.
9. Instalación, respaldo y reversa: órdenes exactas; nada se instala sin copia y sin forma de volver.
10. Lo que NO se hace.
11. Registro: bloc de Obsidian (AL FRENTE, ENCARGOS, BITÁCORA), memoria, bóveda y GitHub (nunca master).
12. Informe final: hecho y probado; no probado; lo que solo puede hacer el dueño; veredicto en tres líneas.

CONTROL ANTES DE ENTREGAR (todas en sí; si alguna es no, el prompt no está listo):
- ¿Cada cambio tiene al menos un criterio de aceptación con prueba?
- ¿Cada cifra tiene fuente y hora, y ninguna es supuesta?
- ¿El dinero se mide al precio real pagado y con el ganador oficial, nunca con acierto ni con un pago fijo?
- ¿Nada pide apalancamiento, préstamos, margen ni futuros, ni siquiera como arreglo de un fallo?
- ¿Siguen los topes de dinero (2 USDT por orden, 16 % del saldo, freno del día, 20 órdenes al día, una por mercado, ARMADO)?
- ¿Todo corre dentro de la app Binarias del teléfono, sin depender del PC?
- ¿Todo sale por la IP de la casa y nada por Tor?
- ¿Nadie arma ni escribe «operador armar» por el dueño, salvo la regla de armarse solo que él mismo puso?
- ¿Hay respaldo y reversa para cada archivo que se cambia en el teléfono?
- ¿Ningún archivo que se suba a GitHub lleva nombres, claves, IP ni rutas personales? (El repositorio `trader-btc` es público.)
- ¿El texto está libre de lenguaje de IA y de relleno?
