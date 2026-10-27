"""Cierre con velas de 1 minuto de Coinbase BTC-USD de las órdenes del domingo 25/10/2026 que dejó la rutina
(REGISTRO v5 del correo de las 14:18 UTC). Reglas copiadas del REGISTRO:
- CL-005 / ORD-004 (P05b largo): cierre de 15 m > 81.863,57 -> límite de compra en 81.863,57 válido 60 min;
  stop: cierre de 15 m < 80.769,67; salida 23:59 UTC. Señal hasta las 23:45. Comisión 0,02 + 0,05 %.
- CL-006 / ORD-004 (P05b corto): cierre de 15 m < 79.675,77 -> límite de venta; stop: cierre de 15 m > 80.769,67.
- ORD-005 (P05c): niveles 82.957,47 / 78.581,87, mismo stop y salida.
- Una señal por día: la primera que aparezca.
- AZ-002 ... AZ-007: testigos al azar; stop con un cierre de 15 m al nivel; salida 23:59 UTC. Comisión 0,05 %/lado.
Antes de cerrar exige las 1.440 velas de 1 minuto del día sin huecos (si no, no cierra)."""
import datetime as dt
import sys
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from t6_ordenes import velas, lectura, LecturaInsuficiente

DIA = dt.datetime(2026, 10, 25, tzinfo=dt.timezone.utc)
AP = 80769.67


def main(parcial=False):
    fin = min(DIA + dt.timedelta(days=1), dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0))
    m = velas(60, DIA, fin)
    m = m[m[:, 0] < fin.timestamp()]
    try:
        lectura(m, 60, 60 if parcial else 1440, "de 1 min del 25/10")
    except LecturaInsuficiente as e:
        print("NO SE CIERRA:", e); return
    t, lo, hi, op, cl = m[:, 0], m[:, 1], m[:, 2], m[:, 3], m[:, 4]
    n15 = len(cl) // 15
    c15, t15 = cl[14:n15 * 15:15], t[14:n15 * 15:15] + 60  # cierre e instante de cada vela de 15 m completa
    print(f"Velas de 15 m completas: {n15}. Último precio {cl[-1]:,.2f} ({dt.datetime.fromtimestamp(t[-1], dt.timezone.utc):%H:%M} UTC)")
    hora = lambda x: dt.datetime.fromtimestamp(x, dt.timezone.utc).strftime("%H:%M")

    def p05(nombre, up, dn):
        lim = int((DIA + dt.timedelta(hours=23, minutes=45)).timestamp())
        j = next((i for i, x in enumerate(c15) if t15[i] <= lim and (x > up or x < dn)), None)
        if j is None:
            print(f"{nombre}: sin activar (banda {dn:,.2f} - {up:,.2f}; cierres de 15 m de {c15.min():,.2f} a {c15.max():,.2f})")
            return
        lado, nivel = (1, up) if c15[j] > up else (-1, dn)
        i0 = int(np.searchsorted(t, t15[j]))
        f = next((i for i in range(i0, min(i0 + 60, len(t))) if (lado > 0 and lo[i] < nivel) or (lado < 0 and hi[i] > nivel)), None)
        if f is None:
            print(f"{nombre}: señal {'larga' if lado > 0 else 'corta'} a las {hora(t15[j])}, límite sin llenar en 60 min"); return
        px, mot = cl[-1], "tiempo" if not parcial else "abierta"
        for i in range(len(c15)):
            if t15[i] > t[f] + 60 and ((lado > 0 and c15[i] < AP) or (lado < 0 and c15[i] > AP)):
                px, mot = c15[i], "stop"; break
        b = lado * (px / nivel - 1) * 100
        print(f"{nombre}: {'LARGO' if lado > 0 else 'CORTO'} lleno a las {hora(t[f])} en {nivel:,.2f} -> {px:,.2f} ({mot}) "
              f"bruto {b:+.3f} % neto {b - 0.07:+.3f} %")

    p05("CL-005/CL-006 y ORD-004 (P05b)", 81863.57, 79675.77)
    p05("ORD-005 (P05c)", 82957.47, 78581.87)

    azar = [("AZ-002", -1, "02:30", 80737.63, 81817.63), ("AZ-003", -1, "04:23", 80769.99, 81849.99),
            ("AZ-004", -1, "06:00", 80500.47, 81580.47), ("AZ-005", -1, "08:30", 80287.21, 80287.21 + 1094),
            ("AZ-006", -1, "10:00", 80224.13, 80224.13 + 2188), ("AZ-007", 1, "18:49", None, None)]
    for nombre, lado, hh, pe, st in azar:
        te = (DIA + dt.timedelta(hours=int(hh[:2]), minutes=int(hh[3:]))).timestamp()
        if te > t[-1]:
            print(f"{nombre}: todavía no entra ({hh} UTC)"); continue
        if pe is None:
            pe = op[int(np.searchsorted(t, te))]; st = pe - 1094
        px, mot = cl[-1], "tiempo" if not parcial else "abierta"
        for i in range(len(c15)):
            if t15[i] > te and ((lado < 0 and c15[i] >= st) or (lado > 0 and c15[i] <= st)):
                px, mot = c15[i], "stop"; break
        b = lado * (px / pe - 1) * 100
        print(f"{nombre}: {'LARGO' if lado > 0 else 'CORTO'} {pe:,.2f} -> {px:,.2f} ({mot}) bruto {b:+.3f} % neto {b - 0.10:+.3f} %")


if __name__ == "__main__":
    main(parcial="parcial" in sys.argv)
