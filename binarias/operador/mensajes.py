"""Telegram del operador (16/11/2026): el bot de siempre, por Tor y con curl, igual que el laboratorio (partes.py).

Va en un hilo aparte, porque una llamada por Tor puede tardar medio minuto y el operador no puede dejar de mirar el
mercado mientras tanto. Lo que hay que mandar se deja en una cola; lo que escribe el dueño se entrega en otra.
La clave del bot se lee al momento de ~/.config/binarias/telegram (línea 1: clave, línea 2: chat) y viaja a curl por la
entrada estándar. Los mensajes del chat se leen con getUpdates sin offset, para no quitarle los suyos a otros programas;
solo cuentan los del chat del dueño, escritos por él y en privado."""
import json
import os
import queue
import subprocess
import threading
import time

CLAVE = os.path.expanduser("~/.config/binarias/telegram")
TOR = os.environ.get("OPERADOR_TOR", "127.0.0.1:9050")
REINTENTOS = 8           # un aviso que no sale se reintenta este número de veces, cada vez más espaciado
CADA_S = 20              # cada cuánto se mira el chat


def _comillas(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


class Correo:
    def __init__(self, log, vistos=(), clave=CLAVE, tor=TOR):
        self.log, self.ruta_clave, self.tor = log, clave, tor
        self.salida, self.entrada = queue.Queue(), queue.Queue()
        self.vistos = set(vistos)
        self.hilo, self.t_falla = None, -1e9

    def _clave(self):
        try:
            with open(self.ruta_clave, encoding="utf-8") as f:
                x = f.read().split()
            return x[0], x[1]
        except Exception:
            return None, None

    def _llamar(self, metodo, campos=None, consulta="", tiempo=60):
        token, _chat = self._clave()
        if not token:
            return None
        conf = ["url = " + _comillas(f"https://api.telegram.org/bot{token}/{metodo}{consulta}")]
        for k, v in (campos or {}).items():
            conf.append("form-string = " + _comillas(f"{k}={v}"))
        usuario = f"op{int(time.time()) % 100000}:x"  # circuito propio por llamada
        try:
            r = subprocess.run(["curl", "-s", "--max-time", str(tiempo), "--socks5-hostname", f"{usuario}@{self.tor}", "-K", "-"],
                               input="\n".join(conf) + "\n", capture_output=True, text=True, timeout=tiempo + 30)
            return json.loads(r.stdout) if r.stdout.strip() else None
        except Exception as ex:
            if time.monotonic() - self.t_falla > 1800:
                self.t_falla = time.monotonic()
                self.log(f"Telegram falló en {metodo} ({type(ex).__name__})")
            return None

    # ------------------------------------------------------------ lo que usa el operador
    def enviar(self, texto):
        self.salida.put([texto[:4000], 0, 0.0])

    def recibidos(self):
        """Los mensajes nuevos del dueño, del más viejo al más nuevo: {id, fecha, texto}."""
        out = []
        while True:
            try:
                out.append(self.entrada.get_nowait())
            except queue.Empty:
                return out

    def arrancar(self):
        if self.hilo is None:
            self.hilo = threading.Thread(target=self._bucle, daemon=True)
            self.hilo.start()

    # ------------------------------------------------------------ el hilo
    def _mandar(self, texto):
        _token, chat = self._clave()
        r = self._llamar("sendMessage", {"chat_id": chat, "text": texto})
        if r and r.get("ok"):
            return True
        if r:
            self.log(f"Telegram no aceptó el mensaje: {str(r)[:160]}")
        return False

    def _leer(self):
        _token, chat = self._clave()
        if not chat:
            return
        r = self._llamar("getUpdates", consulta="?limit=100&timeout=0", tiempo=40)
        for u in (r.get("result", []) if r and r.get("ok") else []):
            uid, m = u.get("update_id"), u.get("message")   # un mensaje editado no cuenta: una orden vieja no revive al corregirla
            if uid is None or not m or uid in self.vistos:
                continue
            self.vistos.add(uid)
            c, de = m.get("chat") or {}, m.get("from") or {}
            if str(c.get("id")) != str(chat) or c.get("type") != "private" or str(de.get("id")) != str(chat) or de.get("is_bot"):
                continue
            self.entrada.put({"id": uid, "fecha": float(m.get("date") or 0), "texto": (m.get("text") or "").strip()})

    def _bucle(self):
        t_chat, espera = 0.0, []
        while True:
            try:
                espera.append(self.salida.get(timeout=2))
            except queue.Empty:
                pass
            ahora = time.monotonic()
            for x in list(espera):
                if ahora < x[2]:
                    continue
                if self._mandar(x[0]):
                    espera.remove(x)
                else:
                    x[1] += 1
                    x[2] = time.monotonic() + min(600, 15 * 2 ** x[1])
                    if x[1] >= REINTENTOS:
                        espera.remove(x)
                        self.log(f"aviso sin entregar tras {REINTENTOS} intentos: {x[0][:80]}")
            if time.monotonic() - t_chat >= CADA_S:
                t_chat = time.monotonic()
                try:
                    self._leer()
                except Exception as ex:
                    self.log(f"no pude leer el chat ({type(ex).__name__})")


class CorreoMudo:
    """Para las pruebas y para correr sin Telegram: guarda lo que se mandaría y entrega lo que se le ponga."""

    def __init__(self):
        self.enviados, self.cola = [], []

    def enviar(self, texto):
        self.enviados.append(texto)

    def recibidos(self):
        out, self.cola = self.cola, []
        return out

    def arrancar(self):
        pass
