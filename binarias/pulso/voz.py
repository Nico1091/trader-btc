"""Voz de Salomé para Pulso BTC: lee el texto de la entrada estándar y escribe el MP3.
Usa el edge-tts portátil de voice-claude con la misma voz, velocidad y tono, y sale por el proxy que se le indique
(el puente de pulso hacia Tor). Uso: python -I voz.py salida.mp3 http://127.0.0.1:9077"""
import asyncio
import sys

sys.path.insert(0, r"C:\Users\ni109\voice-claude\libs")
import edge_tts  # noqa: E402

VOZ, VELOCIDAD, TONO = "es-CO-SalomeNeural", "-8%", "+8Hz"


async def main():
    texto = sys.stdin.buffer.read().decode("utf-8").strip()
    com = edge_tts.Communicate(texto, VOZ, rate=VELOCIDAD, pitch=TONO, proxy=sys.argv[2])
    await com.save(sys.argv[1])


asyncio.run(main())
