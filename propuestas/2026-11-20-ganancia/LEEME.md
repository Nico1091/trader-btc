# Medidor de ganancia por apuesta de las binarias · propuesta del 20/11/2026

## Qué es

Un programa que responde a una sola pregunta: **¿cada estrategia gana dinero, medido en USDT por apuesta, con el precio que realmente se pagó y con el ganador oficial?**

No pregunta «¿acierta más del 72 %?». Pregunta cuánto deja cada apuesta. Usa solo la biblioteca estándar de Python (3.8 o superior). No se conecta a Binance, no envía órdenes, no lee la caja ni el teléfono, no toca `binarias/operador/` ni `binarias/aprobador/` y no escribe nada salvo el JSON que se pida con `--json`.

## Por qué esta y no otra

- Las reglas que arman y compran hoy miden **acierto**: 18 de 25 para armar, 19 de 25 con ganancia para que la IA reciba un punto. El acierto no dice dinero cuando el precio cambia de una apuesta a otra. Con un precio de 0,80 el equilibrio está en 81,6 %: un acierto de 72 % pierde 0,118 USDT por cada USDT apostado, aunque parezca alto. La propuesta de la regla del 70 % (18/11) ya midió que 18 de 25 arma por azar en casi todos los periodos de 30 días.
- El evaluador de ventaja del 17/11 compara el acierto con un equilibrio medio. Este programa usa el precio **de cada apuesta** y la ganancia real de cada una, sin promediar el precio antes.
- Es la pieza que falta entre las propuestas anteriores: ninguna decide con dinero, que es lo que el dueño necesita para decidir si una estrategia merece dinero real.

## Criterio (fijado antes de ver ningún registro real)

- Convención del bloc: al comprar un lado a precio `p` con 1 USDT, si acierta se cobra `0,98 / p`; si falla se pierde 1 USDT. Por apuesta: `r = 0,98/p − 1` si acierta, `r = −1` si falla. El neto por USDT es la media de `r`.
- Por cada estrategia se calculan dos límites unilaterales de la media de `r`: uno normal y uno bootstrap (2.000 remuestras, semilla fija). El nivel de error se divide entre el número de estrategias (corrección de Bonferroni): `alfa / k`, con `alfa = 0,05` por defecto.
- **GANA DINERO (demostrado):** los dos límites inferiores son mayores que 0 y hay al menos 100 apuestas.
- **PIERDE DINERO (demostrado):** los dos límites superiores son menores que 0.
- **NO DEMOSTRADO:** cualquier otro caso. Es lo que debe pasar mientras no haya prueba.
- **MUESTRA INSUFICIENTE:** menos de 100 apuestas (mínimo configurable, nunca menos de 2).
- Suposición que no se cumple del todo: las apuestas se tratan como independientes. Varias estrategias que compran el mismo mercado en la misma ventana no son independientes, y la corrección de Bonferroni no lo corrige. Con varias estrategias en una misma ventana, la prueba es **optimista**.

## Archivos

| Archivo | Para qué |
|---|---|
| `medidor_ganancia.py` | El medidor. Se usa desde la línea de comandos. |
| `prueba_medidor_ganancia.py` | 14 pruebas automáticas. Con `--generar` escribe el ejemplo sintético. |
| `ejemplo_SINTETICO.csv` | Registro **inventado** de 2.260 apuestas en cinco estrategias, con precios y aciertos fijados. Sirve para ver que el medidor decide bien. |
| `salida_ejemplo.txt`, `salida_ejemplo.json` | Salida real de ejecutar el medidor sobre ese ejemplo. |

## Cómo se usa

1. Prepare un registro con una fila por apuesta resuelta: `estrategia`, `precio` (el precio pagado por el lado comprado, entre 0,01 y 0,99, en el minuto de entrada) y `acierto` (1/0, sí/no o true/false). Acepta CSV (también con coma decimal) o JSONL. Las demás columnas se ignoran.
2. Ejecute:

   ```
   python3 medidor_ganancia.py --registro registro.csv
   python3 medidor_ganancia.py --registro registro.jsonl --minimo 100 --alfa 0.05 --json salida.json
   python3 prueba_medidor_ganancia.py
   ```

3. Las filas malas no se descartan en silencio: se cuentan y se muestran las cinco primeras con su número de línea.

## Lo que se probó

- **14 pruebas, todas bien** (`python3 prueba_medidor_ganancia.py`): la convención de pago (acierto a 0,46 da 1,1304 por USDT; falla da −1), el equilibrio a precio fijo (0,80 da 81,6 %), el neto con apuesta de 2 USDT, la decisión de 18 de 25 a precio 0,80 (muestra insuficiente), 720 de 1.000 a precio 0,80 (pierde demostrado), 125 de 500 a precio 0,20 (gana demostrado), la corrección por 1.000 estrategias (la misma muestra deja de demostrar), todas perdidas, el orden de los límites, la lectura de CSV con coma decimal y sí/no, la lectura de JSONL con booleanos, el conteo de filas malas y la línea de comandos sobre el ejemplo.
- **Ejecución real sobre el ejemplo sintético** (salida completa en `salida_ejemplo.txt`):

```
Filas válidas: 2260 · filas malas (no entran): 0
Convención: acierta = 0.98 / precio - 1 ; falla = -1 (por USDT). Corrección por 5 estrategias, alfa 0.050.
estrategia  n  acierto  equilibrio  precio  USDT/apuesta  IC95 inf-sup (boot)  decisión
A_moneda_al_50       400    50.0 %     50.9 %   0.499        -0.015       -0.124 ; +0.103  NO DEMOSTRADO
B_acierta_caro       400    74.0 %     81.6 %   0.800        -0.094       -0.158 ; -0.035  PIERDE DINERO (demostrado)
C_barato_gana       1000    25.0 %     20.4 %   0.200        +0.225       +0.076 ; +0.380  GANA DINERO (demostrado)
D_barato_azar        400    20.0 %     20.3 %   0.199        -0.026       -0.247 ; +0.191  NO DEMOSTRADO
E_pocas               60    60.0 %     30.6 %   0.300        +0.952                     -  MUESTRA INSUFICIENTE
Estrategias con acierto de 72 % o más: 1 · de ellas con ganancia por USDT positiva: 0
Decisión final: C_barato_gana
```

  La estrategia B tiene 74 % de acierto y, aun así, pierde dinero: es el caso que la regla 18 de 25 no ve. Con 400 apuestas, A y D no se pueden distinguir de cero.

- Con cinco estrategias, C no se demostraba con 400 apuestas (la corrección exige más muestra). Por eso el ejemplo tiene 1.000 apuestas en C. Es el comportamiento esperado, no un fallo.

## Lo que quedó sin probar

- **No se ejecutó con registros reales.** El ejemplo es sintético; las cifras de la salida son de datos inventados y no dicen nada de las binarias reales.
- **Independencia de las apuestas.** No se modela la correlación entre estrategias que compran la misma ventana. La prueba es optimista en ese caso.
- **Aproximaciones.** La normal y el bootstrap son aproximaciones. Con pocas apuestas o precios muy bajos (0,01 a 0,05) la distribución de `r` es muy asimétrica y los límites son poco fiables. Por eso el mínimo son 100 apuestas.
- **Llenado.** Supone que la orden se llenó al precio registrado. No mide la liquidez ni el deslizamiento.
- **No está conectado a nada.** Ninguna decisión del operador ni de la IA cambia por este programa.

## Cambio propuesto para el operador (no aplicado)

Sustituir el armado «18 de 25» y la compuerta «19 de 25 con ganancia» por la decisión **GANA DINERO (demostrado)** de este medidor, calculada sobre apuestas reales resueltas. Mientras ninguna estrategia tenga esa decisión, el operador no arma. Este cambio toca `binarias/operador/` y `binarias/aprobador/`, que esta propuesta no modifica: queda para decidirlo en esas carpetas.

## Lo que solo puede hacer el dueño

1. Exportar en su propio equipo el registro de apuestas resueltas (precio pagado en el minuto de entrada y resultado oficial), sin subirlo al repositorio.
2. Ejecutar `medidor_ganancia.py` sobre ese registro y leer la decisión de cada estrategia.
3. Decidir si el armado y la compuerta de la IA pasan a esa regla. El cambio es suyo, en las carpetas del operador y del aprobador.
