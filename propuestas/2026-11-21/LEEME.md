# Escáner de secretos y datos personales en el historial · propuesta del 21/11/2026

## Rama y carpeta

Esta entrega va en la rama `claude/proyectos-2026-11-21`, creada desde `master`.
El nombre pedido, `claude/proyectos-2026-11-17`, ya existe en el repositorio con
trabajo de una entrega anterior, y no se ha sobrescrito. La carpeta lleva la fecha
de hoy por la misma razón: otras entregas ya ocupan `propuestas/2026-11-17/`.

## Qué es

Un programa que responde a una pregunta: **¿hay en el historial de este repositorio
alguna credencial, o algún dato personal o de red, que no debería estar en un
repositorio público?**

Revisa cada archivo (`blob`) alcanzable desde cualquier rama o etiqueta, también los
ya borrados, porque siguen en el historial. Solo lee: no cambia el repositorio, no
se conecta a internet y no envía nada.

## Por qué esta y no otra

- Las propuestas de los días anteriores ya miden las binarias (evaluadores, pruebas
  de ventaja, medidores de ganancia, verificadores de cierres). Ninguna mide esto.
- El repositorio es público (lo confirma la consulta a GitHub del 21/11) y su
  historial tiene 119 commits y 20 referencias. Un secreto de Binance o de Telegram
  que hubiera llegado a un commit público se pudo copiar, aunque después se borrara.
  Eso lo haría perder el capital, y es el riesgo que no admite reparación posterior.
- El bloc dice que el repositorio tiene la IP de la casa y deja en manos del dueño la
  decisión de volverlo privado. Este escáner da los datos para decidirlo con pruebas.

## Cómo se usa

```
python3 escaner_secretos.py --repo RUTA_DEL_REPOSITORIO
python3 escaner_secretos.py --repo . --sensibles lista.txt --json resultado.json
python3 prueba_escaner.py
```

- `--sensibles`: archivo con un texto por línea (por ejemplo, un nombre de usuario o
  una IP) que no debe aparecer en el repositorio. Las líneas que empiezan por `#` se
  ignoran. Ese archivo no se guarda en el repositorio.
- `--json`: guarda el resultado sin valores completos.
- Códigos de salida: `0` sin hallazgos CRÍTICO; `1` con hallazgos CRÍTICO; `2` error.

## Qué busca

| Nivel | Qué detecta |
|---|---|
| CRÍTICO | Clave privada (bloque PEM); token de Telegram; clave de Anthropic, OpenAI, GitHub o AWS; asignación de `token`, `password`, `api_key` o `clave` con valor de alta entropía; cadena de 64 caracteres con mayúsculas, minúsculas y dígitos junto a la palabra «binance» |
| REVISAR | IP pública; ruta de usuario de Windows (`C:\Users\...`); correo; cualquier texto de `--sensibles` |

Reglas para evitar ruido:

- Se descartan valores de ejemplo o marcadores (`TU_TOKEN_AQUI`, `xxxx`, `ejemplo`).
- Una contraseña de menos de 16 caracteres, o sin letras y dígitos mezclados, no cuenta.
- Una cadena de 64 caracteres solo hexadecimales se toma por hash SHA-256, no por clave de Binance.
- El token público de cliente de la lectura en voz de Microsoft Edge (publicado por proyectos abiertos) está en una lista de valores conocidos que no son credenciales.
- Un correo que termina en extensión de archivo (`usuario@informe.txt`, sintaxis de `curl`) o de robot (`noreply@`) no cuenta.

Los valores de los secretos nunca se imprimen completos: se muestran los 4 primeros y
los 2 últimos caracteres. Los correos y las rutas de usuario se muestran como
etiqueta, sin el dato.

## Cómo se lee la salida

Ejemplo de formato (datos inventados):

```
[CRITICO] clave_anthropic · valor sk-a…Xz (92 car.)
   rutas: binarias/…
   primer commit de binarias/…: 1a2b3c4 2026-10-25
   en la rama principal: no, solo en el historial
```

- «en la rama principal: no, solo en el historial» quiere decir que el archivo ya no
  está en `master`, pero sigue en un commit al que cualquiera puede acceder.
- Un CRÍTICO en el historial de un repositorio público hay que tratarlo como
  comprometido: revocar o cambiar la clave en el proveedor. Borrar el archivo no
  la quita del historial.

## Pruebas

`prueba_escaner.py` crea repositorios temporales con datos falsos. Todos los valores
con forma de credencial se generan al ejecutar, con semilla fija, para que ningún
literal con aspecto real quede guardado en el repositorio. La salida completa está en
`salida_pruebas.txt`.

```
Ran 21 tests in 0.387s
OK
```

Las pruebas cubren: secreto borrado que sigue en el historial; clave que solo existe
en otra rama; marcadores y contraseñas cortas que no cuentan; IP pública frente a
privada; ruta de usuario enmascarada; correo personal frente a correo de robot;
hash hexadecimal frente a clave de Binance; token público conocido; texto de la lista
de sensibles; que ningún valor completo aparezca en la salida; código de salida; y un
repositorio limpio que da cero.

## Resultado de la pasada real (21/11/2026)

Sobre el historial completo del repositorio (20 referencias, 1.040 archivos, 5,5 s):

- **CRÍTICO: 0.** Tras depurar, no hay ninguna credencial con forma real en el historial.
  Los cuatro CRÍTICO de la primera pasada eran falsos positivos (tres hashes SHA-256 y
  el token público de Edge), y por eso se añadieron las reglas de arriba.
- **REVISAR: 11.** Son datos personales y de red que sí están publicados: una dirección
  de correo personal, el nombre de usuario de Windows en decenas de archivos, y varias
  IP públicas, entre ellas una que el propio repositorio identifica como la de la casa.
  Los datos concretos, con sus rutas, se entregaron al dueño por Telegram y **no** se
  escriben en este repositorio, porque el repositorio es público.

Esta pasada no prueba que no exista ninguna clave en otro sitio: solo revisa el repositorio.

## Qué no se probó y límites

- **No revisa nada fuera del repositorio**: ni el PC, ni el teléfono, ni la caja, ni la
  nube, ni el correo. Un secreto que nunca llegó a git no aparece aquí.
- **Solo reconoce los patrones de la tabla.** Una clave con otro formato, o partida en
  varias líneas, puede pasar. Añadir un patrón es una línea en `PATRONES`.
- **Falsos positivos conocidos**: una IP dentro de una cadena de versión (por ejemplo,
  de un navegador) cuenta como IP pública; `1.2.3.4` en ejemplos de documentación también.
  Se muestran como REVISAR y se revisan a mano.
- **No detecta teléfonos ni nombres**, salvo los que se pasen en `--sensibles`.
- **No reescribe el historial.** Quitar datos del historial (por ejemplo, con
  `git filter-repo`) es destructivo y cambia todas las ramas: es una decisión del dueño.
- **Lo ya publicado no se deshace con esta herramienta.** Volver privado el repositorio
  reduce la exposición futura; no borra lo que ya se copió.
- Probado con Python 3.11 en Linux. No se probó en Windows ni en el teléfono.

## Lo que solo puede hacer el dueño

1. Decidir si el repositorio pasa a privado.
2. Decidir si se reescribe el historial para quitar los datos personales (es destructivo).
3. Si alguna vez una clave de Binance, de Telegram o de un proveedor estuvo en este
   repositorio, cambiarla en el proveedor. La pasada no encontró ninguna, pero no revisa
   lo que está fuera del repositorio.
