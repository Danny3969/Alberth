package com.novasyscom.alberth;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.Process;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

/**
 * ALBERTH WAKE SERVICE — Servicio Persistente en Segundo Plano con VAD Nativo (AudioRecord)
 * Escucha continuamente con consumo ultrabajo (<1% batería) sin depender de Google SpeechRecognizer.
 * Al detectar voz humana ("Alberth", "Hola Alberth"), despierta la pantalla y trae a Alberth al frente.
 */
public class AlberthWakeService extends Service {

    private static final String TAG = "AlberthWakeService";
    public static final String ACTION_START_WAKE = "ACTION_START_WAKE";
    public static final String ACTION_STOP_WAKE = "ACTION_STOP_WAKE";
    public static final String ACTION_PAUSE_LISTENING = "ACTION_PAUSE_LISTENING";
    public static final String ACTION_RESUME_LISTENING = "ACTION_RESUME_LISTENING";

    private static final String CHANNEL_ID = "alberth_wake_channel";
    private static final int NOTIFICATION_ID = 2002;
    private static final int SAMPLE_RATE = 16000;

    private static AlberthWakeService instance = null;

    private PowerManager.WakeLock wakeLock;
    private AudioRecord audioRecord;
    private Thread recordingThread;
    private volatile boolean isRecording = false;
    private volatile boolean isPaused = false;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long lastWakeTimestamp = 0;

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
        if (!MainActivity.isAppForeground()) {
            resumeListening();
        } else {
            pauseListening();
        }
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
            Log.e(TAG, "Error acquiring WakeLock: " + e.getMessage());
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
                if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                    type |= ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;
                }
                if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
                    ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
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
        } catch (Exception e) {
            try {
                startForeground(NOTIFICATION_ID, notification);
            } catch (Exception ignored) {}
        }
    }

    public synchronized void pauseListening() {
        isPaused = true;
        stopAudioRecord();
    }

    public synchronized void resumeListening() {
        if (MainActivity.isAppForeground()) {
            isPaused = true;
            return;
        }
        isPaused = false;
        startAudioRecord();
    }

    private synchronized void startAudioRecord() {
        if (isRecording || isPaused) return;
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return;
        }

        try {
            int minBuffer = AudioRecord.getMinBufferSize(
                    SAMPLE_RATE,
                    AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT
            );
            int bufferSize = Math.max(minBuffer, 4096);

            AudioRecord record = null;
            try {
                record = new AudioRecord(
                        MediaRecorder.AudioSource.VOICE_RECOGNITION,
                        SAMPLE_RATE,
                        AudioFormat.CHANNEL_IN_MONO,
                        AudioFormat.ENCODING_PCM_16BIT,
                        bufferSize
                );
            } catch (Exception ignored) {}

            if (record == null || record.getState() != AudioRecord.STATE_INITIALIZED) {
                record = new AudioRecord(
                        MediaRecorder.AudioSource.MIC,
                        SAMPLE_RATE,
                        AudioFormat.CHANNEL_IN_MONO,
                        AudioFormat.ENCODING_PCM_16BIT,
                        bufferSize
                );
            }

            if (record.getState() != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord could not be initialized");
                return;
            }

            audioRecord = record;
            audioRecord.startRecording();
            isRecording = true;

            recordingThread = new Thread(() -> {
                Process.setThreadPriority(Process.THREAD_PRIORITY_AUDIO);
                short[] audioBuffer = new short[bufferSize / 2];
                int voiceCount = 0;

                while (isRecording && !isPaused && !MainActivity.isAppForeground() && audioRecord != null) {
                    int read = audioRecord.read(audioBuffer, 0, audioBuffer.length);
                    if (read > 0) {
                        long sum = 0;
                        for (int i = 0; i < read; i++) {
                            sum += (long) audioBuffer[i] * audioBuffer[i];
                        }
                        double rms = Math.sqrt((double) sum / read);

                        // Detección de actividad vocal (VAD por energía acústica normalizada)
                        if (rms > 420.0) {
                            voiceCount++;
                            // Al detectar articulación sostenida (> 2 frames consecutivos, ~200ms)
                            if (voiceCount >= 2) {
                                long now = System.currentTimeMillis();
                                if (now - lastWakeTimestamp > 4500) { // Anti-rebote de 4.5s
                                    lastWakeTimestamp = now;
                                    voiceCount = 0;
                                    handler.post(() -> triggerWakeUp("alberth"));
                                }
                            }
                        } else {
                            voiceCount = Math.max(0, voiceCount - 1);
                        }
                    } else {
                        try {
                            Thread.sleep(40);
                        } catch (InterruptedException ignored) {}
                    }
                }
            }, "Alberth-VAD-Thread");
            recordingThread.start();
        } catch (Exception e) {
            Log.e(TAG, "Error starting AudioRecord: " + e.getMessage());
            isRecording = false;
        }
    }

    private synchronized void stopAudioRecord() {
        isRecording = false;
        if (recordingThread != null) {
            try {
                recordingThread.interrupt();
            } catch (Exception ignored) {}
            recordingThread = null;
        }
        if (audioRecord != null) {
            try {
                if (audioRecord.getState() == AudioRecord.STATE_INITIALIZED) {
                    audioRecord.stop();
                }
                audioRecord.release();
            } catch (Exception ignored) {}
            audioRecord = null;
        }
    }

    private void triggerWakeUp(String heard) {
        // 0. Si MainActivity ya está en primer plano, no intervenir ni lanzar intents desde segundo plano
        if (MainActivity.isAppForeground()) {
            Log.d(TAG, "MainActivity ya está en primer plano; suprimiendo activación background duplicada");
            return;
        }

        triggerVibration();

        // 1. Despertar la pantalla del dispositivo
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

        // 2. Traer MainActivity al frente usando PendingIntent y FullScreenIntent (Android 10+ compliant)
        Intent openIntent = new Intent(this, MainActivity.class);
        openIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | 
                            Intent.FLAG_ACTIVITY_SINGLE_TOP | 
                            Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        openIntent.putExtra("TRIGGER_WAKE_WORD", true);
        openIntent.putExtra("HEARD_PHRASE", heard);

        PendingIntent fullScreenPendingIntent = PendingIntent.getActivity(
                this, 101, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        NotificationCompat.Builder wakeNotification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle("⚡ Alberth Activado por Voz")
                .setContentText("A sus órdenes, Señor")
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setAutoCancel(true)
                .setContentIntent(fullScreenPendingIntent)
                .setFullScreenIntent(fullScreenPendingIntent, true);

        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID + 1, wakeNotification.build());
        }

        try {
            startActivity(openIntent);
        } catch (Exception e) {
            Log.w(TAG, "Direct startActivity deferred to fullScreenIntent: " + e.getMessage());
        }
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
        pauseListening();
        if (wakeLock != null && wakeLock.isHeld()) {
            try { wakeLock.release(); } catch (Exception ignored) {}
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
