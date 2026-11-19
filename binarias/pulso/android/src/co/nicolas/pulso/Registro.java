package co.nicolas.pulso;

import android.content.Context;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/** Registro de la capa Java (hora de Colombia), junto al del motor en .pulso/registro.log. */
final class Registro {
    private Registro() {
    }

    static synchronized void anotar(Context ctx, String texto) {
        SimpleDateFormat f = new SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.ROOT);
        f.setTimeZone(TimeZone.getTimeZone("America/Bogota"));
        File log = new File(ctx.getFilesDir(), "app.log");
        try (FileOutputStream out = new FileOutputStream(log, true)) {
            out.write((f.format(new Date()) + " " + texto + "\n").getBytes(StandardCharsets.UTF_8));
        } catch (Exception ignorada) {
            // sin registro no se detiene nada
        }
    }
}
