# trader-btc

Repositorio privado con los sistemas de Bitcoin que trabajan en papel. Qué es cada cosa:

- **`binarias/` (activo).** Apuestas binarias de sube o baja a 10 minutos en los Contratos de Evento de Binance, en papel, con un aviso de SÍ o NO en cada señal. Manda `binarias/PLAN-TOTAL.md` (v7, 04/11/2026). Lo que corre todo el día en la caja Android y en el teléfono está en `binarias/dispositivos/`. Lo que sabe el agente de Claude está en `binarias/OPERATIVA.md` y `binarias/PROMPT-OPERADOR.md`. El detalle, en `binarias/README.md`, y la guía para quien quiera aplicar el método, en `binarias/GUIA-PARA-LA-GENTE.md`.
- **`binarias/pulso/` (Pulso BTC).** El programa del PC (Rust sin dependencias, en WSL) que le escribe y le habla por Telegram: el precio cada 30 s, las velas de 5 min y de 1 h, sus cinco líneas en 1 min, noticias, informes y una lectura del mercado cada 15 min. No apuesta ni decide: el SÍ o NO lo manda la caja.
- **La raíz (detenido desde el 20/10/2026).** El agente de trading de futuros BTCUSDT en papel y en la red de pruebas de Binance, con su banco de estrategias, topes de riesgo y diario. Se conserva como historia y referencia.

Las carpetas de trabajo viven fuera del repositorio (`Ingresos\binarias-papel` y `Ingresos\pulso-btc`). `binarias/herramientas/sincronizar_repo.py` copia aquí lo vigente con una sola orden, sin datos, estados ni claves, y solo a la rama de las binarias.

Reglas del repositorio: ninguna clave entra al historial, porque se leen al ejecutar desde archivos privados; los datos de mercado, los estados y los diarios quedan fuera (`.gitignore`); ningún código mueve dinero real.
