"""Laboratorio de binarias BTC/USDT (11/11/2026): el ciclo que corre solo en la caja. Solo papel.

Cada minuto trae de Binance (directo) las velas cerradas, el índice y, cada 5 min, el interés abierto; en cada cierre de 5 min
evalúa las formas vivas y abre sus apuestas de papel; cada 20 s atiende las peticiones del dueño; cada 5 min edita el tablero;
cada hora corre una tanda de búsqueda (si no hay pausa, calor ni reloj mal); a las 00:30 reajusta las redes, rota las formas
y copia la base; a las 6:00 manda el parte. Instancia única (puerto 8798, que además da el estado en JSON), PARAR en esta
carpeta, guardia de calor (pausa a 70 °C, vuelve a 62 °C) y guardia de reloj (pausa si se desvía más de 30 s de Binance).
Uso: python3 -I laboratorio.py [--seco] [--minutos N] [--base RUTA]"""
import os
import sys

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import datetime as dt  # noqa: E402
import http.server  # noqa: E402
import json  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402

import numpy as np  # noqa: E402

import base  # noqa: E402
import busqueda as BQ  # noqa: E402
import comun  # noqa: E402
import emulador as EM  # noqa: E402
import partes as P  # noqa: E402
import perdida as PD  # noqa: E402
import peticiones as PE  # noqa: E402
import rasgos as RG  # noqa: E402
import red as R  # noqa: E402
import velas as VL  # noqa: E402
from comun import COL, DATOS, DESDE_PRUEBAS, PUERTO, TOPE_VIVO, TRAMO, hora, log, num, pct, temperatura  # noqa: E402

CALIENTE, FRESCO = 70.0, 62.0
PLACA = os.environ.get("LAB_PLACA", "http://192.168.20.159:8080")  # la ESP32-S3 en la red de la casa
PRECIO_PROPIO = os.environ.get("LAB_PRECIO", "/data/local/tmp/precio/datos/precio.json")  # resumen del servicio de precio
ESTADO = {"latido": 0}


class Manejador(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        cuerpo = json.dumps(ESTADO, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


def candado():
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    except OSError:
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def ahora_col():
    return dt.datetime.now(COL)


class Lab:
    def __init__(self, seco, ruta_base=None):
        self.seco = seco
        P.SECO = seco
        self.inicio = int(time.time())
        self.con = base.abrir(ruta_base) if ruta_base else base.abrir()
        L = lambda k, d: base.leer(self.con, k, d)  # noqa: E731
        self.pausa, self.tope, self.cada = L("pausa", False), L("tope", TOPE_VIVO), L("cada", 60)
        self.calor, self.pausas_calor, self.t_max, self.reloj_ok = False, 0, None, True
        self.marcha = L("marcha", [])
        hoy = ahora_col().strftime("%Y%m%d")
        self.dia_tareas = L("dia_tareas", hoy)
        self.dia_parte = L("dia_parte", hoy if ahora_col().hour >= 6 else None)
        self.hora_busqueda, self.hora_revision = L("hora_busqueda", None), None
        self.prox_vela, self.prox_pet, self.ult_tab, self.ult_res = 0.0, 0.0, 0.0, time.time()
        self.avisos, self.sin_velas_desde, self.ultima_tanda = [], None, L("ultima_tanda", None)
        latido = L("latido", None)
        if latido and self.inicio - latido > 600:
            self.avisos.append(f"Laboratorio de vuelta tras {num((self.inicio - latido) / 60, 0)} min sin marcha.")

    # ------------------------------------------------------------ carga
    def cargar(self):
        vel = VL.Velas(*VL.historia(DESDE_PRUEBAS))
        interes = VL.cargar_interes()
        VL.cargar_indice(vel)
        VL.desde_base(vel, interes, self.con)
        try:
            n = VL.rellenar(vel, interes, self.con)
            log(f"velas rellenadas al arrancar: {n}")
        except Exception as ex:
            log(f"sin red al arrancar ({type(ex).__name__}); sigo con lo guardado")
        self.vel, self.interes = vel, interes
        self.motor = EM.MotorRed()
        self.ctx = RG.Contexto(vel.recorte(DESDE_PRUEBAS, TRAMO["juzga"][1] + 86400), interes)
        self.ctx.prob = EM.prob_historia(self.ctx, self.motor)
        self.emu = EM.Emulador(self.con, vel, interes, self.motor)
        self.perdida = PD.Perdida(self.con, vel)
        P.LINEAS_EXTRA = [self.perdida.linea, self.linea_precio_propio, self.linea_placa]
        log(f"cargado: {vel.n} minutos (última {hora(vel.t_ultima() + 60)}), {len(self.emu.vivas)} formas en vivo")

    # ------------------------------------------------------------ ciclo
    def correr(self, minutos=None):
        fin = time.time() + 60 * minutos if minutos else None
        texto = (f"Laboratorio en marcha · {len(self.emu.vivas)} formas en vivo · "
                 f"{'en seco, sin Telegram' if self.seco else 'informes a Telegram'} · Es papel.")
        base.evento(self.con, "arranque", texto)
        base.encolar(self.con, "aviso", texto + ("\n" + "\n".join(self.avisos) if self.avisos else ""))
        self.avisos = []
        while not comun.parar() and not (fin and time.time() >= fin):
            try:
                self.vuelta(time.time())
            except Exception as ex:
                log("error en la vuelta: " + "".join(traceback.format_exception_only(type(ex), ex)).strip()[:300])
                log(traceback.format_exc()[-1500:])
                base.evento(self.con, "error", f"{type(ex).__name__}: {str(ex)[:200]}")
                time.sleep(20)
            time.sleep(2)
        motivo = "PARAR" if comun.parar() else "fin de la prueba"
        base.evento(self.con, "detenido", f"laboratorio detenido ({motivo})")
        base.encolar(self.con, "aviso", f"Laboratorio detenido ({motivo}) a las {hora(time.time(), '%H:%M')}.")
        self.despachar()
        base.poner(self.con, "marcha", self.marcha)

    def vuelta(self, ahora):
        if ahora >= self.prox_vela and ahora % 60 >= 3:
            self.prox_vela = (ahora // 60 + 1) * 60 + 3
            self.traer(ahora)
            self.minuto(ahora)
        if self.emu.paso():
            pass
        self.emu.cerrar()
        if ahora - getattr(self, "_ult_perdida", 0) >= 20:
            self._ult_perdida = ahora
            try:
                self.perdida.paso()
            except Exception as ex:
                log(f"pérdida sin calcular ({type(ex).__name__}: {str(ex)[:80]})")
        if ahora - getattr(self, "_ult_placa", 0) >= 120:
            self._ult_placa = ahora
            self.consultar_placa()
        if not self.seco and ahora >= self.prox_pet:
            self.prox_pet = ahora + 20
            PE.atender(self)
        if ahora - self.ult_tab >= 300:
            self.ult_tab = ahora
            self.tablero()
        if ahora - self.ult_res >= 60 * self.cada:
            base.encolar(self.con, "resumen", P.resumen(self.con, self.ult_res, temperatura()))
            self.ult_res = ahora
        hc = ahora_col()
        clave_hora = hc.strftime("%Y%m%d%H")
        if hc.minute >= 2 and clave_hora != self.hora_revision:
            self.hora_revision = clave_hora
            self.revisar_hora()
        if hc.minute >= 7 and clave_hora != self.hora_busqueda and not self.pausa and not self.calor and self.reloj_ok:
            self.hora_busqueda = clave_hora
            base.poner(self.con, "hora_busqueda", clave_hora)
            self.buscar()
        dia = hc.strftime("%Y%m%d")
        if (hc.hour > 0 or hc.minute >= 30) and dia != self.dia_tareas:
            self.dia_tareas = dia
            base.poner(self.con, "dia_tareas", dia)
            self.tareas_diarias()
        if hc.hour >= 6 and dia != self.dia_parte:
            self.dia_parte = dia
            base.poner(self.con, "dia_parte", dia)
            base.encolar(self.con, "parte", P.parte_diario(self.con, self))
        self.despachar()

    def traer(self, ahora):
        if not self.reloj_ok:
            return
        antes = self.vel.n
        try:
            VL.rellenar(self.vel, self.interes if int(ahora // 60) % 5 == 1 else None, self.con, hasta=ahora)
        except Exception as ex:
            log(f"sin velas ({type(ex).__name__}: {str(ex)[:80]})")
        if self.vel.n > antes:
            self.sin_velas_desde = None
        elif self.sin_velas_desde is None:
            self.sin_velas_desde = ahora
        elif ahora - self.sin_velas_desde > 600 and not getattr(self, "_avisado_red", False):
            self._avisado_red = True
            self.avisos.append(f"Sin velas nuevas de Binance desde las {hora(self.sin_velas_desde, '%H:%M')}.")
        if self.sin_velas_desde is None:
            self._avisado_red = False

    def minuto(self, ahora):
        temp = temperatura()
        if temp is not None:
            self.t_max = temp if self.t_max is None else max(self.t_max, temp)
            if temp >= CALIENTE and not self.calor:
                self.calor = True
                self.pausas_calor += 1
                self.avisos.append(f"Calor: la caja llegó a {num(temp, 0)} °C; búsqueda y reajuste en pausa hasta {num(FRESCO, 0)} °C.")
                base.evento(self.con, "calor", f"{temp} °C")
            elif self.calor and temp <= FRESCO:
                self.calor = False
                base.evento(self.con, "fresco", f"{temp} °C")
        m = int(ahora // 60)
        self.marcha = [x for x in self.marcha if x > m - 1440] + [m]
        if m % 10 == 0:
            base.poner(self.con, "marcha", self.marcha)
        base.poner(self.con, "latido", int(ahora))
        ESTADO.update({"latido": int(ahora), "vivas": len(self.emu.vivas), "ultima_vela": self.vel.t_ultima() + 60,
                       "temperatura": temp, "pausa": self.pausa, "calor": self.calor, "reloj_ok": self.reloj_ok,
                       "seco": self.seco, "ultima_tanda": self.ultima_tanda,
                       "abiertas": self.con.execute("SELECT COUNT(*) FROM senales WHERE res IS NULL").fetchone()[0]})
        if not self.seco:  # el PC lo lee por ADB (herramientas\estado.py) y calcula la edad con su propio reloj
            try:
                with open(os.path.join(AQUI, "latido.json.tmp"), "w", encoding="utf-8") as f:
                    json.dump({k: v for k, v in ESTADO.items() if k != "tablero"}, f, ensure_ascii=False)
                os.replace(os.path.join(AQUI, "latido.json.tmp"), os.path.join(AQUI, "latido.json"))
            except OSError:
                pass

    # ------------------------------------------------------------ la ESP32 (11/11): su estado, sus señales y el precio real del PC
    def consultar_placa(self):
        import urllib.request
        try:
            d = json.loads(urllib.request.urlopen(PLACA + "/estado", timeout=6).read())
            self.placa, self.placa_vista = d, time.time()
            if getattr(self, "_placa_caida", False):
                self._placa_caida = False
                self.avisos.append("La placa ESP32 volvió a contestar.")
        except Exception:
            if time.time() - getattr(self, "placa_vista", self.inicio) > 900 and not getattr(self, "_placa_caida", False):
                self._placa_caida = True
                self.avisos.append("La placa ESP32 no contesta desde hace 15 min (¿desconectada o sin WiFi?).")

    def linea_precio_propio(self):
        """El precio real propio de la caja (servicio aparte, con su llave de solo lectura): aquí solo se lee su resumen."""
        try:
            d = json.load(open(PRECIO_PROPIO, encoding="utf-8"))
        except (OSError, ValueError):
            return "Precio real propio de la caja: falta la llave de solo lectura."
        r = d.get("resumen") or {}
        t = "Precio real propio de la caja: "
        t += (f"{r['k']} de {r['n']} compras de papel ganadas, ganancia {num(r.get('neto', 0), 2)} USDT por "
              f"{num(r.get('apostado', 0), 0)} apostados" if r.get("n") else "aún sin compras liquidadas")
        red = r.get("red")
        if red and red.get("ask") is not None and time.time() - red.get("t", 0) < 900:
            t += (f"; la red dice que el perdedor ({'SUBE' if red['lado'] > 0 else 'BAJA'}) vale hasta {num(red['precio_max'], 3)} "
                  f"y la app lo vende a {num(red['ask'], 3)}")
        edad = time.time() - d.get("hora", 0)
        return t + ("." if edad < 300 else f" (sin precio hace {num(edad / 60, 0)} min).")

    def linea_placa(self):
        d = getattr(self, "placa", None)
        if not d:
            return "Placa ESP32: sin datos todavía."
        b = d.get("binarias", {})
        partes = []
        for k in ("10", "15"):
            x = b.get(k, {})
            partes.append(f"{k} min {x.get('k', 0)} de {x.get('n', 0)}" + (f" ({pct(x['k'] / x['n'])})" if x.get("n") else ""))
        t = "Placa ESP32 (red propia, confianza 0,56): " + "; ".join(partes)
        pr = d.get("perdida", {})
        if pr.get("n"):
            t += f". Pérdida en la placa: {pr['k']} de {pr['n']}"
        real = d.get("real")
        if real and real.get("n"):
            t += (f". Con precio real (PC): {real['k']} de {real['n']}, ganancia {num(real.get('neto', 0), 2)} USDT "
                  f"por {num(real.get('apostado', 0), 0)} apostados")
        edad = time.time() - getattr(self, "placa_vista", 0)
        return t + ("." if edad < 900 else f"; sin respuesta hace {num(edad / 60, 0)} min.")

    def horas_marcha(self):
        m = int(time.time() // 60)
        return len([x for x in self.marcha if x > m - 1440]) / 60

    # ------------------------------------------------------------ tareas
    def tablero(self):
        texto = P.tablero(self.con, temperatura())
        ESTADO["tablero"] = texto
        if self.seco:
            return
        mid = base.leer(self.con, "tablero_mid")
        r = P.editar(mid, texto) if mid else "falta"
        if r == "falta":
            mid = P.enviar(texto)
            if mid:
                base.poner(self.con, "tablero_mid", mid)
                P.anclar(mid)

    def revisar_hora(self):
        try:
            desvio = time.time() - VL.hora_binance()
            ok = abs(desvio) <= 30
            if not ok and self.reloj_ok:
                self.avisos.append(f"Reloj mal: la caja va {num(desvio, 0)} s desviada de Binance; laboratorio en pausa.")
                base.evento(self.con, "reloj", f"desvío {desvio:.1f} s")
            self.reloj_ok = ok
        except Exception as ex:
            log(f"hora de Binance sin dato ({type(ex).__name__})")
        cambios = self.emu.situaciones()
        for fid, antes, nueva, n, k, origen, nombre in cambios:
            if nueva in ("prometedora", "apta en papel", "descartada") and antes is not None:
                self.avisos.append(f"F-{fid:04d} ({origen}) {nombre}: {antes} → {nueva}, {k} de {n} en vivo.")
        if self.avisos:
            base.encolar(self.con, "aviso", "Laboratorio · avisos\n" + "\n".join(self.avisos[:15]) + "\nEs papel.")
            self.avisos = []

    def buscar(self):
        t = time.time()
        r = BQ.tanda(self.con, self.ctx, semilla=int(t // 3600), tope=self.tope)
        self.ultima_tanda = {"lote": r["lote"], "t": int(t), "probadas": r["probadas"], "admitidas": r["admitidas"]}
        base.poner(self.con, "ultima_tanda", self.ultima_tanda)
        log(f"tanda {r['lote']}: {r['probadas']} probadas, {r['admitidas']} pasaron la valla, {r['a_vivo']} a vivo (las demás esperan "
            f"cupo de su familia), red de búsqueda {'sí' if r['red'] else 'no'}, {time.time() - t:.0f} s")
        if r["entraron"]:
            self.emu.recargar()
            for fid, estado in r["entraron"]:
                nombre = self.con.execute("SELECT nombre FROM formas WHERE id=?", (fid,)).fetchone()[0]
                self.avisos.append(f"Nueva en vivo: F-{fid:04d} {nombre} ({estado}).")

    def tareas_diarias(self):
        t = time.time()
        if not self.calor and not self.pausa:
            try:
                self.reentrenar()
            except Exception as ex:
                base.evento(self.con, "error", f"reajuste de redes: {type(ex).__name__}: {str(ex)[:160]}")
        self.emu.situaciones()
        salen, entran = self.emu.rotar(self.tope)
        base.evento(self.con, "rotación", f"salen {len(salen)}, entran {len(entran)}")
        try:
            base.respaldo(self.con)
        except Exception as ex:
            log(f"copia de la base falló ({type(ex).__name__})")
        self.t_max = temperatura()
        self.pausas_calor = 0
        log(f"tareas diarias en {time.time() - t:.0f} s")

    def reentrenar(self):
        z = np.load(os.path.join(DATOS, "red_X.npz"))
        X0, ok0, T0 = z["X"].astype(np.float64), z["ok"], z["T"].astype(np.int64)
        c = RG.Contexto(self.vel.recorte(int(T0[-1]) - 3 * 86400), None)
        b = np.flatnonzero(c.T > T0[-1])
        X1, ok1 = c.rasgos_red(b)
        X, ok, T = np.vstack([X0, X1]), np.r_[ok0, ok1], np.r_[T0, c.T[b]]
        hc = ahora_col()
        corte = int(dt.datetime(hc.year, hc.month, hc.day, tzinfo=COL).timestamp())
        notas = []
        for p in (10, 15):
            y = np.r_[z[f"y{p}"], c.etiqueta(p, b)]
            n = R.reajustar(X, ok, y, T, p, self.motor.red[p], self.motor.neu[p], corte, semilla=int(corte // 86400))
            notas.append(f"{p} min con {n}")
        self.motor.guardar()
        self.con.execute("INSERT INTO redes (tipo, plazo, t, datos, nota) VALUES ('mercado', NULL, ?, ?, ?)",
                         (int(time.time()), json.dumps({p: self.motor.usa[p] for p in (10, 15)}), "reajuste diario: " + "; ".join(notas)))
        self.con.commit()
        base.evento(self.con, "redes", "reajuste diario: " + "; ".join(notas))

    def despachar(self):
        for sid, t, tipo, texto in self.con.execute("SELECT id, t, tipo, texto FROM salida WHERE enviado=0 ORDER BY id LIMIT 5").fetchall():
            if self.seco:
                self.con.execute("UPDATE salida SET enviado=-1 WHERE id=?", (sid,))
                continue
            if time.time() - t > 7200 and tipo != "parte":
                self.con.execute("UPDATE salida SET enviado=-2 WHERE id=?", (sid,))
                continue
            mid = P.enviar(texto)
            if mid is None:
                break
            self.con.execute("UPDATE salida SET enviado=1, mensaje=? WHERE id=?", (mid, sid))
        self.con.commit()

    def estado_texto(self):
        c = self.con
        q = lambda s, *a: c.execute(s, a).fetchone()[0]  # noqa: E731
        vivas, adm = q("SELECT COUNT(*) FROM formas WHERE estado='viva'"), q("SELECT COUNT(*) FROM formas WHERE estado='admitida'")
        prob, des = q("SELECT COUNT(*) FROM formas WHERE origen IN ('red','azar')"), q("SELECT COUNT(*) FROM formas WHERE estado='descartada'")
        ab, ce, ac = (q("SELECT COUNT(*) FROM senales WHERE res IS NULL"), q("SELECT COUNT(*) FROM senales WHERE res IN (0,1)"),
                      q("SELECT COALESCE(SUM(res),0) FROM senales WHERE res IN (0,1)"))
        temp = temperatura()
        ut = self.ultima_tanda
        lineas = [f"Laboratorio · estado · {hora(time.time())}",
                  f"Formas en vivo: {vivas} (tope {self.tope}); esperando cupo: {adm}; nuevas probadas: {num(prob, 0)}; descartadas: {des}.",
                  f"Papel en vivo: {ab} abiertas, {ce} cerradas ({ac} aciertos).",
                  f"Última vela: {hora(self.vel.t_ultima() + 60, '%H:%M')}. Caja: " +
                  (f"{num(temp, 0)} °C (máx. {num(self.t_max or temp, 0)})" if temp is not None else "sin sensor") +
                  f". Reloj {'bien' if self.reloj_ok else 'mal'}. Pausa: {'sí' if self.pausa else 'no'}. Calor: {'sí' if self.calor else 'no'}.",
                  "Redes: " + "; ".join(f"{p} min usa la {self.motor.usa[p]}" for p in (10, 15)) + f"; último ajuste {hora(self.motor.t)}.",
                  (f"Última tanda: {ut['lote']} a las {hora(ut['t'], '%H:%M')} ({ut['probadas']} probadas, {ut['admitidas']} entraron)."
                   if ut else "Aún sin tandas de búsqueda en esta caja.") + f" Resumen cada {self.cada} min. Es papel."]
        return "\n".join(lineas)


def main():
    seco = "--seco" in sys.argv
    minutos = int(sys.argv[sys.argv.index("--minutos") + 1]) if "--minutos" in sys.argv else None
    ruta = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else None
    srv = candado()
    if srv is None:
        log("otra copia del laboratorio ya corre (puerto 8798 ocupado): salgo")
        return 0
    try:
        lab = Lab(seco, ruta)
        lab.cargar()
        if "--medir-reajuste" in sys.argv:  # prueba: reajusta sin tocar las redes vigentes (guarda en redes_prueba.json)
            lab.motor.ruta = os.path.join(DATOS, "redes_prueba.json")
            t0, c0 = time.time(), temperatura()
            lab.reentrenar()
            print(f"reajuste de las dos redes en {time.time() - t0:.0f} s; temperatura {c0} → {temperatura()}", flush=True)
            return 0
        lab.correr(minutos)
    finally:
        srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
