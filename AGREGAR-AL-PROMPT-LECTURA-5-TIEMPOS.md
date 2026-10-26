# Texto para añadir al prompt de la rutina de trading (26/10/2026)

**Requisito previo:** la rutina necesita el repositorio `trader-btc` en sus fuentes (claude.ai → la rutina → Editar → Repositorios), con los commits de la rama `claude/encargo-cloud-md-q0u3ex` ya subidos. Sin el repositorio, el script no existe en su máquina.

Pegar justo debajo de la sección «SOLO OPERAS TÚ»:

---

LECTURA RÁPIDA EN 5 TIEMPOS (pedido de Nicolás del 26/10/2026: más rápida y con foto de cada tiempo)
- Antes de cada decisión del libro CLAUDE, corre: `python3 -I consolidacion/lectura_mercado.py /tmp/lectura`. Tarda unos 2 segundos.
- Deja en /tmp/lectura:
  - `resumen.txt`, con una línea por tiempo: dirección, cambio, rango, posición en el rango, volatilidad frente a su media, pendiente y patrón de la última vela. Los cinco tiempos son la última hora en velas de 5 min, 3 horas en 5 min, 16 horas en 15 min, 1 día en 1 h y 3 meses en velas diarias.
  - Debajo de esas líneas: el contexto (cierre de ayer frente a la SMA 50), el ATR14 y los niveles de hoy de P05b y P05c.
  - Las cinco fotos de velas (`1_5min.png` a `5_3meses.png`).
- Lee `resumen.txt` y mira las cinco fotos con la herramienta de lectura de archivos. Cada foto dice cosas distintas:
  - 3 meses y 1 día: la tendencia de fondo.
  - 16 horas: la estructura de hoy.
  - 3 horas y 5 min: el momento de entrar y el riesgo inmediato.
- Escribe en el diario, en una línea, qué viste en cada tiempo y cómo pesó en tu decisión.
- Reglas medidas el 26/10 (consolidación, tareas 10 y 11). Úsalas así:
  - Decide el lado con el contexto lento: cierre diario frente a su SMA 50. Sobre ella, solo largos (P11, P05b, P05c). Bajo ella, P05b solo en corto, y ningún largo de P05b ni de P11.
  - No exijas que todos los tiempos vayan a favor para entrar: medido en 2020-2026, eso hace entrar tarde y empeora (P05b largo pasa de +21,6 % a −1,1 % en la prueba). Usa los tiempos cortos para ver el riesgo (un rebote fuerte contra el contexto, volatilidad mucho mayor que su media) y para no entrar en el peor momento, no como condición de entrada.
- Si el programa dice «Lectura INCOMPLETA: NO OPERAR», no operes en esa pasada.
- El programa no decide ni abre nada: decides tú.

---

Además, en «LO QUE QUIERE NICOLÁS»: la rutina sigue cada 6 horas. El 26/10 la pasada de las 14:05 UTC falló por el límite de uso de la cuenta; Nicolás decidió no bajar la frecuencia.
