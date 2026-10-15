package com.novasyscom.alberth;

import android.annotation.SuppressLint;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.IBinder;
import android.provider.Settings;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.Nullable;

/**
 * FloatingOrbService — Orbe Cuántico Flotante Superpuesto sobre cualquier App
 * Permite al Señor interactuar con Alberth mientras utiliza Waze, Google Maps, Spotify u otra app.
 */
public class FloatingOrbService extends Service {

    public static final String ACTION_START = "ACTION_START_FLOATING_ORB";
    public static final String ACTION_STOP = "ACTION_STOP_FLOATING_ORB";

    private WindowManager windowManager;
    private View floatingView;
    private WindowManager.LayoutParams params;
    private static boolean isRunning = false;

    public static boolean isOrbActive() {
        return isRunning;
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopFloatingOrb();
            stopSelf();
            return START_NOT_STICKY;
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            stopSelf();
            return START_NOT_STICKY;
        }

        startFloatingOrb();
        return START_STICKY;
    }

    @SuppressLint("ClickableViewAccessibility")
    private void startFloatingOrb() {
        if (isRunning || floatingView != null) return;

        int layoutType = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O ?
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY :
                WindowManager.LayoutParams.TYPE_PHONE;

        params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                layoutType,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT
        );

        params.gravity = Gravity.TOP | Gravity.START;
        params.x = 40;
        params.y = 200;

        // Contenedor del Orbe Cuántico
        FrameLayout root = new FrameLayout(this);
        root.setPadding(12, 12, 12, 12);

        // Orbe circular con brillo neón cian
        FrameLayout orb = new FrameLayout(this);
        GradientDrawable shape = new GradientDrawable();
        shape.setShape(GradientDrawable.OVAL);
        shape.setColor(Color.parseColor("#040711"));
        shape.setStroke(4, Color.parseColor("#00f0ff"));
        orb.setBackground(shape);

        int sizePx = Math.round(54 * getResources().getDisplayMetrics().density);
        FrameLayout.LayoutParams orbParams = new FrameLayout.LayoutParams(sizePx, sizePx);
        orbParams.gravity = Gravity.CENTER;
        orb.setLayoutParams(orbParams);

        // Ícono o texto dentro del orbe
        TextView icon = new TextView(this);
        icon.setText("⚡");
        icon.setTextSize(18);
        icon.setTextColor(Color.parseColor("#00f0ff"));
        icon.setGravity(Gravity.CENTER);
        orb.addView(icon);

        root.addView(orb);
        floatingView = root;

        // Gestos táctiles: Arrastrar o Tocar para abrir Alberth
        floatingView.setOnTouchListener(new View.OnTouchListener() {
            private int initialX, initialY;
            private float initialTouchX, initialTouchY;
            private long touchStartTime = 0;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = params.x;
                        initialY = params.y;
                        initialTouchX = event.getRawX();
                        initialTouchY = event.getRawY();
                        touchStartTime = System.currentTimeMillis();
                        return true;

                    case MotionEvent.ACTION_MOVE:
                        params.x = initialX + (int) (event.getRawX() - initialTouchX);
                        params.y = initialY + (int) (event.getRawY() - initialTouchY);
                        if (floatingView != null) {
                            windowManager.updateViewLayout(floatingView, params);
                        }
                        return true;

                    case MotionEvent.ACTION_UP:
                        long duration = System.currentTimeMillis() - touchStartTime;
                        float diffX = Math.abs(event.getRawX() - initialTouchX);
                        float diffY = Math.abs(event.getRawY() - initialTouchY);

                        if (duration < 250 && diffX < 15 && diffY < 15) {
                            // Clic en el orbe: Traer Alberth al frente
                            Intent openApp = new Intent(FloatingOrbService.this, MainActivity.class);
                            openApp.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                            openApp.putExtra("TRIGGER_WAKE_WORD", true);
                            openApp.putExtra("HEARD_PHRASE", "alberth");
                            startActivity(openApp);
                        }
                        return true;
                }
                return false;
            }
        });

        try {
            windowManager.addView(floatingView, params);
            isRunning = true;
        } catch (Exception e) {
            e.printStackTrace();
            isRunning = false;
        }
    }

    private void stopFloatingOrb() {
        isRunning = false;
        if (floatingView != null && windowManager != null) {
            try {
                windowManager.removeView(floatingView);
            } catch (Exception ignored) {}
            floatingView = null;
        }
    }

    @Override
    public void onDestroy() {
        stopFloatingOrb();
        super.onDestroy();
    }
}
