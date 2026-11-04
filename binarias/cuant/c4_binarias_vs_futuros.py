"""C4 (03/11/2026): las dos modalidades se evalúan con modelos distintos. Solo estudio: no opera nada.

BINARIAS (Contratos de Evento de Binance): pago fijo p que Binance fija al apostar (se mide con 0,80, 0,85 y 0,90),
vencimiento de 10 min, 30 min, 1 h o 1 día, mínimo de 5 USDT. Acierto de equilibrio = 1/(1+p). Expectativa por peso
= a·p − (1 − a). No existe apalancamiento ni liquidación: lo máximo que se pierde es lo apostado.

FUTUROS PERPETUOS USDT-M (solo estudio; Nicolás decidió no usar apalancamiento):
- Comisión: creador 0,02 %, tomador 0,05 % del nocional por lado (niveles base; con BNB, 10 % menos).
- Financiación: cada 8 h, nocional × tasa (positiva: los largos pagan a los cortos).
- Liquidación aislada aproximada: largo P_liq ≈ P·(1 − 1/L + mm); corto P_liq ≈ P·(1 + 1/L − mm), con margen de
  mantenimiento mm ≈ 0,4 % en el primer escalón de BTCUSDT.
- Con 1x (sin apalancamiento) no hay liquidación práctica en largo (haría falta que el precio llegue casi a 0).
- SL/TP: expectativa = a·TP − (1 − a)·SL − costos; equilibrio a* = (SL + costos)/(TP + SL).
Uso: python -I c4_binarias_vs_futuros.py
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validacion as V  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "resultados")
TASA = 3180.0  # COP por USDT (mediana P2P usada en el banco)


def es(x, d=2):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def liquidacion(P, L, lado, mm=0.004):
    if L <= 1 and lado == "largo":
        return P * mm  # prácticamente nunca
    return P * (1 - 1 / L + mm) if lado == "largo" else P * (1 + 1 / L - mm)


def futuros_esperanza(a, tp, sl, comision_lado=0.0005, financiacion_8h=0.0001, horas=0.25):
    costos = 2 * comision_lado + financiacion_8h * horas / 8
    return a * tp - (1 - a) * sl - costos, (sl + costos) / (tp + sl)


def main():
    L = ["C4 · binarias frente a futuros: modelos de evaluación distintos (solo estudio)", ""]
    L.append("BINARIAS: acierto de equilibrio, expectativa y Kelly")
    for p in (0.80, 0.85, 0.90):
        L.append(f"  pago {es(p)}: equilibrio {es(100 * V.equilibrio(p), 1)} %")
        for a in (0.54, 0.56, 0.58, 0.60, 0.857):
            L.append(f"     con acierto {es(100 * a, 1)} %: expectativa {es(100 * V.expectativa(a, p), 2)} % por apuesta · Kelly {es(100 * V.kelly(a, p), 1)} % · "
                     f"medio Kelly {es(50 * V.kelly(a, p), 1)} %")
    L.append("  Con 100.000 COP el mínimo de 5 USDT (≈ 15.900 COP) es el 15,9 % del saldo: mayor que medio Kelly para cualquier acierto realista;")
    L.append("  por eso el centinela apuesta siempre el mínimo hasta que la cuenta pase de ~453.000 COP.")
    L.append("")
    L.append("FUTUROS (solo estudio): liquidación según apalancamiento, BTC a 77.000")
    for lev in (1, 2, 3, 5, 10, 20, 50, 100):
        lq_l = liquidacion(77000, lev, "largo")
        lq_c = liquidacion(77000, lev, "corto")
        L.append(f"  {lev:>3}x: largo se liquida en {es(lq_l, 0)} ({es(100 * (lq_l / 77000 - 1), 1)} %) · corto en {es(lq_c, 0)} ({es(100 * (lq_c / 77000 - 1), 1)} %)")
    L.append("")
    L.append("FUTUROS: expectativa por operación de 15 min con SL/TP y costos (tomador 0,05 % por lado, financiación 0,01 % cada 8 h)")
    for tp, sl in ((0.003, 0.003), (0.004, 0.002), (0.006, 0.003), (0.002, 0.004)):
        for a in (0.50, 0.55, 0.60):
            e, eq = futuros_esperanza(a, tp, sl)
            L.append(f"  TP {es(100 * tp, 1)} % / SL {es(100 * sl, 1)} %, acierto {es(100 * a, 0)} %: {es(100 * e, 3)} % del nocional · equilibrio {es(100 * eq, 1)} %")
    L.append("")
    L.append("Diferencia de fondo: en binarias lo que importa es el acierto frente a 1/(1+pago); en futuros, el tamaño de lo ganado")
    L.append("frente a lo perdido y los costos por operación (0,10 % ida y vuelta como tomador), que con movimientos de 10 min de")
    L.append("0,05-0,15 % se comen la ventaja (medido en trader-btc el 20/10). El apalancamiento no crea ventaja: multiplica la")
    L.append("ganancia y la pérdida, acerca la liquidación y vuelve fatales las rachas. Decisión de Nicolás: no usarlo.")
    os.makedirs(SALIDA, exist_ok=True)
    texto = "\n".join(L)
    open(os.path.join(SALIDA, "c4_binarias_vs_futuros.txt"), "w", encoding="utf-8").write(texto + "\n")
    print(texto)


if __name__ == "__main__":
    main()
