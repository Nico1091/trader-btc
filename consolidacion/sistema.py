"""Sistema consolidado en vivo (27/10/2026): un solo motor con las reglas exactas del simulador (consolidado.py).

Solo biblioteca estándar: corre igual en el PC, en esta nube y en la rutina. Lee velas de una «fuente»:
  - Coinbase BTC-USD (en vivo; la API de Binance da 451 desde la nube),
  - o el archivo de velas de 1 minuto de Binance (.npy), para comprobar el motor contra el simulador.
El programa NO decide: calcula contexto, niveles, confirmaciones y señales, y cierra con velas reales. Decide Claude.

Uso:
  python3 -I sistema.py estado              -> señales de hoy hasta ahora (para decidir)
  python3 -I sistema.py cerrar 2026-10-27   -> resultado del día completo, por libro y contra el azar

LIBROS (horas UTC):
  PRINCIPAL (papel en futuros, en %; los largos marcados «pesos» también van a la cuenta de 40.000 en contado)
    P11      lunes 00:00, solo largo con contexto alcista; stop 3 %; salida 23:59.               [pesos]
    P05b     primer cierre de 15 m fuera de apertura ± 0,5·ATR14 (hasta 23:45); vale si va en el lado del contexto
             y la señal llega hasta las 21:00. Límite en la banda 60 min; stop: cierre de 15 m de vuelta a la
             apertura; salida 23:59.
    P05b+pat el largo de P05b con un patrón alcista del curso en las 3 últimas velas de 1 h.        [pesos]
    P05c     como P05b con 1,0·ATR14, solo largo, contexto alcista, y 1 h, 4 h y 1 día sobre su EMA 20. [pesos]
  PRUEBA (papel, en %)
    N9       rango de Asia (00:00-06:59) roto entre las 07:00 y las 13:00 en el lado del contexto; límite 60 min;
             stop: cierre de 15 m de vuelta al punto medio del rango; salida 23:59.
    N8       miércoles 00:00, solo largo con contexto alcista; stop 3 %; salida 23:59.
  AZAR      testigo diario: lado y minuto (00:00-20:59) sorteados con la fecha como semilla; stop 3 %; salida 23:59.
Contexto = cierre diario de ayer frente a la media de sus 50 últimos cierres (SMA 50)."""
import datetime as dt
import json
import os
import random
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patrones_std  # noqa: E402

UTC = dt.timezone.utc
COM = {"creador": 0.02, "tomador": 0.05}  # futuros USDⓈ-M, usuario normal


# ---------------------------------------------------------------- fuentes de velas
class Coinbase:
    API = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

    def velas(self, gran, ini, fin):
        """Velas [t, low, high, open, close, vol] con ini <= t < fin, ordenadas. ini y fin en segundos UTC."""
        out = {}
        paso = gran * 300
        t = ini
        while t < fin:
            t1 = min(t + paso, fin)
            u = (f"{self.API}?granularity={gran}&start={dt.datetime.fromtimestamp(t, UTC):%Y-%m-%dT%H:%M:%SZ}"
                 f"&end={dt.datetime.fromtimestamp(t1 - 1, UTC):%Y-%m-%dT%H:%M:%SZ}")
            for intento in range(4):
                try:
                    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "sistema"}), timeout=30)
                    for x in json.loads(r.read()):
                        if ini <= x[0] < fin:  # la hora como entero: con float, el motor fallaba (encontrado en las pruebas)
                            out[int(x[0])] = [int(x[0])] + [float(v) for v in x[1:]]
                    break
                except Exception:
                    time.sleep(1 + intento)
            t = t1
        return [out[k] for k in sorted(out)]


class Npy:
    """Velas de 1 minuto de Binance (archivo .npy de descargar_um.py), agregadas a la granularidad pedida."""

    def __init__(self, ruta):
        import numpy as np
        self.np = np
        a = np.load(ruta)
        self.t = (a[:, 0] // 1000).astype("int64")
        self.o, self.h, self.l, self.c, self.v = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]

    def velas(self, gran, ini, fin):
        np = self.np
        i0, i1 = np.searchsorted(self.t, ini), np.searchsorted(self.t, fin)
        if i1 <= i0:
            return []
        t = self.t[i0:i1]
        g = t - t % gran
        cortes = np.flatnonzero(np.diff(g)) + 1
        ini_g = np.concatenate([[0], cortes])
        fin_g = np.concatenate([cortes, [len(t)]])
        out = []
        for a, b in zip(ini_g, fin_g):
            out.append([int(g[a]), float(self.l[i0 + a:i0 + b].min()), float(self.h[i0 + a:i0 + b].max()),
                        float(self.o[i0 + a]), float(self.c[i0 + b - 1]), float(self.v[i0 + a:i0 + b].sum())])
        return out


# ---------------------------------------------------------------- lectura comprobada
class LecturaInsuficiente(Exception):
    pass


def comprobar(v, gran, minimo, que, log):
    huecos = sum(1 for a, b in zip(v, v[1:]) if b[0] - a[0] != gran)
    log.append(f"lectura {que}: {len(v)} velas, {huecos} huecos (mínimo {minimo})")
    if len(v) < minimo or huecos:
        raise LecturaInsuficiente(f"{que}: {len(v)} velas y {huecos} huecos; hacen falta {minimo} seguidas")
    return v


def ema(valores, n=20):
    a, e, out = 2 / (n + 1), None, []
    for x in valores:
        e = x if e is None else e + a * (x - e)
        out.append(e)
    return out


# ---------------------------------------------------------------- un día
class Dia:
    def __init__(self, fuente, dia, ahora=None):
        """dia: datetime.date. ahora: segundos UTC hasta donde se ve (por defecto, el fin del día o el momento actual)."""
        self.d0 = int(dt.datetime.combine(dia, dt.time(), UTC).timestamp())
        fin_dia = self.d0 + 86400
        self.ahora = min(ahora or int(time.time()), fin_dia)
        self.log = []
        D = 86400
        d = fuente.velas(D, self.d0 - 130 * D, self.d0)
        self.dias = comprobar(d, D, 120, "diarias (SMA 50, ATR14, EMA 20 diaria, semana)", self.log)
        h1 = fuente.velas(3600, self.d0 - 40 * D, self.ahora)
        self.h1 = comprobar([x for x in h1 if x[0] + 3600 <= self.ahora], 3600, 600, "de 1 h cerradas (EMA 20 de 1 h y 4 h, patrones)", self.log)
        m = fuente.velas(60, self.d0, self.ahora)
        self.m1 = [x for x in m if x[0] + 60 <= self.ahora]
        completo = self.ahora >= fin_dia
        comprobar(self.m1, 60, 1440 if completo else max(1, (self.ahora - self.d0) // 60 - 2), "de 1 min del día", self.log)
        if self.m1[0][0] != self.d0:
            raise LecturaInsuficiente("falta la vela de 1 min de las 00:00 UTC")
        self.completo = completo
        # contexto, ATR14, apertura
        c = [x[4] for x in self.dias]
        self.cierre_ayer = c[-1]
        self.sma50 = sum(c[-50:]) / 50
        self.ctx = 1 if self.cierre_ayer > self.sma50 else -1 if self.cierre_ayer < self.sma50 else 0
        tr = [max(b[2] - b[1], abs(b[2] - a[4]), abs(b[1] - a[4])) for a, b in zip(self.dias[-15:], self.dias[-14:])]
        self.atr = sum(tr) / 14
        self.ap = self.m1[0][3]
        self.ema_d = ema(c)[-1]  # EMA 20 diaria al cierre de ayer (la última vela diaria cerrada en cualquier hora de hoy)
        # 1 h y 4 h
        self.h1_t = [x[0] for x in self.h1]
        cs = [x[4] for x in self.h1]
        self.h1_ema = ema(cs)
        self.alc3, self.baj3 = patrones_std.a_favor_3([x[3] for x in self.h1], [x[2] for x in self.h1], [x[1] for x in self.h1], cs)
        g4 = {}
        for x in self.h1:
            g4.setdefault(x[0] - x[0] % 14400, []).append(x)
        self.h4_t = sorted(k for k, v in g4.items() if len(v) == 4)
        self.h4_c = [g4[k][-1][4] for k in self.h4_t]
        self.h4_ema = ema(self.h4_c)
        # cierres de 15 m del día (instante de cierre, precio)
        self.c15 = [(self.m1[i][0] + 60, self.m1[i][4]) for i in range(len(self.m1)) if (self.m1[i][0] - self.d0) % 900 == 840]

    # --- confirmaciones de los otros tiempos, con velas ya cerradas en el instante t
    def _ultimo(self, tiempos, t, dur):
        j = -1
        for k, x in enumerate(tiempos):
            if x + dur <= t:
                j = k
            else:
                break
        return j

    def e1h(self, t, lado):
        j = self._ultimo(self.h1_t, t, 3600)
        return j >= 0 and lado * (self.h1[j][4] - self.h1_ema[j]) > 0

    def e4h(self, t, lado):
        j = self._ultimo(self.h4_t, t, 14400)
        return j >= 0 and lado * (self.h4_c[j] - self.h4_ema[j]) > 0

    def e1d(self, t, lado):
        return lado * (self.cierre_ayer - self.ema_d) > 0

    def patron1h(self, t, lado):
        j = self._ultimo(self.h1_t, t, 3600)
        return j >= 0 and (self.alc3[j] if lado > 0 else self.baj3[j])

    # --- piezas comunes
    def _idx(self, t):
        return (t - self.d0) // 60  # índice del minuto que empieza en t

    def _llenado(self, t, nivel, lado, W=60):
        for i in range(self._idx(t), min(self._idx(t) + W, len(self.m1))):
            if (lado > 0 and self.m1[i][1] < nivel) or (lado < 0 and self.m1[i][2] > nivel):
                return i
        return None

    def _salida_por_cierre15(self, i_ll, ref, lado):
        """Primer cierre de 15 m desde la vela que contiene el llenado que vuelve a ref (largo: <=; corto: >=)."""
        ini_barra = self.m1[i_ll][0] - (self.m1[i_ll][0] - self.d0) % 900
        for tc, x in self.c15:
            if tc - 900 >= ini_barra and tc <= self.d0 + 23 * 3600 + 45 * 60 and lado * (x - ref) <= 0:
                return tc - 60, x, "stop"
        if self.completo:
            return self.m1[-1][0], self.m1[-1][4], "tiempo"
        return self.m1[-1][0], self.m1[-1][4], "abierta"

    def _a_mercado(self, i_e, lado, stop_pct=3.0):
        pe = self.m1[i_e][3]
        st = pe * (1 - lado * stop_pct / 100)
        for i in range(i_e, len(self.m1)):
            if (lado > 0 and self.m1[i][1] <= st) or (lado < 0 and self.m1[i][2] >= st):
                return pe, self.m1[i][0], st, "stop"
        return pe, self.m1[-1][0], self.m1[-1][4], "tiempo" if self.completo else "abierta"

    def _op(self, libro, nombre, lado, t_senal, i_e, pe, t_s, px, motivo, entrada, pesos=False, nota=""):
        bruto = lado * (px / pe - 1) * 100
        neto = bruto - COM[entrada] - COM["tomador"]
        return dict(libro=libro, estrategia=nombre, lado=lado, senal=t_senal, entrada=self.m1[i_e][0], pe=pe,
                    salida=t_s, px=px, motivo=motivo, bruto=bruto, neto=neto, pesos=pesos, nota=nota)

    # --- estrategias
    def p11(self, nombre="P11", libro="PRINCIPAL", dia_sem=0, pesos=True):
        if dt.datetime.fromtimestamp(self.d0, UTC).weekday() != dia_sem:
            return [], f"{nombre}: no es su día"
        if self.ctx <= 0:
            return [], f"{nombre}: NO opera (contexto bajista)"
        pe, t_s, px, mot = self._a_mercado(0, 1)
        return [self._op(libro, nombre, 1, self.d0, 0, pe, t_s, px, mot, "tomador", pesos)], f"{nombre}: compra a las 00:00"

    def _primer_rompimiento(self, k):
        up, dn = self.ap + k * self.atr, self.ap - k * self.atr
        for tc, x in self.c15:
            if tc > self.d0 + 23 * 3600 + 45 * 60:
                break
            if x > up:
                return tc, 1, up
            if x < dn:
                return tc, -1, dn
        return None, 0, None

    def p05(self):
        ops, notas = [], []
        # P05b por régimen y su variante de pesos
        t, lado, nivel = self._primer_rompimiento(0.5)
        bandas = f"{self.ap - 0.5 * self.atr:,.0f} / {self.ap + 0.5 * self.atr:,.0f}"
        if t is None:
            notas.append(f"P05b (banda {bandas}): sin rompimiento" + ("" if self.completo else " todavía"))
        elif lado != self.ctx:
            notas.append(f"P05b: el primer rompimiento ({'arriba' if lado > 0 else 'abajo'}, {self._h(t)}) va contra el contexto: no opera hoy")
        elif t > self.d0 + 21 * 3600:
            notas.append(f"P05b: señal a las {self._h(t)}, después de las 21:00: no opera")
        else:
            i = self._llenado(t, nivel, lado)
            conf = f"1h {'sí' if self.e1h(t, lado) else 'no'} · 4h {'sí' if self.e4h(t, lado) else 'no'} · 1d {'sí' if self.e1d(t, lado) else 'no'} · patrón 1h {'sí' if self.patron1h(t, lado) else 'no'}"
            if i is None:
                espera = "esperando llenado hasta las " + self._h(t + 3600) if self.ahora < t + 3600 else "límite sin llenar"
                notas.append(f"P05b: señal {'larga' if lado > 0 else 'corta'} a las {self._h(t)} ({conf}); {espera} en {nivel:,.0f}")
            else:
                t_s, px, mot = self._salida_por_cierre15(i, self.ap, lado)
                ops.append(self._op("PRINCIPAL", "P05b", lado, t, i, nivel, t_s, px, mot, "creador", nota=conf))
                if lado > 0 and self.patron1h(t, 1):
                    ops.append(self._op("PRINCIPAL", "P05b+pat", 1, t, i, nivel, t_s, px, mot, "creador", pesos=True, nota=conf))
                notas.append(f"P05b: SEÑAL {'larga' if lado > 0 else 'corta'} a las {self._h(t)} ({conf})")
        # P05c largo con los 3 tiempos mayores a favor
        t, lado, nivel = self._primer_rompimiento(1.0)
        if self.ctx <= 0:
            notas.append("P05c: no opera (contexto bajista)")
        elif t is None:
            notas.append(f"P05c (> {self.ap + self.atr:,.0f}): sin rompimiento" + ("" if self.completo else " todavía"))
        elif lado < 0:
            notas.append(f"P05c: el primer rompimiento fue hacia abajo ({self._h(t)}): no opera hoy")
        elif t > self.d0 + 21 * 3600:
            notas.append(f"P05c: señal después de las 21:00: no opera")
        elif not (self.e1h(t, 1) and self.e4h(t, 1) and self.e1d(t, 1)):
            notas.append(f"P05c: señal a las {self._h(t)} sin los 3 tiempos mayores a favor: no opera")
        else:
            i = self._llenado(t, nivel, 1)
            if i is None:
                notas.append(f"P05c: señal a las {self._h(t)}; límite sin llenar")
            else:
                t_s, px, mot = self._salida_por_cierre15(i, self.ap, 1)
                ops.append(self._op("PRINCIPAL", "P05c", 1, t, i, nivel, t_s, px, mot, "creador", pesos=True))
                notas.append(f"P05c: SEÑAL larga a las {self._h(t)}")
        return ops, notas

    def n9(self):
        if self.ctx == 0:
            return [], "N9: sin contexto"
        if self.ahora < self.d0 + 7 * 3600:
            return [], "N9: el rango de Asia (00:00-07:00) aún no está completo"
        asia = [x for x in self.m1 if x[0] < self.d0 + 7 * 3600]
        if len(asia) < 400:
            return [], "N9: rango de Asia incompleto"
        ah, al = max(x[2] for x in asia), min(x[1] for x in asia)
        nv, medio = (ah if self.ctx > 0 else al), (ah + al) / 2
        for tc, x in self.c15:
            if self.d0 + 7 * 3600 < tc <= self.d0 + 13 * 3600 and self.ctx * (x - nv) > 0:
                i = self._llenado(tc, nv, self.ctx)
                if i is None:
                    return [], f"N9: señal a las {self._h(tc)}; límite sin llenar"
                t_s, px, mot = self._salida_por_cierre15(i, medio, self.ctx)
                return [self._op("PRUEBA", "N9", self.ctx, tc, i, nv, t_s, px, mot, "creador")], f"N9: SEÑAL a las {self._h(tc)}"
        return [], f"N9 (Asia {al:,.0f}-{ah:,.0f}; {'largo >' if self.ctx > 0 else 'corto <'} {nv:,.0f}, 07:00-13:00): sin señal"

    def azar(self):
        r = random.Random(int(dt.datetime.fromtimestamp(self.d0, UTC).strftime("%Y%m%d")))
        minuto, lado = r.randrange(0, 1260), r.choice([-1, 1])
        if minuto >= len(self.m1):
            return [], f"AZAR: entra a las {minuto // 60:02d}:{minuto % 60:02d} ({'largo' if lado > 0 else 'corto'})"
        pe, t_s, px, mot = self._a_mercado(minuto, lado)
        return ([self._op("AZAR", "AZAR", lado, self.m1[minuto][0], minuto, pe, t_s, px, mot, "tomador")],
                f"AZAR: {'largo' if lado > 0 else 'corto'} a las {minuto // 60:02d}:{minuto % 60:02d}")

    def todo(self):
        ops, notas = [], []
        for f in (self.p11, self.p05, self.n9,
                  lambda: self.p11("N8", "PRUEBA", 2, False), self.azar):
            o, n = f()
            ops += o
            notas += n if isinstance(n, list) else [n]
        return ops, notas

    def _h(self, t):
        return dt.datetime.fromtimestamp(t, UTC).strftime("%H:%M")


def informe(fuente, dia, ahora=None):
    D = Dia(fuente, dia, ahora)
    ops, notas = D.todo()
    L = [f"SISTEMA CONSOLIDADO · {dia} · contexto {'ALCISTA' if D.ctx > 0 else 'BAJISTA' if D.ctx < 0 else 'NEUTRO'} "
         f"(cierre de ayer {D.cierre_ayer:,.2f} vs SMA 50 {D.sma50:,.2f}, {(D.cierre_ayer / D.sma50 - 1) * 100:+.2f} %) · "
         f"apertura {D.ap:,.2f} · ATR14 {D.atr:,.0f}"]
    L += ["  " + x for x in D.log]
    L += ["  " + n for n in notas]
    for o in ops:
        L.append(f"  [{o['libro']}] {o['estrategia']} {'LARGO' if o['lado'] > 0 else 'CORTO'} {o['pe']:,.2f} -> {o['px']:,.2f} "
                 f"({o['motivo']}) bruto {o['bruto']:+.3f} % neto {o['neto']:+.3f} %{' · va a la cuenta en pesos' if o['pesos'] else ''}")
    return D, ops, "\n".join(L)


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else "estado"
    dia = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.datetime.now(UTC).date()
    try:
        _, _, texto = informe(Coinbase(), dia, None if accion == "estado" else int(time.time()))
        print(texto)
    except LecturaInsuficiente as e:
        print("NO SE OPERA: lectura insuficiente ->", e)
