# Binarias en papel (Contratos de Evento de Binance) · módulo del proyecto

Manda `PLAN-TOTAL.md` (v6, 03/11/2026, congruente): solo devolución en BTC/USDT, real solo en días VERDES del semáforo, sin
apalancamiento, centinela en la caja T95H y en el teléfono. La evidencia y la auditoría de congruencia están en `INFORME-TOTAL.md`.

- `binarias.py`, `motor/`: centinela v4 y su motor (señales, selección mensual, modelo, historial).
- `pruebas/`: banco a ciegas t10 a t33 con sus salidas.
- `cuant/`: investigación del 03/11 (seis dimensiones, validación, regímenes, CRT, ICT, libro de órdenes, opciones, semáforo).
- `dispositivos/`: lo que corre en la caja y el teléfono (arranque, avisos por Tor, semáforo).
- Fuera del repositorio, a propósito: velas y libro (`datos/`), estados y registros de apuestas, capturas de pantalla,
  material descargado de terceros y cualquier clave (las claves se leen al ejecutar desde archivos privados de cada equipo).
