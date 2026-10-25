---
name: trader-btc-en-curso
description: "Agente de trading SEGUIDO de BTC (ciclos de segundos a minutos) en Ingresos/trader-btc: corre en papel desde el 20/10/2026; lo medido (seguido pierde por comisiones), cómo se maneja, las trampas y las decisiones pendientes de Nicolás."
metadata:
  node_type: memory
  type: project
  originSessionId: f76b4f0f-3a8b-4a8e-b54b-3b26f7b8e523
  modified: 2026-10-21T02:26:57.786Z
---

Pedido el 19/10/2026 y corregido el 20/10: operar BTC «seguido», un ciclo tras otro de segundos a minutos, leyendo el mercado de segundos a días, con probabilidad por ciclo y pausas por tandas de 100 a 800 ciclos, en papel primero ([[trading-seguido-no-por-dias]]). El diseño del 19/10 (velas de 5 min a 1 h) quedó en `banco.py`, `estrategias.py` y `simulador.py`, sin usar.

**Dónde y cómo** (`C:\Users\ni109\Ingresos\trader-btc\`, biblioteca estándar, git local sin remoto, 33 pruebas en verde):
- `agente.py` corre oculto con pythonw desde el 20/10 20:22. Se arranca con `ARRANCAR AGENTE.cmd` y se para con `PARAR AGENTE.cmd` (o creando el archivo PARAR). PAUSA impide abrir ciclos; REANUDAR quita la detención de una tanda. Panel en `panel.html`; estado en `estado.json`; diario en `diario/`. Informe para él en `INFORME-TRADING-SEGUIDO.md`.
- Cuatro libros en papel de 9,7 USDT: contado (marcado «sin ventaja demostrada»), BTC/FDUSD de creador (el único válido, por poco), futuros (sin ventaja) y un testigo que opera seguido sin filtro. No hay ningún camino de órdenes: dinero real imposible desde este archivo.
- `banco_rapido.py` entrena y elige (unos 6 min con caché); deja `modelos/trading-seguido.json`. `pruebas/paridad_motor.py [fecha] [días] [modelo] [--siempre]` compara banco contra agente: 587 ciclos idénticos el 20/10.
- Datos: velas de 1 s de BTCUSDT y BTCFDUSD de mayo al 19/10 (`descargar.py segundos ... --directo`), contado de 1 min desde 2023, métricas de 5 min y financiación (el mes en curso por la API).

**Medido (tramo final 16/09-19/10, sin tocar):** la dirección a minutos es casi azar (AUC 0,51-0,56; la probabilidad de subir nunca llegó a 0,85). Operar seguido sin filtro: contado −17 %, BTC/FDUSD −39 %, futuros −21 %, testigo −16,9 % (el azar, −16,1 %). Con la regla de ganancia esperada neta casi no entra (4-5 ciclos al mes). La causa es la comisión por ciclo (0,04-0,20 %) frente a movimientos de 0,05-0,14 % con BTC al 0,94 % diario.

**Trampas que costaron tiempo:**
- Por Tor, data.binance.vision baja a 0,02-0,07 MB/s (todos los circuitos pasan por el puente del Buscador); su regla permite ir directo a Binance: 344 archivos en 3 min.
- WebSocket de futuros: `/ws` y `/stream` conectan pero ya no mandan nada; usar `/market/stream` y `/public/stream`.
- pythonw lanzado con Start-Process deja `sys.stdout` en None: reconfigure revienta en silencio. Windows 11 frena el proceso oculto (EcoQoS); se quita con SetProcessInformation(ProcessPowerThrottling). El bookTicker de BTCUSDT (cientos de mensajes por segundo) atrasaba las velas: se usa depth5@1000ms. La API de Binance llegó a tardar 13 s: nunca dentro del ciclo por segundo.
- La agenda de Trump se mudó a rollcall.com/factbase; el CSV de media-cdn.factba.se responde por Tor.
- El agente arma la vela de 1 min solo con segundos que tuvieron operaciones; si no, no coincide con la de Binance.

**Orden suya del 20/10, 20:40:** «pon el agente a hacer pruebas suponiendo que empiezas operando con 40k pesos colombianos y déjalo ahí moviéndose por lo menos hasta que yo te diga». Antes: «proceda a probar por ahora aquí; luego usaremos plugin y/o lo adaptaremos para enviar las operaciones directamente en la nube». Hecho:
- Capital por libro: 40.000 COP = 12,5871 USDT, a 3.177,85 COP por USDT (mediana de 20 avisos de compra en Binance P2P, la tasa real que le darían; la TRM de datos.gov.co no se toca). Queda en `config.json` (capital_cop, tasa, capital_usdt) y el panel muestra los pesos.
- Arranque con Windows: valor `AgenteTradingSeguido` en HKCU\...\Run (pythonw -I agente.py). Se quita con `QUITAR ARRANQUE AUTOMATICO.cmd` y se pone con `PONER ARRANQUE AUTOMATICO.cmd`. Candado `agente.lock`: nunca corren dos agentes.
- Probado en vivo el 20/10: pausa (30 s frenados), corte de golpe con un ciclo abierto (al volver lo cierra con «REINICIO» y los conteos siguen), arranque y parada con los .cmd. El ensayo previo de 9,7 USDT quedó en `diario/ensayo-9.7usdt-2026-10-20/`.
- No pararlo hasta que él lo diga.
- **DETENIDO por su orden el 20/10 a las 21:26 («detén todo por ahora»):** turnos de CronCreate cancelados, agente parado limpio (los cuatro libros en 40.000 COP, sin posiciones) y arranque con Windows quitado. Para reanudar, solo si él lo pide: `ARRANCAR AGENTE.cmd`, `PONER ARRANQUE AUTOMATICO.cmd` y volver a crear los turnos cada 5 min.
- **Decido yo, Claude Code, sin API (20/10, 21:20):** «estamos perdiendo dinero… la idea es que las decisiones las tomes tú como si fueras el agente»; y al ver una prueba con `claude -p`: «no uses la API de Anthropic, haz de cuenta que eres literalmente tú, Claude Code». Montado así: libro «claude» (futuros, papel) que ejecuta lo que escribo con `python -I claude_orden.py comprar|vender|esperar|cerrar --objetivo --stop --minutos --razon`; leo `resumen-claude.txt` (se rehace cada 5 s); turnos con CronCreate cada 5 min (solo en la sesión que lo creó; muere con ella y caduca a los 7 días). Nada de `claude -p`, OpenRouter ni DeepSeek para decidir. La pérdida que vio era del testigo (−0,85 % en 3 ciclos, compraba sin filtro); se retiró.
- El agente no tiene ventana (pythonw): el 20/10 preguntó «no veo el agente, ¿dónde está?». Lo que se ve es el panel: acceso «Panel del agente de trading» en su escritorio; se abre en el Buscador (LibreWolf) y se recarga cada 5 s. En el Administrador de tareas aparece como pythonw.exe.

**Para la nube (más adelante):** Binance responde 451 a las IP de EE. UU., también a servidores en la nube de esas regiones; hará falta un servidor fuera de EE. UU. Y su regla de privacidad dice que ninguna plataforma ni IA de terceros vea sus operaciones: decírselo antes de montar nada ahí.

**Pendiente de Nicolás:** (1) sumar su MEZCLA de 1 h (única con ventaja medida, junio) como libro aparte; (2) clave nueva de la red de pruebas en `claves-testnet.env` (las de `arbitraje-cero-gas\.env` y `Downloads\api binance.txt` son de su cuenta REAL: no se usan); (3) dónde y cómo irá a la nube. La consulta de la TRM a datos.gov.co la detuvo él: no relanzarla sin preguntar.

**Why:** quiere ingresos operando seguido con poco dinero, sin que nadie vea sus operaciones, y ya perdió confianza por soluciones dadas por buenas sin probar ([[no-decir-que-funciona-sin-probarlo]]).
**How to apply:** retomar desde «Pendiente»; mirar `estado.json` y el diario antes de opinar; ningún flujo de agentes sin su sí ([[ultracode-activado]]); reglas de broker y privacidad en [[trading-broker-y-privacidad]]; el agente gasta 0,55 % de un núcleo ([[granja-ingresos-sin-desgastar-equipo]]).
