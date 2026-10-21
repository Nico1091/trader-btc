"""Prueba de paridad: el agente en vivo y el banco de pruebas deben dar los MISMOS ciclos.

Uso:  python -u -I pruebas/paridad_motor.py [AAAA-MM-DD] [días]     (por omisión 2026-10-12, 1 día)

Se toma un tramo de velas de 1 s ya descargadas y se pasa por los dos caminos:
- banco: rapido.Serie + rapido.Contexto con los archivos, probabilidades por segundo y
  rapido.simular_libro (lo mismo que hace banco_rapido.py);
- agente: el código real de agente.py (SerieViva, contexto rehecho cada minuto como en vivo,
  ModeloVivo, LibroVivo.segundo), alimentado segundo a segundo con un «mercado» que sirve
  los mismos datos de los archivos y nunca deja ver el futuro.
Si los ciclos no coinciden (hora, lado, precios, motivo), el agente no opera lo que se probó.
"""
import array
import datetime as dt
import math
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import agente as ag  # noqa: E402
import banco_rapido as br  # noqa: E402
import datos  # noqa: E402
import rapido as rp  # noqa: E402

SEG, MIN, HORA, DIA = 1000, 60_000, 3_600_000, 86_400_000


class MercadoDeArchivos:
    """Imita vivo.Mercado con los archivos, sin dejar ver nada posterior a `ahora`."""

    def __init__(self, v1m, met, fin):
        self.v1m, self.met, self.fin = v1m, met, fin
        self.v1h = datos.agregar(v1m, 60)
        self.ahora = 0
        self.salud = {"ws_contado": "archivo", "ws_futuros": "archivo", "reconexiones": 0, "ultimo_mensaje_ms": 0}
        self.marca, self.libro = {}, {}

    def _filas(self, v, desde, hasta):
        import bisect
        a, b = bisect.bisect_left(v.t, desde), bisect.bisect_left(v.t, hasta)
        return [(v.t[k], v.o[k], v.h[k], v.l[k], v.c[k], v.v[k], v.tb[k], v.n[k]) for k in range(a, b)]

    def klines_rango(self, simbolo, intervalo, desde, hasta, ancho):
        assert simbolo == "BTCUSDT" and intervalo == "1m"
        return [f for f in self._filas(self.v1m, desde, hasta) if f[0] + MIN <= self.ahora]

    def klines(self, simbolo, intervalo, desde, limite):
        assert intervalo == "1h"
        return [f for f in self._filas(self.v1h, desde, desde + limite * HORA) if f[0] + HORA <= self.ahora][:limite]

    def metricas_oi(self, limite):
        import bisect
        k = bisect.bisect_right(self.met.t, self.ahora)
        return [(self.met.t[j], self.met.oi[j]) for j in range(max(0, k - limite), k)]

    def financiacion(self, limite):
        import bisect
        k = bisect.bisect_right(self.fin[0], self.ahora)
        return [(self.fin[0][j], self.fin[1][j]) for j in range(max(0, k - limite), k)]

    def liquidado(self, desde):
        return (0.0, 0.0)


class SinContexto:
    def bloqueo(self, t):
        return None

    def resumen(self):
        return {}

    def proximo(self, t):
        return None


class DiarioNulo:
    def __getattr__(self, nombre):
        return lambda *a, **k: None


def ciclos_clave(ciclos):
    return [(c["t_entrada"], c["t_salida"], c["lado"], round(c["entrada"], 6), round(c["salida"], 6), c["motivo"],
             round(c["cantidad"], 8)) for c in ciclos if not c.get("relleno")]


def main():
    siempre = "--siempre" in sys.argv                     # entra en cada segundo libre: cientos de ciclos
    args = [x for x in sys.argv[1:] if x != "--siempre"]
    fecha = args[0] if args else "2026-10-12"
    dias = float(args[1]) if len(args) > 1 else 1.0
    if len(args) > 2:
        ag.RUTA_MODELOS = args[2]
    W0 = int(dt.datetime.fromisoformat(fecha).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    W1 = W0 + int(dias * DIA)
    inicio = time.time()
    modelo = ag.ModeloVivo(ag.RUTA_MODELOS)
    if siempre:
        for e in modelo.instrumentos.values():
            e["margen"] = -1.0
    v_u = datos.cargar_velas("contado-1s-BTCUSDT", "1s")
    v_f = datos.cargar_velas("contado-1s-BTCFDUSD", "1s")
    calent = (rp.VENTANA_MIN + 120) * SEG
    u = datos.recortar(v_u, W0 - calent, W1)
    f = datos.recortar(v_f, W0 - calent, W1)
    v1m = datos.cargar_1m("contado-1m")
    met = datos.cargar_metricas()
    fin = datos.cargar_financiacion(completar=True)

    # ---------------- camino del banco
    s, sf = rp.Serie(u), rp.Serie(f, rasgos=False)
    ctx = rp.Contexto(datos.recortar(v1m, W0 - 30 * DIA, W1 + DIA), met, fin)
    i0 = s.indice(W0)
    usados = {}
    for clave, e in modelo.instrumentos.items():
        usados.setdefault(tuple(e["config"]), [])
    arr = {cfg: (array.array("d"), array.array("d"), array.array("d")) for cfg in usados}
    for i in range(i0, s.largo - 1):
        x = rp.rasgos_segundo(s, i, ctx.en(s.t[i] + SEG))
        for cfg, (B, H, D) in arr.items():
            mh, md = modelo.modelos[cfg]                  # mismas cuentas que banco_rapido.py
            b = rp.barrera_de(x[rp.I_VOL3600], cfg[0], cfg[1], cfg[2])
            z = br.z_de(x + [math.log(b * 100)], mh.media, mh.desvio)
            B.append(b)
            H.append(br.p_de(mh, z))
            D.append(br.p_de(md, z))
    banco = {}
    gestion = rp.Gestion(capital=ag.CAPITAL, tanda=rp.tanda_por_capital(ag.CAPITAL))
    for clave, inst in rp.INSTRUMENTOS.items():
        e = modelo.instrumentos[clave]
        cfg = tuple(e["config"])
        B, H, D = arr[cfg]
        lib, _ = rp.simular_libro(s, sf if clave == "fdusd" else s, i0, s.largo - 1,
                                  rp.decisor_ev(B, H, D, i0, inst, e["margen"]), inst, gestion, cfg[0])
        banco[clave] = ciclos_clave(lib.ciclos)
    print(f"banco: {', '.join(f'{k} {len(v)} ciclos' for k, v in banco.items())} ({time.time() - inicio:.0f} s)", flush=True)

    # ---------------- camino del agente (código real)
    a = ag.Agente(reproducir=True)
    if siempre:
        for lv in a.libros.values():
            lv.margen = -1.0
    a.diario = DiarioNulo()
    a.externo = SinContexto()
    a.mercado = MercadoDeArchivos(datos.recortar(v1m, W0 - 50 * DIA, W1 + DIA), met, fin)
    a.mercado.ahora = W0
    a._cargar_contexto(W0)
    for k in range(i0):                                   # calentamiento sin decisiones, como arrancar()
        a.serie.agregar(u.t[k], u.o[k], u.h[k], u.l[k], u.c[k], u.v[k], u.tb[k], u.n[k])
        a.serie_fd.agregar(f.t[k], f.o[k], f.h[k], f.l[k], f.c[k], f.v[k], f.tb[k], f.n[k])
    a.ultimo_t = u.t[i0 - 1]
    for k in range(i0, len(u.t) - 1):
        a.mercado.ahora = u.t[k] + SEG
        a.procesar(u.t[k], (u.t[k], u.o[k], u.h[k], u.l[k], u.c[k], u.v[k], u.tb[k], u.n[k]),
                   (f.t[k], f.o[k], f.h[k], f.l[k], f.c[k], f.v[k], f.tb[k], f.n[k]), en_vivo=True)
    # Fin de los datos: el banco cierra por tiempo en la última vela lo que siga abierto (recorrer);
    # en vivo los datos no se acaban, así que aquí se hace lo mismo para comparar todo.
    ult = len(u.t) - 2
    for clave, lv in a.libros.items():
        if lv.estado == "posicion":
            serie_ej = f if clave == "fdusd" else u
            c = serie_ej.c[ult]
            lv._cerrar(serie_ej.t[ult], "TIEMPO", c * (1 - lv.pos.desliz) if lv.pos.largo else c * (1 + lv.pos.desliz),
                       a.diario, True)
    vivo_ = {k: ciclos_clave(lv.libro.ciclos) for k, lv in a.libros.items()}
    print(f"agente: {', '.join(f'{k} {len(v)} ciclos' for k, v in vivo_.items())} ({time.time() - inicio:.0f} s)", flush=True)
    # las velas de 1 min que el agente armó con las de 1 s, contra las oficiales de Binance
    oficiales = {v1m.t[k]: k for k in range(len(v1m.t)) if W0 <= v1m.t[k] < W1}
    distintas = revisadas = 0
    for k in range(len(a.v1m.t)):
        j = oficiales.get(a.v1m.t[k])
        if j is None:
            continue
        revisadas += 1
        if any(abs(getattr(a.v1m, c)[k] - getattr(v1m, c)[j]) > 1e-6 for c in ("o", "h", "l", "c", "v")):
            distintas += 1
            if distintas <= 3:
                print("   vela de 1 min distinta:", a.v1m.t[k], [getattr(a.v1m, c)[k] for c in "ohlcv"],
                      [getattr(v1m, c)[j] for c in "ohlcv"])
    print(f"velas de 1 min armadas por el agente: {revisadas} revisadas, {distintas} distintas de las de Binance")

    # ---------------- comparación
    # El último ciclo puede quedar cortado por el fin de los datos (el banco cierra en la última
    # vela; el agente, una antes): de ese solo se compara la entrada.
    corte = u.t[-1] - 2 * SEG

    def partir(lista):
        completos = [c for c in lista if not (c[5] == "TIEMPO" and c[1] >= corte)]
        cortados = [(c[0], c[2], c[3], c[6]) for c in lista if c[5] == "TIEMPO" and c[1] >= corte]
        return completos + cortados

    banco = {k: partir(v) for k, v in banco.items()}
    vivo_ = {k: partir(v) for k, v in vivo_.items()}
    fallos = 0
    for clave in banco:
        b, v = banco[clave], vivo_[clave]
        iguales = sum(1 for x, y in zip(b, v) if x == y)
        estado = "IGUALES" if b == v else "DISTINTOS"
        print(f"{clave}: banco {len(b)} · agente {len(v)} · coinciden {iguales} -> {estado}")
        if b != v:
            fallos += 1
            for x, y in zip(b, v):
                if x != y:
                    print("   primer desacuerdo:\n     banco ", x, "\n     agente", y)
                    break
            for x in b[len(v):]:
                print("   solo en el banco: ", x)
            for y in v[len(b):]:
                print("   solo en el agente:", y)
    print("PARIDAD:", "BIEN" if fallos == 0 else f"MAL ({fallos} libros distintos)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
