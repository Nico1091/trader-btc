# Segunda opinión: deepseek-openrouter

Modelo pedido: deepseek/deepseek-chat-v3-0324 · responde: deepseek/deepseek-chat-v3-0324 · fin: stop · 49.4 s · huella 08503621b4477924

### **Revisión Crítica del Plan de Investigación (Respuestas Numeradas)**  

#### **1. Errores de Método y Fugas de Información**  
- **Fuga de datos en validación**:  
  - Usar **octubre 2026** para juzgar el modelo (aunque sea "intacto") es un error: ese mes ya se filtró en la selección de celdas (p.ej., rupturas alcistas/bajistas con 61,7%/55,0% en BTC). **Solución**: Purga total de 2024-2026 en entrenamiento y prueba; walk-forward con ventanas móviles.  
  - **PBO (Probability of Backtest Overfitting) subestimado**: CSCV con 16 bloques es insuficiente para 15.500 celdas. Aplicar **CPCV (Combinatorial Purged Cross-Validation)** o aumentar bloques a 50+.  

- **Problemas no medidos**:  
  - **Coste de ejecución**: En binarias, entrar 1-2 segundos tarde reduce el pago fijo (ej: de 0,85 a 0,80). Simular retrasos de 1-5 segundos.  
  - **Desvío por tamaño mínimo (5 USDT)**: Kelly asume apuestas continuas; el mínimo artificial infla el riesgo. Probar con 1 USDT.  

#### **2. Meta Realista de Acierto**  
- **85,7% es imposible** en binarias de 10-60 min:  
  - El mejor caso observado (66-69% en prueba) es **ruido estadístico** (15.500 celdas → 1/20.000 chance de 69% por azar).  
  - **Límite teórico**: Con microestructura de órdenes, el máximo histórico en estudios académicos es ~60-65% (y decae en 1-2 años).  
- **Meta honesta**:  
  - **54-56% neto** (ajustando por costes y desvíos) con **Sharpe > 2** en walk-forward.  
  - **Métrica clave**: Probabilidad de quiebra (Kelly + simulación Monte Carlo).  

#### **3. Factores con Potencial Real**  
Ordenados por viabilidad/costo:  
1. **Libro de órdenes (L2)**:  
   - **Foco**: Desequilibrio en profundidad (ej: 3x más bids que asks) + delta de mercado.  
   - **Prueba**: Datos de TradeView (baratos) o Bybit/Binance L2 históricos (gratis con límites). Validar con purga temporal.  
2. **Flujo de opciones (GEX/DEX)**:  
   - **Foco**: Gamma flip en strikes cercanos (10-30 min antes de vencimiento).  
   - **Prueba**: Datos de Deribit (API gratuita para OHLC de opciones).  
3. **Footprint/TPO**:  
   - **Foco**: Clústeres de volumen en zonas de precio clave (ej: 70% del volumen en 0,1% del rango).  
   - **Prueba**: Plataformas como QuantData o TradingView (coste moderado).  

*Macro y Wall Street son irrelevantes para 10-60 min*.  

#### **4. Tamaño de Apuesta y "Pausar al Ganar"**  
- **Kelly mínimo de 5 USDT**:  
  - **Error**: Introduce sesgo de supervivencia (solo sobreviven las series con suerte inicial). Usar **Kelly fraccional (0,1-0,3x)** y tamaño mínimo de 1 USDT.  
- **Pausar al ganar**:  
  - **No funciona**: Los datos muestran **ninguna autocorrelación positiva** (tras acertar: 51,8%; tras fallar: 53,9%). Es superstición.  

#### **5. Próximos 5 Experimentos (Reglas Predefinidas)**  
1. **Walk-forward con purga estricta**:  
   - **Regla**: Ventana de 24 meses entrenamiento, 6 meses prueba; purgar 1 mes antes/después de cada prueba. Elegir mejor modelo por Sharpe, no acierto.  
2. **Microestructura con L2**:  
   - **Regla**: Apostar **en contra** del delta de mercado (taker buy/sell) si el desequilibrio en L2 es > 2:1 en los 5 niveles más cercanos.  
3. **Footprint + zonas de liquidez**:  
   - **Regla**: Operar rupturas de rango con volumen acumulado > 300% del promedio en la última hora.  
4. **Anomalías con autocorrelación negativa**:  
   - **Regla**: Tras 3 velas consecutivas en una dirección (ej: bajistas), apostar reversión con filtro de ATR(15 min) > 1,5x la media.  
5. **Simulación de costes reales**:  
   - **Regla**: Aplicar retraso de 2 segundos en cada entrada y reducir pago fijo en 0,05 puntos. Máximo 10 operaciones simultáneas.  

---  
### **Conclusión**  
El proyecto tiene **potencial modesto (54-56% neto)** pero está lastrado por metas irreales (85,7%) y fugas de datos. Priorizar:  
1. **Corregir validación** (walk-forward + CPCV).  
2. **Enfoque en microestructura** (L2, footprint).  
3. **Rediseñar gestión de riesgo** (Kelly fraccional, sin pausas).  
4. **Abandonar factores sin edge** (macro, "mano caliente").
