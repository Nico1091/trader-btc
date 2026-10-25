# Consolidación del agente trader de BTC (sesión en la nube, 25/10/2026)

Informe del encargo `ENCARGO-CLOUD.md`. Solo papel: ni dinero real, ni claves, ni cuentas, ni brokers.

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

_(Las tareas 1 a 7 se van añadiendo abajo a medida que se terminan.)_
