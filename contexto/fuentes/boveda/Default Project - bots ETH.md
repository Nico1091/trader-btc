---
tags:
  - area/cripto
  - tipo/proyecto
creado: 2026-08-05
estado: activo
ruta: C:\Users\ni109\Documents\Default Project
---

# Default Project — bots ETH

Carpeta de trabajo de OpenCode con varios experimentos paralelos sobre Ethereum. Actividad concentrada el 3 de agosto de 2026.

**Ruta:** `C:\Users\ni109\Documents\Default Project`

## Subproyectos

| Carpeta | Idea |
|---|---|
| `airdrop_claimer` | Reclamar airdrops |
| `airdrop_farmer` | Farmear elegibilidad para airdrops |
| `flashloan` | Flash loans |
| `p2p-arbitrage-bot` | Arbitraje P2P |
| `hidden-edges` | Búsqueda de ineficiencias |
| `polycode` | Evaluación (`polycode_eval_output.txt`) |

> [!danger] Riesgo de seguridad — revisar
> `SEED_INSTRUCCIONES.txt` pide escribir la **seed phrase en texto plano** en `seed.txt` dentro de esta misma carpeta. Una seed en claro en disco es la clave de todos los fondos: cualquier script, backup en la nube o proceso con acceso al disco la lee entera.
> - [ ] Comprobar si `seed.txt` llegó a crearse y si tiene fondos asociados
> - [ ] Si existe con una seed real: mover fondos a una wallet nueva y borrar el archivo
> - [ ] Cambiar el diseño para derivar solo desde direcciones públicas, sin seed

## Siguientes pasos

- [ ] Resolver primero el punto de la seed
- [ ] Consolidar los `CONSENSO_*.md` contradictorios en una sola conclusión

Parte de [[Cripto y trading]].
