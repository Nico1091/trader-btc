# trader-btc

Repositorio privado con dos sistemas de Bitcoin que trabajan en papel.

- **`binarias/` (activo).** Apuestas binarias de sube o baja a 10 minutos en los Contratos de Evento de Binance, en papel, con un aviso de SÍ o NO en cada señal. Manda `binarias/PLAN-TOTAL.md` (v7, 04/11/2026). El detalle está en `binarias/README.md` y la guía para quien quiera aplicar el método, en `binarias/GUIA-PARA-LA-GENTE.md`.
- **La raíz (detenido desde el 20/10/2026).** El agente de trading de futuros BTCUSDT en papel y en la red de pruebas de Binance, con su banco de estrategias, topes de riesgo y diario. Se conserva como historia y referencia.

Reglas del repositorio: ninguna clave entra al historial, porque se leen al ejecutar desde archivos privados; los datos de mercado, los estados y los diarios quedan fuera (`.gitignore`); ningún código mueve dinero real.
