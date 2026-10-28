# Prompt maestro del trading de Nicolás (v2, 28/10/2026)

Sale de `PROMPT-PARA-MEJORAR-EL-PROMPT.md`; la v1 queda en `PROMPT-MAESTRO-REVISION-TOTAL.anterior-2026-10-27.md`.

## 0. Uso

- **En el PC (lo normal):** Claude Code en `C:\Users\ni109\Ingresos\trader-btc`, en la rama `local/maestro-v2-2026-10-27`, hasta que Nicolás la una a `master` con su PR. Mientras tanto se trabaja en la carpeta `.claude\worktrees\maestro-v2`, que es esa rama. Los datos de 1 minuto viven en `C:\Users\ni109\Ingresos\trader-btc\datos\um`: en cada consola, `set TRADER_DATOS=C:\Users\ni109\Ingresos\trader-btc\datos` (o `export TRADER_DATOS=…` en bash).
- **En la nube:** necesita que la app de Claude tenga acceso a `trader-btc` (un clic de Nicolás en GitHub). Sin él, sigue el camino «sin repositorio» de `PROMPT-AGENTE-TRADING-NUBE.md`.
- Pega este prompt entero como primer mensaje y lee antes `GUIA-DECISION-CLAUDE.md`.

## 1. El proyecto en una página

- **Objetivo:** que el papel gane cada día la mayor cantidad de pesos que permitan las estrategias medidas, y que eso se vea en pesos todos los días. **Opera Claude, no un código:** los programas leen, calculan, cierran con velas reales y miden contra el azar.
- **Capital de referencia:** 40.000 COP (12,59 USDT a 3.177,85 COP/USDT). Dinero real bloqueado.
- **Lo medido, con su archivo:**
  - Un 11 % u 8 % diario no se alcanza con ningún riesgo. Por encima del óptimo, la ganancia baja y llega la ruina; lo sostenible es ~0,2-0,3 % al día (`investigacion/plan-diario/a1_riesgo_diario.txt`).
  - La mejor combinación, elegida en 2020-23 y comprobada en 2024-26 entre 1.023, es **P05c en 7 activos + P05b, P11 y N8 de BTC** (`a2_combinaciones.txt`).
  - Con libros de pesos, reapertura y paradas, de 2020 a 2026 desde 40.000 COP: **LC al 5 % → 9.403.999 COP (+0,225 %/día); LC8 al 8 % → 15.952.941 (+0,246 %/día, peor día −62,5 %)**. L11 al 19 % se arruina en 2020 (`consolidacion/plan_diario.py --historia investigacion/operaciones`).
  - Operar al revés no gana con ninguna estrategia. Reglas candidatas, preregistradas: N8 con volatilidad alta, P11 con 1 h y 1 d a favor, y P05c lejos de la SMA 50 (`a3_ingenieria_inversa.txt`, `PREREGISTRO-PLAN-DIARIO.md`).
  - Apuestas de segundos o minutos (reversión tras velas fuertes) y la regla de las 3 resistencias, tal como se tradujo: sin ventaja suficiente en BTC (`a6`, `a7`). Falta medir el método real de Nicolás.
  - Una vela sola casi no anticipa nada: tras una alcista fuerte, el precio sube después el 47-49 %; tras una bajista fuerte, el 54-57 % (`a5_base_velas.txt`).
- **Dinero diario según el capital:** con +0,2 %/día, 40.000 COP dan ~80 COP/día; 1.000.000 dan ~2.000/día. El que sube los pesos es el capital, no el apalancamiento.

## 2. Mapa del repositorio

| Archivo | Qué hace |
|---|---|
| `GUIA-DECISION-CLAUDE.md` (v4) | Guía diaria: libros, régimen, cuándo no operar |
| `PROMPT-AGENTE-LOCAL-SESION-LARGA.md` (v2) | La sesión larga en el PC: lectura vela por vela, pronósticos, ciegas y papel |
| `PROMPT-AGENTE-TRADING-NUBE.md` (v4) | La rutina de la nube |
| `consolidacion/sistema.py` | Motor en vivo: `estado`, `orden`, `cerrar`, `riesgo`, con `--activo X`, `--todos` y `--fuente auto\|binance\|coinbase`. `BinanceFut` y `Coinbase` por activo |
| `consolidacion/riesgo.py` | Topes de la cuenta en pesos, y órdenes y libro por activo (`papel/ordenes.jsonl`, `papel/libro.jsonl`) |
| `consolidacion/plan_diario.py` | Los libros en pesos: L2, L5, LK, L11, **LC (5 %)** y **LC8 (8 %)**; `--historia`, `--teorico` |
| `consolidacion/lector_velas.py` | Lector v2: contexto, todas las velas de 6 marcos con su significado y su base medida; `--solo-nuevas`, `--json`, `--activo`, `--fotos` |
| `consolidacion/clases_vela.py`, `base_velas.json` | Definición única de la clase de cada vela y lo que pasó después en el historial |
| `consolidacion/eventos.json` | Eventos macro del día (Reserva Federal, etc.) con su regla. Se actualiza a mano |
| `consolidacion/pruebas_sistema.py`, `prueba_multiactivo.py` | Pruebas 1-7 (BTC) y 10 (SOL, DOGE, …): deben decir SIN FALLAS |
| `consolidacion/velas_ciclo.py`, `pronosticos.py`, `ciegas.py` | Paquete de velas de un ciclo, pronósticos puntuados y entrenamiento a ciegas |
| `investigacion/plan-diario/` | a1 a a8 con sus salidas y `PREREGISTRO-PLAN-DIARIO.md` |
| `investigacion/operaciones/ops_*.csv` | Operaciones del simulador por activo (`c1_operaciones.py`) |
| `C:\Users\ni109\Ingresos\tg_pc.py` (fuera del repo) | Telegram desde el PC: lee la clave en el momento (WSL) y sale por Tor. `python -I tg_pc.py texto.txt` |

## 3. Reglas que no se rompen

1. **Dinero real:** solo con su sí explícito y el `criterio_dinero_real`, desde su PC, con `AUTORIZO-DINERO-REAL.txt` del día. Nunca claves ni órdenes reales desde la nube.
2. **Secretos:** ninguna clave en pantalla, archivos ni commits.
3. **Ni brokers ni casas de México.** Privacidad total: sus operaciones no salen a terceros ni a otras IA.
4. **Cifras honestas:** cada cifra lleva su comando o archivo; lo no comprobado se escribe «sin verificar». Se informa en tres niveles: comprobado en su equipo, laboratorio y sin probar.
5. **Reglas de estrategia:** solo cambian por el preregistro y el fuera de muestra. Los **tamaños** sí cambian en papel (libro abierto de Nicolás).
6. **Ninguna operación para cumplir una meta.** El porcentaje se mide en los libros.
7. **Órdenes condicionadas** registradas antes del llenado y válidas todo el día UTC (`sistema.py orden <E> --activo X --dia AAAA-MM-DD "razón"`). Las señales se llenan a los 3 minutos de mediana.
8. **Hora** con comando, en UTC y en Colombia (UTC−5).
9. **Telegram en texto directo**, nunca `.md`. Cada avance del plan se marca con ✅ · 🔄 · ⬜ en la nota de la bóveda `03-Proyectos/Plan de trading diario`.
10. **Sin subagentes ni flujos** en la sesión del PC. **Git:** trabajo en ramas, nunca push a `master`, nunca `--force`.

## 4. Estado al 28/10/2026, 14:30 Colombia

- **Código:** rama `local/maestro-v2-2026-10-27`, en GitHub (`721d253` o posterior). `pruebas_sistema.py`: SIN FALLAS (14.034 de 14.034). `prueba_multiactivo.py`: SOL 430/430 y DOGE 350/350.
- **Datos:** 1 m de futuros en `datos/um` de BTC, SOL, DOGE, ETH, BNB y XRP; ADA y LINK, AVAX, LTC, DOT y TRX en descarga.
- **Papel:**
  - el 26/10 sin señal;
  - el 27/10, N9 corto −0,93 %, teórico y no ejecutado;
  - 0 operaciones ejecutadas;
  - orden condicionada **P05b BTC para el 29/10**.
  - Libro oficial: el de la rama (`papel/`).
- **Mercado:** el 28/10, los 7 activos están bajo su SMA 50. La cartera de largos no tiene señales; P05b de BTC sí opera corto (+0,16 / +0,14 % neto por operación en 2020-23 / 2024-26).
- **Nube:** las rutinas están apagadas desde el 26/10 (límite semanal). La de trading tiene el prompt del 25/10. Se activa a las 07, 14 y 22 UTC cuando termine la sesión larga, con el prompt v4.
- **Pendiente de Nicolás:**
  - su método real (historial exportado o detalles de las 3 resistencias);
  - unir la rama a `master`;
  - el clic de GitHub;
  - más capital, si quiere más pesos por día.

## 5. Plan diario de ganancias

- **Libros**, sobre las mismas decisiones de Claude, con su saldo en pesos cada día (`plan_diario.py`):
  - **LC** al 5 % (principal) y **LC8** al 8 % (agresivo): P05c en todos los activos y P05b, P11 y N8 de BTC, hasta 3 posiciones;
  - **L11** al 19 % (la meta de 11 % de Nicolás);
  - L2, L5 y LK de comparación.
  - Reapertura tras la parada total: 30 días quieto y vuelta con la mitad del riesgo; la segunda parada es definitiva.
- **Régimen:** con contexto alcista se toman largos; con contexto bajista, los cortos de P05b en BTC. El corto R11 queda como hipótesis (H5, sin adoptar).
- **Decisión:** a los 30 días o con 30 operaciones ejecutadas, Nicolás elige libro con los pesos ganados y frente al azar.
- **Para subir el porcentaje diario:** más ventajas independientes (P05c en los 5 activos nuevos, si pasa H4) y filtros que suben la ganancia por operación (H1-H3, si pasan). Nunca más riesgo por encima del óptimo.

## 6. Lector y ciclo de decisión

1. Hora: `python -c "import datetime as d;u=d.datetime.now(d.timezone.utc);print(u.strftime('%Y-%m-%d %H:%M UTC'),'·',(u-d.timedelta(hours=5)).strftime('%H:%M Colombia'))"`.
2. Lectura: `python -I consolidacion/lector_velas.py --solo-nuevas` en cada ciclo. Lectura completa cada hora: `python -I consolidacion/lector_velas.py --fotos diario/sesion-larga/fotos`. Otras monedas: `--activo SOL`, etc.
3. Señales de los 7 activos: `python -I consolidacion/sistema.py estado --todos`.
4. Escribe por cada marco qué te dice el lector y **en qué no estás de acuerdo con él**. La base medida de cada vela no se ignora: una vela «alcista fuerte» no es señal de compra (sube después el 47-49 %).
5. Decide: tomar la señal, condicionarla o esperar, con confianza de 1 a 10 y la razón. Registra con `sistema.py orden … --activo X` antes del llenado.
6. Pronósticos (`pronosticos.py registrar`) y ciegas (`ciegas.py`) según la sesión larga.
7. **Al pasar las 00:00 UTC** (19:00 de Colombia): `python -I consolidacion/sistema.py cerrar AAAA-MM-DD --todos > papel/AAAA-MM-DD.txt`. Da los libros en pesos al final.

## 7. Revisión y reproducción

- `set DATOS_BTC=C:\Users\ni109\Ingresos\trader-btc\datos\um\BTCUSDT_um_1m.npy` y `python -I consolidacion/pruebas_sistema.py`: debe dar SIN FALLAS.
- `python -I consolidacion/prueba_multiactivo.py SOL DOGE ETH BNB XRP ADA`: debe dar SIN FALLAS.
- `python -I consolidacion/consolidado.py %DATOS_BTC% BTC` frente a `consolidacion/consolidado_BTC.txt`: solo pueden cambiar los días posteriores al 24/10.
- Cada análisis `a*` se reproduce con el comando de su cabecera.

## 8. Prioridades (en este orden)

1. **Fuera de muestra H1-H6** (`a8_fuera_de_muestra.py`), con las 5 monedas nuevas y `c1_operaciones.py`. Se adopta solo lo que cumpla los tres criterios del preregistro.
2. **Su método real:** con el historial o los detalles que dé Nicolás, se mide y, si gana, entra al papel como libro propio.
3. **Sesión larga** (`PROMPT-AGENTE-LOCAL-SESION-LARGA.md` v2) con los libros, el lector y el experimento de imágenes (F4).
4. **PDF del plan** (F12): libros, mejores y peores estrategias, cuadros que pierden y porcentaje óptimo.
5. **Rutina de la nube** con el prompt v4, a las 07, 14 y 22 UTC.
6. Datos más útiles a Telegram (F5), y al final audio (F10) y Software III (F13, F14), sin datos inventados.

## 9. Encargos de las fotos (27/10)

| Id | Encargo | Destino y estado |
|---|---|---|
| F1 | Reposo de marketing y ventas esta semana | ✅ Apagadas desde el 26/10; se pregunta el lunes 2/11 |
| F2 | Clase de las 6 PM | Pasó (aviso del 27/10) |
| F3 | Barron Trump y brokers | ❌ Fuera por su orden del 28/10 |
| F4 | Con y sin imágenes | ⬜ Experimento en la sesión larga (`ciegas.py --brazo`) |
| F5 | Datos más útiles a Telegram | 🔄 a3 hecho; se manda con el resultado de a8 |
| F6 | Seguir el prompt local | ⬜ Sesión larga v2, hoy |
| F7 | GitHub automático | ⬜ Un clic suyo («All repositories» en la app de Claude) |
| F8 | «Falta mucho por escribir» | ✅ Esta v2 y la sesión larga v2 |
| F9 | Agente de estructuración | ✅ Este meta-prompt y su ejecución |
| F10 | Telegram, llamada y audio | ✅ Telegram en texto · ⬜ audio con Piper al final |
| F11 | Copia del proyecto y reglas para el mayor retorno diario | ✅ Rama en GitHub y libros por tamaño · ⬜ etiqueta de respaldo |
| F12 | PDF del plan | ⬜ |
| F13, F14 | Software III | ⬜ Al final, sin respuestas inventadas |

## 10. Entrega

- Informe en el repositorio: qué se hizo, con qué comando, qué cambió y qué decide Nicolás.
- Telegram en **texto directo** con `python -I C:\Users\ni109\Ingresos\tg_pc.py archivo.txt`.
- La nota de la bóveda `03-Proyectos/Plan de trading diario` con los chulitos al día.
- Commit en la rama y push de la rama.

## 11. Errores que no se repiten

- Prometer o aceptar metas diarias sin la cifra medida al lado.
- Leer una orden suya como otra («baja el interés» no era «3 %»): si una palabra admite dos lecturas, se pregunta en una línea.
- Elegir con la prueba y presentar la prueba como independiente; definiciones que miran el futuro (medianas de todo el historial).
- pandas 3 guarda los tiempos en segundos: no dividir entre 10⁹. Salidas con «≥» en cp1252 se caen: `sys.stdout.reconfigure(encoding="utf-8")`. Git Bash cambia las rutas de `gh api` (`MSYS_NO_PATHCONV=1`) y las barras de los guiones largos en la línea de comandos: escribirlos en archivo.
- PowerShell con `-ExecutionPolicy Bypass` lo bloquea el clasificador: `-Command` en línea.

## Auditoría (pasada H del meta-prompt)

- **Requisitos:** M1-M20 y F1-F14 tienen destino en las secciones 1, 3, 5, 6, 8 o 9, o quedan fuera con su razón (F3, por M12).
- **Ensayo en seco** (28/10, PC):
  - `lector_velas.py`: probado, 1,9 s.
  - `sistema.py estado --todos`: probado, 13 s.
  - `plan_diario.py --historia`: probado.
  - `pruebas_sistema.py`: SIN FALLAS.
  - `prueba_multiactivo.py SOL DOGE`: SIN FALLAS.
  - `sistema.py orden --activo --dia`: probado.
  - `tg_pc.py`: probado, 9 envíos `ok`.
  - `cerrar --todos` y el informe de libros al cerrar: sin probar; se prueban al primer cierre del 29/10 UTC.
- **Normas:** privacidad, dinero real, secretos, casas, hora, Telegram en texto, sin subagentes: verificadas en las secciones 3 y 10.
