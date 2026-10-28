"""C1 (28/10/2026): ¿copiar a los traders líderes de Binance da dinero a los que copian?

Pedido de Nicolás: «averigüe usted mismo cómo funciona el trading y pruebe copy trading en papel con alguien que tome los
riesgos que yo tomo». Antes de copiar a nadie se mira lo que de verdad ganaron sus copiadores (`copierPnl`, público en la
tabla de líderes de futuros de Binance), frente a lo que muestra el líder (ROI y PnL propios).

Fuente: la web pública de Binance (rutas internas sin cuenta ni clave: home-page/query-list). Solo lectura, una consulta
cada 0,6 s. Guarda la tabla cruda en datos/copy/ (fuera de git) y escribe el resumen.
Uso: python -I c1_tabla_lideres.py > c1_tabla_lideres.txt"""
import json
import os
import sys
import time
import urllib.request

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(os.environ.get("TRADER_DATOS") or os.path.join(AQUI, "..", "..", "datos"), "copy")
URL = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/home-page/query-list"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/141.0 Safari/537.36",
     "Content-Type": "application/json", "clienttype": "web"}


def pagina(rango, orden, n):
    cuerpo = {"pageNumber": n, "pageSize": 20, "timeRange": rango, "dataType": orden, "favoriteOnly": False,
              "hideFull": False, "nickname": "", "order": "DESC", "portfolioType": "PUBLIC"}
    req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode(), headers=H, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["data"]["list"]


def bajar(rango, orden, total=500):
    filas = []
    for n in range(1, total // 20 + 1):
        filas += pagina(rango, orden, n)
        time.sleep(0.6)
    return filas


def resumen(nombre, filas):
    def num(x, k):
        try:
            return float(x.get(k) or 0)
        except ValueError:
            return 0.0
    roi = np.array([num(x, "roi") for x in filas])
    pnl = np.array([num(x, "pnl") for x in filas])
    cp = np.array([num(x, "copierPnl") for x in filas])
    aum = np.array([num(x, "copyAum") for x in filas])
    mdd = np.array([num(x, "mdd") for x in filas])
    copios = np.array([num(x, "currentCopyCount") for x in filas])
    con = aum > 0
    roi_cop = np.where(con, cp / np.where(aum > 0, aum, 1) * 100, np.nan)
    print(f"\n== {nombre}: {len(filas)} líderes ==")
    print(f"   ROI propio del líder: mediana {np.median(roi):,.0f} % · p10 {np.percentile(roi, 10):,.0f} % · p90 {np.percentile(roi, 90):,.0f} %")
    print(f"   PnL propio sumado: {pnl.sum():,.0f} USD · PnL de sus copiadores sumado: {cp.sum():,.0f} USD sobre {aum.sum():,.0f} USD copiados "
          f"({cp.sum() / max(1, aum.sum()) * 100:+.2f} %)")
    print(f"   Líderes cuyos copiadores ganan en total: {(cp > 0).sum()} de {len(filas)} ({(cp > 0).mean() * 100:.0f} %)")
    print(f"   Rendimiento de los copiadores (copierPnl / copyAum), mediana {np.nanmedian(roi_cop):+.2f} % · p10 {np.nanpercentile(roi_cop, 10):+.2f} % · p90 {np.nanpercentile(roi_cop, 90):+.2f} %")
    print(f"   Caída máxima del líder: mediana {np.median(mdd):.0f} % · con más del 50 %: {(mdd > 50).mean() * 100:.0f} %")
    corr = np.corrcoef(roi[con], roi_cop[con])[0, 1] if con.sum() > 5 else float("nan")
    print(f"   ¿El ROI del líder dice cuánto ganan sus copiadores? correlación {corr:+.2f}")
    orden = np.argsort(-cp)
    print("   Los 8 con más ganancia de sus copiadores:")
    for i in orden[:8]:
        x = filas[i]
        print(f"     {x.get('nickname', '')[:18]:18s} id {x.get('leadPortfolioId')} · ROI líder {roi[i]:,.0f} % · copiadores {cp[i]:+,.0f} USD "
              f"sobre {aum[i]:,.0f} ({roi_cop[i]:+.1f} %) · caída {mdd[i]:.0f} % · {int(copios[i])} copiando")


def main():
    os.makedirs(DATOS, exist_ok=True)
    fecha = time.strftime("%Y-%m-%d", time.gmtime())
    print(f"C1 · tabla pública de líderes de copy trading de futuros de Binance, bajada el {fecha} (UTC)")
    for rango, orden in (("30D", "ROI"), ("90D", "ROI"), ("90D", "PNL")):
        filas = bajar(rango, orden)
        json.dump(filas, open(os.path.join(DATOS, f"lideres-{rango}-{orden}-{fecha}.json"), "w", encoding="utf-8"))
        resumen(f"{rango} ordenados por {orden}", filas)


if __name__ == "__main__":
    main()
