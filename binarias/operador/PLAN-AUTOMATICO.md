# Operador automático de binarias en la caja T95H · plan

Escrito el 16/11/2026 a las 14:03, hora de Colombia, antes de construir y antes de medir nada nuevo. Si una sesión se corta, la siguiente lee este archivo, mira las casillas de la sección 6 y sigue desde la primera sin marcar. La copia que manda es esta (`Ingresos\binarias-papel\operador\PLAN-AUTOMATICO.md`); en la caja hay una copia igual en `/data/local/tmp/operador/`.

## 1. El pedido

Suyo, del 16/11/2026 a las 13:47: que la caja T95H automatice la parte final de las binarias, las compras y los cobros, para que se hagan solos; plazos de 5, 10 y 15 minutos con la mejor estrategia para cada uno según lo ya medido; todo escrito y registrado en la caja; probado sin fondos, porque hoy la cuenta no tiene; y un plan escrito por si la sesión no alcanza.

## 2. Lo que se encontró hoy (comprobado, con su fuente)

Mercados. La API oficial de predicción de Binance (`/sapi/v1/w3w/wallet/prediction`) lista «BTC Up or Down» de 5 minutos (`btc-updown-5m-…`), de 15 minutos (`btc-updown-15m-…`), por hora y por día. Fuente: el listado real del 04/11 a las 17:56. De 10 minutos no hay: las de 10 minutos son los Contratos de Evento, que viven solo en la app, no tienen API y Binance prohíbe operarlos con programas. Hoy no se pudo repetir el listado por lo que sigue.

Llave. Desde hoy Binance rechaza toda consulta firmada con −2015, también la de saldo y también desde el PC. La causa: la IP pública de la casa cambió. La llave del 04/11 solo acepta 181.54.121.46 y hoy la casa sale por 201.221.178.15. El archivo de la llave no ha cambiado desde el 04/11. Mientras no se corrija, nadie puede leer el libro de precios, el saldo ni cotizar. En la caja nunca hubo llave: `precio_vivo.py` espera desde el 11/11 una de solo lectura que no se creó.

Caja. Encendió hoy a las 13:47 y levantó sola Tor, el centinela, el avisador y el laboratorio (600 formas vivas, 51 °C). Estuvo apagada desde el 11/11 a las 23:15. El laboratorio solo tiene dos horas de papel en vivo; lo demás son señales rehechas con velas.

Compras reales. El 12/11 la Mesa compró de verdad desde la billetera de predicción con sus toques: SUBE 4,62 USDT a 0,55 (perdió) y BAJA 4,11 USDT a 0,86 (ganó 0,57). Neto real: −4,05 USDT. Dos órdenes de esa madrugada quedaron anotadas como «SUBMITTED» y la Mesa nunca les leyó el cierre.

Comprador. El 12/11 a las 19:00 quedaron escritas, antes de medir, las reglas del comprador por ganancia esperada (`comprador\REGLAS-ANTES-DE-MEDIR.md`) y su modelo (logística de doce rasgos, huella 55ae2f665546aa40). La sesión se cortó a las 19:22 por el límite de uso: el papel alcanzó a hacer tres miradas y ninguna compra, y nada llegó a la caja ni al bloc.

Papel con precio real, que es el que cuenta. En el borrador de 15 minutos el precio real 30 s después de la señal fue 0,544 en promedio, no el 0,51 que se suponía: a ese precio el equilibrio sube a 55,5 %. Las compras «sobre la pérdida» de la serie anterior van −25,4 USDT en 84 de papel. Ninguna estrategia ha mostrado todavía ganancia con precios reales. Las cifras buenas (56 % a 59 % de aciertos) son con velas y precio supuesto.

## 3. Qué se construye

Un solo programa en la caja, `operador.py`, que corre siempre y arranca con ella.

Mira dos mercados, el de 15 minutos y el de 5 minutos. Al cierre de cada minuto calcula, para sube y para baja, cuánto vale cada lado según el modelo y cuánto cuesta en el libro: es el vector de ganancia que usted pidió el 12/11. Compra el lado cuya ganancia esperada prudente llega al margen de las reglas. Los plazos salen de ahí: en el mercado de 15 minutos se compra cuando faltan 15, 10 o 5 minutos (o cualquier minuto intermedio) y en el de 5, cuando faltan 5 o menos. Cada compra queda anotada con el plazo que le faltaba.

Tiene tres estados y pasa de uno a otro solo, sin que nadie lo toque:

1. Sin llave: mide en vivo si el modelo acierta lo que dice (probabilidad contra resultado), con velas públicas. Es lo que puede hacer hoy.
2. Con una llave que lea: papel con precios reales del libro y llenado honesto, la serie que decide si el comprador queda apto. Al ver por primera vez una llave que funciona hace la prueba sin fondos y la manda a su Telegram.
3. Con llave de operar propia de la caja, saldo en la billetera de predicción y el archivo `ARMADO`: compra de verdad, relee cada orden hasta que Binance la cierre, cobra lo ganado y lo anota.

Todo queda en `/data/local/tmp/operador/registro/` (un archivo por día con cada mirada, decisión, orden y resultado), en `estado.json` y en un parte a su Telegram.

Lo que no hace: no toca la app de Binance ni los Contratos de Evento; no usa la llave del PC; no baja el margen; no apalanca; no compra si el importe no llega al mínimo; no decide con IA.

## 4. Reglas

Las del 12/11 siguen intactas para el mercado de 15 minutos. Para el de 5 minutos y para las órdenes reales se agregó la enmienda 2 a `comprador\REGLAS-ANTES-DE-MEDIR.md`, fechada hoy antes de medir. En corto:

- Mercado de 5 minutos: mismas reglas, miradas en los minutos 1 a 4, modelo propio aprendido con 2021-2023 por el mismo procedimiento, serie de papel propia que empieza de cero.
- Importe real: el del libro B (una cuarta parte del Kelly prudente, tope del 16 % del saldo, sin pasar de lo que ofrece el libro, mínimo 2 USDT), sobre el saldo real de la billetera de predicción.
- Una orden por mercado. Antes de enviar, cotización real: si el precio medio cotizado ya no deja la ganancia prudente en el margen, no se envía.
- Freno del día: si lo perdido en el día de Colombia llega al 16 % del saldo con que empezó, no compra más hasta el día siguiente. Tope de 20 órdenes reales por día.
- Una orden solo es «comprada» si Binance lo confirma. Cualquier estado que no sea final se relee hasta que lo sea, también después de un reinicio.
- Armado: el real exige el archivo `ARMADO`, que solo se crea por orden suya («operador armar» desde su Telegram, o dicha a Claude). `PARAR` o «operador parar» lo detienen.
- Si Binance responde −2015, el operador vuelve al estado 1 y le avisa con la IP de ese momento.

## 5. Criterios de éxito, fijados antes de ver resultados

1. Paridad. Con ventana de 15, el núcleo nuevo da exactamente lo mismo que `comprador\ganancia.py` en miradas al azar de la historia (diferencia máxima menor que 1e-9), y el entrenador nuevo reproduce `modelo.json` (pesos, h y H iguales).
2. Modelo de 5 minutos hecho con el mismo procedimiento. Se informa su pérdida logarítmica en «elige» y «juzga» frente a la fórmula normal. Entra a papel con cualquier resultado, porque el papel no arriesga nada; no entra a real sin la sección 7.
3. Pruebas con un Binance simulado, todas sin fallos: compra completa, rechazo, orden que queda abierta y luego cierra, reinicio a mitad de orden, saldo que no alcanza, importe menor que el mínimo, segunda orden en el mismo mercado, freno del día, falta de `ARMADO`, −2015, y cobro.
4. En la caja: corre una hora seguida sin caerse, por debajo de 65 °C, con el registro completo, y vuelve sola tras reiniciar la caja.
5. Prueba sin fondos contra el Binance real: billetera, saldos, mercado de 5 y de 15 en curso, libro de los dos lados y una cotización que falla solo por saldo. Sin enviar ninguna orden. Bloqueada hasta que la llave pase; el operador la hace solo en cuanto pase.
6. Real: primera compra y primer cobro verificados contra la app. Hasta entonces el cobro figura como sin probar.

«Listo» solo vale para lo que cumpla su criterio. Lo que quede bloqueado se dice bloqueado.

## 6. Pasos

- [ ] 1. Plan en el PC y en la caja; enmienda 2 de las reglas; AL FRENTE del bloc.
- [ ] 2. `nucleo.py`: rasgos, modelo, vector de ganancia y decisión con ventana de 5 o 15. Criterio 1.
- [ ] 3. `entrenar.py`: reproduce el modelo de 15 y hace el de 5. Criterios 1 y 2.
- [ ] 4. `papel.py`: el comprador de papel del 12/11 con ventana de 5 o 15.
- [ ] 5. `conexion.py` de la caja: velas públicas, predicción firmada, mercado de 5 y de 15, llave propia.
- [ ] 6. `ejecutor.py`: órdenes reales con candado, topes, relectura y cobro.
- [ ] 7. `operador.py`: los tres estados, registro, parte y órdenes por Telegram, prueba sin fondos.
- [ ] 8. `simulador.py` y `prueba_operador.py`. Criterio 3.
- [ ] 9. A la caja con huellas iguales; marcha de una hora; arranque solo. Criterio 4.
- [ ] 10. Bloc, plan total (sección 7e), memoria y bóveda al día.
- [ ] 11. Con él: llave (sección 7). Criterio 5.
- [ ] 12. Con él: fondos y armado. Criterio 6.

## 7. Lo que solo puede hacer usted

1. La llave. En la app de Binance, Gestión de API. Lo mínimo es editar la llave actual y poner la IP de hoy, 201.221.178.15: con eso vuelve la Mesa del PC. Para que la caja opere sola hace falta además una llave nueva solo para ella, con Lectura y Predicción y nada más (sin spot, margen, futuros, retiros ni transferencias), restringida a esa misma IP. Se guarda en `C:\Users\ni109\.config\binance\caja.txt` con el mismo formato de `lectura.txt` y se lleva a la caja con el botón «Llave de la caja» o diciéndoselo a Claude. La llave vieja no va a la caja: tiene permisos de más y la caja tiene el ADB abierto en la red de la casa.
2. Los fondos. Pasar USDT de Spot a la billetera de predicción en la app, como el 12/11. Solo lo que esté dispuesto a arriesgar: es lo único que la llave de la caja puede tocar.
3. El armado. Escribir «operador armar» en su Telegram cuando quiera que compre sola. El operador responde con las cifras del papel y, si el comprador todavía no es apto según R6, se lo dice antes de armar.

## 8. Riesgos, dichos de frente

- No hay ventaja demostrada con precios reales. Lo más probable hoy, si se arma sin esperar el papel, es perder despacio por la comisión del 2 % y el precio. El margen del 10 % de las reglas existe para que compre poco y solo cuando el precio esté claramente mal puesto; puede pasar días sin comprar.
- Con saldos pequeños el importe del libro B casi nunca llega a 2 USDT en las compras baratas. El operador lo anota como «importe menor que el mínimo» y no compra.
- La IP de la casa cambia sin avisar y cada cambio deja las llaves sin pasar hasta que usted la actualice.
- La caja se apaga a veces. Una binaria abierta se liquida sola en Binance; lo ganado espera el cobro hasta que la caja vuelva.
- El ADB de la caja está abierto en la red de la casa. Por eso su llave solo puede llevar Predicción y la billetera, lo justo.
- El cobro por API (`batch-redeem`) no se ha probado con una posición real.

## 9. Para la sesión que siga

Leer este plan y el AL FRENTE del 16/11 en el bloc. Código en `Ingresos\binarias-papel\operador\`. Probar con `python -X utf8 prueba_operador.py`. Llevar a la caja con `python -X utf8 llevar_operador.py` (compara huellas). En la caja: `/data/local/tmp/operador/`, registro en `operador.log`, parar con el archivo `PARAR`. Nada de órdenes reales, de copiar llaves ni de crear `ARMADO` sin su orden expresa en esa conversación (candado de `settings.json`).
