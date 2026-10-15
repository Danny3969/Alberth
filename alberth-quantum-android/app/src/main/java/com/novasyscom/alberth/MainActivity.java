package com.novasyscom.alberth;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.location.Address;
import android.location.Geocoder;
import android.location.Location;
import android.location.LocationManager;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import org.json.JSONObject;

import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class MainActivity extends AppCompatActivity {

    private static final String PREFS_NAME = "AlberthPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_TUNNEL_URL = "https://interact-deeply-asn-tracy.trycloudflare.com/";
    private static final int PERMISSION_REQ_CODE = 101;

    private View rootLayout;
    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private LinearLayout offlineOverlay;
    private TextView errorText;
    private SharedPreferences prefs;
    private long backPressedTime = 0;

    // Asistente Nativo de Voz y Detección de Wake Word ("Alberth")
    private SpeechRecognizer speechRecognizer;
    private Intent speechIntent;
    private TextToSpeech tts;
    public static volatile boolean isAppInForeground = false;
    private volatile boolean isAlberthSpeaking = false;
    private boolean isListening = false;
    private int consecutiveErrors = 0;
    private final Handler voiceHandler = new Handler(Looper.getMainLooper());

    private LocationManager locationManager;

    public static boolean isAppForeground() {
        return isAppInForeground;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        configureSystemBars();
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);

        rootLayout = findViewById(R.id.rootLayout);
        webView = findViewById(R.id.webView);
        swipeRefresh = findViewById(R.id.swipeRefresh);
        offlineOverlay = findViewById(R.id.offlineOverlay);
        errorText = findViewById(R.id.errorText);
        Button btnRetry = findViewById(R.id.btnRetry);
        Button btnConfig = findViewById(R.id.btnConfig);

        applyWindowInsetsPadding();
        setupSwipeRefresh();
        setupWebView();
        initTextToSpeech();
        requestHardwarePermissions();

        // Configurar pantalla para encenderse y mostrarse sobre bloqueo al ser invocado por voz
        configureLockScreenDisplay();

        btnRetry.setOnClickListener(v -> loadActiveUrl());
        btnConfig.setOnClickListener(v -> showConfigDialog());

        loadActiveUrl();
        handleAssistantIntent(getIntent());
    }

    private void startPersistentWakeService() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        try {
            Intent serviceIntent = new Intent(this, AlberthWakeService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void configureLockScreenDisplay() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        }
        getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON |
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
        );
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleAssistantIntent(intent);
    }

    private void handleAssistantIntent(Intent intent) {
        if (intent != null) {
            String action = intent.getAction();
            boolean isWakeTrigger = intent.getBooleanExtra("TRIGGER_WAKE_WORD", false);
            if (isWakeTrigger || Intent.ACTION_ASSIST.equals(action) || Intent.ACTION_VOICE_COMMAND.equals(action)) {
                configureLockScreenDisplay();
                triggerHapticFeedback(90);
                String heard = intent.getStringExtra("HEARD_PHRASE");
                notifyWebWakeWordActivated(heard != null ? heard : "alberth");

                String initCmd = intent.getStringExtra("INITIAL_VOICE_CMD");
                if (initCmd != null && !initCmd.isEmpty()) {
                    voiceHandler.postDelayed(() -> dispatchVoiceCommandToWeb(initCmd), 800);
                }
            }
        }
    }

    private void configureSystemBars() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            Window window = getWindow();
            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            window.setStatusBarColor(Color.parseColor("#040711"));
            window.setNavigationBarColor(Color.parseColor("#040711"));
        }
    }

    private void applyWindowInsetsPadding() {
        if (rootLayout != null) {
            ViewCompat.setOnApplyWindowInsetsListener(rootLayout, (v, windowInsets) -> {
                Insets insets = windowInsets.getInsets(
                        WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout()
                );
                v.setPadding(insets.left, insets.top, insets.right, insets.bottom);
                return windowInsets;
            });
        }
    }

    private void setupSwipeRefresh() {
        swipeRefresh.setColorSchemeColors(Color.parseColor("#00f0ff"), Color.parseColor("#00ffa3"));
        swipeRefresh.setProgressBackgroundColorSchemeColor(Color.parseColor("#040711"));
        swipeRefresh.setOnRefreshListener(() -> {
            if (webView != null) {
                webView.reload();
            }
        });
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setGeolocationEnabled(true);
        s.setGeolocationDatabasePath(getFilesDir().getPath());
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        webView.setBackgroundColor(Color.parseColor("#040711"));
        webView.addJavascriptInterface(new AlberthBridge(), "AlberthAndroid");

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    try {
                        request.grant(request.getResources());
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                });
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
            }

            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress >= 90) {
                    swipeRefresh.setRefreshing(false);
                }
            }

            @Override
            public boolean onConsoleMessage(ConsoleMessage cm) {
                return true;
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                swipeRefresh.setRefreshing(false);
                offlineOverlay.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request != null && request.isForMainFrame()) {
                    swipeRefresh.setRefreshing(false);
                    offlineOverlay.setVisibility(View.VISIBLE);
                    errorText.setText("No se pudo conectar al servidor Alberth.\nVerifique que el túnel seguro o su Mac estén encendidos.");
                }
            }
        });
    }

    private void requestHardwarePermissions() {
        List<String> permList = new ArrayList<>();
        permList.add(Manifest.permission.RECORD_AUDIO);
        permList.add(Manifest.permission.CAMERA);
        permList.add(Manifest.permission.MODIFY_AUDIO_SETTINGS);
        permList.add(Manifest.permission.ACCESS_FINE_LOCATION);
        permList.add(Manifest.permission.ACCESS_COARSE_LOCATION);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permList.add(Manifest.permission.POST_NOTIFICATIONS);
        }

        String[] permissions = permList.toArray(new String[0]);
        boolean needed = false;
        for (String p : permissions) {
            if (ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED) {
                needed = true;
                break;
            }
        }

        if (needed) {
            ActivityCompat.requestPermissions(this, permissions, PERMISSION_REQ_CODE);
        } else {
            initNativeVoiceAssistant();
            startPersistentWakeService();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQ_CODE) {
            boolean audioGranted = ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
            if (audioGranted) {
                initNativeVoiceAssistant();
                startPersistentWakeService();
            }
        }
    }

    // ─── Reconocimiento de Voz Nativo Continuo & Wake Word ("Alberth") ───────

    private boolean isExpectingFollowupCommand = false;
    private final Runnable resetFollowupRunnable = () -> isExpectingFollowupCommand = false;

    private void initNativeVoiceAssistant() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            return;
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return;
        }

        try {
            if (speechRecognizer != null) {
                try { speechRecognizer.destroy(); } catch (Exception ignored) {}
            }
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
                    consecutiveErrors = 0;
                }

                @Override
                public void onBeginningOfSpeech() {
                    isListening = true;
                }

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
                    if (!isAppInForeground || isAlberthSpeaking) {
                        return;
                    }

                    consecutiveErrors++;
                    long delayMs = 1500;

                    if (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY || error == SpeechRecognizer.ERROR_CLIENT) {
                        delayMs = 2500;
                        if (consecutiveErrors >= 3) {
                            consecutiveErrors = 0;
                            voiceHandler.removeCallbacksAndMessages(null);
                            voiceHandler.postDelayed(MainActivity.this::initNativeVoiceAssistant, 1200);
                            return;
                        }
                    } else if (error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT || error == SpeechRecognizer.ERROR_NO_MATCH) {
                        delayMs = 1400;
                    } else if (error == SpeechRecognizer.ERROR_AUDIO || error == SpeechRecognizer.ERROR_SERVER) {
                        delayMs = 2000;
                    }

                    voiceHandler.removeCallbacksAndMessages(null);
                    voiceHandler.postDelayed(MainActivity.this::startListeningSafely, delayMs);
                }

                @Override
                public void onResults(Bundle results) {
                    isListening = false;
                    consecutiveErrors = 0;
                    processVoiceResults(results);
                    // Reiniciar escucha continua con debounce prudencial si Alberth no está hablando
                    if (isAppInForeground && !isAlberthSpeaking) {
                        voiceHandler.removeCallbacksAndMessages(null);
                        voiceHandler.postDelayed(MainActivity.this::startListeningSafely, 800);
                    }
                }

                @Override
                public void onPartialResults(Bundle partialResults) {
                    processPartialVoiceResults(partialResults);
                }

                @Override
                public void onEvent(int eventType, Bundle params) {}
            });

            if (isAppInForeground && !isAlberthSpeaking) {
                voiceHandler.postDelayed(this::startListeningSafely, 600);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private synchronized void startListeningSafely() {
        if (!isAppInForeground || isAlberthSpeaking || isListening || speechRecognizer == null || speechIntent == null) {
            return;
        }
        try {
            speechRecognizer.startListening(speechIntent);
        } catch (Exception ignored) {
            if (isAppInForeground && !isAlberthSpeaking) {
                voiceHandler.postDelayed(this::startListeningSafely, 2000);
            }
        }
    }

    private void stopListeningSafely() {
        isListening = false;
        if (speechRecognizer != null) {
            try {
                speechRecognizer.stopListening();
                speechRecognizer.cancel();
            } catch (Exception ignored) {}
        }
    }

    private void processVoiceResults(Bundle results) {
        if (results == null) return;
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) return;

        for (String match : matches) {
            String lower = match.toLowerCase(Locale.ROOT).trim();
            if (isWakeWordMatch(lower)) {
                triggerHapticFeedback(70);
                String cmd = extractCommand(lower);
                if (cmd.length() >= 2) {
                    isExpectingFollowupCommand = false;
                    dispatchVoiceCommandToWeb(cmd);
                } else {
                    isExpectingFollowupCommand = true;
                    voiceHandler.removeCallbacks(resetFollowupRunnable);
                    voiceHandler.postDelayed(resetFollowupRunnable, 8000);
                    notifyWebWakeWordActivated(lower);
                }
                return;
            } else if (isExpectingFollowupCommand) {
                triggerHapticFeedback(50);
                isExpectingFollowupCommand = false;
                voiceHandler.removeCallbacks(resetFollowupRunnable);
                dispatchVoiceCommandToWeb(lower);
                return;
            }
        }
    }

    private void processPartialVoiceResults(Bundle partialResults) {
        if (partialResults == null) return;
        ArrayList<String> matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) return;

        for (String match : matches) {
            String lower = match.toLowerCase(Locale.ROOT).trim();
            if (isWakeWordMatch(lower) && !isExpectingFollowupCommand) {
                triggerHapticFeedback(60);
                notifyWebWakeWordActivated(lower);
                return;
            }
        }
    }

    private boolean isWakeWordMatch(String text) {
        return text.contains("alberth") || text.contains("alberto") ||
               text.contains("albert")  || text.contains("álbert")  ||
               text.contains("álberth") || text.contains("alverth") ||
               text.contains("alverto") || text.contains("albeth")  ||
               text.contains("albet")   || text.contains("alber")   ||
               text.contains("hola alberth") || text.contains("estas alli") ||
               text.contains("estás allí")   || text.contains("estas ahi")  ||
               text.contains("oye alberth")  || text.contains("hey alberth");
    }

    private String extractCommand(String text) {
        return text.replaceAll("^.*?(alberth|alberto|albert|álbert|álberth|alverth|alverto|albeth|albet|alber|hola\\s+alberth|estas\\s+alli\\s+alberth|est[aá]s\\s+all[ií]|oye\\s+alberth)\\s*", "").trim();
    }

    private void triggerHapticFeedback(int ms) {
        try {
            Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (v != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    v.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    v.vibrate(ms);
                }
            }
        } catch (Exception ignored) {}
    }

    private void dispatchVoiceCommandToWeb(String cmd) {
        runOnUiThread(() -> {
            if (webView != null) {
                String safeCmd = cmd.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ");
                webView.evaluateJavascript("if (window.onNativeVoiceCommand) { window.onNativeVoiceCommand(\"" + safeCmd + "\"); }", null);
            }
        });
    }

    private void notifyWebWakeWordActivated(String phrase) {
        runOnUiThread(() -> {
            if (webView != null) {
                String safePhrase = (phrase != null ? phrase : "alberth").replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ");
                webView.evaluateJavascript("if (window.onNativeWakeWord) { window.onNativeWakeWord(\"" + safePhrase + "\"); }", null);
            }
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        isAppInForeground = true;
        // Pausar escucha del servicio background para evitar colisión de micrófono
        if (AlberthWakeService.getInstance() != null) {
            AlberthWakeService.getInstance().pauseListening();
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            startPersistentWakeService();
            if (!isAlberthSpeaking) {
                voiceHandler.removeCallbacksAndMessages(null);
                voiceHandler.postDelayed(this::startListeningSafely, 600);
            }
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        isAppInForeground = false;
        voiceHandler.removeCallbacksAndMessages(null);
        stopListeningSafely();
        // Reanudar escucha en segundo plano permanente para responder a "Alberth"
        if (AlberthWakeService.getInstance() != null) {
            AlberthWakeService.getInstance().resumeListening();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (speechRecognizer != null) {
            try {
                speechRecognizer.destroy();
            } catch (Exception ignored) {}
            speechRecognizer = null;
        }
        if (tts != null) {
            try {
                tts.stop();
                tts.shutdown();
            } catch (Exception ignored) {}
            tts = null;
        }
    }

    private void initTextToSpeech() {
        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                tts.setLanguage(new Locale("es", "ES"));
                tts.setSpeechRate(1.05f);
            }
        });
    }

    public void speakNativeText(String text) {
        runOnUiThread(() -> {
            if (tts != null) {
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "AlberthTTS_" + System.currentTimeMillis());
            }
        });
    }

    // ─── Geolocalización & GPS Nativo ───────────────────────────────

    private Location getLastKnownLocation() {
        if (locationManager == null) return null;
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            return null;
        }

        Location best = null;
        List<String> providers = locationManager.getProviders(true);
        for (String p : providers) {
            try {
                Location l = locationManager.getLastKnownLocation(p);
                if (l != null && (best == null || l.getAccuracy() < best.getAccuracy())) {
                    best = l;
                }
            } catch (Exception ignored) {}
        }
        return best;
    }

    public String getCurrentLocationJson() {
        JSONObject obj = new JSONObject();
        try {
            Location loc = getLastKnownLocation();
            if (loc == null) {
                obj.put("ok", false);
                obj.put("error", "No se pudo obtener señal GPS del teléfono.");
                return obj.toString();
            }

            double lat = loc.getLatitude();
            double lng = loc.getLongitude();
            float speedKmh = Math.round(loc.getSpeed() * 3.6f);

            obj.put("ok", true);
            obj.put("latitude", lat);
            obj.put("longitude", lng);
            obj.put("speed_kmh", speedKmh);
            obj.put("altitude", loc.getAltitude());
            obj.put("accuracy_meters", loc.getAccuracy());

            // Geocodificación inversa
            try {
                Geocoder geocoder = new Geocoder(this, new Locale("es", "ES"));
                List<Address> addresses = geocoder.getFromLocation(lat, lng, 1);
                if (addresses != null && !addresses.isEmpty()) {
                    Address addr = addresses.get(0);
                    String thoroughfare = addr.getThoroughfare();
                    String subThoroughfare = addr.getSubThoroughfare();
                    String locality = addr.getLocality();
                    String subLocality = addr.getSubLocality();
                    String country = addr.getCountryName();

                    StringBuilder sb = new StringBuilder();
                    if (thoroughfare != null) sb.append(thoroughfare);
                    if (subThoroughfare != null) sb.append(" ").append(subThoroughfare);
                    if (subLocality != null && !subLocality.equals(thoroughfare)) sb.append(", ").append(subLocality);
                    if (locality != null) sb.append(", ").append(locality);
                    if (country != null) sb.append(", ").append(country);

                    String humanAddress = sb.toString().trim();
                    if (humanAddress.isEmpty() && addr.getAddressLine(0) != null) {
                        humanAddress = addr.getAddressLine(0);
                    }
                    obj.put("address", humanAddress);
                    obj.put("city", locality != null ? locality : "");
                } else {
                    obj.put("address", String.format(Locale.ROOT, "Lat: %.5f, Lng: %.5f", lat, lng));
                }
            } catch (Exception ge) {
                obj.put("address", String.format(Locale.ROOT, "Lat: %.5f, Lng: %.5f", lat, lng));
            }
        } catch (Exception e) {
            try {
                obj.put("ok", false);
                obj.put("error", e.getMessage());
            } catch (Exception ignored) {}
        }
        return obj.toString();
    }

    public void openNativeMap(String query) {
        runOnUiThread(() -> {
            try {
                Intent intent;
                if (query != null && !query.trim().isEmpty()) {
                    Uri uri = Uri.parse("geo:0,0?q=" + Uri.encode(query.trim()));
                    intent = new Intent(Intent.ACTION_VIEW, uri);
                } else {
                    Location loc = getLastKnownLocation();
                    if (loc != null) {
                        Uri uri = Uri.parse("geo:" + loc.getLatitude() + "," + loc.getLongitude() + "?z=16");
                        intent = new Intent(Intent.ACTION_VIEW, uri);
                    } else {
                        Uri uri = Uri.parse("geo:0,0?q=mi+ubicacion");
                        intent = new Intent(Intent.ACTION_VIEW, uri);
                    }
                }
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception e) {
                Toast.makeText(this, "No se encontró aplicación de mapas", Toast.LENGTH_SHORT).show();
            }
        });
    }

    public void startNativeNavigation(String destination) {
        runOnUiThread(() -> {
            try {
                Uri navUri = Uri.parse("google.navigation:q=" + Uri.encode(destination.trim()));
                Intent navIntent = new Intent(Intent.ACTION_VIEW, navUri);
                navIntent.setPackage("com.google.android.apps.maps");
                navIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(navIntent);
            } catch (Exception e) {
                try {
                    Uri genericUri = Uri.parse("geo:0,0?q=" + Uri.encode(destination.trim()));
                    Intent fallback = new Intent(Intent.ACTION_VIEW, genericUri);
                    fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(fallback);
                } catch (Exception ex) {
                    Toast.makeText(this, "No se pudo iniciar navegación GPS", Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    // ─── Gestión de Aplicaciones y Media ─────────────────────────────

    private static final Map<String, String> COMMON_PACKAGES = new HashMap<>();
    static {
        COMMON_PACKAGES.put("whatsapp", "com.whatsapp");
        COMMON_PACKAGES.put("spotify", "com.spotify.music");
        COMMON_PACKAGES.put("maps", "com.google.android.apps.maps");
        COMMON_PACKAGES.put("mapas", "com.google.android.apps.maps");
        COMMON_PACKAGES.put("waze", "com.waze");
        COMMON_PACKAGES.put("youtube", "com.google.android.youtube");
        COMMON_PACKAGES.put("chrome", "com.android.chrome");
        COMMON_PACKAGES.put("telegram", "org.telegram.messenger");
        COMMON_PACKAGES.put("instagram", "com.instagram.android");
        COMMON_PACKAGES.put("uber", "com.ubercab");
        COMMON_PACKAGES.put("camara", "com.android.camera");
        COMMON_PACKAGES.put("fotos", "com.google.android.apps.photos");
    }

    public boolean openAppByName(String appName) {
        if (appName == null || appName.trim().isEmpty()) return false;
        String normalized = appName.toLowerCase().trim();

        // 1. Coincidencia directa por paquete conocido
        if (COMMON_PACKAGES.containsKey(normalized)) {
            String pkg = COMMON_PACKAGES.get(normalized);
            Intent launch = getPackageManager().getLaunchIntentForPackage(pkg);
            if (launch != null) {
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(launch);
                return true;
            }
        }

        // 2. Búsqueda por etiqueta de aplicación instalada
        PackageManager pm = getPackageManager();
        List<ApplicationInfo> packages = pm.getInstalledApplications(PackageManager.GET_META_DATA);
        for (ApplicationInfo app : packages) {
            String label = pm.getApplicationLabel(app).toString().toLowerCase();
            if (label.contains(normalized)) {
                Intent launch = pm.getLaunchIntentForPackage(app.packageName);
                if (launch != null) {
                    launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(launch);
                    return true;
                }
            }
        }
        return false;
    }

    public void dispatchMediaControl(String action) {
        int keyCode = KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE;
        if ("next".equalsIgnoreCase(action)) keyCode = KeyEvent.KEYCODE_MEDIA_NEXT;
        else if ("prev".equalsIgnoreCase(action)) keyCode = KeyEvent.KEYCODE_MEDIA_PREVIOUS;
        else if ("pause".equalsIgnoreCase(action)) keyCode = KeyEvent.KEYCODE_MEDIA_PAUSE;
        else if ("play".equalsIgnoreCase(action)) keyCode = KeyEvent.KEYCODE_MEDIA_PLAY;

        long eventTime = SystemClock.uptimeMillis();
        Intent down = new Intent(Intent.ACTION_MEDIA_BUTTON);
        down.putExtra(Intent.EXTRA_KEY_EVENT, new KeyEvent(eventTime, eventTime, KeyEvent.ACTION_DOWN, keyCode, 0));
        sendOrderedBroadcast(down, null);

        Intent up = new Intent(Intent.ACTION_MEDIA_BUTTON);
        up.putExtra(Intent.EXTRA_KEY_EVENT, new KeyEvent(eventTime, eventTime, KeyEvent.ACTION_UP, keyCode, 0));
        sendOrderedBroadcast(up, null);
    }

    // ─── Navegación y URLs ──────────────────────────────────────────

    private void loadActiveUrl() {
        String url = prefs.getString(KEY_SERVER_URL, DEFAULT_TUNNEL_URL);
        if (url == null || url.trim().isEmpty()) {
            url = DEFAULT_TUNNEL_URL;
        }
        offlineOverlay.setVisibility(View.GONE);
        swipeRefresh.setRefreshing(true);
        webView.loadUrl(url);
    }

    private void showConfigDialog() {
        String currentUrl = prefs.getString(KEY_SERVER_URL, DEFAULT_TUNNEL_URL);
        final EditText input = new EditText(this);
        input.setText(currentUrl);
        input.setHint("https://... o http://192.168.x.x:8080/");
        input.setTextColor(Color.WHITE);
        input.setBackgroundColor(Color.parseColor("#0e1a2f"));
        input.setPadding(30, 20, 30, 20);

        new AlertDialog.Builder(this)
                .setTitle("⚙️ Servidor Alberth")
                .setMessage("Ingrese la URL del Túnel Cloudflare o la IP local de su Mac:")
                .setView(input)
                .setPositiveButton("Conectar", (dialog, which) -> {
                    String newUrl = input.getText().toString().trim();
                    if (!newUrl.isEmpty()) {
                        if (!newUrl.startsWith("http://") && !newUrl.startsWith("https://")) {
                            newUrl = "https://" + newUrl;
                        }
                        prefs.edit().putString(KEY_SERVER_URL, newUrl).apply();
                        loadActiveUrl();
                    }
                })
                .setNeutralButton("Restaurar Túnel", (dialog, which) -> {
                    prefs.edit().putString(KEY_SERVER_URL, DEFAULT_TUNNEL_URL).apply();
                    loadActiveUrl();
                })
                .setNegativeButton("Cancelar", null)
                .show();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            if (backPressedTime + 2000 > System.currentTimeMillis()) {
                super.onBackPressed();
            } else {
                Toast.makeText(this, "Presione de nuevo para salir de Alberth", Toast.LENGTH_SHORT).show();
                backPressedTime = System.currentTimeMillis();
            }
        }
    }

    // ─── Bridge de JavaScript (window.AlberthAndroid) ───────────────

    public class AlberthBridge {
        @JavascriptInterface
        public String getAppVersion() {
            return "6.4-Quantum";
        }

        @JavascriptInterface
        public void vibrateDevice(int durationMs) {
            triggerHapticFeedback(durationMs > 0 ? durationMs : 50);
        }

        @JavascriptInterface
        public void openConfig() {
            runOnUiThread(MainActivity.this::showConfigDialog);
        }

        @JavascriptInterface
        public void showNativeToast(String msg) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, msg, Toast.LENGTH_SHORT).show());
        }

        @JavascriptInterface
        public void speakNative(String text) {
            speakNativeText(text);
        }

        @JavascriptInterface
        public void startCopilotService() {
            runOnUiThread(() -> {
                try {
                    Intent serviceIntent = new Intent(MainActivity.this, CopilotService.class);
                    serviceIntent.setAction(CopilotService.ACTION_START_COPILOT);
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(serviceIntent);
                    } else {
                        startService(serviceIntent);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
        }

        @JavascriptInterface
        public void stopCopilotService() {
            runOnUiThread(() -> {
                try {
                    Intent serviceIntent = new Intent(MainActivity.this, CopilotService.class);
                    serviceIntent.setAction(CopilotService.ACTION_STOP_COPILOT);
                    startService(serviceIntent);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
        }

        @JavascriptInterface
        public void setSpeakingState(boolean speaking) {
            runOnUiThread(() -> {
                isAlberthSpeaking = speaking;
                if (speaking) {
                    voiceHandler.removeCallbacksAndMessages(null);
                    stopListeningSafely();
                } else {
                    voiceHandler.removeCallbacksAndMessages(null);
                    if (isAppInForeground) {
                        voiceHandler.postDelayed(MainActivity.this::startListeningSafely, 600);
                    }
                }
            });
        }

        @JavascriptInterface
        public boolean getSpeakingState() {
            return isAlberthSpeaking;
        }

        @JavascriptInterface
        public void restartVoiceAssistant() {
            runOnUiThread(() -> {
                if (isAppInForeground && !isAlberthSpeaking) {
                    startListeningSafely();
                }
            });
        }

        // ── Métodos de Geolocalización y Mapas ──
        @JavascriptInterface
        public String getLocationInfo() {
            return getCurrentLocationJson();
        }

        @JavascriptInterface
        public void openMap(String query) {
            openNativeMap(query);
        }

        @JavascriptInterface
        public void startNavigation(String destination) {
            startNativeNavigation(destination);
        }

        // ── Métodos de Lanzador de Aplicaciones y Control Multimedia ──
        @JavascriptInterface
        public boolean openApp(String appName) {
            return openAppByName(appName);
        }

        @JavascriptInterface
        public void controlMedia(String action) {
            dispatchMediaControl(action);
        }

        // ── Métodos de Accesibilidad y Control de Pantalla ──
        @JavascriptInterface
        public boolean isAccessibilityEnabled() {
            return AlberthAccessibilityService.isServiceRunning();
        }

        @JavascriptInterface
        public void openAccessibilitySettings() {
            runOnUiThread(() -> {
                try {
                    Toast.makeText(MainActivity.this, "Active el interruptor de Alberth para permitir control de pantalla y aplicaciones", Toast.LENGTH_LONG).show();
                    Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                } catch (Exception ignored) {}
            });
        }

        @JavascriptInterface
        public String getScreenText() {
            AlberthAccessibilityService s = AlberthAccessibilityService.getInstance();
            if (s != null) {
                return s.getScreenContentSummary();
            }
            return "Servicio de Accesibilidad de Alberth no habilitado. Active el servicio en los Ajustes de Accesibilidad de Android.";
        }

        @JavascriptInterface
        public boolean pressHome() {
            AlberthAccessibilityService s = AlberthAccessibilityService.getInstance();
            if (s != null) {
                return s.goHome();
            }
            // Fallback de navegación si accesibilidad no está activa
            Intent startMain = new Intent(Intent.ACTION_MAIN);
            startMain.addCategory(Intent.CATEGORY_HOME);
            startMain.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(startMain);
            return true;
        }

        @JavascriptInterface
        public boolean pressBack() {
            AlberthAccessibilityService s = AlberthAccessibilityService.getInstance();
            if (s != null) {
                return s.goBack();
            }
            return false;
        }

        @JavascriptInterface
        public boolean takeScreenshot() {
            AlberthAccessibilityService s = AlberthAccessibilityService.getInstance();
            if (s != null) {
                return s.takeScreenshotAction();
            }
            return false;
        }
    }
}
