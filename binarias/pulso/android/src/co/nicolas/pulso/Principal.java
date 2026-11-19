package co.nicolas.pulso;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.List;

/** Pantalla mínima: arranca el servicio, pide lo necesario para que Android no lo duerma y muestra el registro. */
public class Principal extends Activity {
    private TextView texto;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != 0) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        if (!pm.isIgnoringBatteryOptimizations(getPackageName())) {
            startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + getPackageName())));
        }
        startForegroundService(new Intent(this, Servicio.class));

        LinearLayout raiz = new LinearLayout(this);
        raiz.setOrientation(LinearLayout.VERTICAL);
        raiz.setPadding(32, 48, 32, 32);
        raiz.setBackgroundColor(0xFF131722);
        Button grafico = new Button(this);
        grafico.setText("Abrir el gráfico en vivo (TradingView)");
        grafico.setOnClickListener(new android.view.View.OnClickListener() {
            @Override
            public void onClick(android.view.View v) {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://es.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT")));
            }
        });
        texto = new TextView(this);
        texto.setTextColor(0xFFD1D4DC);
        texto.setTextSize(13);
        ScrollView sv = new ScrollView(this);
        sv.addView(texto);
        raiz.addView(grafico);
        raiz.addView(sv);
        setContentView(raiz);
    }

    @Override
    protected void onResume() {
        super.onResume();
        StringBuilder s = new StringBuilder("Pulso corre solo en este teléfono, por Tor. Los avisos llegan a Telegram.\n\n");
        s.append(cola(new File(getFilesDir(), ".pulso/registro.log"), 25));
        s.append("\n— capa de la app —\n").append(cola(new File(getFilesDir(), "app.log"), 10));
        texto.setText(s.toString());
    }

    private static String cola(File f, int n) {
        try {
            List<String> l = Files.readAllLines(f.toPath(), StandardCharsets.UTF_8);
            return String.join("\n", l.subList(Math.max(0, l.size() - n), l.size())) + "\n";
        } catch (Exception e) {
            return "(todavía sin registro)\n";
        }
    }
}
