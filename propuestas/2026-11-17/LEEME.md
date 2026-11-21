# Prueba del ejecutor de binarias contra un Binance simulado · propuesta del 21/11/2026

## Rama y carpeta

Esta entrega va en la rama `claude/proyectos-2026-11-17-g`, creada desde `master`, sin PR y sin unir.

El nombre pedido, `claude/proyectos-2026-11-17`, ya existe en el repositorio con el trabajo de la entrega del 18/11, y no se ha sobrescrito. Por la misma razón se usa el sufijo `-g`, la siguiente letra libre de esa serie. La carpeta sí es la indicada en el encargo: `propuestas/2026-11-17/`.

## Qué es

Un programa que ejecuta el código real del ejecutor del operador de binarias (`binarias/operador/ejecutor.py`, la parte que toca dinero) contra un Binance simulado que vive en memoria. Comprueba 22 reglas de seguridad que el propio código dice cumplir: el archivo `ARMADO`, el archivo `PARAR`, la llave restringida, el freno del 16 % del saldo, el tope de 20 órdenes al día, el máximo de dos envíos por mercado, la cotización frente al precio visto por la IA, las órdenes sin respuesta, el −2015 y el cierre de la liquidación.

No hay red, no hay llaves, no hay saldo. Nada de esto puede enviar una orden ni gastar un centavo.

## Por qué esta y no otra

- Las doce entregas anteriores de esta serie miden si las binarias dan ventaja. Todas coinciden: a precio real, ninguna fuente gana dinero.
- Ninguna de ellas prueba el camino que compra con dinero real. Ese camino es el único que puede causar una pérdida que no se recupera.
- El plan del operador (`binarias/operador/PLAN-AUTOMATICO.md`, paso 8 y criterio 3) pide esta prueba y sigue sin marcar.
- El escáner de secretos del 21/11 ya cubre el riesgo del repositorio público. No se repite.

## Cómo se usa

Requisitos: Python 3, sin dependencias nuevas. Se necesita el operador tal como estaba en el commit `29ecb39` de la rama `binarias/plan-v7-2026-11-04`, sin modificarlo:

```
git archive 29ecb39 binarias/operador | tar -x -C /ruta/a/op-src
python -X utf8 prueba_ejecutor_simulado.py --operador /ruta/a/op-src/binarias/operador
```

La prueba no escribe en la carpeta del operador. Usa un directorio temporal para sus datos. Sale con código 0 si todo se cumple y con 1 si algún escenario falla.

Para ver el parche propuesto:

```
git apply --check parche_ejecutor_llave_menos2015.diff   # desde la raíz de un checkout que tenga binarias/operador
```

El parche no está aplicado en el repositorio. Está en `binarias/operador/`, carpeta que esta entrega no modifica.

## Resultados (salida completa en `salida_pruebas.txt`)

- Operador tal como está: 19 de 22 escenarios cumplen. Fallan 3: E17, E18 y E19.
- Operador con el parche propuesto: 21 de 22 cumplen. Falla E17, que el parche no corrige.

## Hallazgos

1. **El −2015 no llega al operador desde la compra (E18 y E19).** `ejecutar_ia` captura el error de `cotizar` y el de `ordenar` y los convierte en una nota. El operador tiene la reacción prevista para −2015 (pasar al estado 1 y avisar), pero solo la activa si la excepción sube hasta él. Consecuencias: si la llave deja de pasar (por ejemplo, porque cambió la IP de la casa), el intento se repite cada 15 segundos sin aviso al dueño, y una orden rechazada por −2015 cuenta como rechazo normal. No se pierde dinero en estos casos, porque Binance no ejecutó nada, pero el operador queda engañado sobre el estado de la llave. Severidad: media, por la falta de aviso. **Corrección propuesta:** `parche_ejecutor_llave_menos2015.diff`, de 3 cambios pequeños en `ejecutor.py`. Probada en una copia de trabajo: E18 y E19 pasan y los demás escenarios no cambian.

2. **Una compra ajena puede adoptarse como propia (E17).** Si la respuesta al envío se pierde (estado `DUDOSA`) y el dueño compra a mano en el mismo mercado y en la misma cuenta dentro de la ventana de búsqueda, `_aclarar` toma esa orden como la del operador. Se cuenta en el freno del día y en el registro, con el importe equivocado. No se gasta dinero de más, pero el registro y el freno quedan mal. Severidad: baja, porque exige coincidencia en el tiempo. **Corrección pendiente:** comparar el importe y la cotización, lo que exige confirmar con una consulta real qué campos devuelve la lista de órdenes de Binance. No se propone aquí una corrección a ciegas.

## Qué no se probó

- **Binance real.** El simulado sigue la documentación interna del ejecutor. Los campos, los códigos de error y los tiempos reales pueden ser distintos. La prueba verifica la coherencia interna del ejecutor, no que Binance responda igual.
- **El cobro.** `cobrar` y `estado_cobro` no se llaman en la prueba; si el ejecutor los llamara, la prueba fallaría con un aviso explícito. El cobro real sigue sin probar, como indica el plan.
- **El nodo, el aprobador, la llave y la caja Android.** No se tocaron ni se leyeron sus secretos.
- **La parte de liquidación con ganador real.** El ganador se fija a mano en el simulado. Solo se probó el caso de acertar, con el cálculo del ejecutor.
- **El parche sobre la caja.** Se probó con la suite, no en un equipo real.

## Lo que solo puede hacer el dueño

1. Decidir si se aplica `parche_ejecutor_llave_menos2015.diff` a `binarias/operador/ejecutor.py`. Esta entrega no lo aplica.
2. Confirmar con una consulta de solo lectura, sin fondos y con una llave que no pueda operar, qué campos devuelve la lista de órdenes de la billetera de predicción. Según el plan, la llave de la caja todavía no existe. Con esa respuesta se puede corregir el hallazgo 2.
3. Nada de esta entrega envía órdenes, toca fondos ni usa llaves.

## Archivos

- `prueba_ejecutor_simulado.py`: la prueba, 22 escenarios.
- `salida_pruebas.txt`: salida completa del operador original y del operador con el parche.
- `parche_ejecutor_llave_menos2015.diff`: el cambio propuesto para `ejecutor.py`.
- `LEEME.md`: este archivo.
