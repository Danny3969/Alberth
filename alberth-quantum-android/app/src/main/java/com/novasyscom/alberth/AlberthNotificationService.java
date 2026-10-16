package com.novasyscom.alberth;

import android.content.ComponentName;
import android.content.Context;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

/**
 * AlberthNotificationService — Servicio Oficial de Notificaciones y Control Universal de Multimedia
 * Permite a Alberth:
 * 1. Controlar cualquier reproductor de música (Spotify, YouTube Music, Apple Music, etc.)
 * 2. Leer canciones, artistas y estado de reproducción en tiempo real.
 * 3. Extraer y anunciar notificaciones entrantes (WhatsApp, Telegram, SMS) para el Señor.
 */
public class AlberthNotificationService extends NotificationListenerService {

    private static AlberthNotificationService instance;
    private static final int MAX_HISTORY = 15;
    private static final List<NotificationItem> notificationHistory = Collections.synchronizedList(new LinkedList<>());

    public static class NotificationItem {
        public String packageName;
        public String appName;
        public String title;
        public String text;
        public long postTime;

        public JSONObject toJson() {
            JSONObject obj = new JSONObject();
            try {
                obj.put("package", packageName != null ? packageName : "");
                obj.put("app_name", appName != null ? appName : "");
                obj.put("title", title != null ? title : "");
                obj.put("text", text != null ? text : "");
                obj.put("time", postTime);
            } catch (Exception ignored) {}
            return obj;
        }
    }

    public static AlberthNotificationService getInstance() {
        return instance;
    }

    public static boolean isServiceRunning() {
        return instance != null;
    }

    @Override
    public void onListenerConnected() {
        super.onListenerConnected();
        instance = this;
    }

    @Override
    public void onListenerDisconnected() {
        if (instance == this) {
            instance = null;
        }
        super.onListenerDisconnected();
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null) return;
        try {
            String pkg = sbn.getPackageName();
            // Ignorar notificaciones internas de Alberth para evitar bucles
            if (getPackageName().equals(pkg)) return;

            Bundle extras = sbn.getNotification() != null ? sbn.getNotification().extras : null;
            if (extras == null) return;

            CharSequence titleCs = extras.getCharSequence("android.title");
            CharSequence textCs = extras.getCharSequence("android.text");
            if (titleCs == null && textCs == null) return;

            String title = titleCs != null ? titleCs.toString().trim() : "";
            String text = textCs != null ? textCs.toString().trim() : "";
            if (title.isEmpty() && text.isEmpty()) return;

            String appLabel = pkg;
            try {
                CharSequence label = getPackageManager().getApplicationLabel(
                        getPackageManager().getApplicationInfo(pkg, 0)
                );
                if (label != null) appLabel = label.toString();
            } catch (Exception ignored) {}

            NotificationItem item = new NotificationItem();
            item.packageName = pkg;
            item.appName = appLabel;
            item.title = title;
            item.text = text;
            item.postTime = sbn.getPostTime();

            synchronized (notificationHistory) {
                notificationHistory.add(0, item);
                if (notificationHistory.size() > MAX_HISTORY) {
                    notificationHistory.remove(notificationHistory.size() - 1);
                }
            }

            // Notificar a MainActivity para anuncio proactivo en Modo Copiloto
            MainActivity activity = MainActivity.getInstance();
            if (activity != null) {
                activity.notifyIncomingNotification(item);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Notificación descartada por el usuario
    }

    // ─── Control Universal de Multimedia (MediaSessionManager) ───────────────

    public String getCurrentMediaTrackInfo() {
        JSONObject res = new JSONObject();
        try {
            MediaSessionManager msm = (MediaSessionManager) getSystemService(Context.MEDIA_SESSION_SERVICE);
            if (msm == null) {
                res.put("ok", false);
                res.put("error", "MediaSessionManager no disponible");
                return res.toString();
            }

            ComponentName cn = new ComponentName(this, AlberthNotificationService.class);
            List<MediaController> controllers = msm.getActiveSessions(cn);
            if (controllers == null || controllers.isEmpty()) {
                res.put("ok", false);
                res.put("error", "No hay reproductores de música activos actualmente");
                return res.toString();
            }

            // Priorizar controlador que pertenezca a Echo Music o que esté reproduciendo activamente
            MediaController bestMc = null;
            for (MediaController mc : controllers) {
                PlaybackState state = mc.getPlaybackState();
                boolean isPlaying = state != null && state.getState() == PlaybackState.STATE_PLAYING;
                String pkg = mc.getPackageName() != null ? mc.getPackageName().toLowerCase() : "";

                if (pkg.contains("echo")) {
                    bestMc = mc;
                    if (isPlaying) break;
                } else if (isPlaying && (bestMc == null || !bestMc.getPackageName().toLowerCase().contains("echo"))) {
                    bestMc = mc;
                } else if (bestMc == null) {
                    bestMc = mc;
                }
            }

            if (bestMc != null) {
                PlaybackState state = bestMc.getPlaybackState();
                boolean isPlaying = state != null && state.getState() == PlaybackState.STATE_PLAYING;
                MediaMetadata meta = bestMc.getMetadata();

                String title = "";
                String artist = "";
                String album = "";

                if (meta != null) {
                    title = meta.getString(MediaMetadata.METADATA_KEY_TITLE);
                    artist = meta.getString(MediaMetadata.METADATA_KEY_ARTIST);
                    album = meta.getString(MediaMetadata.METADATA_KEY_ALBUM);
                }

                if (title == null) title = "";
                if (artist == null) artist = "";
                if (album == null) album = "";

                res.put("ok", true);
                res.put("is_playing", isPlaying);
                res.put("title", title.isEmpty() ? "Echo Music" : title);
                res.put("artist", artist.isEmpty() ? "Reproductor Nativo" : artist);
                res.put("album", album);
                res.put("package", bestMc.getPackageName());
                return res.toString();
            }

            res.put("ok", false);
            res.put("error", "Música en pausa o sin metadatos disponibles");
        } catch (SecurityException se) {
            try {
                res.put("ok", false);
                res.put("error", "Permiso de escucha de notificaciones no activado en Android");
            } catch (Exception ignored) {}
        } catch (Exception e) {
            try {
                res.put("ok", false);
                res.put("error", e.getMessage());
            } catch (Exception ignored) {}
        }
        return res.toString();
    }

    public boolean executeMediaCommand(String action) {
        try {
            MediaSessionManager msm = (MediaSessionManager) getSystemService(Context.MEDIA_SESSION_SERVICE);
            if (msm == null) return false;

            ComponentName cn = new ComponentName(this, AlberthNotificationService.class);
            List<MediaController> controllers = msm.getActiveSessions(cn);
            if (controllers == null || controllers.isEmpty()) return false;

            // Priorizar controlador de Echo Music o el que esté sonando
            MediaController target = null;
            for (MediaController mc : controllers) {
                String pkg = mc.getPackageName() != null ? mc.getPackageName().toLowerCase() : "";
                PlaybackState state = mc.getPlaybackState();
                boolean isPlaying = state != null && state.getState() == PlaybackState.STATE_PLAYING;

                if (pkg.contains("echo")) {
                    target = mc;
                    break;
                }
                if (isPlaying && target == null) {
                    target = mc;
                }
            }
            if (target == null) {
                target = controllers.get(0);
            }

            MediaController.TransportControls tc = target.getTransportControls();
            if (tc == null) return false;

            if ("play".equalsIgnoreCase(action)) {
                tc.play();
                return true;
            } else if ("pause".equalsIgnoreCase(action)) {
                tc.pause();
                return true;
            } else if ("next".equalsIgnoreCase(action) || "skip".equalsIgnoreCase(action)) {
                tc.skipToNext();
                return true;
            } else if ("prev".equalsIgnoreCase(action) || "previous".equalsIgnoreCase(action)) {
                tc.skipToPrevious();
                return true;
            } else if ("toggle".equalsIgnoreCase(action)) {
                PlaybackState state = target.getPlaybackState();
                if (state != null && state.getState() == PlaybackState.STATE_PLAYING) {
                    tc.pause();
                } else {
                    tc.play();
                }
                return true;
            }
            return false;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    public String getRecentNotificationsJson(int maxCount) {
        JSONObject res = new JSONObject();
        JSONArray arr = new JSONArray();
        try {
            synchronized (notificationHistory) {
                int limit = Math.min(notificationHistory.size(), maxCount > 0 ? maxCount : 5);
                for (int i = 0; i < limit; i++) {
                    arr.put(notificationHistory.get(i).toJson());
                }
            }
            res.put("ok", true);
            res.put("notifications", arr);
        } catch (Exception e) {
            try {
                res.put("ok", false);
                res.put("error", e.getMessage());
            } catch (Exception ignored) {}
        }
        return res.toString();
    }
}
