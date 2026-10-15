package com.novasyscom.alberth;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * BOOT RECEIVER — Inicia el servicio de escucha en segundo plano al reiniciar el teléfono.
 */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent != null && (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction()) ||
                               "android.intent.action.QUICKBOOT_POWERON".equals(intent.getAction()))) {
            Intent serviceIntent = new Intent(context, AlberthWakeService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent);
            } else {
                context.startService(serviceIntent);
            }
        }
    }
}
