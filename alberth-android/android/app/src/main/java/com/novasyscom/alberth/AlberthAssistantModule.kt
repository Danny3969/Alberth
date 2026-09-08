package com.novasyscom.alberth

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.provider.Settings
import android.util.Log
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import org.json.JSONArray
import org.json.JSONObject

class AlberthAssistantModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext) {

    companion object {
        private const val TAG = "AlberthAssistantModule"
    }

    override fun getName(): String = "AlberthAssistantModule"

    @ReactMethod
    fun isAccessibilityEnabled(promise: Promise) {
        try {
            if (AlberthAccessibilityService.isRunning()) {
                promise.resolve(true)
                return
            }
            val enabledServices = Settings.Secure.getString(
                reactApplicationContext.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: ""
            val isEnabled = enabledServices.contains(reactApplicationContext.packageName)
            promise.resolve(isEnabled)
        } catch (e: Exception) {
            promise.resolve(false)
        }
    }

    @ReactMethod
    fun openAccessibilitySettings(promise: Promise) {
        try {
            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            reactApplicationContext.startActivity(intent)
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("SETTINGS_ERROR", e.message)
        }
    }

    @ReactMethod
    fun isDefaultAssistant(promise: Promise) {
        try {
            val currentAssistant = Settings.Secure.getString(
                reactApplicationContext.contentResolver,
                "assistant"
            ) ?: ""
            val isDefault = currentAssistant.contains(reactApplicationContext.packageName) || AlberthVoiceInteractionService.isActive
            promise.resolve(isDefault)
        } catch (e: Exception) {
            promise.resolve(false)
        }
    }

    @ReactMethod
    fun openAssistantSettings(promise: Promise) {
        try {
            val intent = Intent(Settings.ACTION_VOICE_INPUT_SETTINGS).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            reactApplicationContext.startActivity(intent)
            promise.resolve(true)
        } catch (e: Exception) {
            try {
                val fallback = Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                reactApplicationContext.startActivity(fallback)
                promise.resolve(true)
            } catch (e2: Exception) {
                promise.reject("SETTINGS_ERROR", e2.message)
            }
        }
    }

    @ReactMethod
    fun performClick(x: Double, y: Double, promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service == null) {
            promise.reject("SERVICE_NOT_RUNNING", "El servicio de accesibilidad de Alberth no está activo. Actívalo en Ajustes.")
            return
        }
        service.performClick(x.toFloat(), y.toFloat()) { success ->
            if (success) promise.resolve(true) else promise.reject("CLICK_FAILED", "No se pudo realizar el toque en pantalla.")
        }
    }

    @ReactMethod
    fun performSwipe(x1: Double, y1: Double, x2: Double, y2: Double, durationMs: Double, promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service == null) {
            promise.reject("SERVICE_NOT_RUNNING", "El servicio de accesibilidad de Alberth no está activo.")
            return
        }
        service.performSwipe(x1.toFloat(), y1.toFloat(), x2.toFloat(), y2.toFloat(), durationMs.toLong()) { success ->
            if (success) promise.resolve(true) else promise.reject("SWIPE_FAILED", "No se pudo realizar el deslizamiento.")
        }
    }

    @ReactMethod
    fun pressHome(promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service != null && service.pressHome()) {
            promise.resolve(true)
            return
        }
        try {
            val homeIntent = Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_HOME)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            reactApplicationContext.startActivity(homeIntent)
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("HOME_ERROR", e.message)
        }
    }

    @ReactMethod
    fun pressBack(promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service != null && service.pressBack()) {
            promise.resolve(true)
        } else {
            promise.reject("SERVICE_NOT_RUNNING", "El servicio de accesibilidad de Alberth es requerido para presionar Atrás.")
        }
    }

    @ReactMethod
    fun pressRecents(promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service != null && service.pressRecents()) {
            promise.resolve(true)
        } else {
            promise.reject("SERVICE_NOT_RUNNING", "El servicio de accesibilidad es requerido para abrir apps recientes.")
        }
    }

    @ReactMethod
    fun pressNotifications(promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service != null && service.pressNotifications()) {
            promise.resolve(true)
        } else {
            promise.reject("SERVICE_NOT_RUNNING", "Servicio de accesibilidad inactivo.")
        }
    }

    @ReactMethod
    fun pressQuickSettings(promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service != null && service.pressQuickSettings()) {
            promise.resolve(true)
        } else {
            promise.reject("SERVICE_NOT_RUNNING", "Servicio de accesibilidad inactivo.")
        }
    }

    @ReactMethod
    fun readScreenText(promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service == null) {
            promise.reject("SERVICE_NOT_RUNNING", "El servicio de accesibilidad de Alberth no está activo para leer la pantalla.")
            return
        }
        val hierarchy = service.readScreenHierarchy()
        promise.resolve(hierarchy)
    }

    @ReactMethod
    fun clickTextOnScreen(text: String, promise: Promise) {
        val service = AlberthAccessibilityService.instance
        if (service == null) {
            promise.reject("SERVICE_NOT_RUNNING", "El servicio de accesibilidad no está activo.")
            return
        }
        service.findAndClickText(text) { success ->
            if (success) {
                promise.resolve(true)
            } else {
                promise.reject("NOT_FOUND", "No se encontró el texto '$text' en la pantalla.")
            }
        }
    }

    @ReactMethod
    fun launchApp(packageName: String, promise: Promise) {
        try {
            val pm = reactApplicationContext.packageManager
            val launchIntent = pm.getLaunchIntentForPackage(packageName)
            if (launchIntent != null) {
                launchIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                reactApplicationContext.startActivity(launchIntent)
                promise.resolve(true)
            } else {
                promise.reject("APP_NOT_FOUND", "La aplicación $packageName no está instalada.")
            }
        } catch (e: Exception) {
            promise.reject("LAUNCH_ERROR", e.message)
        }
    }

    @ReactMethod
    fun playMedia(queryOrUrl: String, mediaType: String, promise: Promise) {
        try {
            if (mediaType.equals("youtube", ignoreCase = true) || queryOrUrl.contains("youtube.com") || queryOrUrl.contains("youtu.be")) {
                val intent = if (queryOrUrl.startsWith("http://") || queryOrUrl.startsWith("https://")) {
                    Intent(Intent.ACTION_VIEW, Uri.parse(queryOrUrl))
                } else {
                    Intent(Intent.ACTION_SEARCH).apply {
                        setPackage("com.google.android.youtube")
                        putExtra("query", queryOrUrl)
                    }
                }
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                try {
                    reactApplicationContext.startActivity(intent)
                    promise.resolve(true)
                    return
                } catch (e: Exception) {
                    val webIntent = Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com/results?search_query=" + Uri.encode(queryOrUrl))).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    reactApplicationContext.startActivity(webIntent)
                    promise.resolve(true)
                    return
                }
            } else if (mediaType.equals("spotify", ignoreCase = true)) {
                val intent = Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH).apply {
                    setPackage("com.spotify.music")
                    putExtra(MediaStore.EXTRA_MEDIA_FOCUS, "vnd.android.cursor.item/*")
                    putExtra(android.app.SearchManager.QUERY, queryOrUrl)
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                try {
                    reactApplicationContext.startActivity(intent)
                    promise.resolve(true)
                    return
                } catch (e: Exception) {
                    val webIntent = Intent(Intent.ACTION_VIEW, Uri.parse("https://open.spotify.com/search/" + Uri.encode(queryOrUrl))).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    reactApplicationContext.startActivity(webIntent)
                    promise.resolve(true)
                    return
                }
            } else {
                val intent = Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH).apply {
                    putExtra(android.app.SearchManager.QUERY, queryOrUrl)
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                reactApplicationContext.startActivity(intent)
                promise.resolve(true)
            }
        } catch (e: Exception) {
            promise.reject("MEDIA_ERROR", e.message)
        }
    }

    @ReactMethod
    fun openUrl(url: String, promise: Promise) {
        try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            reactApplicationContext.startActivity(intent)
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("URL_ERROR", e.message)
        }
    }

    @ReactMethod
    fun getInstalledApps(promise: Promise) {
        try {
            val pm = reactApplicationContext.packageManager
            val mainIntent = Intent(Intent.ACTION_MAIN, null).apply {
                addCategory(Intent.CATEGORY_LAUNCHER)
            }
            val apps = pm.queryIntentActivities(mainIntent, 0)
            val result = JSONArray()
            for (app in apps) {
                val obj = JSONObject().apply {
                    put("label", app.loadLabel(pm).toString())
                    put("package", app.activityInfo.packageName)
                }
                result.put(obj)
            }
            promise.resolve(result.toString())
        } catch (e: Exception) {
            promise.reject("APPS_ERROR", e.message)
        }
    }
}
