# Preregistro de la investigación cuantitativa (27/10/2026, antes de mirar resultados nuevos)

Base congelada: commit `0556636` (rama `claude/encargo-cloud-md-q0u3ex`). Todo el trabajo va en la rama local
`investigacion/quant-2026-10-27` (worktree `/home/user/trader-btc-investigacion`). No se toca la rutina ni se publica nada.

## 1. Por qué hace falta un periodo nuevo

El tramo 2024-2026 de BTC y todo ETH ya se miraron en las tareas 1 a 13 para decidir qué estrategias sobreviven.
Ya no son una prueba independiente: sirven para describir, no para demostrar. La única evidencia fuera de muestra
limpia que se puede conseguir hoy son **activos que nunca se miraron**, con las reglas exactamente como están.

## 2. Validación en activos nunca mirados (reglas fijas, sin ajustar nada)

- Activos, elegidos por liquidez antes de ver datos: **SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, ADAUSDT**
  (futuros USDⓈ-M de Binance, velas de 1 minuto de data.binance.vision con SHA-256).
- Reglas: las del sistema consolidado tal cual (`consolidacion/consolidado.py`), con la versión final de cada estrategia
  (P05b base, P11 base, P05c «todos 3 de 3», N9 base, N8 base). Ningún parámetro se toca.
- Costes: 0,05 % tomador / 0,02 % creador y el doble.
- Criterio fijado ahora: una estrategia «generaliza» si su media neta con comisión doble es positiva en al menos
  4 de los 5 activos nuevos **y** la media agregada de todas sus operaciones en esos activos es positiva con un
  intervalo de confianza del 90 % (bootstrap por bloques de meses) que no incluya el cero.
  Si no generaliza, su resultado en BTC se trata como posiblemente específico o fruto de la búsqueda.

## 3. Experimentos en BTC (y ETH como comprobación)

Partición cronológica para todo lo que elija algo:
- **entrenamiento** 2020-01 a 2022-12 · **validación** 2023-01 a 2023-12 · **prueba** 2024-01 a 2026-10
  (la prueba de BTC ya está contaminada, ver punto 1; se informa, pero la decisión se apoya en el punto 2).
- Walk-forward anclado: para cada año Y de 2022 a 2026, elegir con los años < Y y aplicar a Y.

Familias que se prueban (todas las variantes quedan en `registro_variantes.csv`, ganen o pierdan):
- D1 sensibilidad de parámetros: P05b k ∈ {0,3; 0,4; 0,5; 0,6; 0,7}, ventana del límite W ∈ {30, 60, 120} min, hora tope
  ∈ {19, 21, 23}; N9 ventana de rotura (07-13, 07-11, 07-16); P11/N8 stop ∈ {2, 3, 5 %, sin stop}.
- D2 salidas: P05b, P05c y N9 con (a) la salida actual, (b) sin stop, solo 23:59, (c) stop duro intraminuto en la referencia,
  (d) salida a las 4 h, (e) salida a las 8 h.
- D3 riesgo por operación 0,25 / 0,5 / 1 / 2 % con las restricciones reales del contado (mínimo 5 USDT, paso 0,00001 BTC,
  comisión cobrada en BTC) y, para separar efectos, con un capital sin restricciones.
- D4 frecuencia: el mecanismo de P05b (banda de ATR anclada a la apertura de la sesión, en el lado del contexto) en
  sesiones de 1, 2, 4, 8 y 24 h, para medir si más operaciones conservan la ventaja o solo suman costes.
- D5 cartera BTC + ETH con N8 y N9 (las únicas marcadas como robustas en ETH).

Regla de adopción (igual para todas): una variante solo se propone si mejora la media neta con comisión doble en
entrenamiento **y** en validación, no empeora la caída máxima en más de un 20 % relativo, su mejora no depende de un único
parámetro aislado (los vecinos también mejoran) y, en el walk-forward, lo elegido supera a la base en la mayoría de los años.
