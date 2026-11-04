"""C6 (03/11/2026): CRT, conceptos ICT que faltaban y el libro de órdenes (Bookmap), en BTCUSDT. A ciegas.

Pedido de Nicolás (03/11): footprint, Bookmap, SMC, CRT e ICT. SMC (BOS, CHoCH, FVG, order block, barridos, AMD) ya
está en C1. Aquí, con la misma regla de C1 (sentido elegido en 2021-2023; juicio intacto en 2024 a sep-2026 y oct-2026;
binaria de 10 min, una decisión cada 10 min, empate = fallo):
- CRT (Candle Range Theory) en velas de 1 h y de 4 h: la vela en curso barre el máximo (o el mínimo) de la vela anterior y
  el precio vuelve a estar dentro de su rango.
- ICT: killzones en hora de Nueva York con horario de verano (Asia 20-24, Londres 2-5, NY AM 7-10, silver bullet 10-11,
  NY PM 13:30-16); premium o discount dentro del rango de 24 h; OTE (retroceso de 62 a 79 % del último tramo de 5 min);
  divergencia SMT con ETH (uno barre el máximo o mínimo de la hora previa y el otro no).
- Libro de órdenes (bookDepth de Binance, fotos cada 30 s, 2023 a 2026): desequilibrio a ±0,2 %, ±1 % y ±5 % y cambio
  del desequilibrio de ±1 % en 10 min. Aquí el entrenamiento es solo 2023 (no hay libro antes).
- Footprint: con velas de 1 min solo existe el delta agregado (compra agresiva menos venta agresiva), ya probado en C1.
  El footprint por nivel de precio exige las operaciones una por una (aggTrades): queda en el plan.
Uso: python -I c6_crt_ict_libro.py
"""
import datetime as dt
import glob
import io
import os
import sys
import zipfile

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base as B  # noqa: E402
import validacion as V  # noqa: E402
from c1_cruces import datos, es, pct  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "resultados")
EQ = B.EQUILIBRIO


def ny_offset(ts):
    """Horas a sumar a UTC para la hora de Nueva York (EE. UU.: 2.º domingo de marzo a 1.er domingo de noviembre)."""
    out = np.full(len(ts), -5, np.int64)
    años = np.unique([dt.datetime.utcfromtimestamp(int(x)).year for x in ts[:: max(1, len(ts) // 400)]] + [dt.datetime.utcfromtimestamp(int(ts[-1])).year])
    for a in años:
        mar = dt.datetime(a, 3, 8)
        ini = mar + dt.timedelta(days=(6 - mar.weekday()) % 7)  # segundo domingo de marzo
        nov = dt.datetime(a, 11, 1)
        fin = nov + dt.timedelta(days=(6 - nov.weekday()) % 7)  # primer domingo de noviembre
        i0 = (ini.replace(tzinfo=dt.timezone.utc).timestamp() + 7 * 3600)  # 2:00 hora estándar = 7:00 UTC
        i1 = (fin.replace(tzinfo=dt.timezone.utc).timestamp() + 6 * 3600)  # 2:00 hora de verano = 6:00 UTC
        out[(ts >= i0) & (ts < i1)] = -4
    return out


def evaluar(nombre, estados, etiquetas, y, tr, lineas, minimo=100):
    """Sentido por estado elegido en entrenamiento y acierto en los tres tramos."""
    filas = []
    for k, et in enumerate(etiquetas):
        m = estados == k
        m0 = m & (tr == 0)
        if m0.sum() < minimo:
            continue
        s = 1 if np.sum(y[m0] == 1) >= np.sum(y[m0] == -1) else -1
        res = []
        for j in range(3):
            mj = m & (tr == j)
            n = int(mj.sum())
            res.append((float(np.mean(y[mj] == s)) if n else float("nan"), n))
        lb = V.wilson(int(round(res[0][0] * res[0][1])), res[0][1])[0]
        filas.append((et, s, res, lb))
        lineas.append(f"  {nombre:<14} {et:<30} {'SUBE' if s == 1 else 'BAJA'}: " + " / ".join(pct(a) for a, _ in res)
                      + "  (" + " / ".join(f"{n:,}" for _, n in res).replace(",", ".") + ")")
    return filas


def libro(t_dec, sim):
    """Desequilibrios del libro en cada decisión (foto anterior más cercana, a menos de 60 s)."""
    archivos = sorted(glob.glob(os.path.join(B.RAIZ, "datos", "bookdepth", sim, f"{sim}-bookDepth-*.zip")))
    if not archivos:
        return None
    marcas, filas = [], []
    for ruta in archivos:
        try:
            z = zipfile.ZipFile(ruta)
            texto = z.read(z.namelist()[0]).decode()
        except Exception:
            continue
        actual, foto = None, {}
        for lin in texto.splitlines()[1:]:
            p = lin.split(",")
            if len(p) < 3:
                continue
            ts = p[0]
            if ts != actual:
                if actual is not None and len(foto) >= 10:
                    marcas.append(actual)
                    filas.append(foto)
                actual, foto = ts, {}
            # solo las fotos de los segundos 30-59 del minuto 9 de cada tramo de 10 min (la última antes de decidir)
            if ts[15] == "9" and ts[17] in "345":
                foto[float(p[1])] = float(p[2])
            elif ts[15] == "9":
                pass
        if actual is not None and len(foto) >= 10:
            marcas.append(actual)
            filas.append(foto)
    if not marcas:
        return None
    tt = np.array([dt.datetime.strptime(m, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp() for m in marcas])
    def lado(f, p):
        return f.get(-p, np.nan), f.get(p, np.nan)
    imb = {}
    for p in (0.2, 1.0, 5.0):
        b = np.array([lado(f, p)[0] for f in filas])
        a = np.array([lado(f, p)[1] for f in filas])
        imb[p] = (b - a) / (b + a)
    orden = np.argsort(tt)
    tt = tt[orden]
    for p in imb:
        imb[p] = imb[p][orden]
    j = np.searchsorted(tt, t_dec, side="right") - 1
    valido = (j >= 0) & (t_dec - tt[np.maximum(j, 0)] <= 60)
    out = {}
    for p in imb:
        v = np.where(valido, imb[p][np.maximum(j, 0)], np.nan)
        out[p] = v
    # cambio del desequilibrio de ±1 % frente a la foto de 10 min antes
    j10 = np.searchsorted(tt, t_dec - 600, side="right") - 1
    v10 = (j10 >= 0) & (t_dec - 600 - tt[np.maximum(j10, 0)] <= 60)
    out["d1"] = np.where(valido & v10, imb[1.0][np.maximum(j, 0)] - imb[1.0][np.maximum(j10, 0)], np.nan)
    out["n"] = int(valido.sum())
    return out


def terciles(x, tr_mask):
    a, b = np.nanpercentile(x[tr_mask], [33.3, 66.7])
    e = np.where(np.isnan(x), -1, np.where(x < a, 0, np.where(x > b, 2, 1)))
    return e.astype(int), (a, b)


def main():
    sim = "BTCUSDT"
    d = datos(sim)
    y, tr, td = d["y"].astype(int), d["tramo"], d["t"]
    t, o, h, l, c, v, tb = B.cargar(sim)
    i = np.searchsorted(t, td - 60)
    L = [f"C6 · {sim} · CRT, ICT y libro de órdenes · binaria de 10 min, una decisión cada 10 min, empate = fallo",
         "acierto entrenamiento / prueba / adelante (apuestas); sentido de cada estado elegido en entrenamiento", ""]
    # ---- CRT en 1 h y 4 h
    for horas in (1, 4):
        P = 3600 * horas
        ini_v = (td - 1) // P * P  # inicio de la vela en curso
        crt = np.full(len(td), 2, int)
        for k in range(len(td)):
            a_cur = np.searchsorted(t, ini_v[k])
            a_prev = np.searchsorted(t, ini_v[k] - P)
            if a_prev >= a_cur or a_cur > i[k]:
                continue
            hp, lp = h[a_prev:a_cur].max(), l[a_prev:a_cur].min()
            hc, lc = h[a_cur:i[k] + 1].max(), l[a_cur:i[k] + 1].min()
            arriba = hc > hp and c[i[k]] < hp
            abajo = lc < lp and c[i[k]] > lp
            if arriba and not abajo:
                crt[k] = 0
            elif abajo and not arriba:
                crt[k] = 1
        L.append(f"CRT en velas de {horas} h:")
        evaluar(f"CRT {horas} h", crt, ["barrió máximo y volvió", "barrió mínimo y volvió", "sin CRT"], y, tr, L)
    # ---- killzones (hora de Nueva York)
    off = ny_offset(td)
    m_ny = ((td + off * 3600) % 86400) // 60  # minuto del día en Nueva York
    kz = np.select([(m_ny >= 20 * 60), (m_ny >= 2 * 60) & (m_ny < 5 * 60), (m_ny >= 7 * 60) & (m_ny < 10 * 60),
                    (m_ny >= 10 * 60) & (m_ny < 11 * 60), (m_ny >= 13 * 60 + 30) & (m_ny < 16 * 60)], [0, 1, 2, 3, 4], 5)
    L.append("")
    L.append("ICT · killzones (hora de Nueva York, con horario de verano):")
    evaluar("killzone", kz, ["Asia (20-24 NY)", "Londres (2-5 NY)", "NY AM (7-10 NY)", "silver bullet (10-11 NY)", "NY PM (13:30-16 NY)", "fuera de killzone"], y, tr, L)
    # reversión dentro de cada killzone (la familia que sí funciona)
    imp = d["F"]["impulso"]
    rev = np.where(imp == 0, 1, np.where(imp == 1, -1, 0))
    L.append("  reversión de 15 min por killzone (prueba): " + " · ".join(
        f"{et} {pct(np.mean(y[(kz == k) & (rev != 0) & (tr == 1)] == rev[(kz == k) & (rev != 0) & (tr == 1)]))}"
        for k, et in enumerate(["Asia", "Londres", "NY AM", "silver bullet", "NY PM", "fuera"])))
    # ---- premium / discount en el rango de 24 h
    from numpy.lib.stride_tricks import sliding_window_view
    hi24 = np.full(len(t), np.nan)
    lo24 = np.full(len(t), np.nan)
    hi24[1439:] = sliding_window_view(h, 1440).max(axis=1)
    lo24[1439:] = sliding_window_view(l, 1440).min(axis=1)
    pos = (c[i] - lo24[i]) / np.maximum(hi24[i] - lo24[i], 1e-9)
    pdz = np.select([pos > 0.55, pos < 0.45], [0, 1], 2)
    L.append("")
    L.append("ICT · premium / discount (posición en el rango de 24 h):")
    evaluar("zona", pdz, ["premium (>55 %)", "discount (<45 %)", "equilibrio (45-55 %)"], y, tr, L)
    # ---- OTE con giros de 5 min
    T5, O5, H5, L5, C5, V5, TB5, fin5 = B.velas5(t, o, h, l, c, v, tb)
    n5 = len(C5)
    sh_v, sh_k, sl_v, sl_k = np.full(n5, np.nan), np.full(n5, -1), np.full(n5, np.nan), np.full(n5, -1)
    a_sh, a_shk, a_sl, a_slk = np.nan, -1, np.nan, -1
    for k in range(4, n5):
        g = k - 2
        if H5[g] > H5[g - 1] and H5[g] > H5[g - 2] and H5[g] >= H5[g + 1] and H5[g] >= H5[g + 2]:
            a_sh, a_shk = H5[g], g
        if L5[g] < L5[g - 1] and L5[g] < L5[g - 2] and L5[g] <= L5[g + 1] and L5[g] <= L5[g + 2]:
            a_sl, a_slk = L5[g], g
        sh_v[k], sh_k[k], sl_v[k], sl_k[k] = a_sh, a_shk, a_sl, a_slk
    j5 = np.searchsorted(fin5, i, side="right") - 1
    ote = np.full(len(td), 2, int)
    rango = sh_v[j5] - sl_v[j5]
    sube_ult = sh_k[j5] > sl_k[j5]
    r_up = (sh_v[j5] - c[i]) / np.maximum(rango, 1e-9)
    r_dn = (c[i] - sl_v[j5]) / np.maximum(rango, 1e-9)
    ote[(sube_ult) & (r_up >= 0.62) & (r_up <= 0.79)] = 0
    ote[(~sube_ult) & (r_dn >= 0.62) & (r_dn <= 0.79)] = 1
    L.append("")
    L.append("ICT · OTE (retroceso de 62-79 % del último tramo de 5 min):")
    evaluar("OTE", ote, ["OTE de compra (tramo al alza)", "OTE de venta (tramo a la baja)", "sin OTE"], y, tr, L)
    # ---- SMT con ETH
    te, oe, he, le, ce, ve, tbe = B.cargar("ETHUSDT")
    ie = np.searchsorted(te, td - 60)
    ok = (ie < len(te)) & (te[np.minimum(ie, len(te) - 1)] == td - 60)
    def barre(hh, ll, idx):
        H60 = np.r_[np.full(15, np.nan), sliding_window_view(hh, 60).max(axis=1)[:-15] if len(hh) > 75 else []]
        H60 = np.r_[np.full(59, np.nan), H60][: len(hh)]
        L60 = np.r_[np.full(15, np.nan), sliding_window_view(ll, 60).min(axis=1)[:-15]]
        L60 = np.r_[np.full(59, np.nan), L60][: len(ll)]
        h15 = np.r_[np.full(14, np.nan), sliding_window_view(hh, 15).max(axis=1)]
        l15 = np.r_[np.full(14, np.nan), sliding_window_view(ll, 15).min(axis=1)]
        return h15[idx] > H60[idx], l15[idx] < L60[idx]
    hb, lb_ = barre(h, l, i)
    he_, le_ = barre(he, le, np.minimum(ie, len(te) - 1))
    smt = np.full(len(td), 2, int)
    smt[ok & (hb ^ he_) & ~(lb_ ^ le_)] = 0
    smt[ok & (lb_ ^ le_) & ~(hb ^ he_)] = 1
    L.append("")
    L.append("ICT · divergencia SMT con ETH (uno barre el extremo de la hora previa y el otro no):")
    evaluar("SMT", smt, ["SMT en máximos", "SMT en mínimos", "sin SMT"], y, tr, L)
    # ---- libro de órdenes
    L.append("")
    lb = libro(td.astype(float), sim)
    if lb is None:
        L.append("LIBRO DE ÓRDENES: todavía no hay archivos bookDepth descargados.")
    else:
        L.append(f"LIBRO DE ÓRDENES (bookDepth de Binance, {lb['n']:,} decisiones con foto; entrenamiento = 2023):".replace(",", "."))
        tr_l = tr.copy()
        t23 = dt.datetime(2023, 1, 1, tzinfo=dt.timezone.utc).timestamp()
        tr_l[(tr == 0) & (td < t23)] = -1  # sin libro antes de 2023
        for clave, nom in ((0.2, "deseq. ±0,2 %"), (1.0, "deseq. ±1 %"), (5.0, "deseq. ±5 %"), ("d1", "cambio ±1 % 10 min")):
            x = lb[clave]
            entreno = (tr_l == 0) & ~np.isnan(x)
            if entreno.sum() < 1000:
                L.append(f"  {nom}: sin datos suficientes en el entrenamiento ({int(entreno.sum())}); Binance lo publica desde después")
                continue
            est, cortes = terciles(x, entreno)
            L.append(f"  {nom}: cortes de entrenamiento {es(cortes[0], 3)} y {es(cortes[1], 3)} (positivo = más compras en el libro)")
            evaluar(nom, est, ["tercio bajo (más ventas)", "tercio medio", "tercio alto (más compras)"], y, tr_l, L)
    os.makedirs(SALIDA, exist_ok=True)
    texto = "\n".join(L)
    open(os.path.join(SALIDA, f"c6_{sim}.txt"), "w", encoding="utf-8").write(texto + "\n")
    print(texto)


if __name__ == "__main__":
    main()
