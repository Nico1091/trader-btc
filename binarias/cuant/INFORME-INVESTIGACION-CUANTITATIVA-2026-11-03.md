# Investigación cuantitativa y diagnóstico técnico de las binarias

3 de noviembre de 2026 · BTCUSDT y ETHUSDT, Contratos de Evento de Binance, todo en papel · hora de Colombia.

Todo lo que se presenta como medido sale de un guion de `cuant/` cuya salida está en `cuant/resultados/`. Lo que es opinión o hipótesis se dice así.

## 1. Método fijado antes de ver resultados

- Objetivo de cada prueba: la binaria de 10 minutos (sube o baja), con una decisión cada 10 minutos para que los plazos no se encimen. El empate cuenta como fallo, que es lo más prudente: Binance devuelve lo apostado en empate.
- Tramos: se elige solo con 2021-2023; se juzga intacto en enero de 2024 a septiembre de 2026 («prueba») y en octubre de 2026 («adelante»), que nunca se miró al elegir. En el libro de órdenes el entrenamiento es solo 2023, porque Binance publica el libro desde entonces.
- Equilibrio: 1/(1 + pago). Con pago 0,85 hace falta 54,05 %; con 0,80, 55,6 %; con 0,90, 52,6 %.
- Pruebas múltiples: Benjamini-Hochberg con q = 0,05 sobre todas las celdas; límite de Wilson al 95 %; probabilidad de sobreajuste (PBO) por validación cruzada simétrica combinatoria con 16 bloques; comparación con el máximo que daría el azar.
- Datos: velas de 1 minuto de futuros de Binance de 2020 a 2026 con volumen de compra agresiva, profundidad del libro (bookDepth) de 2023 a 2026, opciones de Deribit, CBOE, Tesoro de EE. UU. y Banco Mundial.

## 2. Las seis dimensiones, una por una (BTC; ETH da lo mismo con diferencias de un punto)

Cifras: acierto en entrenamiento / prueba / adelante, con el sentido elegido en entrenamiento.

**1. Temporalidad.** Sesiones, fin de semana, killzones de ICT en hora de Nueva York y silver bullet: entre 48,9 y 50,6 %. La hora sola no dice hacia dónde va el precio.

**2. Dirección.** Cuando 1 h, 4 h y 1 día van en el mismo sentido, apostar al revés da 53,7 / 53,0 / 52,9 %. Tras una caída de 15 minutos mayor que una desviación, apostar SUBE da 55,7 / 54,1 / 53,4 % (ETH: 55,7 / 55,0 / 54,9 %). Es reversión de corto plazo, no seguimiento.

**3. Volatilidad, contracción, expansión y rupturas.** El hallazgo más fuerte de todo el estudio: cuando la vela de 5 minutos cierra por encima del máximo de las 20 anteriores, apostar BAJA da 59,4 / 56,1 / 61,7 %; cuando cierra por debajo del mínimo, apostar SUBE da 59,2 / 55,8 / 55,0 %. ETH: 57,4 / 56,0 / 61,4 % y 57,8 / 56,7 / 53,0 %. La volatilidad y el ancho de Bollinger solos quedan en 50 %.

**4. Liquidez y volumen.** El flujo de órdenes de 15 minutos al revés (compradores → BAJA) da 53,2 / 52,0 %. Los barridos de la hora previa, 50,7-51,1 % en la prueba. El volumen relativo solo, 50 %. El libro de órdenes (Bookmap: desequilibrio a ±1 %) da 52,1 % en la prueba, y aquí a favor del lado cargado del libro. A ±5 % y en su cambio de 10 minutos, 50,8-51,6 %.

**5. Estructura (SMC, ICT y CRT).** Tendencia por estructura al revés: 52,7 / 51,7 %. CHoCH al revés: 51,2-52,4 %. FVG, order blocks, AMD (barrido del rango de Asia), área de valor del día anterior (AMT), premium y discount, OTE, divergencia SMT con ETH y CRT en velas de 1 h y 4 h: entre 49,7 y 52 % en la prueba. Ninguno llega al equilibrio a 10 minutos.

**6. Estadística de resultados.** Rachas: en la cartera de celdas, tras acertar se acierta 51,8 % y tras fallar 53,9 %. En las apuestas a ciegas del banco, 57,5 % tras acertar y 58,6 % tras fallar (BTC, t18). No existe la «mano caliente»: la idea de apostar más «cuando hay suerte» no se sostiene a nivel de apuesta. Autocorrelación de 10 minutos negativa y decreciente (BTC de −0,043 a −0,026; ETH de −0,061 a −0,011): la reversión que da la ventaja se está gastando.

## 3. El cruce de las dimensiones

- 14.638 celdas de 2 y 3 variables con 300 o más apuestas en entrenamiento; 7.075 pasan Benjamini-Hochberg; 1.457 tienen además Wilson por encima del equilibrio (ETH: 1.209).
- Las mejores bajan de 65-68 % a 53-62 % fuera de muestra. 1.092 de las 1.457 siguen sobre el equilibrio en la prueba, pero juntas como cartera dan 52,8 % en BTC y 53,1 % en ETH: pierden con pago 0,85. Cruzar diluye la señal buena con muchas débiles.
- PBO de 0,1 % (BTC) y 2,7 % (ETH): el orden entre celdas se conserva (las buenas siguen arriba), aunque el nivel cae. No es lo mismo que rentabilidad.
- Cadena de Markov de orden 3: tras tres tramos de 10 minutos iguales, apostar al revés da 56,4 % en entrenamiento y 53,8 % en la prueba.
- HMM gaussiano de 3 regímenes (calma, normal, agitado): ningún régimen tiene sesgo de dirección; la reversión de 15 minutos funciona en los tres (53-56 %).
- Agrupamiento k-medias: los grupos que sirven son los de impulso extremo (54-55 % en la prueba): otra vez reversión.
- Anomalías (movimiento de 10 minutos con z robusto de 4 o 5): apostar en contra da 54-56 %.

## 4. La meta de 85,7 %

Ninguna celda la alcanza ni siquiera en entrenamiento: el máximo con 300 apuestas ronda 68 %. La mejor celda de la prueba, escogida mirando el resultado (con trampa), da 66,5 % en BTC y 68,9 % en ETH, y eso es lo que daría el puro azar entre 15.500 celdas de 100 apuestas (69,1 %). Con las dimensiones pedidas y en binarias de 10 minutos, 85,7 % no existe en los datos de 2021 a 2026. Las dos IA consultadas llegan a lo mismo. La meta honesta que se propone es 56-57 % fuera de muestra con el pago real, y no declarar nada sin el límite de Wilson por encima del equilibrio.

## 5. El semáforo papel → real (su idea del 03/11)

Probado en `c7_semaforo.py` con las apuestas a ciegas de BTC, entrando 60 s tarde (como él toca a mano), 5 USDT fijos y pago 0,85:
- Encender el modo real si el día anterior fue bueno (S3) no sirve: igual que elegir días al azar (p de 0,25 a 0,76).
- Encenderlo si las últimas 100 apuestas de papel van en 58 % o más (S2) sí suma: con las reglas de BTC, 57,7 % frente a 56,4 % de días al azar (p = 0,005); con la «ruptura al revés» y la parada en la primera pérdida, 59,8 % frente a 58,3 % (p = 0,003), unas 2,5 apuestas reales por día encendido. Con el modelo de BTC no suma.
- Parar en la primera pérdida no cambia lo esperado de cada apuesta; reduce cuántas se hacen. Su aparente mejora es en parte aritmética, por eso se comparó con el azar bajo la misma parada.
- Se hicieron 27 comparaciones: es una pista para confirmar con días nuevos, no una ley.
- Estado hoy: las últimas 100 apuestas de papel de la «ruptura al revés» en BTC van en 48 %. El semáforo está en ROJO.

## 6. Binarias frente a futuros (modelos distintos)

En binarias importa el acierto frente a 1/(1 + pago) y no hay apalancamiento ni liquidación: lo más que se pierde es lo apostado. En futuros importa el tamaño de lo ganado frente a lo perdido y los costos: con comisión de tomador de 0,05 % por lado, una salida simétrica de 0,3 % exige 66,7 % de acierto. El apalancamiento no crea ventaja; con 10x la liquidación queda a −9,6 % y con 100x a −0,6 %. Decisión de Nicolás: real sin apalancamiento; el apalancamiento, si se estudia, solo en papel (`c4_binarias_vs_futuros.py`).

## 7. Mercado en vivo (03/11, 20:32; `c3_contexto_vivo.py`)

BTC 76.882: −0,3 % en 1 h, −1,3 % en 4 h, −4,8 % en 7 días, −11,3 % en 30 días. Impulso de 15 minutos a la baja (z −1,63), flujo vendedor (−17 %), volatilidad 2,4 veces su mediana, régimen normal. Opciones de BTC (Deribit, índice 76.772): GEX positiva de 28 M USD por 1 % (los creadores frenan los movimientos), gamma flip en 76.312, muro de calls en 90.000 y de puts en 74.000, DVOL 38,5 (percentil 71). Wall Street a la defensiva: VIX 21,15 (+15 % en 5 sesiones), S&P 500 7.541 (−1,8 %), bono de 10 años en 4,95 %. Banco Mundial: el PIB mundial creció 2,92 % en 2025, dato anual que no sirve para 10 minutos. Lectura: la familia de reversión apunta a rebote de corto plazo con 52-54 %, sin ventaja suficiente para el pago 0,85.

## 8. Segunda opinión de otras IA (`c5_segunda_opinion.py`)

Se consultó a Nemotron 3 Super de NVIDIA y a DeepSeek v3 por OpenRouter, por Tor. Vieron la metodología y los resultados agregados; no vieron apuestas, saldos ni claves. La clave propia de DeepSeek del `.env` está inválida.
- Coinciden con el estudio: 85,7 % es imposible en este producto; la meta realista está entre 54 y 60 %; no hay mano caliente y «pausar al ganar» no se apoya en datos; la macro no sirve a 10-60 minutos; lo más prometedor es la microestructura (libro y flujo).
- Aportan y se adopta: validación por meses sucesivos (walk-forward) con purga y embargo, simulación de entrada tarde (0, 30, 60 s), prueba de permutación del máximo, grabar el libro de nivel 2 y el flujo de opciones desde ahora.
- Se equivocan en: decir que se eligió mirando la prueba (se eligió solo con 2021-2023; la «mejor con trampa» era la referencia del azar), en que la historia de opciones de Deribit es gratis (solo lo es la foto del momento) y Nemotron en seguir el flujo a favor, cuando aquí funciona al revés.

## 9. Diagnóstico técnico del plan

**Existe y está bien hecho.** Banco a ciegas mensual (t18 y t19) con elección por Wilson; regla escrita antes en cada prueba (t26 a t33); medio Kelly con mínimo de 5 USDT; cuentas de control (AZAR, BTC FIJO); paridad diaria; centinela v4. Desde hoy: el centinela corre en la caja T95H y en el teléfono, 24/7, con avisos por Tor (la caja primero; el teléfono solo si no ve la caja); el semáforo papel → real de BTC; el módulo `cuant/` con las seis dimensiones, validación, regímenes, CRT, ICT, libro de órdenes y opciones.

**Falta.**
1. El pago real de Binance: todo depende de él. Con 0,80 casi nada pasa el equilibrio. Lo tiene que leer él en la app (20 apuestas basta).
2. El retraso real de su toque: el aviso tarda por Tor y él tarda en tocar; cada 60 s cuesta entre 0,5 y 2 puntos.
3. Historia de microestructura fina (footprint por nivel de precio, libro de nivel 2 completo) y de opciones (GEX por día): no es gratis hacia atrás. Hay que grabarla desde ya en la caja y probarla en 60-90 días. El libro agregado (bookDepth) sí existe desde 2023 y ya se probó.
4. Validación walk-forward con purga para las reglas nuevas de `cuant/` (el banco ya lo hace mes a mes).
5. Selección mensual portable a la caja y al teléfono antes del 1/12 (hoy depende de rutas del PC y de trader-btc).
6. Vigilancia de la decadencia: alarma si el acierto de 3 meses cae bajo el equilibrio.
7. Registro de sus comentarios de Telegram: sin mirar su pantalla, la API del bot solo guarda 24 h. Queda pendiente un registrador; por ahora, lo que él reenvíe al bot.

**Incompleto.**
1. El filtro de volumen alto de BTC (t27) se aprobó y no está en el centinela.
2. La sección 18 del PLAN (su señal de dos velas en contra) no se escribió ni se probó.
3. Consolidación: los 7 días de paridad y las 100 apuestas en papel empiezan a contar de nuevo desde el 03/11 en la caja.
4. El operador Claude no opera (sesión caducada desde el 02/11); la cuenta CLAUDE no apuesta. Hay que decidir si se retira.
5. El indicador de TradingView sigue sin probar.
6. En trader-btc, el cuadro de margen de la t3 compone sin tope y da saldos imposibles (474 billones de billones de pesos con pago 0,90): hay que topar el tamaño o quitar el cuadro.
7. El PLAN.md conserva el «16 %» en su objetivo aunque la sección 9 lo reemplazó por medio Kelly.

**Debe mejorarse.**
1. La meta: de 85,7 % a 56-57 % fuera de muestra con el pago real y Wilson sobre el equilibrio.
2. Unificar en BTC (pedido suyo): ningún procedimiento de BTC pasa hoy la valla mensual (el mejor, el modelo de 10 minutos, tiene Wilson 53,5 %); la «ruptura al revés» la pasa justo en 12 meses (Wilson 54,3 %) y no en 6 (54,1 % de acierto). En BTC la ventaja está en el borde; ETH va mejor (58,5 %).
3. No cruzar todo con todo: quedarse con la familia de reversión (ruptura al revés, impulso de 15 minutos, anomalías) y probar solo combinaciones escritas antes.
4. El tamaño: con 100.000 COP, el mínimo de 5 USDT es el 15,9 % del saldo, muy por encima de medio Kelly (2-4 %). En el banco, 30 días quiebran en una de cada tres veces. Con dinero real haría falta capital de 450.000 COP o más para que el tamaño lo decida la ventaja y no el mínimo.
5. Telegram: menos mensajes de precio y más decisiones (semáforo, señal real, resultado).

## 10. Archivos

`cuant/base.py` (seis dimensiones), `validacion.py`, `c1_cruces.py`, `c2_regimenes.py`, `c3_contexto_vivo.py`, `c4_binarias_vs_futuros.py`, `c5_segunda_opinion.py`, `c6_crt_ict_libro.py`, `c7_semaforo.py`, `bajar_bookdepth.py`; salidas en `cuant/resultados/`. Capa de los equipos en `dispositivos/` (avisos, semáforo, arranque).

## 11. Lo que hicieron otros con los mejores resultados verificados

- **Concurso G-Research de predicción de cripto (Kaggle, noviembre de 2021 a mayo de 2022):** 14 monedas, rendimientos de unos 15 minutos; lo organizaron con fondos cuantitativos de primer nivel. El ganador (Meme Lord Capital) llegó a una correlación de 0,0326; el segundo, 0,0283. Los tres primeros usaron LightGBM y atribuyeron el triunfo a la ingeniería de rasgos. Una correlación de 0,03 equivale a acertar la dirección cerca de 51 % en todas las velas. Es la mejor referencia pública mundial: lo que aquí se mide (56 % solo en las velas de ruptura, un 5 % del total) es coherente con ella, y un 85,7 % no tiene ningún antecedente verificable. Fuentes: wrap-up de G-Research (www.gresearch.com/news/wrapping-up-the-g-research-crypto-forecasting-competition/) y tabla final (www.kaggle.com/competitions/g-research-crypto-forecasting/leaderboard).
- **Momentum intradía de BTC (Shen, Urquhart y Wang, 2022, Financial Review):** la primera media hora de mayor volumen predice la última media hora (R² de hasta 3,86 % en días de mucho volumen). En el banco ya está como E05, elegida solo algunos meses. Texto libre en centaur.reading.ac.uk/100181/.
- **Reversión intradía en BTC y ETH** (Wen, Bouri, Xu y Zhao, 2022; JRFM 2026): es la familia que aquí da la ventaja (ruptura al revés, impulso al revés).
- **Regulador europeo (ESMA, 2018):** prohibió vender binarias a minoristas por su rendimiento esperado estructuralmente negativo y su parecido con el juego. Comunicado: www.esma.europa.eu/sites/default/files/library/esma71-98-128_press_release_product_intervention.pdf. Es el contexto honesto de la meta: el producto está diseñado para que la mayoría pierda; solo una ventaja medida y pequeña, con disciplina, lo vuelve jugable.
- **Lo que se adopta de ellos:** la receta ganadora de G-Research (árboles potenciados sobre muchos rasgos de varios activos, validación por tiempo) como experimento E10, y el momentum de la primera media hora de Shen y otros como E11, los dos con la regla escrita en el PLAN-v5.md.
