//! Pulso BTC (31/10/2026): avisos de voz del Bitcoin a su Telegram, todo por Tor y sin librerías externas.
//!
//! - Cada 3 h (al empezar los bloques de 0, 3, 6… UTC) manda el contexto: 3 h, 5 h, 3 meses y los últimos 15 min.
//! - En tiempo real, si desde el último aviso cae 1.200 dólares o sube 3.000, avisa al momento.
//! - Cada aviso va como nota de voz (Salomé, la misma de su equipo), con la gráfica de las últimas 3 h y un botón al
//!   gráfico en vivo de TradingView.
//! - Toda conexión sale por Tor (127.0.0.1:9050). El HTTPS lo hace curl; la voz, el edge-tts de voice-claude, al que este
//!   programa le abre un puente CONNECT→SOCKS5 que solo deja pasar al servicio de voz de Microsoft.
//! - La clave del bot se lee al enviar y se le pasa a curl por la entrada estándar: no aparece en la lista de procesos
//!   ni en el registro.
//!
//! Uso: pulso            (servicio)
//!      pulso prueba     (manda un informe ahora y sale)
use std::collections::VecDeque;
use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const TOR_PC: &str = "127.0.0.1:9050";

/// Dirección SOCKS de Tor: la del PC, o la que le da la app del teléfono (PULSO_TOR).
fn tor() -> String {
    std::env::var("PULSO_TOR").unwrap_or_else(|_| TOR_PC.to_string())
}

/// «completo» (todo), «centinela» (solo los avisos del centinela, cuando el teléfono hace lo demás) o «telefono».
fn modo() -> String {
    std::env::var("PULSO_MODO").ok()
        .or_else(|| fs::read_to_string(casa().join(".pulso/modo")).ok())
        .map(|x| x.trim().to_string()).filter(|x| !x.is_empty())
        .unwrap_or_else(|| "completo".into())
}
const PUENTE: &str = "127.0.0.1:9077";
const VOZ_HOST: &str = "speech.platform.bing.com:443";
const CAIDA: f64 = 1200.0;
const SUBIDA: f64 = 3000.0;
const BLOQUE: u64 = 3 * 3600;
const COL: i64 = -5 * 3600;
const PYTHON: &str = "/mnt/c/Users/ni109/AppData/Local/Programs/Python/Python311/python.exe";
const VOZ_PY: &str = r"C:\Users\ni109\Ingresos\pulso-btc\voz.py";
const AUDIO_WIN: &str = r"C:\Users\ni109\Ingresos\pulso-btc\audio\aviso.mp3";
const AUDIO_WSL: &str = "/mnt/c/Users/ni109/Ingresos/pulso-btc/audio/aviso.mp3";
const TRADINGVIEW: &str = "https://es.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT";

const CENT_ESTADO: &str = "/mnt/c/Users/ni109/Ingresos/binarias-papel/estado.json";
const CENT_APUESTAS: &str = "/mnt/c/Users/ni109/Ingresos/binarias-papel/apuestas.jsonl";
const CADA_NOTICIAS: u64 = 10 * 60;
const LATIDO_MAX: f64 = 600.0;
const ESCALON: f64 = 5000.0;

static CIRCUITO: AtomicU64 = AtomicU64::new(0);

// ---------------------------------------------------------------- JSON mínimo (para leer al centinela)

#[derive(Debug, Clone)]
enum Json {
    Nulo,
    Bool(bool),
    Num(f64),
    Txt(String),
    Lista(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    fn leer(s: &str) -> Option<Json> {
        let b = s.as_bytes();
        let mut i = 0;
        let v = valor(b, &mut i)?;
        Some(v)
    }
    fn get(&self, k: &str) -> Option<&Json> {
        match self {
            Json::Obj(v) => v.iter().find(|x| x.0 == k).map(|x| &x.1),
            _ => None,
        }
    }
    fn num(&self, k: &str) -> Option<f64> {
        match self.get(k)? {
            Json::Num(n) => Some(*n),
            Json::Bool(b) => Some(if *b { 1.0 } else { 0.0 }),
            _ => None,
        }
    }
    fn txt(&self, k: &str) -> Option<&str> {
        match self.get(k)? {
            Json::Txt(s) => Some(s),
            _ => None,
        }
    }
}

fn blancos(b: &[u8], i: &mut usize) {
    while *i < b.len() && (b[*i] as char).is_ascii_whitespace() {
        *i += 1;
    }
}

fn cadena(b: &[u8], i: &mut usize) -> Option<String> {
    *i += 1;
    let mut out = Vec::new();
    while *i < b.len() {
        match b[*i] {
            b'"' => {
                *i += 1;
                return String::from_utf8(out).ok();
            }
            b'\\' => {
                *i += 1;
                match *b.get(*i)? {
                    b'n' => out.push(b'\n'),
                    b't' => out.push(b'\t'),
                    b'u' => {
                        let h = std::str::from_utf8(b.get(*i + 1..*i + 5)?).ok()?;
                        let c = char::from_u32(u32::from_str_radix(h, 16).ok()?).unwrap_or('?');
                        let mut buf = [0u8; 4];
                        out.extend_from_slice(c.encode_utf8(&mut buf).as_bytes());
                        *i += 4;
                    }
                    x => out.push(x),
                }
                *i += 1;
            }
            x => {
                out.push(x);
                *i += 1;
            }
        }
    }
    None
}

fn valor(b: &[u8], i: &mut usize) -> Option<Json> {
    blancos(b, i);
    match *b.get(*i)? {
        b'{' => {
            *i += 1;
            let mut v = Vec::new();
            loop {
                blancos(b, i);
                if *b.get(*i)? == b'}' {
                    *i += 1;
                    return Some(Json::Obj(v));
                }
                let k = cadena(b, i)?;
                blancos(b, i);
                *i += 1; // ':'
                let x = valor(b, i)?;
                v.push((k, x));
                blancos(b, i);
                if *b.get(*i)? == b',' {
                    *i += 1;
                }
            }
        }
        b'[' => {
            *i += 1;
            let mut v = Vec::new();
            loop {
                blancos(b, i);
                if *b.get(*i)? == b']' {
                    *i += 1;
                    return Some(Json::Lista(v));
                }
                v.push(valor(b, i)?);
                blancos(b, i);
                if *b.get(*i)? == b',' {
                    *i += 1;
                }
            }
        }
        b'"' => cadena(b, i).map(Json::Txt),
        b't' => {
            *i += 4;
            Some(Json::Bool(true))
        }
        b'f' => {
            *i += 5;
            Some(Json::Bool(false))
        }
        b'n' => {
            *i += 4;
            Some(Json::Nulo)
        }
        b'N' => {
            *i += 3;
            Some(Json::Nulo)
        }
        _ => {
            let ini = *i;
            while *i < b.len() && matches!(b[*i], b'0'..=b'9' | b'-' | b'+' | b'.' | b'e' | b'E') {
                *i += 1;
            }
            std::str::from_utf8(&b[ini..*i]).ok()?.parse().ok().map(Json::Num)
        }
    }
}

fn ahora() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

fn casa() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/home/rojo".into()))
}

fn registro(texto: &str) {
    let t = ahora() as i64 + COL;
    let linea = format!("{} {}\n", hora_txt(t, true), texto);
    let ruta = casa().join(".pulso/registro.log");
    if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(ruta) {
        let _ = f.write_all(linea.as_bytes());
    }
}

/// Fecha y hora de un instante ya pasado a hora de Colombia.
fn hora_txt(t: i64, con_fecha: bool) -> String {
    let dias = t.div_euclid(86400);
    let s = t.rem_euclid(86400);
    let (h, m) = (s / 3600, (s % 3600) / 60);
    if !con_fecha {
        return format!("{}:{:02}", h, m);
    }
    // Días desde 1970 a fecha civil (algoritmo de Howard Hinnant).
    let z = dias + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let mes = if mp < 10 { mp + 3 } else { mp - 9 };
    let anio = yoe + era * 400 + if mes <= 2 { 1 } else { 0 };
    format!("{:02}/{:02}/{} {:02}:{:02}", d, mes, anio, h, m)
}

// ---------------------------------------------------------------- red por Tor

/// GET por Tor con curl; cada petición usa un circuito propio (usuario SOCKS distinto).
fn get(url: &str) -> Option<String> {
    let n = CIRCUITO.fetch_add(1, Ordering::Relaxed);
    let salida = Command::new("curl")
        .args(["-s", "-m", "60", "--socks5-hostname", &format!("pulso{}:x@{}", n % 64, tor()), url])
        .stdin(Stdio::null())
        .output()
        .ok()?;
    if !salida.status.success() {
        return None;
    }
    String::from_utf8(salida.stdout).ok()
}

fn numero_tras(texto: &str, clave: &str) -> Option<f64> {
    let i = texto.find(clave)? + clave.len();
    let resto = &texto[i..];
    let resto = resto.trim_start_matches(|c: char| c == '"' || c == ':' || c == '[' || c == ' ');
    let fin = resto.find(|c: char| !(c.is_ascii_digit() || c == '.')).unwrap_or(resto.len());
    resto[..fin].parse().ok()
}

fn precio() -> Option<f64> {
    if let Some(p) = binance("ticker/price?symbol=BTCUSDT").and_then(|t| numero_tras(&t, "\"price\"")) {
        return Some(p);
    }
    get("https://api.exchange.coinbase.com/products/BTC-USD/ticker").and_then(|t| numero_tras(&t, "\"price\""))
}

/// Binance va directo, sin Tor: rechaza las salidas de Tor (403) y su regla permite la conexión normal con Binance, como
/// hace el centinela. Es el mismo BTCUSDT que él ve en TradingView y en la app.
fn binance(ruta: &str) -> Option<String> {
    let salida = Command::new("curl")
        .args(["-s", "-m", "15", &format!("https://api.binance.com/api/v3/{}", ruta)])
        .stdin(Stdio::null())
        .output()
        .ok()?;
    if !salida.status.success() {
        return None;
    }
    String::from_utf8(salida.stdout).ok().filter(|t| t.starts_with('[') || t.starts_with('{'))
}

/// Vela completa: tiempo de inicio, apertura, máximo, mínimo y cierre.
#[derive(Clone, Copy)]
struct Vela {
    t: u64,
    o: f64,
    h: f64,
    l: f64,
    c: f64,
    v: f64,
}

/// Velas de BTCUSDT de Binance (Coinbase por Tor si Binance no responde), de la más vieja a la más nueva.
fn velas_ohlc(granularidad: u32) -> Vec<Vela> {
    let intervalo = match granularidad { 60 => "1m", 300 => "5m", 3600 => "1h", _ => "1d" };
    let mut v = Vec::new();
    // Binance: [apertura en ms, "apertura", "máximo", "mínimo", "cierre", …]
    if let Some(Json::Lista(filas)) = binance(&format!("klines?symbol=BTCUSDT&interval={}&limit=300", intervalo)).and_then(|t| Json::leer(&t)) {
        for f in &filas {
            if let Json::Lista(c) = f {
                let n = |i: usize| match c.get(i) { Some(Json::Txt(x)) => x.parse::<f64>().ok(), Some(Json::Num(x)) => Some(*x), _ => None };
                if let (Some(t), Some(o), Some(h), Some(l), Some(cc)) = (n(0), n(1), n(2), n(3), n(4)) {
                    v.push(Vela { t: (t / 1000.0) as u64, o, h, l, c: cc, v: n(5).unwrap_or(0.0) });
                }
            }
        }
    }
    if v.is_empty() {
        // Respaldo por Tor: Coinbase ([tiempo, mínimo, máximo, apertura, cierre, volumen]).
        let url = format!("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity={}", granularidad);
        if let Some(t) = get(&url) {
            for fila in t.split(']') {
                let campos: Vec<f64> = fila.trim_start_matches(|c: char| c == ',' || c == '[').split(',')
                    .filter_map(|x| x.trim().parse::<f64>().ok()).collect();
                if campos.len() >= 5 {
                    v.push(Vela { t: campos[0] as u64, l: campos[1], h: campos[2], o: campos[3], c: campos[4], v: campos.get(5).copied().unwrap_or(0.0) });
                }
            }
        }
    }
    v.sort_by_key(|x| x.t);
    v
}

/// Velas (tiempo, cierre), de la más vieja a la más nueva.
fn velas(granularidad: u32) -> Vec<(u64, f64)> {
    velas_ohlc(granularidad).into_iter().map(|x| (x.t, x.c)).collect()
}

fn entidades(s: &str) -> String {
    let s = s.replace("&amp;", "&").replace("&quot;", "\"").replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">");
    let mut out = String::new();
    let mut resto = s.as_str();
    while let Some(i) = resto.find("&#") {
        out.push_str(&resto[..i]);
        let tras = &resto[i + 2..];
        match tras.find(';').and_then(|f| tras[..f].parse::<u32>().ok().and_then(char::from_u32).map(|c| (f, c))) {
            Some((f, c)) => {
                out.push(c);
                resto = &tras[f + 1..];
            }
            None => {
                out.push_str("&#");
                resto = tras;
            }
        }
    }
    out.push_str(resto);
    out
}

const RSS_CRIPTO: &str = "https://news.google.com/rss/search?q=bitcoin+when:1d&hl=es-419&gl=CO&ceid=CO:es-419";
const RSS_BANCOS: &str = "https://news.google.com/rss/search?q=bitcoin+(%22Banco+Mundial%22+OR+%22Reserva+Federal%22+OR+FMI+OR+Fed)+when:2d&hl=es-419&gl=CO&ceid=CO:es-419";

/// Titulares de un RSS de Google Noticias (por Tor), sin el nombre del medio ni el relleno.
fn titulares(url: &str, max: usize) -> Vec<String> {
    let Some(t) = get(url) else { return vec![] };
    let mut v = Vec::new();
    for item in t.split("<item>").skip(1) {
        if let (Some(a), Some(b)) = (item.find("<title>"), item.find("</title>")) {
            let tit = entidades(&item[a + 7..b]);
            let tit = tit.rsplit_once(" - ").map(|x| x.0.to_string()).unwrap_or(tit).trim().to_string();
            if !ruido(&tit) && !v.contains(&tit) {
                v.push(tit);
            }
        }
        if v.len() == max {
            break;
        }
    }
    v
}

fn noticias_n(max: usize) -> Vec<String> {
    titulares(RSS_CRIPTO, max)
}

/// Relleno que no informa sobre el movimiento: guías, definiciones y pronósticos de precio.
fn ruido(t: &str) -> bool {
    let t = t.to_lowercase();
    ["qué es", "que es un", "cómo comprar", "como comprar", "guía", "tutorial", "predicción", "pronóstico", "podría llegar",
     "puede llegar a", "llegará a", "precio de bitcoin (btc)", "precio del bitcoin hoy", "cotización hoy"]
        .iter().any(|x| t.contains(x))
}

/// Tono del titular para el Bitcoin: +1 alcista, −1 bajista, 0 neutro. Lo bajista pesa en el empate
/// («subida de la Fed» sube tasas, y eso presiona al Bitcoin).
fn tono(t: &str) -> i8 {
    let t = t.to_lowercase();
    let alc = ["sube", "subida", "alza", "repunt", "rebot", "recupera", "máximo", "récord", "record", "rally", "compras",
               "entradas", "aprueb", "impulsa", "dispara", "avanza", "gana ", "recorte de tasas", "baja las tasas", "dovish"]
        .iter().filter(|x| t.contains(*x)).count();
    let baj = ["cae", "caída", "cayó", "desplom", "hackeo", "hack", "robo", "ventas", "vende", "salidas", "liquidac",
               "presiona", "presión", "pierde", "retroced", "restrictiv", "hawkish", "tasas altas", "subida de la fed",
               "sube las tasas", "inflación", "miedo", "a la baja"]
        .iter().filter(|x| t.contains(*x)).count();
    if baj > 0 && baj >= alc { -1 } else if alc > 0 { 1 } else { 0 }
}

fn marca(t: &str) -> &'static str {
    match tono(t) { 1 => "alcista", -1 => "bajista", _ => "neutra" }
}

/// Lectura de los titulares contrastada con el precio real de la última hora. Los titulares cuentan lo que ya pasó: si
/// contradicen al precio, se dice que van atrasados en vez de tomarlos como pronóstico.
fn lectura(v: &[String]) -> String {
    let a = v.iter().filter(|x| tono(x) > 0).count() as i64;
    let b = v.iter().filter(|x| tono(x) < 0).count() as i64;
    let noticias = if a > b + 1 { 1 } else if b > a + 1 { -1 } else { 0 };
    let hora: Vec<(u64, f64)> = velas(60);
    let mov = match (hora.len() >= 61).then(|| hora[hora.len() - 1].1 - hora[hora.len() - 61].1) {
        Some(d) => d,
        None => return format!("de {} noticias del día, {} hablan de subidas y {} de caídas", v.len(), a, b),
    };
    let precio = if mov > 0.0 { format!("en la última hora el precio subió {} dólares", miles(mov)) }
                 else { format!("en la última hora el precio bajó {} dólares", miles(mov)) };
    let juicio = match (noticias, mov > 0.0) {
        (0, _) => "las noticias no apuntan a ningún lado; manda el precio".to_string(),
        (1, true) | (-1, false) => "las noticias y el precio van en el mismo sentido".to_string(),
        (n, _) => format!("las noticias hablan sobre todo de {} pero el precio hace lo contrario: van atrasadas, se ignoran",
                          if n > 0 { "subidas" } else { "caídas" }),
    };
    format!("{} ({} noticias del día: {} de subidas y {} de caídas); {}", precio, v.len(), a, b, juicio)
}

const RSS_BM: &str = "https://news.google.com/rss/search?q=%22Banco+Mundial%22+(crecimiento+OR+econom%C3%ADa+OR+previsi%C3%B3n)+when:7d&hl=es-419&gl=CO&ceid=CO:es-419";

/// Impulso del Banco Mundial: su titular más reciente sobre crecimiento, con su dirección. Sin probar como señal de binarias.
fn impulso_bm() -> Option<String> {
    let t = titulares(RSS_BM, 1).into_iter().next()?;
    let b = t.to_lowercase();
    let pos = ["eleva", "mejora", "aumenta", "crecimiento sólido", "acelera", "optimis", "repunte", "al alza"].iter().any(|x| b.contains(x));
    let neg = ["recorta", "rebaja", "reduce", "desaceler", "recesión", "riesgo", "débil", "a la baja", "advierte"].iter().any(|x| b.contains(x));
    let dir = if neg && !pos { "negativo (menos crecimiento, menos apetito por riesgo)" } else if pos && !neg { "positivo (más crecimiento, más apetito por riesgo)" } else { "sin dirección clara" };
    Some(format!("Impulso del Banco Mundial: {}. «{}».", dir, t.trim_end_matches('.')))
}

/// Compradores frente a vendedores con operaciones reales: últimas 1.000 operaciones agregadas de BTCUSDT en Binance.
/// `m` = verdadero si quien compró esperaba en el libro, o sea que la operación la empujó un vendedor (venta agresiva).
fn presion() -> Option<String> {
    let Json::Lista(ops) = Json::leer(&binance("aggTrades?symbol=BTCUSDT&limit=1000")?)? else { return None };
    let (mut compra, mut venta) = (0.0, 0.0);
    for o in &ops {
        let q: f64 = o.txt("q").and_then(|x| x.parse().ok()).unwrap_or(0.0);
        if matches!(o.get("m"), Some(Json::Bool(true))) { venta += q } else { compra += q }
    }
    let total = compra + venta;
    if total <= 0.0 {
        return None;
    }
    let minutos = match (ops.first().and_then(|o| o.num("T")), ops.last().and_then(|o| o.num("T"))) {
        (Some(a), Some(b)) => ((b - a) / 60000.0).round().max(1.0),
        _ => 0.0,
    };
    let pc = 100.0 * compra / total;
    let quien = if pc >= 55.0 { "mandan los compradores" } else if pc <= 45.0 { "mandan los vendedores" } else { "están parejos" };
    Some(format!("Operaciones reales (Binance, últimos {:.0} min): compra agresiva {:.0} %, venta agresiva {:.0} %; {}.",
                 minutos, pc, 100.0 - pc, quien))
}

/// Cierre de la última vela que empezó antes de `t`.
fn cierre_antes(v: &[(u64, f64)], t: u64) -> Option<f64> {
    v.iter().rev().find(|x| x.0 < t).map(|x| x.1)
}

// ---------------------------------------------------------------- puente para la voz

/// Puente HTTP CONNECT → SOCKS5 de Tor, solo hacia el servicio de voz.
fn puente(escucha: TcpListener) {
    for cliente in escucha.incoming().flatten() {
        thread::spawn(move || {
            let _ = atender(cliente);
        });
    }
}

fn atender(mut cliente: TcpStream) -> std::io::Result<()> {
    cliente.set_read_timeout(Some(Duration::from_secs(20)))?;
    let mut cab = Vec::new();
    let mut b = [0u8; 1];
    while !cab.ends_with(b"\r\n\r\n") && cab.len() < 8192 {
        if cliente.read(&mut b)? == 0 {
            return Ok(());
        }
        cab.push(b[0]);
    }
    let cab = String::from_utf8_lossy(&cab);
    let destino = cab.split_whitespace().nth(1).unwrap_or("");
    if !cab.starts_with("CONNECT ") || destino != VOZ_HOST {
        cliente.write_all(b"HTTP/1.1 403 Forbidden\r\n\r\n")?;
        return Ok(());
    }
    let (host, puerto) = destino.rsplit_once(':').unwrap_or((destino, "443"));
    let puerto: u16 = puerto.parse().unwrap_or(443);
    let mut tor = TcpStream::connect(tor())?;
    tor.set_read_timeout(Some(Duration::from_secs(60)))?;
    let usuario = format!("voz{}", CIRCUITO.fetch_add(1, Ordering::Relaxed) % 64);
    tor.write_all(&[5, 1, 2])?;
    let mut r = [0u8; 2];
    tor.read_exact(&mut r)?;
    let mut auth = vec![1, usuario.len() as u8];
    auth.extend_from_slice(usuario.as_bytes());
    auth.extend_from_slice(&[1, b'x']);
    tor.write_all(&auth)?;
    tor.read_exact(&mut r)?;
    if r[1] != 0 {
        return Ok(());
    }
    let mut pet = vec![5, 1, 0, 3, host.len() as u8];
    pet.extend_from_slice(host.as_bytes());
    pet.extend_from_slice(&puerto.to_be_bytes());
    tor.write_all(&pet)?;
    let mut resp = [0u8; 10];
    tor.read_exact(&mut resp)?;
    if resp[1] != 0 {
        cliente.write_all(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")?;
        return Ok(());
    }
    cliente.write_all(b"HTTP/1.1 200 Connection established\r\n\r\n")?;
    cliente.set_read_timeout(None)?;
    tor.set_read_timeout(None)?;
    let (mut c2, mut t2) = (cliente.try_clone()?, tor.try_clone()?);
    let ida = thread::spawn(move || {
        let _ = std::io::copy(&mut c2, &mut t2);
        let _ = t2.shutdown(std::net::Shutdown::Write);
    });
    let _ = std::io::copy(&mut tor, &mut cliente);
    let _ = cliente.shutdown(std::net::Shutdown::Write);
    let _ = ida.join();
    Ok(())
}

// ---------------------------------------------------------------- gráfica (PNG propio)

const ANCHO: usize = 900;
const ALTO: usize = 420;
const PALETA: [[u8; 3]; 8] = [
    [0x13, 0x17, 0x22], // fondo
    [0x2a, 0x2e, 0x39], // rejilla
    [0x26, 0xa6, 0x9a], // sube
    [0xef, 0x53, 0x50], // baja
    [0xd1, 0xd4, 0xdc], // texto
    [0x29, 0x62, 0xff], // referencia (techo y piso largos)
    [0xff, 0xb3, 0x00], // ámbar (techo y piso cortos)
    [0xc0, 0x7c, 0xff], // violeta (horizontales donde el precio se queda)
];

/// Cifras de 3×5 para las etiquetas de precio.
fn cifra(c: char) -> [u8; 5] {
    match c {
        '0' => [7, 5, 5, 5, 7],
        '1' => [2, 6, 2, 2, 7],
        '2' => [7, 1, 7, 4, 7],
        '3' => [7, 1, 7, 1, 7],
        '4' => [5, 5, 7, 1, 1],
        '5' => [7, 4, 7, 1, 7],
        '6' => [7, 4, 7, 5, 7],
        '7' => [7, 1, 1, 1, 1],
        '8' => [7, 5, 7, 5, 7],
        '9' => [7, 5, 7, 1, 7],
        '.' => [0, 0, 0, 0, 2],
        _ => [0; 5],
    }
}

struct Lienzo(Vec<u8>);

impl Lienzo {
    fn punto(&mut self, x: i64, y: i64, c: u8) {
        if x >= 0 && y >= 0 && (x as usize) < ANCHO && (y as usize) < ALTO {
            self.0[y as usize * ANCHO + x as usize] = c;
        }
    }
    fn linea(&mut self, (x0, y0): (i64, i64), (x1, y1): (i64, i64), c: u8, grosor: i64) {
        let pasos = (x1 - x0).abs().max((y1 - y0).abs()).max(1);
        for i in 0..=pasos {
            let x = x0 + (x1 - x0) * i / pasos;
            let y = y0 + (y1 - y0) * i / pasos;
            for dx in 0..grosor {
                for dy in 0..grosor {
                    self.punto(x + dx, y + dy, c);
                }
            }
        }
    }
    fn texto(&mut self, x: i64, y: i64, s: &str, c: u8) {
        let esc = 3;
        for (k, ch) in s.chars().enumerate() {
            let f = cifra(ch);
            for (fy, fila) in f.iter().enumerate() {
                for fx in 0..3 {
                    if fila >> (2 - fx) & 1 == 1 {
                        for a in 0..esc {
                            for b in 0..esc {
                                self.punto(x + (k as i64) * 4 * esc + fx * esc + a, y + fy as i64 * esc + b, c);
                            }
                        }
                    }
                }
            }
        }
    }
}

fn crc32(datos: &[u8]) -> u32 {
    let mut crc = 0xffff_ffffu32;
    for &b in datos {
        crc ^= b as u32;
        for _ in 0..8 {
            crc = if crc & 1 == 1 { (crc >> 1) ^ 0xedb8_8320 } else { crc >> 1 };
        }
    }
    !crc
}

fn trozo(png: &mut Vec<u8>, tipo: &[u8], datos: &[u8]) {
    png.extend_from_slice(&(datos.len() as u32).to_be_bytes());
    let mut c = tipo.to_vec();
    c.extend_from_slice(datos);
    png.extend_from_slice(&c);
    png.extend_from_slice(&crc32(&c).to_be_bytes());
}

/// PNG de paleta con deflate en bloques sin comprimir (válido y sin librerías).
fn png(lienzo: &Lienzo) -> Vec<u8> {
    let mut crudo = Vec::with_capacity((ANCHO + 1) * ALTO);
    for y in 0..ALTO {
        crudo.push(0);
        crudo.extend_from_slice(&lienzo.0[y * ANCHO..(y + 1) * ANCHO]);
    }
    let mut z = vec![0x78, 0x01];
    let bloques: Vec<&[u8]> = crudo.chunks(65535).collect();
    for (i, b) in bloques.iter().enumerate() {
        z.push(if i + 1 == bloques.len() { 1 } else { 0 });
        z.extend_from_slice(&(b.len() as u16).to_le_bytes());
        z.extend_from_slice(&(!(b.len() as u16)).to_le_bytes());
        z.extend_from_slice(b);
    }
    let (mut a, mut b) = (1u32, 0u32);
    for &x in &crudo {
        a = (a + x as u32) % 65521;
        b = (b + a) % 65521;
    }
    z.extend_from_slice(&((b << 16) | a).to_be_bytes());
    let mut out = vec![0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a];
    let mut ihdr = Vec::new();
    ihdr.extend_from_slice(&(ANCHO as u32).to_be_bytes());
    ihdr.extend_from_slice(&(ALTO as u32).to_be_bytes());
    ihdr.extend_from_slice(&[8, 3, 0, 0, 0]);
    trozo(&mut out, b"IHDR", &ihdr);
    trozo(&mut out, b"PLTE", &PALETA.concat());
    trozo(&mut out, b"IDAT", &z);
    trozo(&mut out, b"IEND", &[]);
    out
}

/// Gráfica de las últimas 3 h (velas de 1 min) con la referencia de las alertas.
fn grafica(v: &[(u64, f64)], referencia: f64) -> Vec<u8> {
    let mut l = Lienzo(vec![0; ANCHO * ALTO]);
    let (izq, der, arr, aba) = (20i64, ANCHO as i64 - 150, 20i64, ALTO as i64 - 20);
    for k in 0..=4 {
        let y = arr + (aba - arr) * k / 4;
        l.linea((izq, y), (der, y), 1, 1);
    }
    if v.len() < 2 {
        return png(&l);
    }
    let mut lo = v.iter().map(|x| x.1).fold(f64::MAX, f64::min).min(referencia);
    let mut hi = v.iter().map(|x| x.1).fold(f64::MIN, f64::max).max(referencia);
    let m = ((hi - lo) * 0.05).max(1.0);
    lo -= m;
    hi += m;
    let y_de = |p: f64| aba - ((p - lo) / (hi - lo) * (aba - arr) as f64) as i64;
    let x_de = |i: usize| izq + (i as i64) * (der - izq) / (v.len() as i64 - 1);
    let yr = y_de(referencia);
    let mut x = izq;
    while x < der {
        l.linea((x, yr), ((x + 8).min(der), yr), 5, 2);
        x += 16;
    }
    let color = if v[v.len() - 1].1 >= v[0].1 { 2 } else { 3 };
    for i in 1..v.len() {
        l.linea((x_de(i - 1), y_de(v[i - 1].1)), (x_de(i), y_de(v[i].1)), color, 3);
    }
    let ult = v[v.len() - 1].1;
    l.texto(der + 12, y_de(hi - m) , &format!("{:.0}", hi - m), 4);
    l.texto(der + 12, y_de(lo + m) - 15, &format!("{:.0}", lo + m), 4);
    l.texto(der + 12, (y_de(ult) - 7).clamp(arr + 25, aba - 40), &format!("{:.0}", ult), color);
    png(&l)
}

/// Gráfica de velas japonesas, con los colores de TradingView.
fn grafica_velas(v: &[Vela]) -> Vec<u8> {
    let mut l = Lienzo(vec![0; ANCHO * ALTO]);
    let (izq, der, arr, aba) = (12i64, ANCHO as i64 - 150, 20i64, ALTO as i64 - 20);
    for k in 0..=4 {
        let y = arr + (aba - arr) * k / 4;
        l.linea((izq, y), (der, y), 1, 1);
    }
    if v.is_empty() {
        return png(&l);
    }
    let lo = v.iter().map(|x| x.l).fold(f64::MAX, f64::min);
    let hi = v.iter().map(|x| x.h).fold(f64::MIN, f64::max);
    let m = ((hi - lo) * 0.04).max(1.0);
    let (lo2, hi2) = (lo - m, hi + m);
    let y_de = |p: f64| aba - ((p - lo2) / (hi2 - lo2) * (aba - arr) as f64) as i64;
    let paso = (der - izq) / v.len() as i64;
    let cuerpo = (paso * 7 / 10).max(1);
    for (i, x) in v.iter().enumerate() {
        let color = if x.c >= x.o { 2 } else { 3 };
        let cx = izq + i as i64 * paso + paso / 2;
        l.linea((cx, y_de(x.h)), (cx, y_de(x.l)), color, 1);
        let (ya, yb) = (y_de(x.o.max(x.c)), y_de(x.o.min(x.c)).max(y_de(x.o.max(x.c)) + 1));
        for y in ya..=yb {
            l.linea((cx - cuerpo / 2, y), (cx - cuerpo / 2 + cuerpo, y), color, 1);
        }
    }
    let ult = v[v.len() - 1];
    l.texto(der + 12, y_de(hi), &format!("{:.0}", hi), 4);
    l.texto(der + 12, y_de(lo) - 15, &format!("{:.0}", lo), 4);
    l.texto(der + 12, (y_de(ult.c) - 7).clamp(arr + 25, aba - 40), &format!("{:.0}", ult.c), if ult.c >= ult.o { 2 } else { 3 });
    png(&l)
}

const OPERATIVA: &str = "/mnt/c/Users/ni109/Ingresos/binarias-papel/OPERATIVA.md";
const GIRO: usize = 30;

/// Volumen de las velas de 1 h de BTCUSDT en Binance (cerradas), de la más vieja a la más nueva.
fn volumen_horas() -> Vec<f64> {
    let Some(Json::Lista(filas)) = binance("klines?symbol=BTCUSDT&interval=1h&limit=200").and_then(|t| Json::leer(&t)) else { return vec![] };
    let ahora_ms = ahora() as f64 * 1000.0;
    filas.iter().filter_map(|f| match f {
        Json::Lista(c) => {
            let cierre = match c.get(6) { Some(Json::Num(x)) => *x, _ => return None };
            if cierre > ahora_ms { return None }
            match c.get(5) { Some(Json::Txt(x)) => x.parse().ok(), _ => None }
        }
        _ => None,
    }).collect()
}

/// Su señal de dos velas (t31, líneas largas): en la vela i, +1 si dos verdes seguidas cierran sobre la horizontal del rango
/// (mayor cierre entre 65 y 5 velas antes) y sobre la diagonal de máximos que bajan; −1 si dos rojas cierran bajo el soporte
/// y la diagonal de mínimos que suben; 0 si no.
fn dos_velas(v: &[Vela]) -> Vec<i8> {
    let n = v.len();
    let mut out = vec![0i8; n];
    if n < 150 {
        return out;
    }
    let es_giro = |j: usize, alto: bool| -> bool {
        if j < GIRO || j + GIRO >= n { return false }
        (j - GIRO..=j + GIRO).all(|k| if alto { v[k].h <= v[j].h } else { v[k].l >= v[j].l })
    };
    let diagonal = |i: usize, alto: bool| -> Option<f64> {
        let giros: Vec<usize> = (0..i.saturating_sub(GIRO)).filter(|&j| j + GIRO <= i && es_giro(j, alto)).collect();
        let (&p2, &p1) = (giros.last()?, giros.get(giros.len().checked_sub(2)?)?);
        let (v1, v2) = if alto { (v[p1].h, v[p2].h) } else { (v[p1].l, v[p2].l) };
        if (alto && v2 >= v1) || (!alto && v2 <= v1) { return None }
        Some(v2 + (v2 - v1) / (p2 - p1) as f64 * (i - p2) as f64)
    };
    let sobre = |i: usize| -> bool {
        let techo = v[i - 65..i - 5].iter().map(|x| x.c).fold(f64::MIN, f64::max);
        v[i].c > v[i].o && v[i].c > techo && diagonal(i, true).map(|d| v[i].c > d).unwrap_or(false)
    };
    let bajo = |i: usize| -> bool {
        let piso = v[i - 65..i - 5].iter().map(|x| x.c).fold(f64::MAX, f64::min);
        v[i].c < v[i].o && v[i].c < piso && diagonal(i, false).map(|d| v[i].c < d).unwrap_or(false)
    };
    for i in (n - 20).max(67)..n {
        if sobre(i) && sobre(i - 1) && v[i].c > v[i - 1].c && !sobre(i - 2) {
            out[i] = 1;
        } else if bajo(i) && bajo(i - 1) && v[i].c < v[i - 1].c && !bajo(i - 2) {
            out[i] = -1;
        }
    }
    out
}

/// Estocástico %K(14) suavizado (3) en velas de 5 min cerradas.
fn estocastico() -> Option<f64> {
    let v: Vec<Vela> = velas_ohlc(300).into_iter().filter(|x| x.t + 300 <= ahora()).collect();
    if v.len() < 20 {
        return None;
    }
    let k = |i: usize| -> f64 {
        let ven = &v[i + 1 - 14..=i];
        let (hi, lo) = (ven.iter().map(|x| x.h).fold(f64::MIN, f64::max), ven.iter().map(|x| x.l).fold(f64::MAX, f64::min));
        if hi > lo { 100.0 * (v[i].c - lo) / (hi - lo) } else { 50.0 }
    };
    let n = v.len();
    Some((k(n - 1) + k(n - 2) + k(n - 3)) / 3.0)
}

/// Triángulo en velas de 1 min: máximos de giro que bajan y mínimos que suben, con el precio entre las dos rectas.
fn triangulo(v: &[Vela]) -> bool {
    let n = v.len();
    if n < 150 {
        return false;
    }
    let es_giro = |j: usize, alto: bool| -> bool {
        j >= GIRO && j + GIRO < n && (j - GIRO..=j + GIRO).all(|k| if alto { v[k].h <= v[j].h } else { v[k].l >= v[j].l })
    };
    let recta = |alto: bool| -> Option<f64> {
        let g: Vec<usize> = (0..n).filter(|&j| es_giro(j, alto)).collect();
        let (&p2, &p1) = (g.last()?, g.get(g.len().checked_sub(2)?)?);
        let (a, b) = if alto { (v[p1].h, v[p2].h) } else { (v[p1].l, v[p2].l) };
        if (alto && b >= a) || (!alto && b <= a) { return None }
        Some(b + (b - a) / (p2 - p1) as f64 * (n - 1 - p2) as f64)
    };
    match (recta(true), recta(false)) {
        (Some(t), Some(p)) => t > p && v[n - 1].c < t && v[n - 1].c > p,
        _ => false,
    }
}

/// Lo que él escribió en Centro nocturno en las últimas 3 h (sin tocar la cola del bot: sin offset).
fn opiniones() -> Vec<String> {
    let (Some(token), Some(chat)) = (leer_secreto("telegram-token"), leer_secreto("telegram-chat")) else { return vec![] };
    let n = CIRCUITO.fetch_add(1, Ordering::Relaxed);
    let hijo = Command::new("curl")
        .args(["-s", "-m", "60", "--socks5-hostname", &format!("op{}:x@{}", n % 64, tor()), "-K", "-"])
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn();
    let Ok(mut hijo) = hijo else { return vec![] };
    if let Some(mut e) = hijo.stdin.take() {
        let _ = writeln!(e, "url = \"https://api.telegram.org/bot{}/getUpdates?limit=100\"", token);
    }
    let Some(t) = hijo.wait_with_output().ok().and_then(|o| String::from_utf8(o.stdout).ok()) else { return vec![] };
    let Some(Json::Lista(res)) = Json::leer(&t).and_then(|j| j.get("result").cloned()) else { return vec![] };
    let mut v: Vec<String> = res.iter().filter_map(|u| {
        let m = u.get("message")?;
        let de_el = m.get("chat").and_then(|c| c.num("id")).map(|id| format!("{:.0}", id) == chat).unwrap_or(false);
        let reciente = ahora() as f64 - m.num("date").unwrap_or(0.0) <= 3.0 * 3600.0;
        let txt = m.txt("text")?;
        (de_el && reciente && !txt.starts_with('/')).then(|| txt.trim().to_string())
    }).collect();
    let desde = v.len().saturating_sub(3);
    v.drain(..desde);
    v
}

/// El agente: cada 15 min se consolida con la OPERATIVA.md y los indicativos del momento, y dice si operar o no.
fn agente() {
    loop {
        let t = ahora();
        thread::sleep(Duration::from_secs(900 - t % 900 + 5));
        resumen_agente();
    }
}

fn resumen_agente() {
    {
        let t = ahora();
        let version = fs::read_to_string(std::env::var("PULSO_OPERATIVA").unwrap_or_else(|_| OPERATIVA.to_string())).ok()
            .and_then(|m| m.lines().find(|l| l.starts_with("Versión")).map(|l| l.trim_end_matches('.').to_string()))
            .unwrap_or_else(|| "OPERATIVA.md no encontrada".into());
        let Some(p) = precio() else { return };
        let m1: Vec<Vela> = velas_ohlc(60).into_iter().filter(|x| x.t + 60 <= t).collect();
        let mov = |min: usize| m1.len().checked_sub(min + 1).map(|i| p - m1[i].c);
        let txt_mov = |d: Option<f64>, nombre: &str| match d {
            Some(d) if d > 0.0 => format!("{}: sube {}", nombre, miles(d)),
            Some(d) if d < 0.0 => format!("{}: baja {}", nombre, miles(d)),
            Some(_) => format!("{}: quieto", nombre),
            None => format!("{}: sin dato", nombre),
        };
        let mut favor: Vec<String> = Vec::new();
        let mut contra: Vec<String> = Vec::new();
        let cent = centinela();
        let visible = std::path::Path::new(CENT_ESTADO).exists();
        let vivo = !visible || cent.as_ref().map(|e| ahora() as f64 - e.num("latido").unwrap_or(0.0) <= LATIDO_MAX).unwrap_or(false);
        if !visible {
            favor.push("el centinela corre en la caja T95H y en el teléfono; sus apuestas y su semáforo le llegan por Telegram".into())
        } else if vivo {
            favor.push("el centinela funciona y vigila sus señales".into())
        } else {
            contra.push("el centinela no está funcionando".into())
        }
        let vh = volumen_horas();
        let vol_alto = if vh.len() > 170 {
            let ult = vh[vh.len() - 1];
            let mut previas: Vec<f64> = vh[vh.len() - 169..vh.len() - 1].to_vec();
            previas.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            let med = previas[previas.len() / 2];
            let r = if med > 0.0 { ult / med } else { 1.0 };
            let linea = format!("volumen de BTC en la última hora: {:.0} % de lo normal de la semana", 100.0 * r);
            if r > 1.3 { contra.push(format!("{} (alto: la defensa de BTC dice no operar)", linea)); true } else { favor.push(linea); false }
        } else { false };
        if let Some(pr) = presion() { favor.push(pr.trim_end_matches('.').to_string()) }
        let senal = dos_velas(&m1);
        let reciente = senal.iter().enumerate().rev().take(15).find(|x| *x.1 != 0).map(|(i, d)| (m1[i].t + 60, *d));
        let veredicto = if !vivo {
            "NO OPERAR: el sistema no está vigilando.".to_string()
        } else if vol_alto {
            "BTC: NO OPERAR (volumen alto). ETH: operar solo con la señal del sistema.".to_string()
        } else {
            "OPERAR solo con la señal del sistema: cuando llegue «Apuesta en papel», esa es la entrada. Sin señal, no se fuerza nada.".to_string()
        };
        let candidata = match reciente {
            Some((ts, d)) => format!("\nCANDIDATA (sin entrar al sistema): a las {} apareció su señal de dos velas {} sus líneas. Lo probado es apostar en contra: {} a 10 min (57 % en BTC).",
                                     hora_txt(ts as i64 + COL, false), if d > 0 { "verdes sobre" } else { "rojas bajo" }, if d > 0 { "BAJA" } else { "SUBE" }),
            None => "\nSu señal de dos velas no apareció en los últimos 15 min.".to_string(),
        };
        let mut contexto: Vec<String> = Vec::new();
        if let Some(x) = indice() {
            contexto.push(format!("{} en 10 min (red de una neurona, solo indicativo)", texto_indice(x)));
        }
        if let Some(k) = estocastico() {
            let zona = if k >= 80.0 { " (sobrecompra)" } else if k <= 20.0 { " (sobreventa)" } else { "" };
            contexto.push(format!("estocástico de 5 min: {:.0}{}", k, zona));
        }
        {
            let v = &m1[m1.len().saturating_sub(150)..];
            if let Some((techo, _, _)) = sus_lineas(v) {
                let n = v.len();
                if (n.saturating_sub(15)..n).any(|i| v[i].h >= techo.en(i)) {
                    contexto.push("en los últimos 15 min el precio tocó su línea de techo: su lectura «toca la línea, puede caer» acertó 56 % (BTC) y 58 % (ETH) a 10 min en 2026, pero en 2024-25 no llegó al 54 %".into());
                }
            }
        }
        if triangulo(&m1) {
            contexto.push("el precio está dentro de un triángulo: anuncia movimiento, no su sentido (t32: 50/50)".into());
        }
        let cripto = noticias_n(20);
        if !cripto.is_empty() {
            contexto.push(format!("mercado especulativo: {}", lectura(&cripto)));
        }
        if let Some(bm) = impulso_bm() {
            contexto.push(bm.trim_end_matches('.').to_string());
        }
        let ops = opiniones();
        let suya = if ops.is_empty() {
            String::new()
        } else {
            let dir = ops.iter().map(|o| tono(o) as i32).sum::<i32>();
            let cuadra = match (dir.signum(), mov(15).unwrap_or(0.0) > 0.0) {
                (0, _) => "no marca sentido",
                (1, true) | (-1, false) => "va con lo que hace el precio",
                _ => "va contra lo que hace el precio en los últimos 15 min",
            };
            format!("\nSu lectura (análisis humano, se tiene en cuenta): «{}». {}.", ops.join(" / "), cuadra)
        };
        let titulo = format!("Resumen del agente, {}", hora_txt(t as i64 + COL, false));
        let texto = format!("Precio: {} dólares. {}. {}.\nVeredicto: {}{}{}\nA favor: {}.\nEn contra: {}.\nContexto (sin decidir con él): {}.\n(Consolidado con {}.)",
                            miles(p), txt_mov(mov(15), "15 min"), txt_mov(mov(60), "1 hora"), veredicto, candidata, suya,
                            if favor.is_empty() { "nada".into() } else { favor.join("; ") },
                            if contra.is_empty() { "nada".into() } else { contra.join("; ") },
                            if contexto.is_empty() { "nada".into() } else { contexto.join("; ") }, version);
        if std::env::args().nth(1).as_deref() == Some("agente") {
            println!("{}
{}", titulo, texto);
        }
        avisar_corto(&titulo, &texto, "agente");
    }
}

/// Cada 30 s, un mensaje de solo texto con el precio de Binance y cuánto se movió desde el anterior (sin voz, para que
/// llegue enseguida). Alineado a los segundos 0 y 30 de cada minuto.
fn tic() {
    let mut antes: Option<f64> = None;
    loop {
        let t = ahora();
        thread::sleep(Duration::from_secs(30 - t % 30));
        let Some(p) = precio() else { continue };
        let cambio = match antes {
            Some(a) if p > a => format!(" (▲ {} en 30 s)", miles(p - a)),
            Some(a) if p < a => format!(" (▼ {} en 30 s)", miles(p - a)),
            Some(_) => " (igual)".to_string(),
            None => String::new(),
        };
        antes = Some(p);
        let ind = indice().map(|x| format!(" · {}", texto_indice(x))).unwrap_or_default();
        telegram("sendMessage", &[("text", format!("Bitcoin dólar: {}{}{}", miles(p), cambio, ind))]);
    }
}

/// Cada 5 min, la gráfica de velas de 5 min; cada hora, la de 1 h. Con texto y nota de voz.
fn capturas() {
    let mut ultimo5 = ahora() / 300;
    let mut ultimo60 = ahora() / 3600;
    loop {
        thread::sleep(Duration::from_secs(5));
        let t = ahora();
        // 25 s de margen para que Coinbase ya tenga cerrada la vela.
        if (t - 25) / 300 == ultimo5 {
            continue;
        }
        ultimo5 = (t - 25) / 300;
        let hora_llena = (t - 25) / 3600 != ultimo60;
        if hora_llena {
            ultimo60 = (t - 25) / 3600;
        }
        mandar_velas(300, t);
        if hora_llena {
            mandar_velas(3600, t);
        }
    }
}

/// Una gráfica de velas cerradas (5 min o 1 h) con su texto y su nota de voz.
fn mandar_velas(seg: u32, t: u64) {
    let nombre = if seg == 300 { "5 minutos" } else { "1 hora" };
    let cerradas: Vec<Vela> = velas_ohlc(seg).into_iter().filter(|x| x.t + seg as u64 <= t).collect();
    let v = &cerradas[cerradas.len().saturating_sub(72)..];
    if v.len() < 7 {
        registro(&format!("capturas: sin velas de {}", nombre));
        return;
    }
    let ult = v[v.len() - 1];
    let d = ult.c - ult.o;
    let d6 = ult.c - v[v.len() - 6].o;
    let rumbo = if d6 > 0.0 && d > 0.0 { "Va subiendo." } else if d6 < 0.0 && d < 0.0 { "Va cayendo." } else { "Sin rumbo claro." };
    let titulo = format!("Bitcoin en velas de {}, {}", nombre, hora_txt((ult.t + seg as u64) as i64 + COL, false));
    let texto = format!("Precio ahora: {} dólares. La última vela de {} cerró {} {} {} dólares. En las últimas 6 velas {} {} dólares. {}",
                        miles(precio().unwrap_or(ult.c)), nombre, if d >= 0.0 { "al alza:" } else { "a la baja:" },
                        if d >= 0.0 { "subió" } else { "bajó" }, miles(d), if d6 >= 0.0 { "subió" } else { "bajó" }, miles(d6), rumbo);
    let texto = match presion() { Some(pr) => format!("{} {}", texto, pr), None => texto };
    let ruta = casa().join(format!(".pulso/velas_{}.png", seg));
    let _ = fs::write(&ruta, grafica_velas(v));
    let boton = format!("{{\"inline_keyboard\":[[{{\"text\":\"Gráfico en vivo (TradingView)\",\"url\":\"{}\"}}]]}}", TRADINGVIEW);
    let foto = telegram("sendPhoto", &[("photo", format!("@{}", ruta.display())), ("caption", format!("{}\n\n{}", titulo, texto)),
                                       ("reply_markup", boton)]);
    let v_ok = mandar_voz(&format!("{}. {}", titulo, texto), "velas");
    registro(&format!("captura {} · foto {} · voz {}", nombre, foto, v_ok));
}

// ---------------------------------------------------------------- sus líneas (como las traza él)

/// Una recta sobre las velas: precio en la vela `i0` y pendiente por vela.
#[derive(Clone, Copy)]
struct Recta {
    i0: usize,
    p0: f64,
    pend: f64,
}

impl Recta {
    fn en(&self, i: usize) -> f64 {
        self.p0 + self.pend * (i as f64 - self.i0 as f64)
    }
}

/// Sus líneas sobre las velas de 1 min cerradas: el techo nace en la punta más alta y baja tocando los máximos siguientes
/// sin cortarlos; el piso nace en el mínimo más bajo y sube tocando los mínimos siguientes; la horizontal es el nivel donde el
/// precio se queda (mediana de los cierres de la última hora). Se trazan sin las 2 últimas velas, que son las que la rompen.
fn sus_lineas(v: &[Vela]) -> Option<(Recta, Recta, f64)> {
    let n = v.len();
    if n < 60 {
        return None;
    }
    let base = &v[..n - 2];
    let m = base.len();
    let ip = (0..m).max_by(|&a, &b| base[a].h.partial_cmp(&base[b].h).unwrap_or(std::cmp::Ordering::Equal))?;
    let iv = (0..m).min_by(|&a, &b| base[a].l.partial_cmp(&base[b].l).unwrap_or(std::cmp::Ordering::Equal))?;
    if ip + 5 >= m || iv + 5 >= m {
        return None;
    }
    let pend_t = (ip + 3..m).map(|j| (base[j].h - base[ip].h) / (j - ip) as f64).fold(f64::MIN, f64::max);
    let pend_p = (iv + 3..m).map(|j| (base[j].l - base[iv].l) / (j - iv) as f64).fold(f64::MAX, f64::min);
    let mut cierres: Vec<f64> = base[m.saturating_sub(60)..].iter().map(|x| x.c).collect();
    cierres.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let horizontal = cierres[cierres.len() / 2];
    Some((Recta { i0: ip, p0: base[ip].h, pend: pend_t.min(0.0) }, Recta { i0: iv, p0: base[iv].l, pend: pend_p.max(0.0) }, horizontal))
}

/// Las seis líneas (04/11/2026, pedido suyo: «que haga seis líneas»), sobre las mismas velas que `sus_lineas`:
/// techo y piso largos (los de siempre); techo y piso cortos, «desde el inicio de cada caída» (su comentario del 31/10): nacen
/// en el último máximo (o mínimo) de giro, con 3 velas a cada lado, distinto del extremo y cuyo tramo duró 6 velas o más;
/// bajan (o suben) tocando los máximos (o mínimos) siguientes sin cortarlos y, si el precio ya rompió ese tramo, se dibujan
/// solo hasta donde lo rompió. Las dos horizontales van donde el precio se queda arriba y abajo (el nivel con más cierres en
/// el 40 % alto y en el 40 % bajo del rango). La lectura y el DISPARO siguen con las largas y la horizontal del medio, como
/// se probaron (t31); las demás son para mirar.
#[derive(Clone, Copy)]
struct Seis {
    techo: Recta,
    piso: Recta,
    techo_c: Option<(Recta, usize)>, // (recta, vela donde se rompió; usize::MAX si sigue viva)
    piso_c: Option<(Recta, usize)>,
    arriba: f64,
    abajo: f64,
    medio: f64,
}

/// Tramo corto desde el giro `j`: para un techo, hasta el primer máximo que lo supere; para un piso, hasta el primer
/// mínimo que lo perfore. Devuelve la recta y la vela de la ruptura (usize::MAX si sigue viva).
fn tramo_corto(base: &[Vela], j: usize, techo: bool) -> Option<(Recta, usize)> {
    let m = base.len();
    let alto = |k: usize| if techo { base[k].h } else { -base[k].l };
    let fin = (j + 1..m).find(|&k| alto(k) > alto(j)).unwrap_or(m);
    if fin < j + 6 {
        return None;
    }
    let pend = (j + 3..fin).map(|k| (alto(k) - alto(j)) / (k - j) as f64).fold(f64::MIN, f64::max).min(0.0);
    let roto = if fin < m { fin } else { usize::MAX };
    Some(if techo { (Recta { i0: j, p0: base[j].h, pend }, roto) } else { (Recta { i0: j, p0: base[j].l, pend: -pend }, roto) })
}

fn seis_lineas(v: &[Vela]) -> Option<Seis> {
    let (techo, piso, medio) = sus_lineas(v)?;
    let base = &v[..v.len() - 2];
    let m = base.len();
    let corto = |es_techo: bool, extremo: usize| {
        let alto = |k: usize| if es_techo { base[k].h } else { -base[k].l };
        (3..m.saturating_sub(3))
            .rev()
            .filter(|&j| j != extremo && (j - 3..=j + 3).all(|k| alto(k) <= alto(j)))
            .find_map(|j| tramo_corto(base, j, es_techo))
    };
    let (techo_c, piso_c) = (corto(true, techo.i0), corto(false, piso.i0));
    let lo = base.iter().map(|x| x.c).fold(f64::MAX, f64::min);
    let hi = base.iter().map(|x| x.c).fold(f64::MIN, f64::max);
    let ancho = ((hi - lo) / 40.0).max(1e-9);
    let mut cajas = [0usize; 40];
    let mut sumas = [0f64; 40];
    for x in base {
        let k = (((x.c - lo) / ancho) as usize).min(39);
        cajas[k] += 1;
        sumas[k] += x.c;
    }
    let nivel = |rango: std::ops::Range<usize>| -> f64 {
        let k = rango.clone().max_by_key(|&k| cajas[k]).unwrap_or(rango.start);
        if cajas[k] > 0 { sumas[k] / cajas[k] as f64 } else { lo + ancho * (k as f64 + 0.5) }
    };
    Some(Seis { techo, piso, techo_c, piso_c, arriba: nivel(24..40), abajo: nivel(0..16), medio })
}

/// Gráfica de velas de 1 min con las seis líneas: techo y piso largos en azul, cortos en ámbar y las dos horizontales
/// donde el precio se queda, en violeta punteado.
fn grafica_lineas(v: &[Vela], s: &Seis) -> Vec<u8> {
    let mut l = Lienzo(vec![0; ANCHO * ALTO]);
    let (izq, der, arr, aba) = (12i64, ANCHO as i64 - 150, 20i64, ALTO as i64 - 20);
    let n = v.len();
    let extra = 20usize; // velas de espacio a la derecha para ver hacia dónde van las líneas
    let total = n + extra;
    let mut lo = v.iter().map(|x| x.l).fold(f64::MAX, f64::min);
    let mut hi = v.iter().map(|x| x.h).fold(f64::MIN, f64::max);
    let (lo_v, hi_v) = (lo, hi);
    let hasta = |fin: usize| if fin == usize::MAX { total - 1 } else { fin };
    let rectas: Vec<(Recta, u8, usize)> = [
        Some((s.techo, 5, total - 1)),
        Some((s.piso, 5, total - 1)),
        s.techo_c.map(|(r, fin)| (r, 6, hasta(fin))),
        s.piso_c.map(|(r, fin)| (r, 6, hasta(fin))),
    ]
    .into_iter()
    .flatten()
    .collect();
    for &(r, _, fin) in &rectas {
        for i in [r.i0, fin.min(n - 1), fin] {
            let p = r.en(i);
            if p.is_finite() && (p - v[n - 1].c).abs() < (hi_v - lo_v) * 1.5 {
                lo = lo.min(p);
                hi = hi.max(p);
            }
        }
    }
    let m = ((hi - lo) * 0.04).max(1.0);
    let (lo2, hi2) = (lo - m, hi + m);
    let y_de = |p: f64| aba - ((p - lo2) / (hi2 - lo2) * (aba - arr) as f64) as i64;
    let paso = ((der - izq) as f64 / total as f64).max(1.0);
    let x_de = |i: usize| izq + (i as f64 * paso + paso / 2.0) as i64;
    let cuerpo = ((paso * 0.7) as i64).max(1);
    for (i, x) in v.iter().enumerate() {
        let color = if x.c >= x.o { 2 } else { 3 };
        let cx = x_de(i);
        l.linea((cx, y_de(x.h)), (cx, y_de(x.l)), color, 1);
        let (ya, yb) = (y_de(x.o.max(x.c)), y_de(x.o.min(x.c)).max(y_de(x.o.max(x.c)) + 1));
        for y in ya..=yb {
            l.linea((cx - cuerpo / 2, y), (cx - cuerpo / 2 + cuerpo, y), color, 1);
        }
    }
    for h in [s.arriba, s.abajo] {
        let yh = y_de(h);
        let mut x = izq;
        while x < der {
            l.linea((x, yh), ((x + 8).min(der), yh), 7, 1);
            x += 14;
        }
    }
    for &(r, c, fin) in &rectas {
        l.linea((x_de(r.i0), y_de(r.en(r.i0))), (x_de(fin), y_de(r.en(fin))), c, 2);
    }
    let ult = v[n - 1];
    let y_ult = (y_de(ult.c) - 7).clamp(arr + 25, aba - 40);
    l.texto(der + 12, y_de(hi_v), &format!("{:.0}", hi_v), 4);
    l.texto(der + 12, y_de(lo_v) - 15, &format!("{:.0}", lo_v), 4);
    l.texto(der + 12, y_ult, &format!("{:.0}", ult.c), if ult.c >= ult.o { 2 } else { 3 });
    let mut ocupados = vec![y_de(hi_v), y_de(lo_v) - 15, y_ult];
    for h in [s.arriba, s.abajo] {
        let y = y_de(h) - 7;
        if ocupados.iter().all(|&o| (o - y).abs() > 18) {
            l.texto(der + 12, y, &format!("{:.0}", h), 7);
            ocupados.push(y);
        }
    }
    png(&l)
}

/// Estado del precio frente a sus líneas y, si las líneas se juntan, en cuántos minutos.
fn lectura_lineas(v: &[Vela], s: &Seis) -> (String, i8) {
    let (techo, piso, horizontal) = (s.techo, s.piso, s.medio);
    let n = v.len();
    let (a, b) = (&v[n - 2], &v[n - 1]);
    let (t1, t2, p1, p2) = (techo.en(n - 2), techo.en(n - 1), piso.en(n - 2), piso.en(n - 1));
    // Su regla: dos velas del mismo color fuera de la línea, la segunda más lejos.
    let rompe = if a.c > a.o && b.c > b.o && a.c > t1 && b.c > t2 && b.c > a.c && b.c > horizontal {
        1
    } else if a.c < a.o && b.c < b.o && a.c < p1 && b.c < p2 && b.c < a.c && b.c < horizontal {
        -1
    } else {
        0
    };
    let junta = if techo.pend < piso.pend {
        let k = (techo.en(n - 1) - piso.en(n - 1)) / (piso.pend - techo.pend);
        if k > 0.0 && k < 600.0 { format!(" Las líneas se juntan en unos {:.0} min: se viene un movimiento.", k) } else { String::new() }
    } else {
        String::new()
    };
    let corto = |r: Option<(Recta, usize)>| match r {
        Some((r, usize::MAX)) => miles(r.en(n - 1)),
        Some(_) => "roto".to_string(),
        None => "sin trazar".to_string(),
    };
    let seis = format!("techo {} (corto {}), piso {} (corto {}), horizontales {} y {}",
                       miles(t2), corto(s.techo_c), miles(p2), corto(s.piso_c), miles(s.arriba), miles(s.abajo));
    let donde = if b.c > t2 {
        format!("por encima del techo; {}", seis)
    } else if b.c < p2 {
        format!("por debajo del piso; {}", seis)
    } else {
        format!("dentro de sus líneas: {}", seis)
    };
    (format!("Precio {} {}.{}", miles(b.c), donde, junta), rompe)
}

/// Cada minuto revisa la ruptura (el disparo) y cada 5 min manda la gráfica de 1 min con sus líneas.
fn vigia_lineas() {
    let mut ultimo_disparo = 0u64;
    loop {
        let t = ahora();
        thread::sleep(Duration::from_secs(60 - t % 60 + 3));
        let t = ahora();
        let todas: Vec<Vela> = velas_ohlc(60).into_iter().filter(|x| x.t + 60 <= t).collect();
        let v = &todas[todas.len().saturating_sub(150)..];
        let Some(seis) = seis_lineas(v) else { continue };
        let (estado, rompe) = lectura_lineas(v, &seis);
        let ruta = casa().join(".pulso/lineas.png");
        let boton = format!("{{\"inline_keyboard\":[[{{\"text\":\"Gráfico en vivo (TradingView)\",\"url\":\"{}\"}}]]}}", TRADINGVIEW);
        let ult_t = v[v.len() - 1].t;
        if rompe != 0 && ult_t > ultimo_disparo + 600 {
            ultimo_disparo = ult_t;
            let titulo = if rompe > 0 { "DISPARO: el Bitcoin rompió sus líneas hacia arriba" } else { "DISPARO: el Bitcoin rompió sus líneas hacia abajo" };
            let texto = format!("{} Dos velas {} seguidas fuera de la línea, como su regla. Lo probado desde 2021 (t31): seguir la ruptura acierta 43 %; apostar {} a 10 min acierta 57 % en BTC (candidata, sin entrar al sistema).",
                                estado, if rompe > 0 { "verdes" } else { "rojas" }, if rompe > 0 { "BAJA" } else { "SUBE" });
            let _ = fs::write(&ruta, grafica_lineas(v, &seis));
            telegram("sendPhoto", &[("photo", format!("@{}", ruta.display())), ("caption", format!("{}\n\n{}", titulo, texto)), ("reply_markup", boton.clone())]);
            let ok = mandar_voz(&format!("{}. {}", titulo, texto), "disparo");
            registro(&format!("disparo {} · voz {}", if rompe > 0 { "arriba" } else { "abajo" }, ok));
        } else if (t / 60) % 5 == 0 {
            let _ = fs::write(&ruta, grafica_lineas(v, &seis));
            let titulo = format!("Sus seis líneas en 1 min, {}", hora_txt(t as i64 + COL, false));
            let leyenda = "Azul: techo y piso largos. Ámbar: techo y piso cortos, desde el inicio de la última caída o subida. Violeta: donde el precio se queda arriba y abajo. El SÍ o NO de cada señal lo manda la caja.";
            let foto = telegram("sendPhoto", &[("photo", format!("@{}", ruta.display())), ("caption", format!("{}\n\n{}\n\n{}", titulo, estado, leyenda)), ("reply_markup", boton)]);
            registro(&format!("líneas en 1 min · foto {}", foto));
        }
    }
}

// ---------------------------------------------------------------- índice de estabilidad (una neurona, t33)

/// Pesos aprendidos con 2021-23 y medidos a ciegas en 2024-26 (t33): con confianza ≥ 0,56 acertó 55,6 % a 10 min.
const INDICE: &str = include_str!("indice.json");

fn lista(j: &Json, k: &str) -> Vec<f64> {
    match j.get(k) {
        Some(Json::Lista(v)) => v.iter().filter_map(|x| if let Json::Num(n) = x { Some(*n) } else { None }).collect(),
        _ => vec![],
    }
}

/// Probabilidad de que el Bitcoin suba en los próximos 10 min, con la misma fórmula que t33 (velas de 1 min cerradas).
fn indice() -> Option<f64> {
    let pesos = Json::leer(INDICE)?;
    let (mu, de, w) = (lista(&pesos, "mu"), lista(&pesos, "de"), lista(&pesos, "w"));
    if mu.len() != 10 || de.len() != 10 || w.len() != 11 {
        return None;
    }
    let ahora_s = ahora();
    let v: Vec<Vela> = velas_ohlc(60).into_iter().filter(|x| x.t + 60 <= ahora_s).collect();
    let n = v.len();
    if n < 260 {
        return None;
    }
    let j = n - 1;
    let lc: Vec<f64> = v.iter().map(|x| x.c.ln()).collect();
    let r1 = |k: usize| lc[k] - lc[k - 1];
    let sig = |m: usize| ((j + 1 - m..=j).map(|k| r1(k) * r1(k)).sum::<f64>() / m as f64).max(1e-12).sqrt();
    let (s15, s60, s240) = (sig(15), sig(60), sig(240));
    let ret = |m: usize| (lc[j] - lc[j - m]) / (s60 * (m as f64).sqrt());
    let ven = &v[j - 239..=j];
    let (hi, lo) = (ven.iter().map(|x| x.h).fold(f64::MIN, f64::max), ven.iter().map(|x| x.l).fold(f64::MAX, f64::min));
    let pos = if hi > lo { (v[j].c - lo) / (hi - lo) } else { 0.5 };
    let suma = |a: usize| v[j + 1 - a..=j].iter().map(|x| x.v).sum::<f64>() / a as f64;
    let vol = ((suma(15) + 1e-9) / (suma(240) + 1e-9)).ln();
    let k5 = |k: usize| {
        let s = &v[k - 69..=k];
        let (hh, ll) = (s.iter().map(|x| x.h).fold(f64::MIN, f64::max), s.iter().map(|x| x.l).fold(f64::MAX, f64::min));
        if hh > ll { (v[k].c - ll) / (hh - ll) } else { 0.5 }
    };
    let est = (k5(j) + k5(j - 5) + k5(j - 10)) / 3.0;
    let hora = ((v[j].t + 60) % 86400) as f64 / 3600.0;
    let x = [ret(1), ret(5), ret(15), ret(60), (s15 / s240).ln(), pos, vol, est,
             (2.0 * std::f64::consts::PI * hora / 24.0).sin(), (2.0 * std::f64::consts::PI * hora / 24.0).cos()];
    let z: f64 = w[0] + (0..10).map(|i| w[i + 1] * (x[i] - mu[i]) / de[i]).sum::<f64>();
    Some(1.0 / (1.0 + (-z).exp()))
}

fn texto_indice(p: f64) -> String {
    let (dir, prob) = if p >= 0.5 { ("sube", p) } else { ("baja", 1.0 - p) };
    let fuerza = if prob >= 0.56 { " (fuerte: 55,6 % de acierto a ciegas)" } else { " (débil: sin ventaja)" };
    format!("índice {:.0} % {}{}", 100.0 * prob, dir, fuerza)
}

// ---------------------------------------------------------------- Telegram y voz

fn leer_secreto(nombre: &str) -> Option<String> {
    fs::read_to_string(casa().join(".gumroad").join(nombre)).ok().map(|s| s.trim().to_string()).filter(|s| !s.is_empty())
}

/// POST multipart a Telegram por Tor. La dirección con la clave va por la entrada estándar de curl (`-K -`).
fn telegram(metodo: &str, campos: &[(&str, String)]) -> bool {
    let (Some(token), Some(chat)) = (leer_secreto("telegram-token"), leer_secreto("telegram-chat")) else {
        registro("falta la clave o el chat de Telegram");
        return false;
    };
    let n = CIRCUITO.fetch_add(1, Ordering::Relaxed);
    let mut args = vec!["-s".to_string(), "-m".into(), "120".into(), "--socks5-hostname".into(), format!("tg{}:x@{}", n % 64, tor()),
                        "-K".into(), "-".into(), "-F".into(), format!("chat_id={}", chat)];
    for (k, v) in campos {
        // Solo los archivos van con -F (que interpreta «@» y «;»); el texto va literal con --form-string.
        let archivo = (*k == "photo" || *k == "voice") && v.starts_with('@');
        args.push(if archivo { "-F" } else { "--form-string" }.into());
        args.push(format!("{}={}", k, v));
    }
    let hijo = Command::new("curl").args(&args).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn();
    let Ok(mut hijo) = hijo else { return false };
    if let Some(mut e) = hijo.stdin.take() {
        let _ = writeln!(e, "url = \"https://api.telegram.org/bot{}/{}\"", token, metodo);
    }
    let salida = hijo.wait_with_output().ok();
    let ok = salida.as_ref().map(|s| String::from_utf8_lossy(&s.stdout).contains("\"ok\":true")).unwrap_or(false);
    if !ok {
        let txt = salida.map(|s| String::from_utf8_lossy(&s.stdout).chars().take(200).collect::<String>()).unwrap_or_default();
        registro(&format!("Telegram {} falló: {}", metodo, txt.replace(&token, "***")));
    }
    ok
}

/// Texto → MP3 con la voz de Salomé, saliendo por el puente (Tor). Cada hilo usa su propio archivo (`nombre`).
fn voz(texto: &str, nombre: &str) -> Option<String> {
    if let Ok(url) = std::env::var("PULSO_VOZ") {
        // En el teléfono la voz la pide la app (Java) a Microsoft por Tor; aquí solo se le pasa el texto.
        let ruta = casa().join(format!(".pulso/{}.mp3", nombre));
        let _ = fs::remove_file(&ruta);
        let hijo = Command::new("curl")
            .args(["-s", "-m", "150", "--noproxy", "*", "--data-binary", "@-", "-H", "Content-Type: text/plain; charset=utf-8", "-o"])
            .arg(&ruta).arg(&url)
            .stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::null()).spawn();
        let Ok(mut hijo) = hijo else { return None };
        if let Some(mut e) = hijo.stdin.take() {
            let _ = e.write_all(texto.as_bytes());
        }
        let ok = hijo.wait().map(|s| s.success()).unwrap_or(false) && fs::metadata(&ruta).map(|m| m.len() > 1000).unwrap_or(false);
        return ok.then(|| ruta.display().to_string());
    }
    let _ = fs::create_dir_all("/mnt/c/Users/ni109/Ingresos/pulso-btc/audio");
    let wsl = AUDIO_WSL.replace("aviso", nombre);
    let win = AUDIO_WIN.replace("aviso", nombre);
    let _ = fs::remove_file(&wsl);
    let st = Command::new(PYTHON)
        .args(["-I", VOZ_PY, &win, &format!("http://{}", PUENTE)])
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .and_then(|mut h| {
            if let Some(mut e) = h.stdin.take() {
                let _ = e.write_all(texto.as_bytes());
            }
            h.wait()
        });
    let ok = st.map(|s| s.success()).unwrap_or(false) && fs::metadata(&wsl).map(|m| m.len() > 1000).unwrap_or(false);
    ok.then_some(wsl)
}

fn mandar_voz(texto: &str, nombre: &str) -> bool {
    voz(texto, nombre).map(|ruta| telegram("sendVoice", &[("voice", format!("@{}", ruta))])).unwrap_or(false)
}

fn enviar(titulo: &str, texto: &str, v: &[(u64, f64)], referencia: f64) {
    let ruta_png = casa().join(".pulso/grafica.png");
    let _ = fs::write(&ruta_png, grafica(v, referencia));
    let boton = format!("{{\"inline_keyboard\":[[{{\"text\":\"Gráfico en vivo (TradingView)\",\"url\":\"{}\"}}]]}}", TRADINGVIEW);
    let completo = format!("{}\n\n{}", titulo, texto);
    let cabe = completo.chars().count() <= 1000;
    let foto_ok = telegram("sendPhoto", &[("photo", format!("@{}", ruta_png.display())),
                                          ("caption", if cabe { completo.clone() } else { titulo.to_string() }),
                                          ("reply_markup", boton)]);
    if !cabe {
        telegram("sendMessage", &[("text", texto.to_string())]);
    }
    let voz_ok = mandar_voz(&format!("{}. {}", titulo, texto), "informe");
    if !voz_ok {
        telegram("sendMessage", &[("text", "(No salió el audio esta vez; el texto va arriba.)".into())]);
    }
    registro(&format!("enviado «{}» · gráfica {} · voz {}", titulo, foto_ok, voz_ok));
}

/// Aviso rápido: el texto sale primero (para que no espere a la voz) y luego la nota de voz.
fn avisar_corto(titulo: &str, texto: &str, audio: &str) {
    let ok = telegram("sendMessage", &[("text", format!("{}\n\n{}", titulo, texto))]);
    let voz_ok = mandar_voz(&format!("{}. {}", titulo, texto), audio);
    registro(&format!("aviso «{}» · texto {} · voz {}", titulo, ok, voz_ok));
}

// ---------------------------------------------------------------- centinela de binarias y noticias en vivo

fn centinela() -> Option<Json> {
    Json::leer(&fs::read_to_string(CENT_ESTADO).ok()?)
}

fn activo(sim: &str) -> &str {
    match sim {
        "BTCUSDT" => "Bitcoin",
        "ETHUSDT" => "Ethereum",
        x => x,
    }
}

fn consolidado(e: &Json) -> String {
    let mut out = String::from("Binarias en papel:");
    if let Some(Json::Obj(cuentas)) = e.get("cuentas") {
        for (nombre, c) in cuentas.iter().filter(|x| x.0 == "REGLA" || x.0 == "CLAUDE") {
            let (w, f) = (c.num("aciertos").unwrap_or(0.0), c.num("fallos").unwrap_or(0.0));
            out.push_str(&format!("\n• Cuenta {}: {} pesos, {} aciertos y {} fallos{}.",
                                  if nombre == "REGLA" { "principal" } else { "Claude" }, miles(c.num("saldo").unwrap_or(0.0)), w, f,
                                  if w + f > 0.0 { format!(" ({:.0} %)", 100.0 * w / (w + f)) } else { String::new() }));
        }
    }
    let latido = e.num("latido").unwrap_or(0.0);
    if ahora() as f64 - latido > LATIDO_MAX {
        out.push_str("\n• Atención: el centinela no está funcionando.");
    }
    out
}

fn clave_apuesta(a: &Json) -> String {
    format!("{}-{}-{}", a.txt("cuenta").unwrap_or("?"), a.txt("sim").unwrap_or("?"), a.num("t").unwrap_or(0.0))
}

/// Apuestas en papel de la cuenta principal: avisa al abrirse y al cerrarse.
struct Vigia {
    abiertas_vistas: Vec<String>,
    lineas_cerradas: usize,
    caido_avisado: bool,
    noticias_vistas: VecDeque<String>,
}

impl Vigia {
    fn nuevo() -> Vigia {
        let ruta = casa().join(".pulso/noticias_vistas");
        let noticias_vistas: VecDeque<String> = fs::read_to_string(&ruta).unwrap_or_default().lines().map(String::from).collect();
        let lineas_cerradas = fs::read_to_string(CENT_APUESTAS).map(|t| t.lines().count()).unwrap_or(0);
        let abiertas_vistas = centinela()
            .and_then(|e| match e.get("abiertas") { Some(Json::Lista(v)) => Some(v.iter().map(clave_apuesta).collect()), _ => None })
            .unwrap_or_default();
        Vigia { abiertas_vistas, lineas_cerradas, caido_avisado: false, noticias_vistas }
    }

    fn revisar_centinela(&mut self) {
        let Some(e) = centinela() else { return };
        let caido = ahora() as f64 - e.num("latido").unwrap_or(0.0) > LATIDO_MAX;
        if caido && !self.caido_avisado {
            avisar_corto("Atención: el centinela de binarias se detuvo", "Lleva más de 10 minutos sin dar señal. Mientras tanto no hay apuestas en papel.", "vigia");
            self.caido_avisado = true;
        } else if !caido && self.caido_avisado {
            avisar_corto("El centinela de binarias volvió", "Ya está funcionando de nuevo.", "vigia");
            self.caido_avisado = false;
        }
        if let Some(Json::Lista(abiertas)) = e.get("abiertas") {
            for a in abiertas {
                let k = clave_apuesta(a);
                if self.abiertas_vistas.contains(&k) {
                    continue;
                }
                self.abiertas_vistas.push(k);
                if a.txt("cuenta") != Some("REGLA") {
                    continue;
                }
                let sube = a.num("dir").unwrap_or(0.0) > 0.0;
                let titulo = format!("Apuesta en papel: {} {} a {} minutos", activo(a.txt("sim").unwrap_or("?")),
                                     if sube { "SUBE" } else { "BAJA" }, a.num("plazo").unwrap_or(10.0));
                let texto = format!("Entrada a las {}, hora de Colombia. Estrategia: {}. Monto: {} pesos. Si la va a hacer en la app, es ahora.",
                                    hora_txt(a.num("t").unwrap_or(0.0) as i64 + COL, false), a.txt("estrategia").unwrap_or("sin nombre"),
                                    miles(a.num("monto").unwrap_or(0.0)));
                avisar_corto(&titulo, &texto, "vigia");
            }
            if self.abiertas_vistas.len() > 200 {
                self.abiertas_vistas.drain(..100);
            }
        }
        let todas = fs::read_to_string(CENT_APUESTAS).unwrap_or_default();
        let lineas: Vec<&str> = todas.lines().collect();
        for l in lineas.iter().skip(self.lineas_cerradas) {
            let Some(a) = Json::leer(l) else { continue };
            if a.txt("cuenta") != Some("REGLA") {
                continue;
            }
            let r = a.num("res").unwrap_or(0.0);
            let titulo = format!("Resultado: {} {}", activo(a.txt("sim").unwrap_or("?")),
                                 if r > 0.0 { "ACERTÓ" } else if r < 0.0 { "FALLÓ" } else { "EMPATE" });
            let g = a.num("ganancia").unwrap_or(0.0);
            let texto = format!("{} {} pesos. Saldo de la cuenta principal: {} pesos.", if g >= 0.0 { "Ganancia de" } else { "Pérdida de" },
                                miles(g), miles(a.num("saldo").unwrap_or(0.0)));
            avisar_corto(&titulo, &texto, "vigia");
        }
        self.lineas_cerradas = lineas.len();
    }

    fn revisar_noticias(&mut self) {
        let cripto = titulares(RSS_CRIPTO, 20);
        let bancos = titulares(RSS_BANCOS, 8);
        let nuevas_c: Vec<&String> = cripto.iter().filter(|n| !self.noticias_vistas.contains(n)).take(5).collect();
        let nuevas_b: Vec<&String> = bancos.iter().filter(|n| !self.noticias_vistas.contains(n)).take(3).collect();
        if nuevas_c.is_empty() && nuevas_b.is_empty() {
            return;
        }
        let primera_vez = self.noticias_vistas.is_empty();
        for n in nuevas_c.iter().chain(nuevas_b.iter()) {
            self.noticias_vistas.push_back((*n).clone());
        }
        while self.noticias_vistas.len() > 400 {
            self.noticias_vistas.pop_front();
        }
        let _ = fs::write(casa().join(".pulso/noticias_vistas"), self.noticias_vistas.iter().cloned().collect::<Vec<_>>().join("\n"));
        if primera_vez {
            return;
        }
        let linea = |n: &&String| format!("• ({}) {}.", marca(n), n.trim_end_matches('.'));
        // Primero el dato real (precio y quién manda); las noticias van después, como contexto.
        let mut texto = format!("Lectura: {}.", lectura(&cripto));
        if let Some(pr) = presion() {
            texto.push_str(&format!("\n{}", pr));
        }
        if !nuevas_c.is_empty() {
            texto.push_str("\nNoticias nuevas (contexto, no pronóstico):\n");
            texto.push_str(&nuevas_c.iter().map(linea).collect::<Vec<_>>().join("\n"));
        }
        if !nuevas_b.is_empty() {
            texto.push_str("\nBancos centrales y entes oficiales (Fed, FMI, Banco Mundial):\n");
            texto.push_str(&nuevas_b.iter().map(linea).collect::<Vec<_>>().join("\n"));
        }
        if let Some(bm) = impulso_bm() {
            texto.push_str(&format!("\n{}", bm));
        }
        avisar_corto("Noticias nuevas del Bitcoin", &texto, "vigia");
    }
}

// ---------------------------------------------------------------- lo que dice

fn miles(x: f64) -> String {
    let n = x.abs().round() as u64;
    let s = n.to_string();
    let mut out = String::new();
    for (i, c) in s.chars().enumerate() {
        if i > 0 && (s.len() - i) % 3 == 0 {
            out.push('.');
        }
        out.push(c);
    }
    out
}

fn cambio(nombre: &str, ahora: f64, antes: Option<f64>) -> (String, i8) {
    match antes {
        Some(a) if a > 0.0 => {
            let d = ahora - a;
            let pct = format!("{:.2}", 100.0 * d.abs() / a).replace('.', ",");
            let verbo = if d > 0.0 { "subió" } else if d < 0.0 { "bajó" } else { "quedó igual," };
            (format!("{}: {} {} dólares ({} %).", nombre, verbo, miles(d), pct), if d > 0.0 { 1 } else if d < 0.0 { -1 } else { 0 })
        }
        _ => (format!("{}: sin dato.", nombre), 0),
    }
}

fn informe(p: f64, referencia: f64, enviar_ya: bool) -> Option<f64> {
    let m1 = velas(60);
    let h1 = velas(3600);
    let d1 = velas(86400);
    let t = ahora();
    let (c3, s3) = cambio("En las últimas 3 horas", p, cierre_antes(&m1, t - 3 * 3600 + 60).or_else(|| cierre_antes(&h1, t - 3 * 3600 + 3600)));
    let (c5, s5) = cambio("En 5 horas", p, cierre_antes(&h1, t - 5 * 3600 + 3600));
    let (c90, s90) = cambio("En 3 meses", p, cierre_antes(&d1, t - 90 * 86400 + 86400));
    let (c15, s15) = cambio("En los últimos 15 minutos", p, cierre_antes(&m1, t - 15 * 60 + 60));
    let ctx = if s3 == s5 && s5 == s90 && s3 != 0 {
        if s3 > 0 { "Contexto: los tres plazos suben; el mercado va al alza." } else { "Contexto: los tres plazos bajan; el mercado va a la baja." }
    } else {
        "Contexto: mixto, los plazos no coinciden."
    };
    let ahora_txt = match s15 { 1 => "Ahora mismo está subiendo.", -1 => "Ahora mismo está cayendo.", _ => "Ahora mismo está quieto." };
    let tcol = t as i64 + COL;
    let titulo = format!("Bitcoin, informe de las {}", hora_txt(tcol, false));
    let mut texto = format!("Precio: {} dólares.\n{}\n{}\n{}\n{}\n{} {}\nAlertas: si cae {} o sube {} dólares desde {}.",
                            miles(p), c3, c5, c90, c15, ctx, ahora_txt, miles(CAIDA), miles(SUBIDA), miles(p));
    if let Some(e) = centinela() {
        texto.push('\n');
        texto.push_str(&consolidado(&e));
    }
    if let Some(pr) = presion() {
        texto.push('\n');
        texto.push_str(&pr);
    }
    let cripto = noticias_n(20);
    if !cripto.is_empty() {
        texto.push_str(&format!("\nLectura: {}.\nNoticias (contexto, no pronóstico):", lectura(&cripto)));
        for n in cripto.iter().take(3) {
            texto.push_str(&format!("\n• ({}) {}.", marca(n), n.trim_end_matches('.')));
        }
    }
    if let Some(n) = titulares(RSS_BANCOS, 1).first() {
        texto.push_str(&format!("\nBancos centrales: ({}) {}.", marca(n), n.trim_end_matches('.')));
    }
    if let Some(bm) = impulso_bm() {
        texto.push_str(&format!("\n{}", bm));
    }
    let ultimas: Vec<(u64, f64)> = m1.iter().copied().filter(|x| x.0 + 3 * 3600 >= t).collect();
    if enviar_ya {
        enviar(&titulo, &texto, &ultimas, referencia);
    }
    Some(p)
}

fn guardar(refe: f64, bloque: u64) {
    let _ = fs::write(casa().join(".pulso/estado"), format!("referencia={}\nbloque={}\n", refe, bloque));
}

fn cargar() -> (Option<f64>, u64) {
    let txt = fs::read_to_string(casa().join(".pulso/estado")).unwrap_or_default();
    let mut r = (None, 0);
    for l in txt.lines() {
        if let Some(v) = l.strip_prefix("referencia=") {
            r.0 = v.parse().ok();
        }
        if let Some(v) = l.strip_prefix("bloque=") {
            r.1 = v.parse().unwrap_or(0);
        }
    }
    r
}

fn main() {
    let _ = fs::create_dir_all(casa().join(".pulso"));
    // El puerto del puente hace también de candado: si ya está ocupado, otra copia corre y esta sale (nunca avisos dobles).
    let Ok(escucha) = TcpListener::bind(PUENTE) else {
        println!("ya hay un pulso corriendo");
        return;
    };
    thread::spawn(move || puente(escucha));
    thread::sleep(Duration::from_millis(300));
    if std::env::args().nth(1).as_deref() == Some("agente") {
        resumen_agente();
        println!("resumen del agente enviado (ver ~/.pulso/registro.log)");
        return;
    }
    if std::env::args().nth(1).as_deref() == Some("indice") {
        println!("{:?}", indice());
        return;
    }
    if std::env::args().nth(1).as_deref() == Some("lineas") {
        let t = ahora();
        let todas: Vec<Vela> = velas_ohlc(60).into_iter().filter(|x| x.t + 60 <= t).collect();
        let v = &todas[todas.len().saturating_sub(150)..];
        if let Some(seis) = seis_lineas(v) {
            let (estado, rompe) = lectura_lineas(v, &seis);
            let _ = fs::write(casa().join(".pulso/lineas.png"), grafica_lineas(v, &seis));
            println!("{} · ruptura {}", estado, rompe);
        }
        return;
    }
    if std::env::args().nth(1).as_deref() == Some("velas") {
        mandar_velas(300, ahora());
        mandar_velas(3600, ahora());
        println!("velas de 5 min y 1 h enviadas (ver ~/.pulso/registro.log)");
        return;
    }
    if std::env::args().nth(1).as_deref() == Some("prueba") {
        if let Some(p) = precio() {
            informe(p, p, true);
            println!("informe de prueba enviado (ver ~/.pulso/registro.log)");
        } else {
            println!("sin precio: Tor o las fuentes no responden");
        }
        return;
    }
    if modo() == "centinela" {
        // El teléfono manda precio, gráficas, alertas, noticias y el agente; el PC solo lo que únicamente él ve.
        registro("pulso en marcha (modo centinela)");
        let mut vigia = Vigia::nuevo();
        loop {
            vigia.revisar_centinela();
            thread::sleep(Duration::from_secs(5));
        }
    }
    registro("pulso en marcha");
    let (mut referencia, mut bloque) = cargar();
    let mut recientes: VecDeque<(u64, f64)> = VecDeque::new();
    let mut escalon: Option<i64> = None;
    let (mut rango30, mut t_rango, mut avisado_alto, mut avisado_bajo) = ((0.0f64, 0.0f64), 0u64, 0u64, 0u64);
    thread::spawn(capturas);
    thread::spawn(tic);
    thread::spawn(agente);
    thread::spawn(vigia_lineas);
    // El vigía (apuestas en papel, centinela y noticias) va en su propio hilo para no esperar al precio.
    thread::spawn(|| {
        let mut vigia = Vigia::nuevo();
        let mut t_noticias = 0u64;
        loop {
            vigia.revisar_centinela();
            if ahora() >= t_noticias + CADA_NOTICIAS {
                t_noticias = ahora();
                vigia.revisar_noticias();
            }
            thread::sleep(Duration::from_secs(5));
        }
    });
    loop {
        if let Some(p) = precio() {
            let t = ahora();
            recientes.push_back((t, p));
            while recientes.front().map(|x| x.0 + 3 * 3600 < t).unwrap_or(false) {
                recientes.pop_front();
            }
            let refe = *referencia.get_or_insert(p);
            // Máximo y mínimo de los 30 días anteriores (velas diarias cerradas), renovados cada hora. Romperlos es la
            // señal objetiva de que empezó un movimiento fuerte; se avisa una vez por día y por lado.
            if t >= t_rango + 3600 {
                let dias: Vec<Vela> = velas_ohlc(86400).into_iter().filter(|x| x.t + 86400 <= t).collect();
                let ult = &dias[dias.len().saturating_sub(30)..];
                if ult.len() == 30 {
                    rango30 = (ult.iter().map(|x| x.h).fold(f64::MIN, f64::max), ult.iter().map(|x| x.l).fold(f64::MAX, f64::min));
                    t_rango = t;
                }
            }
            let hoy = t / 86400;
            if rango30.0 > 0.0 && p > rango30.0 && avisado_alto != hoy {
                avisado_alto = hoy;
                let (ti, tx) = ("El Bitcoin rompe su máximo de 30 días".to_string(),
                                format!("Precio: {} dólares, por encima del máximo de los últimos 30 días ({}). Es la señal de que arrancó una subida fuerte.", miles(p), miles(rango30.0)));
                thread::spawn(move || avisar_corto(&ti, &tx, "rango"));
            } else if rango30.1 > 0.0 && p < rango30.1 && avisado_bajo != hoy {
                avisado_bajo = hoy;
                let (ti, tx) = ("El Bitcoin rompe su mínimo de 30 días".to_string(),
                                format!("Precio: {} dólares, por debajo del mínimo de los últimos 30 días ({}). Es la señal de una caída fuerte.", miles(p), miles(rango30.1)));
                thread::spawn(move || avisar_corto(&ti, &tx, "rango"));
            }
            // Cruce de un múltiplo de 5.000 dólares (80.000, 85.000… 100.000), con 200 dólares de margen para no repetir
            // el aviso si el precio oscila justo sobre el nivel.
            let arriba = ((p - 200.0) / ESCALON).floor() as i64;
            let abajo = ((p + 200.0) / ESCALON).floor() as i64;
            let previo = *escalon.get_or_insert(arriba);
            let nuevo = if arriba > previo { Some(arriba) } else if abajo < previo { Some(abajo) } else { None };
            if let Some(e) = nuevo {
                let sube = e > previo;
                let nivel = if sube { e } else { previo } as f64 * ESCALON;
                let titulo = format!("El Bitcoin cruzó {} los {} dólares", if sube { "hacia arriba" } else { "hacia abajo" }, miles(nivel));
                let texto = format!("Precio ahora: {} dólares.", miles(p));
                thread::spawn(move || avisar_corto(&titulo, &texto, "escalon"));
                escalon = Some(e);
            }
            let b = t / BLOQUE;
            if b != bloque {
                bloque = b;
                informe(p, p, true);
                referencia = Some(p);
                guardar(p, bloque);
            } else if p - refe <= -CAIDA || p - refe >= SUBIDA {
                let sube = p > refe;
                let titulo = if sube { "Alerta: el Bitcoin subió fuerte" } else { "Alerta: el Bitcoin cayó fuerte" };
                let texto = format!("{} {} dólares desde el último aviso. Estaba en {} y ahora está en {} dólares.",
                                    if sube { "Subió" } else { "Cayó" }, miles(p - refe), miles(refe), miles(p));
                let v: Vec<(u64, f64)> = velas(60).into_iter().filter(|x| x.0 + 3 * 3600 >= t).collect();
                enviar(titulo, &texto, if v.len() > 1 { &v } else { recientes.make_contiguous() }, refe);
                referencia = Some(p);
                guardar(p, bloque);
            }
        }
        thread::sleep(Duration::from_secs(5));
    }
}
