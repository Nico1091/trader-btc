package co.nicolas.pulso;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import java.io.File;

/**
 * Recibe del PC (solo por ADB: el receptor exige el permiso DUMP) la clave del bot, el chat y los puentes de Tor, y los
 * guarda en la carpeta privada de la app. Nunca los registra ni los muestra.
 */
public class Claves extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        try {
            File casa = ctx.getFilesDir();
            String token = intent.getStringExtra("token");
            String chat = intent.getStringExtra("chat");
            String puentes = intent.getStringExtra("puentes");
            if (token != null) Servicio.escribir(new File(casa, ".gumroad/telegram-token"), token.trim());
            if (chat != null) Servicio.escribir(new File(casa, ".gumroad/telegram-chat"), chat.trim());
            if (puentes != null) Servicio.escribir(new File(casa, "tor/puentes"), puentes.replace("\\n", "\n"));
            Registro.anotar(ctx, "claves recibidas por ADB: bot " + (token != null) + ", chat " + (chat != null) + ", puentes " + (puentes != null));
            setResultData("ok");
        } catch (Exception e) {
            setResultData("error: " + e.getClass().getSimpleName());
        }
    }
}
