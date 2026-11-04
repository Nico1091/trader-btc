# Binarias SÍ o NO

Contratos de Evento de Binance · BTC/USDT · 10 minutos

Guía para aplicar el método: de dónde sale cada señal, cuándo se opera y cuándo no, cuánto se apuesta y qué dicen los números medidos desde 2021.

## Qué se apuesta

Cada apuesta es una binaria de sube o baja a 10 minutos sobre BTC/USDT en los Contratos de Evento de Binance, que solo se operan desde la app del teléfono. Binance fija el pago en el momento de apostar, según la volatilidad: si la apuesta acierta, gana entre 0,80 y 0,90 veces lo apostado; si falla, pierde lo apostado; si al vencer el índice de precio queda igual, Binance devuelve lo apostado. No hay apalancamiento ni posiciones que vigilar después de tocar.

## La idea

A 10 minutos, el Bitcoin tiende a devolverse después de estirarse. El método apuesta siempre contra el estirón: si el precio rompe por arriba el rango de los últimos 100 minutos, apuesta a que baja; si lo rompe por abajo, apuesta a que sube.

## La señal

Cada 10 minutos, en los minutos :00, :10, :20, :30, :40 y :50, se mira la última vela de 5 minutos ya cerrada y se compara con las 20 velas anteriores:

- Si cerró por encima del máximo de esas 20 velas: **BAJA a 10 minutos**.
- Si cerró por debajo del mínimo: **SUBE a 10 minutos**.
- Si quedó dentro del rango, no hay señal.

La decisión espera siempre a que cierre la vela de 5 minutos; nunca se decide con una vela en formación. Aparecen unas 15 señales al día. Todas se anotan en papel; solo algunas llegan como SÍ.

## Cuándo se opera: el SÍ o NO

Cada señal llega marcada SÍ OPERAR o NO OPERAR. Es SÍ solo cuando se cumplen tres condiciones al mismo tiempo:

- El papel del día va sumando: el resultado de todas las señales del día, ya cerradas y contadas desde las 0:00 (hora UTC−5), es positivo.
- Ningún SÍ ha perdido ese día.
- El interés abierto de los futuros de BTC no subió en los 15 minutos previos. Cuando sube, el estirón trae posiciones nuevas y el precio se devuelve menos.

La primera pérdida de un SÍ cierra el día. Como el papel arranca cada día en cero, las primeras señales del día siempre llegan como NO.

Ejemplos de aviso:

```
SÍ OPERAR · BTC BAJA a 10 min · precio 77.450,10 · vence 01:20
papel de hoy +0,85 (1 de 1 acertadas) · interés abierto −0,031 % en 15 min (no sube)

NO OPERAR · BTC SUBE a 10 min, solo en papel
papel de hoy −1,15 (1 de 3 acertadas)
```

Cada aviso llega como foto: la gráfica de 1 minuto con las cinco líneas y el aviso en el pie. El papel se cuenta en apuestas: cada acierto suma 0,85 y cada fallo resta 1.

## Qué hacer cuando llega un SÍ

1. Abra la app de Binance, entre a Contratos de Evento y elija BTCUSDT con vencimiento de 10 minutos.
2. Revise el pago que ofrece la app. Con 0,85 hay que acertar el 54,1 % de las veces para no perder; con 0,80, el 55,6 %. Si el pago está por debajo de 0,85, no entre.
3. Toque el sentido del aviso, SUBE o BAJA, en los primeros segundos. Cada minuto de demora resta cerca de 1,7 puntos de acierto.
4. Apueste siempre el mismo monto, el mínimo de 5 USDT, y nunca más del 16 % de su saldo: con 5 USDT, el saldo debe ser de 31,25 USDT o más. Nunca doble después de perder.
5. Si ese SÍ pierde, termine el día, aunque lleguen más señales.

## Las cinco líneas

La gráfica de velas de 1 minuto de las últimas dos horas y media lleva cinco líneas:

- **Azul.** Techo y piso. El techo se apoya en los máximos y el piso en los mínimos; cada uno se ajusta para pasar lo más cerca posible de ellos sin que ninguna vela lo cruce.
- **Ámbar.** Techo y piso cortos, trazados igual desde el inicio de la última caída o de la última subida.
- **Violeta, discontinua.** La recta de la mitad: el centro exacto entre el techo y el piso.

Las líneas muestran cuándo el precio está estirado y hacia dónde va el canal. Se probaron como filtro del SÍ con los datos de 2021 a 2026 y no suben el acierto: sirven para leer el momento; la apuesta la decide el SÍ.

## Lo que dicen los números

Las reglas se escribieron antes de mirar resultados, se ajustaron con 2021 a 2023 y se juzgaron con datos que no se habían usado: de enero de 2024 a septiembre de 2026, y octubre de 2026 aparte. Todas las cifras entran 60 segundos tarde, como quien toca a mano, y cuentan el empate como fallo.

| Qué se apuesta | Acierto ene 2024-sep 2026 | Apuestas al día | Octubre de 2026 |
|---|---|---|---|
| Todas las señales | 54,4 % | 15,1 | 60,7 % |
| Solo cuando el papel suma | 54,8 % | 2,1 | 59,0 % |
| Solo con interés abierto que no sube | 55,2 % | 8,5 | 65,5 % |
| **SÍ: las tres condiciones** | **55,5 %** | **1,8** | **66,7 %** |

De cada 100 SÍ, unos 55 aciertan; con pago de 0,85, el punto de no perder es 54,1. Con 5 USDT por apuesta, el SÍ habría ganado unos 245 USDT entre enero de 2024 y septiembre de 2026, unos 7 USDT al mes, y en su peor racha habría estado unos 140 USDT abajo. Octubre de 2026 fue un mes fuera de lo común y no debe tomarse como lo normal. Son resultados de pruebas con datos pasados y de papel en vivo, y no aseguran lo que pase después.

## Cómo se comprueban los resultados

Cada SÍ que cierra deja un comprobante en PDF con la hora, el sentido, el precio de entrada y el de vencimiento, y enlaces que abren en Binance las velas oficiales de esos minutos y el índice de precio con que se liquida. Cualquiera puede abrir esos enlaces y ver el mismo resultado. Al día siguiente llega además el resumen de todas las señales del día, una por fila.

## Lo que no hay que hacer

- Doblar el monto después de perder (martingala). En una prueba pública, cerca del 45 % de las cuentas no pudo seguir doblando y quebró.
- Creer en estrategias «del 98 %». Ninguna prueba independiente las sostiene: esas cifras salen de la martingala o de contar días ganados en vez de apuestas.
- Apostar a favor de la ruptura, o solo cuando todo parece a favor. A 10 minutos eso pierde, con aciertos entre el 43 y el 52 %.
- Usar como señal a 10 minutos las noticias, los patrones de SMC, ICT o CRT, o las horas del día. Se probaron y no dan ventaja.
- Buscar apalancamiento. Las binarias no lo tienen; en otros productos multiplica las pérdidas.
- Esperar velas de confirmación extra después del aviso. Se probó: baja el acierto de 54,4 a 53,0 %.
- Dejar que un programa apueste por usted. Binance prohíbe los bots en los Contratos de Evento y la apuesta se toca a mano.

## Antes de poner dinero

- Use solo dinero que pueda perder completo. Con el mínimo de 5 USDT, una cuenta de 100 USDT resiste 20 pérdidas seguidas.
- Practique primero en papel: anote al menos 20 avisos con el pago que ofrecía la app, los segundos que tardó en tocar y el resultado.
- Verifique que los Contratos de Evento estén disponibles y permitidos en su país. En la Unión Europea, la autoridad de mercados (ESMA) prohibió en 2018 vender opciones binarias a clientes minoristas.
- Regla de prudencia: con dinero real, opere solo cuando 19 de las últimas 25 señales en papel hayan acertado (76 %); el resto del tiempo, espere. En las pruebas no subió el acierto, pero hace que se arriesgue muy pocas veces, unas dos o tres al mes.
- Esta guía describe un método que todavía se mide en papel. No es una recomendación de inversión.

Versión del 4 de noviembre de 2026. Cifras de pruebas a ciegas con velas públicas de Binance, de enero de 2021 a octubre de 2026, y de la página oficial de Binance sobre los Contratos de Evento, actualizada el 28 de octubre de 2026.
