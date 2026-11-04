# Plan total de las binarias · BTC/USDT (v7, congruente)

4 de noviembre de 2026, 00:35 (hora de Colombia). Reemplaza al v6 del 03/11, que quedó guardado como «posible plan v6» en Descargas y en la USB (partición NUEVO). La evidencia y la auditoría de congruencia están en `INFORME-TOTAL.md`.

## 1. La lógica única

A 10 minutos, BTC tiende a devolverse después de estirarse. La ventaja es pequeña, cambia con el tiempo y depende de entrar rápido y del pago. Por eso:
1. Solo se apuesta a la devolución, nunca a la continuación.
2. En real solo se opera cuando el papel de ese mismo día va sumando (su regla del 03/11, 23:58): cada señal llega con SÍ o NO. La primera pérdida de un SÍ apaga el real hasta el día siguiente. Sin apalancamiento.
3. Nada entra ni sale sin el protocolo de la sección 6.

## 2. Reglas que no se discuten

- Solo Contratos de Evento de Binance, solo BTCUSDT. «Trading» siempre significa esto.
- Papel hasta su orden expresa. En real la apuesta la toca él (Binance prohíbe bots y los Contratos de Evento no tienen API).
- Jamás apalancamiento, ni en real ni en papel (orden suya del 04/11).
- Ningún agente opera solo, ni en los equipos ni en la nube: los Contratos de Evento no tienen API (página oficial de Binance del 28/10/2026: solo en la app de Android e iOS) y Binance prohíbe los bots en ellos. Automatizar la pantalla del teléfono arriesgaría el cierre de la cuenta con su dinero dentro.
- Tope por apuesta: 16 % del saldo, y mejor menos (orden suya del 04/11). Con el mínimo de 5 USDT, el saldo debe ser de 31,25 USDT o más.
- Parada: la primera pérdida de un SÍ apaga el día; nunca se llega a dos pérdidas reales en un día (su máximo del 04/11).
- Solo velas cerradas: cada decisión espera el cierre de la vela de 5 min; ninguna se toma con una vela en formación.
- Binance directo; todo lo demás por Tor. Nadie ve sus operaciones; ninguna IA externa recibe apuestas ni saldos.
- Pesos colombianos y hora de Colombia.

## 3. Dónde corre

- Caja T95H (principal, `/data/local/tmp/centinela`) y teléfono (respaldo, Termux `~/centinela`), 24/7, con arranque solo (Termux:Boot), Tor, centinela, avisador, semáforo y, en la caja, vigilante de 80 °C. El teléfono calla mientras ve el latido de la caja.
- PC: investigación (`cuant/`) y Pulso. El centinela del PC está parado con `PARAR` y sin arranque con Windows.
- Parar un equipo: archivo `PARAR` en su carpeta. Volver: borrarlo y `sh arrancar.sh` en Termux.

## 4. Qué se opera

- **Núcleo:** ruptura de 20 velas de 5 minutos al revés en BTC, binaria de 10 minutos. Lleva la cuenta de papel del semáforo.
- **BTC FIJO:** reglas de BTC del mes, todas de devolución; control y avisos en papel.
- **REGLA:** en noviembre mide ETH en silencio (elegida el 1/11, sin avisos). Desde el 1/12, elección mensual solo entre estrategias de devolución en BTC; si ninguna pasa la valla del año (Wilson sobre el equilibrio), no apuesta ese mes.
- **AZAR:** control. **CLAUDE:** sin operador; no apuesta.

## 5. SÍ o NO (cómo se decide el real; su regla desde el 04/11)

- En cada señal del núcleo, la caja (y el teléfono si la caja cae) manda «SÍ OPERAR» si el neto del papel de hoy (día de Colombia; +0,85 por acierto y −1 por fallo, solo apuestas ya cerradas, entrando 60 s tarde) es mayor que 0, ningún SÍ ha perdido hoy y el interés abierto de futuros no sube (P15: cambio en 15 min de hasta +0,022 %). Si no, «NO OPERAR (solo papel)», con el motivo. El día empieza en NO. Medido en 2024-sep 2026: el SÍ acierta 55,5 % con 1,8 apuestas al día.
- La primera pérdida de un SÍ lo apaga hasta el día siguiente, y se le avisa.
- Dinero real: solo con el archivo `REAL_AUTORIZADO` en la carpeta del centinela (caja y teléfono), que se crea con su orden expresa. Sin él, el SÍ queda en papel como espejo del real y el mensaje lo dice. Tocar en segundos: cada minuto de demora cuesta cerca de 1,7 puntos. 5 USDT, sin apalancamiento.
- Lo medido (C9, variante D1 elegida en 2021-2023): no sube el acierto (54,8 % frente a 54,4 % del núcleo en 2024-sep 2026, p = 0,35), pero recorta el riesgo: 2,1 apuestas reales al día, neto de +0,47 M COP y caída máxima de 0,46 M COP, frente a 1,79 M de apostar siempre. El VERDE anterior (últimas 100 en 58 %) daba 0,7 al día con 54,3 %. Paridad entre la caja y el banco: 14 SÍ de 14 iguales.
- Gráfica: cada SÍ o NO llega a su Telegram como foto con las seis líneas, dibujada por la caja con las velas de futuros con que decide (semáforo v3.2, `graficas.py`, idéntica a Pulso píxel a píxel cuando están las seis; si el máximo o el mínimo es de los últimos 5 min, esa línea larga no se traza y el pie lo dice). Pulso sigue mandando cada 5 min «Sus seis líneas en 1 min» con las velas de contado que muestra la app: techo y piso largos (azul), techo y piso cortos desde el inicio de la última caída o subida (ámbar) y las dos horizontales donde el precio se queda (violeta). Las líneas son para mirar; solo su señal de dos velas al revés está probada (t31, 56-57 %).
- Comprobantes («facturación», orden suya del 04/11): cada SÍ cerrado trae un PDF con la entrada, el vencimiento, el resultado con el precio de futuros y con el índice, y enlaces que abren en Binance las velas oficiales de ese minuto, con la huella SHA-256 del registro (`comprobantes.py`). A las 00:15 llega el resumen del papel del día anterior, con un enlace por señal. Lo hace el bot solo, en la caja y, si la caja cae, en el teléfono.
- Para la gente: si él crea un canal de Telegram y pone al bot como administrador, los SÍ y NO con su foto también se publican ahí (archivo `~/.config/binarias/canal` en cada equipo). Los comprobantes van solo a él.
- Guía para la gente: `guia/` (página, Markdown y texto corto para Telegram), sin nombres ni claves.

## 6. Protocolo para cualquier idea

1. Regla y criterio escritos aquí antes de ver resultados.
2. Debe ser de devolución; lo que apueste a la continuación se rechaza sin probar.
3. Elegir en un tramo y juzgar en otro sin usar (2021-2023 → 2024-2026 → lo más reciente).
4. Benjamini-Hochberg si son muchas variantes; Wilson; comparación con el azar y con el máximo del azar; PBO si se elige entre muchas.
5. Entrada 60 s tarde y pagos de 0,80, 0,85 y 0,90.
6. Rachas y quiebra por remuestreo con 100.000 COP y el mínimo de 5 USDT.
7. Validación mes a mes con purga de un plazo.
8. Paridad entre el centinela y el banco.
9. «Listo» solo con los criterios cumplidos.

## 7. Siguientes pasos (todos congruentes, con su regla)

- **P1 · Pago y demora reales.** Él anota el pago que ofrece Binance en 20 apuestas y cuántos segundos tarda en tocar tras el aviso. Se recalculan el equilibrio y el costo de la demora.
- **P2 · Selección mensual de devolución.** Antes del 1/12 corre en el teléfono con el mismo código (rutas ya portables) y solo con candidatas de devolución en BTC; debe dar lo mismo que en el PC.
- **P3 · Filtro de volumen alto en BTC (t27).** Al centinela y al semáforo, con la misma cuenta en el banco.
- **P4 · Grabar desde ya en la caja.** Libro de 20 niveles cada 10 s, operaciones una por una y opciones de Deribit cada hora. A los 90 días, la hipótesis congruente: la devolución acierta 1 punto o más con GEX positiva que con GEX negativa. Si se cumple, entra como filtro.
- **P5 · Defensa macro.** No operar 30 minutos antes ni después de FOMC, IPC y nóminas de EE. UU. Entra si sube 0,5 puntos o más sin bajar de 3 apuestas al día.
- **P6 · Su señal de dos velas al revés (sección 18 del PLAN).** Como candidata de devolución del banco.
- **P7 · SÍ en vivo.** A los 30 días (03/12), comparar el acierto de las señales SÍ con el de las NO, en papel. Si el SÍ queda 1 punto o más por debajo, se le avisa con los números y decide él.

Probados y descartados hoy: E1 (sumar impulso y anomalía a la ruptura diluye: 53,1 %), el HMM de la racha como semáforo (sin efecto), y por incongruentes E3, E10 y E11 del plan v5.

### 7b. Pruebas C9 (reglas escritas el 03/11/2026 a las 23:59, antes de ver resultados)

Base común: el núcleo en BTC, entrada 60 s tarde, empate = fallo, pago 0,85 (gana +0,85, pierde −1). Solo cuentan apuestas de papel ya cerradas antes de cada señal. Se elige en 2021-2023 y se juzga en 2024-sep 2026 y en octubre de 2026. Guion: `cuant/c9_mejoras.py`.

- **P8 · Su regla: el real solo cuando el papel esté sumando** (dicho por él el 03/11 a las 23:58: «solo en días que esté sumando directamente en nuestras operaciones, sí o sí sumando, generando dinero»). Variantes: D, el neto de papel del día de Colombia es mayor que 0; H2, H3 y H6, el neto de las últimas 2, 3 o 6 horas es mayor que 0; D1, D con parada en la primera pérdida real del día; R2 y R3, los últimos 2 o 3 papeles cerrados acertaron. Se comparan con el semáforo VERDE actual (S2 con parada). Se elige en 2021-2023 la de mejor acierto con al menos 1 apuesta real por día en promedio. Entra si en 2024-sep 2026 acierta 1 punto o más sobre el núcleo sin filtro y supera al 95 % de 2.000 sorteos que toman al azar la misma cantidad de señales de los mismos días. Entre o no, se mide en vivo en la cuenta CLAUDE, que pasa a ser el espejo del real.
- **P9 · Flujo informado** (VPIN simplificado; Easley, López de Prado y O'Hara, 2012). q = desequilibrio entre compra y venta agresivas de los últimos 15 min en el sentido de la ruptura. No se apuesta si q supera el percentil 50, 70, 80 o 90 de 2021-2023.
- **P10 · Régimen de devolución** (razón de varianzas; Lo y MacKinlay, 1988). Autocorrelación de los tramos de 10 min de las últimas 24 h o 72 h; solo se apuesta si es menor que 0, −0,05 o −0,10.
- **P11 · Horas** (su «esas mismas horas»). H12: las 12 horas UTC de mejor acierto del núcleo en 2021-2023. HV: solo en la hora del día cuyo papel de los últimos 30 días esté sumando.
- **P12 · Metaetiquetado** (López de Prado, 2018; Joubert, 2022). Regresión logística propia sobre las señales del núcleo con variables ya medidas: impulso de 15 min, flujo, volumen, ATR, alineación de 1 h, 4 h y 1 día, Bollinger, sesión, fin de semana, autocorrelación de 24 h, tamaño de la ruptura sobre el ATR y hora. Aprende en 2021-2022 y elige en 2023 la parte que se apuesta (30, 50 o 70 % de mayor probabilidad).
- Criterio común de P9 a P12: entra si en 2024-sep 2026 sube 0,5 puntos o más sobre el núcleo (1 punto en P12), con p < 0,05 frente a 2.000 filtros al azar que quitan la misma proporción de señales y Benjamini-Hochberg entre todas las variantes, y conserva al menos 6 apuestas al día.
- **P13 · Medir con el precio con que paga Binance.** Los Contratos de Evento se liquidan con el índice de precio (página de Binance, actualizada el 28/10/2026), no con el último precio de futuros que usa el centinela. Se mide en 2024-sep 2026 cuántas señales cambian de resultado; si el acierto cambia 0,3 puntos o más, el papel pasa a medirse con el índice.
- **P14 · Estirón por liquidaciones** (escrita el 04/11 a las 00:34, antes de bajar los datos; flujo forzado, arXiv 2607.27070). Con el interés abierto de futuros de Binance cada 5 min (desde el 01/12/2021), en cada señal: cambio del interés abierto en los 15 min previos, tomado con 5 min de margen para no mirar adelante. Hipótesis congruente: la devolución acierta más cuando el estirón vino con cierres forzados (interés abierto que cae) que con posiciones nuevas. Variantes: solo apostar si el cambio está por debajo del percentil 50 o 30 de dic 2021-2023. Mismo criterio común que P9 a P12, con Benjamini-Hochberg entre las dos variantes.
- **P14b · El mismo filtro con 5 min más de margen** (escrita el 04/11 a las 00:31, antes de correrla). El archivo histórico marca cada instantánea 5 min antes que el servicio en vivo de Binance (comprobado con el 02/11: el valor de las 12:05 del archivo es el de las 12:10 en vivo). Para no usar información que la caja no tendría, se repite P14 percentil 50 con instantáneas de hasta la decisión − 600 s y − 1.500 s, y el umbral recalculado igual. P14 solo se aplica en vivo si P14b también cumple el criterio común; en vivo se usa la instantánea publicada más reciente que cumpla ese mismo margen.
- **P15 · Su regla con el filtro P14b** (escrita el 04/11 a las 00:34, antes de medirla). SÍ = papel de hoy sumando, ningún SÍ perdido hoy e interés abierto que no sube (P14b). El papel sigue siendo el núcleo entero. Se mide en 2024-sep 2026 y octubre de 2026; va a la caja si su acierto no queda por debajo del de D1 y deja al menos 1 apuesta real al día. Si falta el dato del interés abierto, la señal va como NO.

- **P3b · Volumen alto sobre el SÍ** (escrita el 04/11 antes de medirla, que fue a la 01:00; es el P3 pendiente desde el 31/10). No dar SÍ si el volumen de los 15 min previos supera 1,3 veces su media de 7 días (la marca «volumen alto» de `cuant/base.py`). Entra si, sobre el SÍ de P15, sube 0,5 puntos o más en 2024-sep 2026, con p < 0,05 frente a quitar al azar la misma proporción de SÍ, y deja 1 SÍ al día o más.
- **P16 · Vela de confirmación** (escrita el 04/11 antes de medirla, que fue a la 01:00; pedido suyo: «que siempre tenga espera de velas de confirmación»). La decisión ya espera el cierre de la vela de 5 min. P16 exige además que la vela de 1 min siguiente, la misma en que hoy se entra, cierre en el sentido de la apuesta, y se entra a su cierre (60 s tarde, como ahora). P16b exige las dos primeras velas de 1 min en el sentido de la apuesta y entra 120 s tarde. Sobre el núcleo, criterio común (+0,5 puntos, p < 0,05, Benjamini-Hochberg entre las dos, 6 apuestas al día o más). Sobre el SÍ, entra si no baja el acierto de P15 y deja 1 SÍ al día o más.

**Resultados del 04/11 (detalle en `INFORME-TOTAL.md`, sección 8):**
- P8, su regla: no sube el acierto (D1, 54,8 % frente a 54,4 %, p = 0,35), pero recorta el riesgo (caída máxima de 0,46 M COP frente a 1,79 M). Queda como forma de encender el real por ser su regla y la más prudente.
- P9 a P12 (VPIN, régimen, horas, metaetiquetado): ninguno entra (de −1,16 a +0,51 puntos).
- P13, índice de Binance: −0,25 puntos; no cambia la medida, pero cada apuesta guarda los dos resultados.
- P14 y P14b, interés abierto que no sube: **ENTRA**. Con el margen honesto (P14b): 55,2 % frente a 54,4 % en 2024-sep 2026 (+0,83 puntos, p = 0,011, 8,5 al día) y 65,5 % en octubre; con interés abierto que sube, 53,3 %. En 2021-2023 no se notaba (−0,17 puntos): es un efecto reciente y se vigila en vivo.
- P15, su regla con el filtro: 55,5 % en 2024-sep 2026 con 1,8 apuestas reales al día (neto +0,78 M COP, caída máxima 0,45 M) y 66,7 % en octubre (57 apuestas). Va a la caja y al teléfono desde el 04/11 a las 00:29 (semáforo v3.1), con paridad de 84 de 84 señales frente al banco.
- P3b, volumen alto sobre el SÍ: no entra (−0,46 puntos, p = 0,71). La defensa de volumen alto sigue valiendo solo para las reglas del banco (t27).
- P16 y P16b, velas de confirmación: no entran. Sobre el núcleo bajan el acierto (53,0 % y 52,3 % frente a 54,4 %, p = 1). Sobre el SÍ, P16 cumplió por 0,3 puntos el criterio escrito (55,8 % frente a 55,5 % en 2024-sep 2026), pero perdió 3,1 puntos en 2021-2023 y 7,2 en octubre y deja menos ganancia por día; como el núcleo la rechaza y los otros dos tramos la contradicen, no se aplica. La confirmación que queda es la que ya había: solo se decide con la vela de 5 min cerrada.

## 8. Criterios para el dinero real (todos, y su orden expresa)

1. Pago real medido y equilibrio recalculado.
2. Núcleo con Wilson del último año sobre ese equilibrio, entrando con su demora real.
3. Paridad de 7 días entre la caja y el banco.
4. 300 o más apuestas de papel del núcleo en la caja, 1 punto o más sobre el equilibrio.
5. SÍ en esa señal (papel de hoy sumando, ningún SÍ perdido e interés abierto que no sube); parada en la primera pérdida.
6. Capital: el mínimo de 5 USDT no puede pasar del 16 % del saldo (saldo de 31,25 USDT o más); con 100.000 COP es el 15,9 %.
7. Archivo `REAL_AUTORIZADO` creado en la caja y el teléfono con su orden expresa.

## 9. Cómo no se olvida

Enganche de inicio de Claude con el SIGUIENTE PASO del bloc; encargo en `n8n\encargos\encargo-binarias-plan-v5.md` (apunta a este plan); bloc del Escritorio con su sección AL FRENTE; recordatorio en su teléfono.
