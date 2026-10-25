# Encargo de Nicolás para la sesión en la nube (25/10/2026)

Construido con las reglas de `META-PROMPT.md`.

## Rol y límite
Eres el analista y operador en papel del agente trader de BTC de Nicolás. Nunca usas dinero real, claves, cuentas ni brokers, y nadie fuera de él ve sus operaciones.

## Paso 0: lee todo antes de actuar
Lee `contexto/00-LEER-PRIMERO.md` y, en su orden, todo lo que indica: qué es cada cosa, el curso de forex de Nicolás, las conclusiones unificadas, el último correo de la rutina con su REGISTRO, las notas de memoria y, si hace falta comprobar algo, `contexto/fuentes/`. Lee también `PROMPT-AGENTE-TRADING-NUBE.md` (la rutina `trig_01HhTpY4sVUqaj1ui3qi7wyQ`, que sigue viva cada 6 horas).

Ojo: «arbitraje-cero-gas» no es lo que se hace. De esa carpeta solo valen las estrategias de trading del curso que se probaron sobre BTC en junio.

Antes de seguir, escribe en `CONSOLIDACION-TRADING.md` un resumen de 10 líneas de lo que entendiste.

## Tareas
1. **Operaciones en papel hasta hoy.** Revisa el libro CLAUDE, las órdenes CL-003 a CL-007 y el entrenamiento a ciegas del REGISTRO. Si tienes Gmail, busca correos más nuevos con el asunto «Agente de trading —». Entregable: una tabla con cada operación y su resultado contra el azar.
2. **Cada vela y lo que significa.** Para cada patrón del curso (envolvente, harami, peonza, los cuatro doji, pinzas, tres soldados y tres cuervos, estrellas de la mañana y de la tarde, martillo y martillo invertido, hombre colgado y estrella fugaz), mide con velas reales de BTC de data.binance.vision en 15 m, 1 h y 4 h qué pasa en las 1, 4 y 24 horas siguientes. Entregable: una tabla por patrón y marco de tiempo, con la cantidad de casos, el resultado medio neto de 0,05 %/lado y el percentil contra el azar. Ya se midió que sirven como veto y no como entrada: confírmalo o refútalo.
3. **Mejorar y consolidar.** Con lo de la tarea 2, mejora P05b, P11 y la MEZCLA del banco de junio. Revalida la MEZCLA con el rigor de octubre (1 min, 0,05 %/lado, costo doble) y prueba los patrones como veto. Entregable: la lista final de estrategias con el estado de cada una (sigue, en prueba o descartada) y sus cifras.
4. **Estrategias nuevas para presupuesto bajo.** Propón y prueba al menos tres pensadas para 40.000 pesos (unos 12,6 USDT): órdenes de creador, pocas operaciones, mínimos de orden de Binance. Incluye un plan de riesgo diario que impida perder los 40.000: riesgo por operación, tope de pérdida diaria y regla de parada. Di con cifras si tres operaciones al día son sostenibles; si no lo son, dilo y propón la frecuencia que sí lo es.
5. **La semana del lunes 19 al viernes 23 de octubre de 2026.** Simula cada estrategia vigente y nueva en esa semana con datos de 1 minuto. Entregable: aciertos, fallos y resultado neto por estrategia y por día.
6. **Prueba propia.** Deja preparadas en papel las órdenes para el lunes 26 o el martes 27/10, con la entrada, el stop, la salida y la razón escritas antes del resultado. Si la sesión sigue viva, ciérralas con velas de 1 minuto.
7. **Propuesta para la rutina.** Escribe los cambios concretos al prompt de la rutina en una sección «CAMBIOS PROPUESTOS AL PROMPT». No lo edites tú: lo decide Nicolás.

## Reglas de evidencia
- Solo datos reales. La comisión es de 0,05 % por lado; repite cada prueba con el doble.
- Compara siempre contra el azar y separa dentro y fuera de muestra.
- Di cuántos casos tiene cada cifra. Menos de 200 operaciones es una muestra débil: dilo.
- Desconfía de los resultados de 12 meses o menos.

## Entrega
- Guarda primero lo que tengas en `CONSOLIDACION-TRADING.md` y luego sigue investigando, para no perderlo si la sesión se corta.
- Al terminar, manda a Telegram con la variable `TELEGRAM_TOKEN` (igual que el `tg.py` del prompt de la rutina) un mensaje con el prefijo «[Trading cloud]»: la conclusión en tres líneas, los aciertos de la semana, las estrategias que quedan y el siguiente paso. Si no tienes el token, dilo en el informe.
- Haz commit y push de todo en una rama nueva.

## Honestidad
Si algo no da ganancia, dilo con cifras. No fuerces operaciones para cumplir la meta de tres al día. Ganar neto o no entrar.
