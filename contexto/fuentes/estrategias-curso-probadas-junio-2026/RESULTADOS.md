# RESULTADOS — pruebas del agente IA (modo papel)

Memoria de corridas: cada bloque mide si el criterio de la IA mejora frente a operar todas las señales. Conservar solo lo que mejora.


## Corrida 2026-06-28T03:38:53.396Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 30 | IA operó: 2 | IA esperó: 28

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 30 | 2 | 28 |
| win rate | 40.0% | 0.0% | 42.9% |
| PnL (suma log) | 5.6% | -6.1% | 11.7% |

**Veredicto:** ⚠️ La IA RESTA (frena buenos trades). Revisar su prompt/criterio.

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | wait | -3.05% | 2ª revisión rebajó a esperar: Hora 22 UTC con baja liquidez, señal en zona media de rango  |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | wait | 2.18% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) y confluencia de velas es 0 (n |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | wait | -0.18% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) para estrategia long en tenden |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | wait | -0.08% | Confluencia de velas es 0 (neutra), no hay confirmación de pullback; además, la estrategia |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | wait | 0.61% | Estrategia pullback requiere range_pos 0.35-0.65, pero señal en 0.38 es coherente. Sin emb |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) y confluencia de velas es 0 (n |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | wait | 0.53% | Confluencia de velas neutra (0) no proporciona confirmación adicional; aunque range_pos y  |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | wait | -0.59% | range_pos 0.61 está fuera del rango pullback (0.35-0.65) y confluencia de velas es 0 (neut |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | wait | -0.42% | La posición en rango (0.40) es coherente con pullback, pero la confluencia de velas es 0 ( |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | wait | -0.44% | La señal es long pero range_pos 0.455 está en zona de pullback (0.35-0.65) y pendiente pos |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | operate | -3.05% | Precio en rango medio (0.45) con tendencia alcista fuerte (pendiente 36.6) y GBM 0.63 > 0. |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | wait | 5.95% | La señal es long pero range_pos 0.36 está en zona de pullback (0.35-0.65) y la tendencia e |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | wait | -3.05% | La estrategia es pullback en tendencia alcista, pero range_pos 0.61 está en zona neutral-a |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | wait | 2.88% | Confluencia de velas neutra (0) no confirma pullback en tendencia alcista; además hora UTC |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | wait | -0.48% | range_pos 0.43 está en zona de pullback (0.35-0.65) pero confluencia de velas es 0 (neutra |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | wait | -1.52% | La posición en rango (0.617) está fuera del rango de pullback (0.35-0.65) y la confluencia |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | range_pos 0.56 dentro del rango pullback (0.35-0.65), pendiente positiva fuerte (31.8), GB |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | wait | -3.05% | La estrategia es de reversión en topes de rango, pero range_pos 0.62 está en zona media, n |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | wait | 1.34% | Confluencia de velas neutra (0) no respalda entrada en pullback; además hora tardía aument |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | wait | 2.94% | La estrategia es pullback en tendencia alcista, pero range_pos 0.49 está en zona neutral ( |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | wait | 3.16% | La estrategia es de reversión en topes de rango (suelo para long), pero range_pos=0.64 est |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | wait | 4.23% | La posición en rango (0.538) está en la zona media, no en el suelo (0-0.35) como exige la  |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | wait | 1.50% | range_pos 0.578 está fuera del rango de pullback (0.35-0.65 es válido, pero la estrategia  |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | wait | 4.14% | 2ª revisión rebajó a esperar: GBM apenas supera umbral (0.515), posición en rango 0.38 no  |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | wait | -1.43% | La señal es para BTCUSDC, no para ETHUSDC (mercado único permitido). Además, range_pos 0.5 |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | wait | 4.36% | 2ª revisión rebajó a esperar: Aunque los números son positivos, la hora 18 UTC es tardía p |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | wait | -0.18% | La posición en rango (0.62) está en el límite superior del rango de pullback (0.35-0.65),  |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | wait | -1.62% | La posición en rango (0.38) es coherente con pullback (0.35-0.65) y la pendiente es positi |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | wait | -2.48% | La estrategia es pullback en tendencia alcista (pendiente>0), pero range_pos 0.55 está en  |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | wait | -1.15% | La posición en rango (0.60) está fuera del rango de pullback esperado (0.35-0.65, pero muy |

</details>


## Corrida 2026-06-28T03:44:02.681Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 30 | IA operó: 4 | IA esperó: 26

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 30 | 4 | 26 |
| win rate | 40.0% | 50.0% | 38.5% |
| PnL (suma log) | 5.6% | 4.0% | 1.6% |

**Veredicto:** ⚠️ La IA RESTA (frena buenos trades). Revisar su prompt/criterio.

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | operate | -3.05% | range_pos 0.36 (pullback) con pendiente positiva 1.85, GBM 0.54 > 0.5, confluencia positiv |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | wait | 2.18% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) y confluencia de velas es 0 (n |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | wait | -0.18% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) para estrategia long en tenden |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | wait | -0.08% | Confluencia de velas neutra (0) no confirma patrón de pullback; falta señal de confirmació |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | wait | 0.61% | Señal coherente con estrategia (pullback en tendencia alcista, range_pos 0.38, GBM 0.54 >  |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) y confluencia de velas es 0 (n |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | wait | 0.53% | La posición en rango (0.54) está en la zona de pullback (0.35-0.65) y la tendencia es alci |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | wait | -0.59% | La posición en rango (0.61) está fuera del rango de pullback (0.35-0.65) y la confluencia  |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | wait | -0.42% | La estrategia es pullback en tendencia alcista, pero range_pos 0.40 está en zona de suelo, |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | wait | -0.44% | Confluencia de velas neutra (0) no proporciona confirmación de pullback en tendencia alcis |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | wait | -3.05% | La confluencia de velas es 0 (neutra), no hay patrón de velas que confirme el pullback. Au |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | operate | 5.95% | Precio en zona de pullback (0.36) con tendencia alcista fuerte (pendiente 31.9), GBM 0.53  |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | wait | -3.05% | range_pos 0.61 está fuera del rango de pullback (0.35-0.65) para estrategia long en tenden |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | wait | 2.88% | La posición en rango (0.36) es coherente con pullback, pero la confluencia de velas es 0 ( |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | wait | -0.48% | Estrategia pullback requiere range_pos 0.35-0.65, pero 0.43 está dentro del rango. Sin emb |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | wait | -1.52% | range_pos 0.62 está fuera del rango de pullback (0.35-0.65) y confluencia de velas es 0 (n |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | range_pos 0.56 dentro del rango pullback (0.35-0.65), pendiente positiva fuerte (31.8), GB |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | wait | -3.05% | La posición en rango (0.62) está en el límite superior del rango de pullback, pero la estr |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | wait | 1.34% | Confluencia de velas es 0 (neutra), no hay patrón de confirmación; la estrategia requiere  |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | wait | 2.94% | La posición en rango (0.49) está en la zona de pullback (0.35-0.65) y la pendiente es alci |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | wait | 3.16% | range_pos 0.64 está en el límite superior del rango de pullback (0.35-0.65); aunque GBM su |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | wait | 4.23% | La señal es long pero range_pos 0.538 está en zona de pullback (0.35-0.65) y pendiente pos |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | wait | 1.50% | range_pos 0.578 está fuera del rango de pullback (0.35-0.65) para estrategia long en tende |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | operate | 4.14% | Precio en zona de pullback (0.38) con tendencia alcista (pendiente 0.62), GBM 0.515 > 0.5, |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | wait | -1.43% | La señal es long pero range_pos=0.50 está en medio del rango, no en suelo (0-0.1) ni techo |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | wait | 4.36% | La señal es long con range_pos 0.59 (medio del rango), pero la estrategia validada es reve |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | wait | -0.18% | La posición en rango (0.62) está fuera del rango de pullback (0.35-0.65) para estrategia l |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | wait | -1.62% | La estrategia es pullback en tendencia alcista (pendiente positiva), pero range_pos 0.376  |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | wait | -2.48% | La posición en rango (0.55) no es coherente con la estrategia de pullback (0.35-0.65 es am |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | wait | -1.15% | La posición en rango (0.60) no es suelo ni techo, incoherente con la estrategia de reversi |

</details>


## Corrida 2026-06-28T03:48:26.268Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 60 | IA operó: 7 | IA esperó: 53

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 60 | 7 | 53 |
| win rate | 36.7% | 14.3% | 39.6% |
| PnL (suma log) | 0.6% | -10.8% | 11.4% |

**Veredicto:** ⚠️ La IA RESTA (frena buenos trades). Revisar su prompt/criterio.

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | operate | -3.05% | Precio en zona de pullback (0.36) con tendencia alcista fuerte (pendiente 1.85), GBM 0.54  |
| 2025-12-08T16:00 | 0.49 | 0.55 | +3.8e+1 | 0 | wait | 4.52% | La estrategia es pullback en tendencia alcista, pero range_pos 0.49 está en zona neutral ( |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | wait | 2.18% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) y confluencia 0 no confirma re |
| 2025-12-09T11:00 | 0.58 | 0.51 | +1.9e+1 | 0 | wait | 1.85% | La señal es long pero range_pos 0.58 está en zona de pullback (0.35-0.65) y pendiente posi |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | wait | -0.18% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) para estrategia long en tenden |
| 2025-12-22T22:00 | 0.35 | 0.55 | +2.2e+1 | 0 | operate | -1.48% | range_pos 0.35 en zona de pullback, pendiente positiva 21.99, GBM 0.55 > 0.5, confluencia  |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | wait | -0.08% | La estrategia es pullback en tendencia alcista, no compra en suelo. range_pos 0.37 es suel |
| 2025-12-31T11:00 | 0.61 | 0.53 | +4.4e-2 | 0 | wait | -1.16% | La señal es long pero range_pos 0.61 está fuera del rango de retroceso (0.35-0.65) y confl |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | wait | 0.61% | La señal es long pero range_pos 0.38 está fuera del rango de pullback (0.35-0.65) para ten |
| 2026-01-01T10:00 | 0.40 | 0.51 | +2.4e+0 | 0 | wait | 1.98% | La estrategia es pullback en tendencia alcista, pero range_pos 0.40 está en zona de retroc |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | range_pos 0.64 está fuera del rango de pullback (0.35-0.65) y confluencia de velas es 0 (n |
| 2026-01-10T15:00 | 0.49 | 0.55 | +1.3e+0 | 0 | wait | 0.18% | La señal es long pero range_pos 0.49 está en zona de pullback (0.35-0.65) y la tendencia e |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | wait | 0.53% | La estrategia es pullback en tendencia alcista, pero range_pos 0.54 está en zona media, no |
| 2026-01-12T21:00 | 0.39 | 0.53 | +1.6e+1 | 0 | wait | 3.23% | Confluencia de velas neutra (0) no confirma el retroceso en tendencia alcista; aunque rang |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | wait | -0.59% | La señal es long pero range_pos=0.61 está en zona media, no en suelo (0-0.1) ni techo (0.9 |
| 2026-01-16T04:00 | 0.45 | 0.52 | +2.4e+1 | 0 | wait | -0.01% | La estrategia es pullback en tendencia alcista (pendiente positiva), pero range_pos 0.45 e |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | wait | -0.42% | La posición en rango (0.40) está en zona de pullback (0.35-0.65) y la tendencia es alcista |
| 2026-02-09T07:00 | 0.63 | 0.54 | +2.7e+1 | 0 | wait | -3.05% | range_pos 0.63 está fuera del rango de pullback (0.35-0.65) y confluencia de velas es 0 (n |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | wait | -0.44% | Aunque range_pos y GBM son coherentes con pullback en tendencia alcista, la confluencia de |
| 2026-02-27T01:00 | 0.64 | 0.60 | +7.2e+1 | 2 | wait | -3.05% | La posición en rango (0.635) está fuera del rango de pullback (0.35-0.65) y la estrategia  |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | wait | -3.05% | La estrategia es pullback en tendencia alcista, pero range_pos 0.45 está en zona de pullba |
| 2026-03-03T04:00 | 0.63 | 0.56 | +3.6e+1 | 0 | wait | -0.55% | range_pos 0.63 está fuera del rango de pullback (0.35-0.65) para estrategia long en tenden |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | operate | 5.95% | Precio en zona de pullback (0.36) con tendencia alcista fuerte (pendiente 31.9), GBM 0.53  |
| 2026-03-05T18:00 | 0.61 | 0.60 | +1.1e+2 | 0 | wait | -3.05% | La posición en rango (0.61) está en el límite superior del rango de pullback (0.35-0.65) y |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | wait | -3.05% | range_pos 0.61 está en zona media (0.35-0.65) pero la estrategia es de reversión en topes  |
| 2026-03-06T10:00 | 0.47 | 0.51 | +2.3e+1 | 0 | wait | -3.05% | La estrategia es pullback en tendencia alcista (pendiente positiva), pero range_pos 0.47 e |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | wait | 2.88% | Confluencia de velas neutra (0) no confirma patrón de pullback; aunque range_pos y GBM son |
| 2026-03-13T17:00 | 0.42 | 0.52 | +4.2e+1 | 0 | wait | -0.64% | La señal es long con range_pos 0.42 (medio del rango), lo que no es coherente con la estra |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | wait | -0.48% | Estrategia pullback requiere range_pos 0.35-0.65, pero señal es 0.43 (dentro del rango). S |
| 2026-03-17T05:00 | 0.64 | 0.51 | +7.5e+1 | 0 | wait | -0.17% | La posición en rango (0.64) está fuera del rango de pullback (0.35-0.65) y la confluencia  |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | wait | -1.52% | La posición en rango (0.617) está fuera del rango de pullback (0.35-0.65) y la confluencia |
| 2026-03-17T16:00 | 0.61 | 0.55 | +5.8e+1 | 1 | operate | -3.05% | Precio en rango medio (0.61) con tendencia alcista fuerte (pendiente 57.6) y GBM 0.55 > 0. |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | range_pos 0.56 dentro del rango pullback (0.35-0.65), pendiente positiva fuerte (31.8), GB |
| 2026-03-18T10:00 | 0.45 | 0.53 | +1.5e+1 | 0 | wait | -3.05% | La estrategia es pullback en tendencia alcista (pendiente positiva), pero range_pos 0.45 e |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | wait | -3.05% | La estrategia es de reversión en topes de rango, pero range_pos 0.62 está en zona media, n |
| 2026-03-24T17:00 | 0.42 | 0.55 | +4.9e+1 | 0 | wait | 2.15% | Aunque range_pos (0.42) y GBM (0.55) son coherentes con pullback en tendencia alcista, la  |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | wait | 1.34% | Señal coherente con rango (0.38) y tendencia alcista, GBM supera umbral, pero hora tardía  |
| 2026-03-30T20:00 | 0.52 | 0.57 | +1.3e+1 | 0 | wait | 2.34% | range_pos 0.52 está en zona de pullback (0.35-0.65) pero la estrategia es de reversión en  |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | wait | 2.94% | La posición en rango (0.49) está en la zona de pullback (0.35-0.65) y la pendiente es posi |
| 2026-04-02T01:00 | 0.41 | 0.50 | +3.0e+1 | 0 | wait | -1.14% | La posición en rango (0.41) está dentro del rango de pullback (0.35-0.65), pero la estrate |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | wait | 3.16% | La posición en rango (0.64) está en el límite superior del rango de pullback (0.35-0.65) y |
| 2026-04-07T01:00 | 0.48 | 0.51 | +5.3e+1 | 0 | wait | 5.95% | Aunque rango y GBM son coherentes, la confluencia de velas es neutra (0) y la hora intradí |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | wait | 4.23% | La estrategia es pullback en tendencia alcista, pero range_pos 0.54 está en zona media, no |
| 2026-04-07T13:00 | 0.43 | 0.55 | +3.9e+1 | 0 | wait | 5.95% | Señal long en rango medio (0.43) no es coherente con estrategia de pullback en tendencia a |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | wait | 1.50% | range_pos 0.578 está fuera del rango de pullback (0.35-0.65) para estrategia long en tende |
| 2026-04-15T13:00 | 0.64 | 0.51 | +6.2e+1 | 0 | wait | -0.42% | La señal es long pero range_pos 0.64 está fuera del rango de pullback (0.35-0.65) y no es  |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | wait | 4.14% | La estrategia es Trend Following PULLBACK (range_pos 0.35-0.65), pero range_pos 0.378 está |
| 2026-04-18T12:00 | 0.58 | 0.52 | +5.5e+1 | 0 | wait | -0.89% | La posición en rango (0.58) no está en zona de retroceso (0.35-0.65 es amplio, pero idealm |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | wait | -1.43% | La posición en rango (0.50) está dentro del rango de pullback (0.35-0.65), pero la estrate |
| 2026-04-18T21:00 | 0.50 | 0.53 | +4.0e+1 | 1 | wait | -1.91% | range_pos 0.50 está en zona de pullback (0.35-0.65) pero la estrategia es de reversión en  |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | wait | 4.36% | La señal long en BTCUSDT tiene GBM > 0.5 y confluencia positiva, pero range_pos 0.59 no es |
| 2026-04-23T10:00 | 0.56 | 0.50 | +5.6e+1 | 0 | wait | 0.40% | range_pos 0.555 está fuera del rango de pullback (0.35-0.65 es válido, pero la estrategia  |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | wait | -0.18% | range_pos 0.62 está en el límite superior del rango de pullback (0.35-0.65), pero la estra |
| 2026-04-24T08:00 | 0.60 | 0.53 | +9.9e+0 | 1 | wait | -0.23% | range_pos 0.595 no está en zona de retroceso (0.35-0.65) para pullback long en tendencia a |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | wait | -1.62% | La estrategia es pullback en tendencia alcista, pero range_pos 0.376 está en zona de suelo |
| 2026-05-11T11:00 | 0.45 | 0.51 | +1.7e+1 | 0 | wait | -0.56% | Confluencia de velas es 0 (neutra), no hay patrón de confirmación alcista. La estrategia r |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | wait | -2.48% | La estrategia es pullback en tendencia alcista (pendiente>0), pero range_pos 0.55 está en  |
| 2026-05-15T12:00 | 0.50 | 0.53 | +1.1e+1 | 0 | operate | -3.05% | Precio en medio de rango (0.495) con tendencia alcista fuerte (pendiente 10.74) y GBM 0.52 |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | wait | -1.15% | La posición en rango (0.60) está fuera del rango de pullback (0.35-0.65) y la confluencia  |
| 2026-05-22T09:00 | 0.47 | 0.53 | +8.3e+0 | 1 | operate | -3.05% | Precio en rango medio (0.47) con tendencia alcista fuerte (pendiente 8.27) y GBM 0.53 > 0. |

</details>


## Corrida 2026-06-28T04:08:19.420Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 30 | IA operó: 29 | IA esperó: 1

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 30 | 29 | 1 |
| win rate | 40.0% | 41.4% | 0.0% |
| PnL (suma log) | 5.6% | 8.0% | -2.4% |

**Veredicto:** ✅ La IA MEJORA (su criterio sube el PnL frente a operar todo).

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | operate | -3.05% | Pendiente positiva (1.85), range_pos 0.36 en zona de retroceso, GBM 0.54 > 0.5, confluenci |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | operate | 2.18% | Pendiente fuertemente alcista (34.7), range_pos 0.64 en zona de retroceso, GBM 0.525 > 0.5 |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | operate | -0.18% | Pendiente fuertemente alcista (9.23), range_pos 0.64 en zona de retroceso, GBM 0.53 > 0.5, |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | operate | -0.08% | Pullback long en zona óptima (range_pos 0.37) con pendiente alcista fuerte (15.58) y GBM s |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | operate | 0.61% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 18.5 |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | Señal cumple tendencia, zona y GBM, pero R:R es pobre (recorrido hasta techo 1.5% vs stop  |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | operate | 0.53% | Pullback long en zona óptima (range_pos 0.54) con tendencia alcista fuerte (pendiente 16.5 |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | operate | -0.59% | Señal pullback long en zona de retroceso (0.61) con pendiente fuertemente alcista (75) y G |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | operate | -0.42% | Pullback long en zona óptima (range_pos 0.40) con tendencia alcista fuerte (pendiente 4.95 |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | operate | -0.44% | Pullback long en zona óptima (0.455), tendencia alcista fuerte (pendiente 25.27), GBM 0.57 |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | operate | -3.05% | Pullback long en zona óptima (0.45) con tendencia alcista fuerte (pendiente 36.6) y GBM >0 |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | operate | 5.95% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 31.9 |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 82), range_pos 0.61 en zona óptima, GBM 0.53 |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | operate | 2.88% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 8.6) |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | -0.48% | Pullback long en zona óptima (range_pos 0.43) con tendencia alcista fuerte (pendiente 38.8 |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | operate | -1.52% | Señal pullback long en zona de retroceso (0.62) con tendencia alcista fuerte (pendiente 66 |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 31.8), range_pos 0.56 en zona óptima, GBM 0. |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 12.17), range_pos 0.62 en zona óptima, GBM 0 |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | operate | 1.34% | Pullback long en tendencia alcista (pendiente 8.6), range_pos 0.38 en zona óptima, GBM 0.5 |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | operate | 2.94% | Pendiente positiva (12.27), range_pos 0.49 en zona de retroceso, GBM 0.52 > 0.5, sin patro |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | operate | 3.16% | Pullback long en tendencia alcista (pendiente 5.09), range_pos 0.64 en zona de retroceso,  |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | operate | 4.23% | Señal pullback long en zona óptima (range_pos 0.54) con tendencia alcista fuerte (pendient |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | operate | 1.50% | Pendiente positiva (7.19), range_pos 0.58 en zona de retroceso, GBM 0.51 > 0.5, sin patron |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | operate | 4.14% | Señal pullback long en zona óptima (range_pos 0.38), tendencia alcista fuerte (pendiente 0 |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | operate | -1.43% | Pullback long en zona óptima (range_pos 0.50) con tendencia alcista fuerte (pendiente 49.2 |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | operate | 4.36% | Pendiente fuertemente alcista (22.2), range_pos 0.59 en zona de retroceso, GBM 0.56 > 0.5, |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | operate | -0.18% | Pendiente fuertemente alcista (42.2), range_pos 0.62 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | operate | -1.62% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 24.1 |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | operate | -2.48% | Pullback long en tendencia alcista (pendiente 6.1), range_pos 0.55 en zona óptima, GBM 0.5 |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | operate | -1.15% | Pendiente positiva (15.99), range_pos 0.60 en zona de retroceso, GBM 0.50 supera umbral 0. |

</details>


## Corrida 2026-06-28T04:14:11.240Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 60 | IA operó: 58 | IA esperó: 2

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 60 | 58 | 2 |
| win rate | 36.7% | 36.2% | 50.0% |
| PnL (suma log) | 0.6% | 0.8% | -0.2% |

**Veredicto:** ✅ La IA MEJORA (su criterio sube el PnL frente a operar todo).

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | operate | -3.05% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 1.85 |
| 2025-12-08T16:00 | 0.49 | 0.55 | +3.8e+1 | 0 | operate | 4.52% | Señal pullback long en zona óptima (range_pos 0.49) con tendencia alcista fuerte (pendient |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | wait | 2.18% | Aunque tendencia y zona son correctas, el R:R es pobre (distancia al techo 1.8% vs stop 3% |
| 2025-12-09T11:00 | 0.58 | 0.51 | +1.9e+1 | 0 | operate | 1.85% | Pendiente positiva (19.03), range_pos 0.58 en zona de retroceso, GBM 0.51 > 0.5, sin patro |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | operate | -0.18% | Pendiente fuertemente alcista (9.23), range_pos 0.64 en zona de retroceso, GBM 0.53 > 0.5, |
| 2025-12-22T22:00 | 0.35 | 0.55 | +2.2e+1 | 0 | operate | -1.48% | Pullback long en zona óptima (range_pos 0.35) con tendencia alcista fuerte (pendiente 22)  |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | operate | -0.08% | Señal de pullback long en zona óptima (range_pos 0.37) con tendencia alcista fuerte (pendi |
| 2025-12-31T11:00 | 0.61 | 0.53 | +4.4e-2 | 0 | operate | -1.16% | Señal pullback long en zona correcta (0.61) con tendencia alcista (pendiente 0.044) y GBM  |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | operate | 0.61% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 18.5 |
| 2026-01-01T10:00 | 0.40 | 0.51 | +2.4e+0 | 0 | operate | 1.98% | Pendiente fuertemente alcista (2.4), range_pos 0.40 en zona de retroceso, GBM 0.51 > 0.5,  |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | Señal cumple tendencia, zona y GBM, pero R:R es pobre (1.5% potencial vs 3% stop) y hora t |
| 2026-01-10T15:00 | 0.49 | 0.55 | +1.3e+0 | 0 | operate | 0.18% | Señal de pullback long en tendencia alcista (pendiente>0), range_pos 0.49 en zona óptima,  |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | operate | 0.53% | Pullback long en zona óptima (range_pos 0.54) con tendencia alcista fuerte (pendiente 16.5 |
| 2026-01-12T21:00 | 0.39 | 0.53 | +1.6e+1 | 0 | operate | 3.23% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.39 en zona óptima, GBM 0.53  |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | operate | -0.59% | Señal pullback long en zona correcta (range_pos 0.61) con tendencia alcista fuerte (pendie |
| 2026-01-16T04:00 | 0.45 | 0.52 | +2.4e+1 | 0 | operate | -0.01% | Pullback long en zona óptima (range_pos 0.45) con tendencia alcista fuerte (pendiente 24.3 |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | operate | -0.42% | Pullback long en zona óptima (range_pos 0.40) con tendencia alcista fuerte (pendiente 4.95 |
| 2026-02-09T07:00 | 0.63 | 0.54 | +2.7e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (26.8), range_pos 0.63 en zona de retroceso, GBM 0.54 > 0.5, |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | operate | -0.44% | Pullback long en zona óptima (0.455) con tendencia alcista fuerte (pendiente 25.27), GBM 0 |
| 2026-02-27T01:00 | 0.64 | 0.60 | +7.2e+1 | 2 | operate | -3.05% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.635 en zona de retroceso, GB |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.45 en zona óptima, GBM 0.63  |
| 2026-03-03T04:00 | 0.63 | 0.56 | +3.6e+1 | 0 | operate | -0.55% | Pendiente fuertemente alcista (36.05), range_pos 0.626 en zona de retroceso, GBM 0.564 > 0 |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | operate | 5.95% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 31.9 |
| 2026-03-05T18:00 | 0.61 | 0.60 | +1.1e+2 | 0 | operate | -3.05% | Pullback long en zona óptima (range_pos 0.61) con tendencia alcista fuerte (pendiente 113) |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 82), range_pos 0.61 en zona óptima, GBM 0.53 |
| 2026-03-06T10:00 | 0.47 | 0.51 | +2.3e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (22.8), range_pos 0.47 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | operate | 2.88% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 8.6) |
| 2026-03-13T17:00 | 0.42 | 0.52 | +4.2e+1 | 0 | operate | -0.64% | Pullback long en zona óptima (0.42) con tendencia alcista fuerte (pendiente 41.6) y GBM so |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | -0.48% | Pullback long en tendencia alcista (pendiente 38.8), range_pos 0.43 en zona óptima, GBM 0. |
| 2026-03-17T05:00 | 0.64 | 0.51 | +7.5e+1 | 0 | operate | -0.17% | Pendiente fuertemente alcista (75.4), range_pos 0.64 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | operate | -1.52% | Pullback long en zona óptima (0.62) con tendencia alcista fuerte (pendiente 66.4) y GBM su |
| 2026-03-17T16:00 | 0.61 | 0.55 | +5.8e+1 | 1 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 57.6), range_pos 0.61 en zona dorada, GBM 0. |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 31.8), range_pos 0.56 en zona óptima, GBM 0. |
| 2026-03-18T10:00 | 0.45 | 0.53 | +1.5e+1 | 0 | operate | -3.05% | Pendiente positiva (15.5), range_pos 0.45 en zona de retroceso, GBM 0.53 > 0.5, sin patron |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (12.17), range_pos 0.62 en zona de retroceso, GBM 0.55 > 0.5 |
| 2026-03-24T17:00 | 0.42 | 0.55 | +4.9e+1 | 0 | operate | 2.15% | Señal pullback long en zona óptima (range_pos 0.42) con tendencia alcista fuerte (pendient |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | operate | 1.34% | Pullback long en tendencia alcista (pendiente 8.6), range_pos 0.38 en zona óptima, GBM 0.5 |
| 2026-03-30T20:00 | 0.52 | 0.57 | +1.3e+1 | 0 | operate | 2.34% | Pendiente positiva (12.58), range_pos 0.52 en zona de retroceso, GBM 0.57 > 0.5, sin patro |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | operate | 2.94% | Pendiente fuertemente alcista (12.27), range_pos 0.49 en zona de retroceso, GBM 0.52 > 0.5 |
| 2026-04-02T01:00 | 0.41 | 0.50 | +3.0e+1 | 0 | operate | -1.14% | Pullback long en zona óptima (0.41) con tendencia alcista fuerte (pendiente 29.6), GBM jus |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | operate | 3.16% | Pendiente positiva (5.09), range_pos 0.64 en zona de retroceso, GBM 0.55 > 0.5, sin patron |
| 2026-04-07T01:00 | 0.48 | 0.51 | +5.3e+1 | 0 | operate | 5.95% | Pendiente fuertemente alcista (53.2), range_pos 0.48 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | operate | 4.23% | Señal pullback long en tendencia alcista (pendiente 48.6), range_pos 0.54 en zona óptima,  |
| 2026-04-07T13:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | 5.95% | Pullback long en zona óptima (range_pos 0.43) con tendencia alcista fuerte (pendiente 39.3 |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | operate | 1.50% | Pullback long en zona óptima (range_pos 0.58) con tendencia alcista fuerte (pendiente 7.19 |
| 2026-04-15T13:00 | 0.64 | 0.51 | +6.2e+1 | 0 | operate | -0.42% | Pendiente fuertemente alcista (62.5), range_pos 0.64 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | operate | 4.14% | Pullback long en tendencia alcista (pendiente 0.62), range_pos 0.38 en zona óptima, GBM 0. |
| 2026-04-18T12:00 | 0.58 | 0.52 | +5.5e+1 | 0 | operate | -0.89% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.58 en zona óptima, GBM 0.52  |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | operate | -1.43% | Pendiente fuertemente alcista (49.18), range_pos 0.50 en zona de retroceso, GBM 0.53 > 0.5 |
| 2026-04-18T21:00 | 0.50 | 0.53 | +4.0e+1 | 1 | operate | -1.91% | Señal pullback long en zona óptima (range_pos 0.5) con tendencia alcista fuerte (pendiente |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | operate | 4.36% | Pullback long en zona óptima (range_pos 0.59) con tendencia alcista fuerte (pendiente 22.2 |
| 2026-04-23T10:00 | 0.56 | 0.50 | +5.6e+1 | 0 | operate | 0.40% | Pullback long en zona óptima (range_pos 0.555) con tendencia alcista fuerte (pendiente 56. |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | operate | -0.18% | Pendiente positiva, range_pos 0.62 en zona de retroceso, GBM 0.51 > 0.5, confluencia posit |
| 2026-04-24T08:00 | 0.60 | 0.53 | +9.9e+0 | 1 | operate | -0.23% | Pullback long en zona óptima (range_pos 0.60) con tendencia alcista fuerte (pendiente 9.9) |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | operate | -1.62% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 24.1 |
| 2026-05-11T11:00 | 0.45 | 0.51 | +1.7e+1 | 0 | operate | -0.56% | Pullback long en zona óptima (range_pos 0.45) con tendencia alcista fuerte (pendiente 16.5 |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | operate | -2.48% | Señal pullback long en zona óptima (range_pos 0.55) con tendencia alcista fuerte (pendient |
| 2026-05-15T12:00 | 0.50 | 0.53 | +1.1e+1 | 0 | operate | -3.05% | Pendiente positiva (10.74), range_pos 0.495 en zona de retroceso, GBM 0.527 > 0.5, conflue |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | operate | -1.15% | Pendiente fuertemente alcista (15.99), range_pos 0.60 en zona de retroceso, GBM 0.50 super |
| 2026-05-22T09:00 | 0.47 | 0.53 | +8.3e+0 | 1 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 8.27), range_pos 0.47 en zona óptima, GBM 0. |

</details>


## Corrida 2026-06-28T04:18:04.135Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 30 | IA operó: 24 | IA esperó: 6

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 30 | 24 | 6 |
| win rate | 40.0% | 45.8% | 16.7% |
| PnL (suma log) | 5.6% | 11.6% | -6.0% |

**Veredicto:** ✅ La IA MEJORA (su criterio sube el PnL frente a operar todo).

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | operate | -3.05% | Pendiente positiva (1.85), range_pos 0.36 en zona de retroceso, GBM 0.54 > 0.5, confluenci |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | wait | 2.18% | Señal pullback long con tendencia alcista y rango correcto, pero el recorrido hasta el tec |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | operate | -0.18% | Pendiente fuertemente alcista (9.23), range_pos 0.64 en zona de retroceso, GBM 0.53 > 0.5, |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | operate | -0.08% | Pendiente fuertemente alcista (15.58), range_pos 0.37 en zona de retroceso, GBM 0.53 > 0.5 |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | operate | 0.61% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 18.5 |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | Señal cumple tendencia, zona y GBM, pero R:R es pobre (distancia al techo 1.5% vs stop 3%) |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | operate | 0.53% | Pullback long en tendencia alcista (pendiente 16.5), range_pos 0.54 en zona óptima, GBM 0. |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | wait | -0.59% | Señal en zona de retroceso y tendencia alcista, pero distancia al techo es solo 2.5% (meno |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | operate | -0.42% | Pullback long en zona óptima (range_pos 0.40) con tendencia alcista fuerte (pendiente 4.95 |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | operate | -0.44% | Pendiente positiva fuerte (25.27), range_pos 0.455 en zona de retroceso, GBM 0.575 > 0.5,  |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | operate | -3.05% | Pendiente positiva fuerte (36.6), range_pos 0.45 en zona de retroceso, GBM 0.63 > 0.5, sin |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | operate | 5.95% | Señal pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendient |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | operate | -3.05% | Pendiente fuertemente alcista (82), range_pos 0.61 en zona de retroceso, GBM 0.53 > 0.5, c |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | operate | 2.88% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 8.6) |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | -0.48% | Pullback long en tendencia alcista (pendiente 38.8), range_pos 0.43 en zona óptima, GBM 0. |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | wait | -1.52% | Pendiente alcista fuerte y range_pos en zona de retroceso, pero distancia al techo es solo |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 31.8), range_pos 0.56 en zona óptima, GBM 0. |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.62 en zona de retroceso, GBM |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | operate | 1.34% | Pendiente positiva (8.62), range_pos 0.38 en zona de retroceso, GBM 0.55 > 0.5, confluenci |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | operate | 2.94% | Pendiente fuertemente positiva (12.27), range_pos 0.49 en zona de retroceso, GBM 0.52 > 0. |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | operate | 3.16% | Pullback long en tendencia alcista (pendiente 5.09), range_pos 0.64 en zona de retroceso,  |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | operate | 4.23% | Pendiente fuertemente alcista (48.56), range_pos 0.54 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | operate | 1.50% | Señal pullback long en zona óptima (0.578), pendiente positiva fuerte, GBM supera umbral,  |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | operate | 4.14% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 0.62 |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | operate | -1.43% | Pendiente fuertemente alcista (49.18), range_pos 0.50 en zona de retroceso, GBM 0.53 > 0.5 |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | operate | 4.36% | Pendiente positiva, range_pos 0.59 en zona de retroceso, GBM 0.56 > 0.5, confluencia +2 co |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | operate | -0.18% | Pendiente fuertemente alcista (42.2), range_pos 0.62 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | operate | -1.62% | Pendiente fuertemente alcista (24.15), range_pos 0.38 en zona de retroceso, GBM 0.52 > 0.5 |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | wait | -2.48% | Aunque tendencia alcista y rango correcto, el R:R es pobre: stop 3% y TP 2R requeriría 6%  |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | wait | -1.15% | Pendiente alcista fuerte y range_pos en zona de retroceso, pero distancia al techo muy cor |

</details>


## Corrida 2026-06-28T04:23:24.137Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 60 | IA operó: 53 | IA esperó: 7

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 60 | 53 | 7 |
| win rate | 36.7% | 39.6% | 14.3% |
| PnL (suma log) | 0.6% | 7.3% | -6.7% |

**Veredicto:** ✅ La IA MEJORA (su criterio sube el PnL frente a operar todo).

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | operate | -3.05% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.36 en zona óptima, GBM 0.54  |
| 2025-12-08T16:00 | 0.49 | 0.55 | +3.8e+1 | 0 | operate | 4.52% | Señal pullback long en zona óptima (range_pos 0.49), tendencia alcista fuerte (pendiente 3 |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | wait | 2.18% | Aunque tendencia y zona son correctas, el recorrido hasta el techo (1.8%) es menor que el  |
| 2025-12-09T11:00 | 0.58 | 0.51 | +1.9e+1 | 0 | operate | 1.85% | Pendiente positiva (19.03), range_pos 0.58 en zona de retroceso, GBM 0.51 > 0.5, confluenc |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | operate | -0.18% | Pendiente fuertemente alcista (9.23), range_pos 0.64 en zona de retroceso, GBM 0.53 > 0.5, |
| 2025-12-22T22:00 | 0.35 | 0.55 | +2.2e+1 | 0 | operate | -1.48% | Pendiente fuertemente alcista (21.99), range_pos 0.35 en zona de retroceso, GBM 0.55 > 0.5 |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | operate | -0.08% | Pendiente positiva (15.58), range_pos 0.37 en zona de retroceso, GBM 0.53 > 0.5, sin patro |
| 2025-12-31T11:00 | 0.61 | 0.53 | +4.4e-2 | 0 | operate | -1.16% | Pendiente positiva (0.044), range_pos 0.61 en zona de retroceso, GBM 0.53 > 0.5, confluenc |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | operate | 0.61% | Pullback long en tendencia alcista (pendiente 18.5), range_pos 0.38 en zona óptima, GBM 0. |
| 2026-01-01T10:00 | 0.40 | 0.51 | +2.4e+0 | 0 | operate | 1.98% | Pendiente fuertemente positiva (2.4), range_pos 0.40 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | Señal en zona de retroceso y tendencia alcista, pero el recorrido hasta el techo (1.5%) es |
| 2026-01-10T15:00 | 0.49 | 0.55 | +1.3e+0 | 0 | operate | 0.18% | Señal de pullback long en zona óptima (range_pos 0.49) con tendencia alcista (pendiente 1. |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | operate | 0.53% | Pendiente positiva (16.5), range_pos 0.54 en zona de retroceso, GBM 0.57 > 0.5, sin patron |
| 2026-01-12T21:00 | 0.39 | 0.53 | +1.6e+1 | 0 | operate | 3.23% | Pendiente positiva (16.3), range_pos 0.39 en zona de retroceso, GBM 0.53 > 0.5, confluenci |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | wait | -0.59% | R:R insuficiente: distancia al techo (2.5%) es menor que 1.5x stop (4.5%). Patrón de velas |
| 2026-01-16T04:00 | 0.45 | 0.52 | +2.4e+1 | 0 | operate | -0.01% | Pendiente alcista fuerte (24.28), range_pos 0.45 en zona de retroceso, GBM 0.52 > 0.5, sin |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | operate | -0.42% | Pullback long en tendencia alcista (pendiente 4.95), range_pos 0.40 en zona óptima, GBM 0. |
| 2026-02-09T07:00 | 0.63 | 0.54 | +2.7e+1 | 0 | wait | -3.05% | Señal pullback long en zona correcta (0.628) y tendencia alcista, pero distancia al techo  |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | operate | -0.44% | Pendiente fuertemente alcista (25.27), range_pos 0.455 en zona de retroceso, GBM 0.575 > 0 |
| 2026-02-27T01:00 | 0.64 | 0.60 | +7.2e+1 | 2 | operate | -3.05% | Pendiente fuertemente alcista (71.86), range_pos 0.635 en zona de retroceso, GBM 0.6 > 0.5 |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | operate | -3.05% | Pendiente positiva (36.6), range_pos 0.45 en zona de retroceso, GBM 0.63 > 0.5, sin patron |
| 2026-03-03T04:00 | 0.63 | 0.56 | +3.6e+1 | 0 | operate | -0.55% | Pendiente positiva (36.05), range_pos 0.626 en zona de retroceso, GBM 0.564 > 0.5, conflue |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | operate | 5.95% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.36 en zona óptima, GBM 0.53  |
| 2026-03-05T18:00 | 0.61 | 0.60 | +1.1e+2 | 0 | operate | -3.05% | Pendiente positiva fuerte (113), range_pos 0.61 en zona de retroceso, GBM 0.60 > 0.5, conf |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | operate | -3.05% | Pendiente fuertemente alcista, range_pos en zona de retroceso (0.61), GBM supera umbral, c |
| 2026-03-06T10:00 | 0.47 | 0.51 | +2.3e+1 | 0 | operate | -3.05% | Pendiente positiva, range_pos 0.47 en zona de retroceso, GBM 0.51 > 0.5, confluencia neutr |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | operate | 2.88% | Pendiente fuertemente alcista (8.6), range_pos 0.36 en zona de retroceso, GBM apenas super |
| 2026-03-13T17:00 | 0.42 | 0.52 | +4.2e+1 | 0 | operate | -0.64% | Pullback long en zona óptima (range_pos 0.42) con tendencia alcista fuerte (pendiente 41.6 |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | -0.48% | Pendiente positiva (38.8), range_pos 0.43 en zona de retroceso, GBM 0.55 > 0.5, confluenci |
| 2026-03-17T05:00 | 0.64 | 0.51 | +7.5e+1 | 0 | wait | -0.17% | Pendiente alcista fuerte y range_pos en zona de retroceso, pero distancia al techo (2.7%)  |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | wait | -1.52% | GBM apenas supera umbral (0.507), confluencia neutra (0), y distancia al techo (2.7%) limi |
| 2026-03-17T16:00 | 0.61 | 0.55 | +5.8e+1 | 1 | operate | -3.05% | Pendiente fuertemente positiva (57.6), range_pos 0.61 en zona de retroceso, GBM 0.55 > 0.5 |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (31.8), range_pos 0.56 en zona de retroceso, GBM 0.61 > 0.5, |
| 2026-03-18T10:00 | 0.45 | 0.53 | +1.5e+1 | 0 | operate | -3.05% | Señal de pullback long en tendencia alcista (pendiente 15.5), range_pos 0.45 dentro de zon |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | operate | -3.05% | Pendiente positiva fuerte (12.17), range_pos 0.62 en zona de retroceso, GBM 0.55 > 0.5, si |
| 2026-03-24T17:00 | 0.42 | 0.55 | +4.9e+1 | 0 | operate | 2.15% | Pendiente fuertemente positiva (48.5), range_pos 0.42 en zona de retroceso, GBM 0.55 > 0.5 |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | operate | 1.34% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 8.6) |
| 2026-03-30T20:00 | 0.52 | 0.57 | +1.3e+1 | 0 | operate | 2.34% | Pendiente positiva (12.58), range_pos 0.52 en zona de retroceso, GBM 0.57 > 0.5, sin patro |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | operate | 2.94% | Pullback long en zona óptima (range_pos 0.49) con tendencia alcista fuerte (pendiente 12.2 |
| 2026-04-02T01:00 | 0.41 | 0.50 | +3.0e+1 | 0 | operate | -1.14% | Pendiente fuertemente alcista (29.6), range_pos 0.41 en zona de retroceso, GBM justo en um |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | operate | 3.16% | Pendiente positiva fuerte (5.09), range_pos 0.64 en zona de retroceso, GBM 0.55 > 0.5, con |
| 2026-04-07T01:00 | 0.48 | 0.51 | +5.3e+1 | 0 | operate | 5.95% | Pendiente fuertemente positiva (53.2), range_pos 0.48 en zona de retroceso, GBM 0.51 super |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | operate | 4.23% | Pendiente fuertemente alcista (48.56), range_pos 0.54 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-04-07T13:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | 5.95% | Señal pullback long en zona óptima (range_pos 0.43) con tendencia alcista fuerte (pendient |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | operate | 1.50% | Pendiente positiva (7.19), range_pos 0.58 en zona de retroceso, GBM 0.51 > 0.5, confluenci |
| 2026-04-15T13:00 | 0.64 | 0.51 | +6.2e+1 | 0 | operate | -0.42% | Pendiente fuertemente alcista (62.5), range_pos 0.64 en zona de retroceso, GBM 0.514 > 0.5 |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | operate | 4.14% | Pullback long en tendencia alcista (pendiente 0.62), range_pos 0.38 en zona dorada, GBM 0. |
| 2026-04-18T12:00 | 0.58 | 0.52 | +5.5e+1 | 0 | operate | -0.89% | Pendiente positiva fuerte, range_pos en zona de retroceso (0.58), GBM supera umbral, RSI s |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | operate | -1.43% | Señal de pullback long en zona óptima (range_pos 0.50) con tendencia alcista fuerte (pendi |
| 2026-04-18T21:00 | 0.50 | 0.53 | +4.0e+1 | 1 | operate | -1.91% | Pendiente fuertemente alcista (40.3), range_pos 0.5 en zona de retroceso, GBM 0.53 > 0.5,  |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | operate | 4.36% | Pullback long en zona óptima (0.59) con tendencia alcista fuerte, GBM >0.5, patrones alcis |
| 2026-04-23T10:00 | 0.56 | 0.50 | +5.6e+1 | 0 | operate | 0.40% | Pendiente positiva (56.4), range_pos 0.555 en zona de retroceso, GBM 0.504 > 0.5, confluen |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | operate | -0.18% | Pendiente fuertemente alcista (42.2), range_pos 0.62 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-04-24T08:00 | 0.60 | 0.53 | +9.9e+0 | 1 | operate | -0.23% | Señal de pullback long en tendencia alcista (pendiente 9.9), range_pos 0.595 en zona óptim |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | operate | -1.62% | Pendiente fuertemente alcista (24.15), range_pos 0.38 en zona de retroceso, GBM 0.52 > 0.5 |
| 2026-05-11T11:00 | 0.45 | 0.51 | +1.7e+1 | 0 | operate | -0.56% | Señal de pullback long en tendencia alcista (pendiente 16.5), range_pos 0.45 en zona óptim |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | operate | -2.48% | Señal pullback long en zona correcta (range_pos 0.55) con tendencia alcista fuerte (pendie |
| 2026-05-15T12:00 | 0.50 | 0.53 | +1.1e+1 | 0 | operate | -3.05% | Señal de pullback long en zona óptima (range_pos 0.495), tendencia alcista fuerte (pendien |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | wait | -1.15% | Señal en zona de retroceso y tendencia alcista, pero el recorrido hasta el techo es solo 1 |
| 2026-05-22T09:00 | 0.47 | 0.53 | +8.3e+0 | 1 | operate | -3.05% | Pendiente positiva (8.27), range_pos 0.47 en zona de retroceso, GBM 0.53 > 0.5, confluenci |

</details>


## Corrida 2026-06-28T04:33:01.495Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 120 | IA operó: 105 | IA esperó: 15

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 120 | 105 | 15 |
| win rate | 40.8% | 41.9% | 33.3% |
| PnL (suma log) | 2.1% | 11.4% | -9.3% |

**Veredicto:** ✅ La IA MEJORA (su criterio sube el PnL frente a operar todo).

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.54 | +1.9e+0 | 1 | operate | -3.05% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 1.85 |
| 2025-12-07T22:00 | 0.46 | 0.60 | +1.7e+0 | 0 | operate | 1.32% | Señal pullback long en zona óptima (range_pos 0.46) con tendencia alcista fuerte (pendient |
| 2025-12-08T16:00 | 0.49 | 0.55 | +3.8e+1 | 0 | operate | 4.52% | Pendiente positiva fuerte (37.5), range_pos 0.49 en zona de retroceso, GBM 0.55 > 0.5, con |
| 2025-12-08T18:00 | 0.48 | 0.55 | +3.6e+1 | 0 | operate | 4.30% | Señal de pullback long en zona óptima (range_pos 0.48) con tendencia alcista fuerte (pendi |
| 2025-12-08T23:00 | 0.64 | 0.53 | +3.5e+1 | 0 | wait | 2.18% | Aunque la tendencia es alcista y la posición en rango es correcta, el R:R es pobre (recorr |
| 2025-12-09T06:00 | 0.54 | 0.52 | +2.7e+1 | 0 | wait | 2.72% | R:R insuficiente (distancia al techo 2.4% vs stop 3% da ~0.8R, no alcanza 1.5R mínimo). Ad |
| 2025-12-09T11:00 | 0.58 | 0.51 | +1.9e+1 | 0 | operate | 1.85% | Pendiente positiva (19.03), range_pos 0.58 en zona de retroceso, GBM 0.51 > 0.5, sin patro |
| 2025-12-09T14:00 | 0.58 | 0.54 | +1.4e+1 | 0 | operate | 1.57% | Pendiente positiva (14.5), range_pos 0.58 en zona de retroceso, GBM 0.54 > 0.5, confluenci |
| 2025-12-22T01:00 | 0.64 | 0.53 | +9.2e+0 | 1 | operate | -0.18% | Pullback long en tendencia alcista (pendiente 9.23), range_pos 0.64 en zona de retroceso,  |
| 2025-12-22T17:00 | 0.57 | 0.52 | +2.6e+1 | 0 | wait | -3.05% | R:R insuficiente: el recorrido hasta el techo (1.4%) es menor que 1.5x el stop (4.5%). Aun |
| 2025-12-22T22:00 | 0.35 | 0.55 | +2.2e+1 | 0 | operate | -1.48% | Pendiente fuertemente alcista (21.99), range_pos 0.35 en zona de retroceso, GBM 0.55 > 0.5 |
| 2025-12-25T23:00 | 0.37 | 0.51 | +9.0e+0 | 0 | operate | 0.12% | Pullback long en zona óptima (range_pos 0.37) con tendencia alcista fuerte (pendiente 9.03 |
| 2025-12-26T20:00 | 0.37 | 0.53 | +1.6e+1 | 0 | operate | -0.08% | Señal de pullback long en tendencia alcista fuerte (pendiente 15.58), range_pos 0.37 en zo |
| 2025-12-28T22:00 | 0.52 | 0.50 | +2.5e+0 | 0 | operate | -0.68% | Señal de pullback long en zona óptima (range_pos 0.52) con tendencia alcista fuerte (pendi |
| 2025-12-31T11:00 | 0.61 | 0.53 | +4.4e-2 | 0 | operate | -1.16% | Pendiente positiva (0.044), range_pos 0.61 en zona de retroceso, GBM 0.53 > 0.5, confluenc |
| 2025-12-31T13:00 | 0.61 | 0.56 | +2.8e+0 | 0 | operate | -1.26% | Pendiente positiva (2.85), range_pos 0.607 en zona de retroceso, GBM 0.556 > 0.5, confluen |
| 2025-12-31T21:00 | 0.38 | 0.54 | +1.8e+1 | 0 | operate | 0.61% | Pullback long en zona óptima (0.38) con tendencia alcista fuerte (pendiente 18.5) y GBM >  |
| 2026-01-01T08:00 | 0.36 | 0.50 | +5.2e+0 | 0 | operate | 1.54% | Pendiente alcista fuerte (5.22), range_pos 0.36 en zona de retroceso, GBM justo sobre umbr |
| 2026-01-01T10:00 | 0.40 | 0.51 | +2.4e+0 | 0 | operate | 1.98% | Pendiente fuertemente alcista (2.4), range_pos 0.40 en zona de retroceso, GBM supera umbra |
| 2026-01-06T20:00 | 0.42 | 0.54 | +4.0e+1 | 0 | operate | -1.64% | Pendiente positiva (39.56), range_pos 0.42 en zona de retroceso, GBM 0.54 > 0.5, confluenc |
| 2026-01-06T22:00 | 0.64 | 0.53 | +3.7e+1 | 0 | wait | -2.41% | Señal en zona de retroceso y tendencia alcista, pero el recorrido hasta el techo (1.5%) es |
| 2026-01-10T13:00 | 0.49 | 0.55 | +9.4e-1 | 0 | operate | 0.16% | Pendiente positiva (0.94), range_pos 0.485 en zona de retroceso, GBM 0.55 > 0.5, sin patro |
| 2026-01-10T15:00 | 0.49 | 0.55 | +1.3e+0 | 0 | operate | 0.18% | Señal pullback long en zona óptima (range_pos 0.49) con tendencia alcista (pendiente>0) y  |
| 2026-01-10T17:00 | 0.45 | 0.56 | +1.8e+0 | 0 | operate | 0.44% | Señal pullback long en zona correcta (range_pos 0.445), tendencia alcista (pendiente 1.82) |
| 2026-01-12T07:00 | 0.54 | 0.57 | +1.7e+1 | 0 | operate | 0.53% | Señal pullback long en zona óptima (range_pos 0.54) con tendencia alcista fuerte (pendient |
| 2026-01-12T17:00 | 0.58 | 0.52 | +1.4e+1 | 0 | operate | 1.81% | Pendiente fuertemente alcista (14.44), range_pos 0.58 en zona de retroceso, GBM 0.52 > 0.5 |
| 2026-01-12T21:00 | 0.39 | 0.53 | +1.6e+1 | 0 | operate | 3.23% | Pendiente positiva (16.3), range_pos 0.39 en zona de retroceso, GBM 0.53 > 0.5, confluenci |
| 2026-01-12T23:00 | 0.49 | 0.50 | +1.7e+1 | 1 | operate | 4.36% | Pullback long en zona óptima (0.49) con tendencia alcista fuerte (pendiente 16.6), GBM sup |
| 2026-01-15T19:00 | 0.61 | 0.52 | +7.5e+1 | 0 | wait | -0.59% | Señal en zona de retroceso y tendencia alcista, pero distancia al techo es solo 2.5% (stop |
| 2026-01-15T21:00 | 0.62 | 0.52 | +6.4e+1 | 0 | operate | -0.11% | Pendiente fuertemente alcista (63.99), range_pos 0.62 en zona de retroceso, GBM 0.52 > 0.5 |
| 2026-01-16T04:00 | 0.45 | 0.52 | +2.4e+1 | 0 | operate | -0.01% | Pendiente alcista fuerte (24.28), range_pos 0.45 en zona de retroceso, GBM 0.52 > 0.5, sin |
| 2026-01-16T07:00 | 0.41 | 0.50 | +1.2e+1 | 0 | operate | -0.63% | Pendiente fuertemente alcista (11.93), range_pos 0.41 en zona de retroceso, GBM 0.504 supe |
| 2026-01-16T09:00 | 0.40 | 0.55 | +4.9e+0 | 0 | operate | -0.42% | Señal pullback long en zona óptima (range_pos 0.40) con tendencia alcista fuerte (pendient |
| 2026-01-28T20:00 | 0.59 | 0.53 | +3.6e+1 | 0 | operate | -3.05% | Pendiente positiva fuerte (35.9), range_pos 0.59 en zona de retroceso, GBM 0.53 > 0.5, con |
| 2026-02-09T07:00 | 0.63 | 0.54 | +2.7e+1 | 0 | wait | -3.05% | Pendiente alcista fuerte y range_pos en zona de retroceso, pero la distancia al techo (2.6 |
| 2026-02-09T12:00 | 0.37 | 0.59 | +2.5e+1 | 0 | operate | -0.83% | Señal pullback long en zona óptima (range_pos 0.37) con tendencia alcista fuerte (pendient |
| 2026-02-09T15:00 | 0.46 | 0.58 | +2.5e+1 | 0 | operate | -0.44% | Pendiente positiva fuerte (25.27), range_pos 0.455 en zona de retroceso, GBM 0.575 > 0.5,  |
| 2026-02-26T17:00 | 0.58 | 0.70 | +1.0e+2 | 1 | operate | -1.75% | Señal pullback long en zona óptima (range_pos 0.58) con tendencia alcista fuerte (pendient |
| 2026-02-27T01:00 | 0.64 | 0.60 | +7.2e+1 | 2 | operate | -3.05% | Pendiente fuertemente alcista (71.86), range_pos 0.635 en zona de retroceso, GBM 0.6 > 0.5 |
| 2026-02-27T07:00 | 0.63 | 0.51 | +5.1e+1 | 1 | operate | -3.05% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.63 en zona de retroceso, GBM |
| 2026-02-27T10:00 | 0.45 | 0.63 | +3.7e+1 | 0 | operate | -3.05% | Pendiente positiva (36.6), range_pos 0.45 en zona de retroceso, GBM 0.63 > 0.5, sin patron |
| 2026-03-01T20:00 | 0.44 | 0.55 | +2.0e+1 | 0 | operate | 5.95% | Pendiente fuertemente alcista (19.85), range_pos 0.44 en zona de retroceso, GBM 0.55 > 0.5 |
| 2026-03-03T04:00 | 0.63 | 0.56 | +3.6e+1 | 0 | wait | -0.55% | Señal pullback long con tendencia alcista y rango correcto, pero el riesgo/beneficio es po |
| 2026-03-03T07:00 | 0.62 | 0.50 | +3.5e+1 | 0 | wait | 1.87% | R:R insuficiente: distancia al techo (2.8%) es menor que 1.5x el stop (4.5%). Aunque tende |
| 2026-03-03T10:00 | 0.36 | 0.53 | +3.2e+1 | 1 | operate | 5.95% | Pullback long en tendencia alcista (pendiente 31.9), range_pos 0.36 en zona óptima, GBM 0. |
| 2026-03-03T13:00 | 0.37 | 0.59 | +3.1e+1 | 0 | operate | 5.95% | Pendiente positiva fuerte (31.02), range_pos 0.37 en zona de retroceso, GBM 0.59 > 0.5, RS |
| 2026-03-05T18:00 | 0.61 | 0.60 | +1.1e+2 | 0 | operate | -3.05% | Pendiente positiva, range_pos 0.61 en zona de retroceso, GBM 0.60 > 0.5, confluencia neutr |
| 2026-03-05T22:00 | 0.64 | 0.72 | +9.4e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista fuerte (pendiente 93.7), range_pos 0.64 en zona de retr |
| 2026-03-06T00:00 | 0.61 | 0.53 | +8.2e+1 | 1 | operate | -3.05% | Pendiente fuertemente positiva (82), range_pos 0.61 en zona de retroceso, GBM 0.53 > 0.5,  |
| 2026-03-06T05:00 | 0.46 | 0.56 | +5.2e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.46 en zona óptima, GBM 0.56  |
| 2026-03-06T10:00 | 0.47 | 0.51 | +2.3e+1 | 0 | operate | -3.05% | Pendiente fuertemente positiva (22.8), range_pos 0.47 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-03-06T12:00 | 0.38 | 0.59 | +7.8e+0 | 0 | operate | -3.05% | Señal de pullback long en tendencia alcista (pendiente 7.79), range_pos 0.377 en zona ópti |
| 2026-03-12T05:00 | 0.36 | 0.50 | +8.6e+0 | 0 | operate | 2.88% | Pendiente fuertemente alcista (8.6), range_pos 0.36 en zona de retroceso, GBM apenas super |
| 2026-03-13T15:00 | 0.58 | 0.54 | +4.1e+1 | 0 | operate | -1.81% | Pullback long en tendencia alcista (pendiente 41.1), range_pos 0.58 en zona óptima, GBM 0. |
| 2026-03-13T17:00 | 0.42 | 0.52 | +4.2e+1 | 0 | operate | -0.64% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.42 en zona óptima, GBM 0.52  |
| 2026-03-13T19:00 | 0.45 | 0.55 | +4.1e+1 | 0 | operate | -0.74% | Pullback long en tendencia alcista (pendiente 40.6), range_pos 0.45 en zona óptima, GBM 0. |
| 2026-03-13T21:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | -0.48% | Pendiente positiva (38.8), range_pos 0.43 en zona de retroceso, GBM 0.55 > 0.5, confluenci |
| 2026-03-13T23:00 | 0.40 | 0.53 | +3.5e+1 | 1 | operate | 0.35% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.395 en zona óptima, GBM 0.53 |
| 2026-03-17T05:00 | 0.64 | 0.51 | +7.5e+1 | 0 | wait | -0.17% | Aunque tendencia y zona son correctas, el recorrido hasta el techo (2.7%) es menor que el  |
| 2026-03-17T09:00 | 0.61 | 0.53 | +7.0e+1 | 0 | wait | 0.28% | Aunque tendencia y zona son correctas y GBM supera umbral, la confluencia de velas es neut |
| 2026-03-17T11:00 | 0.62 | 0.51 | +6.6e+1 | 0 | wait | -1.52% | Señal en zona de retroceso y tendencia alcista, pero R:R no es favorable (distancia al tec |
| 2026-03-17T13:00 | 0.52 | 0.52 | +6.1e+1 | 0 | operate | -2.08% | Pendiente fuertemente positiva (61.4), range_pos 0.52 en zona de retroceso, GBM 0.516 > 0. |
| 2026-03-17T16:00 | 0.61 | 0.55 | +5.8e+1 | 1 | operate | -3.05% | Pendiente fuertemente positiva (57.6), range_pos 0.61 en zona de retroceso, GBM 0.55 > 0.5 |
| 2026-03-18T02:00 | 0.65 | 0.64 | +4.1e+1 | 0 | operate | -3.05% | Pendiente fuertemente positiva (40.76), range_pos 0.645 en zona de retroceso, GBM 0.64 > 0 |
| 2026-03-18T05:00 | 0.56 | 0.61 | +3.2e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (31.8), range_pos 0.56 en zona de retroceso, GBM 0.61 > 0.5, |
| 2026-03-18T07:00 | 0.54 | 0.61 | +2.4e+1 | 1 | operate | -3.05% | Pullback long en zona óptima (range_pos 0.54) con tendencia alcista fuerte (pendiente 23.9 |
| 2026-03-18T10:00 | 0.45 | 0.53 | +1.5e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (15.49), range_pos 0.45 en zona de retroceso, GBM 0.53 > 0.5 |
| 2026-03-21T16:00 | 0.59 | 0.53 | +1.1e+1 | 0 | operate | -3.05% | Pendiente positiva fuerte (10.87), range_pos 0.59 en zona de retroceso, GBM 0.53 > 0.5, co |
| 2026-03-21T18:00 | 0.62 | 0.55 | +1.2e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (12.17), range_pos 0.62 en zona de retroceso, GBM 0.55 > 0.5 |
| 2026-03-21T20:00 | 0.65 | 0.56 | +1.2e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (11.7), range_pos 0.65 en zona de retroceso, GBM 0.556 > 0.5 |
| 2026-03-24T17:00 | 0.42 | 0.55 | +4.9e+1 | 0 | operate | 2.15% | Señal pullback long en tendencia alcista fuerte (pendiente 48.5), range_pos 0.42 en zona ó |
| 2026-03-29T20:00 | 0.44 | 0.51 | +7.3e+0 | 0 | operate | 0.01% | Pendiente positiva (7.28), range_pos 0.44 en zona de retroceso, GBM 0.51 > 0.5, sin patron |
| 2026-03-29T22:00 | 0.38 | 0.55 | +8.6e+0 | 0 | operate | 1.34% | Pendiente fuertemente alcista (8.6), range_pos 0.38 en zona de retroceso, GBM 0.55 > 0.5,  |
| 2026-03-30T18:00 | 0.52 | 0.55 | +1.5e+1 | 0 | operate | 1.74% | Pendiente positiva fuerte (14.55), range_pos 0.52 en zona de retroceso, GBM 0.55 > 0.5, si |
| 2026-03-30T20:00 | 0.52 | 0.57 | +1.3e+1 | 0 | operate | 2.34% | Pendiente positiva (12.58), range_pos 0.52 en zona de retroceso, GBM 0.57 > 0.5, sin patro |
| 2026-03-30T23:00 | 0.57 | 0.53 | +9.4e+0 | 2 | operate | 2.15% | Pullback long en zona óptima (range_pos 0.57) con tendencia alcista fuerte (pendiente 9.44 |
| 2026-03-31T11:00 | 0.49 | 0.52 | +1.2e+1 | 0 | operate | 2.94% | Pullback long en zona óptima (range_pos 0.49) con tendencia alcista fuerte (pendiente 12.2 |
| 2026-04-01T13:00 | 0.64 | 0.52 | +2.1e+1 | 0 | wait | -3.05% | Señal en zona de retroceso y tendencia alcista, pero la distancia al techo (1.8%) no permi |
| 2026-04-02T01:00 | 0.41 | 0.50 | +3.0e+1 | 0 | operate | -1.14% | Pullback long en zona óptima (range_pos 0.41) con tendencia alcista fuerte (pendiente 29.6 |
| 2026-04-04T12:00 | 0.48 | 0.55 | +6.7e+0 | 0 | operate | -0.52% | Pendiente positiva fuerte (6.7), range_pos 0.48 en zona de retroceso, GBM 0.55 > 0.5, conf |
| 2026-04-05T17:00 | 0.64 | 0.55 | +5.1e+0 | 0 | operate | 3.16% | Pendiente positiva fuerte (5.09), range_pos 0.64 en zona de retroceso, GBM 0.55 > 0.5, sin |
| 2026-04-06T22:00 | 0.59 | 0.56 | +5.5e+1 | 0 | operate | 3.80% | Señal de pullback long en tendencia alcista (pendiente 55.4), range_pos 0.59 en zona óptim |
| 2026-04-07T01:00 | 0.48 | 0.51 | +5.3e+1 | 0 | operate | 5.95% | Pendiente positiva fuerte (53.2), range_pos 0.48 en zona de retroceso, GBM 0.51 > 0.5, con |
| 2026-04-07T04:00 | 0.60 | 0.51 | +5.2e+1 | 0 | operate | 3.81% | Pullback long en zona óptima (range_pos 0.60) con tendencia alcista fuerte (pendiente 51.6 |
| 2026-04-07T07:00 | 0.54 | 0.51 | +4.9e+1 | 1 | operate | 4.23% | Pullback long en zona óptima (range_pos 0.54) con tendencia alcista fuerte (pendiente 48.6 |
| 2026-04-07T11:00 | 0.46 | 0.54 | +4.4e+1 | 1 | operate | 5.95% | Pendiente fuertemente alcista (43.8), range_pos 0.46 en zona de retroceso, GBM 0.54 > 0.5, |
| 2026-04-07T13:00 | 0.43 | 0.55 | +3.9e+1 | 0 | operate | 5.95% | Pullback long en tendencia alcista (pendiente 39.3), range_pos 0.43 en zona óptima, GBM 0. |
| 2026-04-07T17:00 | 0.56 | 0.53 | +2.9e+1 | 0 | operate | 4.48% | Pendiente positiva fuerte (28.66), range_pos 0.56 en zona de retroceso, GBM 0.53 > 0.5, co |
| 2026-04-10T09:00 | 0.58 | 0.51 | +7.2e+0 | 0 | operate | 1.50% | Pendiente positiva (7.19), range_pos 0.58 en zona de retroceso, GBM 0.51 > 0.5, confluenci |
| 2026-04-10T11:00 | 0.62 | 0.52 | +9.3e+0 | 0 | operate | 1.02% | Pendiente fuertemente alcista (9.25), range_pos 0.62 en zona de retroceso, GBM 0.52 > 0.5, |
| 2026-04-15T13:00 | 0.64 | 0.51 | +6.2e+1 | 0 | operate | -0.42% | Pendiente fuertemente alcista (62.5), range_pos 0.64 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-04-16T08:00 | 0.54 | 0.52 | +5.7e+0 | 0 | operate | 1.42% | Pullback long en tendencia alcista (pendiente 5.74), range_pos 0.54 en zona óptima, GBM 0. |
| 2026-04-16T17:00 | 0.38 | 0.52 | +6.2e-1 | 1 | operate | 4.14% | Pullback long en zona óptima (range_pos 0.38) con tendencia alcista fuerte (pendiente 0.62 |
| 2026-04-18T10:00 | 0.57 | 0.52 | +5.7e+1 | 0 | operate | -1.33% | Señal de pullback long en zona correcta (range_pos 0.57) con tendencia alcista fuerte (pen |
| 2026-04-18T12:00 | 0.58 | 0.52 | +5.5e+1 | 0 | operate | -0.89% | Pendiente positiva fuerte (55.1), range_pos 0.58 en zona de retroceso, GBM 0.52 > 0.5, sin |
| 2026-04-18T14:00 | 0.59 | 0.53 | +5.3e+1 | 0 | operate | -0.35% | Señal pullback long en zona correcta (range_pos 0.585) con tendencia alcista fuerte (pendi |
| 2026-04-18T17:00 | 0.50 | 0.53 | +4.9e+1 | 0 | operate | -1.43% | Pendiente positiva fuerte (49.18), range_pos 0.50 en zona de retroceso, GBM 0.53 > 0.5, si |
| 2026-04-18T19:00 | 0.47 | 0.52 | +4.5e+1 | 0 | operate | -0.96% | Pendiente fuertemente alcista (45), range_pos 0.47 en zona de retroceso, GBM 0.52 > 0.5, s |
| 2026-04-18T21:00 | 0.50 | 0.53 | +4.0e+1 | 1 | operate | -1.91% | Pendiente fuertemente alcista (40.3), range_pos en zona ideal (0.50), GBM supera umbral (0 |
| 2026-04-18T23:00 | 0.47 | 0.51 | +3.5e+1 | 0 | operate | -2.58% | Pendiente fuertemente alcista (34.57), range_pos 0.47 en zona de retroceso, GBM 0.505 supe |
| 2026-04-21T18:00 | 0.59 | 0.56 | +2.2e+1 | 2 | operate | 4.36% | Señal pullback long en zona óptima (range_pos 0.59) con tendencia alcista fuerte (pendient |
| 2026-04-21T20:00 | 0.62 | 0.51 | +2.1e+1 | 0 | operate | 3.50% | Pendiente fuertemente alcista (21.45), range_pos 0.62 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-04-23T10:00 | 0.56 | 0.50 | +5.6e+1 | 0 | wait | 0.40% | Aunque tendencia y zona son correctas, las últimas velas son todas rojas (sin confirmación |
| 2026-04-23T13:00 | 0.58 | 0.55 | +5.2e+1 | 0 | operate | 0.67% | Pendiente positiva (52.25), range_pos 0.58 en zona de retroceso, GBM 0.55 > 0.5, confluenc |
| 2026-04-23T19:00 | 0.62 | 0.51 | +4.2e+1 | 1 | operate | -0.18% | Pendiente fuertemente alcista (42.2), range_pos 0.62 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-04-24T04:00 | 0.61 | 0.51 | +2.6e+1 | 0 | operate | -0.12% | Señal pullback long en tendencia alcista (pendiente 26.38), range_pos 0.61 dentro de zona  |
| 2026-04-24T08:00 | 0.60 | 0.53 | +9.9e+0 | 1 | operate | -0.23% | Pullback long en zona óptima (range_pos 0.60) con tendencia alcista fuerte (pendiente 9.9) |
| 2026-04-24T10:00 | 0.55 | 0.55 | +8.6e-1 | 0 | operate | -0.00% | Señal pullback long en tendencia alcista (pendiente>0), rango medio (0.55), GBM supera umb |
| 2026-05-07T03:00 | 0.38 | 0.52 | +2.4e+1 | 0 | operate | -1.62% | Pendiente fuertemente positiva (24.15), range_pos 0.38 en zona de retroceso, GBM 0.52 > 0. |
| 2026-05-07T05:00 | 0.43 | 0.52 | +2.1e+1 | 0 | operate | -1.90% | Pendiente fuertemente alcista (20.6), range_pos 0.43 en zona de retroceso, GBM 0.52 > 0.5, |
| 2026-05-11T11:00 | 0.45 | 0.51 | +1.7e+1 | 0 | operate | -0.56% | Señal de pullback long en tendencia alcista (pendiente 16.5), range_pos 0.45 en zona óptim |
| 2026-05-12T02:00 | 0.45 | 0.51 | +1.6e+1 | 1 | operate | -0.30% | Pullback long en zona óptima (0.45), pendiente alcista fuerte, GBM supera umbral, patrón h |
| 2026-05-15T06:00 | 0.55 | 0.50 | +6.1e+0 | 0 | operate | -2.48% | Pullback long en zona óptima (range_pos 0.55) con tendencia alcista fuerte (pendiente 6.1) |
| 2026-05-15T09:00 | 0.53 | 0.53 | +8.8e+0 | 0 | operate | -3.05% | Pendiente positiva fuerte (8.79), range_pos 0.53 en zona de retroceso, GBM supera umbral ( |
| 2026-05-15T12:00 | 0.50 | 0.53 | +1.1e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (10.74), range_pos 0.495 en zona de retroceso, GBM 0.527 > 0 |
| 2026-05-21T11:00 | 0.51 | 0.55 | +2.0e+1 | 0 | operate | 0.26% | Señal de pullback long en zona óptima (range_pos 0.51) con tendencia alcista fuerte (pendi |
| 2026-05-21T18:00 | 0.60 | 0.50 | +1.6e+1 | 0 | wait | -1.15% | R:R insuficiente: distancia al techo 1.0% vs stop 3% da R:R ~0.33:1, muy por debajo del mí |
| 2026-05-22T06:00 | 0.54 | 0.51 | +1.1e+1 | 0 | operate | -2.70% | Pendiente positiva fuerte (11.3), range_pos 0.54 en zona de retroceso, GBM 0.51 > 0.5, sin |
| 2026-05-22T09:00 | 0.47 | 0.53 | +8.3e+0 | 1 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 8.27), range_pos 0.47 en zona óptima, GBM 0. |
| 2026-05-26T01:00 | 0.59 | 0.52 | +2.3e+1 | 0 | wait | -1.20% | Señal de pullback en zona correcta y tendencia alcista, pero el R:R es pobre: el techo est |

</details>


## Corrida 2026-06-28T05:02:11.177Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 50 | IA operó: 46 | IA esperó: 4

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 50 | 46 | 4 |
| win rate | 44.0% | 43.5% | 50.0% |
| PnL (suma log) | 14.1% | 15.3% | -1.2% |

**Veredicto:** ✅ La IA MEJORA (su criterio sube el PnL frente a operar todo).

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.58 | +1.9e+0 | 1 | operate | -3.05% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 1.85 |
| 2025-12-08T16:00 | 0.49 | 0.60 | +3.8e+1 | 0 | operate | 4.52% | Señal pullback long en zona óptima (range_pos 0.49), tendencia alcista fuerte (pendiente 3 |
| 2025-12-09T02:00 | 0.51 | 0.55 | +3.2e+1 | 1 | operate | 2.61% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.51 en zona óptima, GBM 0.55  |
| 2025-12-09T08:00 | 0.61 | 0.50 | +2.5e+1 | 0 | operate | 2.25% | Pendiente positiva (24.58), range_pos 0.61 en zona de retroceso, GBM 0.503 > 0.5, confluen |
| 2025-12-19T17:00 | 0.42 | 0.60 | +1.2e+1 | 0 | operate | 1.36% | Pullback long en tendencia alcista (pendiente 12.48), range_pos 0.42 en zona óptima, GBM 0 |
| 2025-12-21T15:00 | 0.52 | 0.53 | +1.0e+1 | 0 | operate | 1.82% | Pendiente positiva fuerte (10.43), range_pos en zona de retroceso (0.52), GBM supera umbra |
| 2025-12-22T02:00 | 0.58 | 0.58 | +9.6e+0 | 1 | operate | -0.33% | Pendiente alcista fuerte (9.6), range_pos 0.58 en zona de retroceso, GBM 0.58 > 0.5, confl |
| 2025-12-25T22:00 | 0.57 | 0.53 | +9.1e+0 | 0 | operate | -0.16% | Pendiente fuertemente alcista (9.07), range_pos 0.57 en zona de retroceso, GBM 0.53 > 0.5, |
| 2026-01-06T16:00 | 0.47 | 0.57 | +5.3e+1 | 0 | operate | -1.60% | Pendiente positiva fuerte (53.44), range_pos 0.47 en zona de retroceso, GBM 0.57 > 0.5, co |
| 2026-01-07T01:00 | 0.40 | 0.52 | +2.9e+1 | 0 | operate | -1.15% | Pendiente fuertemente alcista (28.75), range_pos 0.40 en zona de retroceso, GBM 0.52 > 0.5 |
| 2026-01-07T07:00 | 0.48 | 0.51 | +8.6e+0 | 0 | operate | -3.05% | Pendiente fuertemente positiva (8.58), range_pos 0.48 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-01-10T17:00 | 0.45 | 0.52 | +1.8e+0 | 0 | operate | 0.44% | Señal de pullback long en tendencia alcista (pendiente>0), range_pos 0.445 en zona óptima, |
| 2026-01-12T17:00 | 0.58 | 0.61 | +1.4e+1 | 0 | operate | 1.81% | Pullback long en zona óptima (range_pos 0.58) con tendencia alcista fuerte (pendiente 14.4 |
| 2026-01-15T20:00 | 0.57 | 0.51 | +6.9e+1 | 0 | wait | 0.26% | Señal pullback long con tendencia alcista y rango correcto, pero el R:R es pobre: stop 3%  |
| 2026-01-16T02:00 | 0.58 | 0.54 | +3.4e+1 | 0 | operate | -0.19% | Pendiente fuertemente positiva (34.1), range_pos 0.58 en zona de retroceso, GBM 0.54 > 0.5 |
| 2026-01-16T07:00 | 0.41 | 0.54 | +1.2e+1 | 0 | operate | -0.63% | Pendiente fuertemente alcista (11.93), range_pos 0.41 en zona de retroceso, GBM 0.54 > 0.5 |
| 2026-01-28T20:00 | 0.59 | 0.51 | +3.6e+1 | 0 | operate | -3.05% | Pendiente positiva, range_pos 0.59 en zona de retroceso, GBM 0.51 > 0.5, confluencia neutr |
| 2026-02-03T16:00 | 0.40 | 0.69 | +8.5e+0 | 0 | operate | -3.05% | Pendiente positiva (8.49), range_pos 0.396 en zona de retroceso, GBM 0.69 > 0.5, sin patro |
| 2026-02-09T14:00 | 0.40 | 0.64 | +2.4e+1 | 0 | operate | -1.23% | Pullback long en tendencia alcista fuerte (pendiente 23.9), range_pos 0.40 en zona óptima, |
| 2026-02-15T18:00 | 0.49 | 0.52 | +4.0e+1 | 0 | operate | -0.92% | Pendiente positiva, range_pos en zona de retroceso (0.49), GBM supera umbral, confluencia  |
| 2026-02-16T00:00 | 0.48 | 0.51 | +1.0e+1 | 1 | operate | -0.00% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.48 en zona óptima, GBM 0.51  |
| 2026-02-27T11:00 | 0.36 | 0.65 | +2.9e+1 | 0 | operate | -3.05% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 29.4 |
| 2026-03-02T10:00 | 0.64 | 0.54 | +2.8e+1 | 0 | wait | 0.77% | R:R insuficiente: distancia al techo 2.8% vs stop 3% da R:R ~0.93, menor al mínimo 1.5. Co |
| 2026-03-03T08:00 | 0.39 | 0.64 | +3.4e+1 | 0 | operate | 5.95% | Pendiente fuertemente alcista (34.16), range_pos 0.39 en zona de retroceso, GBM 0.64 > 0.5 |
| 2026-03-03T15:00 | 0.53 | 0.56 | +3.2e+1 | 0 | operate | 5.95% | Pendiente positiva, range_pos 0.53 en zona de retroceso, GBM 0.56 > 0.5, confluencia neutr |
| 2026-03-06T04:00 | 0.48 | 0.57 | +5.8e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (57.8), range_pos 0.48 en zona de retroceso, GBM 0.57 > 0.5, |
| 2026-03-06T11:00 | 0.42 | 0.65 | +1.6e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 15.8), range_pos 0.42 en zona óptima, GBM 0. |
| 2026-03-12T08:00 | 0.45 | 0.52 | +1.2e+0 | 0 | operate | 2.64% | Señal pullback long en zona óptima (range_pos 0.45) con tendencia alcista fuerte (pendient |
| 2026-03-13T19:00 | 0.45 | 0.58 | +4.1e+1 | 0 | operate | -0.74% | Pullback long en tendencia alcista (pendiente 40.6), range_pos 0.45 en zona óptima, GBM 0. |
| 2026-03-14T03:00 | 0.40 | 0.52 | +3.1e+1 | 0 | operate | 0.35% | Pendiente fuertemente alcista (30.66), range_pos 0.40 en zona de retroceso, GBM 0.52 > 0.5 |
| 2026-03-17T06:00 | 0.65 | 0.54 | +7.4e+1 | 1 | operate | -0.23% | Pendiente fuertemente alcista (74.2), range_pos 0.646 en zona de retroceso, GBM 0.536 > 0. |
| 2026-03-17T13:00 | 0.52 | 0.51 | +6.1e+1 | 0 | operate | -2.08% | Pendiente fuertemente positiva (61.4), range_pos 0.52 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-03-18T04:00 | 0.61 | 0.52 | +3.5e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 34.96), range_pos 0.61 en zona óptima, GBM 0 |
| 2026-03-18T10:00 | 0.45 | 0.53 | +1.5e+1 | 0 | operate | -3.05% | Señal de pullback long en tendencia alcista (pendiente 15.5), range_pos 0.45 en zona óptim |
| 2026-03-21T21:00 | 0.60 | 0.52 | +1.2e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (12.0), range_pos 0.60 en zona de retroceso, GBM 0.52 > 0.5, |
| 2026-03-26T06:00 | 0.38 | 0.54 | +9.1e+0 | 1 | wait | -2.13% |  |
| 2026-03-30T20:00 | 0.52 | 0.59 | +1.3e+1 | 0 | operate | 2.34% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.52 en zona óptima, GBM 0.59  |
| 2026-03-31T11:00 | 0.49 | 0.51 | +1.2e+1 | 0 | operate | 2.94% | Pendiente positiva fuerte (12.27), range_pos 0.49 en zona de retroceso, GBM 0.51 > 0.5, co |
| 2026-04-05T17:00 | 0.64 | 0.59 | +5.1e+0 | 0 | operate | 3.16% | Pendiente positiva fuerte (5.09), range_pos 0.64 en zona de retroceso, GBM 0.59 > 0.5, sin |
| 2026-04-07T03:00 | 0.58 | 0.57 | +5.2e+1 | 0 | operate | 3.53% | Pullback long en tendencia alcista (pendiente 52), range_pos 0.58 en zona óptima, GBM 0.57 |
| 2026-04-07T08:00 | 0.62 | 0.50 | +4.8e+1 | 0 | operate | 4.02% | Pendiente fuertemente alcista (47.8), range_pos 0.62 en zona de retroceso, GBM supera umbr |
| 2026-04-07T15:00 | 0.42 | 0.57 | +3.4e+1 | 0 | operate | 5.95% | Pullback long en tendencia alcista (pendiente>0), range_pos 0.42 en zona óptima, GBM 0.57  |
| 2026-04-10T08:00 | 0.60 | 0.52 | +9.5e+0 | 1 | operate | 1.42% | Pendiente alcista fuerte (9.47), range_pos 0.60 en zona de retroceso, GBM 0.52 > 0.5, conf |
| 2026-04-16T08:00 | 0.54 | 0.51 | +5.7e+0 | 0 | operate | 1.42% | Pendiente positiva (5.74), range_pos 0.54 en zona de retroceso, GBM 0.51 > 0.5, confluenci |
| 2026-04-18T12:00 | 0.58 | 0.51 | +5.5e+1 | 0 | operate | -0.89% | Señal pullback long en zona correcta (range_pos 0.58), tendencia alcista fuerte (pendiente |
| 2026-04-18T21:00 | 0.50 | 0.53 | +4.0e+1 | 1 | operate | -1.91% | Pendiente fuertemente alcista (40.3), range_pos en zona dorada (0.50), GBM > 0.5, confluen |
| 2026-04-19T02:00 | 0.36 | 0.53 | +2.3e+1 | 0 | operate | -1.50% | Pendiente fuertemente alcista (23.07), range_pos 0.36 en zona de retroceso, GBM 0.525 > 0. |
| 2026-04-21T19:00 | 0.41 | 0.53 | +2.1e+1 | 0 | operate | 4.92% | Señal pullback long en zona óptima (range_pos 0.41) con tendencia alcista fuerte (pendient |
| 2026-04-24T03:00 | 0.63 | 0.57 | +3.0e+1 | 0 | wait | -0.13% | R:R insuficiente: distancia al techo 2.2% no alcanza para TP 2R (necesita ~6%). Además, do |
| 2026-04-24T10:00 | 0.55 | 0.56 | +8.6e-1 | 0 | operate | -0.00% | Pendiente positiva (0.86), range_pos 0.55 en zona de retroceso, GBM 0.56 > 0.5, confluenci |

</details>


## Corrida 2026-06-28T05:04:38.026Z — modelo pullback-long-btc (H=24, thr=0.5)
Señales probadas: 50 | IA operó: 45 | IA esperó: 5

| métrica | operar TODO | solo lo que aprobó la IA | lo que la IA evitó |
|---|---|---|---|
| nº trades | 50 | 45 | 5 |
| win rate | 44.0% | 40.0% | 80.0% |
| PnL (suma log) | 14.1% | 5.6% | 8.5% |

**Veredicto:** ⚠️ La IA RESTA (frena buenos trades). Revisar su prompt/criterio.

<details><summary>Detalle de decisiones</summary>

| fecha | range_pos | conf | slope | confluencia | IA | resultado | razón |
|---|---|---|---|---|---|---|---|
| 2025-11-30T22:00 | 0.36 | 0.58 | +1.9e+0 | 1 | operate | -3.05% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 1.85 |
| 2025-12-08T16:00 | 0.49 | 0.60 | +3.8e+1 | 0 | operate | 4.52% | Señal pullback long en zona óptima (range_pos 0.49), tendencia alcista fuerte (pendiente 3 |
| 2025-12-09T02:00 | 0.51 | 0.55 | +3.2e+1 | 1 | operate | 2.61% | Pullback long en zona óptima (range_pos 0.51) con tendencia alcista fuerte (pendiente 31.8 |
| 2025-12-09T08:00 | 0.61 | 0.50 | +2.5e+1 | 0 | wait | 2.25% | Señal pullback long con tendencia alcista y rango correcto, pero el recorrido hasta el tec |
| 2025-12-19T17:00 | 0.42 | 0.60 | +1.2e+1 | 0 | operate | 1.36% | Pullback long en zona óptima (range_pos 0.42) con tendencia alcista fuerte (pendiente 12.4 |
| 2025-12-21T15:00 | 0.52 | 0.53 | +1.0e+1 | 0 | operate | 1.82% | Pendiente positiva fuerte (10.43), range_pos 0.52 en zona de retroceso, GBM 0.53 > 0.5, co |
| 2025-12-22T02:00 | 0.58 | 0.58 | +9.6e+0 | 1 | operate | -0.33% | Pendiente positiva, range_pos 0.58 en zona de retroceso, GBM > 0.5, confluencia positiva,  |
| 2025-12-25T22:00 | 0.57 | 0.53 | +9.1e+0 | 0 | operate | -0.16% | Pendiente fuertemente alcista (9.07), range_pos 0.57 en zona de retroceso, GBM 0.53 > 0.5, |
| 2026-01-06T16:00 | 0.47 | 0.57 | +5.3e+1 | 0 | operate | -1.60% | Pendiente positiva (53.44), range_pos 0.47 en zona de retroceso, GBM 0.57 > 0.5, sin patro |
| 2026-01-07T01:00 | 0.40 | 0.52 | +2.9e+1 | 0 | operate | -1.15% | Pendiente positiva fuerte (28.75), range_pos 0.40 en zona de retroceso, GBM 0.52 > 0.5, si |
| 2026-01-07T07:00 | 0.48 | 0.51 | +8.6e+0 | 0 | operate | -3.05% | Pendiente fuertemente alcista (8.58), range_pos 0.48 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-01-10T17:00 | 0.45 | 0.52 | +1.8e+0 | 0 | operate | 0.44% | Señal de pullback long en tendencia alcista (pendiente 1.82), range_pos 0.445 en zona ópti |
| 2026-01-12T17:00 | 0.58 | 0.61 | +1.4e+1 | 0 | wait | 1.81% |  |
| 2026-01-15T20:00 | 0.57 | 0.51 | +6.9e+1 | 0 | operate | 0.26% | Pendiente fuertemente alcista (69.2), range_pos 0.57 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-01-16T02:00 | 0.58 | 0.54 | +3.4e+1 | 0 | operate | -0.19% | Pendiente positiva fuerte (34.1), range_pos 0.58 en zona de retroceso, GBM 0.54 > 0.5, sin |
| 2026-01-16T07:00 | 0.41 | 0.54 | +1.2e+1 | 0 | operate | -0.63% | Pendiente fuertemente alcista (11.93), range_pos 0.41 en zona de retroceso, GBM 0.54 > 0.5 |
| 2026-01-28T20:00 | 0.59 | 0.51 | +3.6e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (35.9), range_pos 0.59 en zona de retroceso, GBM 0.51 > 0.5, |
| 2026-02-03T16:00 | 0.40 | 0.69 | +8.5e+0 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 8.49), range_pos 0.396 en zona óptima, GBM 0 |
| 2026-02-09T14:00 | 0.40 | 0.64 | +2.4e+1 | 0 | operate | -1.23% | Pullback long en tendencia alcista fuerte (pendiente 23.9), range_pos 0.40 en zona óptima, |
| 2026-02-15T18:00 | 0.49 | 0.52 | +4.0e+1 | 0 | operate | -0.92% | Pendiente positiva, range_pos 0.49 en zona de retroceso, GBM 0.52 > 0.5, confluencia neutr |
| 2026-02-16T00:00 | 0.48 | 0.51 | +1.0e+1 | 1 | operate | -0.00% | Pendiente fuertemente alcista (10.29), range_pos 0.48 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-02-27T11:00 | 0.36 | 0.65 | +2.9e+1 | 0 | operate | -3.05% | Señal pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendient |
| 2026-03-02T10:00 | 0.64 | 0.54 | +2.8e+1 | 0 | operate | 0.77% | Pullback long en tendencia alcista (pendiente 27.8), range_pos 0.64 en zona de retroceso,  |
| 2026-03-03T08:00 | 0.39 | 0.64 | +3.4e+1 | 0 | operate | 5.95% | Pendiente positiva (34.16), range_pos 0.39 en zona de retroceso, GBM 0.64 > 0.5, sin patro |
| 2026-03-03T15:00 | 0.53 | 0.56 | +3.2e+1 | 0 | operate | 5.95% | Pullback long en zona óptima (range_pos 0.53) con tendencia alcista fuerte (pendiente 32)  |
| 2026-03-06T04:00 | 0.48 | 0.57 | +5.8e+1 | 0 | operate | -3.05% | Señal de pullback long en zona óptima (range_pos 0.48) con tendencia alcista fuerte (pendi |
| 2026-03-06T11:00 | 0.42 | 0.65 | +1.6e+1 | 0 | operate | -3.05% | Pullback long en tendencia alcista (pendiente 15.8), range_pos 0.42 en zona óptima, GBM 0. |
| 2026-03-12T08:00 | 0.45 | 0.52 | +1.2e+0 | 0 | operate | 2.64% | Señal pullback long en zona óptima (range_pos 0.45) con tendencia alcista fuerte (pendient |
| 2026-03-13T19:00 | 0.45 | 0.58 | +4.1e+1 | 0 | operate | -0.74% | Señal pullback long en zona óptima (range_pos 0.45) con tendencia alcista fuerte (pendient |
| 2026-03-14T03:00 | 0.40 | 0.52 | +3.1e+1 | 0 | operate | 0.35% | Pendiente fuertemente positiva (30.66), range_pos 0.40 en zona de retroceso, GBM 0.52 > 0. |
| 2026-03-17T06:00 | 0.65 | 0.54 | +7.4e+1 | 1 | operate | -0.23% | Pendiente fuertemente alcista (74.2), range_pos 0.646 en zona de retroceso, GBM 0.536 > 0. |
| 2026-03-17T13:00 | 0.52 | 0.51 | +6.1e+1 | 0 | operate | -2.08% | Pendiente fuertemente positiva (61.4), range_pos 0.52 en zona de retroceso, GBM 0.51 > 0.5 |
| 2026-03-18T04:00 | 0.61 | 0.52 | +3.5e+1 | 0 | operate | -3.05% | Pendiente positiva (34.96), range_pos 0.61 en zona de retroceso, GBM 0.52 > 0.5, confluenc |
| 2026-03-18T10:00 | 0.45 | 0.53 | +1.5e+1 | 0 | operate | -3.05% | Señal pullback long en tendencia alcista (pendiente>0), range_pos 0.45 en zona óptima, GBM |
| 2026-03-21T21:00 | 0.60 | 0.52 | +1.2e+1 | 0 | operate | -3.05% | Pendiente fuertemente alcista (12.0), range_pos 0.60 en zona de retroceso, GBM 0.52 > 0.5, |
| 2026-03-26T06:00 | 0.38 | 0.54 | +9.1e+0 | 1 | operate | -2.13% | Pendiente fuertemente alcista (9.11), range_pos 0.38 en zona de retroceso, GBM 0.54 > 0.5, |
| 2026-03-30T20:00 | 0.52 | 0.59 | +1.3e+1 | 0 | operate | 2.34% | Pullback long en tendencia alcista (pendiente 12.58), range_pos 0.52 en zona óptima, GBM 0 |
| 2026-03-31T11:00 | 0.49 | 0.51 | +1.2e+1 | 0 | operate | 2.94% | Pendiente positiva (12.27), range_pos 0.49 en zona de retroceso, GBM 0.51 > 0.5, confluenc |
| 2026-04-05T17:00 | 0.64 | 0.59 | +5.1e+0 | 0 | wait | 3.16% | Señal de pullback en tendencia alcista y zona correcta, pero el precio está muy cerca del  |
| 2026-04-07T03:00 | 0.58 | 0.57 | +5.2e+1 | 0 | operate | 3.53% | Pullback long en tendencia alcista (pendiente 52), range_pos 0.58 en zona óptima, GBM 0.57 |
| 2026-04-07T08:00 | 0.62 | 0.50 | +4.8e+1 | 0 | operate | 4.02% | Pendiente fuertemente alcista (47.8), range_pos 0.62 en zona de retroceso, GBM 0.503 super |
| 2026-04-07T15:00 | 0.42 | 0.57 | +3.4e+1 | 0 | operate | 5.95% | Pendiente positiva (33.6), range_pos 0.42 en zona de retroceso, GBM 0.57 > 0.5, confluenci |
| 2026-04-10T08:00 | 0.60 | 0.52 | +9.5e+0 | 1 | operate | 1.42% | Pullback long en tendencia alcista (pendiente 9.47), range_pos 0.60 en zona dorada, GBM 0. |
| 2026-04-16T08:00 | 0.54 | 0.51 | +5.7e+0 | 0 | wait | 1.42% | Señal de pullback en zona correcta y tendencia alcista, pero el recorrido hasta el techo ( |
| 2026-04-18T12:00 | 0.58 | 0.51 | +5.5e+1 | 0 | operate | -0.89% | Pendiente positiva fuerte (55.1), range_pos 0.58 en zona de retroceso, GBM 0.51 > 0.5, con |
| 2026-04-18T21:00 | 0.50 | 0.53 | +4.0e+1 | 1 | operate | -1.91% | Pendiente fuertemente alcista (40.3), range_pos en zona óptima (0.50), GBM supera umbral ( |
| 2026-04-19T02:00 | 0.36 | 0.53 | +2.3e+1 | 0 | operate | -1.50% | Pullback long en zona óptima (range_pos 0.36) con tendencia alcista fuerte (pendiente 23), |
| 2026-04-21T19:00 | 0.41 | 0.53 | +2.1e+1 | 0 | operate | 4.92% | Señal pullback long en zona de retroceso (0.41) con tendencia alcista fuerte (pendiente 21 |
| 2026-04-24T03:00 | 0.63 | 0.57 | +3.0e+1 | 0 | wait | -0.13% | Aunque tendencia alcista y rango correcto, las últimas dos velas rojas grandes indican mom |
| 2026-04-24T10:00 | 0.55 | 0.56 | +8.6e-1 | 0 | operate | -0.00% | Señal pullback long en tendencia alcista (pendiente 0.86), range_pos 0.55 en zona óptima,  |

</details>
