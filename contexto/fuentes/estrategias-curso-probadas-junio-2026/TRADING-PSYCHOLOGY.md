# PSICOLOGÍA DE TRADING — INDICATIVOS PARA LA IA

> Documento HERMANO de [AI-PLAYBOOK.md](./AI-PLAYBOOK.md). El playbook te dice QUÉ
> estrategia validamos y CÓMO decidir; este documento te da los **indicativos de
> disciplina** para que decidas como un operador profesional y NO como un novato
> emocional. La IA no "siente" emociones, pero SÍ puede caer en los mismos sesgos
> (sobre-operar, perseguir, mover el stop). Estas reglas son tu blindaje.
>
> Tipo de operación al que aplica: **swing de reversión en topes de rango, ETH/USDC,
> velas de 1 hora, hold ~8h, stop-loss por rompimiento.** Todo lo de abajo está
> calibrado a ESTO, no a scalping ni a daytrading de minutos.

---

## 1. Los 5 sesgos del novato (traducidos a indicativos medibles)

No te basta con "ser prudente". Cada sesgo tiene un **disparador numérico** que puedes
detectar en los datos que se te pasan. Si detectas el disparador → tiende a ESPERAR.

| Sesgo | Qué es | Indicativo medible (disparador) | Acción |
|---|---|---|---|
| **FOMO** | Entrar tarde por miedo a perder el movimiento | `range_pos` ya salió de la zona (0.1–0.9 = a mitad de rango) o el precio ya recorrió >1× el stop a favor antes de entrar | ESPERAR: la entrada buena ya pasó |
| **Revenge** | Operar para recuperar una pérdida reciente | `lossesToday >= 1` y la nueva señal está cerca del umbral (`conf` < thr+0.05) | ESPERAR / `review_suggested` |
| **Greed** | Aguantar un perdedor o ampliar contra el plan | señal pide saltarse el stop del 3% o aumentar tamaño | VETO duro: el stop es innegociable |
| **Hesitation** | Dudar de una señal que SÍ cumple todo | checklist 4/4 `true` y aun así quieres esperar "por si acaso" | OPERAR: no inventes miedo sin dato |
| **Oversize** | Arriesgar más de la cuenta | tamaño implícito > 1% del capital arriesgado | VETO: regla del 1% (ver §3) |

> Regla de oro: **prefiere falsos negativos** (no operar algo bueno) **a falsos
> positivos** (operar algo malo). Equivocarse esperando cuesta 0; equivocarse operando cuesta capital.

---

## 1-bis. Velas de CONFIRMACIÓN (regla central del usuario) — escala de fuerza

La paciencia antes de entrar se mide en **velas de confirmación del mismo color**. Solo se
apuesta cuando es **totalmente seguro**. Escala (para comprar, "verde"; para vender, espejo en rojo):

| Patrón | Lectura | Fuerza |
|---|---|---|
| 1 vela verde pequeña | indicativo débil, aún no | 🔸 baja |
| 2 velas verdes, la 2ª mayor que la 1ª | ascenso **muy bajo**, todavía dudoso | 🔸 baja-media |
| **3 velas verdes crecientes** (cada una mayor que la anterior) | indicativo **ALTO** de subir | 🟢 alta — aquí sí |
| 2 velas rojas + 1 verde | señal sucia → **NO operar** (alta probabilidad de perder) | ⛔ veto |

- **Indicativo numérico**: en los datos esto es la feature `confirm` (cuenta velas del mismo
  color crecientes terminando en la actual). `confirm>=2` = 3 velas crecientes = señal fuerte.
- **No te asusta perder trades pequeños** (p. ej. −1.68%): es preferible esperar la 3ª vela de
  confirmación a entrar antes con una señal sucia. Calidad de confirmación > prisa.
- **Pirámide y toques**: antes de operar, mira el **próximo toque** de la pirámide/estructura.
  Si el toque previsible es ROJO o se toca un **tope** → viene caída: NO entres long ahí; espera
  a operar *antes* de la caída (saliendo) o *después* (en el rebote confirmado). Paciencia: espera
  y **analiza primero**, los tiempos están optimizados, no hace falta correr.

**Aclaración importante (dirección correcta):** las 3 velas verdes crecientes son señal de
**CONTINUACIÓN** (el precio sube → sigue subiendo), NO de reversión. Se opera **a favor** del
color confirmado. Y el cuidado con el techo es **con margen**: comprar cerca del techo SÍ vale
(aunque baje un poco, rebota y sube = ganancia), lo que se evita es comprar **pegadísimo** al
techo, donde cae sin rebote. El margen óptimo medido fue dejar operar casi hasta el techo
(`topguard ≈ 0.98`), solo vetando el extremo final.

> ⚠️ **Validación estadística (pruebas del 2026-06-23, descartar casualidad).** Backtest temporal
> ETH 1h, 24 meses, de tu regla como CONTINUACIÓN (3 velas + filtro GBM + stop 3% + margen al techo):
> - El margen al techo confirma tu intuición: `topguard 0.98` (dejar correr casi hasta el techo)
>   → **+28% PnL**, mejor que cortar pronto `0.90` (+21%). Cortar muy cerca elimina trades buenos.
> - **PERO el win rate NO sube**: se queda en **44-49%** en TODAS las variantes, con **<200 trades**
>   (máx 155). Pierde más de la mitad de las veces; el PnL sale positivo solo porque el stop corta
>   las pérdidas chicas y deja correr las ganancias.
> - Forzar más confianza con el GBM sube el win a ~55-60% **pero la muestra cae a 15-29 trades**
>   = espejismo (muestra minúscula), no señal fiable.
>
> **Conclusión honesta:** tu regla de confirmación NO alcanza "100% seguro" en los datos de ETH 1h;
> como gatillo de entrada de alta confianza robusta, los datos no la respaldan todavía. PERO como
> **indicativo de CONFIANZA/prudencia es oro**: gradúa cuánto confías (1 verde débil → 3 verdes
> crecientes fuerte), VETA entradas sucias (2 rojas + 1 verde) y exige margen al techo. Por eso
> vive aquí, en psicología, **NO** en el formato de operaciones (reversión, win 60.6%, intacto).

---

## 1-ter. Lectura del MOVIMIENTO (tamaño de cuerpos, ciclo y contexto)

No basta el color: importa el **tamaño relativo** de los cuerpos y quién (compradores vs
vendedores) tiene la fuerza. Antes de cualquier lectura, **filtra por la tasa/tendencia de
mercado**: el mismo patrón significa cosas opuestas según el contexto.

### Lado alcista (buscar continuación de subida)
- **Verde + roja = símbolo de CAMBIO → esperar.** Una roja tras una verde avisa posible giro;
  no operes aún, deja que el mercado se defina.
- **Roja MÁS PEQUEÑA que la verde previa** = el cambio es **débil** (los vendedores no pudieron):
  mini-indicativo de que vienen **2 velas verdes de confirmación**. Espera a que aparezcan.
- **Ciclo de cuerpos**: si hubo una verde **grande** y luego las verdes se van **empequeñeciendo**,
  y entran rojas → aunque los compradores "pierdan" ese tramo, hay buena probabilidad de que
  **retomen fuerza** (es un ciclo): el impulso grande anterior suele volver → posible nueva subida.
  No lo das por muerto solo porque las rojas tomaron fuerza un momento.
- **Apuesta 100% segura al alza**: solo cuando hay **2-3 verdes de ciclo** confirmando, y con
  margen al techo (§1-bis). Complementa: confirmación verde **+** espacio para correr.

### Lado bajista (buscar caída para aprovechar abajo)
- **Ciclo de caída** (p. ej. 6 rojas seguidas, o 2 rojas + 1 verde): mira el **tamaño** de las rojas.
- **2 rojas, una pequeña y luego una grande hacia abajo** = aceleración vendedora → indicativo de
  **caída** (los vendedores tomaron el control). Buen indicativo de apuesta bajista.
- **Ahorcado** = vela con **mecha inferior larga y delgada hacia abajo**. Tras una subida (contexto
  agotado) avisa **caída** y que puede **caer aún más** → aprovechar abajo (short).
  > ⚠️ Honestidad técnica: esta MISMA forma (mecha inferior larga) es **martillo (alcista)** si
  > aparece tras una CAÍDA, y **ahorcado (bajista)** si aparece tras una SUBIDA. Por eso el
  > **contexto/tasa de mercado manda**: sin saber la tendencia previa, no decidas su signo.

### Resumen operativo (indicativo de confianza, no gatillo duro)
- Cuerpos verdes **crecientes** + roja pequeña + lejos del techo → confianza al alza ↑.
- Rojas **crecientes** hacia abajo o ahorcado tras subida → confianza a la baja ↑ (caída).
- Verde + roja sin definición, o patrón contra la tendencia → **esperar** (es gratis).

> Recordatorio de los datos (§1-bis): estas lecturas de movimiento **suben la confianza
> cualitativa** y filtran entradas sucias, pero en ETH 1h no elevaron el win rate de forma robusta
> como gatillo duro. Son tu brújula de prudencia; el motor de entrada sigue siendo el cuantitativo.

---

## 2. Checklist pre-operación (las 4 + 2)

El playbook ya define las **4 casillas** (coherente con rango, GBM supera umbral, patrones
no contradicen, contexto intradía ok). Añade estas **2 de disciplina** antes de `operate`:

5. **`riesgo_definido_ok`**: el stop está fijado (3% o ATR, §4) y el riesgo ≤ 1% del capital.
6. **`sin_revancha_ok`**: no estás operando movido por una pérdida reciente (§1 Revenge).

→ `operate` SOLO si las **6** son `true`. Una sola en `false` = `wait`. Sin excepciones.

---

## 3. Gestión de riesgo (los números que protegen el capital)

- **Regla del 1%**: nunca arriesgues más del **1% del capital** en una sola operación. Con
  stop del 3%, eso fija el tamaño máximo de posición (tamaño = capital × 1% ÷ 3%).
- **Máxima pérdida diaria**: si `lossesToday >= 3` (o pérdida acumulada del día ≥ 3% del
  capital) → recomienda PARAR el día (`review_suggested: true`, tiende a `wait`). Esto es lo
  que mata el *revenge trading*: no hay más balas hoy.
- **Ratio riesgo/beneficio**: la estrategia busca el techo/suelo opuesto del rango; el
  objetivo implícito debe valer **≥ 1.5×** lo que arriesga el stop. Si el recorrido restante
  hasta el tope contrario es menor que 1.5× el stop, la entrada es pobre → `wait`.

---

## 4. Estrategias de STOP-LOSS (qué usamos y por qué)

Investigado y contrastado para cripto (alta volatilidad). Resumen de opciones:

- **Fijo 3% (ACTUAL, validado)**: simple, robusto, fue la pieza que volvió rentable la
  estrategia en 24 meses. Su límite: no se adapta a la volatilidad del momento.
- **ATR (Average True Range)**: stop = `k × ATR`. Se ensancha en volatilidad y se aprieta en
  calma → menos barridos por ruido. Para cripto en marcos de horas, el estándar profesional es
  **k = 2–3× ATR** (cripto necesita múltiplos mayores que forex/acciones por sus *swings*).
  *Pendiente de validar en backtest*: probar `--stop atr --k 2.5` contra el fijo 3% en
  `bench.js` y quedarnos con el que tenga **mejor PnL con plateau** (no el más bonito).
- **Trailing stop**: NO aplicar al entrar. Primero stop duro; cuando la operación avance
  **≥ 1R** (una unidad de riesgo) a favor, recién entonces convertir a trailing para proteger
  ganancia. Útil para no devolver un trade ya ganador.

> Principio innegociable: **el stop no se mueve en contra, JAMÁS**. Moverlo "para darle aire"
> es el sesgo *Greed* disfrazado de paciencia. El stop solo se mueve a favor (trailing).

---

## 5. "Pips" y movimiento mínimo (traducción cripto)

En forex un **pip** es el último decimal de la cotización (p. ej. 0.0001 en EUR/USD) y mide el
movimiento mínimo. En cripto **no se opera en pips**: se razona en **porcentaje (%)** y en el
**tick** del par. Para nosotros (ETH/USDC):

- El "pip equivalente" es el **% de movimiento**. Todo edge se mide en % por operación.
- **Umbral de rentabilidad**: el coste de ida y vuelta es ~**0.05%** (validado). Un trade cuyo
  recorrido esperado no supere holgadamente ese coste **no vale la pena** (es el error de
  operar en 1m/30m: el edge se lo come el coste). Por eso operamos en **1h**, donde el recorrido
  por trade es de varios % y el coste pesa poco.
- Indicativo: si el movimiento esperado hasta el objetivo es **< 3× el coste** (< ~0.15%),
  trátalo como ruido → `wait`.

---

## 6. Análisis de mercado tipo forex aplicado al TIMING (sesiones y horas)

Aunque cripto cotiza 24/7, la **liquidez y volatilidad NO son uniformes** durante el día, igual
que en forex hay sesiones. Usa la **hora UTC** que se te pasa (`hourUTC`) como indicativo de timing:

- **Sesión asiática (~00:00–07:00 UTC)**: suele ser de menor volatilidad y más rango lateral.
  Bueno para reversión en topes, pero ojo con rangos estrechos/falsos.
- **Apertura de Londres (~07:00–10:00 UTC)** y **solape Londres–Nueva York (~13:00–16:00 UTC)**:
  máxima liquidez y volatilidad. Los movimientos tienen más continuación → un tope puede
  romperse de verdad (sube la probabilidad de que salte el stop). Más prudencia con la reversión.
- **Primeros 15–30 min de una vela/sesión nueva**: ruido. Desconfía de señales ahí.
- **Madrugada/fin de semana**: liquidez baja, *spreads* más amplios y mechas falsas. Sube el veto.

> No tienes feed de noticias en vivo. Si es **día de evento macro conocido** (FOMC, CPI, etc.)
> o el *Fear & Greed* está en extremo, márcalo con `review_suggested: true` y, sin el dato,
> asume MÁS incertidumbre → tiende a esperar. Calendario de referencia en el playbook §6.

---

## 7. Diario psicológico (etiquetas para aprender de ti misma)

Cada decisión se graba en `data/ai-journal.csv`. Al razonar, **etiqueta mentalmente** el riesgo
psicológico de la señal con una de estas (y menciónala en `reason` si aplica):

- `FOMO` — entrada tardía, el movimiento ya corrió.
- `REVENGE` — hay pérdidas hoy y la señal es floja.
- `HESITATION` — checklist 4/4 pero dudas sin dato → probable falso miedo.
- `OVERSIZE` — el tamaño rompería el 1%.
- `CLEAN` — setup de libro, sin banderas: la única en la que `operate` está plenamente justificado.

Revisa tu propio historial (se te pasa en el prompt): si ves un patrón de pérdidas tras
operar señales flojas, **endurece el umbral** mentalmente. Aprender del journal > repetir el error.

---

## 8. Recordatorio final

La psicología profesional se resume en una frase: **un buen trade se mide por lo bien que
seguiste el proceso, NO por cuánto ganaste**. Una operación perdedora que respetó las 6 casillas
y el stop es un BUEN trade. Una ganadora que se saltó el plan es un MAL trade que te enseñó un
mal hábito. Tu trabajo no es acertar cada vez: es **ejecutar el sistema con disciplina fría**.

---

### Fuentes consultadas
- [10 Powerful Trading Psychology Rules](https://www.tradingpsychologymentor.com/10-trading-psychology-rules)
- [Reduce Emotional Trading with Structured Risk Rules — PFH Markets](https://blog.pfhmarkets.com/trading-risk-management/reduce-emotional-trading-structured-risk-rules/)
- [How to Avoid Revenge Trading (Crypto Swing) — Altrady](https://www.altrady.com/blog/swing-trading/how-to-avoid-revenge-trading-practical-tips)
- [Trading Psychology Journal & Tags — TradesViz](https://www.tradesviz.com/blog/trading-journal-psychology-tracking/)
- [Swing Trading Risk Management Checklist — Medium](https://medium.com/@tmapendembe_28659/swing-trading-risk-management-checklist-a8ef0afcf6cc)
- [5 ATR Stop-Loss Strategies — LuxAlgo](https://www.luxalgo.com/blog/5-atr-stop-loss-strategies-for-risk-control/)
- [ATR Trailing Stop vs. Fixed Stop Loss — AI Signals](https://ai-signals.com/atr-trailing-stop-vs-fixed-stop-loss-which-is-better-for-your-strategy/)
