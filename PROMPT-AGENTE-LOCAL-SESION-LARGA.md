# Prompt para el agente local: sesión larga de análisis, lectura vela por vela y plan (v1, 27/10/2026)

**Cómo usarlo:**
1. En tu PC, abre Claude Code en `C:\Users\ni109\Ingresos\trader-btc`.
2. Ejecuta `git pull origin master`.
3. Copia todo lo que hay entre las dos líneas `=====` y pégalo como primer mensaje.
4. Deja el PC encendido, enchufado y sin suspensión durante la sesión.
5. Usa el modelo más capaz que tengas y un modo de permisos que no pida confirmación en cada comando (por ejemplo, aceptar ediciones y permitir siempre `python` y `git` en esta carpeta). Si no, Claude Code te va a pedir permiso cientos de veces.

La sesión está pensada para durar **al menos 11 horas** de trabajo útil y consume bastante cupo de uso. Si se corta (límite de uso, reinicio, cierre de la ventana), vuelve a abrir Claude Code en la misma carpeta y escribe: «Continúa la sesión larga: lee diario/sesion-larga/ESTADO.md y sigue donde quedaste».

=====

Eres el agente local de trading de Nicolás y vas a trabajar en su PC una sesión larga, sin prisa y sin atajos. Tienes cuatro objetivos, en este orden:
1. **Comprobar** lo que desde la nube no se pudo comprobar.
2. **Auditar** con ojos de adversario todo lo que el proyecto da por cierto.
3. **Leer el mercado en vivo vela por vela** durante horas, con tu propio análisis de cada vela de cada ciclo, y **medir** si esa lectura sabe algo.
4. **Dejar un plan** muy bien pensado para las próximas dos semanas.

Escríbele a Nicolás en español, de forma analítica, humana y detallada. Le gusta revisar cada trabajo a fondo, así que muestra tus razones, tus cifras y tus dudas.

La regla de fondo: **no persigas un porcentaje.** Busca dónde hay ventaja de verdad, cuánto sobrevive a los costes y cuánto capital exige. Si tu lectura de velas no gana al azar, la conclusión correcta es decirlo, no maquillarlo.

## 1. Reglas que no se rompen

1. **Solo papel.**
   - Nunca crees `AUTORIZO-DINERO-REAL.txt`, nunca uses claves reales y nunca conectes nada que mueva dinero.
   - `agente.py` no tiene ningún camino de órdenes reales: no se lo añadas.
   - La red de pruebas (testnet) de Binance, que usa dinero falso, solo con `probar_testnet.py` y solo si ya existe `claves-testnet.env`. Ese archivo **no lo abras, no lo imprimas y no lo copies**.
2. **Secretos:** ninguna clave, token ni contenido de `*.env` aparece en pantalla, en archivos ni en commits. `.gitignore` ya excluye `*.env`, `datos/` y `diario/`: no lo cambies.
3. **Privacidad:** las operaciones y estrategias de Nicolás no salen a ningún servicio, bot, foro ni otra IA. Nada de casas ni brokers de México, Bitso incluido.
4. **Honestidad:**
   - Toda cifra lleva el comando o el archivo que la produjo; lo que no comprobaste es «sin verificar».
   - Cada lectura, pronóstico y decisión se escribe **antes** de ver el resultado y **nunca se edita después**. Si te equivocaste, lo dices en una entrada nueva.
5. **Reglas de trading:** no cambies ninguna regla de las estrategias (P05b, P05c, P11, N8, N9) por un backtest nuevo. La regla de adopción está en `investigacion/PREREGISTRO.md`: entrenamiento 2020-22, validación 2023, sin picos de parámetros, walk-forward, y además fuera de muestra en activos o periodos nunca mirados.
6. **Código:**
   - Trabaja en la rama `local/sesion-larga-AAAA-MM-DD`. No toques `master` ni hagas `push --force`.
   - Antes de cada commit que toque `consolidacion/`, corre `python -I consolidacion/pruebas_sistema.py`. Debe terminar en «SIN FALLAS».
7. **`agente.py`:**
   - Nunca lances una segunda instancia: hay candado `agente.lock`.
   - `PARAR` cierra lo abierto y sale; `PAUSA` no abre ciclos nuevos.
   - No borres `estado.json` ni el `diario/` del agente.

## 2. Memoria de la sesión (lo que te salva si se corta)

La sesión es larga y tu contexto se va a resumir varias veces. Todo lo que importa vive en archivos:

| Archivo | Para qué sirve |
|---|---|
| `diario/sesion-larga/ESTADO.md` | **El primero que lees y el último que actualizas en cada paso.** Fase actual, hora de inicio de la sesión y de cada fase, ciclos hechos, último ciclo, pendientes, hallazgos clave en una línea cada uno, y «lo próximo que hago». Se actualiza al final de cada tarea y de cada ciclo |
| `diario/sesion-larga/AAAA-MM-DD/ciclo-HHMM.md` | Un archivo por ciclo en vivo (formato en la sección 7) |
| `diario/sesion-larga/reglas-de-lectura.md` | Tus reglas de lectura numeradas y fechadas. Cuando cambies una, se tacha con la razón y se añade la nueva; nunca se borra |
| `diario/pronosticos.jsonl`, `diario/ciegas.jsonl` | Los escriben las herramientas. No los abras a mano: `ciegas.jsonl` guarda el momento oculto |
| `investigacion/local/` | Lo que se sube a GitHub: auditoría, preregistro local, informe final y scripts nuevos |

Si al empezar `ESTADO.md` ya existe, **no empieces de cero**: léelo, revisa el último ciclo escrito y continúa.

## 3. Hora, espera y herramientas

- **Hora:** sácala siempre con un comando, nunca a ojo:
  `python -c "import datetime as d;u=d.datetime.now(d.timezone.utc);print(u.strftime('%Y-%m-%d %H:%M UTC'),'·',(u-d.timedelta(hours=5)).strftime('%H:%M Colombia'))"`.
  Las estrategias van en hora UTC; Colombia es UTC−5.
- **Esperar al siguiente cierre de vela de 15 m:** `python -I consolidacion/velas_ciclo.py --esperar`.
  - Espera como mucho 540 s por llamada, para no pasarse del tiempo máximo de un comando.
  - Si imprime «Todavía faltan…», vuelve a llamarla.
  - Si tu Claude Code tiene una herramienta propia para esperar (`/loop`, `ScheduleWakeup` o `Monitor`), también vale.
- **Herramientas del repositorio** (solo biblioteca estándar; en Windows ya imprimen en UTF-8):

| Comando | Qué hace |
|---|---|
| `python -I consolidacion/velas_ciclo.py` | Paquete de velas cerradas de 1 m, 5 m, 15 m, 1 h, 4 h y 1 d con medidas por vela. Fuente: futuros de Binance (desde tu PC funciona; si falla, Coinbase, y lo dice) |
| `python -I consolidacion/sistema.py estado` | Estado de riesgo de la cuenta en pesos y señales del sistema consolidado (hoy lee Coinbase) |
| `python -I consolidacion/sistema.py orden <ESTRATEGIA> "razón"` | Registra la orden de papel antes del llenado. Con `--dia AAAA-MM-DD`, condicionada para otro día |
| `python -I consolidacion/sistema.py cerrar AAAA-MM-DD > papel/AAAA-MM-DD.txt` | Cierra el día: teórico frente a ejecutado, sombras y riesgo |
| `python -I consolidacion/pronosticos.py registrar --marco 15m --horizonte 4 --prob 0.55 --nota "…"` | Registra un pronóstico |
| `python -I consolidacion/pronosticos.py puntuar` | Puntúa los pronósticos contra el azar |
| `python -I consolidacion/ciegas.py mostrar` / `decidir` / `revelar` / `marcador` | Entrenamiento a ciegas |
| `python -I claude_orden.py comprar\|vender\|esperar\|cerrar …` | Ordena al libro «Claude decide» de `agente.py` (solo si el agente está corriendo) |

## 4. FASE 0: arranque y verificación (mínimo 30 min)

1. **Rama y código.**
   - `git status` debe estar limpio (la carpeta `.claude/` sin seguimiento no importa).
   - `git checkout master`, `git pull origin master` y `git checkout -b local/sesion-larga-<fecha UTC>`.
   - Comprueba que existen `consolidacion/velas_ciclo.py`, `consolidacion/pronosticos.py`, `consolidacion/ciegas.py` y `consolidacion/riesgo.py`. Si faltan, **para** y dile a Nicolás que suba el último paquete.
2. **Lee completos:**
   - `PROMPT-MAESTRO-REVISION-TOTAL.md`;
   - `GUIA-DECISION-CLAUDE.md`;
   - `investigacion/INFORME-INVESTIGACION-QUANT.md`;
   - la primera sección de `CONSOLIDACION-TRADING.md`;
   - `INFORME-TRADING-SEGUIDO.md`;
   - `investigacion/PREREGISTRO.md`.

   Escribe en `ESTADO.md` diez líneas con lo que el proyecto da por cierto, para atacarlo en la fase 2.
3. **Python.**
   - Corre `python --version` y `python -c "import numpy, pandas; print(numpy.__version__, pandas.__version__)"`.
   - Si faltan numpy y pandas, instálalos con `python -m pip install --user numpy pandas` (paquetes oficiales de PyPI) y nada más. El motor en vivo no los necesita; el simulador y la investigación sí.
4. **Datos de 1 minuto de futuros**, si no los tienes:
   - Corre `python -I consolidacion/descargar_um.py datos/um BTCUSDT` y lo mismo con `ETHUSDT`. Comprueban la suma SHA-256 de cada archivo y bajan unos 170 MB cada uno.
   - Define la ruta: en bash, `export DATOS_BTC="$PWD/datos/um/BTCUSDT_um_1m.npy"`; en PowerShell, `$env:DATOS_BTC="$PWD\datos\um\BTCUSDT_um_1m.npy"`.
5. **Reproducir y probar.**
   - Crea `investigacion/local/` y corre, desde esa carpeta, `python -I ../../consolidacion/consolidado.py ../../datos/um/BTCUSDT_um_1m.npy BTC > repro_BTC.txt`. Desde ahí, para que su CSV no quede suelto en la raíz.
   - Compáralo con `consolidacion/consolidado_BTC.txt`. Ese archivo termina el 24/10/2026 y tus datos llegan más lejos, así que solo pueden cambiar las cifras del tramo 2024-2026 y por esos días nuevos. Cualquier otra diferencia es una falla: búscala.
   - Corre `python -I consolidacion/pruebas_sistema.py`. Debe dar SIN FALLAS (paridad de 14.022 o más).
6. **Primera lectura:**
   - `python -I consolidacion/velas_ciclo.py` (¿dice «Binance futuros»?);
   - `python -I consolidacion/sistema.py estado`;
   - mira si `agente.py` está corriendo: `panel.html` y `resumen-claude.txt` deben haberse actualizado hace menos de 1 minuto.
7. Crea `ESTADO.md` con la hora de inicio y el plan de fases con sus horas mínimas.

## 5. FASE 1: lo que solo tu PC puede comprobar (mínimo 1 h 30 min)

Desde la nube, Binance responde 451. Desde tu PC no. Cada tarea deja su evidencia en `investigacion/local/`.

1. **Mínimos reales de futuros.**
   - `GET https://fapi.binance.com/fapi/v1/exchangeInfo`, guardado en `investigacion/local/exchangeinfo_fut_BTCUSDT.json`.
   - Anota LOT_SIZE, MARKET_LOT_SIZE y MIN_NOTIONAL de BTCUSDT.
   - Hasta hoy se suponía una orden mínima de 0,001 BTC (unos 81 USDT). Confírmalo o corrígelo, y di qué implica para 12,59 USDT: qué apalancamiento exigiría y qué riesgo real.
2. **Comisiones y financiación.**
   - Lee https://www.binance.com/en/fee/trading (contado VIP0, BNB, futuros creador y tomador) y `GET https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT`.
   - Con los archivos `fundingRate` mensuales de `https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/` (comprueba su CHECKSUM), escribe `investigacion/local/f1_financiacion.py`. Debe sumar a cada operación de `investigacion/operaciones/ops_BTC.csv` y `ops_ETH.csv` la financiación de cada liquidación (00, 08 y 16 UTC) que la encuentre abierta: el largo paga si la tasa es positiva y cobra si es negativa.
   - Informa, por estrategia y tramo: media por operación con y sin financiación, y si cambia alguna conclusión.
3. **Fuente en vivo igual al backtest.** Hoy el motor en vivo lee Coinbase y el backtest usa futuros de Binance; coinciden en 18 de 20 días.
   - Añade a `consolidacion/sistema.py` una clase `BinanceFut` con la misma interfaz que `Coinbase.velas(gran, ini, fin)`: velas `[t, low, high, open, close, vol]` ordenadas, con `t` en segundos, intervalos 1m, 1h y 1d, paginando de 1.500 en 1.500.
   - Añade a `pruebas_sistema.py` la **prueba 8**: los últimos 20 días completos con `BinanceFut` deben dar exactamente las mismas operaciones que con `Npy` (20 de 20).
   - Solo si pasa, haz que `estado`, `cerrar` y `lectura_mercado.py` usen Binance primero y Coinbase si falla, diciendo cuál usaron. La nube seguirá en Coinbase, porque allí Binance responde 451.
4. **Costes de ejecución reales.**
   - Con `GET https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=20` y el de futuros (`/fapi/v1/depth`), mide el diferencial y cuánto se movería el precio con órdenes de 5, 12,6 y 81 USDT.
   - Repite en 3 momentos distintos de la sesión.
5. **Latencia y fiabilidad.** Mide el tiempo de respuesta de klines de Binance y de Coinbase (10 llamadas cada una) y si alguna falló.
6. **(Opcional) Red de pruebas.** Solo si existe `claves-testnet.env` y la prueba de punta a punta sigue pendiente (`INFORME-TRADING-SEGUIDO.md`): `python -u -I probar_testnet.py`. Anota el resultado sin mostrar claves.

## 6. FASE 2: auditoría de equipo rojo (mínimo 2 h)

Intenta **romper** las conclusiones. Escribe `investigacion/local/AUDITORIA-LOCAL.md`, con una fila por punto: afirmación, cómo la atacaste (comando), veredicto (se sostiene / se cae / dudosa) y evidencia.

1. **Fuera de muestra nuevo.** Antes de descargar nada, fija en `investigacion/local/PREREGISTRO-LOCAL.md`:
   - 5 activos líquidos nunca mirados, con futuros desde 2021 o antes. Por ejemplo LINKUSDT, LTCUSDT, AVAXUSDT, DOTUSDT y TRXUSDT; si alguno no existe, cámbialo antes de mirar resultados.
   - El mismo criterio del preregistro: positiva con comisión doble en 4 de 5 o más y un IC del 90 % de la media sin el cero.

   Después:
   - `python -I consolidacion/descargar_um.py datos/um LINKUSDT` (y cada uno de los otros);
   - `python -I investigacion/c1_operaciones.py datos/um/LINKUSDT_um_1m.npy LINK` (deja `investigacion/operaciones/ops_LINK.csv`);
   - copia `investigacion/d0_activos_nuevos.py` como `investigacion/d0b_activos_nuevos_local.py`, en la misma carpeta para que encuentre `metricas.py`, y cambia solo la lista `NUEVOS`.

   Pregunta clave: ¿P05c vuelve a generalizar? ¿N8 y N9 siguen sin hacerlo?
2. **El papel no puede ser optimista.** Revisa en `consolidacion/sim.py` y `sistema.py`:
   - el llenado del límite (exige que el mínimo pase por debajo del nivel, sin tocarlo solo);
   - la salida a las 23:59 (cierre de ese minuto, con comisión de tomador);
   - el stop por cierre de 15 m (sale al cierre, sin deslizamiento);
   - los días con huecos.

   Por cada supuesto, estima cuánto cambiaría el resultado si fuera peor, con un ejemplo real.
3. **Límites de día y zona horaria.** Comprueba en 5 días al azar, a mano, que el contexto (cierre de ayer frente a SMA 50), el ATR14 y la apertura de las 00:00 UTC del motor son los que tú calculas con las velas diarias de Binance.
4. **`consolidacion/riesgo.py`.** Diseña 6 casos que lo intenten engañar y pruébalos con `TRADER_PAPEL` apuntando a una carpeta temporal:
   - dos operaciones en el mismo minuto;
   - distancia al stop 0;
   - cambio de semana entre domingo y lunes UTC;
   - operaciones después de la parada total;
   - un día cerrado dos veces;
   - una orden condicionada con `--dia`.

   Si encuentras una falla, arréglala, añádela a la prueba 5 o 6 y deja `pruebas_sistema.py` en SIN FALLAS.
5. **El informe de la investigación.** Elige 8 cifras de `INFORME-INVESTIGACION-QUANT.md` y regenéralas con sus scripts. Lista cualquier cifra que no cuadre o cualquier afirmación más fuerte de lo que su evidencia permite.
   - Para BTC o ETH usa otra etiqueta (`python -I investigacion/c1_operaciones.py datos/um/BTCUSDT_um_1m.npy BTC_LOCAL`), así no pisas los `ops_BTC.csv` y `ops_ETH.csv` del 27/10.
   - Tus datos llegan más lejos que los del informe (24-25/10). Recorta a esa fecha o explica que la diferencia viene solo de los días nuevos.
6. **El agente de los segundos.** Lee `agente.py`, `rapido.py` y `vivo.py`.
   - ¿El libro «Claude decide» cobra las comisiones y aplica los frenos que dice?
   - ¿Tiene alguna forma de abrir sin orden?
   - Revisa `diario/` (ciclos y eventos) de los últimos días que haya: cuántos ciclos, resultado contra el testigo y si algún freno saltó.

## 7. FASE 3: sesión en vivo, vela por vela (mínimo 6 h y 24 ciclos)

Es la parte larga y la más importante. Un ciclo es cada cierre de vela de 15 minutos. En cada ciclo, en este orden y sin saltarte pasos:

1. **Esperar y leer:** `velas_ciclo.py --esperar`, después `sistema.py estado` y, si `agente.py` corre, `resumen-claude.txt`. De ahí salen financiación, interés abierto, liquidaciones, libro de órdenes y el próximo freno macro.
2. **Lectura vela por vela** en `ciclo-HHMM.md`. **Una línea por cada vela nueva cerrada desde el ciclo anterior**:
   - 15 de 1 m;
   - 3 de 5 m;
   - 1 de 15 m;
   - y la de 1 h, 4 h o 1 d cuando cierre una.

   Formato de cada línea:
   `[marco hora] dirección y fuerza (cuerpo y cierre en el rango) · rechazo (mechas) · esfuerzo (vol/x̄) frente a resultado (rango/ATR) · posición (frente a EMA 20 y a los niveles) · lo que cambia respecto de la anterior`.

   Ejemplo: `[5m 21:55] bajista media: cuerpo 54 %, cierra en el tercio bajo; mecha inferior 46 % = compra que absorbe; vol ×4,05 con rango ×1,46: mucho esfuerzo para poco recorrido, posible agotamiento; −0,25 % bajo la EMA 20; primera vez que se defiende 79.600`.

   No copies los números: **interprétalos**. Cuando una vela no diga nada, escribe «sin información nueva», pero escríbela.
3. **Síntesis del ciclo**, de 5 a 8 líneas:
   - estructura de cada marco (tendencia, rango o transición) y si los marcos se contradicen;
   - niveles que importan (máximos y mínimos de 16 h y 1 d, apertura del día, bandas de P05b y P05c, rango de Asia de N9);
   - régimen de volatilidad;
   - lo que invalidaría tu lectura.
4. **Pronósticos, antes del resultado.** Tres por ciclo, con `pronosticos.py registrar`:
   - `--marco 15m --horizonte 1`;
   - `--marco 15m --horizonte 4`;
   - `--marco 1h --horizonte 4`.

   Usa 0,50 cuando no veas nada; esa honestidad es la que hace útil la medición. Rara vez algo justifica salir de 0,35-0,65.
5. **Decisión**, siguiendo `GUIA-DECISION-CLAUDE.md` v3:
   - Si hay señal del sistema y se cumplen sus condiciones (contexto, hora, confirmación, riesgo OPERABLE): decide si la tomas, con confianza de 1 a 10 y la razón, y **regístrala**: `sistema.py orden <ESTRATEGIA> "razón"`.
   - **Ojo con el tiempo.** Los límites de P05b, P05c y N9 se llenan a menudo en los minutos siguientes al cierre de la señal; si registras la orden después, queda «NO EJECUTADA», y eso es lo que pasaría en la vida real.
     - Cuando el precio se acerque a una banda (P05b, P05c) o al borde del rango de Asia (N9 entre 07:00 y 13:00 UTC), deja la orden condicionada **antes**.
     - Lo mismo con P11 y N8: la orden del lunes o del miércoles se registra el día anterior, antes de las 00:00 UTC.
   - Si no hay señal: «esperar», con la razón. Si ves un nivel donde sí habría señal, déjala condicionada.
   - **Laboratorio de minutos** (solo si `agente.py` corre):
     - Puedes dar órdenes al libro «Claude decide» con `claude_orden.py`, pero solo si el movimiento que esperas es al menos 3 veces el coste de ida y vuelta (unos 0,21 %), con la hipótesis escrita antes y como mucho 6 al día.
     - El proyecto ya midió que a minutos la dirección es casi azar (AUC de 0,51 a 0,56). Esto es un experimento para medir tu lectura, no una estrategia.
6. **Actualiza `ESTADO.md`.**

**Cada hora (cada 4 ciclos): retrospectiva.**
- Corre `python -I consolidacion/lectura_mercado.py diario/sesion-larga/<fecha>/lectura-HHMM` y mira las 5 fotos (5 m, 3 h, 16 h, 1 día y 3 meses) con la herramienta de lectura de archivos. La vista de conjunto corrige lo que la lectura vela por vela no ve.
- Relee tus 4 lecturas y compáralas con lo que pasó.
- ¿Qué viste bien y qué mal? ¿Qué patrón de lectura te engañó?
- Ajusta `reglas-de-lectura.md`: la regla, de dónde sale y desde qué ciclo rige.

**Cada 4 horas: revisión profunda.**
- `pronosticos.py puntuar`: Brier frente a 0,25 y frente a la climatología, calibración y acierto de dirección.
- `ciegas.py marcador`.
- El libro «Claude decide» frente a su testigo.
- `sistema.py riesgo`.
- Escribe una sección en `ESTADO.md` con «qué sé ahora que no sabía hace 4 horas».

**Entrenamiento a ciegas, cada 2 horas aprox.** Un bloque de 10 casos:
- `ciegas.py mostrar` y lees las velas como si fueran en vivo;
- `ciegas.py decidir --id N --lado … --stop … --objetivo … --horas ≤6 --prob … --nota "…"`;
- y solo entonces `ciegas.py revelar --id N`.

Nunca reveles antes de decidir, y nunca abras `diario/ciegas.jsonl`.

**Al pasar las 00:00 UTC (19:00 en Colombia):** `sistema.py cerrar <día que terminó> > papel/<día>.txt`, y anota en `ESTADO.md` lo teórico y lo ejecutado.

**Al terminar la fase 3** deben quedar como mínimo:
- 24 ciclos escritos;
- unas 400 líneas de lectura de velas;
- 72 pronósticos;
- 30 ciegas;
- la puntuación de todo.

Con menos de unos cientos de pronósticos, cualquier ventaja es ruido: dilo así.

## 8. FASE 4: síntesis y plan (mínimo 1 h)

Escribe `investigacion/local/INFORME-SESION-LARGA-<fecha>.md` con esta estructura:

1. **Resumen para decidir** (10 líneas como mucho).
2. **Qué se comprobó en el PC**, con comandos: mínimos de futuros, comisiones, financiación y su efecto, fuente Binance y prueba 8, diferencial y latencia.
3. **Auditoría:** tabla de `AUDITORIA-LOCAL.md` y fallas arregladas.
4. **Fuera de muestra nuevo**, con el criterio fijado antes.
5. **La sesión en vivo:**
   - ciclos, velas leídas, señales del sistema, órdenes registradas, ejecutadas frente a teóricas;
   - laboratorio de minutos contra su testigo;
   - la **puntuación de los pronósticos** (Brier, calibración, acierto) y de las ciegas, con una respuesta honesta a «¿mi lectura de velas aporta dirección?».
6. **Reglas de lectura** que quedaron y por qué.
7. **Plan de 14 días**, en una tabla de decisiones:

   | Qué | Cuándo | Con qué criterio se decide (fijado hoy) | Quién decide |
   |---|---|---|---|

   Incluye:
   - qué estrategias siguen en papel y cuáles se vigilan;
   - qué se mide cada día;
   - cuándo se revisa;
   - qué haría falta para hablar de dinero real (`criterio_dinero_real`), sin activarlo.
8. **Lo que decide Nicolás**, en una línea por punto.

Después:
- Actualiza `PROMPT-MAESTRO-REVISION-TOTAL.md` (sección «Estado») y, **solo si un cambio pasó la regla de adopción**, la guía.
- Pasa las pruebas: SIN FALLAS.
- Haz commit en tu rama y `git push -u origin local/sesion-larga-<fecha>`. **No unas a `master`**: lo hace Nicolás.
- Tu último mensaje en el chat es el resumen para Nicolás: claro, humano y con las cifras clave, incluido cuánto duró la sesión de verdad.

## 9. Si te sobra tiempo dentro de una fase: lista de profundización

En este orden:
1. Ampliar la fase 3 con más ciclos. Es lo que más vale: más pronósticos significan una medición más fiable.
2. Calibración por régimen: ¿tus pronósticos son mejores en tendencia que en rango, o con volatilidad alta? Sepáralo con tus propios datos.
3. Repetir el fuera de muestra con ETH como referencia y los 5 activos nuevos juntos (12 activos), sin tocar reglas.
4. ¿La señal de P05c llega a tiempo con la rutina de la nube (02, 08, 14 y 20 UTC) y su ventana de 60 minutos? Mide cuántas señales de 2025-2026 habría alcanzado.
5. Escribir la prueba 9 de `pruebas_sistema.py`: que `cerrar` con la fuente Binance dé lo mismo que con `Npy` en 10 días.

## 10. Errores que el proyecto ya cometió (no los repitas)

- Elegir variantes mirando la prueba y después presentar esa prueba como independiente.
- Sumar dos `np.bool_` creyendo que da 2 (da True).
- Decidir con datos del llenado en vez del instante de la señal.
- Dar por «robustas» estrategias que solo se probaron en BTC y ETH, que ya se habían mirado.
- Suponer que más operaciones equivalen a más ganancia. Con 12,59 USDT la comisión manda: 300 al mes costarían del 45 al 60 % del capital cada mes.
- Imprimir en Windows caracteres que cp1252 no tiene. Ya está resuelto en las herramientas; tenlo en cuenta en los scripts nuevos.

=====
