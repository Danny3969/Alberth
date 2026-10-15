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
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import java.util.ArrayList;
import java.util.Locale;

/**
 * ALBERTH WAKE SERVICE — Servicio Persistente en Primer Plano
 * Escucha continuamente en segundo plano (incluso con pantalla bloqueada o en el bolsillo)
 * para despertar la aplicación al decir "Alberth", "Hola Alberth" o "Estás allí Alberth".
 */
public class AlberthWakeService extends Service {

    public static final String ACTION_START_WAKE = "ACTION_START_WAKE";
    public static final String ACTION_STOP_WAKE = "ACTION_STOP_WAKE";
    public static final String ACTION_PAUSE_LISTENING = "ACTION_PAUSE_LISTENING";
    public static final String ACTION_RESUME_LISTENING = "ACTION_RESUME_LISTENING";

    private static final String CHANNEL_ID = "alberth_wake_channel";
    private static final int NOTIFICATION_ID = 2002;

    private static AlberthWakeService instance = null;

    private PowerManager.WakeLock wakeLock;
    private SpeechRecognizer speechRecognizer;
    private Intent speechIntent;
    private boolean isListening = false;
    private boolean isPaused = false;
    private final Handler handler = new Handler(Looper.getMainLooper());

    public static AlberthWakeService getInstance() {
        return instance;
    }

    public static boolean isRunning() {
        return instance != null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        createNotificationChannel();
        acquireWakeLock();
        initSpeechRecognizer();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            if (ACTION_STOP_WAKE.equals(action)) {
                stopSelf();
                return START_NOT_STICKY;
            } else if (ACTION_PAUSE_LISTENING.equals(action)) {
                pauseListening();
                return START_STICKY;
            } else if (ACTION_RESUME_LISTENING.equals(action)) {
                resumeListening();
                return START_STICKY;
            }
        }

        startForegroundServiceNotification();
        resumeListening();
        return START_STICKY;
    }

    private void acquireWakeLock() {
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null && wakeLock == null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Alberth:WakeServiceLock");
                wakeLock.acquire();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Alberth Escucha en Segundo Plano",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Permite que Alberth se active cuando dice 'Alberth' o 'Hola Alberth'.");
            channel.setShowBadge(false);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    private void startForegroundServiceNotification() {
        Intent openApp = new Intent(this, MainActivity.class);
        openApp.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pi = PendingIntent.getActivity(
                this, 0, openApp,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle("🛡️ Alberth Quantum · Escucha activa")
                .setContentText("Diga 'Alberth', 'Hola Alberth' o 'Estás allí Alberth'")
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setOngoing(true)
                .setContentIntent(pi)
                .build();

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                int type = 0;
                if (androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    type |= ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;
                }
                if (androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED ||
                    androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_COARSE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    type |= ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION;
                }
                if (type != 0) {
                    startForeground(NOTIFICATION_ID, notification, type);
                } else {
                    startForeground(NOTIFICATION_ID, notification);
                }
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
        } catch (SecurityException se) {
            try {
                startForeground(NOTIFICATION_ID, notification);
            } catch (Exception ignored) {}
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void initSpeechRecognizer() {
        handler.post(() -> {
            try {
                if (speechRecognizer != null) {
                    try { speechRecognizer.destroy(); } catch (Exception ignored) {}
                }
                if (!SpeechRecognizer.isRecognitionAvailable(this)) return;

                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
                speechIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
                speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-ES");
                speechIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
                speechIntent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);

                speechRecognizer.setRecognitionListener(new RecognitionListener() {
                    @Override
                    public void onReadyForSpeech(Bundle params) {
                        isListening = true;
                    }

                    @Override
                    public void onBeginningOfSpeech() {}

                    @Override
                    public void onRmsChanged(float rmsdB) {}

                    @Override
                    public void onBufferReceived(byte[] buffer) {}

                    @Override
                    public void onEndOfSpeech() {
                        isListening = false;
                    }

                    @Override
                    public void onError(int error) {
                        isListening = false;
                        if (isPaused || MainActivity.isAppForeground()) return;
                        long delay = 1500;
                        if (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY || error == SpeechRecognizer.ERROR_CLIENT) {
                            delay = 3000;
                        }
                        scheduleRestart(delay);
                    }

                    @Override
                    public void onResults(Bundle results) {
                        isListening = false;
                        processResults(results);
                        if (!isPaused && !MainActivity.isAppForeground()) {
                            scheduleRestart(1200);
                        }
                    }

                    @Override
                    public void onPartialResults(Bundle partialResults) {
                        processResults(partialResults);
                    }

                    @Override
                    public void onEvent(int eventType, Bundle params) {}
                });
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }

    private synchronized void startListeningInternal() {
        if (isPaused || MainActivity.isAppForeground() || speechRecognizer == null || speechIntent == null) return;
        handler.post(() -> {
            try {
                if (!isPaused && !MainActivity.isAppForeground() && speechRecognizer != null) {
                    speechRecognizer.startListening(speechIntent);
                }
            } catch (Exception ignored) {
                scheduleRestart(2000);
            }
        });
    }

    private void scheduleRestart(long delayMs) {
        if (isPaused || MainActivity.isAppForeground()) return;
        handler.removeCallbacksAndMessages(null);
        handler.postDelayed(this::startListeningInternal, delayMs);
    }

    public void pauseListening() {
        isPaused = true;
        handler.removeCallbacksAndMessages(null);
        handler.post(() -> {
            if (speechRecognizer != null) {
                try {
                    speechRecognizer.stopListening();
                    speechRecognizer.cancel();
                } catch (Exception ignored) {}
            }
        });
    }

    public void resumeListening() {
        if (MainActivity.isAppForeground()) {
            isPaused = true;
            return;
        }
        isPaused = false;
        scheduleRestart(500);
    }

    private void processResults(Bundle results) {
        if (results == null) return;
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) return;

        for (String match : matches) {
            String lower = match.toLowerCase(Locale.ROOT).trim();
            if (isSleepPhrase(lower)) {
                // Si la app ya está en reposo/segundo plano, ignorar frases de cierre para no despertar la pantalla
                return;
            }
            if (isWakeWord(lower)) {
                triggerWakeUp(lower);
                break;
            }
        }
    }

    private boolean isSleepPhrase(String text) {
        if (text == null) return false;
        String t = text.toLowerCase(Locale.ROOT).trim();
        return t.contains("gracias alberth") ||
               t.contains("es todo alberth") ||
               t.contains("alberth descansar") ||
               t.contains("cierra alberth") ||
               t.contains("alberth eso es todo");
    }

    private boolean isWakeWord(String text) {
        return text.contains("alberth") || text.contains("alberto") ||
               text.contains("albert")  || text.contains("álbert")  ||
               text.contains("álberth") || text.contains("alverth") ||
               text.contains("alverto") || text.contains("albeth")  ||
               text.contains("albet")   || text.contains("alber")   ||
               text.contains("hola alberth") || text.contains("estas alli") ||
               text.contains("estás allí")   || text.contains("estas ahi")  ||
               text.contains("oye alberth")  || text.contains("hey alberth");
    }

    private void triggerWakeUp(String heard) {
        triggerVibration();

        // 1. Despertar la pantalla
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null) {
                PowerManager.WakeLock screenLock = pm.newWakeLock(
                        PowerManager.SCREEN_BRIGHT_WAKE_LOCK |
                        PowerManager.ACQUIRE_CAUSES_WAKEUP |
                        PowerManager.ON_AFTER_RELEASE,
                        "Alberth:WakeScreenTrigger"
                );
                screenLock.acquire(4000);
            }
        } catch (Exception ignored) {}

        // 2. Extraer comando si lo dijo de corrido ("Alberth dónde estoy")
        String cmd = heard.replaceAll("^.*?(alberth|alberto|albert|álbert|álberth|alverth|alverto|albeth|albet|alber|hola\\s+alberth|estas\\s+alli\\s+alberth|est[aá]s\\s+all[ií]|oye\\s+alberth)\\s*", "").trim();

        // 3. Abrir la actividad principal en primer plano
        Intent intent = new Intent(this, MainActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | 
                        Intent.FLAG_ACTIVITY_SINGLE_TOP | 
                        Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        intent.putExtra("TRIGGER_WAKE_WORD", true);
        intent.putExtra("HEARD_PHRASE", heard);
        if (cmd.length() >= 2) {
            intent.putExtra("INITIAL_VOICE_CMD", cmd);
        }
        startActivity(intent);
    }

    private void triggerVibration() {
        try {
            Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (v != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    v.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    v.vibrate(100);
                }
            }
        } catch (Exception ignored) {}
    }

    @Override
    public void onDestroy() {
        instance = null;
        if (wakeLock != null && wakeLock.isHeld()) {
            try { wakeLock.release(); } catch (Exception ignored) {}
        }
        if (speechRecognizer != null) {
            try { speechRecognizer.destroy(); } catch (Exception ignored) {}
        }
        stopForeground(true);
        super.onDestroy();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
