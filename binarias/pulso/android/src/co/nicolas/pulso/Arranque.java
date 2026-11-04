package co.nicolas.pulso;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Al encender el teléfono o al actualizar la app, Pulso vuelve a arrancar solo. */
public class Arranque extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        ctx.startForegroundService(new Intent(ctx, Servicio.class));
    }
}
