package com.novasyscom.alberth;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.graphics.Path;
import android.os.Build;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayList;
import java.util.List;

/**
 * AlberthAccessibilityService — Servicio de Accesibilidad Oficial de Android
 * Permite a Alberth controlar la pantalla, leer contenidos de aplicaciones,
 * navegar (Inicio, Atrás, Recientes), realizar clics y asistir al Señor.
 */
public class AlberthAccessibilityService extends AccessibilityService {

    private static AlberthAccessibilityService instance;

    public static AlberthAccessibilityService getInstance() {
        return instance;
    }

    public static boolean isServiceRunning() {
        return instance != null;
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // Eventos de interfaz activos
    }

    @Override
    public void onInterrupt() {
        // Interrupción del servicio
    }

    @Override
    public void onDestroy() {
        if (instance == this) {
            instance = null;
        }
        super.onDestroy();
    }

    public boolean goHome() {
        return performGlobalAction(GLOBAL_ACTION_HOME);
    }

    public boolean goBack() {
        return performGlobalAction(GLOBAL_ACTION_BACK);
    }

    public boolean openRecents() {
        return performGlobalAction(GLOBAL_ACTION_RECENTS);
    }

    public boolean openNotifications() {
        return performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS);
    }

    public boolean takeScreenshotAction() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            return performGlobalAction(GLOBAL_ACTION_TAKE_SCREENSHOT);
        }
        return false;
    }

    /**
     * Extrae el texto y elementos legibles visibles actualmente en la pantalla.
     */
    public String getScreenContentSummary() {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) {
            return "No se pudo leer la pantalla (ventana no accesible o protegida).";
        }

        StringBuilder sb = new StringBuilder();
        List<String> texts = new ArrayList<>();
        collectNodeTexts(root, texts, 0);

        if (texts.isEmpty()) {
            return "Pantalla analizada, pero no se detectó texto legible.";
        }

        sb.append("=== ELEMENTOS VISIBLES EN PANTALLA ===\n");
        for (String t : texts) {
            sb.append("• ").append(t).append("\n");
            if (sb.length() > 2500) {
                sb.append("... [Contenido truncado]");
                break;
            }
        }
        return sb.toString();
    }

    private void collectNodeTexts(AccessibilityNodeInfo node, List<String> list, int depth) {
        if (node == null || depth > 20 || list.size() > 60) return;

        CharSequence text = node.getText();
        CharSequence desc = node.getContentDescription();

        if (text != null && text.length() > 0) {
            String s = text.toString().trim();
            if (!s.isEmpty() && !list.contains(s)) {
                list.add(s);
            }
        } else if (desc != null && desc.length() > 0) {
            String s = desc.toString().trim();
            if (!s.isEmpty() && !list.contains(s)) {
                list.add("[Icono/Botón] " + s);
            }
        }

        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null) {
                collectNodeTexts(child, list, depth + 1);
                child.recycle();
            }
        }
    }

    /**
     * Realiza un clic táctil mediante GestureDescription en las coordenadas indicadas.
     */
    public boolean clickCoordinates(float x, float y) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            Path clickPath = new Path();
            clickPath.moveTo(x, y);
            GestureDescription.StrokeDescription clickStroke =
                    new GestureDescription.StrokeDescription(clickPath, 0, 50);
            GestureDescription.Builder gestureBuilder = new GestureDescription.Builder();
            gestureBuilder.addStroke(clickStroke);
            return dispatchGesture(gestureBuilder.build(), null, null);
        }
        return false;
    }
}
