# Plan v5 de las binarias · BTC/USDT

Versión 5 · 3 de noviembre de 2026, 21:00 (hora de Colombia). Reemplaza la conducción del PLAN.md (secciones 1 a 18 quedan como historia y evidencia). Base: `cuant/INFORME-INVESTIGACION-CUANTITATIVA-2026-11-03.md`.

## 0. Qué cambia frente a la v4

1. Todo se unifica en BTC/USDT (orden de Nicolás del 03/11). ETH sigue midiéndose en silencio, sin avisos, hasta que el 1/12 la selección mensual quede restringida a BTC.
2. El centinela salió del PC: corre en la caja T95H (principal) y en el teléfono (respaldo), 24/7, con arranque solo al encender. El PC ya no lo ejecuta.
3. Semáforo papel → real: el modo real solo se enciende el día en que el papel de BTC va bien, y se apaga con la primera pérdida. Sin apalancamiento.
4. Meta honesta: 56-57 % fuera de muestra con el pago real. El 85,7 % no existe en los datos (sección 4 del informe).
5. Toda idea nueva pasa por el protocolo de la sección 5. Lo descartado con prueba no se vuelve a probar igual (sección 6).

## 1. Reglas que no se discuten

- Solo Contratos de Evento de Binance (binarias por tiempo). «Trading» siempre significa esto.
- Todo en papel hasta su orden expresa. Ningún código mueve dinero. En real, la apuesta la toca él en la app: Binance prohíbe los bots en los Contratos de Evento (términos, sección 26).
- En real, sin apalancamiento. El apalancamiento solo se estudia en papel, y solo en futuros (en binarias no existe).
- Binance va directo; todo lo demás sale por Tor. Nadie ve sus operaciones; ninguna IA externa recibe apuestas ni saldos.
- Pesos colombianos y hora de Colombia. El dato, no la defensa del dato.

## 2. Dónde corre cada cosa

- Caja T95H (principal; ADB por la red en 192.168.20.45): `/data/local/tmp/centinela/`. Termux:Boot ejecuta `~/.termux/boot/20-centinela.sh`, que llama a `arrancar.sh`: Tor, centinela (`binarias.py` con su vigía) y avisador (`avisos.py`, que lleva dentro el semáforo `semaforo.py` y el vigilante de temperatura de 80 °C). Publica en la red de la casa solo su latido (puerto 8793). Los arranques viejos (fútbol, descargador, recordatorio, surebets) quedaron en `~/.termux/boot-desactivados/`.
- Teléfono (respaldo): lo mismo en la carpeta privada de Termux, `~/centinela/`, rol «telefono». Calla mientras ve el latido de la caja; si no la ve (caja caída o él fuera de casa), avisa él. Fuera de casa pueden llegar avisos dobles, marcados [caja] y [teléfono].
- PC: Pulso (gráficas, voz, noticias) y la investigación (`cuant/`). El centinela del PC quedó parado con el archivo `PARAR` y sin arranque con Windows.
- Parar en un equipo: crear el archivo `PARAR` en su carpeta. Volver: borrarlo y ejecutar `sh arrancar.sh` dentro de Termux.
- La clave del bot Centro nocturno vive en `~/.config/binarias/telegram` (permiso 600) de cada Termux; nunca en los archivos del proyecto.
- Ver las cuentas en el teléfono: navegador en `http://127.0.0.1:8792`.

## 3. Cuentas en papel

- REGLA: procedimiento del mes. En noviembre es el modelo de 10 minutos de ETH (elegido el 1/11); desde el 1/12 solo procedimientos de BTC. Si ninguno de BTC pasa la valla (Wilson del último año sobre el equilibrio), REGLA no apuesta ese mes.
- BTC FIJO: reglas de BTC, control fijo. Es la cuenta de BTC que avisa en noviembre.
- AZAR: misma hora, sentido al azar. Control.
- CLAUDE: sin operador desde el 02/11; no apuesta.
- Semáforo BTC: cuenta propia con la «ruptura al revés» en BTC, unas 14 señales al día, que alimenta el semáforo.

## 4. El semáforo papel → real

- Al empezar cada día de Colombia: VERDE si las últimas 100 apuestas de papel del semáforo aciertan 58 % o más; si no, ROJO. Le llega por Telegram: «Semáforo BTC del día: VERDE/ROJO».
- En VERDE, cada señal le llega como «REAL: toque ahora BTC SUBE/BAJA a 10 min», con el precio y la hora de vencimiento. 5 USDT, sin apalancamiento.
- La primera pérdida en real apaga el modo real hasta el día siguiente y se le avisa.
- Evidencia (C7): 59,8 % con días verdes y parada en la primera pérdida, frente a 58,3 % con días al azar (p = 0,003), en apuestas de 2021-2026 entrando 60 s tarde. Es una pista con 27 comparaciones: se confirma en vivo (E2).
- El 03/11 el semáforo está en ROJO (48 % en las últimas 100).

## 5. Protocolo obligatorio para cualquier idea nueva

1. La regla y el criterio de decisión se escriben aquí antes de ver resultados.
2. Se elige en un tramo y se juzga en otro que no se usó (2021-2023 → 2024-2026 → lo más reciente).
3. Benjamini-Hochberg si se prueban muchas variantes; límite de Wilson; comparación con el máximo que daría el azar.
4. PBO por CSCV si se elige entre muchas.
5. Entrada 60 s tarde y pagos de 0,80, 0,85 y 0,90.
6. Rachas y quiebra por remuestreo con 100.000 COP y el mínimo de 5 USDT.
7. Lo que se adopte se valida mes a mes (walk-forward) con purga de un plazo entre tramos.
8. Paridad: el centinela y el banco deben dar lo mismo sobre las mismas velas.
9. «Listo» solo con los criterios cumplidos; si no, «no consolidable», aunque corra.

## 6. Descartado con prueba (no repetir igual)

85,7 % de acierto; SMC, ICT y CRT a 10 minutos (FVG, order blocks, AMD, área de valor, premium y discount, OTE, SMT, killzones, silver bullet, CRT de 1 h y 4 h); cruzar todas las dimensiones en cartera; mano caliente y «pausar al ganar» como fuente de ventaja; semáforo del día anterior; macro y Banco Mundial como señal de 10 minutos; su estrategia de dos resistencias a favor de la ruptura; tocar la segunda resistencia; triángulo; MHI y torres gemelas; martingala; el 16 % fijo; oro.

## 7. Experimentos siguientes (regla de decisión escrita hoy)

- **E1 · Familia de reversión en BTC.** Apuesta si dispara la ruptura al revés, la caída o subida de 15 minutos mayor que una desviación (al revés) o la anomalía de z ≥ 4 (al revés), y ninguna contradice a otra. Entra al banco si en 2024 a sep-2026 da 56 % o más con 4 o más apuestas al día y Wilson sobre 54,05 %, y en oct-nov de 2026 no baja de 54 %.
- **E2 · Semáforo en vivo.** A los 30 días, comparar el acierto de papel de los días verdes con el de los rojos. Se mantiene si los verdes superan a los rojos por 1 punto o más; si no, el modo real pasa a depender solo de la consolidación (sección 8).
- **E3 · Libro de órdenes con la ruptura.** Apostar la ruptura al revés solo si el desequilibrio a ±1 % no la contradice. Entra si sube 1 punto o más en la prueba con 3 o más apuestas al día.
- **E4 · Grabar desde ya en la caja.** Operaciones una por una (footprint), libro de 20 niveles cada 10 s y opciones de Deribit por hora (GEX, gamma flip, muros, flujo). A los 90 días: entra lo que sume 1 punto o más a E1, con la misma regla.
- **E5 · Defensa macro.** No apostar 30 minutos antes ni después de FOMC, IPC y nóminas de EE. UU. (calendario oficial). Entra si sube 0,5 puntos o más sin bajar de 3 apuestas al día.
- **E6 · Pago y retraso reales.** Él anota 20 pagos que le ofrece Binance y la hora en que toca cada aviso. Se recalcula el equilibrio y el costo del retraso.
- **E7 · Selección mensual portable.** Antes del 1/12, la selección corre en el teléfono con el mismo código (rutas por variables de entorno ya preparadas) y debe dar lo mismo que en el PC.
- **E8 · Filtro de volumen alto de BTC (t27).** Al centinela, con la misma cuenta en el banco y en vivo.
- **E9 · Su señal de dos velas en contra (sección 18 del PLAN).** Como candidata del banco, con la elección mensual.

## 8. Criterios para el dinero real (todos, además de su orden expresa)

1. Pago real medido (E6) y equilibrio recalculado con él.
2. Banco a ciegas de BTC con Wilson del último año sobre el equilibrio del pago real.
3. Paridad de 7 días entre la caja y el banco.
4. 300 o más apuestas de papel de BTC en la caja, con acierto 1 punto o más sobre el equilibrio y no significativamente por debajo del histórico.
5. Semáforo en VERDE ese día.
6. Capital: con 100.000 COP el mínimo de 5 USDT es el 15,9 % del saldo y 30 días quiebran una de cada tres veces; se le dice una vez, sin insistir. La decisión es suya.

## 9. Lo que decide él

El pago real (leerlo en la app); si sube el capital; si retira la cuenta CLAUDE y el operador; si quiere que ETH vuelva a avisar; el registrador de sus comentarios de Telegram (o reenviarlos al bot); los dos traders que mencionó; la reactivación de los agentes en la nube.

## 10. Cómo no se olvida

El enganche de inicio de Claude (`recordatorio_encargo.py`) muestra el siguiente paso de binarias al abrir cada sesión; el encargo vive en `n8n\encargos\encargo-binarias-plan-v5.md` y no se archiva hasta cumplir la sección 8; el bloc (`Desktop\BLOC BINARIAS - TODO EN UNO.txt`) tiene al frente el estado del 03/11; recordatorio en su teléfono.
