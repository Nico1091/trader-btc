# Guía de decisión de Claude, versión consolidada (27/10/2026)

Esta versión reemplaza a las anteriores. Claude decide cada operación. Los programas leen datos, calculan y cierran con velas reales. Todo es papel hasta que Nicolás apruebe otra cosa.

Cifras: velas de 1 minuto de futuros de Binance de 2020 a 2026, ajuste 2020-2023, prueba 2024-2026, comisión real y repetida con el doble. Motor corregido el 27/10. Detalle en `CONSOLIDACION-TRADING.md`, sección «Consolidación final».

## 1. Antes de decidir (unos 3 segundos)

1. `python3 -I consolidacion/lectura_mercado.py /tmp/lectura`. Da el resumen de los 5 tiempos, sus 5 fotos, el contexto, los niveles de hoy, las **señales de los dos libros** (del motor `sistema.py`, comprobado contra el simulador) y la **confirmación de los otros tiempos**.
2. Mirar las 5 fotos:

   | Foto | Qué mirar |
   |---|---|
   | 3 meses y 1 día | La tendencia de fondo |
   | 16 horas | La estructura de hoy |
   | 3 horas y 5 min | El momento y el riesgo inmediato |

3. Si la lectura dice «NO OPERAR, lectura insuficiente», no se opera.
4. Anotar en el diario una línea por tiempo y la decisión, antes del resultado.

## 2. Qué se opera: solo lo que dio positivo

**Contexto** = cierre diario de ayer frente a la media de sus 50 últimos cierres (SMA 50). Decide el lado: con contexto alcista solo largos; con contexto bajista, solo los cortos indicados.

### Libro PRINCIPAL (papel en futuros, en %)

| Estrategia | Regla | Horario UTC | BTC 2020-23 / 2024-26 (neto; con el doble) | ETH, mismas reglas |
|---|---|---|---|---|
| **P05b por régimen** | Primer cierre de 15 m fuera de apertura ± 0,5·ATR14. Opera solo si ese primer rompimiento va en el lado del contexto. Límite en la banda 60 min; stop con un cierre de 15 m que vuelve a la apertura; salida 23:59 | Señal 00:00-21:00 | +74 % / +29 % (+54 / +14); 5 de 7 años | −25 % / +44 %: solo vale en BTC |
| **P11** | Lunes 00:00, largo, solo con contexto alcista; stop 3 %, salida 23:59 | Lunes | +43 % / +51 % (+33 / +43); 5 de 7 años | −30 % / +32 %: solo vale en BTC |
| **P05c** | Como P05b con 1,0·ATR14, solo largo, con contexto alcista **y 1 h, 4 h y 1 día sobre su EMA 20** | Señal 00:00-21:00 | +35 % / +29 % (+32 / +26); 5 de 7 años | −0,5 % / +25 %: plana en 2020-23, positiva en 2024-26 |

### Cuenta de 40.000 pesos (contado BTCUSDT, solo largos, sin apalancamiento)

Solo las piezas que aguantan el contado con comisión doble (0,15 %/lado) en los dos tramos:

| Pieza | BTC 2020-23 / 2024-26 con comisión doble | ETH |
|---|---|---|
| P11 con contexto | +22,4 % / +34,2 % | No resiste |
| P05c largo (3 tiempos a favor) | +24,1 % / +19,0 % | No resiste en 2020-23 |
| **P05b largo con patrón alcista del curso en las 3 últimas velas de 1 h** | +10,3 % / +14,8 % (muestra pequeña: 61 operaciones) | +2,7 % / +16,9 % |

Los cortos de P05b y los largos de P05b sin patrón **no** van a pesos: en contado el corto no existe, y el largo sin patrón no aguanta la comisión doble.

### Libro PRUEBA (papel, en %, aparte, con su propia posición)

| Estrategia | Regla | Horario UTC | BTC 2020-23 / 2024-26 | ETH, mismas reglas |
|---|---|---|---|---|
| **N9** Asia-Londres | Rango de 00:00-06:59 roto por un cierre de 15 m en el lado del contexto; límite 60 min; stop con un cierre de 15 m de vuelta al punto medio; salida 23:59 | 07:00-13:00 | +106 % / +22 % (con el doble +84 / +4) | +94 % / +62 % (con el doble +71 / +44): **robusta** |
| **N8** miércoles | Miércoles 00:00, largo, solo con contexto alcista; stop 3 %, salida 23:59 | Miércoles | +49 % / +39 % | +46 % / +43 %, 6 de 7 años: **robusta** |

Una estrategia de PRUEBA pasa a PRINCIPAL con 30 operaciones de papel o más que ganen neto y superen al azar.

## 3. Los otros tiempos confirman «un poquito» (medido, sin RSI)

| Confirmación | Efecto medido | Uso |
|---|---|---|
| 1 h o 4 h sobre su EMA 20, en P05b | Neutra: el rompimiento ya la trae (prueba +0,13 → +0,14 % por operación) | Se mira, no se exige |
| Los 3 tiempos mayores (1 h, 4 h, 1 día) | Mejora P05c (prueba +0,48 → +0,66 % por operación) | **Exigida en P05c** |
| Los 3 tiempos mayores en P05b o N9 | Empeora: se entra tarde (P05b, prueba +0,13 → +0,08) | No se exige |
| Patrón del curso en las 3 últimas velas de 1 h | Mejora los largos de P05b en contado | **Exigido para llevar P05b a pesos** |
| Semana anterior a favor, en P11 y N8 | Empeora (N8, prueba +0,47 → +0,13) | No se usa |

## 4. Riesgo («un poquito más», medido)

- **2 % por operación** (800 pesos). El nocional sale de la distancia al stop conocida al entrar, con tope en el saldo y mínimo de 5 USDT. Una posición a la vez.
- **Topes:** −4 % en el día (se para el día), −8 % en la semana (se para la semana) y **parada total con −20 % desde el máximo** (vuelta a papel).
- **Por qué 2 % y no más:**

  | Riesgo | 2020-2023 | 2024-2026 | Comisión doble | Caída máxima |
  |---|---|---|---|---|
  | 1,5 % | +10,4 %/año | +11,2 %/año | — | 9 % |
  | **2 %** | **+13,6 %/año** | **+15,5 %/año** | **+8,8 / +9,5 %/año** | **11-17 %** |
  | 2,5 % | — | — | Caída del 20,9 % en 2020-2023, que toca la parada total | 20,9 % |

## 5. Cuándo NO operar

- Lectura incompleta.
- **Contra el contexto:** largos de P05b, P05c, P11 o N8 con contexto bajista; cortos con contexto alcista.
- Si el primer rompimiento del día fue hacia el lado contrario: P05b ya no opera ese día.
- Señales de P05b o P05c después de las 21:00 UTC, y de N9 fuera de 07:00-13:00.
- P05c sin los 3 tiempos mayores a favor.
- Para cumplir una cuota. Con señal salen unas 2,2 operaciones por semana en el libro PRINCIPAL (P05b 1,4; P11 0,5; P05c 0,3) y 2,2 en el de PRUEBA (N9 1,6; N8 0,5).
- Con un tope tocado. En la Reserva Federal (28/10), sin aperturas de 17:00 a 21:00 UTC y a medio riesgo el 27 y el 28.
- **Descartado con datos:** MEZCLA, patrones de vela como entrada, RSI, retroceso a la EMA 20, 50 SMA + precio, ruptura del máximo o mínimo de ayer, N3, cortos de P05c y del lunes, y exigir que todos los tiempos vayan a favor en P05b.

## 6. Después de cada día

`python3 -I consolidacion/sistema.py cerrar AAAA-MM-DD > papel/AAAA-MM-DD.txt`. Cierra cada libro con las 1.440 velas de 1 minuto y lo compara con el testigo al azar del día. Antes de cambiar una regla: `python3 -I consolidacion/pruebas_sistema.py`, que debe terminar en «SIN FALLAS».
