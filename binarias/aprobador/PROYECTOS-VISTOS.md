# Proyectos del dueño que aparecen en el repositorio (17/11/2026)

Revisión corta (menos del 10 % del trabajo de la rutina). Solo lo que se ve en `trader-btc` y en el bloc.

| Proyecto | Dónde aparece | Estado | ¿Ayuda a las binarias? |
|---|---|---|---|
| Agente de futuros BTCUSDT en papel y en la red de pruebas de Binance | raíz del repositorio (`agente.py`, `banco.py`, `estrategias.py`, `vivo.py`) | detenido desde el 20/10/2026, se conserva como historia | Poco: de su banco salieron varias de las estrategias que se midieron; los topes de riesgo en código son el mismo patrón que hoy aplica el operador. |
| Método de un trader en 647 monedas (lista de monedas, «BMT») | rama `local/maestro-v2-2026-10-27` (c4, t1 a t3) | investigación | No: opera otras monedas y la regla del dueño es solo BTC/USDT. |
| Pulso BTC | `binarias/pulso/` (Rust, PC con WSL; carpeta `Ingresos\pulso-btc`) | corre en el PC | No para decidir: lee precio y velas y escribe a Telegram, pero no apuesta. El teléfono debe trabajar solo, así que no conviene depender de él. |
| Laboratorio de formas con red neuronal | `binarias/laboratorio/`, en la caja | investigación (244 MB, 600 formas) | Ya ayudó: su modelo de la pérdida es el núcleo del operador de Fable. No se mueve al teléfono (calor). |
| Estudio cuantitativo | `binarias/cuant/` (c1 a c12) | terminado | Sí: de ahí salen las cifras a ciegas del Centro (P21, P22) y el filtro del interés abierto que no sube, que el contexto de Claude usa. |
| Placa ESP32 de binarias | `binarias/laboratorio/placa/` | corre aparte | No para decidir; solo muestra. |
| Granja de la caja T95H | repositorio `granja-t95h` nombrado en el bloc | no accesible desde esta sesión | No se pudo ver. |
| Rutina «Proyectos: analizar y sacar lo siguiente (04:00)» | bloc, sección 6 | su rama `claude/proyectos-2026-11-17` no existe en GitHub a las 12:55 del 17/11 | No dejó entrega visible. |

Conclusión: el que más ayuda a las binarias es el estudio cuantitativo de `binarias/cuant/`, que ya alimenta al Centro y al contexto del aprobador. Ninguno de los otros hace falta para que el teléfono apruebe y compre solo.
