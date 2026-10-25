---
tags:
  - area/cripto
  - tipo/proyecto
creado: 2026-10-19
estado: activo
ruta: C:\Users\ni109\Ingresos\trader-btc
---

# Trader BTC seguido

Agente que opera BTC «seguido»: un ciclo tras otro, de segundos a minutos, leyendo el mercado en segundos, minutos, horas y días, con una probabilidad por ciclo y pausas de seguridad por tandas de 100 a 800 ciclos. Pedido el 19 de octubre de 2026 y corregido por Nicolás el 20: el primer diseño operaba por días (velas de 5 minutos a 1 hora) y no era lo que pidió. Continúa [[arbitraje-cero-gas]], cuya estrategia MEZCLA de 1 hora sigue siendo la única con ventaja medida.

## Dónde vive y cómo se usa

Código en `C:\Users\ni109\Ingresos\trader-btc\`, en Python con biblioteca estándar únicamente y con historial git local sin remoto. El informe para Nicolás está en `INFORME-TRADING-SEGUIDO.md`, en esa misma carpeta.

- Panel: `panel.html`, que se abre con el Buscador y se rehace cada 5 segundos.
- Arrancar y parar: `ARRANCAR AGENTE.cmd` y `PARAR AGENTE.cmd`. Un archivo `PAUSA` impide abrir ciclos y uno `REANUDAR` levanta la detención de una tanda.
- Diario local en `diario/`: ciclos, eventos, resumen por minuto y velas de 1 s grabadas.

## Decisiones tomadas con Nicolás

- Presupuesto de 40.000 pesos, unos 9,7 USDT por libro.
- A Binance se llega por la red normal; lo demás (calendario macro, agenda de Trump, miedo y codicia, otras casas), por Tor.
- Ningún broker mexicano, ninguna IA ni plataforma de terceros ve las operaciones.
- Dinero real bloqueado: el agente no tiene ningún camino de órdenes.

## Estado al 20/10/2026

Por orden suya de las 20:40, el agente prueba como si empezara con 40.000 pesos por libro (12,59 USDT a 3.177,85 COP por USDT, tasa de compra en Binance P2P) y queda moviéndose hasta que él diga: corre desde las 21:05, arranca solo con Windows (valor `AgenteTradingSeguido` en el registro de inicio de su usuario) y un candado impide dos agentes a la vez. Lleva cuatro libros: contado BTCUSDT, BTC/FDUSD con órdenes de creador, futuros BTCUSDT y un testigo que opera seguido sin filtro. Gasta el 0,55 % de un núcleo. La paridad entre el banco de pruebas y el código real del agente dio 704 ciclos idénticos, y en vivo se probaron la pausa, el corte de golpe con un ciclo abierto y los accesos de arranque y parada.

Lo medido con 14,86 millones de segundos (mayo a octubre de 2026): la dirección del precio a minutos es casi impredecible (AUC de 0,51 a 0,56) y operar seguido pierde en todos los instrumentos por la comisión. En el tramo final, con 40.000 pesos: contado −17,8 %, BTC/FDUSD −39,6 % y futuros −37,6 %. Con la regla de seguridad el agente casi no entra (0 a 4 ciclos en un mes). Detalle en [[2026-10-20 Trader BTC seguido]].

## Pendiente

- Decisiones de Nicolás: sumar la MEZCLA de 1 hora como libro aparte y cómo llevarlo a la nube. Binance responde 451 a las conexiones desde EE. UU., también a servidores en la nube de esa región, y su regla de privacidad pide que ningún tercero vea sus operaciones.
- Clave nueva de la red de pruebas de Binance en `claves-testnet.env` para probar órdenes reales de mentira.
- No detener el agente hasta que él lo diga.

Desde el 24/10/2026, el agente de planeación de trading de la nube estudia y prueba cada 12 horas cómo operar con Claude como quien decide, con el expediente de este proyecto: ver [[Agentes de la nube]].

Parte de [[Cripto y trading]].
