# Aprobador de binarias · avance

Rama `claude/aprobador-binarias-2026-11-17`, salida de `binarias/plan-v7-2026-11-04` en 7429f90. La rutina constructora corre el 17/11/2026 a las 12:42 y a las 17:42 (hora de Colombia).

## Marca de trabajo

- Sesión de las 12:42: EN CURSO. Última marca: 17/11 12:55.
- Si usted es la corrida de las 17:42 y la última marca tiene menos de 40 minutos, la sesión de las 12:42 sigue trabajando: termine en una línea, sin escribir a Telegram y sin tocar la rama. Si tiene más, siga desde el primer paso sin marcar.

## Pasos

- [ ] 1. Leer el bloc, el nodo, el operador de Fable 5.2, el Centro y las reglas; revisar la llamada a Claude contra la documentación oficial.
- [ ] 2. Candado del operador: sin decisión COMPRAR vigente del nodo para ese mercado y sentido, no hay orden real (`operador/aprobacion.py` y tres líneas en `ejecutor.py`). Pruebas con el simulador, antes y después.
- [ ] 3. Nodo: lectura incremental, mercado y ventana en cada punto, vector del operador en el paquete, llamada a Claude revisada (salida estructurada, caché, costo), fallas cerradas. Pruebas, también contra un servidor falso de la API.
- [ ] 4. `CONTEXTO-NODO.md` con lo esencial del bloc y de las reglas de Fable.
- [ ] 5. Medición en papel de la combinación frente a cada fuente sola (`aprobador/medir_combinacion.py`).
- [ ] 6. Costos medidos: una revisión del nodo y una consulta a Claude (al día y al mes).
- [ ] 7. `PLAN-APROBADOR.md`: reglas de Fable y cómo se respetan, opinión con cifras, batería y calor, lo que falta del dueño.
- [ ] 8. Pasos exactos para que la sesión del PC lo suba al teléfono; informe a Telegram; `TERMINADO.md`.

## Hallazgos (anotados sin corregir el código de Fable 5.2)

1. En la rama no están `operador/prueba_operador.py` ni `operador/llevar_operador.py`, que el plan de Fable nombra (sección 9). Sus pruebas propias no se pueden correr desde aquí; se usan el simulador de Fable (`operador/simulador.py`, que sí está) y pruebas nuevas.
2. `operador/nucleo.py` suma flotantes con `sum()` (rasgos y `sigma60`). Desde Python 3.12 `sum()` de flotantes compensa el redondeo, así que el teléfono (3.14) y un equipo con 3.11 pueden diferir en la última cifra (del orden de 1e-16). No cambia decisiones ni la paridad de 1e-9 de su criterio 1, pero una auditoría bit a bit entre equipos con versiones distintas podría ver diferencias mínimas. No se tocó.
