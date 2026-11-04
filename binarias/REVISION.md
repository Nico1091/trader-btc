# Revisiones

Cada revisión aplica `PROMPT-REVISION.md` y anota el hallazgo, la prueba que lo sostiene y el cambio hecho.

## Revisión 1 · 29/10/2026, 21:05 · sobre `PLAN.md` v1 y `PROMPT-OPERADOR.md` v1

1. **El mínimo de Binance rompe el 16 % tras la primera pérdida** (sección 4). Con 100.000 COP el 16 % son 16.000 COP, apenas sobre el mínimo de 5 USDT (unos 15.900 COP). Tras un fallo el saldo queda en 84.000 y el 16 % (13.440) ya no alcanza el mínimo, así que la app obliga a apostar más del 16 %. Cambio: la apuesta es el mayor entre el 16 % del saldo y 5 USDT, y la cuenta queda quebrada cuando el saldo no cubre 5 USDT. Se aplica igual en las pruebas y en vivo.
2. **Estrategias pensadas mirando 2024-26** (sección 1). Las consolidadas (REV5, REV15, las versiones al revés) y las del grupo B (motor de la T95H) se crearon con datos de 2024-26, así que su resultado a ciegas en ese periodo sale favorecido. Las de sus libros (A) y las E son reglas fijas tomadas de libros y artículos (comprobado en `senales_E` de t16: parámetros de Concretum, MACD 12/26/9, EMA 20/50, SMA 10/200). Cambio: el resultado a ciegas se informa por separado en 2021-23 (limpio para A, C y E) y en 2024-26, y los criterios se exigen en los dos tramos.
3. **Rasgos del modelo** (sección 1). Si el modelo usa las señales de C o de B, hereda la ventaja de haberlas pensado mirando 2024-26. Cambio: el modelo usa rasgos generales del mercado y solo las señales del grupo A; las medias y desviaciones para normalizar salen de su ventana de ajuste.
4. **Señales solapadas en la elección** (sección 5). Dos señales de la misma estrategia separadas por menos que el plazo no son independientes e inflan el límite de Wilson. Cambio: las estadísticas de cada candidato se calculan con una apuesta abierta a la vez, igual que en la operación.
5. **Número de procedimientos a ciegas** (sección 2). El plan pedía corregir por Bonferroni sin fijar el número. Cambio: son 8 (reglas en BTC y en ETH; modelo a 10, 30 y 60 min en BTC y en ETH). El límite inferior se calcula al 99,375 % de una cola. Las variantes de sensibilidad (otra ventana, otro número de elegidos) se informan, pero no se pueden escoger.
6. **Muestra necesaria** (sección 5). El criterio pedía «al menos 300 apuestas», pero con 57,8 % el límite corregido supera 54,1 % solo desde unas 1.100. Cambio: se deja dicho que el criterio del límite ya exige esa muestra.
7. **Empates** (sección 4). Binance no publica qué hace si el precio queda igual. Cambio: el empate cuenta como fallo en la cifra principal y se informa aparte.
8. **Precio de liquidación** (sección 3). Las pruebas usan futuros y no se sabe con qué precio liquida Binance estos contratos. Cambio: se mide en cuántas apuestas a 10, 30 y 60 min el sentido de contado y el de futuros no coinciden (velas de contado de 1 min desde 2023).
9. **Retraso real en papel** (sección 3). La cadena es ficha, decisión, aviso y toque. Cambio: cada apuesta en papel guarda el precio al cierre y el de 20 s después; la cuenta CLAUDE se liquida con el de 20 s, que es el que vería él.
10. **Paridad** (sección 7). Si el centinela vuelve a escribir las señales por su cuenta, nada asegura que coincidan con el banco. Cambio: el centinela importa las mismas funciones de señales y de elección que las pruebas, usa velas de 1 min de futuros (`/market/stream`) y corrige la hora con la del servidor de Binance.
11. **Operación** (sección 8). Faltaban el candado contra dos centinelas a la vez, los reintentos al guardar el estado y la continuidad del operador tras apagar el PC. Cambio: candado de archivo, guardado con reintentos y el estado en memoria hasta que se pueda escribir, y el operador arranca solo al iniciar sesión si no hay otro vivo, con herramientas limitadas a Bash y Read para gastar poco.
12. **Regla sin fundamento en el prompt** (sección 2). «Descartar tras 3 fallos seguidos» supone que una racha predice la siguiente apuesta, y las pruebas no lo respaldan. Cambio: se quita. Además, `esperar` entrega todas las fichas pendientes de una vez, el plazo para decidir es el cierre de la vela más 5 s, y la ficha muestra las señales contrarias que el prompt manda mirar.
13. **Días extraordinarios** (sección 5). Cambio: el informe da también el resultado sin los 5 mejores días.

## Revisión 2 · 29/10/2026, 21:40 · sobre lo construido y los resultados (t17 a t20, `binarias.py` v3, `operador.py`)

1. **Información del futuro: no se encontró.**
   - La elección de cada mes solo usa apuestas vencidas antes de empezar el mes (`b − 61 min` en t18 y en el centinela).
   - El modelo se normaliza con su ventana de ajuste.
   - Los patrones de vela (`patrones_std.py`) solo miran la vela actual y las anteriores.
   - La prueba más fuerte es la t20a: la regla escrita de nuevo, sin el banco, da el mismo 58,0 % en 47.935 apuestas.
   - El grupo B no se comprobó, pero no fue elegido en ninguno de los 70 meses.
2. **Elegir mirando el resultado.** Lo que opera en vivo es el procedimiento fijado como principal antes de ver nada (reglas a ciegas en BTC). Las variantes de sensibilidad no se escogieron. La t20 se escribió después de ver la t18, pero solo busca cómo podría fallar; no elige nada.
3. **Entrada y precio.**
   - Con velas de 1 s de contado (mayo a octubre de 2026), entrar entre 0 y 60 s tarde dio entre 54,6 % y 56,3 %, sin una pérdida que crezca con el retraso.
   - Con velas de 1 min, en todo el periodo, entrar 60 s tarde bajó de 58,0 % a 56,5 %.
   - Contado y futuros dan el mismo resultado en el 98,0 % de 9.460 apuestas.
   - Sin comprobar: qué precio usa Binance para liquidar los Contratos de Evento.
4. **Cuentas.** El mínimo de 5 USDT, el empate como fallo, una abierta a la vez y el tope de 16 al día se aplican igual en el banco (`seleccion.operar`, `seleccion.saldo`) y en vivo (`puede`, `apostar`). La tasa de 3.180 COP por USDT es fija desde el 20/10 y puede moverse.
5. **Muestra.** En BTC son 16.898 apuestas a ciegas, con límite corregido de 57,0 %; sin los 5 mejores días, 57,8 %.
6. **Regímenes: la ventaja se está gastando.** La regla cruda bajó de 60,3 % en 2020 a 55,5 % en 2026, y el procedimiento a ciegas en BTC dio 54,9 % en 2026. Apostar siempre arriba a las mismas horas da 50,1 % y el azar 50,0 %, así que la ventaja no viene de la subida de BTC.
7. **Paridad.**
   - `motor/senales.py` coincide con t7 y t16 en las 40 estrategias (t18_paridad).
   - La elección de octubre en vivo coincide con la del banco en BTC y en ETH.
   - La comparación diaria en vivo empieza el 30/10 a las 00:15: sin comprobar todavía.
8. **Operación.**
   - Prueba de punta a punta con una ficha de ensayo: el operador decidió en 6,2 s, con 83,8 s de margen, y volvió a esperar.
   - Arranque automático registrado para el centinela y el operador; sin probar hasta el próximo encendido.
   - Claude Code no lanza sesiones de fondo en carpetas sin confianza. Cambio: el operador corre en `C:\Windows\System32` y usa la ruta completa de `operador.py`.
9. **Cambios al plan por lo construido.**
   - El filtro de volatilidad y la «preventiva sin disparar» no estaban en el banco; si se aplicaran a REGLA, romperían la paridad. La volatilidad pasa a ser un dato de la ficha para el criterio de Claude.
   - El operador lee sus fichas con `pendientes`, porque los avisos de tareas en segundo plano no traen el texto.
10. **Veredicto, con los criterios tal como se escribieron:**
   - El punto 1 falla en la condición de pesos: al 16 %, los 30 días desde 100.000 COP terminan arriba en el 47,6 % de los arranques, frente al 60 % exigido.
   - Los puntos 3 y 4 están pendientes del papel en vivo.
   - Veredicto: **no consolidable con el 16 %**. Con las mismas apuestas, al 8 % desde 200.000 COP terminan arriba el 72,5 % de los arranques.

## Revisión 3 · 29/10/2026, 22:05 · sobre la orden «apueste el porcentaje que crea» (t21 y centinela v4)

1. **Información del futuro.** No se encontró.
   - El procedimiento del mes usa solo el historial a ciegas de los meses anteriores.
   - El medio Kelly usa los 6 meses anteriores.
   - El modelo que entrena el centinela da el mismo umbral que el banco (0,61 en ETH a 10 min para octubre).
   - t19 y t21, pasados a los módulos compartidos (`motor/modelo.py` y `motor/historial.py`), dan informes idénticos byte a byte.
2. **Elegir mirando el resultado.**
   - Las protecciones se decidieron con una regla fijada antes (elegir con 2022-23 y verificar con 2024-26), y no pasó ninguna.
   - El tamaño (medio Kelly) sale de la teoría; frente al mínimo fijo da casi lo mismo.
   - El cambio de procedimiento por historial sí se adoptó después de ver la t21. Fue mejor en 2024-26 (a 30 días termina arriba el 61,2 %, frente al 50,1 % de las reglas fijas en BTC), pero peor en 2022-23 y a un año. Por eso BTC FIJO sigue en vivo como cuenta de control.
3. **Cuentas.** Se apuesta el mayor entre la fracción y 5 USDT, y no se apuesta si la fracción es 0. Es igual en la t21 (`simular`) y en vivo (`monto_de`). Con 100.000 COP, la apuesta es siempre el mínimo hasta que el saldo pase de unos 453.000 COP (modelo ETH) o de unos 795.000 COP (BTC FIJO).
4. **Paridad.**
   - Camino real probado con el modelo sobre la vela de las 15:45: ficha, aprobación, cuatro cuentas y liquidación igual a la fórmula del banco.
   - La comparación diaria en vivo ahora incluye el modelo: decisión y diferencia de probabilidad.
5. **Operación.**
   - El operador se relanzó con el prompt v4 y decidió una ficha de ensayo en 5,9 s.
   - El lanzador solo da por vivo al operador si su latido tiene menos de 3 minutos; si no, cierra la sesión vieja y abre otra.
   - El recálculo mensual del banco se probó el 29/10 a las 21:52: guardó las velas hasta las 21:51, corrió t18 y t19 en BTC y ETH en 228 s y volvió a elegir el modelo a 10 min en ETH para octubre (sin cambio, como debía). Para noviembre elige el mismo, con medio Kelly de 4,48 %.
6. **Criterios de consolidación.** El punto 1 se escribió para el 16 %, y el umbral de 57,8 % solo vale para ese tamaño. Él delegó el tamaño, así que se lee con el tamaño nuevo. Esto es una desviación del plan y queda anotada: el cambio lo causó su orden, no un resultado.
   - Con medio Kelly y el procedimiento por historial, 30 días desde 100.000 COP terminan arriba en el 65,5 % de los arranques de 2022-26, por encima del 60 % exigido.
   - El límite corregido del acierto está por encima de 54,1 % en los dos tramos.
   - Con 60 s de retraso, el modelo a 10 min sigue en 55,4-55,8 %.
   - Siguen abiertos el punto 3 (7 días de paridad en vivo) y el 4 (100 apuestas en papel).
   - **Riesgo que no estaba en los criterios:** aun así, uno de cada tres arranques de 30 días quiebra (32,9 %), porque con 100.000 COP el mínimo de Binance es el 16 % de la cuenta.

## Revisión 4 · 29/10/2026, 22:20 · sobre las pruebas con oro (t22, t23)

1. **Fallo encontrado y corregido.** En la primera versión de `t22_oro_datos.py`, `np.arange(t0, t1 + 1) * 60000` salió con enteros de 32 bits (numpy 1.x en Windows) y la columna de tiempo se desbordó.
   - Lo delató el cruce entre PAXG y XAU, que dio 71.584 minutos en común en vez de 464.828.
   - Las corridas de t18 y t19 sobre esos archivos fallaron al leer las fechas; no se usó ningún resultado.
   - Se corrigió con `dtype=np.int64` y un `assert` sobre los pasos.
   - El resto del sistema no tiene ese fallo: BTC y ETH vienen de `astype(np.int64)` y la paridad de señales lo había comprobado.
2. **Empates.** En PAXG los empates fueron el 8 % de las apuestas; en BTC, el 0,1 %. Contarlos como fallo es lo que se hace en todas las pruebas. Sin contarlos, PAXG sube a 61-65 %, pero esa cifra viene de los años sin liquidez y no se toma como ventaja.
3. **Muestra del oro real.** XAUUSDT tiene 10,5 meses: la ventana de 12 meses no se llena, así que los meses elegidos usaron menos historia. Con 1.671 apuestas a 53,6 %, el límite de Wilson al 95 % (51,2 %) queda por debajo del equilibrio. No hay ventaja demostrada.
4. **Veredicto, sin cambiar los criterios:** ningún procedimiento con oro cumple el punto 1 de la sección 6 en el periodo reciente, y Binance no ofrece dónde apostarlo. No se agrega al centinela.
