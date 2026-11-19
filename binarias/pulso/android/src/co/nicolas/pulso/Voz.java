package co.nicolas.pulso;

import android.content.Context;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.text.SimpleDateFormat;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.TimeZone;

import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;

/**
 * La voz de Salomé desde el teléfono: recibe el texto del motor en 127.0.0.1 y lo pide al servicio de voz de Microsoft
 * (el mismo de edge-tts) por Tor, con WebSocket escrito a mano. La ficha Sec-MS-GEC depende solo de la hora (bloques de
 * 5 min); el PC las calcula por adelantado con edge-tts y la app las trae en assets/gec.txt.
 */
class Voz implements Runnable {
    private static final String HOST = "speech.platform.bing.com";
    private static final String TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
    private static final String VOZ = "es-CO-SalomeNeural";
    private static final String UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0";

    private final Context ctx;
    private final int puerto;
    private final int puertoTor;
    private final SecureRandom azar = new SecureRandom();
    private Map<Long, String> fichas;
    private String version = "2-143.0.3650.75";

    Voz(Context ctx, int puerto, int puertoTor) {
        this.ctx = ctx;
        this.puerto = puerto;
        this.puertoTor = puertoTor;
    }

    @Override
    public void run() {
        try (ServerSocket ss = new ServerSocket(puerto, 20, InetAddress.getByName("127.0.0.1"))) {
            while (true) {
                final Socket c = ss.accept();
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        atender(c);
                    }
                }, "voz-peticion").start();
            }
        } catch (Exception e) {
            Registro.anotar(ctx, "voz: no abre el puerto " + puerto + ": " + e);
        }
    }

    private void atender(Socket c) {
        try (Socket cliente = c) {
            DataInputStream in = new DataInputStream(cliente.getInputStream());
            int largo = 0;
            String linea;
            while (!(linea = leerLinea(in)).isEmpty()) {
                if (linea.toLowerCase(Locale.ROOT).startsWith("content-length:")) {
                    largo = Integer.parseInt(linea.substring(15).trim());
                }
            }
            byte[] cuerpo = new byte[largo];
            in.readFully(cuerpo);
            byte[] mp3 = sintetizar(new String(cuerpo, StandardCharsets.UTF_8));
            OutputStream out = cliente.getOutputStream();
            if (mp3.length > 0) {
                out.write(("HTTP/1.1 200 OK\r\nContent-Type: audio/mpeg\r\nContent-Length: " + mp3.length + "\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
                out.write(mp3);
            } else {
                out.write("HTTP/1.1 503 Sin voz\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".getBytes(StandardCharsets.US_ASCII));
            }
            out.flush();
        } catch (Exception e) {
            Registro.anotar(ctx, "voz: " + e);
        }
    }

    private static String leerLinea(InputStream in) throws Exception {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        int x;
        while ((x = in.read()) != -1 && x != '\n') {
            if (x != '\r') b.write(x);
        }
        return b.toString("UTF-8");
    }

    private synchronized String ficha() throws Exception {
        if (fichas == null) {
            fichas = new HashMap<>();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(ctx.getAssets().open("gec.txt"), StandardCharsets.US_ASCII))) {
                version = r.readLine().trim();
                String l;
                while ((l = r.readLine()) != null) {
                    int k = l.indexOf(' ');
                    if (k > 0) fichas.put(Long.parseLong(l.substring(0, k)), l.substring(k + 1));
                }
            }
        }
        long t = System.currentTimeMillis() / 1000;
        String f = fichas.get(t - t % 300);
        if (f == null) throw new IllegalStateException("se acabaron las fichas de voz: hay que renovar gec.txt desde el PC");
        return f;
    }

    private String hexAzar(int bytes) {
        byte[] b = new byte[bytes];
        azar.nextBytes(b);
        StringBuilder s = new StringBuilder();
        for (byte x : b) s.append(String.format(Locale.ROOT, "%02X", x));
        return s.toString();
    }

    private static String escapar(String t) {
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private static String fechaJs() {
        SimpleDateFormat f = new SimpleDateFormat("EEE MMM dd yyyy HH:mm:ss", Locale.US);
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        return f.format(new Date()) + " GMT+0000 (Coordinated Universal Time)";
    }

    byte[] sintetizar(String texto) throws Exception {
        Socket crudo = new Socket(new Proxy(Proxy.Type.SOCKS, new InetSocketAddress("127.0.0.1", puertoTor)));
        crudo.connect(InetSocketAddress.createUnresolved(HOST, 443), 60000);
        crudo.setSoTimeout(60000);
        SSLSocket s = (SSLSocket) ((SSLSocketFactory) SSLSocketFactory.getDefault()).createSocket(crudo, HOST, 443, true);
        try {
            s.startHandshake();
            OutputStream out = s.getOutputStream();
            DataInputStream in = new DataInputStream(s.getInputStream());
            byte[] llave = new byte[16];
            azar.nextBytes(llave);
            String ruta = "/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=" + TOKEN
                    + "&ConnectionId=" + hexAzar(16).toLowerCase(Locale.ROOT)
                    + "&Sec-MS-GEC=" + ficha() + "&Sec-MS-GEC-Version=" + version;
            String pedido = "GET " + ruta + " HTTP/1.1\r\n"
                    + "Host: " + HOST + "\r\n"
                    + "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                    + "Sec-WebSocket-Key: " + Base64.getEncoder().encodeToString(llave) + "\r\n"
                    + "Sec-WebSocket-Version: 13\r\n"
                    + "Pragma: no-cache\r\nCache-Control: no-cache\r\n"
                    + "Origin: chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold\r\n"
                    + "User-Agent: " + UA + "\r\n"
                    + "Accept-Language: en-US,en;q=0.9\r\n"
                    + "Cookie: muid=" + hexAzar(16) + ";\r\n\r\n";
            out.write(pedido.getBytes(StandardCharsets.US_ASCII));
            out.flush();
            String estado = leerLinea(in);
            if (!estado.contains(" 101")) {
                throw new IllegalStateException("el servicio de voz respondió: " + estado);
            }
            while (!leerLinea(in).isEmpty()) {
                // cabeceras de la respuesta
            }
            String fecha = fechaJs();
            enviarTexto(out, "X-Timestamp:" + fecha + "\r\nContent-Type:application/json; charset=utf-8\r\nPath:speech.config\r\n\r\n"
                    + "{\"context\":{\"synthesis\":{\"audio\":{\"metadataoptions\":{\"sentenceBoundaryEnabled\":\"false\",\"wordBoundaryEnabled\":\"false\"},"
                    + "\"outputFormat\":\"audio-24khz-48kbitrate-mono-mp3\"}}}}\r\n");
            String ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
                    + "<voice name='" + VOZ + "'><prosody pitch='+8Hz' rate='-8%' volume='+0%'>" + escapar(texto)
                    + "</prosody></voice></speak>";
            enviarTexto(out, "X-RequestId:" + hexAzar(16).toLowerCase(Locale.ROOT) + "\r\nContent-Type:application/ssml+xml\r\nX-Timestamp:"
                    + fecha + "Z\r\nPath:ssml\r\n\r\n" + ssml);
            ByteArrayOutputStream audio = new ByteArrayOutputStream();
            ByteArrayOutputStream mensaje = new ByteArrayOutputStream();
            int tipo = 0;
            while (true) {
                int b0 = in.readUnsignedByte();
                int b1 = in.readUnsignedByte();
                boolean fin = (b0 & 0x80) != 0;
                int op = b0 & 0x0F;
                long n = b1 & 0x7F;
                if (n == 126) n = in.readUnsignedShort();
                else if (n == 127) n = in.readLong();
                byte[] carga = new byte[(int) n];
                in.readFully(carga);
                if (op == 9) {
                    enviarMarco(out, 0xA, carga);
                    continue;
                }
                if (op == 8) break;
                if (op == 1 || op == 2) {
                    tipo = op;
                    mensaje.reset();
                }
                if (op == 0 || op == 1 || op == 2) mensaje.write(carga);
                if (!fin) continue;
                byte[] m = mensaje.toByteArray();
                if (tipo == 1) {
                    if (new String(m, StandardCharsets.UTF_8).contains("Path:turn.end")) break;
                } else if (tipo == 2 && m.length >= 2) {
                    int hl = ((m[0] & 0xFF) << 8) | (m[1] & 0xFF);
                    if (hl + 2 <= m.length && new String(m, 2, hl, StandardCharsets.UTF_8).contains("Path:audio")) {
                        audio.write(m, 2 + hl, m.length - 2 - hl);
                    }
                }
            }
            return audio.toByteArray();
        } finally {
            s.close();
        }
    }

    private void enviarTexto(OutputStream out, String texto) throws Exception {
        enviarMarco(out, 1, texto.getBytes(StandardCharsets.UTF_8));
    }

    /** Marco de cliente: siempre con máscara, como exige el protocolo. */
    private void enviarMarco(OutputStream out, int op, byte[] datos) throws Exception {
        ByteArrayOutputStream f = new ByteArrayOutputStream();
        f.write(0x80 | op);
        if (datos.length < 126) {
            f.write(0x80 | datos.length);
        } else if (datos.length < 65536) {
            f.write(0x80 | 126);
            f.write(datos.length >> 8);
            f.write(datos.length & 0xFF);
        } else {
            f.write(0x80 | 127);
            for (int i = 7; i >= 0; i--) f.write((int) ((long) datos.length >> (8 * i)) & 0xFF);
        }
        byte[] mascara = new byte[4];
        azar.nextBytes(mascara);
        f.write(mascara);
        for (int i = 0; i < datos.length; i++) f.write(datos[i] ^ mascara[i % 4]);
        out.write(f.toByteArray());
        out.flush();
    }
}
