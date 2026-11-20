# Revisión del prompt del plan v9 contra lo hecho · 20/11/2026, 17:45

Se revisa `3-PROMPT-PLAN-v9-GANANCIA.md` criterio por criterio, con la evidencia de cada uno. Pruebas en el PC (Python 3.11) y en el teléfono con el motor de la app (Python 3.14.8), en una carpeta aparte, antes de instalar.

## Criterios de aceptación

- A1 · BIEN. `nodo/prueba_ganancia.py`: lo que deja cada apuesta (acierto, empate y fallo) exacto; la cuenta de prueba igual a la cuenta hecha a mano en tres casos, sin depender del orden y sin desbordarse; una apuesta por ventana. Paridad con el medidor de la vigilante: mismo límite normal, mismo bootstrap (misma semilla y cortes) y la misma decisión en cuatro casos (gana, pierde, gana barato y pocas).
- A2 · BIEN. `ganancia/paridad_vigilante.py` sobre los datos reales: en el PC (271 apuestas, 16:55) y en el teléfono (datos vivos), «PARIDAD BIEN» en las ocho fuentes; ninguna demuestra ganancia. Lo que escribe el nodo en `ganancia.json` coincide con la herramienta.
- A3 · BIEN. 25 de 25 no es alto; 80 de 100 pagando 0,86 pierde y no es alto; tres aciertos de lotería a 0,02 (neto +47) no demuestran nada. En `prueba_nodo.py`, 20 de 25 a mano ya no es alto; en `prueba_rutina.py`, 80 % de 25 con ganancias tampoco.
- A4 · BIEN. 210 de 300 a 0,50: GANA DINERO (demostrado), cuenta de prueba 4.948.118; con sus últimas 25 perdidas queda en pausa; 160 de 400 a 0,25 (comprando barato) también se demuestra; 70 de 300 queda PIERDE DINERO (demostrado). Una fuente así sí sube a la IA (`prueba_nodo.py`, caso 4).
- A5 · BIEN. Sin ventaja y mirando después de cada apuesta: la regla v9 arma por azar en el 3,0 % de 200 meses de 8 fuentes y 1.000 apuestas (el tope teórico es 5 %); la regla fija de la vigilante sola, mirada así, armaría en el 35,5 %. Con solo 40 meses salía 12,5 %: es la misma semilla y una muestra chica (los primeros 40 traen 5 armados); por eso la prueba usa siempre 200.
- A6 · BIEN. `operador/prueba_armar_ganancia.py`, 21 de 21: sin regla no arma; sin `ganancia.json`, con el archivo de más de 15 min o con la fuente en pausa, no arma; con una fuente de 15 min demostrada arma solo el de 15 y avisa con su dinero; con una de 5 min, solo el de 5; «operador parar», «operador automático» y «operador dinero» funcionan; `ARMAR_AL_70` pasa a `ARMAR_POR_GANANCIA` una sola vez; con una llave con futuros no arma y avisa una vez; ninguna orden ni escritura en Binance.
- A7 · BIEN. `mesa/prueba_centro_dinero.py`, 6 de 6: con `ganancia.json`, la señal y el resultado dicen el dinero y no «k de 25» ni APTA, y no salen los avisos de 75 % y 82 %; sin el archivo (la Mesa del PC), igual que antes. `prueba_centro.py` (señales frente a c12) sin fallos.
- A8 · BIEN. `prueba_nodo.py` 70 de 70, `prueba_rutina.py` 37 de 37, `prueba_aprobacion.py` 57 de 57, `prueba_paridad.py` 10 de 10 con los datos reales (121 de 121 señales iguales). Solo se ajustaron los casos que medían el «alto» por acierto, y la prueba de paridad ahora entrega el registro día por día (como en el equipo) y comprueba aparte que de golpe da lo mismo.
- A9 · BIEN. Teléfono a las 17:38: los seis programas vivos (uno de cada uno), operador «versión 4», nodo «v9», Centro relanzado con su código nuevo, regla `ARMAR_POR_GANANCIA`, sin ARMADO, `ganancia.json` escrito y con los mismos estados que en el PC. Revisión estándar de la app (`revision.sh app`): 23 de 23 en BIEN (sin Tor, salida directa, llaves en 600).
- A10 · BIEN. No existe `operador/datos/ordenes.json`; las pruebas confirman cero órdenes y cero escrituras en Binance; la llave, el importe y los topes no se tocaron.

## Hallazgos durante la construcción (corregidos)

- Al arrancar, el nodo lee tres días del registro de una vez y poda su memoria a 600 ventanas antes de apuntar: el papel de 5 min del operador quedaba con 85 de 123 apuestas. Ahora apunta antes de podar (`_apuntar_antes_de_podar`) y quedó con 124. Reinstalado solo el nodo a las 17:37 (`ganancia.sh nodo`).
- `paridad_vigilante.py` importaba el nodo viejo del equipo en vez de la copia que se probaba (orden de rutas). Corregido.
- El Centro reconocía `ganancia.json` por su hora: dos escrituras en el mismo instante pasaban por una. Ahora usa inodo, hora en ns y tamaño, como el nodo.

## Lo que no se hizo y por qué

- La vigilante no atiende pedidos por disparo: la plataforma los trata como datos. Darle la cláusula «PEDIDO DEL DUEÑO» lo negó el control de permisos de Claude Code («Undermining Oversight»). Queda para el dueño (texto en el informe de la sesión).
- Laboratorio de la ESP32 (C6): no se cambió; queda como fase 2.
- El repositorio `trader-btc` es público desde el 25/10/2026 y el bloc publicado trae la IP de la casa (11 veces), la IP vieja, el usuario de Windows y las IP internas. Volverlo privado es decisión del dueño.

## Veredicto

Los diez criterios se cumplen y el plan v9 corre en el teléfono. Hoy ninguna fuente demuestra ganancia de dinero, así que el sistema no arma ni consulta a la IA: los 20,50 USDT no están en juego. Listo.
