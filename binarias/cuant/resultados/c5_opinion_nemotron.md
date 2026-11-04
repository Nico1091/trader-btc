# Segunda opinión: nemotron

Modelo pedido: nvidia/nemotron-3-super-120b-a12b · responde: nvidia/nemotron-3-super-120b-a12b · fin: stop · 60.6 s · huella 48134aab3190858b



**Revisión cuantitativa – plan de investigación y validación para binarias de 10 min (BTC/ETH)**  

---

### 1. Qué está bien  
| Ítem | Comentario | Evidencia / número |
|------|------------|--------------------|
| **Base de datos** | Uso de velas 1 min de futuros perpetuos 2020‑2026 con taker‑buy volume es sólido y cubre varios ciclos de mercado. | ~6 años, > 500 k barras. |
| **Procedimiento de selección mensual a ciegas** | Elegir el mejor de 8 modelos con los 12 meses anteriores evita sobre‑ajuste inmediato y da una línea de base reproducible. | Banco 2021‑2026: 57‑58 % acierto en 11‑43 k apuestas. |
| **Exploración multivariada** | Se probaron 6 dimensiones discretizadas y se generaron 14 600 celdas de 2‑3 variables, lo que muestra un esfuerzo de búsqueda razonable. | 7 000 pasan BH; 1.200‑1.450 con Wilson > 54,1 %. |
| **Control de falsos descubrimientos** | Aplicación de Benjamini‑Hochberg y cálculo de intervalos de Wilson indica conciencia del problema de múltiplos tests. | BH reduce a 7 k; Wilson filtra a ~1.3 k. |
| **Análisis de out‑of‑sample (OOS)** | Se reporta desempeño fuera de muestra (prueba 2021‑2023) y se calcula PBO mediante CSCV (16 bloques). | PBO = 0,1 % (BTC) y 2,7 % (ETH). |
| **Estudio de rachas y autocorrelación** | Se examinó la persistencia de aciertos y la estructura de retornos a 10 min, mostrando falta de “mano caliente”. | Tras acertar 51,8 % (cartera) vs 53,9 % tras fallar. |
| **Modelo de régimen (HMM)** | Se probó si existen regímenes con sesgo direccional; resultado negativo es útil para descartar hipótesis simples. | Sin sesgo en ninguno de los 3 regímenes. |

### 2. Qué está mal / fuentes de sesgo  
| Problema | Por qué invalida o debilita el resultado | Impacto aproximado |
|----------|------------------------------------------|--------------------|
| **Selección basada en el mismo conjunto que se usa para evaluar** | Las “mejores celdas” se eligen mirando el resultado de la prueba (2021‑2023) y luego se reportan sus tasas OOS como si fueran independientes. Esto infla el sesgo de selección (look‑ahead bias). | Puede añadir 2‑4 % punto porcentual de acierto aparente. |
| **Uso de una única variable “sentido elegido en entrenamiento”** | Reduce la dimensionalidad a posteriori; la variable se escoge porque ya mostró alta tasa en entrenamiento, lo que constituye *double‑dipping*. | Sobre‑estima la fuerza de la señal; el rendimiento real tiende a caer a ~53 % (como se observa). |
| **Tamaño de muestra insuficiente para celdas de alta dimensión** | Muchas celdas tienen apenas 300‑500 apuestas; el intervalo de Wilson es amplio y la probabilidad de superar el umbral por azar es alta. | Con 300 apuestas, un 55 % observado tiene un IC 95 % ≈ [49,2‑60,8]; muchos “> 54,1 %” son ruido. |
| **Ausence de purga y embargo (purging & embargo)** | En series financieras con autocorrelación negativa a 10 min, los folds de validación pueden contener información filtrada del entrenamiento si no se deja un gap. | Puede inflar el acierto en ~0,5‑1 % punto porcentual. |
| **No se descontó el número total de pruebas (multiple‑testing correction final)** | Se aplicó BH a nivel de celdas, pero el reporte final (“la mejor de la prueba, escogida mirando el resultado, 66‑69 %”) ignora que se está escogiendo el máximo entre ~15 500 celdas de 100 apuestas. El ajuste necesario sería un *max‑t* o *bootstrap* de la distribución del máximo bajo nulo. | El 66‑69 % es exactamente lo que se espera por azar (ver comentario). |
| **Costos de entrada tardía y slippage no modelados** | Binance fija el pago al momento de la apuesta; entrar unos segundos después puede cambiar el precio subyacente y, por ende, la probabilidad real de ganar. En datos de 1 min, el slippage medio puede ser 1‑2 bp, lo que equivale a ~0,1‑0,2 % de pérdida esperada por apuesta. | Reduce el acierto neto en ~0,1‑0,2 % punto porcentual. |
| **Falta de walk‑forward o CPCV completo** | Sólo se usó CSCV con 16 bloques; no se probó una ventana que se desplace mensualmente (walk‑forward) ni se validó la estabilidad de los parámetros a lo largo del tiempo. | Riesgo de sobre‑ajuste a regímenes específicos (p. ej., alta volatilidad 2020‑2021). |
| **Definición de “empate = fallo” sin justificación** | Arbitrariamente penaliza las señales neutras; si la distribución de probabilidades es simétrica, esto puede bajar el acierto esperado en ~0,5 % punto porcentual. | Peor caso: sub‑estimación de la verdadera capacidad. |

### 3. Qué falta (validaciones y mejoras)  
1. **Purging & embargo** en cualquier esquema de validación cruzada (mínimo 1 barra de 10 min = 10 min de gap).  
2. **Walk‑forward mensual** (entrenar 12 meses, validar el mes siguiente, repetir) para medir la decadencia del desempeño.  
3. **Deflacionar el acierto por número de pruebas**: usar la distribución del máximo bajo nulo (permuta etiquetas o bootstrap) y reportar el *p‑valor* del mejor modelo.  
4. **Análisis de sensibilidad al slippage y al tiempo de ejecución** (simular entrada a t+0, t+30 s, t+60 s).  
5. **Evaluación de Kelly fraccionario** (fKelly = 0.5‑0.25) y comparación con tamaño fijo 5 USDT para ver si el criterio de tamaño mejora la razón de Sharpe.  
6. **Prueba de robustez a cambios de régimen** (dividir la muestra en alta/ baja volatilidad, bull/bear, y ver si el modelo mantiene > 54 %).  
7. **Out‑of‑sample totalmente ciego**: usar un periodo que nunca haya tocado ni siquiera para la selección de variables (p. ej., 2024‑2025) y reportar solo ahí.  
8. **Análisis de costo de oportunidad** (pausar al ganar) mediante simulación de una estrategia que continúe operando vs. una que se detenga N apuestas después de una victoria.  

### 4. Prioridad de acciones (qué hacer después)  
1. **Implementar walk‑forward con purging & embargo** y volver a calcular el acierto OOS y el PBO.  
2. **Aplicar corrección de máximo de pruebas** (bootstrap del máximo bajo nulo) para obtener un intervalo de confianza real del mejor modelo.  
3. **Simular slippage y latencia** (0‑60 s) y re‑estimar el acierto neto.  
4. **Probar Kelly fraccionario y tamaño fijo** en el mismo walk‑forward para decidir la política de apuesta.  
5. **Validar en un periodo totalmente ciego (2024‑2025)** antes de considerar cualquier puesta en producción.  

---

## Respuestas a las preguntas del dueño  

**1. Errores de método / fugas de información y validaciones faltantes**  
- **Fuga principal:** selección de la “mejor celda” mirando el resultado de la prueba y luego reportarla como OOS (look‑ahead bias).  
- **Otras fugas:** ausencia de purging/embargo en el CSCV, uso de una única variable elegida a posteriori, y no corregir el máximo de pruebas.  
- **Validaciones que faltan:** walk‑forward mensual con purging & embargo, corrección del máximo de pruebas (bootstrap/permuta), simulación de slippage y latencia, y una muestra totalmente ciega (2024‑2025) para el reporte final.  

**2. Plausibilidad de 85,7 % y meta honesta**  
- Con el pago fijo de Binance (0,80‑0,90) el punto de equilibrio está entre 52,6‑55,6 %. Para superar el 85,7 % se necesitaría una ventaja bruta de ≈ 33  puntos porcentuales, lo que equivale a una razón de Sharpe anual > 5 en un activo con volatilidad diaria del 3‑4 % – prácticamente imposible en mercados eficientes sin información privilegiada.  
- **Meta honesta:** 58‑60 % de acierto (≈ 2‑4 % sobre el punto de equilibrio) con una razón de Sharpe de 0,3‑0,4 en el periodo de validación walk‑forward. Se mide como:  
  \[
  \text{Acierto neto}= \frac{\#\text{ganadas}}{\#\text{apuestas}} - \text{equilibrio}
  \]  
  y se reporta el intervalo de confianza del 95 % mediante bootstrap de las apuestas.  

**3. Qué de la lista nueva (L2, footprint, opciones/GEX, macro) tiene más probabilidad de sumar ventaja a 10‑60 min**  
- **Footprint / delta de volumen agresivo (taker‑buy vs taker‑sell) a escala de 1‑5 min** muestra la mayor persistencia en estudios de microestructura de futuros BTC/ETH (autocorrelación del orden flow ≈ 0,1‑0,2 a 1‑min).  
- **Cómo probarlo a ciegas con datos gratuitos/baratos:**  
  1. Descargar el *trade‑by‑trade* (ticks) de Binance futures vía su API pública (limit 500 ticks/seg, suficiente para 1‑min agregados).  
  2. Construir el *cumulative delta* (compras agresivas – ventas agresivas) en ventanas de 1, 3 y 5 min.  
  3. Definir una regla simple: si el delta de los últimos 3 min supera el percentil 80 de su distribución histórica (entrenado en los 12 meses previos) → apostar *SUBE*; si está bajo el percentil 20 → apostar *BAJA*.  
  4. Validar con walk‑forward 12‑meses‑entrenado / 1‑mes‑test, purging de 1 barra (10 min) y embargo de 1 barra, reportando acierto y PBO.  
  Si el acierto neto supera el 55 % con p‑valor < 0,05, se considera una señal válida.  

**4. Tamaño de apuesta y regla de “pausar al ganar”**  
- **Tamaño:** usar una fracción fija de Kelly (fKelly = 0.25) calculada con la probabilidad estimada *p* y el pago *b* (pago = 0,80‑0,90). Esto reduce la varianza y evita la ruina cuando la verdadera ventaja es pequeña. En la práctica, con p≈0,55 y b=0,85, Kelly≈0,018 → 0,25·Kelly≈0,0045 → 4,5 USDT (redondeado a 5 USDT). Mantener el mínimo de 5 USDT es razonable, pero revisarlo cada mes según la *p* actualizada.  
- **Pausar al ganar:** la idea de detenerse tras una victoria asume una “mano caliente” que los datos muestran inexistente (51,8 % tras acertar vs 53,9 % tras fallar). En vez de pausar, aplicar un *stop de ganancia* basado en una racha máxima (p. ej., después de 2 victorias seguidas, reducir la fracción de Kelly a 0,10) o simplemente continuar con la misma fracción. Simular ambas opciones en el walk‑forward mostrará que “pausar al ganar” reduce el retorno esperado en ≈ 0,1‑0,2 % punto porcentual sin mejorar la razón de Sharpe.  

**5. Los 5 próximos experimentos (regla de decisión escrita antes)**  

| # | Experimento | Hipótesis | Regla de decisión (escrita antes de ver resultados) | Métrica de éxito |
|---|-------------|-----------|------------------------------------------------------|------------------|
| 1 | **Footprint delta 3 min** | El delta acumulado de compras agresivas en los últimos 3 min predice la dirección del precio a 10 min. | Si `delta_3m > P80(delta_3m, entrenamiento)` → **SUBE**; si `< P20` → **BAJA**; else **NO OPERAR**. Entrenamiento: últimos 12 meses; test: mes siguiente; purging = 1 barra (10 min); embargo = 1 barra. | Acierto neto > 55 % con IC 95 % excluyendo 52,6 % (p‑valor < 0,05). |
| 2 | **Order‑book imbalance (L2) 1 min** | Un desequilibrio > 2 sigma en el volumen de las 5 primeras niveles de ask/bid indica presión direccional a 10 min. | Calcular `imb = (VolAsk5‑VolBid5)/(VolAsk5+VolBid5)`. Si `imb > +2σ` → **SUBE**; si `imb < -2σ` → **BAJA**; else **NO OPERAR**. Mismos folds que en 1. | Acierto neto > 55 % y reducción de varianza vs. baseline (ΔSharpe > 0,05). |
| 3 | **Gamma‑flip de opciones BTC/ETH (1‑día)** | Cuando el strike con mayor OI cruza el precio subyacente (gamma‑flip) la probabilidad de movimiento al alza en los próximos 30 min aumenta. | Obtener OI por strike desde datos públicos de Deribit (gratuitos). Si `precio > strike_gamma_flip` → **SUBE**; si `precio < strike_gamma_flip` → **BAJA**; else **NO OPERAR**. Entrenamiento: 12 meses; test: mes siguiente; purging = 1 barra (30 min). | Acierto neto > 55 % y p‑valor < 0,05. |
| 4 | **Macro sorpresa (CPI EE. UU.)** | Las sorpresas del índice de precios al consumo (diferencia entre consenso y dato real) generan un sesgo direccional de 10‑60 min en BTC/ETH. | En la publicación del CPI (hora conocida), calcular `surprise = real - consenso`. Si `surprise > +0,1 %` → **SUBE**; si `< -0,1 %` → **BAJA**; else **NO OPERAR**. Usar solo los días de publicación (≈ 12/año). Entrenamiento: 24 meses anteriores; test: mes siguiente; purging = 1 barra (60 min). | Acierto neto > 55 % y número suficiente de trades (> 30) para significancia. |
| 5 | **Combined model (delta + L2 + gamma‑flip)** | Una combinación ponderada de las tres señales mejora la robustez frente a ruido individual. | Puntaje = w1·sign(delta_3m) + w2·sign(imb) + w3·sign(gamma‑flip). Pesos optimizados por regresión logística L2 en entrenamiento (12 meses). Operar **SUBE** si puntaje > 0,5; **BAJA** si < ‑0,5; else **NO OPERAR**. Mismo esquema de walk‑forward con purging = 1 barra (10 min). | Acierto neto > 57 % (objetivo ambicioso pero plausible) y PBO < 0,5 %. |

*Nota:* Cada experimento se ejecutará **en papel** (simulado) hasta que pase la validación walk‑forward sin mirar los resultados del periodo de prueba; sólo entonces se considerará para posible puesta en producción.  

---  

**Resumen:** El plan actual muestra buen esfuerzo pero contiene varios sesgos de selección y falta de validaciones rigurosas. Corregirlos reducirá el supuesto desempeño de ~66‑69 % a un rango más realista de 54‑58 %. Un objetivo honesto es 58‑60 % de acierto (≈ 2‑4 % sobre el punto de equilibrio). El flujo de órdenes agresivo (footprint/delta) y el desequilibrio del libro de órdenes (L2) son las vías más prometedoras para obtener esa ventaja a 10‑60 min, y pueden probarse a bajo costo con datos públicos de ticks y L2. El tamaño de apuesta debería basarse en una fracción conservadora de Kelly y la regla de “pausar al ganar” no está respaldada por los datos. Los cinco experimentos propuestos, con reglas de decisión fijadas antes de ver los resultados, ofrecerán un camino claro para validar o descartar cada fuente potencial de alfa.  

---  

*Fin de la revisión.* (≈ 730 palabras)
