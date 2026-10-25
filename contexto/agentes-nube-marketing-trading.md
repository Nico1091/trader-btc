---
name: agentes-nube-marketing-trading
description: "Agente socio de marketing y agente de reclutamiento y planeación de trading en la nube, cada 6 h desde el 24/10/2026 noche, con Telegram (bot Centro nocturno), lista de PERMISOS y autocorrección; entorno, horarios, red comprobada y trampas."
metadata:
  node_type: memory
  type: project
  originSessionId: 097c480a-5c5a-4c9e-9725-4c0c536eebc2
  modified: 2026-10-24T22:48:15.745Z
---

Pedidos el 24/10/2026 (encargo y registro en `Ingresos\ENCARGO-AGENTES-NUBE.md`). Los dos leen y contestan su Telegram y le escriben un resumen en cada pasada.

**Las dos rutinas** (Opus 5.5, solo el conector Gmail, entorno `env_01U1UuDgLxFk8ajhs71bDzrM`, que él creó el 24/10 con `TELEGRAM_TOKEN` y red completa):
- **Marketing** `trig_012gXSJD8v7AuYGGDGXJSxor`, cron `0 5,11,17,23 * * *` (0:00, 6:00, 12:00 y 18:00 de Colombia). Prompt v2 en `Ingresos\marketing\PROMPT-AGENTE-MARKETING.md`. Él lo llama «el más importante». La investigación base (temas 1 a 4) está hecha: desde el 24/10 noche **ejecuta**. Cada pasada entrega como mínimo leads de menos de 72 h con la respuesta redactada, tres piezas listas para publicar, un plan de tres acciones de 15 minutos para él y un tema investigado a fondo. Él pidió «sin límite, que cree perfiles a mi nombre»: el agente tiene libertad total para decidir y producir, pero **no publica, no crea cuentas ni escribe a terceros**. Se lo deja listo a él, con los pasos. Nada de gastos: «la cuenta donde Gumroad le deposita», nunca «método de pago», porque él entendió que había que pagar.
- **Trading** `trig_01HhTpY4sVUqaj1ui3qi7wyQ`, cron `0 2,8,14,20 * * *` (21:00, 3:00, 9:00 y 15:00). Prompt v2 en `Ingresos\trader-btc\PROMPT-AGENTE-TRADING-NUBE.md`. Recluta estrategias y planea. Opera en papel con precios reales y órdenes condicionadas de hasta 6 h, y las cierra con velas de 1 minuto contra el azar. Lleva el REGISTRO JSON al final de cada correo. Mínimo por pasada: verificar una estrategia con 6 meses de datos y reclutar 5 nuevas. Nunca dinero, claves ni cuentas.
- **Trading v3 (24/10, 18:20, orden suya: «Claude como tal opera, no un código; tú debes operar» y «que sí o sí genere ganancias»):**
  - **Libro CLAUDE:** el agente decide cada operación con su juicio, sobre las señales del catálogo. Anota decisión, razón y confianza antes del resultado. Arranca con 40.000 COP en papel y su plan de riesgo.
  - **Aprendizaje:** diario de cada decisión, «reglas_de_claude» de 5 a 15 que salen de sus resultados, calibración de la confianza y tamaño según resultados.
  - **Entrenamiento a ciegas:** 20 decisiones por pasada sobre momentos pasados en porcentajes, sin fecha ni precio, escritas antes de revelar el resultado.
  - **GUÍA DE CLAUDE CODE:** sección que yo actualizo tras revisar cada pasada.
  - **Meta honesta:** ganar neto o no entrar, con órdenes condicionadas en vez de forzar operaciones.
  - **Hallazgo base:** de 10 estrategias probadas con 25 meses de 1 min de Binance, ninguna gana neta con 0,05 %/lado. La mejor pista es E09 (ATR de Concretum, +10,2 % bruto en la prueba), que necesita ~0,03 %/lado: probar órdenes de creador.
- Los dos tienen la lista **PERMISOS** (sin preguntar / lo decide Nicolás / nunca) y la **AUTOCORRECCIÓN**, pedidas en su mensaje 766.

**Telegram** (bot «Centro nocturno», @Centronocturnobot, el del publicador): `tg.py` sin offset, idéntico en los dos prompts y en `Ingresos\tg.py` (probado por Tor el 24/10). Muestra a qué mensaje responde cada uno. **Reparto:** trading toma lo que empieza por «trading/trader», lo que responde a «[Trading]» y lo de mercados o cripto; marketing toma todo lo demás. «Telegram atendidos:» en cada correo evita respuestas dobles. Para leerlo yo desde el PC sin borrar nada: token en `~/.gumroad/telegram-token` (WSL Ubuntu-26.04, usuario rojo), curl por Tor `socks5h://…@127.0.0.1:9050`.

**Las de Gmail usan OTRO bot**, «Informes_gmail» (@Hdtdtdt_bot), con el token escrito en sus prompts desde el 25/09, a propósito. Su offset no toca Centro nocturno. **Error mío del 24/10:** le dije que sí; lo comprobé comparando el número de bot de cada token y se lo corregí.

**Red del entorno, comprobada el 24/10:**
- Abren Telegram, data.binance.vision, Coinbase, Kraken, Bitstamp, Gumroad (la API da 401 sin token), n8n.io y su foro, LinkedIn, Pinterest, Hacker News, Google y Hugging Face.
- La API de Binance da 451 (servidor en EE. UU.).
- Reddit, Workana, Upwork, Product Hunt e Indie Hackers dan 403: los propios sitios bloquean los servidores en la nube.
- La única variable puesta por él es `TELEGRAM_TOKEN` (46 caracteres, forma válida).

**Rutina de diagnóstico** `trig_01RNoQxaHEk6HmnZQ99TkDpa` («Prueba de entorno», Sonnet, apagada, se lanza a mano): imprime solo los NOMBRES de las variables y el código de cada sitio. Los registros cortan las salidas largas, así que hay que imprimir corto.

**Trampas:**
- 24/10 18:11: la pasada de trading se cortó por el límite de uso antes del correo y se perdió entera. Sus hallazgos se pasaron a la GUÍA DE CLAUDE CODE (v3.1, 19:30), con la regla «entregar el correo antes de seguir investigando». Si vuelve a pasar: `get_run_log` y copiar lo medido a la guía.
- En Git Bash, `TZ=America/Bogota date` da la hora UTC (no conoce el nombre): usar `TZ=UTC+5 date` o Python.
- `update` con `session_request` cambia también `job_config`.
- El prompt local y el de la nube se comparan con Python (`get`/`list` van a un archivo).
- Él edita prompts a mano en la web: comparar antes de pisar. El 24/10 añadió «dentro y fuera de Gumroad tienes que captar leads y compradores», y se conservó.

**Why:** quiere que sigan solos aunque esta sesión se quede sin cupo, hablarles por Telegram y que avancen rápido, con más tiempo de pensar.
**How to apply:**
- Para ver cómo van: `list_runs` y `get_run_log`.
- Si se agota el cupo del plan, bajar a cada 8 h.
- Pasadas manuales: el 24/10 a las 19:35 autorizó «lanzar los agentes por tu cuenta por ahora… hasta que sientas que estén consolidados». Mientras dure la consolidación las lanzo yo, de una en una y sin cruzarlas con las programadas, porque gastan del mismo cupo que la sesión. Consolidadas, vuelve la regla: ninguna sin su sí ([[no-usar-agentes]]). Subagentes en mi sesión siguen prohibidos.
- Marketing v5 (24/10, 20:10): Reddit por Arctic Shift (gratis, casi al día), foro «Hire a Pro» de Make, entregar el correo primero, «PEDIDO PARA EL FABRICANTE» (el fabricante lo lee a las 8:00 y responde en su correo) y **publica solo** en Bluesky, LinkedIn y Threads cuando él guarde en el entorno `BLUESKY_HANDLE`+`BLUESKY_APP_PASSWORD`, `LINKEDIN_TOKEN` o `THREADS_TOKEN` (scripts probados contra un servidor de imitación y con permisos falsos contra las API reales). Límites: 1 por pasada en Bluesky y Threads, 1 al día en LinkedIn (L-V, pasada de 6:00 o 12:00); nada de respuestas, mensajes, seguir ni reacciones. Bright Data descartado por él («no lo voy a utilizar»).
- Versiones vigentes (24/10, 21:30, verificadas idénticas a los archivos locales): marketing v6 y trading v3.3. Trading 21:02 salió limpia: REGISTRO v3, libro CLAUDE estrenado (40.000 COP, R1-R7), ciegas 4/6 (+3,04 % vs −0,33 %), P05b (E09 con entrada de creador) +4,9 % en 84 operaciones de prueba pero pierde con costo doble, y criterio_dinero_real propuesto (200 ops de prueba + 60 en papel en 4 semanas, neto con costo real y no negativo con el doble, p95 vs azar, racha ≤10, caída ≤15 %, 100 ciegas p90, y su sí). Siguiente para P05b: historia desde 2019, financiación y capital mínimo para el tema 14.
- **Trampa de Gmail:** el conector devuelve cada enlace envuelto en `https://www.google.com/url?q=…&source=gmail&ust=…&sa=E` (caduca). Los dos prompts llevan la fórmula para desenvolverlo: `re.sub(r'https://www\.google\.com/url\?q=([^&\s"]+)&source=gmail&ust=\d+&sa=E', lambda m: urllib.parse.unquote(m.group(1)), texto)`. Sin ella, el REGISTRO crece en cada pasada y marketing publicaría enlaces de Google.
- Guía paso a paso para conectar Bluesky, LinkedIn y Threads: se la mandé por Telegram (bot Centro nocturno) el 24/10 a las 20:10, tres mensajes con el prefijo «[Claude Code]»; copia en `~/.claude/jobs/f30b2748/tmp/tg_1..3.txt` mientras dure el trabajo.
- **LinkedIn no se publica en automático** (condiciones de su API, 3.1(26)): el agente le manda el texto listo por Telegram y él publica. Pendiente: sacar `linkedin.py` y la regla de LinkedIn del prompt de marketing en la próxima subida.
- **Bluesky (24/10, 21:35):** él creía que yo ya tenía la credencial; no está en la memoria, la bóveda, el PC, Linux ni en los entornos `env_01UtUE…` (vars: DEEPSEEK_API_KEY, DEEPSEEK_MODEL, TAOSTATS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) ni `env_01U1Uu…`. La cuenta que recuerda es la de «Lumiere» (joyería, rutina centro-nocturno de agosto), con la regla «PROHIBIDO reutilizar Lumiere: sus cuentas son EXCLUSIVAS de joyería». La otra red con permiso gratis que le dije el 12/09 es **Mastodon** (bóveda, 06-Transcripciones 2026-09-12).
- Dónde publicar (investigado el 24/10): sí LinkedIn (Share on LinkedIn, página básica obligatoria, generador de permisos de 60 días), Threads (app en modo desarrollo con él de probador), Bluesky (contraseña de aplicación). No: X (cobra por publicación desde 02/2026), Reddit (API cerrada desde 11/2025), Medium (sin claves nuevas), Hashnode (de pago). Pinterest solo con revisión por video. dev.to: no tiene cuenta.
- Dinero real en trading: su decisión del 24/10 19:40, «cuando realmente gane el papel… pensarla muy muy bien antes». No se arma conexión real. En la nube no sirve (451); si algún día va, es desde su PC y con clave nueva solo de operar, sin retiros. Sus claves reales están en texto plano en `Downloadspi binance.txt` y `arbitraje-cero-gas\.env`: le recomendé crear una nueva y borrar esas.
- Reglas: [[trading-broker-y-privacidad]], [[productos-sin-credenciales-ni-nombres]], [[linkedin-publicidad-revisado]].
