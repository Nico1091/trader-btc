# Verificador de la llave de Binance para la caja de binarias · propuesta del 20/11/2026

## Rama y carpeta

Esta entrega va en la rama `claude/proyectos-2026-11-17-f`, creada desde `master`. El nombre pedido, `claude/proyectos-2026-11-17`, ya existe en el repositorio con el evaluador del 17/11 de otra sesión, y no se ha sobrescrito. Las variantes `-b` a `-e` y `claude/proyectos-2026-11-18`, `-regla70`, `claude/proyectos-2026-11-19` y `-b` también existen. Sin PR y sin unir a `master`.

## Qué es

Un programa que lee las banderas de una llave de Binance (la respuesta de `GET /sapi/v1/account/apiRestrictions`) y dice si la llave cumple la regla de la caja de binarias:

- Lectura activada y restricción por IP activada.
- Sin retiros por API, sin transferencias internas ni universales, sin futuros, sin margen, sin spot y margen, sin opciones, sin margen de cartera y sin operar por FIX.
- La IP de la caja está en la lista de IP que usted escribió en Binance.
- La Predicción la confirma usted a mano (ver abajo por qué).

El veredicto es `APTA`, `PENDIENTE` (todo lo que se puede leer cumple, falta confirmar la Predicción) o `NO APTA`. Cualquier campo que falte cuenta como no apta: no se da por buena una llave que no se puede leer entera.

## Por qué esta y no otra

Las nueve propuestas anteriores sobre binarias miden la ventaja, el armado, la compuerta de compra o el dinero en riesgo. Ninguna tiene a la vista las apuestas reales con precio real (están en el teléfono), y ninguna demuestra ventaja con ese precio. Añadir otro indicador de rendimiento no aporta nada nuevo.

Lo que sí tiene riesgo de pérdida total en la cuenta de binarias es la llave. Una llave con retiros, con futuros o sin restricción de IP expone todo el saldo. El bloc deja pendiente, a decisión suya, comprobar esas banderas, y el error −2015 por cambio de IP ya dejó la llave sin funcionar. Este programa convierte esa comprobación en un resultado verificable y repetible.

No mejora el rendimiento de las binarias. Protege la cuenta.

## Cómo se usa

1. Obtenga la respuesta de `GET /sapi/v1/account/apiRestrictions` desde la caja, con su propia herramienta y su llave. Guárdela en un archivo JSON. Esa respuesta no trae la llave, pero no la pegue en ningún chat.
2. Ejecute:

   ```
   python verificador_llave.py restricciones.json --ip-caja IP_DE_LA_CAJA_HOY --ip-lista IP1,IP2
   ```

   `--ip-caja` es la IP pública de salida de la caja en este momento. `--ip-lista` son las IP que usted escribió en la lista de la llave en Binance, separadas por coma.
3. Revise la app de Binance: que la llave tenga Predicción y nada más. Si lo confirma, vuelva a correr con `--confirmo-prediccion`.
4. Opcional: `--json informe.json` guarda el resultado sin ningún valor de la llave ni del archivo.

Códigos de salida: `0` APTA, `1` PENDIENTE, `2` NO APTA, `3` entrada mala (archivo ilegible, campo con valor que no es verdadero o falso, IP no válida, o un texto largo que podría ser una llave; en ese caso se detiene sin mostrarlo).

Archivos:

| Archivo | Para qué |
|---|---|
| `verificador_llave.py` | El verificador. Solo biblioteca estándar, Python 3.11 o superior. |
| `prueba_verificador_llave.py` | 22 pruebas. Los textos de prueba son inventados y se arman en tiempo de ejecución. |
| `ejemplo_restricciones_SINTETICO.json` | Banderas inventadas, sin ninguna llave. Son las de una llave bien configurada. |
| `salida_pruebas.txt` | Salida real de las 22 pruebas. |
| `salida_ejemplo.txt` | Salidas reales en cuatro casos: pendiente, apta, IP fuera de la lista y texto largo. |

## Qué se probó

- Las 22 pruebas pasan (`salida_pruebas.txt`): el caso bueno en las dos variantes, cada bandera prohibida por separado, lectura apagada, IP sin restricción, IP de la caja fuera de la lista, lista con varias IP, IP inválida, red con barra, campo que falta, valor que no es booleano, JSON roto o que no es un objeto, archivo inexistente, texto largo (no se muestra), informe JSON sin valores del archivo, y coherencia de las listas de banderas.
- Los nombres de las banderas se comprobaron contra la página oficial de Binance (`developers.binance.com/legacy-docs/wallet/account/api-key-permission`). Una prueba verifica que cada nombre usado figura en la lista oficial.
- La línea de comandos corre y devuelve los códigos de salida indicados.

## Qué no se probó

- **No se conectó a Binance.** No se usó ninguna llave ni IP real. Los nombres de campo salen de la documentación, no de una respuesta real. Si la respuesta real trae un campo distinto, el programa dirá que falta y no dará la llave por buena. Es el comportamiento deseado, pero conviene confirmarlo con la primera respuesta real.
- **La Predicción no se verifica.** El endpoint no la muestra. Por eso siempre queda `PENDIENTE` hasta que usted la confirme a mano.
- **La lista de IP no la lee el programa.** Usted la escribe en `--ip-lista`. El programa comprueba que la IP de la caja esté en lo que usted escribió, no en la lista real de Binance. Si la lista real es distinta de lo escrito, el programa no lo detecta.
- **La IP de la caja la escribe usted** en `--ip-caja`. El programa no la mide.
- **No vigila.** Es una foto del momento. Un cambio posterior de IP o de permisos no se detecta hasta que se vuelva a correr.
- **`APTA` no dice nada de ventaja.** Solo dice que la llave tiene los permisos y la IP correctos.

## Lo que solo puede hacer usted

- Obtener la respuesta de `apiRestrictions` con su llave, en la caja.
- Confirmar a mano que la llave solo tiene Predicción, en la app de Binance.
- Decidir si conviene aplicar esta comprobación antes de cada armado del operador. Esta propuesta no toca `binarias/operador/` ni `binarias/aprobador/`, y no se conecta a ellos.
