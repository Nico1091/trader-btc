# Consolidación del agente trader de BTC (sesión en la nube, 25/10/2026)

Informe del encargo `ENCARGO-CLOUD.md`. Solo papel: ni dinero real, ni claves, ni cuentas, ni brokers.

## Conclusión en tres líneas

1. **Hay una ventaja que resiste todo lo que le pedí: P11, el largo del lunes UTC.** Son 353 operaciones de 2020 a 2026: +104,6 % neto y +69,3 % con comisión doble, positiva en el ajuste (2020-2023) y en la prueba (2024-2026). La segunda es P05b, pero solo en los largos o con un veto de velas de 1 h.
2. **La MEZCLA de junio no se sostiene con el rigor de octubre** (1.610 operaciones, −107 % neto). Los patrones de vela no sirven como entrada (0 de 144 combinaciones) y como veto solo ayudan en un caso concreto, no en general.
3. **Tres operaciones al día con 40.000 pesos no son sostenibles.** Las ventajas medidas dan de 1 a 2,5 operaciones por semana, y con la orden mínima de futuros no se puede arriesgar el 1,5 %. La forma realista es en contado y solo en largo: de 1.500 a 2.400 pesos al año de ganancia esperada, sin tocar el capital.

Datos de todo el informe: velas de 1 minuto de BTCUSDT perpetuo (futuros USDⓈ-M de Binance), de data.binance.vision, del 01/01/2020 al 24/10/2026. Son 3.584.160 velas en 105 archivos, con el SHA-256 correcto y sin huecos: las mismas que usó la rutina. Ajuste: 2020-2023. Prueba: 2024-01 a 2026-10, mirada una sola vez por variante. Código en `consolidacion/`.

---

## Paso 0: lo que entendí (10 líneas)

1. El proyecto es uno: un agente que opera BTC en papel con 40.000 pesos (12,59 USDT). «arbitraje-cero-gas» y los bots de ETH son historia; de ahí solo valen las estrategias del curso probadas en junio.
2. Tiene dos partes: la rutina de la nube `trig_01HhTpY4sVUqaj1ui3qi7wyQ` (cada 6 h, Claude decide en el libro CLAUDE) y el agente Python del PC, que opera a minutos y pierde por comisión.
3. Lo medido: a segundos y minutos BTC es casi azar (AUC 0,51-0,56) y la comisión (0,04-0,20 % por ciclo) se come movimientos de 0,05-0,14 %.
4. En junio, en 1 h y 24 meses de spot, ganó la MEZCLA (retroceso largo en tendencia + corto con range_pos ≥ 0,9): 864 ops, +248 %. En octubre, sus reglas sin clasificador dieron −1,7 % (429 ops) y −44,6 % con costo doble: hay que revalidarla.
5. Los patrones de vela del curso no sirven como entrada; como veto «nunca empeora». Eso se midió en junio sobre 1 h y está por confirmar.
6. Candidatas vivas: P05b (banda ATR de E09 con entrada de creador, k = 0,5), con ventaja bruta real pero frágil: −13,2 % con costo doble y caída del 22 %. P11 (largo del lunes UTC con stop del 3 %): 355 ops, +109 % neto, +73,5 % con el doble, pero solo 38 ops fuera de muestra real.
7. Papel: CL-001 a CL-004 no se activaron. Quedan abiertas CL-005/CL-006 (horquilla de P05b, hasta las 23:45 UTC del 25/10) y CL-007 (P11, lunes 26/10). El libro CLAUDE sigue en 40.000 pesos sin operaciones cerradas.
8. A ciegas: 60 decisiones, 20 operaciones, 11 aciertos, +7,63 % frente a −0,63 % del azar. La muestra es pequeña y la confianza alta rinde menos (R13).
9. Reglas de evidencia: datos reales de data.binance.vision, 0,05 %/lado y repetir con el doble, comparar con el azar, separar dentro y fuera de muestra, decir el tamaño de la muestra (menos de 200 es débil), desconfiar de 12 meses o menos.
10. La meta de tres operaciones al día con 40.000 pesos choca con lo medido. «No perder» se traduce en reglas de riesgo y en no entrar sin ventaja. No se fuerza nada.

**Comprobación del motor.** Antes de medir nada nuevo, reproduje dos cifras de la rutina con mi código:
- **P11:** 353 operaciones y +104,6 % neto. La rutina tenía 355 y +109,0 %; yo empiezo el 16/01/2020.
- **P05b:** 1.020 operaciones, +64,6 % neto y −6,8 % con el doble. La rutina tenía 1.012, +57,5 % y −13,3 %; ella sumó la financiación real.

Coinciden lo bastante para fiarse del resto.

---

## Tarea 1: operaciones en papel hasta hoy

Fuentes: el REGISTRO v5 del correo del 25/10 a las 14:18 UTC y Gmail. No hay correos de la rutina más nuevos: la próxima pasada es a las 20:00 UTC. Precio de las 16:19 UTC: 80.501,79 (Coinbase).

| Id | Libro o estrategia | Qué era | Resultado | Contra el azar |
|---|---|---|---|---|
| CL-001 / CL-002 | CLAUDE (P05b) | Horquilla hasta las 08:00 UTC | No se activaron (rango 80.310-80.925) | No cuenta |
| CL-003 / CL-004 | CLAUDE (P05b) | Horquilla 81.863,57 / 79.675,77 hasta las 14:00 | No se activaron (cierres de 15 m de 80.069 a 80.514) | No cuenta |
| CL-005 / CL-006 | CLAUDE (P05b) | Horquilla con los mismos niveles hasta las 23:45 | **Abiertas.** A las 16:15 UTC sin activarse (cierres de 15 m de 80.229 a 80.584) | — |
| CL-007 | CLAUDE (P11) | Largo el lunes 26 a las 00:00 UTC, stop 3 % | Pendiente | Testigo AZ-008 |
| ORD-001 | E01 (corto en techo) | Condicionada | No se activó | No cuenta |
| ORD-002 | E09 tomador | Condicionada | No se activó | No cuenta |
| ORD-003 | P05b | Condicionada hasta las 08:00 | No se activó | No cuenta |
| ORD-004 / ORD-005 | P05b / P05c | Condicionadas hasta las 23:45 | Abiertas, sin activarse a las 16:15 | — |
| ORD-006 | P11 | Lunes 26 | Pendiente | — |
| AZ-001 | Azar | Corto del 24/10 22:53 | **−0,42 % neto** (cerrada) | Es el azar |
| AZ-002 … AZ-006 | Azar | Cortos de hoy | Abiertas. Marca a las 16:19: +0,29, +0,33, 0,00, −0,27 y −0,35 % bruto | — |
| AZ-007 / AZ-008 | Azar | Largo 18:49 / lunes 00:00 | Pendientes | — |

**Entrenamiento a ciegas** (las únicas decisiones ya resueltas del libro CLAUDE):

| Sesión | Operaciones | Aciertos | Neto | Azar | Percentil |
|---|---|---|---|---|---|
| 25/10 02:10 (contado) | 6 | 4 | +3,04 % | −0,33 % | 90 |
| 25/10 08:09 (futuros) | 7 | 3 | +1,60 % | +0,18 % | 62 |
| 25/10 14:07 (futuros) | 7 | 4 | +2,99 % | −0,48 % | 95 |
| **Total** | **20** | **11** | **+7,63 %** | **−0,63 %** | — |
| Filtro de P05b a ciegas | 13 de 20 tomadas | — | −3,58 % (todas: −1,73 %) | — | 23: el filtro resta |

**Lectura honesta.** En papel en vivo todavía no hay ni una operación cerrada de una estrategia ni del libro CLAUDE: todo lo que se ordenó desde el 24/10 quedó sin activarse, en un fin de semana con un rango de 0,7 %. La única comparación posible es la de las ciegas: 20 operaciones con +8,3 puntos sobre el azar. Es una muestra débil (el criterio pide 100). Y el filtro propio sobre P05b restó.

---

## Tarea 2: cada vela y lo que significa

**Método** (`consolidacion/t2_velas.py`):
- Patrones definidos como en el curso: forma más contexto. Los de giro exigen una tendencia previa de 10 velas en contra.
- Marcos de 15 m, 1 h y 4 h armados con las velas de 1 minuto.
- Entrada al cierre de la vela del patrón, en el lado que indica.
- Retorno a 1, 4 y 24 horas con las velas de 1 minuto.
- **Neto:** bruto − 0,10 % (0,05 %/lado); el doble está en el CSV.
- **Percentil contra el azar:** la media del patrón frente a 2.000 sorteos de igual tamaño, de velas del mismo marco y del mismo lado. 50 es lo que da el azar; 95 o más es ventaja.
- Patrones de indecisión (peonza y dojis): miden si anticipan el **tamaño** del movimiento, no su dirección.

**Resultado:**
- **Como entrada no sirven. Se confirma.** De 144 combinaciones direccionales (16 patrones × 3 marcos × 3 horizontes), ninguna gana neto y supera el percentil 95 en el ajuste y en la prueba a la vez. Solo 8 dan neto positivo en ambos tramos, y en la prueba con percentiles de 55 a 92: nada sólido.
- **El percentil medio es 49 (ajuste) y 48 (prueba):** en promedio, el lado que «anuncia» el patrón rinde igual que el azar.
- **Casos que destacan, ninguno operable:**
  - El **martillo de 15 m** es una trampa: en la hora siguiente el precio **baja** (percentil 0,9 y 7).
  - El **martillo invertido de 15 m** sí acierta la dirección a 4 h (percentiles 96 y 98), pero gana +0,08-0,10 % bruto, que no paga el 0,10 % de comisión.
  - El **harami alcista** y la **estrella de la mañana de 1 h** a 24 h eran excelentes en 2020-2023 (percentiles 99,8 y 99,2) y se desinflan en 2024-2026 (78 y 61). Es el aviso de siempre: lo que brilla en un tramo no sobrevive al siguiente.
  - **Tres soldados blancos de 1 h** a 24 h: percentiles 89 y 92, con solo 85 y 75 casos (muestra débil).
- **La indecisión anticipa movimiento, no dirección.** Tras un doji de piernas largas el movimiento siguiente es mayor (percentil 100 a 1 h en los dos tramos). Tras una peonza de 1 h o 4 h es menor (percentil 0-3). Sirve para saber *cuándo* no esperar movimiento, no para elegir el lado.
- **Como veto, «nunca empeora» queda refutado.** Solo 40 de 144 combinaciones van mejor que el azar en los dos tramos (el azar daría unas 36). En la tarea 3 el veto ayuda en un caso (1 h, 3 velas) y empeora en otros (15 m, 3 velas; 4 h, 3 velas).

**Tabla por patrón y marco de tiempo.** Neto medio por operación en la prueba, en %. Percentil frente al azar en el ajuste y en la prueba. Para la indecisión: movimiento medio |r| del patrón frente al del azar y su percentil. El CSV completo, con el bruto, el doble y el acierto, está en `consolidacion/t2_velas.csv`.

| Patrón | Marco | Lado | Casos (aj./pr.) | 1 h: neto medio pr. · pct aj./pr. | 4 h: neto medio pr. · pct aj./pr. | 24 h: neto medio pr. · pct aj./pr. |
|---|---|---|---|---|---|---|
| Envolvente alcista | 15 m | largo | 7253/5214 | -0,10 · 18/16 | -0,08 · 57/71 | -0,04 · 40/20 |
| Envolvente alcista | 1 h | largo | 1754/1295 | -0,09 · 75/64 | -0,07 · 3/64 | -0,00 · 33/57 |
| Envolvente alcista | 4 h | largo | 405/321 | -0,09 · 46/50 | -0,23 · 22/1 | -0,28 · 78/2 |
| Envolvente bajista | 15 m | corto | 7448/5270 | -0,10 · 9/51 | -0,10 · 38/85 | -0,17 · 87/69 |
| Envolvente bajista | 1 h | corto | 1858/1365 | -0,09 · 4/86 | -0,10 · 37/73 | -0,15 · 61/72 |
| Envolvente bajista | 4 h | corto | 486/359 | -0,09 · 32/71 | -0,11 · 5/55 | -0,33 · 61/12 |
| Harami alcista | 15 m | largo | 3631/2638 | -0,10 · 91/30 | -0,07 · 80/81 | -0,02 · 20/42 |
| Harami alcista | 1 h | largo | 902/654 | -0,11 · 55/29 | -0,07 · 53/69 | +0,06 · 100/78 |
| Harami alcista | 4 h | largo | 233/172 | -0,06 · 59/83 | -0,11 · 39/40 | +0,10 · 48/74 |
| Harami bajista | 15 m | corto | 3770/2858 | -0,11 · 68/14 | -0,13 · 69/30 | -0,24 · 62/14 |
| Harami bajista | 1 h | corto | 1019/702 | -0,12 · 91/15 | -0,11 · 95/61 | -0,26 · 70/23 |
| Harami bajista | 4 h | corto | 256/152 | -0,05 · 33/94 | -0,07 · 22/70 | -0,21 · 79/43 |
| Peonza | 15 m | indecisión | 17298/10729 | mov. +0,32 vs +0,32 · pct mov. 62/75 | mov. +0,67 vs +0,65 · pct mov. 97/99 | mov. +1,75 vs +1,72 · pct mov. 100/97 |
| Peonza | 1 h | indecisión | 5098/3145 | mov. +0,31 vs +0,32 · pct mov. 2/0 | mov. +0,63 vs +0,65 · pct mov. 20/3 | mov. +1,70 vs +1,72 · pct mov. 55/29 |
| Peonza | 4 h | indecisión | 1386/873 | mov. +0,30 vs +0,31 · pct mov. 0/19 | mov. +0,61 vs +0,66 · pct mov. 0/2 | mov. +1,62 vs +1,71 · pct mov. 2/4 |
| Doji de piernas largas | 15 m | indecisión | 1526/1051 | mov. +0,37 vs +0,32 · pct mov. 100/100 | mov. +0,68 vs +0,65 · pct mov. 100/92 | mov. +1,78 vs +1,72 · pct mov. 99/91 |
| Doji de piernas largas | 1 h | indecisión | 416/286 | mov. +0,42 vs +0,32 · pct mov. 100/100 | mov. +0,75 vs +0,65 · pct mov. 91/98 | mov. +1,84 vs +1,72 · pct mov. 67/88 |
| Doji de piernas largas | 4 h | indecisión | 129/99 | mov. +0,39 vs +0,31 · pct mov. 17/98 | mov. +0,76 vs +0,66 · pct mov. 81/91 | mov. +1,76 vs +1,71 · pct mov. 21/63 |
| Doji de cuatro precios | 15 m | indecisión | 26/22 | mov. +0,08 vs +0,32 · pct mov. 0/0 | mov. +0,19 vs +0,65 · pct mov. 0/0 | mov. +1,40 vs +1,72 · pct mov. 0/19 |
| Doji de cuatro precios | 1 h | indecisión | 1/1 | mov. +0,29 vs +0,32 · pct mov. 33/63 | mov. +0,54 vs +0,65 · pct mov. 80/58 | mov. +3,97 vs +1,72 · pct mov. 40/90 |
| Doji de cuatro precios | 4 h | indecisión | 0/0 | mov. — vs +0,31 · pct mov. —/— | mov. — vs +0,66 · pct mov. —/— | mov. — vs +1,71 · pct mov. —/— |
| Doji lápida | 15 m | corto | 513/323 | -0,10 · 90/62 | -0,09 · 93/67 | -0,32 · 98/16 |
| Doji lápida | 1 h | corto | 74/68 | -0,20 · 33/6 | -0,09 · 53/59 | -0,39 · 76/24 |
| Doji lápida | 4 h | corto | 16/15 | +0,03 · 78/87 | +0,57 · 58/99 | -0,42 · 63/35 |
| Doji libélula | 15 m | largo | 515/316 | -0,13 · 62/13 | -0,17 · 46/5 | +0,12 · 8/82 |
| Doji libélula | 1 h | largo | 99/79 | -0,19 · 15/5 | -0,19 · 4/17 | +0,01 · 7/54 |
| Doji libélula | 4 h | largo | 15/19 | -0,10 · 4/47 | -0,34 · 16/13 | -1,15 · 16/2 |
| Pinzas arriba | 15 m | corto | 4063/2966 | -0,11 · 8/29 | -0,11 · 96/55 | -0,19 · 98/48 |
| Pinzas arriba | 1 h | corto | 956/705 | -0,10 · 8/49 | -0,08 · 4/87 | -0,18 · 27/52 |
| Pinzas arriba | 4 h | corto | 218/171 | -0,04 · 31/96 | -0,03 · 9/87 | -0,14 · 28/58 |
| Pinzas abajo | 15 m | largo | 3504/2692 | -0,09 · 60/55 | -0,07 · 72/81 | -0,01 · 48/52 |
| Pinzas abajo | 1 h | largo | 786/592 | -0,06 · 74/94 | -0,05 · 42/83 | +0,00 · 32/55 |
| Pinzas abajo | 4 h | largo | 185/133 | -0,09 · 79/61 | -0,17 · 35/15 | -0,13 · 92/30 |
| Tres soldados blancos | 15 m | largo | 469/463 | -0,11 · 98/27 | -0,09 · 99/41 | +0,03 · 30/65 |
| Tres soldados blancos | 1 h | largo | 85/75 | -0,20 · 73/4 | -0,29 · 99/4 | +0,35 · 89/92 |
| Tres soldados blancos | 4 h | largo | 20/22 | -0,28 · 11/5 | -0,50 · 5/2 | -0,88 · 73/5 |
| Tres cuervos negros | 15 m | corto | 371/428 | -0,15 · 38/4 | -0,08 · 47/81 | -0,13 · 51/68 |
| Tres cuervos negros | 1 h | corto | 65/77 | -0,07 · 57/74 | -0,03 · 31/80 | +0,02 · 49/77 |
| Tres cuervos negros | 4 h | corto | 11/15 | -0,31 · 19/5 | -0,36 · 18/15 | -0,91 · 94/12 |
| Estrella de la mañana | 15 m | largo | 973/686 | -0,08 · 28/80 | -0,00 · 13/98 | +0,10 · 4/88 |
| Estrella de la mañana | 1 h | largo | 209/173 | -0,12 · 77/26 | -0,12 · 95/32 | +0,03 · 99/60 |
| Estrella de la mañana | 4 h | largo | 49/32 | -0,08 · 74/58 | -0,09 · 77/50 | +0,81 · 26/97 |
| Estrella de la tarde | 15 m | corto | 962/738 | -0,10 · 67/51 | -0,11 · 56/59 | -0,31 · 38/8 |
| Estrella de la tarde | 1 h | corto | 234/157 | -0,18 · 23/2 | -0,18 · 18/21 | -0,35 · 27/19 |
| Estrella de la tarde | 4 h | corto | 59/39 | -0,08 · 88/63 | -0,41 · 28/3 | -0,58 · 36/15 |
| Martillo | 15 m | largo | 2150/1412 | -0,12 · 1/7 | -0,07 · 0/75 | -0,02 · 2/46 |
| Martillo | 1 h | largo | 511/313 | -0,12 · 2/22 | -0,11 · 10/31 | -0,03 · 44/45 |
| Martillo | 4 h | largo | 100/71 | -0,03 · 81/88 | -0,29 · 21/5 | -0,60 · 19/2 |
| Martillo invertido | 15 m | largo | 1390/1090 | -0,07 · 71/95 | -0,02 · 96/98 | +0,07 · 31/86 |
| Martillo invertido | 1 h | largo | 267/203 | -0,07 · 88/73 | -0,15 · 99/16 | -0,15 · 70/22 |
| Martillo invertido | 4 h | largo | 48/31 | +0,08 · 68/98 | -0,00 · 58/70 | +0,11 · 75/62 |
| Hombre colgado | 15 m | corto | 1602/1206 | -0,10 · 92/55 | -0,09 · 98/80 | -0,12 · 47/84 |
| Hombre colgado | 1 h | corto | 356/262 | -0,09 · 97/65 | -0,08 · 80/72 | -0,08 · 11/75 |
| Hombre colgado | 4 h | corto | 82/57 | -0,03 · 7/89 | -0,12 · 17/49 | -0,11 · 23/58 |
| Estrella fugaz | 15 m | corto | 2090/1370 | -0,12 · 5/16 | -0,10 · 13/74 | -0,10 · 52/91 |
| Estrella fugaz | 1 h | corto | 394/272 | -0,15 · 15/5 | -0,18 · 64/12 | -0,32 · 92/18 |
| Estrella fugaz | 4 h | corto | 88/68 | -0,13 · 69/33 | -0,20 · 47/24 | -0,17 · 85/52 |

---

## Tarea 3: mejorar y consolidar (P05b, P11 y la MEZCLA)

**Método** (`consolidacion/t3_estrategias.py`):
- Gestión con velas de 1 minuto y una posición a la vez.
- Comisión: tomador 0,05 %/lado y creador 0,02 %; el doble, 0,10 % y 0,04 %.
- **Azar:** las mismas operaciones (lado y duración) en momentos sorteados, 500 veces.
- **Vetos de velas:** no operar si en las últimas *n* velas cerradas del marco hay un patrón de lado contrario. Seis variantes: 15 m, 1 h o 4 h, con 1 o 3 velas. El veto se elige en el ajuste y después se mira la prueba.

| Estrategia | Ajuste 2020-23: ops · neto · doble · pct | Prueba 2024-26: ops · neto · doble · pct | Total: ops · neto · doble · caída |
|---|---|---|---|
| **MEZCLA reglas** (junio, sin clasificador) | 1.004 · −148,2 % · −248,6 % · 22 | 606 · +41,2 % · −19,4 % · 90 | 1.610 · −107,1 % · −268,1 % · 195 pts |
| MEZCLA solo largo | 664 · −16,8 % · −83,2 % · 36 | 403 · +32,6 % · −7,8 % · 62 | 1.067 · +15,8 % · −90,9 % |
| MEZCLA solo corto | 544 · −129,2 % · −183,6 % · 38 | 375 · −44,6 % · −82,1 % · 75 | 919 · −173,8 % |
| MEZCLA + veto 1 h (3 velas), el mejor veto en el ajuste | 918 · −75,4 % · −167,2 % · 50 | 560 · +65,9 % · +9,9 % · 96 | 1.478 · −9,5 % · −157,3 % |
| MEZCLA solo largo + veto 1 h (3 velas) | 573 · +0,9 % · −56,4 % · 46 | 352 · +52,3 % · +17,1 % · 74 | 925 · +53,2 % · −39,3 % |
| **P05b k = 0,5** (base) | 561 · +44,7 % · +5,4 % · 98 | 459 · +19,9 % · −12,2 % · 95 | 1.020 · +64,6 % · −6,8 % · 49 pts |
| **P05b solo largo** | 280 · +52,0 % · +32,4 % · 98 | 216 · +21,6 % · +6,5 % · 84 | 496 · +73,6 % · **+38,9 %** · 44 pts |
| P05b solo corto | 281 · −7,4 % · −27,0 % · 88 | 243 · −1,7 % · −18,7 % · 89 | 524 · −9,0 % · −45,7 % |
| **P05b + veto 1 h (3 velas)**, el mejor veto en el ajuste | 382 · +59,9 % · +33,2 % · 99 | 307 · +27,9 % · +6,5 % · 96 | 689 · +87,8 % · **+39,6 %** · 33 pts |
| P05b + veto 15 m (3 velas) | 385 · −12,0 % · −39,0 % · 77 | 314 · +6,4 % · −15,6 % · 86 | 699 · −5,7 % (el veto **empeora**) |
| P05b + veto 4 h (3 velas) | 403 · +21,2 % · −7,0 % · 94 | 319 · +3,6 % · −18,7 % · 84 | 722 · +24,8 % (empeora) |
| P05c k = 1,0 | 179 · +26,9 % · +14,3 % · 97 | 166 · +16,4 % · +4,8 % · 92 | 345 · +43,2 % · +19,1 % · 49 pts |
| **P11 lunes, stop 3 %** (base) | 206 · +55,9 % · +35,3 % · 88 | 147 · +48,7 % · +34,0 % · 86 | 353 · +104,6 % · **+69,3 %** · 36 pts |
| P11 sin stop | 206 · +53,8 % · +33,2 % · 80 | 147 · +60,5 % · +45,8 % · 92 | 353 · +114,3 % · +79,0 % · 47 pts |
| P11 stop 2 % / 5 % | +25,4 % / +50,3 % | +47,0 % / +42,0 % | +72,4 % / +92,3 % |
| P11 lunes + miércoles | 412 · +90,6 % · +49,4 % · 91 | 294 · +81,1 % · +51,7 % · 90 | 706 · +171,7 % · +101,1 % |
| P11 + veto 4 h (3 velas) | 135 · +34,1 % | 90 · −8,4 % · pct 31 | el veto **empeora** |

Qué quiere decir:
- **La MEZCLA se descarta tal como está.** Sin el clasificador, sus reglas pierden en el ajuste (percentil 22) y en total. Los cortos en el techo, que en junio eran «el edge más fuerte», pierden en los dos tramos. El +248 % de junio venía del clasificador (que aquí no pude replicar: no hay scikit-learn y no instalo nada) o del cálculo de entonces. Con el veto de 1 h mejora, pero sigue en −9,5 % y −157 % con el doble.
- **P05b mejora de dos formas, y las dos resisten el doble de comisión.** Quitar los cortos da +38,9 % con el doble. Con el veto de 1 h y 3 velas, +39,6 %: se eligió en el ajuste y se confirmó en la prueba (+27,9 % frente a +19,9 % de la base). Las dos son positivas con el doble en el ajuste y en la prueba. **Pero la elección del veto salió de 6 variantes: es una prueba múltiple, y las otras empeoran.** Por eso queda «en prueba», no «sigue».
- **P11 es la más robusta:** positiva con el doble en los dos tramos, con cualquier stop entre el 2 y el 5 %. El stop del 3 % se queda: sin stop gana un poco más, pero sin protección ante un desplome. Añadir el miércoles parece sumar (+81 % en la prueba), pero salió de mirar los 7 días: es una hipótesis, no una regla.
- **Los vetos de velas no son universales.** El de 1 h con 3 velas ayudó a P05b y a la MEZCLA en los dos tramos. El de 15 m y el de 4 h con 3 velas empeoraron a P05b y a P11. Se usa solo donde se midió.

**Lista final de estrategias**

| Estrategia | Estado | Cifras que lo deciden |
|---|---|---|
| **P11, largo del lunes UTC, stop 3 %** | **Sigue** (candidata principal, en papel) | 353 ops, +104,6 % neto, +69,3 % doble, positiva en los dos tramos, percentil 95 |
| P05b + veto de velas de 1 h (3 velas) | En prueba (mejor versión de P05b) | 689 ops, +87,8 %, doble +39,6 %, percentil 99 / 96. Riesgo: veto elegido entre 6 |
| P05b solo largo | En prueba | 496 ops, +73,6 %, doble +38,9 % |
| P05b k = 0,5 con los dos lados | En prueba, frágil (la reemplazan las dos de arriba) | 1.020 ops, +64,6 %, doble −6,8 % |
| P05c k = 1,0 | En prueba | 345 ops, +43,2 %, doble +19,1 % (muestra justa) |
| P11 + miércoles | Hipótesis (prueba múltiple) | 706 ops, +171,7 %; sin confirmar con otra muestra |
| MEZCLA reglas, en todas sus variantes | **Descartada** | 1.610 ops, −107,1 % neto, −268 % doble; ajuste percentil 22 |
| MEZCLA con clasificador (E01 completa) | Sin verificar | Sin réplica posible aquí |
| Patrones de vela como entrada | **Descartados** | 0 de 144 combinaciones con ventaja neta en los dos tramos |
| Patrones de vela como veto general | **Descartados** | Empeoran a P05b (15 m y 4 h) y a P11 (4 h); solo el de 1 h con 3 velas ayudó |

---

## Tarea 4: estrategias nuevas para presupuesto bajo y plan de riesgo

### La restricción que manda

Con 12,59 USDT:
- **Futuros BTCUSDT:** la orden mínima es 0,001 BTC, unos 80 USDT (6,4 veces el saldo; dato que la rutina leyó en binance.com el 25/10). Con el stop del 3 % de P11, esa orden arriesga **2,4 USDT, el 19 % de la cuenta**. Con el stop típico de P05b (≈1,3 %), el 8 %. Para arriesgar el 1,5 % harían falta stops de 0,24 %, y ninguna ventaja medida funciona así.
- **Conclusión:** con 40.000 pesos, en futuros **no se puede cumplir el plan de riesgo**. CL-007 («nocional de 0,5 veces el saldo») no se podría ejecutar en real.
- **La salida es el contado BTCUSDT:** nocional mínimo de 5 USDT, sin apalancamiento, solo largos. Comisión VIP0 del 0,10 % por lado, de creador y de tomador (el doble: 0,20 %).
- Uso las velas de futuros como aproximación del contado: la diferencia entre los dos precios es de centésimas de punto.

### Las estrategias nuevas

`consolidacion/t4_presupuesto.py`. Todas son de pocas operaciones.

| Estrategia | Idea | Ajuste 2020-23: ops · neto · doble | Prueba 2024-26: ops · neto · doble | Total: ops/semana · neto · doble · pct | Estado |
|---|---|---|---|---|---|
| **N1: P11 en contado** | Largo del lunes UTC, stop 3 %, tomador | 206 · +35,3 % · −6,0 % | 147 · +34,0 % · +4,6 % | 1,0 · +69,3 % · −1,3 % · 95 | **Sigue** |
| N2: P05b solo largo en contado | Límite en la banda alta | 280 · +15,6 % · −40,4 % | 216 · −6,5 % · −49,7 % | 1,4 · +9,1 % · −90,1 % | Descartada (en contado) |
| N2v: N2 + veto 1 h | Igual, con el veto de la tarea 3 | 185 · +13,1 % · −23,9 % | 146 · +8,9 % · −20,3 % | 0,9 · +22,0 % · −44,2 % | En prueba, frágil |
| **N2c: P05c (k = 1) solo largo, en contado** | Límite en apertura + 1·ATR | 91 · +22,0 % · +3,8 % | 79 · +22,8 % · +7,0 % | 0,5 · +44,8 % · **+10,8 %** · 100 | **En prueba** (170 ops: muestra débil) |
| N3: retroceso de creador en tendencia diaria (curso) | Cierre sobre la SMA 50 diaria y subiendo: límite en apertura − x·ATR, stop 1·ATR. Rejilla de 4, elegida en el ajuste | (mejor: x = 0,5, 2 días) 211 · +107,0 % · +64,8 % | 169 · −38,5 % · −72,3 % | 1,1 · +68,5 % · −7,5 % | **Descartada**: lo elegido en el ajuste pierde en la prueba |

Con la comisión del contado (0,20 % ida y vuelta), solo sobreviven las estrategias que ganan mucho por operación: P11 (+0,40 % bruto de media) y P05c en largo (+0,46 %). P05b en largo da +0,22 % y la comisión se lo come. N3 es el ejemplo de manual de un sobreajuste.

### ¿Son sostenibles tres operaciones al día? No. Las cifras:

- **Comisión de tres operaciones al día:** en contado, 0,60 % del nocional cada día; en futuros, 0,30 %. Para no perder, cada operación tendría que ganar en bruto más de 0,20 % (contado) o 0,10 % (futuros).
- **Las que llegan a esa frecuencia no ganan eso:**
  - MEZCLA: 0,65 operaciones al día, con +0,034 % bruto por operación.
  - P10 (horquilla en compresión): +0,04 % bruto.
  - Los ciclos a minutos del PC: de 0,05 a 0,14 % de movimiento frente a 0,04-0,20 % de comisión.
  - Todas pierden neto.
- **Las que sí ganan son poco frecuentes:** P11 una vez por semana, P05b-L con veto 0,9 por semana y P05c-L 0,5 por semana.
- **Frecuencia sostenible: de 1 a 2,5 operaciones por semana.** Esa es la propuesta. Más operaciones solo suman comisión.

### Plan de riesgo diario para no perder los 40.000

| Regla | Valor | Por qué |
|---|---|---|
| Mercado | Contado BTCUSDT, solo largos, sin apalancamiento | El peor caso de cada operación es el nocional, nunca más; en futuros el mínimo obliga a arriesgar del 8 al 19 % |
| Riesgo por operación | **1,5 % = 600 pesos** | Nocional = 600 pesos ÷ distancia al stop, con tope en el saldo. Si sale menos de 5 USDT (≈15.900 pesos), no se opera |
| Posiciones a la vez | 1 | Las ventajas están correlacionadas (todas son BTC) |
| Entradas por día | Máximo 2 | Las ventajas medidas no dan más |
| Pérdida diaria máxima | **3 % = 1.200 pesos** → se para el día | Dos stops seguidos |
| Pérdida semanal máxima | **6 % = 2.400 pesos** → se para la semana | Cuatro stops |
| Parada total | **Caída del 10 % desde el máximo (4.000 pesos)** → se vuelve a papel y a revisión | En la simulación de abajo, el peor saldo de N1 fue 38.032 pesos (−4,9 %): el 10 % deja margen sin dejar que una racha destruya la cuenta |
| Deslizamiento | Contar con que un stop se pase | Peor minuto de la historia: −9,3 % (13/03/2020); 337 minutos con caídas de más del 2 %. Con nocional de 6,3 USDT, un desplome así cuesta 0,6 USDT (1.900 pesos), no la cuenta |
| Eventos | Sin aperturas de 17:00 a 21:00 UTC el día de la Reserva Federal; medio riesgo el día anterior | Regla R4 de la rutina |

Simulación de la cuenta con este plan (velas reales, comisión de contado):

| Estrategia | Tramo | Ops | Saldo final | Peor saldo | Con el doble de comisión |
|---|---|---|---|---|---|
| N1 (P11 en contado) | 2020-2023 | 206 | 45.988 pesos (+15,0 %) | 38.032 | 37.427 (−6,4 %) |
| N1 (P11 en contado) | 2024-2026 | 147 | 46.784 pesos (+17,0 %) | 40.000 | 40.391 (+1,0 %) |
| N2c (P05c largo en contado) | 2024-2026 | 79 | 46.547 pesos (+16,4 %) | 39.467 | 41.781 (+4,5 %) |
| N2c | 2020-2023 | 0 | — | — | No hubo ninguna: con el ATR de esos años, el stop de 1·ATR (≈4-5 %) deja el nocional bajo el mínimo de 5 USDT a riesgo del 1,5 % |

**En pesos, la verdad es esta:** con el plan que protege el capital, la ganancia esperada de P11 es de unos **1.500 a 2.400 pesos al año** (+3,6 % anual en 2020-2023 y +6 % en 2024-2026). El peor saldo medido no bajó de 38.000. Proteger los 40.000 es posible. Ganar mucho con 40.000, no: el capital es el límite, no la estrategia.

---

## Tarea 5: la semana del lunes 19 al viernes 23 de octubre de 2026

`consolidacion/t5_semana.py`, con salida en `consolidacion/t5_semana.txt`. Velas de 1 minuto, entradas de esa semana y la posición real de cada estrategia.

**BTC esa semana (futuros):** lunes −0,21 % (rango 1,8 %), martes +1,32 % (2,8 %), miércoles +1,28 % (2,8 %), jueves **−3,17 %** (4,3 %), viernes −0,28 % (2,0 %).

| Estrategia | Ops | Aciertos | Fallos | Lun 19 | Mar 20 | Mié 21 | Jue 22 | Vie 23 | Neto semana | Con el doble |
|---|---|---|---|---|---|---|---|---|---|---|
| P11 (futuros) | 1 | 0 | 1 | −0,31 | · | · | · | · | −0,31 % | −0,41 % |
| P05b k = 0,5 | 2 | 1 | 1 | · | −0,02 | · | **+1,88** (corto) | · | +1,86 % | +1,72 % |
| P05b solo largo | 1 | 0 | 1 | · | −0,02 | · | · | · | −0,02 % | −0,09 % |
| P05b + veto 1 h | 2 | 1 | 1 | · | −0,02 | · | +1,88 | · | +1,86 % | +1,72 % |
| P05c k = 1,0 | 0 | — | — | · | · | · | · | · | 0 | 0 |
| MEZCLA reglas (descartada) | 3 | 3 | 0 | +0,68 | +1,36 | +2,01 | · | · | +4,06 % | +3,76 % |
| MEZCLA + veto 1 h (descartada) | 3 | 3 | 0 | +1,01 | +1,13 | +2,01 | · | · | +4,15 % | +3,85 % |
| N1: P11 en contado | 1 | 0 | 1 | −0,41 | · | · | · | · | −0,41 % | −0,61 % |
| N2v: P05b largo + veto (contado) | 1 | 0 | 1 | · | −0,15 | · | · | · | −0,15 % | −0,35 % |
| N2c: P05c largo (contado) | 0 | — | — | · | · | · | · | · | 0 | 0 |
| N3 (descartada) | 1 | 0 | 1 | · | · | · | −2,72 (stop) | · | −2,72 % | −2,92 % |
| Azar: 5 operaciones de 6 h al azar (2.000 sorteos) | 5 | — | — | | | | | | mediana −0,47 % (p5 −3,43; p95 +2,32) | |

Aciertos de la semana, con las estrategias vigentes (P11, P05b con sus variantes, P05c, N1, N2v y N2c): **1 de 6 operaciones**. Esa una fue la que más rindió: el corto de P05b del jueves, cuando BTC cayó 3,2 %. La MEZCLA acertó 3 de 3, pero en la historia larga pierde: una semana con 3 operaciones no cambia 1.610.

**Lectura:** fue una semana de tendencia alcista y luego una caída fuerte. P11 perdió un lunes plano, cosa que pasa en el 53 % de los lunes. La muestra semanal es diminuta (de 0 a 3 operaciones por estrategia) y no dice nada sobre si la ventaja existe. Lo dicen las 353 y las 689 operaciones de la tarea 3.

---

## Tarea 6: prueba propia (lunes 26 y martes 27/10)

Las órdenes quedaron escritas en `ORDENES-PRUEBA-PROPIA.md` el **25/10 a las 16:20 UTC**, antes del resultado, con entrada, stop, salida, tamaño y razón:
- **Lunes:** PP-1 (P11 / N1), PP-2 (P05b con veto 1 h), PP-3 (P05c largo) y el testigo AZ-P1 (corto a las 15:41 UTC, sorteado).
- **Martes:** PP-4, PP-5 y AZ-P2 (largo a las 11:15 UTC), a medio riesgo por la Reserva Federal.

Se cierran con `python3 -I consolidacion/t6_ordenes.py cerrar 2026-10-26` (y `2026-10-27`), que usa velas de 1 minuto de Coinbase. Validé el script con días ya conocidos:
- **Lunes 19/10:** P11 da −0,206 % bruto en Coinbase (en Binance, −0,21 %).
- **Martes 20/10:** P05b da el mismo largo que en Binance.

**Resultado:** pendiente. Al escribir esto es domingo 16:20 UTC. Si la sesión no sigue viva el martes, la rutina puede cerrarlas en su pasada siguiente con el mismo script (ver la tarea 7).

---

## Tarea 7: CAMBIOS PROPUESTOS AL PROMPT

No edité `PROMPT-AGENTE-TRADING-NUBE.md`: lo decide Nicolás. Estos son los cambios concretos, con su razón medida.

1. **«EL EXPEDIENTE», punto 1 (MEZCLA).** Cambiar «Es la única estrategia con ventaja medida» por: «Revalidada el 25/10 con velas de 1 minuto de futuros 2020-2026 y 0,05 %/lado: sus reglas pierden (1.610 ops, −107 % neto; ajuste percentil 22). Descartada sin el clasificador. El clasificador queda sin verificar».
2. **Añadir al EXPEDIENTE un punto 8, «Velas del curso (25/10)»:** «En 15 m, 1 h y 4 h, a 1, 4 y 24 horas, ningún patrón gana neto y supera el p95 en el ajuste y en la prueba (0 de 144). No se usan como entrada. Como veto, solo el de 1 h (patrón contrario en las 3 últimas velas cerradas) mejoró a P05b y a la MEZCLA; los de 15 m y 4 h empeoran. El doji de piernas largas anticipa más movimiento y la peonza menos: es dato de volatilidad, no de dirección».
3. **Libro CLAUDE, plan de riesgo.** Sustituir «3 % por operación, 15 % abierto a la vez, pérdida diaria máxima del 15 % y semanal del 20 %» por el plan de la tarea 4: 1,5 % (600 pesos) por operación, una posición, máximo 2 entradas por día, −3 % al día, −6 % a la semana y parada total con −10 % desde el máximo. Añadir: «Con 40.000 pesos, en futuros la orden mínima (0,001 BTC) arriesga del 8 al 19 % de la cuenta: el tamaño en pesos se calcula como contado, solo largos. Los cortos se registran en porcentaje, sin tamaño en pesos».
4. **«LO QUE QUIERE NICOLÁS» y libro CLAUDE, la meta de 3 al día.** Cambiar «Al menos 3 operaciones al día es la meta» por: «La meta de 3 al día no es sostenible con lo medido (las ventajas dan de 1 a 2,5 operaciones por semana; con 3 al día la comisión cuesta 0,3-0,6 % diario). Opera solo cuando haya ventaja medida y no fuerces la cuenta diaria». Nicolás debería confirmar este cambio, porque toca su meta.
5. **Candidatas en el libro CLAUDE.** Reemplazar «P05b se toma entera» (R14) por: «P05b se toma con el veto de 1 h de la consolidación del 25/10 o solo en largo; los cortos de P05b sin veto pierden en los dos tramos (−9 %)». P11 sigue como está (R15). Añadir P05c-L (k = 1, solo largo) como candidata de contado.
6. **Cierre de la prueba propia.** Añadir a «QUÉ ENTREGA CADA PASADA», punto 2: «Si existen `ORDENES-PRUEBA-PROPIA.md` y `consolidacion/t6_ordenes.py` en el repositorio trader-btc, cierra las órdenes PP-* y AZ-P* del día vencido con el script y anota el resultado». Solo aplica si la rutina tiene el repositorio. Si no, copiar las reglas de PP-1 a PP-5 a sus órdenes condicionadas.
7. **«CÓMO PROBAR».** Añadir: «Cuando pruebes rejillas, filtros o vetos, elige en el ajuste y mira la prueba una sola vez; di cuántas variantes probaste. N3 (retroceso del curso) ganaba +107 % en el ajuste y perdía −38 % en la prueba».
8. **Temas.** Marcar como hechos el 10 (réplica de la MEZCLA sin clasificador) y la parte de capital mínimo del 14. Añadir un tema 15: «Comisiones de contado de creador por par (BTCUSDT, BTC/USDC, BTC/FDUSD) leídas en binance.com con fecha. Es lo que más cambia el resultado en contado: N2 pasa de perder a ganar si la comisión de creador baja de 0,10 %».
9. **Lectura antes de operar (pedido de Nicolás).** Añadir al libro CLAUDE: «Antes de cada decisión, lee y comprueba las velas que la regla necesita, completas y sin huecos: 15 diarias para el ATR14, 50 diarias para la SMA 50, 60 de 1 h cerradas para los patrones y las de 15 m y 1 min del día. Escribe en el diario cuántas leíste. Si falta alguna, no operes». `consolidacion/t6_ordenes.py` ya lo hace así.

---

## Tarea 8 (pedido de Nicolás, 25/10): operar solo cuando las velas y el mercado confirman

**Pedido:** quedarse solo con lo que acierta, descartar lo que no da y operar únicamente cuando las velas están como dice la estrategia y el mercado se mueve a su favor.

**Bases:** las que sobrevivieron a la tarea 3. P11, P05b solo largo, P05b con veto de 1 h y P05c solo largo.

**Diez filtros de confirmación**, medidos en el instante de la señal con velas ya cerradas:
- patrón de vela a favor en las últimas 1 o 3 velas de 15 m o de 1 h;
- impulso a favor en 1, 4 o 24 h;
- vela de fuerza (cuerpo ≥ 50 % del rango y cierre en el extremo);
- volumen mayor que 1,5 veces la media;
- tendencia diaria a favor (cierre sobre la SMA 50).

Son 60 combinaciones. Código en `consolidacion/t8_confirmacion.py`, `t8b_valor_filtro.py` y `t8c_cartera.py`.

**Lo que no funcionó, dicho primero.** La regla fijada antes de mirar era elegir el filtro en 2020-2023 (el de mejor neto con el doble por operación) y comprobarlo en 2024-2026. **Falló:**
- Para P05b eligió la «vela de fuerza», que en la prueba empeoró: +11,6 % frente a +21,6 % sin filtro, y −2,7 % frente a +27,9 % en la versión con veto.
- Para P11 eligió el impulso de 1 h, que en la prueba bajó a la mitad: +25,0 % frente a +48,7 %.
- El impulso de 1 a 4 h no filtra nada en P05b: la señal ya es un rompimiento al alza.

**Lo que sí funcionó.** Dos filtros mejoran en los dos tramos y tienen la lógica del curso: patrón de vela que confirma, y operar a favor de la tendencia mayor. Para saber si el filtro aporta o solo hereda la ventaja de la estrategia, comparé las operaciones filtradas con 5.000 subconjuntos al azar del mismo tamaño sacados de la misma estrategia:

| Estrategia + confirmación | Ajuste 2020-23: ops · media neta · pct frente a subconjuntos | Prueba 2024-26: ops · media neta · pct | Prueba: neto y doble |
|---|---|---|---|
| **P05b largo + patrón alcista en las 3 últimas velas de 1 h** (futuros) | 54 de 280 · +0,567 % (base +0,186 %) · 88 | 57 de 216 · **+0,810 %** (base +0,100 %) · **99,9** | +46,2 % · doble +42,2 % |
| La misma, en contado (0,10 %/lado) | 54 · +0,437 % (base +0,056 %) · 88 | 57 · +0,680 % (base −0,030 %) · 100 | +38,8 % · doble +27,4 % |
| **P11 + cierre diario sobre la SMA 50** (futuros) | 103 de 206 · +0,417 % (base +0,271 %) · 71 | 83 de 147 · +0,612 % (base +0,331 %) · 92 | +50,8 % · doble +42,5 % (sin filtro: +48,7 % con el doble de operaciones) |
| P05b + veto 1 h + patrón alcista 1 h | 69 · +0,338 % · 70 | 87 · +0,366 % · 93 | +31,8 % · doble +25,7 % |

**Cuenta de 40.000 pesos en contado** con las tres juntas: P11 con tendencia, P05b largo confirmado y P05c largo. Una posición a la vez, riesgo del 1,5 %, topes de −3 % al día y −6 % a la semana. El tamaño sale de la distancia al stop conocida al entrar.

| Tramo | Operaciones | Aciertos | Saldo final | Por año | Peor saldo | Con el doble de comisión |
|---|---|---|---|---|---|---|
| 2020-2023 | 195 (0,95 por semana) | 47 % | 58.931 pesos (+47,3 %) | +10,4 % | 36.884 | 47.095 (+4,2 %/año) |
| 2024-2026 | 186 (1,28 por semana) | 47 % | 57.943 pesos (+44,9 %) | +14,1 % | 40.000 | 46.493 (+5,5 %/año) |

**Cuánto creerle.**
- El filtro de la vela alcista de 1 h se miró después de ver los dos tramos y salió de 60 combinaciones. Su percentil en el ajuste (88) no llega a 95.
- Son 111 operaciones en 6,8 años (unas 0,3 por semana): **muestra débil**.
- Queda **en prueba**, no como regla. Lo honesto es esperar menos de lo que dice la tabla: entre el resultado con el doble de comisión (+4 a +5 % al año) y el base (+10 a +14 %).
- La primera prueba real es PP-6 (lunes 26 y martes 27).
- Una corrección en el camino: la primera versión de la cartera daba +22 % al año porque calculaba el tamaño con la pérdida real, que no se conoce al entrar. Lo arreglé antes de dar cifras.

**Año por año** (`consolidacion/t8d_por_anio.py`; neto en futuros, suma de % por año):

| Año | P05b largo: base | P05b largo + vela alcista 1 h (ops) | P11: base | P11 + tendencia diaria (ops) |
|---|---|---|---|---|
| 2020 | +44,4 | +21,1 (19) | +45,0 | +22,5 (28) |
| 2021 | +24,1 | +13,2 (15) | +13,0 | +22,9 (32) |
| 2022 | −29,0 | −11,7 (12) | −8,9 | −7,1 (10) |
| 2023 | +12,5 | +8,1 (8) | +6,8 | +4,7 (33) |
| 2024 | +21,1 | +29,6 (19) | +53,1 | +41,2 (33) |
| 2025 | −0,1 | +7,3 (17) | −19,7 | −1,3 (25) |
| 2026 | +0,6 | +9,2 (21) | +15,3 | +10,9 (25) |

Las dos versiones confirmadas ganan en 6 de 7 años (P05b) y en 5 de 7 (P11). En los años malos (2022 y 2025) pierden mucho menos que la base: la confirmación protege más de lo que suma. 2022, el año bajista, sigue en negativo en las dos.

**Lista final actualizada («operar solo cuando debe»)**

| Estrategia | Cuándo opera | Estado |
|---|---|---|
| P11 | Lunes 00:00 UTC, solo si el cierre diario de ayer está sobre la SMA 50 | Sigue (la versión sin filtro también es válida) |
| P05b largo confirmado | Rompimiento de apertura + 0,5·ATR **y** patrón alcista en las 3 últimas velas de 1 h | En prueba (muestra débil, muy buena en 2024-26) |
| P05c largo | Rompimiento de apertura + 1·ATR | En prueba |
| Vela de fuerza, impulso de 1-24 h y volumen como confirmación | — | Descartados: no mejoran en la prueba |

**Operar yo directamente con un MCP de pantalla.** Desde esta sesión no se puede, y aunque se pudiera no lo haría sin tu sí explícito:
- Esta sesión corre en un servidor de Anthropic, no en tu PC. No ve tu pantalla ni tiene un conector de control de escritorio hacia tu equipo.
- Para que Claude use tu pantalla haría falta abrir una sesión en tu PC (Claude Code o la app de escritorio con control del equipo).
- Tus propias reglas dicen «dinero real solo cuando el papel gane de verdad y tú lo apruebes», y el papel en vivo todavía tiene 0 operaciones cerradas.
- Lo que sí puedo hacer aquí es lo de arriba: decidir yo cada orden de papel con estas reglas y cerrarla con velas reales.

## Comisiones de contado verificadas (25/10, binance.com/en/fee/trading)

- Usuario normal (VIP 0), contado: **0,100 % creador / 0,100 % tomador**; **0,075 % / 0,075 % pagando con BNB** (descuento del 25 %, vigente «hasta nuevo aviso» según el anuncio de Binance de 2022, actualizado en 2023).
- Pares en USDC: 0,095 % (0,07125 % con BNB). La tabla no deja claro si esa cifra es la de creador o la de tomador: por confirmar en la página.
- BTC/FDUSD: no aparece. No hay ninguna promoción de comisión cero para BTC en esas páginas.
- **Efecto:** con BNB, la ida y vuelta en contado baja de 0,20 % a 0,15 %. P11 en contado gana unos +0,05 puntos por operación. P05b largo confirmado (+0,81 % bruto de media en la prueba) sigue muy por encima de cualquiera de las dos comisiones. El plan sigue igual; conviene pagar las comisiones con BNB cuando haya dinero real.

## Pendientes y avisos

- **Dinero real: nada cambia.** Ninguna estrategia cumple el criterio de dinero real de la rutina: le faltan 60 operaciones de papel en vivo y 100 decisiones a ciegas.
- **Telegram:** enviado el 25/10 a las 16:30 UTC con el prefijo «[Trading cloud]», con `TELEGRAM_TOKEN` del entorno (el mismo `tg.py` de la rutina). El token no se imprimió ni se guardó.
- **Repositorio:** el código, los CSV y este informe están en commits de la rama `claude/encargo-cloud-md-q0u3ex`. Desde esta sesión GitHub dejó leer, pero no escribir (`git push` respondió 403). Por eso también se entrega `consolidacion-trader-btc.bundle`, para aplicarlo a mano. Las velas no se suben: se vuelven a bajar con `consolidacion/descargar_um.py`, que comprueba el SHA-256.
