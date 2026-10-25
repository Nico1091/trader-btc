# Metaprompt: cómo construir el prompt de la sesión en la nube

Este documento no lo ejecuta la IA. Son las reglas con las que se escribió `ENCARGO-CLOUD.md`, para que cualquier versión futura del encargo se arme igual.

## 1. Qué debe lograr el prompt
Que un modelo que llega sin memoria (otra sesión de Claude en una máquina de Anthropic) entienda todo el contexto de trading de Nicolás, no repita lo ya medido, y entregue mejoras verificadas del agente trader en papel.

## 2. Análisis previo (lo que el redactor debe resolver antes de escribir)
- **Quién lee:** un modelo capaz, sin historial, con acceso al repositorio, a internet (data.binance.vision, Coinbase, Kraken sí; API de Binance no, da 451) y quizá sin Gmail.
- **Qué sabe ya el repositorio:** `contexto/` (curso, conclusiones, registro, notas) y el prompt de la rutina.
- **Riesgos de malinterpretación:**
  1. Tomar «arbitraje-cero-gas» como el proyecto actual.
  2. Prometer tres operaciones diarias aunque lo medido diga que la comisión se las come.
  3. Tocar dinero real.
  4. Usar patrones de vela como señal de entrada, cuando ya se midió que solo sirven como veto.
  5. Fiarse de resultados de 12 meses o sin comisión.
- **Qué pidió Nicolás, en sus palabras convertidas a tareas:** revisar el agente, leer cada vela y su significado, mejorar y consolidar estrategias, crear nuevas para presupuesto bajo, 40.000 pesos diarios sin pérdidas, revisar operaciones en papel, analizar la semana del lunes 19 al viernes 23/10 con aciertos, una prueba propia el lunes o martes, informe por Telegram.

## 3. Estructura obligatoria del prompt
1. **Rol y límite** en dos líneas: quién es y qué nunca hace.
2. **Paso 0, lectura:** orden exacto de los archivos de `contexto/` y un resumen de lo entendido antes de actuar.
3. **Tareas numeradas**, cada una con su entregable concreto (archivo, tabla o cifra).
4. **Reglas de evidencia:** datos reales, comisión de 0,05 %/lado y prueba con el doble, comparación contra el azar, separar dentro y fuera de muestra, decir el tamaño de la muestra.
5. **Restricciones de Nicolás:** solo papel, nada de claves, cuentas ni brokers mexicanos, nadie más ve sus operaciones.
6. **Entrega:** qué archivo escribir, qué mandar a Telegram y con qué prefijo, y en qué orden (entregar primero, investigar después).
7. **Criterio de honestidad:** si algo no da, decirlo con cifras; no forzar operaciones para cumplir una meta.

## 4. Estilo
Español claro, frases cortas, verbos en imperativo. Sin relleno ni adornos. Cada tarea medible. Nada que el modelo deba adivinar.

## 5. Comprobación final antes de publicar
- ¿Cubre cada punto que pidió Nicolás? 
- ¿Neutraliza los cinco riesgos?
- ¿Cada tarea tiene entregable?
- ¿Se puede cumplir sin acceso a su PC?
