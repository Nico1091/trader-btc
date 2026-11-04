# Prompt de revisión

Se aplica a `PLAN.md`, a `PROMPT-OPERADOR.md`, al código y a los resultados, cada vez que cambien. Quien revisa busca fallos, no virtudes: cada punto se responde con una prueba concreta (una línea de código, una cifra, un archivo) y no con una impresión. Lo que no se pueda comprobar se anota como «sin comprobar». Los hallazgos y lo que se cambió por cada uno van a `REVISION.md`.

## 1. Información del futuro

- ¿Alguna decisión usa un dato posterior al momento en que él tocaría la app? Revisar velas sin cerrar, el contexto diario del mismo día, medias o normalizaciones calculadas con todo el periodo, y umbrales o filtros elegidos con el mes que se evalúa.
- ¿La selección del mes M usa solo datos que terminan antes del primer minuto de M?
- ¿El modelo se normaliza solo con su ventana de ajuste?

## 2. Elegir mirando el resultado

- ¿Cuántos procedimientos se miraron fuera de muestra? ¿Se corrigió el nivel de confianza por ese número?
- ¿Se cambió algún parámetro (ventana, número de elegidos, umbral, plazo) después de ver un resultado a ciegas? Si pasó, ese resultado deja de contar como ciego.
- ¿El informe separa lo elegido mirando el pasado de lo probado en días que no se usaron para elegir?

## 3. Precio y momento de entrada

- ¿La prueba entra al precio que vería él al tocar, con el retraso real de la cadena ficha, decisión, aviso y toque?
- ¿El vencimiento se mide al mismo plazo exacto que usa Binance?
- ¿Las velas son de futuros mientras Binance liquida con otro precio? Medir la diferencia o anotarla como riesgo.

## 4. Cuentas

- Pago, empates y mínimo de 5 USDT: ¿están modelados como en la app?
- ¿La apuesta es el 16 % del saldo del momento y nunca menos que el mínimo? ¿Qué pasa cuando el 16 % no alcanza el mínimo?
- ¿Una apuesta abierta a la vez y el tope diario se respetan igual en la prueba y en vivo?

## 5. Tamaño y dependencia de la muestra

- ¿Hay apuestas suficientes para la conclusión que se da? Con 57,8 % frente a 54,1 % hacen falta unas 1.100.
- ¿Las apuestas se solapan en el tiempo y se cuentan como independientes?
- ¿El resultado depende de pocos días extraordinarios? Mirarlo sin los 5 mejores días.

## 6. Regímenes

- Por años, por mitades, alcista frente a bajista, BTC frente a ETH.
- Comparación con apostar siempre arriba (la deriva de BTC) y con el azar a las mismas horas.

## 7. Paridad entre prueba y vivo

- ¿El centinela calcula exactamente las mismas señales que el banco con las mismas velas? Comprobarlo con datos reales, no por lectura del código.
- ¿La elección mensual en vivo usa el mismo código que la prueba?

## 8. Operación

- PC apagado, red caída, Telegram caído, operador ausente o tardío, dos centinelas a la vez, reloj del PC desfasado: ¿qué pasa en cada caso y dónde queda anotado?
- ¿El error de «Acceso denegado» al guardar puede perder una apuesta?
- ¿Cuánto gasta el operador por día (turnos y tamaño) y cómo se mantiene bajo?

## 9. Reglas de Nicolás

- 16 % del saldo, sin stop, desde 100.000 COP, sin proponer el 2 %; binarias por tiempo, no trading común; solo Binance; papel; privacidad; sin subagentes; sin mirar la pantalla; sin instalar nada; cifras en pesos y hora de Colombia; prioridad baja en el equipo.
- Redacción del informe: registro formal, sin justificaciones largas, «N apuestas al día, todos los días», separando lo elegido de lo probado a ciegas.

## 10. Veredicto

- ¿Los criterios de consolidación se aplicaron tal como quedaron escritos antes de ver los resultados?
- Si el veredicto es «consolidado», ¿alguna de las preguntas anteriores quedó «sin comprobar»? En ese caso, el veredicto no puede ser «consolidado».
