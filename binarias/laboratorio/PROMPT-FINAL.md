# Prompt 3 · Prompt final del laboratorio

Versión 1: copia fiel del plan aprobado el 11/11/2026 a las 11:39 (laboratorio\PLAN-LABORATORIO.md).
Versión 2 (11/11/2026, 20:40), consolidada con REVISION.md y la primera construcción. Cambios, todos marcados «v2» abajo:
- Tope de 12 formas vivas por familia (mismos disparos, filtros, sentido y plazo); las demás esperan cupo y entran en la
  rotación diaria, las de mejor «elige» primero (REVISION 2.3 y 2.4: a 15 min la valla es blanda y las mejores de
  «elige» caen a cerca de 54 % a ciegas).
- RSI de Cutler y ventanas deslizantes por tramos (REVISION 1.2; en Android de 32 bits numpy no acepta vistas de más de 2 GB).
- Archivos nuevos: velas.py (historia, rejilla densa e interés abierto), busqueda.py (tandas), llevar.py (a la caja con
  huellas), marcar_bloc.py, medir_caja.py y revisar_prob.py; herramientas\estado.py lee el latido del laboratorio.
- Medido en el paso 6: 1.000 formas vivas en 1,6 s por cierre de 5 min a 53 °C; una forma en la historia, 0,39 s;
  paridad exacta PC-caja (huella 0ce55b0f72196ac0cd064ae3) y con la clase Centro en 40 días.

```text
PROMPT FINAL · Laboratorio de binarias BTC/USDT · versión 2 (11/11/2026)

1. PROPÓSITO
Construir y dejar corriendo en la caja T95H un programa que emule en papel y en tiempo real hasta
1.000 formas de hacer binarias sobre BTCUSDT, las pasadas y las que una red neuronal propia
proponga cada hora; que guarde cada prueba y cada señal en SQLite; que informe al Telegram del
dueño cuáles rinden más y atienda sus peticiones. No apuesta, no conoce llaves y no decide el
dinero real.

2. REGLAS QUE NO SE DISCUTEN
- Solo papel. Ningún archivo del laboratorio importa conexion.py, lee llaves ni escribe en la
  carpeta centinela; de ella solo lee el historial de velas. REAL_AUTORIZADO y semaforo.json no
  se tocan.
- Solo velas cerradas; entrada al cierre del minuto siguiente (60 s tarde); empate = fallo; una
  apuesta abierta por forma.
- Las formas a favor del movimiento se emulan para comparar. Por la regla 6.2 de PLAN-TOTAL, al
  protocolo de dinero solo pasan las de devolución.
- Biblioteca estándar y numpy, que ya están en la caja. Nada se instala ni se compila antes del
  paso 12.
- Binance directo; Telegram por Tor con avisos.enviar. Ninguna IA externa. Todo lo hace esta
  sesión, sin agentes ni flujos.
- Calor: un hilo y nice 10; la búsqueda y el entrenamiento se pausan a 70 °C y vuelven a 62 °C.
  Un argumento desconocido nunca lanza trabajo pesado.
- Mismo código en el PC y en la caja; sumas en bucle o con numpy (sum() cambia entre 3.11 y 3.14)
  y tiempos con dtype=np.int64.

3. ESTADO DE PARTIDA, MEDIDO EL 11/11/2026
- Caja: Android 10, ARMv8 de 4 núcleos a 1,5 GHz en 32 bits, 3,2 GB de memoria libres, 21 GB de
  disco, 50 °C en reposo; Python 3.14.8, numpy 2.5.4, sqlite 3.54.1; 0,52 s por pasada de 200.000
  muestras. Tiene clang y whisper.cpp; no tiene llama.cpp.
- Historial en la caja: 3.595.265 velas de 1 min, del 31/12/2019 a las 19:00 al 01/11/2026 a las
  12:04 (centinela/datos/BTCUSDT_um_1m_vivo.npy).
- Reloj de la caja en hora desde su reinicio del 11/11 (hora automática encendida). Su centinela
  corrió de las 14:35 a las 19:42 con el papel rehecho de las velas y se detuvo a las 19:42 con
  ESPERA_ESTADO y PARAR; Tor sigue vivo. El teléfono no está por ADB: su estado de hoy queda sin
  comprobar y el centinela de la caja vuelve cuando se le copie.
- En la caja desde el 11/11, 19:45: quince.py del 07/11 (09c1b308…) y arrancar.sh con ESPERA_ESTADO
  y la línea del laboratorio (34bffd3d…).
- Referencia a 15 min, 2024-sep 2026: E1 54,6 %, E2 55,1 %, E3 57,7 %, E4 54,4 %, E5 51,8 %;
  equilibrio 52,04 %. A 10 min el equilibrio es 54,05 %.

4. ARCHIVOS (PC: Ingresos\binarias-papel\laboratorio; caja: /data/local/tmp/laboratorio, 777)
- base.py: SQLite en modo WAL. Tablas velas, formas, pruebas, senales, redes, eventos, peticiones
  y salida (cola de mensajes). Copia diaria; se guardan siete.
- rasgos.py: una sola función para historia y vivo. Los diez rasgos de t33_indice.py más distancia
  al máximo y al mínimo de 20 y 50 velas, Bollinger, RSI de 5 y 15 min, cuerpo de la vela y racha
  (19 entradas).
- formas.py: formas pasadas, gramática y generador (parte 5).
- red.py: las dos redes (parte 5), con numpy; esp32-neurona\placa\red.py como referencia.
- juez.py: pruebas a ciegas, vallas y rotación (parte 6) con cuant\validacion.py.
- emulador.py: papel en vivo con la medición de mesa\centro.py; resultado con futuros y con el
  índice de precio.
- partes.py: tablero, resumen, parte diario y avisos (parte 7).
- peticiones.py: lee el chat del dueño y atiende la lista cerrada (parte 7).
- laboratorio.py: ciclo, instancia única, PARAR, guardia de calor y guardia de reloj.
- prueba_laboratorio.py y probar.sh: paridad, fuga de futuro, candado y prueba en seco.
- herramientas\traer_laboratorio.py: copia la base al PC cuando está encendido.
- Se tocan: dispositivos\arrancar.sh (una línea que llama al arranque del laboratorio y la espera
  ESPERA_ESTADO), herramientas\estado.py (edad del latido con el reloj del PC), PLAN-TOTAL.md
  (sección 7d), PROMPT-REVISION.md (sección 11) y el bloc.

5. FORMAS Y REDES
- Una forma es un disparo, sus filtros, un sentido (al revés o a favor) y un plazo de 10 o 15 min.
  Guarda su origen: pasada, red, azar, dueño o IA.
- Formas pasadas, fijas y con su regla original: E1 a E5 de mesa\centro.py; el banco de
  motor\senales.py y motor\patrones_std.py con las configuraciones de seleccion.json; las
  variantes de cuant\c12_estudio_06nov.py; la neurona de t33.
- Disparos de las nuevas: ruptura de N velas de 5 min (N de 10 a 120); cierre fuera de Bollinger
  (ventana de 10 a 60, ancho de 1,5 a 3,0); RSI de 5 o 15 min sobre U o bajo 100 − U (U de 65 a
  85); rendimiento de m minutos mayor que z volatilidades (m de 5 a 60, z de 1,0 a 3,5); posición
  en el rango de H horas (H de 1 a 24) más allá del cuantil q (de 0,85 a 0,98); y la red sola. Se
  admiten dos disparos a la vez.
- Filtros: interés abierto que no sube (0,022 %, fijo), franja horaria, volatilidad 15/240 y
  confianza de la red de mercado (de 0,52 a 0,62) a favor de la apuesta.
- Red de mercado: perceptrón de 19 entradas, 16 y 8 neuronas con tanh y salida sigmoide; una por
  plazo. Aprende con 2021-2023; de 2024 en adelante, cada mes lo predice una red ajustada solo con
  datos anteriores, con purga de un plazo. Se reajusta cada día a las 00:30. Línea base: la
  neurona de t33; si la red no la supera en 0,3 puntos en el tramo de elección, se usa la neurona
  y se informa.
- Red de búsqueda: recibe la ficha codificada y predice su margen sobre el equilibrio. Cada hora
  ordena 2.000 fichas al azar y manda a prueba las 40 mejores (origen «red») y 10 al azar (origen
  «azar», que mide si la red de búsqueda aporta). Aprende de todas las pruebas guardadas.

6. CRITERIOS, ESCRITOS ANTES DE VER RESULTADOS
- Tramos: aprende 2021-2023; elige ene-2024 a jun-2025; juzga jul-2025 a oct-2026; después, vivo.
- La ficha se guarda con su huella antes de probarse. Ningún parámetro cambia después: un cambio
  es otra forma.
- Entra a vivo la forma nueva que pasa «elige»: 300 señales o más, Wilson inferior al 95 % sobre
  el equilibrio y Benjamini-Hochberg con q = 0,05 en su tanda. Su cifra de «juzga» se calcula una
  sola vez al entrar y se muestra como «a ciegas». Las pasadas entran todas.
- En vivo, hasta 1.000 formas (confirmado en el paso 6: 1,6 s por cierre a 53 °C) y como mucho 12
  por familia; las demás esperan cupo (v2).
- Estados: «en observación» hasta 100 cerradas; «prometedora» con 100 o más y 1 punto sobre el
  equilibrio; «apta en papel» con 300 o más, Wilson inferior sobre el equilibrio y «juzga» 1 punto
  o más sobre el equilibrio; «descartada» con 100 o más y Wilson superior bajo el equilibrio, o
  30 días sin llegar a 100.
- Rotación diaria: salen las descartadas y entran las que esperaban cupo, las de mejor «elige» primero
  y sin pasar de 12 por familia (v2). Las pasadas no rotan.
- El tablero ordena por Wilson inferior en vivo. El parte diario trae el acierto que el azar solo
  le daría a la mejor de N formas con ese n (acierto_maximo_por_azar) y el rendimiento por origen.
- «Apta en papel» no autoriza dinero: la forma pasa al protocolo de la sección 6 y a la orden del
  dueño.
- Cada cifra se informa a pagos de 0,80, 0,85 y 0,90 (10 min) y a compra de 0,50, 0,51 y 0,53
  (15 min).

7. TELEGRAM Y PETICIONES (texto directo, por el bot de siempre, con el prefijo «Laboratorio»)
- Tablero: un mensaje que se edita cada 5 min con las diez mejores formas en vivo.
- Resumen cada hora: las tres mejores de la hora y de hoy, con su neto.
- Parte diario a las 6:00: formas nacidas, probadas, admitidas y descartadas; resultados en vivo;
  rendimiento por origen; estado de las redes; horas de marcha, temperatura máxima y pausas.
- Aviso aparte, uno por hora como máximo: forma que queda prometedora, apta o descartada;
  laboratorio detenido o de vuelta; reloj mal; calor.
- Peticiones, solo desde el chat del dueño y con lista cerrada: mejores [hoy|semana|todo];
  forma F-n; estado; origen; pausa; sigue; tope N; cada N (minutos del resumen); probar <disparo,
  parámetros, sentido, plazo>. La caja mira el chat cada 20 s sin consumir los mensajes
  (getUpdates sin offset) y anota la petición y la respuesta.
- Ejemplo de formato, con cifras inventadas:
    Laboratorio · 11/11 14:35 · 640 formas en vivo · caja 52 °C
    1. F-0142 · red · 15 min al revés · 31 de 52 (59,6 %) · últimas 25: 16 · a ciegas 55,8 % en 1.940
    2. F-0002 · pasada · 15 min al revés · 12 de 21 (57,1 %) · a ciegas 55,1 % en 10.244
    Hoy: 1.200 formas nuevas, 31 entraron a vivo, 12 descartadas. Es papel.

8. ORDEN DE TRABAJO (marcar en el bloc al cerrar cada paso)
⬜ 0. Hooks: aplicar H1 y H2 con respaldo y prueba en seco.
⬜ 1. Caja: detener su centinela con ESPERA_ESTADO; reloj en hora con settings put global
      ntp_server o cmd alarm set-time, comprobado con date; quince.py y arrancar.sh nuevos con su
      huella; el centinela vuelve cuando reciba el estado del teléfono (pide el teléfono por USB).
⬜ 2. Escribir PROMPT-HOOKS.md, PROMPT-ORGANIZADOR.md y PROMPT-FINAL.md; sección 7d en
      PLAN-TOTAL.md; AL FRENTE y ENCARGOS en el bloc.
⬜ 3. Aplicar PROMPT-REVISION.md al plan y a este prompt; hallazgos en laboratorio\REVISION.md;
      consolidar.
⬜ 4. Construir en el PC base, rasgos, formas, juez, red, emulador, partes, peticiones y
      laboratorio.
⬜ 5. Probar en el PC: E1 a E5 idénticas a centro.py en 40 días y las demás pasadas idénticas a
      su código de origen; ninguna señal anterior a T cambia al recortar el historial en T;
      candado; 30 min en seco con datos en vivo y sin Telegram.
⬜ 6. Primera construcción de rasgos y redes en el PC; llevar todo a la caja con huellas; paridad
      PC-caja; medir el tope de formas; 30 min en seco en la caja.
⬜ 7. Arranque: línea en arrancar.sh, lanzado desde Termux para que tome el bloqueo de reposo;
      reinicio de prueba.
⬜ 8. Telegram: tablero, resumen, primer parte real, un aviso de prueba y cada petición de la
      lista, confirmados por el dueño en su teléfono.
⬜ 9. 48 horas de marcha; auditoría de un día de señales contra las velas oficiales.
⬜ 10. Revisión final contra lo construido; ajustar este prompt; informe.
⬜ 11. Consolidar: bloc, PLAN-TOTAL.md, memoria, bóveda, GitHub con sincronizar_repo.py y USB.
⬜ 12. IA pequeña en la caja: compilar llama.cpp con dos hilos y guardia de calor; bajar por Tor
      un modelo de menos de 0,6 GB de su fuente oficial; medir. Se enciende solo si, con un hilo,
      la caja no pasa de 62 °C, responde en 60 s o menos y traduce bien 45 de 50 peticiones de
      prueba a la lista cerrada. Encendida, propone fichas con origen «IA». Si no cumple, queda
      apagada y se informa con las medidas.

9. «LISTO»
Se dice solo con los pasos 5, 6, 8 y 9 cumplidos y sin preguntas de la revisión «sin comprobar».
El informe separa lo que corre del veredicto sobre las formas y del resultado del paso 12. Con
57 % de acierto real, una forma necesita unas 400 señales en vivo para quedar apta; con 55,5 %,
unas 800.

10. FRENOS
Ante cualquier negación, ejecutar PROMPT-HOOKS.md y avisar al dueño con el cambio exacto.

11. DESPUÉS
El tablero dentro de la aplicación del teléfono y una página en el Centro del PC.

12. TRATO
De usted, sin el nombre del dueño, también en Telegram. Hora de Colombia. Ninguna cifra sin su n.
```
