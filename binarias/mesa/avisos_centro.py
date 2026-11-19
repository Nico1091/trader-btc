"""Avisos del Centro de estrategias a su Telegram y a la pantalla del PC (07/11/2026). Solo biblioteca estándar.

Pedido del dueño del 07/11: «que todos esos avisos múltiples se muestren en vivo en la pantalla y en mi Telegram», solo en el
programa de binarias actual.
- Telegram: bot Centro nocturno, por Tor (127.0.0.1:9050), igual que la caja y Pulso. La clave y el chat se leen una vez de WSL
  (~/.gumroad/telegram-token y telegram-chat), quedan solo en memoria y van a curl por la entrada estándar: no aparecen en la
  lista de procesos ni en ningún registro. Texto directo, nunca archivos.
- El resultado de cada señal se escribe sobre el mismo mensaje (editMessageText): una señal, un mensaje.
- Pantalla: notificación de Windows con el mismo texto, además de la franja de avisos de la Mesa y del Centro.
Todo va en un hilo con cola: si Tor tarda, la Mesa no se detiene. Nada de esto compra.
"""
import json
import os
import queue
import subprocess
import threading
import time

TOR = "127.0.0.1:9050"
CURL = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe")
SIN_VENTANA = 0x08000000  # CREATE_NO_WINDOW: ni curl ni PowerShell abren consola


def _comillas(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


class Notificador:
    def __init__(self, log, telegram=True, pantalla=True):
        self.log, self.telegram, self.pantalla = log, telegram, pantalla
        self.cola = queue.Queue()
        self._clave = None
        threading.Thread(target=self._correr, daemon=True).start()

    # ------------------------------------------------------------ lo que llama el Centro
    def avisar(self, aviso, al_enviar=None):
        """aviso: {"texto", "titulo", "editar": message_id o None}. al_enviar(message_id) guarda el número para editarlo luego."""
        self.cola.put((aviso, al_enviar))

    # ------------------------------------------------------------ hilo
    def _correr(self):
        while True:
            aviso, al_enviar = self.cola.get()
            try:
                if self.pantalla and aviso.get("corto"):
                    self._windows(aviso.get("titulo") or "Centro de estrategias", aviso["corto"])
                if self.telegram:
                    mid = self._telegram(aviso["texto"], aviso.get("editar"))
                    if mid and al_enviar:
                        al_enviar(mid)
            except Exception as ex:
                self.log(f"avisos: {type(ex).__name__}: {str(ex)[:120]}")

    def _leer_clave(self):
        if self._clave is None:
            r = subprocess.run(["wsl.exe", "-e", "sh", "-c", "cat ~/.gumroad/telegram-token; echo; cat ~/.gumroad/telegram-chat"],
                               capture_output=True, text=True, timeout=60, creationflags=SIN_VENTANA)
            partes = (r.stdout or "").split()
            if len(partes) < 2:
                raise RuntimeError("no encuentro la clave del bot en WSL")
            self._clave = (partes[0], partes[1])
        return self._clave

    def _telegram(self, texto, editar=None):
        """Manda (o corrige) el mensaje; devuelve el message_id o None."""
        token, chat = self._leer_clave()
        metodo = "editMessageText" if editar else "sendMessage"
        lineas = ["url = " + _comillas(f"https://api.telegram.org/bot{token}/{metodo}"),
                  "form-string = " + _comillas(f"chat_id={chat}"),
                  "form-string = " + _comillas(f"text={texto[:4000]}")]
        if editar:
            lineas.append("form-string = " + _comillas(f"message_id={editar}"))
        usuario = f"centro{int(time.time()) % 100000}:x"  # circuito propio por aviso, como la caja
        for intento in range(3):
            r = subprocess.run([CURL, "-s", "--max-time", "60", "--socks5-hostname", f"{usuario}@{TOR}", "-K", "-"],
                               input="\n".join(lineas) + "\n", capture_output=True, text=True, timeout=90, creationflags=SIN_VENTANA)
            try:
                d = json.loads(r.stdout or "{}")
            except ValueError:
                d = {}
            if d.get("ok"):
                return (d.get("result") or {}).get("message_id")
            if editar and "message is not modified" in str(d.get("description", "")):
                return editar
            if editar and d.get("error_code") == 400:  # mensaje viejo o borrado: se manda uno nuevo
                return self._telegram(texto, None)
            self.log(f"Telegram sin confirmar (intento {intento + 1}, curl {r.returncode}): {str(d.get('description') or r.stderr)[:120]}")
            time.sleep(5)
        return None

    def _windows(self, titulo, texto):
        """Notificación de Windows sin módulos extra (API de notificaciones de Windows desde PowerShell)."""
        def esc(x):
            return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "''")
        cuerpo = esc(texto[:600]).replace("\n", "&#10;")
        ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
              "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
              "$x = New-Object Windows.Data.Xml.Dom.XmlDocument;"
              f"$x.LoadXml('<toast><visual><binding template=\"ToastGeneric\"><text>{esc(titulo)}</text><text>{cuerpo}</text></binding></visual></toast>');"
              "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
              "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($x))")
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, timeout=30, creationflags=SIN_VENTANA)
