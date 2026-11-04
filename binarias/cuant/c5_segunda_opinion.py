"""C5 (03/11/2026): segunda opinión de otros modelos de IA sobre el plan y la investigación. Por Tor.

Lo que ven los modelos: la metodología y los resultados agregados de las pruebas. NO ven apuestas, saldos, claves ni
datos de Nicolás (regla de privacidad del bloc). Las claves se leen del .env de polycode al momento y van a curl por la
entrada estándar. Se valida finish_reason == "stop", contenido no vacío y huella distinta entre respuestas.
Uso: python -I c5_segunda_opinion.py
"""
import hashlib
import json
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "resultados")
ENV = r"C:\Users\ni109\Documents\Default Project\polycode\.env"

PREGUNTA = """Eres un revisor cuantitativo exigente. Revisa este plan de investigación y validación para opciones binarias de
corto plazo y di con franqueza qué está bien, qué está mal, qué falta y qué harías después, en orden de prioridad.
Responde en español, con números cuando puedas, en menos de 900 palabras.

CONTEXTO
- Producto: Contratos de Evento de Binance (binarias por tiempo) sobre BTCUSDT y ETHUSDT, a 10 min, 30 min, 1 h o 1 día.
  Pago fijo que Binance fija al apostar, medido con 0,80, 0,85 y 0,90. Equilibrio = 1/(1+pago): 55,6 / 54,1 / 52,6 %.
  Sin API: la apuesta se toca a mano en la app (Binance prohíbe bots ahí). Todo en papel por ahora.
- Datos: velas de 1 min de futuros perpetuos de Binance 2020-2026 con volumen de compra agresiva (taker buy).
- Sistema actual: cada mes se elige, con los 12 meses anteriores y a ciegas, el mejor de 8 procedimientos (reglas o una
  regresión logística propia de 53 rasgos, a 10/30/60 min); tamaño medio Kelly con mínimo de 5 USDT; sin stop.
  Banco a ciegas 2021-2026: 57-58 % de acierto en 11.000-43.000 apuestas; el acierto viene bajando (60 % en 2020 a 55 % en 2026).

INVESTIGACIÓN NUEVA (elegir en 2021-2023, juzgar intacto en 2024 a sep-2026 y oct-2026; decisión cada 10 min, empate = fallo)
- Seis dimensiones discretizadas: temporalidad (sesión, fin de semana), dirección (1h/4h/1d e impulso de 15 min en
  desviaciones), volatilidad (ATR/mediana 30 d, ancho de Bollinger, ruptura de 20 velas de 5 min), liquidez (volumen
  relativo, flujo de órdenes, barrido de la hora previa), estructura SMC (BOS, CHoCH, FVG, order block, AMD por barrido del
  rango de Asia, área de valor del día anterior) y estadística de resultados (rachas, caída, quiebra).
- Una sola variable, sentido elegido en entrenamiento (entrenamiento / prueba / octubre 2026):
  BTC: ruptura alcista de 20 velas -> BAJA 59,4 / 56,1 / 61,7 %; ruptura bajista -> SUBE 59,2 / 55,8 / 55,0 %;
  caída de 15 min > 1 desviación -> SUBE 55,7 / 54,1 / 53,4 %; alineación 1h-4h-1d al revés ~53 %; flujo de órdenes al
  revés ~52 %; FVG, order blocks, AMD, área de valor y sesión entre 50 y 51,6 %. ETH muy parecido (ruptura al revés 56-57 %).
- 14.600 celdas de 2 y 3 variables con 300+ apuestas; 7.000 pasan Benjamini-Hochberg; 1.200-1.450 tienen Wilson > 54,1 %.
  Las mejores bajan de 65-68 % a 53-62 % fuera de muestra. La cartera de todas las elegidas da 52,8-53,1 % en la prueba.
  PBO por CSCV (16 bloques, 29.000 estrategias): 0,1 % en BTC y 2,7 % en ETH (la jerarquía persiste aunque el nivel cae).
- Ninguna celda alcanza 85,7 % ni en entrenamiento; la mejor de la prueba, escogida mirando el resultado, 66-69 %, que es
  lo que daría el azar entre 15.500 celdas de 100 apuestas.
- Rachas: tras acertar se acierta 51,8 % y tras fallar 53,9 % (cartera); en el banco real, 57,5 % tras acertar y 58,6 %
  tras fallar: no hay «mano caliente».
- HMM gaussiano de 3 regímenes (1 h): sin sesgo de dirección en ningún régimen; la reversión de 15 min funciona en los tres
  (53-56 %). Autocorrelación de 10 min negativa y decreciente (BTC -0,043 a -0,026; ETH -0,061 a -0,011).
- Anomalías (z robusto >= 4-5 en 10 min) apostando en contra: 54-56 %.

PEDIDOS DEL DUEÑO DEL PROYECTO
- Meta: 85,7 % de acierto. Idea: operar solo «cuando hay suerte» (cuando el algoritmo está en racha) y pausar al ganar.
- Quiere estudiar además: libro de nivel 2, footprint, mapas de calor de liquidez, teoría de subasta (AMT), muros de puts y
  calls, gamma flip, GEX, DEX, VEX, flujo de opciones, macroeconomía, Wall Street y Banco Mundial. Sin apalancamiento.

PREGUNTAS
1. ¿Hay errores de método o fugas de información que invaliden algo? ¿Qué validación falta (por ejemplo, purga y
   embargo, walk-forward, CPCV, deflactar el acierto por número de pruebas, costos de entrar tarde)?
2. ¿Es plausible 85,7 % en binarias de 10 min sobre BTC/ETH? ¿Qué meta honesta propondrías y cómo medirla?
3. De la lista nueva (L2, footprint, opciones/GEX, macro), ¿qué tiene más probabilidad real de sumar ventaja a 10-60 min
   y cómo probarlo a ciegas con datos gratuitos o baratos?
4. ¿Qué harías con el tamaño de apuesta (mínimo de 5 USDT con 100.000 COP) y con la regla de «pausar al ganar»?
5. Dame los 5 próximos experimentos, cada uno con su regla de decisión escrita antes.
"""


def clave(nombre):
    for lin in open(ENV, encoding="utf-8"):
        if lin.startswith(nombre + "="):
            return lin.split("=", 1)[1].strip()
    raise KeyError(nombre)


def consultar(url, key, modelo, max_tokens):
    cuerpo = json.dumps({"model": modelo, "messages": [{"role": "user", "content": PREGUNTA}], "max_tokens": max_tokens, "temperature": 0.3})
    conf = f'url = "{url}"\nheader = "Authorization: Bearer {key}"\nheader = "Content-Type: application/json"\n'
    ruta = os.path.join(SALIDA, ".cuerpo.json")
    open(ruta, "w", encoding="utf-8").write(cuerpo)
    conf += f'data-binary = "@{ruta.replace(chr(92), "/")}"\n'
    t0 = time.time()
    r = subprocess.run(["curl", "-s", "--max-time", "600", "--socks5-hostname", f"ia{int(t0) % 9999}:x@127.0.0.1:9050", "-K", "-"],
                       input=conf, capture_output=True, text=True, timeout=660, encoding="utf-8", errors="replace")
    os.remove(ruta)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return {"error": (r.stdout or r.stderr)[:300], "segundos": time.time() - t0}
    if "choices" not in d:
        return {"error": json.dumps(d)[:300], "segundos": time.time() - t0}
    ch = d["choices"][0]
    return {"modelo_pedido": modelo, "modelo_responde": d.get("model"), "fin": ch.get("finish_reason"),
            "texto": (ch.get("message") or {}).get("content") or "", "segundos": round(time.time() - t0, 1)}


def main():
    os.makedirs(SALIDA, exist_ok=True)
    solo = sys.argv[1:]  # nombres a correr; vacío = todos
    trabajos = [
        ("deepseek", "https://api.deepseek.com/v1/chat/completions", "DEEPSEEK_KEY", ["deepseek-chat"], 6000),
        # 03/11: la clave propia de DeepSeek dio «Authentication Fails»; el mismo modelo por OpenRouter
        ("deepseek-openrouter", "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_KEY2",
         ["deepseek/deepseek-chat", "deepseek/deepseek-chat-v3-0324", "openai/gpt-4o-mini"], 6000),
        ("nemotron", "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_KEY1",
         ["nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3-super-120b-a12b:free", "openai/gpt-4o-mini"], 8000),
    ]
    huellas = set()
    for nombre, url, var, modelos, mt in trabajos:
        if solo and nombre not in solo:
            continue
        key = clave(var)
        for m in modelos:
            res = consultar(url, key, m, mt)
            ok = res.get("fin") == "stop" and len(res.get("texto", "").strip()) > 200
            h = hashlib.sha256(res.get("texto", "").encode()).hexdigest()[:16]
            if ok and h not in huellas:
                huellas.add(h)
                open(os.path.join(SALIDA, f"c5_opinion_{nombre}.md"), "w", encoding="utf-8").write(
                    f"# Segunda opinión: {nombre}\n\nModelo pedido: {res['modelo_pedido']} · responde: {res['modelo_responde']} · "
                    f"fin: {res['fin']} · {res['segundos']} s · huella {h}\n\n{res['texto']}\n")
                print(f"{nombre}: {res['modelo_responde']} · {res['fin']} · {len(res['texto'])} caracteres · {res['segundos']} s")
                break
            print(f"{nombre}: {m} falló o vino incompleto ({res.get('fin')}, {res.get('error', '')[:160]}); siguiente")


if __name__ == "__main__":
    main()
