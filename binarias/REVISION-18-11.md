# Revisión de binarias · 18/11/2026, 11:35 a 11:45 (hora de Colombia)

Hecha con REVISION-PROMPT.md, solo lectura: nada compró, armó ni tocó la cuenta de Binance.

## Resultado: TODO BIEN en el teléfono, la nube, el dinero y las pruebas. Pendiente: la caja no responde desde las 11:31.

A. Teléfono, app Binarias (versión 3): BIEN en todo.
- Motor dentro (python3.14 y python3), sin el programa de Tor.
- Seis programas, uno de cada uno: centinela, avisos, centro, nodo, operador y publicador. Ningún Tor.
- Salida directa (AVISOS_TOR, NODO_TOR, OPERADOR_TOR y PG_TOR vacíos); certificados de la app en los cuatro que salen a internet.
- Ocho llaves en 600 y carpetas en 700 (binance/operar.txt; binarias/telegram, nodo, rutina, github, llamada/; publicador-github).
- Inicio automático de HyperOS permitido, fuera del ahorro de batería, RUN_ANY_IN_BACKGROUND permitido.
- Código idéntico al del PC: 29 de 29 archivos (binarias.py está en la raíz de binarias-papel).
- Depuración por wifi apagada, sin puerto de adb en la red.

B. Termux del teléfono (respaldo): BIEN. Ningún programa ni Tor; su arranque apartado; el respaldo que despierta la app;
arrancar.sh sin Tor.

C. Caja: SIN REVISAR EN VIVO. Dejó de responder a las 11:31:35 (el nodo del teléfono la da por caída; no responde a ping ni
a adb). Lo último comprobado (11:05): centinela, avisos y nodo uno de cada uno, operador con PARAR, sin Tor, sin llaves de
Binance, rutina ni GitHub. No afecta al dinero: el teléfono hace todo solo. Hay que mirarla en persona (corriente o reposo).

D. Cadena de decisión: BIEN.
- Rutina activa, con las instrucciones del 18/11 y su token; última corrida (10:10) terminada bien.
- Nodo: decisor rutina, token y GitHub listos.
- El teléfono lee en GitHub la decisión real de la prueba de las 10:10 (NO COMPRAR) y un id que no existe da nada.

E. Operador y dinero real: BIEN.
- Llave: pasa; restringida por IP; sin retiros, transferencias, margen ni futuros (trae compraventa de contado, permitida).
- Billetera de predicción: 20,50 USDT. Cotización real de 2 USDT: 0,46, sin enviar nada.
- Estado 2, sin ARMADO; regla ARMAR_AL_70 puesta (se arma sola con una estrategia en 18 de 25).
- Un solo operador vivo: el de la app (Termux 0; caja con PARAR en lo último visto).

F. Red: BIEN en el teléfono (sale con 201.221.178.15, la de la casa; Telegram directo responde). La caja, sin revisar.

G. Pruebas en el PC: nodo 65 de 65, rutina 29 de 29, aprobación 50 de 50, regla del 70 % 16 de 16, publicador 42 de 42.

H. Registro: GitHub al día (rama binarias/plan-v7-2026-11-04, 701cfcc, igual al origen); bloc y memoria al día.

I. Higiene (se le dice al dueño; no se borra nada sin su sí): en Descargas hay claves en texto plano: «Clave para API
Rutina.txt», «Claves api gratuitas.txt», «Claves rivadas c;laude.txt», «claves metamask.txt», «credenciales gumroad.txt»,
«credenciales the hacker news.txt» y «credenciales xiaomi.txt».

Arreglos de las herramientas de prueba (no del sistema): comprobar_lectura.py buscaba el nodo en la carpeta de Termux; ahora
usa la casa de quien lo corre. Para probar a mano dentro de la app hay que darle SSL_CERT_FILE, como hace la app.
