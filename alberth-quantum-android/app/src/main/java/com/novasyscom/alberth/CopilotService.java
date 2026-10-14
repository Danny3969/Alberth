package com.novasyscom.alberth;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioManager;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

public class CopilotService extends Service {

    public static final String ACTION_START_COPILOT = "ACTION_START_COPILOT";
    public static final String ACTION_STOP_COPILOT = "ACTION_STOP_COPILOT";
    private static final String CHANNEL_ID = "alberth_copilot_channel";
    private static final int NOTIFICATION_ID = 2001;

    private PowerManager.WakeLock wakeLock;
    private AudioManager audioManager;
    private boolean isRunning = false;

    @Override
    public void onCreate() {
        super.onCreate();
        audioManager = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP_COPILOT.equals(intent.getAction())) {
            stopCopilotMode();
            stopSelf();
            return START_NOT_STICKY;
        }

        startCopilotMode();
        return START_STICKY;
    }

    private void startCopilotMode() {
        if (isRunning) return;
        isRunning = true;

        // 1. Iniciar servicio en primer plano con notificación continua
        Notification notification = buildNotification();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }

        // 2. Adquirir WakeLock para que la CPU no se congele con la pantalla apagada en el bolsillo
        try {
            PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (powerManager != null && wakeLock == null) {
                wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Alberth:CopilotPocketWakeLock");
                wakeLock.acquire(4 * 60 * 60 * 1000L); // Hasta 4 horas de ruta continua
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        // 3. Enrutar audio al casco / audífonos Bluetooth (Bluetooth SCO)
        try {
            if (audioManager != null) {
                audioManager.setMode(AudioManager.MODE_IN_COMMUNICATION);
                if (audioManager.isBluetoothScoAvailableOffCall()) {
                    audioManager.startBluetoothSco();
                    audioManager.setBluetoothScoOn(true);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void stopCopilotMode() {
        isRunning = false;

        // Liberar WakeLock
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {}
            wakeLock = null;
        }

        // Restaurar modo de audio
        if (audioManager != null) {
            try {
                if (audioManager.isBluetoothScoOn()) {
                    audioManager.setBluetoothScoOn(false);
                    audioManager.stopBluetoothSco();
                }
                audioManager.setMode(AudioManager.MODE_NORMAL);
            } catch (Exception ignored) {}
        }

        stopForeground(true);
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Alberth Copiloto",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Mantiene la escucha manos libres activa en auto y moto.");
            channel.setShowBadge(false);
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildNotification() {
        Intent openAppIntent = new Intent(this, MainActivity.class);
        openAppIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, openAppIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Intent stopIntent = new Intent(this, CopilotService.class);
        stopIntent.setAction(ACTION_STOP_COPILOT);
        PendingIntent stopPendingIntent = PendingIntent.getService(
                this, 1, stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle("🚗 Alberth Modo Copiloto Activo")
                .setContentText("Manos libres en auto y moto · Diga 'Alberth'")
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setOngoing(true)
                .setContentIntent(pendingIntent)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cerrar Copiloto", stopPendingIntent)
                .build();
    }

    @Override
    public void onDestroy() {
        stopCopilotMode();
        super.onDestroy();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
