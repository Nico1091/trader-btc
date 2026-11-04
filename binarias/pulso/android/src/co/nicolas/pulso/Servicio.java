package co.nicolas.pulso;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.IBinder;
import android.os.PowerManager;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Map;

/**
 * Sostiene a Pulso en el teléfono, sin PC: arranca Tor (con su enmascaramiento webtunnel si hay puentes), el servidor de la
 * voz de Salomé y el motor en Rust, y los vuelve a levantar si alguno cae. Todo lo de red de Pulso sale por este Tor, salvo
 * Binance, que va directo como en el PC.
 */
public class Servicio extends Service {
    static final int PUERTO_TOR = 9150;
    static final int PUERTO_VOZ = 9078;
    private static final String CANAL = "pulso";

    private boolean iniciado;
    private Process tor;
    private Process pulso;
    private PowerManager.WakeLock candado;

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (!iniciado) {
            iniciado = true;
            startForeground(1, aviso(), ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
            PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
            candado = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "pulso:servicio");
            candado.acquire();
            new Thread(new Voz(this, PUERTO_VOZ, PUERTO_TOR), "voz").start();
            new Thread(new Runnable() {
                @Override
                public void run() {
                    vigilar();
                }
            }, "vigia").start();
        }
        return START_STICKY;
    }

    private Notification aviso() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(CANAL, "Pulso en marcha", NotificationManager.IMPORTANCE_LOW));
        PendingIntent abrir = PendingIntent.getActivity(this, 0, new Intent(this, Principal.class), PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CANAL)
                .setSmallIcon(R.drawable.icono)
                .setContentTitle("Pulso")
                .setContentText("Vigilando el Bitcoin por Tor; los avisos llegan a Telegram.")
                .setContentIntent(abrir)
                .setOngoing(true)
                .build();
    }

    /** Cada 10 s: Tor vivo, y cuando Tor ya circula, el motor en Rust vivo. */
    private void vigilar() {
        while (true) {
            try {
                if (tor == null || !tor.isAlive()) {
                    tor = arrancarTor();
                }
                if (torListo() && (pulso == null || !pulso.isAlive())) {
                    pulso = arrancarPulso();
                }
            } catch (Exception e) {
                Registro.anotar(this, "vigía: " + e);
            }
            try {
                Thread.sleep(10000);
            } catch (InterruptedException e) {
                return;
            }
        }
    }

    private String nativo(String nombre) {
        return getApplicationInfo().nativeLibraryDir + "/" + nombre;
    }

    private Process arrancarTor() throws Exception {
        File dir = new File(getFilesDir(), "tor");
        new File(dir, "datos").mkdirs();
        StringBuilder rc = new StringBuilder();
        rc.append("SocksPort 127.0.0.1:").append(PUERTO_TOR).append(" IsolateSOCKSAuth\n");
        rc.append("DataDirectory ").append(new File(dir, "datos").getAbsolutePath()).append('\n');
        rc.append("ClientOnly 1\nAvoidDiskWrites 1\n");
        rc.append("Log notice file ").append(new File(dir, "tor.log").getAbsolutePath()).append('\n');
        File puentes = new File(dir, "puentes");
        if (puentes.exists()) {
            rc.append("UseBridges 1\n");
            rc.append("ClientTransportPlugin webtunnel exec ").append(nativo("liblyrebird.so")).append('\n');
            for (String l : new String(Files.readAllBytes(puentes.toPath()), StandardCharsets.UTF_8).split("\n")) {
                if (l.trim().startsWith("Bridge ")) {
                    rc.append(l.trim()).append('\n');
                }
            }
        }
        File torrc = new File(dir, "torrc");
        escribir(torrc, rc.toString());
        new File(dir, "tor.log").delete();
        ProcessBuilder pb = new ProcessBuilder(nativo("libtor.so"), "-f", torrc.getAbsolutePath());
        pb.directory(dir);
        pb.redirectErrorStream(true);
        pb.redirectOutput(new File(dir, "tor.salida"));
        Registro.anotar(this, "Tor arranca" + (puentes.exists() ? " con puentes webtunnel" : ""));
        return pb.start();
    }

    private boolean torListo() {
        File log = new File(getFilesDir(), "tor/tor.log");
        try (Socket s = new Socket()) {
            s.connect(new InetSocketAddress("127.0.0.1", PUERTO_TOR), 2000);
            return log.exists() && new String(Files.readAllBytes(log.toPath()), StandardCharsets.UTF_8).contains("Bootstrapped 100%");
        } catch (Exception e) {
            return false;
        }
    }

    private Process arrancarPulso() throws Exception {
        File casa = getFilesDir();
        File operativa = new File(casa, "OPERATIVA.md");
        try (InputStream in = getAssets().open("OPERATIVA.md"); OutputStream out = new FileOutputStream(operativa)) {
            byte[] b = new byte[8192];
            int n;
            while ((n = in.read(b)) > 0) {
                out.write(b, 0, n);
            }
        }
        ProcessBuilder pb = new ProcessBuilder(nativo("libpulso.so"));
        Map<String, String> env = pb.environment();
        env.put("HOME", casa.getAbsolutePath());
        env.put("PATH", "/system/bin:/system/xbin");
        env.put("PULSO_TOR", "127.0.0.1:" + PUERTO_TOR);
        env.put("PULSO_VOZ", "http://127.0.0.1:" + PUERTO_VOZ + "/");
        env.put("PULSO_MODO", "telefono");
        env.put("PULSO_OPERATIVA", operativa.getAbsolutePath());
        pb.directory(casa);
        pb.redirectErrorStream(true);
        pb.redirectOutput(new File(casa, "pulso.salida"));
        Registro.anotar(this, "motor Rust arranca");
        return pb.start();
    }

    static void escribir(File f, String texto) throws Exception {
        f.getParentFile().mkdirs();
        try (OutputStream out = new FileOutputStream(f)) {
            out.write(texto.getBytes(StandardCharsets.UTF_8));
        }
    }

    @Override
    public void onDestroy() {
        if (pulso != null) pulso.destroy();
        if (tor != null) tor.destroy();
        if (candado != null && candado.isHeld()) candado.release();
        super.onDestroy();
    }
}
