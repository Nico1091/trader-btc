# Investigación cuantitativa de Trading Cloud: auditoría, diagnóstico y validación (27/10/2026)

**Rama:** `investigacion/quant-2026-10-27`, aislada en el worktree `/home/user/trader-btc-investigacion`.
**Base congelada:** commit `0556636`, que no se modificó. La rutina de producción no se tocó, no se publicó nada y no se operó con dinero real.

Todo lo que dice «medido» sale de un script de `investigacion/` cuya salida está guardada al lado (`.txt` o `.csv`). Lo que es estimación o hipótesis se dice así.

## Resumen para decidir

1. **La versión consolidada se reproduce idéntica.** BTC y ETH coinciden byte a byte, y las 4 pruebas del sistema dan «SIN FALLAS».
2. **Los porcentajes publicados no son rentabilidad de la cuenta.** Son sumas simples del % neto de cada operación, con el 100 % del nocional y sin componer. La cuenta de 40.000 pesos, con 2 % de riesgo, da +12 a +15 % al año: unos **5.000 a 6.000 pesos al año**.
3. **Ninguna estrategia demuestra una ventaja que sobreviva a la búsqueda.** El proyecto registró unas 337 variantes. Corrigiendo por eso, ninguna llega a evidencia fuerte (Sharpe deflactado ≥ 0,95), ni siquiera suponiendo que solo se probaron 10.
4. **En 5 activos que nunca se miraron, con las reglas sin tocar, solo P05c generaliza.** Es positiva en los 5, pero depende de sus mejores operaciones: sin las 5 mejores de cada activo, su media es negativa. **N8 y N9, que se daban por «robustas», no generalizan** (positivas en 2 de 5), y P11 tampoco (1 de 5).
5. **El beneficio está muy concentrado.** Sin sus 5 mejores operaciones, P05b pasa de +74 % a −10 % en 2020-2023, y P11 de +43 % a −16 %.
6. **Las cinco estrategias son, en buena parte, la misma apuesta:** BTC a favor del contexto. Los días en que coinciden, su P&L se mueve con una correlación de 0,75 a 0,96.
7. **El parámetro de P05b es frágil.** En entrenamiento (2020-22), k = 0,5 es un pico aislado: con k = 0,4 y 0,6 pierde. En los otros 6 activos, el mejor k cambia de uno a otro (`d1_p05b_k_por_activo.txt`). Es la firma del sobreajuste, no de una regla estable.
8. **300 operaciones al mes no son viables.** El mismo mecanismo en sesiones de 1 y 2 horas (72 a 122 operaciones al mes) tiene una ventaja bruta de entre −0,02 % y +0,06 % por operación en 5 activos, y en las de 4 y 8 horas no hay un signo estable. Los costes van de 0,07 a 0,20 % por ida y vuelta. Con 40.000 pesos, las comisiones de 300 operaciones al mes costarían entre el 45 % y el 60 % del capital cada mes en contado, y entre el 135 % y el 193 % en futuros (por la orden mínima).
9. **Bajar el riesgo a 0,25 %, 0,5 % o 1 % no es posible con este capital.** Por el mínimo de 5 USDT no cabe el 100 %, el 96 % y el 78 % de las operaciones, respectivamente. Subir al 2,5 % multiplica por seis la probabilidad de tocar el −20 % (del 0,5 % al 2,9 % a 2 años).
10. **Ninguna variante cumple todas las condiciones para avanzar.** Se recomienda **conservar las reglas actuales**, corregir lo que el informe dice de ellas y poner los controles de riesgo en el código. Los cambios propuestos están en el punto 11.

---

## 1. Estado inicial reproducido (fase A)

Comandos, ejecutados desde `investigacion/reproduccion/`:

```
python3 -I ../../consolidacion/consolidado.py /home/user/datos-btc/BTCUSDT_um_1m.npy BTC   # 10 s
python3 -I ../../consolidacion/consolidado.py /home/user/datos-btc/ETHUSDT_um_1m.npy ETH   # 18 s
python3 -I ../../consolidacion/pruebas_sistema.py                                          # 58 s
```

| Comprobación | Resultado |
|---|---|
| `consolidado_BTC.txt` y `.csv` frente a los guardados | **idénticos** (`diff` vacío) |
| `consolidado_ETH.txt` frente al guardado | **idéntico** |
| Patrones de vela (motor en vivo frente a simulador) | 0 diferencias en 25.508 patrones |
| Motor en vivo = simulador | 2.502 de 2.502 comparaciones iguales: 417 días × 6 estrategias. Son todos los días de 2026 más 120 días al azar de 2020-2025, es decir, una **muestra del 17 % del historial**, no todo |
| Sin mirar el futuro | 80 de 80 señales iguales con los datos cortados en su instante |
| Coinbase (fuente en vivo) frente a Binance | 18 de 20 días con las mismas operaciones |

Tabla del informe anterior, comprobada:

| Variante | BTC 2020-2023 | BTC 2024-2026 | ¿Coincide? |
|---|---|---|---|
| P05b por régimen | +73,95 % | +29,37 % | sí |
| P11 con contexto | +42,99 % | +50,80 % | sí |
| P05c con los 3 marcos | +35,18 % | +29,15 % | sí |
| N9 Asia-Londres | +106,07 % | +22,26 % | sí |
| N8 miércoles | +48,89 % | +39,28 % | sí |

**Fechas exactas.**
- BTC: velas de 1 minuto del 2020-01-01 00:00 al 2026-10-24 23:59 UTC. ETH: hasta el 2026-10-25 23:59.
- Ajuste: del 2020-01-01 al 2023-12-31. Prueba: del 2024-01-01 al final de los datos (unos 2 años y 10 meses).
- Las estrategias empiezan después de su calentamiento: P05b a los 15 días con un ATR de 14, N9 a los 60 días y el contexto cuando existe la SMA 50.

**Cómo se calculan los porcentajes** (no estaba escrito): es la **suma simple** del % neto de cada operación sobre el 100 % del nocional, en futuros, con creador 0,02 % y tomador 0,05 %. No es rentabilidad de una cuenta ni está compuesta. Los del ETH del informe también cuadran (N9 +94,07 / +62,14).

## 2. Arquitectura y flujo encontrados

**Producción (en papel):**
- La rutina de la nube (`trig_01HhTpY4sVUqaj1ui3qi7wyQ`) arranca con `PROMPT-AGENTE-TRADING-NUBE.md`.
- Claude ejecuta `consolidacion/lectura_mercado.py`, que lee los 5 tiempos con sus fotos y llama a `sistema.informe(Coinbase(), hoy)`.
- Claude decide y anota la orden de papel en `ORDENES-PRUEBA-PROPIA.md`.
- Al terminar el día, `consolidacion/sistema.py cerrar AAAA-MM-DD` cierra con las 1.440 velas y lo guarda en `papel/`.
- **No hay motor de ejecución en producción**: no se envía ninguna orden.

**Simulador:**
- `consolidacion/lib.py`: carga de datos, remuestreo y patrones.
- `consolidacion/sim.py`: motor de minutos, P05b, P11, salidas, comisiones y testigo al azar.
- `consolidacion/consolidado.py`: contexto, confirmaciones, N9, la selección por variantes y la cuenta de 40.000 pesos.
- `consolidacion/pruebas_sistema.py`: las pruebas.

**Fuera de producción** (agente local de octubre):
- `agente.py`, `vivo.py`, `rapido.py`, `banco.py` y `claude_orden.py`.
- `binance.py`: candado de dinero real con `AUTORIZO-DINERO-REAL.txt`, redondeo a los filtros del par y órdenes con identificador propio sin reintentos a ciegas.
- `simulador.py`: las reglas reales del contado.

**Controles de riesgo:**
- Los topes de −4 % al día, −8 % a la semana y −20 % total solo existen **en texto** (la guía y el prompt) y en la función `cuenta()` del simulador.
- `sistema.py` no lleva saldo, no sabe qué posiciones hay abiertas y no bloquea nada.

## 3. Errores e inconsistencias detectados

Ninguno invalida la reproducción: son límites de lo que los números pueden afirmar.

1. **El tramo de prueba está contaminado.** 2024-2026 de BTC y todo ETH se miraron en las tareas 1 a 13 para decidir qué sobrevivía (eso dicen el propio CONSOLIDACION-TRADING.md y los CSV `t*.csv`). Ya no son evidencia independiente.
2. **P05c «todos 3 de 3» se adoptó mirando la prueba.** La regla estaba fijada antes, pero la decisión usó la media de la prueba (`consolidado.py:203`).
3. **El riesgo real es mayor que el planeado.**
   - El stop de P05b es un cierre de 15 minutos, no una orden de stop. En la cuenta en pesos, las pérdidas por stop fueron **1,39 veces la distancia planeada** (mediana; p90: 1,63). Con 2 % de riesgo, la mayor pérdida de una operación llegó al 2,7-2,8 % del saldo (`b2_cuenta_pesos_BTC.txt`, punto 3).
   - En el libro de futuros, la peor operación de P05b perdió **−15,6 % del nocional** (corto del 13/03/2020) cuando la distancia planeada era del 7,1 %.
4. **El libro de futuros no se puede ejecutar con 40.000 pesos.**
   - La orden mínima de BTCUSDT en futuros es 0,001 BTC, unos 81 USDT con BTC a 80.844. Con 12,59 USDT haría falta un apalancamiento de 6,4 veces o más.
   - El dato viene del informe del 20/10. Hoy no se pudo comprobar: la API de futuros de Binance responde 451 desde la nube.
   - Los filtros del contado sí se comprobaron hoy, y están guardados en `investigacion/datos/`: paso de 0,00001 BTC (0,0001 ETH) y mínimo de 5 USDT.
5. **Los topes de riesgo no están en el código.**
   - En `cuenta()`, la parada del −20 % solo se revisa antes de cada operación nueva. Una posición abierta sigue hasta su salida, así que la caída puede pasar del −20 % dentro de una operación.
   - En vivo no hay nada implementado.
6. **El papel supone una ejecución perfecta.**
   - `sistema.py cerrar` calcula lo que la estrategia habría hecho con las velas, haya estado o no la rutina para poner el límite en su ventana de 60 minutos.
   - Fallos como el del 26/10 (límite de uso) no se reflejan en el resultado.
   - No existen órdenes parciales ni desconexiones en el modelo. `sistema.py` no guarda estado: al reconectar recalcula todo, pero no puede saber si la orden se puso.
7. **La fuente en vivo no es la del backtest.** En vivo se usa Coinbase BTC-USD al contado; el backtest usa futuros de Binance. Coinciden en 18 de 20 días: 1 de cada 10 días el sistema en vivo no hace lo mismo que el probado.
8. **El testigo al azar favorece un poco a las estrategias.** Paga tomador a la entrada y no tiene stop, mientras que las estrategias entran como creador: unos 0,03 % por operación a su favor. Es menor.
9. **Costes que no están en las cuentas:**
   - Pasar pesos a USDT por P2P y volver cuesta cerca del 1 % (3.178 frente a 3.147 COP por USDT, informe del 20/10).
   - La comisión del 0,075 % exige tener BNB, y con 12,59 USDT eso inmoviliza parte del capital.
10. **Datos:** limpios (`b1_auditoria_datos.txt`).
    - 0 minutos faltantes, 0 duplicados y 0 velas OHLC incoherentes. Solo 369 velas de BTC sin volumen (0,01 %).
    - Saltos extremos reales: BTC +7,3 % en un minuto (13/03/2020) y ETH 25,5 % (19/05/2021).
    - SOL y XRP tienen 2 huecos de minutos cada uno.

## 4. Resultados por estrategia y activo

### 4.1 BTC: comisión de futuros base, % del nocional por operación (`c2_diagnostico.txt`)

| Estrategia | Tramo | Ops | Media | Aciertos | PF | Suma | Caída máx. (compuesta) | Sharpe | IC 90 % de la media |
|---|---|---|---|---|---|---|---|---|---|
| P05b | 2020-23 | 280 | +0,26 | 47,5 % | 1,26 | +74,0 | 25,6 % | 0,57 | [−0,02, +0,55] |
| P05b | 2024-26 | 226 | +0,13 | 45,1 % | 1,20 | +29,4 | 15,5 % | 0,57 | [−0,04, +0,30] |
| P11 | 2020-23 | 103 | +0,42 | 46,6 % | 1,38 | +43,0 | 22,1 % | 0,57 | [−0,03, +0,86] |
| P11 | 2024-26 | 83 | +0,61 | 49,4 % | 1,82 | +50,8 | 10,4 % | 1,15 | [+0,14, +1,15] |
| P05c | 2020-23 | 48 | +0,73 | 58,3 % | 2,02 | +35,2 | 15,4 % | 0,87 | [+0,11, +1,24] |
| P05c | 2024-26 | 44 | +0,66 | 52,3 % | 2,78 | +29,2 | 3,4 % | 1,44 | [+0,28, +1,12] |
| N9 | 2020-23 | 315 | +0,34 | 37,5 % | 1,44 | +106,1 | 24,5 % | 0,91 | [+0,07, +0,60] |
| N9 | 2024-26 | 260 | +0,09 | 34,6 % | 1,16 | +22,3 | 17,3 % | 0,49 | [−0,07, +0,25] |
| N8 | 2020-23 | 110 | +0,44 | 48,2 % | 1,37 | +48,9 | 19,0 % | 0,67 | [−0,03, +0,93] |
| N8 | 2024-26 | 83 | +0,47 | 50,6 % | 1,65 | +39,3 | 11,2 % | 0,95 | [−0,13, +1,11] |

**Cómo se midió:**
- Sharpe y Sortino: sobre el P&L diario de calendario (0 los días sin operación), anualizados con √365.
- IC: bootstrap por bloques de meses (`metricas.py`).
- 6 de los 10 intervalos incluyen el cero.

### 4.2 Siete activos con las reglas sin tocar: media neta con comisión doble (`d0_activos_nuevos.txt`)

| Estrategia | SOL | BNB | XRP | DOGE | ADA | **5 nuevos: positivas / IC 90 %** | BTC | ETH | Veredicto preregistrado |
|---|---|---|---|---|---|---|---|---|---|
| P05b | −0,13 | +0,22 | +0,06 | −0,01 | +0,01 | 3/5 · [−0,16, +0,24] | +0,13 | −0,03 | **no generaliza** |
| P11 | −0,57 | −0,10 | +0,18 | −0,24 | −0,66 | 1/5 · [−0,61, +0,10] | +0,40 | −0,09 | **no generaliza** |
| P05c | +0,35 | +0,61 | +1,21 | +2,24 | +0,42 | 5/5 · [+0,26, +1,62] | +0,63 | +0,22 | **generaliza** (pero sin las 5 mejores de cada activo su media es −0,20) |
| N9 | +0,06 | −0,02 | −0,00 | −0,25 | +0,10 | 2/5 · [−0,15, +0,11] | +0,15 | +0,19 | **no generaliza** |
| N8 | −0,00 | +0,14 | −0,40 | −0,25 | +0,08 | 2/5 · [−0,48, +0,33] | +0,36 | +0,36 | **no generaliza** |

- El criterio se fijó en `PREREGISTRO.md` **antes** de descargar los activos: positiva en 4 de 5 o más, y un IC 90 % de la media conjunta que no incluya el cero.
- Además, en 2024-2026 P05b pierde en 4 de los 5 activos nuevos.

## 5. Diagnóstico: de dónde sale el beneficio

- **Unas pocas operaciones grandes** (`c2`, punto 1). Si se quitan las 5 mejores de cada tramo:

  | Estrategia | Tramo | Suma | Sin las 5 mejores |
  |---|---|---|---|
  | P05b | 2020-23 | +74 | **−10** |
  | P05b | 2024-26 | +29 | **−9** |
  | P11 | 2020-23 | +43 | **−16** |
  | N9 | 2024-26 | +22 | **−14** |
  | N8 | los dos tramos | — | ~0 |

  Solo P05c sigue positiva (+3,3 y +8,2). Es lo esperable de un sistema de tendencia (pocas ganancias grandes, muchas pérdidas pequeñas), pero con 200 a 300 operaciones por tramo deja la ventaja estadísticamente débil.
- **El «contexto» explica buena parte de la ventaja** (`d4_frecuencia_*.txt`, columna «testigo»).
  - Estar todo el día del lado del contexto, sin ninguna señal, da +0,205 % bruto por día en BTC 2020-23 y +0,097 % en 2024-26. P05b da +0,334 y +0,200.
  - La señal de P05b añade unos +0,1 % brutos por operación sobre la deriva del contexto.
  - La regla clásica de tendencia sola tiene un Sharpe de 1,41 y 0,97 en BTC, y es positivo en 13 de 14 casos (activo × tramo), con 1,3 a 2,4 cambios de posición al mes (`d5_contexto_puro.txt`).
- **Las estrategias no son independientes** (`c2`, punto 8).
  - La mitad de los días de P05c son días de P05b en el mismo lado.
  - N9 coincide con P05b en el 33-38 % de sus días.
  - Correlación del P&L diario: 0,61 entre P05b y N9. Los días en que operan las dos, entre 0,75 y 0,96 entre cualquier par.
  - En la cartera: hasta 4 posiciones abiertas a la vez, todas del mismo lado (`d6_cartera.txt`).
- **Cuándo funciona (BTC, descriptivo):**
  - Por régimen de volatilidad: P05c pierde con volatilidad alta (−0,81 % por operación) y N9 no gana con volatilidad baja (−0,03).
  - Las señales de P05b después de las 17:00 pierden en 2024-26 (−0,39), y en los 5 activos nuevos también (−0,10 frente a +0,05).
  - En ETH, el signo por sesión cambia de un tramo a otro. Nada de esto se adoptó: son hipótesis.
- **Costes** (`c2`, punto 2). Con comisión doble o adversa (todo tomador más 0,02 % de deslizamiento), la media de P05b y N9 en 2024-26 queda en **+0,06 y +0,02**. En contado normal (0,10 %), P05b 2024-26 da **0,000**.
- **Años perdedores:** P05b pierde en 2022 y 2025, P11 en 2022 y 2025, N9 en 2023 y 2025, y N8 en 2021, 2022 y 2026. Son compatibles con su distribución: la mediana de P05b, P11 y N9 es negativa o cero (solo P05c, y N8 en 2024-26, la tienen positiva) y dependen de pocas operaciones. No hay una ruptura identificable.

## 6. Viabilidad económica con 40.000 pesos (12,59 USDT)

Restricciones del contado comprobadas hoy, con `b2_cuenta_pesos.py` y `exchangeinfo_spot_*.json`:

| Riesgo por operación | ¿Caben las operaciones? (saldo inicial) | Resultado con las restricciones reales, comisión BNB |
|---|---|---|
| 0,25 % | **no cabe ninguna** (todas < 5 USDT) | 0 operaciones |
| 0,50 % | 96 % no caben | 5 y 3 operaciones en 4 y 3 años |
| 1 % | 78 % no caben | +5,7 y +3,1 %/año; caída 4,1 y 3,3 % |
| **2 %** | 2 % no caben | **+13,3 y +15,2 %/año; caída 12,0 y 10,5 %** |
| 2,5 % | todas | +15,5 y +19,0 %/año; caída 16,0 y 12,0 % |

Los dos valores de cada celda son 2020-2023 y 2024-2026.

- Con la comisión de 0,10 % cobrada en BTC (sin BNB): +12,1 y +13,3 %/año. Con el doble (0,15 %): **+8,6 y +10,0 %/año, con una caída del 17,5 %**.
- Mi reimplementación de `cuenta()` reproduce **exactamente** las 12 cifras publicadas (`b2`, punto 1).
- El paso de cantidad, el polvo y la forma de pago de la comisión cambian poco el resultado: con 2 %, la cuenta real queda entre 0,2 y 0,5 puntos al año por encima o por debajo de la del simulador con la misma comisión.

**Monte Carlo a 2 años** (2.000 trayectorias de meses sorteados de todo el historial, restricciones reales y BNB). Es **optimista**, porque sortea de un historial ya usado para elegir:

| Riesgo | Caída máx. mediana / p95 | P(tocar −20 %) | Saldo a 2 años: p5 / mediana / p95 | P(perder) |
|---|---|---|---|---|
| 1 % | 2,6 / 5,3 % | 0 % | 39.538 / 43.608 / 50.125 | 9 % |
| **2 %** | **8,8 / 15,3 %** | **0,5 %** | **39.493 / 51.530 / 71.066** | **6 %** |
| 2,5 % | 10,8 / 18,6 % | 2,9 % | 39.085 / 53.965 / 77.462 | 7 % |

**En pesos:** con 2 %, la ganancia esperada histórica es de unos 5.000 a 6.000 COP al año, antes del ~1 % del P2P. No hay manera de generar ingresos diarios constantes con este capital: en la mayoría de las estrategias, la mediana por operación es negativa o cero y el beneficio llega en pocas operaciones grandes.

## 7. Frecuencia y riesgo: ¿300 operaciones al mes?

**Frecuencia real hoy:**
- Todos los libros de BTC en papel de futuros: 19,2 operaciones al mes (N9 7,1; P05b 6,3; N8 2,4; P11 2,3; P05c 1,1).
- La cuenta en pesos: 3,3 a 4,0 al mes.

**Coste mensual de 300 operaciones de ida y vuelta** (cálculo directo):

| Lugar | Ida y vuelta | Nocional por operación | Coste al mes | En % del capital |
|---|---|---|---|---|
| Contado normal | 0,20 % | 12,59 USDT | 7,55 USDT | **60 %** |
| Contado con BNB | 0,15 % | 12,59 | 5,67 | **45 %** |
| Futuros, creador + tomador | 0,07 % | 81 USDT (orden mínima; exige 6,4 veces de apalancamiento) | 17,0 | **135 %** |
| Futuros, tomador + tomador | 0,10 % | 81 | 24,3 | **193 %** |

**¿Hay ventaja a esa frecuencia?** Se probó el mecanismo de P05b en sesiones de H horas (`d4_frecuencia.py`, 5 activos, sin parámetros nuevos):

| Sesión | Operaciones al mes (media de 5 activos) | Ventaja bruta por operación (rango de 5 activos × 2 tramos) |
|---|---|---|
| 1 h | 122 | −0,02 a +0,01 % |
| 2 h | 72 | −0,02 a +0,06 % |
| 4 h | 32 | −0,08 a +0,11 % |
| 8 h | 18 | −0,11 a +0,20 % |
| 24 h (≈ P05b) | 7 | −0,28 a +0,59 % |

- Por debajo de 24 horas no hay ventaja bruta medible. Cualquier coste la vuelve negativa: en BTC, la sesión de 1 hora suma **−455 %** y **−308 %** netos en futuros por tramo.
- Coincide con el laboratorio de alta frecuencia del 20/10 (`INFORME-TRADING-SEGUIDO.md`): la dirección a segundos y minutos da un AUC de 0,51 a 0,56 y operar seguido perdió entre −17 % y −40 % en 34 días.
- **Conclusión: 300 operaciones al mes solo aumentan los costes.** Con 40.000 pesos, lo que tiene sentido es lo contrario: pocas operaciones, las de mayor ventaja bruta (P05c y P11 en BTC).

## 8. Hipótesis probadas y resultados de cada experimento

Todas las variantes están en `variantes/registro_variantes_*.csv`: 263 por activo, en 7 activos, ganen o pierdan. Fuera de lo preregistrado solo se añadió P05c con k = 0,8 y 1,2 (además de 1,0), y queda registrado igual.

Regla de adopción, fijada antes de mirar (`PREREGISTRO.md`): mejorar en entrenamiento (2020-22) y en validación (2023), sin empeorar la caída más de un 20 %, conservando al menos el 40 % de las operaciones, sin ser un pico aislado y ganando a la base en la mayoría de los años del walk-forward.

| Familia (BTC) | Variantes | Pasan la regla | Walk-forward (gana a la base) | La mejor de entrenamiento en BTC, ¿mejora en los 7 activos? | Comentario |
|---|---|---|---|---|---|
| P05b: k × W × hora × salida | 225 | **0** | 2 de 5 años | 4 de 7 | k = 0,5 es un pico aislado: k = 0,4 y 0,6 pierden en entrenamiento. Lo mejor en entrenamiento (W = 30, stop duro) empeora en validación |
| P05c: k × salida | 15 | **0** | 1 de 5 | 2 de 7 | La base sigue siendo la mejor fuera de entrenamiento |
| N9: ventana × salida | 15 | 1 (07-11) | 3 de 5 | 3 de 7 | Pasa formalmente, pero mejora de −0,112 a −0,089 en validación (las dos pierden) y es peor en la prueba. **No se recomienda**: mejora una estrategia que no generaliza |
| P11: stop | 4 | **0** | 0 de 5 | (la base es la mejor) | El stop del 3 % es el mejor en entrenamiento |
| N8: stop | 4 | 2 (sin stop, stop 5 %) | 4 de 5 | 6 de 7 | Sin stop gana en entrenamiento, validación y prueba, pero en los 5 activos nuevos su IC incluye el cero y su **peor operación pierde entre −19 y −38 %** en altcoins (−28 % en ETH; `d7`). **No se adopta**: viola el control de riesgo |

Lo que se elige en BTC no se transfiere mejor que tirando una moneda (P05b 4 de 7, N9 3 de 7, P05c 2 de 7). La excepción es N8 sin stop (6 de 7), y se descarta por su riesgo de cola.

**Salidas:**
- Salir a las 4 u 8 horas **empeora** P05b, P05c y N9 en todos los tramos: la ventaja está en dejar correr hasta las 23:59.
- El **stop duro** intraminuto en P05b reduce la caída en entrenamiento (de 25,6 % a 15,8 %) y en la prueba (de 15,5 % a 14,7 %), y sube la media en entrenamiento. Pero baja la de validación (de +0,190 a +0,134), así que no pasa la regla. Como **control de riesgo** (no como mejora de la ventaja) merece una prueba hacia adelante, porque acota pérdidas como la del 13/03/2020.

**Pruebas múltiples** (`c3_pruebas_multiples.txt`). Sharpe deflactado (Bailey y López de Prado) en BTC:

| Supuesto de variantes probadas | Rango del Sharpe deflactado |
|---|---|
| N = 10 | 0,21 a 0,85 |
| N = 100 | 0,04 a 0,42 |

Ninguno llega a 0,95. Con valores p corregidos por Holm dentro de cada tramo, solo P05c 2020-23 queda por debajo de 0,05 (0,037; en 2024-26, 0,055).

## 9. Fuera de muestra y sensibilidad a costes

- **Fuera de muestra limpio:** los 5 activos nuevos, en el punto 4.2. Es la única evidencia que no estuvo expuesta a las decisiones.
- **Costes, media por operación en BTC 2024-26:**

  | Estrategia | Base | Doble | Adverso |
  |---|---|---|---|
  | P05b | +0,13 | +0,06 | +0,06 |
  | N9 | +0,09 | +0,02 | +0,02 |
  | P11 | +0,61 | +0,51 | +0,57 |
  | P05c | +0,66 | +0,59 | +0,59 |
  | N8 | +0,47 | +0,37 | +0,43 |

  Las que sobreviven con margen son las de pocas operaciones y mayor recorrido.

## 10. Versión base frente a las candidatas

| Candidata | ¿Reproduce y pasa la integridad? | ¿Expectativa sustentada? | ¿Mejora fuera de muestra? | ¿Respeta el riesgo? | ¿Aguanta costes adversos? | ¿No depende de pocas operaciones o de un parámetro? | **Decisión** |
|---|---|---|---|---|---|---|---|
| Base consolidada | sí | débil (Sharpe deflactado < 0,95) | solo P05c en activos nuevos | sí, en papel | P05b y N9 quedan cerca de 0 | **no** | se conserva, con etiquetas corregidas |
| P05b W = 30 + stop duro | sí | no (empeora en validación) | no | sí | — | pico de parámetros | no |
| N9 07-11 | sí | no (pierde en validación) | no | sí | — | — | no |
| N8 sin stop | sí | positiva, pero IC con cero en los activos nuevos | 4 de 5 activos | **no** (cola de −28 a −38 %) | sí | no | no |
| Regla de tendencia sola (SMA 50, largo o fuera) | sí | Sharpe 0,97-1,41 en BTC, positivo en 13 de 14 | no se eligió con estos datos | **no** en la cuenta: al 40 % del saldo casi no cabe (el redondeo la deja bajo 5 USDT) y desde el 60 % la caída llega al 20-22 % y dispara la parada (`d5b_tendencia_cuenta.txt`) | sí (1-2 cambios al mes) | no | referencia, no candidata |

**Ninguna variante cumple todas las condiciones.** Se conserva la versión actual. Para hacer cualquier cambio de estrategia falta:
- papel hacia adelante con ejecución real registrada (punto 11);
- más activos u otro periodo nunca mirado;
- para P05c, más operaciones: hoy son 92 en BTC en casi 7 años.

## 11. Cambios de código propuestos (no aplicados)

| # | Cambio | Archivos | Pruebas necesarias |
|---|---|---|---|
| 1 | **Controles de riesgo en código:** un estado de saldo, P&L del día y la semana, y caída desde el máximo leído de `papel/`. `sistema.py estado` diría «BLOQUEADO» si se tocó −4 %, −8 % o −20 %, y qué hacer con lo abierto (cerrar al tocar la parada total) | `consolidacion/sistema.py` y un archivo de estado nuevo | Pruebas unitarias de cada transición (día, semana, total, reinicio); que la paridad 2.502/2.502 siga igual |
| 2 | **Separar el papel teórico del ejecutado:** anotar si la rutina estuvo presente en la ventana del límite, la hora real de la orden y si se llenó. `cerrar` informaría las dos cifras | `sistema.py`, formato de `ORDENES-PRUEBA-PROPIA.md` | Un día con la rutina ausente debe dar «no ejecutada» |
| 3 | **Stop duro de protección** en la referencia, además del cierre de 15 minutos (P05b, P05c y N9), solo para acotar colas. Se valida hacia adelante, no se adopta por backtest | `sim.py` (como opción), `sistema.py` | Comprobar con `d1_variantes.py` (salida «stop duro»); paridad entre motor y simulador con la opción activada |
| 4 | **Etiquetas honestas** en la guía y el prompt. «Robusta» solo para lo que pasó el fuera de muestra (P05c). N8 y N9: «no generalizan». P05b y P11: «propias de BTC, parámetro frágil». Decir que los % son sumas al 100 % del nocional | `GUIA-DECISION-CLAUDE.md`, `PROMPT-AGENTE-TRADING-NUBE.md` | Revisión de texto |
| 5 | **Nada de 300 operaciones al mes ni de bajar el riesgo del 2 %** con este capital (punto 6). Si el capital crece hasta unos 50 USDT, se puede volver a medir 1 % | Guía | — |
| 6 | **Referencia diaria de la regla de tendencia** en el informe de cierre, para ver en vivo si las estrategias aportan algo sobre ella | `sistema.py cerrar` | Paridad con `d5_contexto_puro.py` |
| 7 | **Ampliar la prueba de paridad** a todo el historial (hoy cubre el 17 %) y hacer que el testigo al azar use las mismas comisiones de entrada | `pruebas_sistema.py`, `sim.py` | Tiempo de ejecución; los mismos resultados |

## 12. Limitaciones, riesgos que quedan y siguiente validación

**Limitaciones:**
- Los activos nuevos son altcoins, más volátiles que BTC. Una regla puede valer solo para BTC por una razón real (por ejemplo, el hueco de fin de semana del CME para el lunes), pero eso es una hipótesis sin comprobar.
- El Monte Carlo y los IC usan meses del propio historial.
- El deslizamiento de las órdenes límite (que no se llenen por la cola) solo se modeló como coste adverso.
- No se pudo comprobar hoy el mínimo de futuros (error 451).

**Riesgos que quedan:**
- Saltos de precio en los que un stop por cierre pierde 2 o más veces lo planeado.
- La rutina que no llega a tiempo a la ventana de 60 minutos.
- La fuente en vivo que da otra señal 1 de cada 10 días.

**Siguiente validación:**
1. 30 o más operaciones de papel por estrategia con la ejecución real registrada (cambio 2).
2. Repetir `d0_activos_nuevos.py` con otros 5 activos líquidos y con datos posteriores al 27/10/2026, sin tocar reglas.
3. Si el capital crece, volver a medir la viabilidad del 1 %.

## Comandos para reproducir todo (desde `investigacion/`)

```
python3 -I b1_auditoria_datos.py > b1_auditoria_datos.txt
python3 -I c1_operaciones.py /home/user/datos-btc/BTCUSDT_um_1m.npy BTC      # y ETH, SOL, BNB, XRP, DOGE, ADA
python3 -I c2_diagnostico.py > c2_diagnostico.txt
python3 -I c3_pruebas_multiples.py > c3_pruebas_multiples.txt
python3 -I b2_cuenta_pesos.py BTC > b2_cuenta_pesos_BTC.txt
python3 -I d0_activos_nuevos.py > d0_activos_nuevos.txt
python3 -I d1_comprobar.py /home/user/datos-btc/BTCUSDT_um_1m.npy BTC         # la variante «actual» = base
python3 -I d1_variantes.py /home/user/datos-btc/BTCUSDT_um_1m.npy BTC         # y los otros 6 activos
python3 -I d1_analisis.py > d1_analisis.txt
python3 -I d4_frecuencia.py /home/user/datos-btc/BTCUSDT_um_1m.npy BTC        # y ETH, BNB, DOGE, ADA
python3 -I d5_contexto_puro.py > d5_contexto_puro.txt
python3 -I d5b_tendencia_cuenta.py > d5b_tendencia_cuenta.txt
python3 -I d6_cartera.py > d6_cartera.txt
python3 -I d7_n8_sin_stop.py BTC /home/user/datos-btc/BTCUSDT_um_1m.npy      # y los otros 6
python3 -I /home/user/trader-btc-investigacion/consolidacion/descargar_um.py /home/user/datos-otros SOLUSDT   # datos nuevos
```
