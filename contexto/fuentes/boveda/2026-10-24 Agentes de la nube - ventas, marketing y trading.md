---
tags:
  - area/automatizacion
  - area/cripto
  - tipo/sesion
creado: 2026-10-24
estado: activo
---

# 2026-10-24 Agentes de la nube: ventas, marketing y trading

Proyecto: [[Agentes de la nube]].

## Qué pidió

Que el agente de ventas no fabrique solo cosas de dinero, después de mirar en internet qué se vende más en Gumroad. Que se pensaran estrategias nuevas para otro agente. A las 10:00 corrigió: ese otro agente es un **socio de marketing** y va a la nube, no en local. Que haya un agente en la nube investigando cómo operar con Claude como quien decide, con todas las estrategias de la bóveda. Que los agentes corran uno por uno, que dos de ellos lean su Telegram cada 12 horas, y que al terminar se le escriba por Telegram. A las 10:15 precisó: libertad y lo último para el de marketing; day trading de al menos 3 operaciones al día, otros mercados y papel de planeación para el de trading.

## Qué se hizo

- **Estudio de Gumroad** (`Ingresos\gumroad\ESTUDIO-MAS-VENDIDOS-GUMROAD.md`), con fuentes abiertas por Tor. Del código abierto de Gumroad sale lo decisivo. Un producto solo entra en Discover con una venta real y si el vendedor tiene método de pago y la revisión aprobada. Discover ordena por la comisión de tres meses, y la búsqueda exige todas las palabras sin reconocer plurales. La cuenta lleva 0 ventas (leído en la API).
- **Agente de ventas**: rota seis áreas (el dinero, una vez de cada seis), alterna apps y guías interactivas, usa la categoría del tema y escribe la ficha para el buscador. El `revisar.py` nuevo se probó con los 8 productos guardados.
- **Agente socio de marketing** y **agente de planeación de trading**, creados en la nube, cada 12 horas. El de trading lleva el expediente: la MEZCLA de 1 h, la IA como filtro, el trading seguido con sus modelos por meses, el plan de riesgo, las funciones del agente del PC y lo demás de la bóveda.
- **Turnos**: las aprobaciones de Gmail chocaban a diario con el agente de ventas y se movieron de las 8:00 a las 10:00.
- **Telegram**: dos mensajes enviados por el bot «Centro nocturno», por Tor.

## Hallazgos y errores

- Las rutinas no admiten variables de entorno propias, y el clasificador bloqueó, con razón, sacar el token del bot a la sesión: lo pone él en el entorno de la nube.
- `TZ=America/Bogota date` de Git Bash da la hora UTC: el encargo salió fechado cinco horas adelante y se corrigió.
- La rutina de aprobaciones de Gmail, de septiembre, lleva el token de su bot escrito en el texto del prompt.

## Pendiente

- Él: poner `TELEGRAM_TOKEN` en el entorno de la nube, y subir su documento en Gumroad para que la tienda pueda entrar en Discover.
- Su sí para el commit de los cambios en `gumroad` y `trader-btc`.
- Rehacer `probar_prompt.py`, desfasado desde el 23/10.

## Segunda parte, noche: los agentes en marcha

**Qué pidió.** Revisar qué pasó con los agentes, arreglar lo que fallara y ponerlos a moverse ya. Que marketing, «uno de los más importantes», tenga libertad total y no proponga nada de pago; que tengan más tiempo para pensar e investigar; que le avisen por Telegram cómo van; y que yo revise sus pasadas y los vaya puliendo. Por Telegram pidió además una lista de permisos que les sirva de compañera para operar y corregirse solos (mensaje 766), y que trading le avise cómo quedó el plan (767).

**Qué se hizo.**
- Diagnóstico: los dos agentes no leían Telegram porque el token no estaba en su entorno y porque la red de ese entorno bloqueaba casi todo. Él creó el entorno `env_01U1UuDgLxFk8ajhs71bDzrM` con el token y la red completa. Una rutina de diagnóstico confirmó que el token es válido, que no sobra ninguna variable y qué sitios abren.
- Prompts v2 de marketing y de trading: cada 6 horas, lista de PERMISOS, AUTOCORRECCIÓN, entregas mínimas por pasada y `tg.py` con reparto de mensajes. Marketing pasa de investigar a ejecutar (leads con respuesta redactada, piezas listas, plan de tres acciones). Trading opera en papel con precios reales y verifica estrategias con velas de Binance (data.binance.vision), Coinbase y Kraken.
- Horarios: marketing a las 0:00, 6:00, 12:00 y 18:00; trading a las 21:00, 3:00, 9:00 y 15:00.

**Hallazgos y errores.**
- Error mío, corregido: le dije que la rutina de aprobaciones de Gmail le quitaba los mensajes a los otros dos con `offset`. No es así: las de Gmail usan otro bot, «Informes_gmail», y su token va escrito en el prompt desde septiembre a propósito.
- Marketing no crea cuentas ni publica por su cuenta aunque él lo autorizó: las plataformas cierran los perfiles que maneja un bot. Le deja todo listo con los pasos.
- Reddit, Workana, Upwork, Product Hunt e Indie Hackers bloquean los servidores en la nube (403); la API de Binance da 451.

**Pendiente.**
- Él: subir su documento en Gumroad y configurar la cuenta donde Gumroad le deposita (no es un pago).
- Su sí para el commit de los cambios en `gumroad` y `trader-btc`.
- Revisar las primeras pasadas v2 y pulir los prompts con lo que entreguen.
