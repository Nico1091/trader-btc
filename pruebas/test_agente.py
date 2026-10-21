"""Pruebas del agente en vivo sin red: huecos, velas faltantes, apagones, estado guardado y frenos.

Uso:  python -I -m unittest discover -s pruebas -v   (desde trader-btc)
"""
import datetime as dt
import json
import os
import queue
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agente as ag  # noqa: E402
import contexto as cx  # noqa: E402
import rapido as rp  # noqa: E402

SEG, MIN, HORA = 1000, 60_000, 3_600_000
T0 = 1_792_000_000_000 // MIN * MIN


def fila(t, precio=80_000.0, bajo=None, alto=None, n=3.0):
    return (t, precio, alto if alto is not None else precio, bajo if bajo is not None else precio, precio,
            0.5, 0.25, n)


class MercadoFalso:
    """Sirve velas de 1 s desde diccionarios y anota cada pedido a la «API»."""

    def __init__(self, u, f):
        self.u, self.f = u, f
        self.pedidos = []
        self.salud = {"ws_contado": "falso", "ws_futuros": "falso", "reconexiones": 0, "ultimo_mensaje_ms": 0}
        self.libro, self.marca = {}, {}
        self.cola = queue.Queue()

    def klines_rango(self, simbolo, intervalo, desde, hasta, ancho):
        self.pedidos.append((simbolo, intervalo, desde, hasta))
        origen = self.u if simbolo == "BTCUSDT" else self.f
        return [origen[t] for t in range(desde, hasta, ancho) if t in origen]

    def liquidado(self, desde):
        return (0.0, 0.0)

    def parar(self):
        pass


class DiarioMemoria:
    def __init__(self):
        self.eventos = []

    def evento(self, t, tipo, **d):
        self.eventos.append((t, tipo, d))

    def __getattr__(self, nombre):
        return lambda *a, **k: None


class SinContexto:
    def bloqueo(self, t):
        return None

    def resumen(self):
        return {}

    def proximo(self, t):
        return None

    def parar(self):
        pass


def agente_de_prueba(u, f, desde, hasta):
    """Agente con serie cargada hasta `desde` (exclusivo), sin red ni modelos de contexto."""
    a = ag.Agente(reproducir=True)
    a.mercado = MercadoFalso(u, f)
    a.diario = DiarioMemoria()
    a.externo = SinContexto()
    a.ctx = None                                    # sin contexto: no decide, solo mueve el tiempo y las salidas
    for t in range(desde - 50 * SEG, desde, SEG):
        a.serie.agregar(*u[t])
        a.serie_fd.agregar(*f[t])
    a.ultimo_t = desde - SEG
    return a


class Huecos(unittest.TestCase):
    def setUp(self):
        self.u = {T0 + k * SEG: fila(T0 + k * SEG) for k in range(-100, 400)}
        self.f = {T0 + k * SEG: fila(T0 + k * SEG, 80_100.0) for k in range(-100, 400)}

    def test_faltan_velas_de_btcusdt_se_piden_y_no_abren_ciclos(self):
        u = dict(self.u)
        u[T0 + 3 * SEG] = fila(T0 + 3 * SEG, 80_000.0, bajo=79_000.0)       # en el hueco cae el precio
        a = agente_de_prueba(u, self.f, T0, None)
        a.mercado.u = u
        lv = a.libros["testigo"]
        lv.estado = "posicion"
        lv.pos = rp.Posicion(True, 80_000.0, 80_400.0, 79_600.0, T0 + 600 * SEG, 0.0)
        lv.pos_meta = {"q": 0.0001, "t_in": T0 - 10 * SEG, "creador": False,
                       "p": {"b": 0.005, "esperanza": 0.0, "dec": {"prob_mov": None, "prob_sube": None}}}
        for k in range(6, 12):                          # el flujo trae del segundo 6 en adelante
            t = T0 + k * SEG
            a.pendientes[t] = {"BTCUSDT": u[t], "BTCFDUSD": self.f[t]}
        a._consumir()
        self.assertEqual(a.estadisticas["rellenados"], 6)              # segundos 0 a 5 por la API
        self.assertEqual(a.ultimo_t, T0 + 11 * SEG)
        self.assertEqual(a.mercado.pedidos[0][:2], ("BTCUSDT", "1s"))
        salida = [e for e in a.diario.eventos if e[1] == "salida"]
        self.assertEqual(len(salida), 1)
        self.assertEqual(salida[0][0], T0 + 3 * SEG)                    # el stop se cumple en el segundo del hueco
        self.assertEqual(salida[0][2]["motivo"], "STOP")
        self.assertFalse(lv.libro.ciclos[-1]["en_vivo"])
        self.assertFalse([e for e in a.diario.eventos if e[1] in ("decision", "entrada")])

    def test_falta_la_vela_de_fdusd_se_usa_una_quieta_sin_esperar(self):
        a = agente_de_prueba(self.u, self.f, T0, None)
        for k in range(0, 5):
            t = T0 + k * SEG
            a.pendientes[t] = {"BTCUSDT": self.u[t]}
            if k:
                a.pendientes[t]["BTCFDUSD"] = self.f[t]
        a._consumir()
        self.assertEqual(a.estadisticas["fdusd_quietas"], 1)
        self.assertEqual(a.ultimo_t, T0 + 4 * SEG)
        self.assertEqual(a.serie_fd.v[-5], 0.0)                          # la vela quieta no tiene volumen
        self.assertFalse(a.mercado.pedidos)                             # y no se llamó a la API

    def test_espera_si_el_hueco_es_reciente(self):
        a = agente_de_prueba(self.u, self.f, T0, None)
        a.pendientes[T0 + SEG] = {"BTCUSDT": self.u[T0 + SEG], "BTCFDUSD": self.f[T0 + SEG]}
        a._consumir()
        self.assertEqual(a.ultimo_t, T0 - SEG)                          # falta T0 y solo pasó 1 s: espera
        self.assertFalse(a.mercado.pedidos)

    def test_apagado_mas_de_seis_horas_cierra_y_rearranca(self):
        a = agente_de_prueba(self.u, self.f, T0, None)
        llamadas = []
        a.arrancar = lambda sin_flujos=False: llamadas.append(sin_flujos)
        lv = a.libros["futuros"]
        lv.estado = "posicion"
        lv.pos = rp.Posicion(False, 80_000.0, 79_900.0, 80_100.0, T0 + 600 * SEG, 0.0001)
        lv.pos_meta = {"q": 0.001, "t_in": T0 - 10 * SEG, "creador": True,
                       "p": {"b": 0.00125, "esperanza": 0.0, "dec": {"prob_mov": None, "prob_sube": None}}}
        lejos = T0 + 7 * HORA
        a.pendientes[lejos] = {"BTCUSDT": fila(lejos), "BTCFDUSD": fila(lejos)}
        a._consumir()
        self.assertEqual(llamadas, [True])
        self.assertEqual(lv.libro.ciclos[-1]["motivo"], "HUECO_LARGO")
        self.assertEqual(lv.estado, "libre")


class EstadoGuardado(unittest.TestCase):
    def test_se_recupera_y_cierra_lo_que_quedo_abierto(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "estado.json")
            guardado = {"libros": {"testigo": {
                "efectivo": 8.5, "polvo": 0.000009, "ciclos": 37, "tandas": [], "detenido": "",
                "inicio_tanda": 9.7, "omitidas": {"pausas_por_perdidas": 2}, "sin_llenar": 0, "bloqueos": {"pausa": 4},
                "ultimos": [{"lado": "largo", "ganancia_usdt": -0.01, "t_salida": T0}],
                "posicion": {"largo": True, "entrada": 80_000.0, "tp": 80_080.0, "sl": 79_920.0,
                             "fin": T0 + 300 * SEG, "t_in": T0, "q": 0.0001}}},
                "estadisticas": {"segundos": 1234}}
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(guardado, f)
            original = ag.RUTA_ESTADO
            ag.RUTA_ESTADO = ruta
            try:
                a = ag.Agente()
            finally:
                ag.RUTA_ESTADO = original
            lv = a.libros["testigo"]
            self.assertEqual(len(lv.libro.ciclos), 37)                  # la cuenta de tandas sigue
            self.assertAlmostEqual(lv.libro.efectivo, 8.5)
            self.assertEqual(lv.libro.omitidas["pausas_por_perdidas"], 2)
            self.assertEqual(a.estadisticas["segundos"], 1234)
            self.assertEqual(lv._posicion_guardada["entrada"], 80_000.0)
            # al arrancar, lo abierto se cierra a mercado como tomador
            a.diario = DiarioMemoria()
            lv.estado = "posicion"
            pg = lv._posicion_guardada
            lv.pos = rp.Posicion(pg["largo"], pg["entrada"], pg["tp"], pg["sl"], pg["fin"], lv.inst.desliz)
            lv.pos_meta = {"q": pg["q"], "t_in": pg["t_in"], "creador": False,
                           "p": {"b": 0.0, "esperanza": 0.0, "dec": {"prob_mov": None, "prob_sube": None}}}
            lv.cerrar_ya(T0 + 60 * SEG, 80_010.0, "REINICIO", a.diario)
            self.assertEqual(len(lv.libro.ciclos), 38)
            self.assertEqual(lv.libro.ciclos[-1]["motivo"], "REINICIO")
            self.assertAlmostEqual(lv.libro.ciclos[-1]["salida"], 80_010.0 * (1 - lv.inst.desliz))


class Frenos(unittest.TestCase):
    def test_calendario_y_agenda_de_trump_con_hora_de_nueva_york(self):
        c = cx.Contexto()
        c.datos["calendario"] = [
            {"title": "CPI m/m", "country": "USD", "date": "2026-10-22T08:30:00-04:00", "impact": "High"},
            {"title": "Unemployment Claims", "country": "USD", "date": "2026-10-22T10:00:00-04:00", "impact": "Medium"},
            {"title": "GDP", "country": "GBP", "date": "2026-10-22T02:00:00-04:00", "impact": "High"},
            {"title": "Pending Home Sales", "country": "USD", "date": "2026-10-22T12:00:00-04:00", "impact": "Low"}]
        c.datos["trump"] = ('Date,Time,"Day of Week",Category,Details,Location\n'
                            '2026-10-23,14:00:00,Friday,"President Schedule","The President delivers Remarks","WH"\n'
                            '2026-10-23,16:00:00,Friday,"President Schedule","The President participates in Executive Time","WH"\n'
                            '2026-12-03,11:00:00,Thursday,"President Schedule","The President delivers a Speech","WH"\n')
        c._armar_eventos()

        def ms(texto):
            return int(dt.datetime.fromisoformat(texto).timestamp() * 1000)

        self.assertIn("CPI", c.bloqueo(ms("2026-10-22T08:20:00-04:00")) or "")       # 10 min antes: frena
        self.assertIsNone(c.bloqueo(ms("2026-10-22T08:10:00-04:00")))                # 20 min antes: no
        self.assertIn("CPI", c.bloqueo(ms("2026-10-22T08:59:00-04:00")) or "")       # 29 min después: frena
        self.assertIsNone(c.bloqueo(ms("2026-10-22T09:01:00-04:00")))
        self.assertIn("Claims", c.bloqueo(ms("2026-10-22T09:57:00-04:00")) or "")    # medio: 5 antes
        self.assertIsNone(c.bloqueo(ms("2026-10-22T09:50:00-04:00")))
        self.assertIsNone(c.bloqueo(ms("2026-10-22T02:00:00-04:00")))                # otro país: no
        self.assertIsNone(c.bloqueo(ms("2026-10-22T12:00:00-04:00")))                # impacto bajo: no
        self.assertIn("Trump", c.bloqueo(ms("2026-10-23T18:05:00+00:00")) or "")     # 14:05 en Nueva York (verano)
        self.assertIsNone(c.bloqueo(ms("2026-10-23T20:00:00+00:00")))                # Executive Time: no frena
        self.assertIn("Trump", c.bloqueo(ms("2026-12-03T16:00:00+00:00")) or "")     # 11:00 en invierno = 16:00 UTC
        self.assertIsNone(c.bloqueo(ms("2026-12-03T15:00:00+00:00")))
        self.assertEqual(c.proximo(ms("2026-10-21T00:00:00+00:00"))["motivo"][:6], "dato d")


if __name__ == "__main__":
    unittest.main()
