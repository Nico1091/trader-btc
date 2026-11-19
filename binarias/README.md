# Binarias en papel · Contratos de Evento de Binance (BTC/USDT, 10 minutos)

Este módulo estudia y vigila, en papel, apuestas binarias de sube o baja a 10 minutos sobre BTC/USDT en los Contratos de Evento de Binance. Si la apuesta acierta, Binance paga un monto fijo (entre 0,80 y 0,90 veces lo apostado); si falla, se pierde lo apostado; en empate devuelve lo apostado. No se opera futuros ni contado: las velas de 1 minuto de futuros, el interés abierto y el índice de precio solo deciden cuándo apostar.

Manda `PLAN-TOTAL.md` (v7, 04/11/2026). La evidencia está en `INFORME-TOTAL.md`, la operativa que leen el agente y Pulso en `OPERATIVA.md`, el prompt del agente de Claude en `PROMPT-OPERADOR.md` (v5) y el registro de cada paso en `BLOC-BINARIAS-TODO-EN-UNO.txt`. `GUIA-PARA-LA-GENTE.md` explica el método a quien lo quiera aplicar.

## La lógica

A 10 minutos, BTC tiende a devolverse después de estirarse. El núcleo es la ruptura de 20 velas de 5 minutos al revés: en cada decisión (minutos :00, :10, :20…, con la vela cerrada), si la última vela de 5 minutos cerró por encima del máximo de las 20 anteriores se apuesta BAJA a 10 minutos, y si cerró por debajo del mínimo, SUBE.

Cada señal llega con SÍ OPERAR o NO OPERAR. Va SÍ cuando se cumplen tres condiciones:

1. El papel del día (hora de Colombia, solo apuestas ya cerradas) va sumando.
2. Ningún SÍ ha perdido ese día.
3. El interés abierto de los futuros no subió en los 15 minutos previos (cambio de hasta +0,022 %, con la instantánea publicada 5 minutos antes de la decisión).

La primera pérdida de un SÍ lo apaga hasta el día siguiente. El dinero real solo corre en un SÍ si, además, 19 de las últimas 25 apuestas de papel acertaron (la regla del 76 % del dueño, P17) y existe el archivo `REAL_AUTORIZADO` en la carpeta del centinela, creado por su orden expresa. Ningún código apuesta: los Contratos de Evento no tienen API, Binance prohíbe los bots y la apuesta se toca a mano en la app; el aviso del SÍ real trae los pasos del toque.

## Resultados a ciegas

Las reglas se escribieron antes de ver resultados. Se eligió con 2021-2023 y se juzgó con 2024-septiembre de 2026 y con octubre de 2026, entrando 60 segundos tarde y contando el empate como fallo.

| Variante | 2024-sep 2026 | Apuestas al día | Octubre de 2026 |
|---|---|---|---|
| Núcleo | 54,4 % | 15,1 | 60,7 % |
| Papel del día sumando | 54,8 % | 2,1 | 59,0 % |
| Interés abierto que no sube | 55,2 % | 8,5 | 65,5 % |
| SÍ (las tres condiciones) | 55,5 % | 1,8 | 66,7 % |

Con pago de 0,85 hace falta acertar 54,1 % para no perder; con 0,80, 55,6 %. La ventaja es pequeña y depende del pago y de tocar en segundos: cada minuto de demora cuesta cerca de 1,7 puntos. Medido con el índice de precio con que liquida Binance, el núcleo de 2024-2026 queda en 54,1 %.

Se descartaron con prueba: seguir las rupturas (43-46 %), operar con todo a favor, SMC, ICT y CRT a 10 minutos (49-52 %), VPIN, el régimen por autocorrelación, las horas del día, el metaetiquetado, el volumen alto sobre el SÍ, las velas de confirmación, las cinco líneas como filtro (P18: +0,30 puntos sin diferencia con el azar), la martingala y las estrategias «del 98 %». La regla del 76 % no sube el acierto (P17), pero se aplica por ser orden del dueño.

## Carpetas

- `dispositivos/`: lo que corre todo el día en la caja Android (principal) y en el teléfono (respaldo) con Termux: arranque, avisos por Tor a Telegram, aviso de relevo cuando la caja deja de latir y el semáforo SÍ o NO (`semaforo.py`, v3.3). Cada SÍ o NO sale como foto con las cinco líneas (`graficas.py`, idéntica a Pulso píxel a píxel) y cada SÍ cerrado trae su comprobante en PDF con enlaces a las velas oficiales de Binance (`comprobantes.py`); a las 00:15 llega el resumen del papel del día anterior. Todo en Python puro, sin librerías.
- `pulso/`: Pulso BTC, el nodo de avisos en Rust sin dependencias (gráficas de velas, las cinco líneas en 1 minuto, informes, lectura del mercado y voz) y su versión para Android. Se compila en una caja sellada sin red con `caja.sh` (y `caja-prueba.sh` para una copia de prueba).
- `herramientas/`: cómo va el papel de hoy (`estado.py`), la auditoría de un día con los archivos oficiales de Binance (`auditor_dia.py`), la paridad de las cinco líneas entre Rust y Python con sus 12 ventanas fijas (`paridad_lineas.py`), la prueba en seco del semáforo (`prueba_semaforo.py`), el posible plan en Descargas y la USB (`posible_plan.py`) y la sincronización de este repositorio (`sincronizar_repo.py`).
- `cuant/`: la investigación cuantitativa, de C1 a C9f, con sus resultados.
- `pruebas/`: el banco a ciegas, de t10 a t33.
- `binarias.py` y `motor/`: el centinela v4 y su selección mensual.
- `sesiones/`: la nota de cada sesión de trabajo. `historia/`: versiones anteriores del centinela y del plan.

## Cómo repetir las pruebas de noviembre

```
python -I cuant/c9_mejoras.py
python -I cuant/c9b_indice.py CARPETA_NUEVA_PARA_EL_INDICE
python -I cuant/c9c_interes.py CARPETA_NUEVA_PARA_EL_INTERES_ABIERTO 600
python -I cuant/c9e_regla76.py CARPETA_DEL_INTERES_ABIERTO
python -I cuant/c9f_lineas.py CARPETA_DEL_INTERES_ABIERTO
python -I herramientas/paridad_lineas.py
python -I herramientas/auditor_dia.py AAAA-MM-DD
```

Las velas de 1 minuto con compra agresiva (`datos/BTCUSDT_um_1m_tb.npy`) no van en el repositorio; salen de las velas públicas de data.binance.vision.

## Lo que queda fuera del repositorio

Velas y libros (`datos/`), cachés, estados y registros de apuestas, capturas de pantalla, binarios de Tor y del APK, y cualquier clave. Las claves se leen al ejecutar desde archivos privados de cada equipo.
