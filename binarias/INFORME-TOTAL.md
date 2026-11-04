# Informe total de las binarias (congruencia, evidencia y diagnóstico)

3 de noviembre de 2026, 21:40 (hora de Colombia). Reemplaza como lectura principal al informe de `cuant/` del mismo día; el detalle de cada prueba sigue en `cuant/resultados/`. Todas las cifras de acierto que deciden algo se dan con entrada 60 s tarde, como él toca a mano.

## 1. La lógica única del sistema

Todo lo que se queda responde a una sola idea, medida de varias formas:

**A 10 minutos, BTC tiende a devolverse después de estirarse. La ventaja es pequeña, cambia con el tiempo y depende de entrar rápido y del pago que fije Binance.**

De esa idea salen tres reglas que no se contradicen:
1. Se apuesta solo a la devolución (reversión), nunca a la continuación.
2. Se opera en real solo los días en que la estrategia viene demostrando que funciona (semáforo VERDE), se para con la primera pérdida y nunca con apalancamiento.
3. Nada entra sin la misma prueba: regla escrita antes, elegir en un tramo y juzgar en otro, entrada tarde y pago real.

## 2. Evidencia de la idea (BTC, a ciegas)

- Autocorrelación negativa de los tramos de 10 minutos (−0,043 en 2021-23, −0,026 en 2024-26) y razón de varianzas menor que 1 (z ≈ −2,3): el precio se devuelve más de lo que seguiría el azar, y cada vez menos.
- Ruptura de 20 velas de 5 minutos al revés, entrando 60 s tarde: 57,0 % en 2021-23, 54,4 % en 2024 a sep-2026 (Wilson 53,6 %) y 60,7 % en octubre de 2026. Entrando al cierre, 56,1 % en la prueba: cada minuto de demora cuesta cerca de 1,7 puntos.
- Las demás medidas de la misma idea coinciden en el sentido: el impulso de 15 minutos al revés (54-55 % al cierre), la anomalía de 10 minutos al revés (54-56 %), tres tramos iguales al revés (53,8 %), el flujo de órdenes al revés (52 %). Cuando la ruptura y el impulso disparan a la vez, apuntan al mismo lado el 100 % de las veces (19.746 casos).
- Todo lo que apuesta a la continuación pierde a 10 minutos: seguir la ruptura de sus líneas (43-46 %), operar con todo a favor (44-52 %), el triángulo (46-53 %).

## 3. El factor probabilístico de la racha (lo que él preguntó)

- Existe hacia atrás: un modelo oculto de Markov sobre los aciertos de la propia estrategia separa rachas buenas (58,1 %) y malas (55,7 %) que duran unas 50 apuestas.
- No se deja ver hacia adelante: filtrado sin mirar el futuro, en 2024-26 da 54,5 % frente a 54,4 % de operar siempre (p = 0,22). La correlación entre el acierto de las últimas 100 apuestas y el del día siguiente es 0,026 (ruido por debajo de 0,062).
- El semáforo de las últimas 100 en 58 % o más, medido bien (60 s tarde), da en 2021-2026 56,5 % frente a 55,9 % de días al azar (p = 0,04), y con la parada en la primera pérdida 57,4 % frente a 56,4 % (p = 0,12). En 2024-26 solo, sin efecto.
- Conclusión congruente: el semáforo no adivina los días buenos; los aprovecha cuando ya vienen y limita lo que se arriesga en los malos. Es la forma honesta de su regla «solo se opera cuando está dando resultados».

## 4. Auditoría de congruencia

**Se queda (congruente con la lógica única):**
- La ruptura de 20 velas de 5 minutos al revés en BTC: núcleo del semáforo.
- Las reglas de BTC FIJO de noviembre, todas de devolución (hombre colgado en su sentido, E19 EMA-RSI al revés, techo y piso de 24 h).
- Su señal de dos velas, al revés (56-57 % en contra): candidata E9.
- El índice de estabilidad (t33): aprendió solo devolución; se usa como contexto.
- Defensas que nacen de la misma idea, porque la devolución falla cuando el movimiento trae información: no operar con volumen alto en BTC (t27, ya aprobado) y no operar alrededor de anuncios macro (por probar).
- Hipótesis congruente para probar con datos que hay que grabar: la devolución debería funcionar mejor con GEX positiva (los creadores de mercado frenan los movimientos) y peor bajo el gamma flip.
- El semáforo con parada en la primera pérdida, medio Kelly y el mínimo de 5 USDT.

**Se descarta (incongruente):**
- Toda apuesta a la continuación a 10-30 minutos: sus dos resistencias a favor, el toque de la segunda resistencia, «todo a favor», la ruptura del triángulo, el momentum de la primera media hora (E11 del plan v5) y el libro de órdenes leído a favor (E3 del plan v5).
- Las cajas negras que mezclan lógicas contrarias y no se pueden explicar: el modelo unificado U y la receta de árboles potenciados de G-Research (E10 del plan v5). La referencia de G-Research se conserva como medida de lo posible, no como estrategia.
- SMC, ICT, CRT, killzones, área de valor, OTE, SMT, premium y discount como señales: sin ventaja y con lógica ambigua a este plazo.
- La «mano caliente» y «pausar al ganar» como fuente de ventaja; la martingala; el 16 % fijo; el oro.
- La meta de 85,7 %: contradice los datos de 2021 a 2026 y la mejor referencia mundial.
- ETH como mercado operado: contradice la unificación en BTC. En noviembre sigue midiéndose en silencio (la cuenta REGLA ya estaba elegida el 1/11); desde el 1/12 la selección queda solo en BTC y solo entre estrategias de devolución.

**Contexto (se mira, nunca decide):** opciones (GEX, gamma flip, muros, DVOL), libro de órdenes, VIX, S&P 500, bono de 10 años, noticias, Banco Mundial, régimen del HMM de mercado y sus comentarios en Centro nocturno.

## 5. Diagnóstico técnico

**Existe:** banco a ciegas mensual; centinela en la caja T95H y el teléfono, 24/7, con avisos por Tor y respaldo mutuo; semáforo con medida de 60 s; estudio C1 a C8; protocolo de validación; memoria y recordatorio que insisten.

**Falta, en orden de importancia:**
1. El pago real de Binance (todo depende de él: con 0,80 hace falta 55,6 %).
2. Su demora real al tocar (cada minuto cuesta cerca de 1,7 puntos).
3. Grabar desde ya en la caja el libro, las operaciones una por una y las opciones, para probar la hipótesis de la GEX en 90 días.
4. Selección mensual portable al teléfono y restringida a estrategias de devolución en BTC antes del 1/12.
5. El filtro de volumen alto de BTC dentro del centinela.

**Incompleto:** sección 18 del PLAN (su señal de dos velas al revés); consolidación (7 días de paridad y 300 apuestas en papel desde el 03/11); operador Claude sin uso; Pulso por recompilar.

**Corregido hoy:** C7 medía la ruptura al cierre y lo presentaba como 60 s tarde; con la corrección, el 59,8 % que se informó pasa a 57,4 % frente a 56,4 % del azar. El semáforo de los equipos también medía al cierre; desde las 21:39 mide con 60 s.

## 6. Qué es posible y qué no

En binarias de 10 minutos sobre BTC, lo alcanzable con lo medido es 55-57 % en los días buenos, con un pago de 0,85 o mejor y entrando en segundos. El concurso G-Research (Kaggle, 2022) lo ganaron fondos cuantitativos con una correlación de 0,0326 a 15 minutos, unos 51 % sobre todas las velas: un 85,7 % no tiene antecedentes. La ESMA prohibió las binarias para minoristas en 2018 por su rendimiento esperado negativo. Con 100.000 COP, el mínimo de 5 USDT es el 15,9 % del saldo: la ruina pesa más que la ventaja hasta que el capital ronde los 450.000 COP.

## 7. Mercado del 03/11 (20:32)

BTC 76.882 (−11 % en 30 días), volatilidad 2,4 veces su mediana, régimen normal; GEX positiva de 28 M USD por 1 %, gamma flip en 76.312, muros en 90.000 y 74.000; VIX 21,15, S&P 500 −1,8 % en 5 sesiones, bono de 10 años en 4,95 %. Semáforo del día: ROJO.
