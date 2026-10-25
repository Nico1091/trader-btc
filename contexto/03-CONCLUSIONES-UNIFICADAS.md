# Conclusiones unificadas (hasta el 25/10/2026)

Todo lo medido con datos reales de Binance, de junio a hoy. Cifras con comisión salvo que se diga lo contrario. Las fuentes están entre paréntesis.

## 1. El marco de tiempo pesa más que la estrategia

- A segundos y minutos BTC es casi azar (AUC 0,51-0,56). Operar seguido pierde en todo: contado −17,8 %, BTC/FDUSD −39,6 %, futuros −37,6 % en un mes con 40.000 pesos. La causa es la comisión (0,04-0,20 % por ciclo) frente a movimientos de 0,05-0,14 % (agente del PC, octubre).
- En 1 hora, las estrategias del curso sí muestran ventaja (banco de junio).

## 2. Las estrategias del curso sobre BTC en 1 hora, 24 meses (junio)

| Estrategia | Operaciones | Acierto | Resultado | Con comisión doble |
|---|---|---|---|---|
| MEZCLA: retroceso largo en tendencia + corto en techo extremo (range_pos ≥ 0,9) | 864 | 53,6 % | +248 % | +239 % |
| Corto en techo (reversión) | 275 | 67 % | +173 % | — |
| Retroceso largo con ganancia en 2R (contado) | 308 | 47 % | +112 % | +140 % |
| 50 SMA + precio | 64 | 58-60 % | +30 % | muestra corta: solo sirve de filtro |
| Fibonacci zona dorada estricta | 268 | 44 % | −46 % | descartada |
| Rupturas | <200 | negativo | — | descartada |

Configuración de la MEZCLA: 1 h, stop 3 %, horizonte 24 h, ganancia 2R, equilibrio en 1R. Necesita futuros para los cortos; en contado solo queda el largo. Advertencia: el banco de octubre (10 estrategias, 25 meses de 1 min, 0,05 %/lado) no encontró ninguna que gane neta; hay que revalidar la MEZCLA con el mismo rigor antes de fiarse.

## 3. Lecciones sobre velas y patrones

- Los patrones de vela **no sirven como señal de entrada**: sumados como señales diluyen la calidad (de +47 % a +21 %) y como variables del modelo no mejoran (+30 %).
- **Sí sirven como veto**: no operar cuando los patrones contradicen la señal. Nunca empeora y sube un poco el acierto.
- Acierto alto no es rentabilidad: con pérdidas grandes y ganancias chicas se pierde. El stop fijo del 3 % corrigió eso.
- Los resultados de 12 meses engañan: ETH daba +94 % en 12 meses y casi cero en 24.

## 4. La IA como quien decide

- En junio, con poco contexto, la IA restaba (frenaba operaciones buenas). Con el manual completo y los datos reales pasó a sumar (+11,4 % frente a +2,1 % de operar todo, en 120 señales).
- En octubre, la rutina de la nube a ciegas: 20 operaciones, 11 aciertos, +7,63 % frente a −0,63 % del azar. Su confianza alta rinde menos que la media: no subir el tamaño por confianza (R13).
- Filtrar P05b por la tendencia resta (R14): se toma entera o no se toma.

## 5. Candidatas vivas (rutina de la nube)

- **P11, largo del lunes UTC:** compra a las 00:00 UTC, stop 3 %, cierre 23:59. De 2020 a 2026: 355 operaciones, +109 % neto, +73,5 % con comisión doble; tras su publicación, 38 operaciones y +12 %. Primera en papel el 26/10.
- **P05b (E09, ATR de Concretum con orden de creador):** candidata principal pero frágil: con comisión doble −13,2 %, caída del 22 % frente a un tope del 15 %.
- Descartadas: P10 (horquilla en compresión) y el filtro propio sobre P05b.

## 6. Lo que esto implica para la meta de Nicolás

- **Tres operaciones al día con 40.000 pesos no se sostienen en BTC con lo medido.** Las ventajas que existen son de 1 hora o de un día por semana, y forzar más operaciones pierde por comisión.
- Con 40.000 pesos (unos 12,6 USDT), los mínimos de orden y la comisión pesan mucho más que en una cuenta grande: priorizar órdenes de creador (0,02-0,03 %/lado) y pocas operaciones buenas.
- «No perder» se traduce en reglas: riesgo del 1-1,5 % por operación, pérdida diaria máxima fijada, y no operar cuando no hay ventaja medida.
- Para el dinero real sigue vigente el criterio propuesto: 200 operaciones de prueba y 60 en papel en 4 semanas, neto con costo real y no negativo con el doble, caída ≤15 %, 100 decisiones a ciegas y el sí de Nicolás.
