# Plan total de las binarias · BTC/USDT (v6, congruente)

3 de noviembre de 2026, 22:40 (hora de Colombia). Reemplaza al PLAN-v5.md y manda sobre todo lo anterior. La evidencia y la auditoría de congruencia están en `INFORME-TOTAL.md`.

## 1. La lógica única

A 10 minutos, BTC tiende a devolverse después de estirarse. La ventaja es pequeña, cambia con el tiempo y depende de entrar rápido y del pago. Por eso:
1. Solo se apuesta a la devolución, nunca a la continuación.
2. En real solo se opera los días en que la estrategia viene funcionando («corona, corona, corona»): semáforo VERDE. La primera pérdida apaga el real hasta el día siguiente. Sin apalancamiento.
3. Nada entra ni sale sin el protocolo de la sección 6.

## 2. Reglas que no se discuten

- Solo Contratos de Evento de Binance, solo BTCUSDT. «Trading» siempre significa esto.
- Papel hasta su orden expresa. En real la apuesta la toca él (Binance prohíbe bots). Sin apalancamiento en real; en papel solo como estudio de futuros.
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

## 5. El semáforo (cómo se decide el real)

- A las 0:00 de cada día: VERDE si las últimas 100 apuestas de papel del núcleo, medidas entrando 60 s tarde, aciertan 58 % o más. Si no, ROJO y ese día solo papel.
- En VERDE, cada señal llega como «REAL: toque ahora BTC SUBE/BAJA a 10 min». Tocar en segundos: cada minuto de demora cuesta cerca de 1,7 puntos. 5 USDT, sin apalancamiento.
- La primera pérdida en real apaga el modo real hasta el día siguiente, y se le avisa.
- Lo que hace y lo que no: no adivina los días buenos (la racha no se deja ver hacia adelante); los aprovecha cuando ya vienen y limita lo que se arriesga en los malos. En 2021-2026: 57,4 % con parada en la primera pérdida frente a 56,4 % de días al azar.
- Para la gente: cuando él quiera, el mismo aviso del semáforo (VERDE/ROJO y las señales REAL) puede ir a un canal de Telegram para sus seguidores. Necesita que él cree el canal y ponga al bot como administrador.

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
- **P7 · Semáforo en vivo.** A los 30 días, comparar el papel de los días verdes con el de los rojos; se mantiene si los verdes superan a los rojos por 1 punto o más. Si no, el real pasa a depender solo de la sección 8.

Probados y descartados hoy: E1 (sumar impulso y anomalía a la ruptura diluye: 53,1 %), el HMM de la racha como semáforo (sin efecto), y por incongruentes E3, E10 y E11 del plan v5.

## 8. Criterios para el dinero real (todos, y su orden expresa)

1. Pago real medido y equilibrio recalculado.
2. Núcleo con Wilson del último año sobre ese equilibrio, entrando con su demora real.
3. Paridad de 7 días entre la caja y el banco.
4. 300 o más apuestas de papel del núcleo en la caja, 1 punto o más sobre el equilibrio.
5. Semáforo en VERDE ese día; parada en la primera pérdida.
6. Capital: con 100.000 COP el mínimo de 5 USDT es el 15,9 % del saldo; se le dice una vez y decide él.

## 9. Cómo no se olvida

Enganche de inicio de Claude con el SIGUIENTE PASO del bloc; encargo en `n8n\encargos\encargo-binarias-plan-v5.md` (apunta a este plan); bloc del Escritorio con su sección AL FRENTE; recordatorio en su teléfono.
