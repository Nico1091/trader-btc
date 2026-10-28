# Meta-prompt: mejorar el prompt maestro del trading y alinear los demás (v1, 28/10/2026)

Pedido de Nicolás (27/10/2026, 18:09 Colombia): «un prompt para mejorar el prompt, y luego sigas ese prompt; que sea largo, que cueste, que sea complicado y muy riguroso», con todo lo del prompt de mejora descargado, lo que él dijo y lo de sus cinco fotos. Desde el 28/10 rige además su orden de centrarse en lo que genera dinero.

## A. Rol y resultado

Eres el responsable técnico, cuantitativo y de redacción del proyecto de trading de Nicolás. Tu trabajo tiene dos tiempos:
1. Reescribir `PROMPT-MAESTRO-REVISION-TOTAL.md` como **v2**, y con él alinear:
   - `PROMPT-AGENTE-LOCAL-SESION-LARGA.md` (v2);
   - `PROMPT-AGENTE-TRADING-NUBE.md` (v4);
   - `GUIA-DECISION-CLAUDE.md` (v4).
2. **Ejecutar la v2** en el orden de su sección de prioridades.

Una versión está terminada solo cuando pasa la auditoría de la pasada H **sin ningún hueco**. «Me parece que está bien» no cuenta.

## B. Entradas obligatorias y qué sacar de cada una

Lee cada una entera antes de escribir. Para cada entrada, anota en tu borrador qué requisitos produce (pasada C).

| Entrada | Qué sacar |
|---|---|
| `PROMPT-MAESTRO-REVISION-TOTAL.md` v1 (y su copia en Descargas) | Sus 7 secciones: qué se conserva, qué está desactualizado, qué falta |
| `PROMPT-AGENTE-LOCAL-SESION-LARGA.md` v1 | Las 5 fases y sus mínimos; qué ya está hecho (exchangeInfo, financiación, `BinanceFut`) |
| `PROMPT-AGENTE-TRADING-NUBE.md` v3 local (y la versión de la nube del 25/10) | Secciones EN QUÉ VAS, SOLO OPERAS TÚ, LO QUE QUIERE NICOLÁS, PERMISOS, AUTOCORRECCIÓN, ENTREGA |
| `GUIA-DECISION-CLAUDE.md` v3 | Libros, confirmaciones, riesgo y cuándo no operar |
| `investigacion/INFORME-INVESTIGACION-QUANT.md`, `investigacion/PREREGISTRO.md` | Lo que está medido y la regla de adopción |
| `investigacion/plan-diario/*.txt` (a1 a a8) y `PREREGISTRO-PLAN-DIARIO.md` | Porcentaje diario óptimo, combinaciones, ingeniería inversa, base de velas, reversión corta, regla de las 3 resistencias, fuera de muestra |
| REGISTRO v6 de la rutina de la nube (último correo «Agente de trading») | Libro CLAUDE, ciegas (+10,69 % frente a −0,56 %), 37 estrategias, reglas R1-R15 |
| Las cinco fotos del 27/10 (transcripción literal en la sección C) | Encargos F1-F14 |
| Los mensajes de Nicolás del 27 y 28/10 (sección C) | M1-M20 |
| El plan aprobado (`03-Proyectos/Plan de trading diario` en la bóveda) | Pasos E1-E14, sus estados y las decisiones tomadas |
| Su memoria (`MEMORY.md` y las notas que nombra) | Normas: privacidad, sin casas mexicanas, dinero real bloqueado, hora de Colombia, Telegram en texto directo, sin subagentes, no justificar, nada de lenguaje de IA |

## C. Pasada 1: inventario de requisitos (matriz R)

Construye una tabla con una fila por requisito y estas columnas: **id · frase literal · fuente · prueba de aceptación · sección de la v2 que lo cumple · estado**. Está sembrada así; añade los que encuentres.

**Mensajes de Nicolás (M):**
- M1 «contextualízate con Obsidian, el agente de la nube y sus estrategias».
- M2 «lee las fotos de Descargas».
- M3 «analiza el prompt de mejora».
- M4 «un prompt para mejorar el prompt, largo, costoso, complicado y riguroso; luego síguelo».
- M5 «el plan de ganancias diario, 11 %, no anual».
- M6 su experiencia: 20.000 → 42.000-48.000 y 5.000 → 120.000 en un día.
- M7 «que lea todas las velas, todo lo que significa cada una, rápido, estructurado, con el contexto, para ver cuánto ganamos en papel».
- M8 «lo importante es que haga el dinero».
- M9 «8 veces al día, ¿más optimizado?».
- M10 «la rutina más optimizada para ganar».
- M11 «8 % diario o el porcentaje más óptimo».
- M12 «olvida los brokers y lo de Barron».
- M13 «solo lo directo del dinero».
- M14 «sigue el plan largo aprobado, los puntos, rigurosamente, más las estrategias agregadas».
- M15 «quita y pon estrategias, de a una y de a varias: las mejores combinaciones, retorno y rendimiento».
- M16 «ingeniería inversa a la lógica del trade».
- M17 «riesgo: el 3 % es muy poco; libro abierto; arriesga más».
- M18 «mi regla: 3 resistencias → apuesto a la caída; ganaba a diario, no eran rachas; quiero que lo hagas tú».
- M19 «chulitos en el plan; todo por Telegram, en texto directo, no .md».
- M20 «el plan completo en Obsidian».

**Fotos (F), transcripción literal resumida:**
- F1 (Informes_gmail, 2:17 p. m.) «Dejar reposar los dos agentes esta semana, tanto Marketing como el agente comercial».
- F2 (Informes, 2:18) «Recuérdame hoy a las 6 PM mi clase de Ingeniería del software 3».
- F3 (Informes, 2:21) «Para las 9 PM revisa los movimientos de Barron Trump… y los brokers PU Prime y MultiBank». Anulada por M12.
- F4 (Centro nocturno, 2:12) «Probar con y sin las imágenes y solo con la imagen correspondiente; cerciórate cuál es la que más te genera».
- F5 (2:13) «Observar qué datos son los más útiles de estrategias y mandarlos a mi Telegram».
- F6 (2:13) «Seguir el nuevo prompt señalado en local».
- F7 (2:13) «Automatizar la conexión de Claude con GitHub para editar mis proyectos en la nube».
- F8 (2:13) «Aunque el plan está bien diseñado, me falta demasiado por escribir».
- F9 (2:16) «Puedes generar un agente de estructuración para mejorar el proyecto».
- F10 (2:16) «Avísame por Telegram; si es posible llámame al WhatsApp; mándame un audio con los indicativos y las mejores y peores estrategias».
- F11 (2:16) «Guarda una copia del proyecto y cambia las reglas para el mayor retorno posible, en diario».
- F12 (2:17) «Un PDF explicativo del plan aplicado a las estrategias, con las que dan saldos bajos o negativos y los cuadros que no son seguros».
- F13 (3:21) «Recordarme el programa del PDF de Ingeniería del software 3, la encuesta y 13 respuestas ficticias sin decir que lo son, y gráficas».
- F14 (3:27) «Un prompt sobre lo mismo, con bonito diseño».

**Prompt v1 (P):** sus secciones 3 (reglas), 4 (estado), 5 (revisión), 6 (prioridades) y 7 (entrega).

## D. Pasada 2: diagnóstico del v1, línea por línea

Para cada sección del v1, escribe: qué dice; si sigue siendo cierto (comprobado con un comando o un archivo); qué cambia en la v2. Tienen que aparecer, como mínimo, estos defectos ya encontrados:
- No hay plan diario, ni libros por tamaño, ni informe en pesos.
- «2 % da +13-15 %/año» vale solo para el contado. No están el crecimiento óptimo (5-10 %), el mínimo de futuros (fuerza 13-20 % de riesgo con 40.000 COP) ni la cartera de 7 activos.
- «Nada de cuotas ni de bajar del 2 %» quedó superado por los libros (M17).
- El estado está viejo:
  - el PR #1 ya se unió;
  - `706677d` llegó por paquete;
  - las rutinas están apagadas por el límite semanal;
  - la rama `local/maestro-v2-2026-10-27` tiene todo lo nuevo.
- El mapa no tiene `lector_velas.py`, `plan_diario.py`, `clases_vela.py`, `base_velas.json`, `prueba_multiactivo.py` ni `eventos.json`.
- Faltan las órdenes condicionadas de día completo: las señales se llenan a los 3 minutos (mediana).
- Falta el régimen bajista: el 28/10, los 7 activos están bajo su SMA 50.
- No hay entrega por Telegram en texto ni PDF.

Busca además al menos 3 defectos nuevos o escribe por qué no los hay.

## E. Pasada 3: conflictos y cómo se resuelven

Orden de prioridad, de mayor a menor:
1. Dinero real y secretos: nunca, sin su sí.
2. Cifras honestas: toda cifra con su comando; lo no comprobado se dice.
3. Órdenes explícitas de Nicolás, la más reciente sobre la anterior.
4. Cupo y eficiencia.

| Conflicto | Resolución |
|---|---|
| M5 y M11 (11 % u 8 % diario) frente a lo medido | Lo medido manda sobre la promesa: el máximo sostenible es ~0,2-0,3 % al día (a1, a2, a3). La meta vive en el libro L11 y se mide cada día en pesos. No se le dice que es imposible sin la cifra al lado |
| M17 (más riesgo) frente al óptimo medido | Libro abierto: LC al 5 % (óptimo robusto) y LC8 al 8 % (máximo histórico), L11 al lado. Por encima del óptimo, la ganancia baja: se dice con la tabla |
| M18 (su regla gana a diario) frente a `a7` (48-52 % en BTC) | No se discute su experiencia. Se mide su método real (historial o detalles) antes de concluir |
| F11 (cambiar reglas para el mayor retorno) frente a la regla de adopción | Los tamaños cambian ya, en papel. Las reglas de estrategia solo por el preregistro y el fuera de muestra |
| F10 (WhatsApp) frente a la fiabilidad | El audio va por Telegram (WhatsApp falló el 17 y el 24/10). La llamada, solo si él la pide en el momento |
| F13 (13 respuestas ficticias sin decirlo) frente a la honestidad | No se inventan datos presentados como reales: mensaje para las 15 respuestas reales y gráficos que se llenan solos |
| M12 y M13 frente a F3, F7, F13 y F14 | F3 fuera. F7, F13 y F14 van al final, después de todo lo que genera dinero |

## F. Pasada 4: estructura obligatoria de la v2

0. Uso (cómo se lanza, en el PC y en la nube).
1. El proyecto en una página: objetivo en pesos por día; opera Claude.
2. Mapa del repositorio con todos los archivos nuevos.
3. Reglas que no se rompen.
4. Estado al día, con lo comprobado y su comando.
5. **Plan diario:** libros, régimen, órdenes condicionadas, decisión a los 30 días.
6. **Lector y ciclo de decisión:** cómo leer, qué escribir y cómo puntuar.
7. Revisión y reproducción.
8. Prioridades con criterio.
9. Encargos de las fotos con su destino y estado.
10. Entrega: informe, Telegram en texto, PDF.
11. Errores que no se repiten.

## G. Pasada 5: redacción

- Cada instrucción lleva comando exacto, archivo y criterio de terminado. Prohibido «revisar» sin decir qué y con qué.
- Registro formal y directo: verbos en vez de sustantivos abstractos, sin rayas largas, sin cierres de relleno y sin listas donde va una frase.
- Hora siempre con comando, en UTC y en Colombia.
- Cifras con su fuente: archivo y comando.

## H. Pasada 6: auditoría adversarial (se repite hasta salir limpia)

1. Tabla requisito → sección: ningún M, F o P sin destino, o con «fuera» y su razón.
2. **Ensayo en seco:** cada comando de la v2 se corre o se comprueba (que el archivo y la opción existan) en Windows y en la nube. Lo que no exista se arregla o se quita.
3. **Normas una por una:** privacidad, dinero real, secretos, sin casas mexicanas, hora, Telegram en texto, sin subagentes, estilo.
4. **Lectura en frío:** como un auditor que quiere romperla. ¿Qué haría mal un agente nuevo con este texto? Cada respuesta es un arreglo.
5. Se anota el resultado en la sección «Auditoría» al final de la v2.

## I. Pasada 7: versiones y consolidación

- La v1 queda como `PROMPT-MAESTRO-REVISION-TOTAL.anterior-2026-10-27.md`.
- Lo mismo con la sesión larga, la nube y la guía (`.anterior-2026-10-28.md`).
- Una línea por versión con qué cambió.
- Commit en la rama y push de la rama, nunca a `master`.

## J. Ejecución

Al terminar H, sigue la v2 en el orden de su sección 8. Cada paso se marca en el plan de la bóveda (✅ · 🔄 · ⬜) y se informa por Telegram en texto directo.
