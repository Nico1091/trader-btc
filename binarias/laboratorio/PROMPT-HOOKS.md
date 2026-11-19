# Prompt 1 · Revisión de hooks y frenos

Copia fiel del plan aprobado el 11/11/2026 a las 11:39 (laboratorio\PLAN-LABORATORIO.md).

```text
PROMPT DE REVISIÓN DE HOOKS Y FRENOS
Se ejecuta antes de empezar cada fase del laboratorio y cada vez que una orden sea negada.

Actúa como revisor de la configuración de Claude Code de este equipo. Tu entrega es una lista
de frenos, cada uno con su arreglo exacto. No cambies nada sin el sí del dueño en ese momento.

1. Lee ~/.claude/settings.json, C:\Windows\System32\.claude\settings.local.json y cualquier
   .claude\settings*.json de la carpeta de trabajo. Anota, por evento, cada hook: orden, matcher,
   qué hace y si puede bloquear. Anota también permissions (allow, deny, ask, defaultMode),
   autoMode (allow, soft_deny, hard_deny, environment) y worktree.
2. Toma la lista de avance del bloc y escribe, por cada paso pendiente, las órdenes que exige:
   editar archivos, adb push, adb shell, settings put, curl, schtasks.
3. Clasifica cada orden: pasa; la frena un hook; la frena una regla deny o ask; la puede negar el
   clasificador del modo automático; la frena una norma del dueño guardada en memoria; la frena
   un límite externo (equipo, red, Binance).
4. Por cada freno escribe quién lo levanta, el cambio exacto (bloque JSON, línea del guion o norma
   que el dueño tendría que levantar) y la alternativa que no necesita cambio. Se prefiere la
   alternativa.
5. Antes de escribir en un archivo de configuración: copia nombre.bak-AAAAMMDD. Después: valida el
   JSON, prueba el hook en seco con su entrada por stdin (código de salida y texto) y di si hace
   falta abrir /hooks o reiniciar la sesión.
6. Los campos y eventos se comprueban contra la referencia de configuración vigente, no de memoria.
7. Si una orden es negada durante el trabajo: copia el texto de la negación, clasifícala según el
   punto 3, avisa al dueño con el cambio propuesto y sigue con lo que no dependa de ella. No se
   reintenta la misma orden con otra forma.
8. Nunca se levanta sin orden expresa del dueño en ese momento: dinero real, llaves, instalar
   programas fuera de lo aprobado, agentes y mirar la pantalla.

Salida: por cada paso, una línea «paso · freno · arreglo»; al final, los cambios aplicados con su
prueba y los que esperan el sí del dueño.
```
