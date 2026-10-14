package com.novasyscom.alberth;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
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

import java.util.ArrayList;
import java.util.Locale;

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
    private boolean isAppInForeground = false;
    private boolean isListening = false;
    private final Handler voiceHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Barra de estado y navegación en color Sci-Fi oscuro (#040711)
        configureSystemBars();

        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);

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
        requestHardwarePermissions();

        btnRetry.setOnClickListener(v -> loadActiveUrl());
        btnConfig.setOnClickListener(v -> showConfigDialog());

        loadActiveUrl();
        handleAssistantIntent(getIntent());
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
            if (Intent.ACTION_ASSIST.equals(action) || Intent.ACTION_VOICE_COMMAND.equals(action)) {
                triggerHapticFeedback(90);
                notifyWebWakeWordActivated();
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

    /**
     * Aplica padding exacto para la barra de estado superior y la barra de navegación inferior,
     * garantizando que el HUD de Alberth encuadre al 100% sin ser tapado por el reloj, batería o botones.
     */
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

        // Interfaz nativa accesible desde JavaScript (window.AlberthAndroid)
        webView.addJavascriptInterface(new AlberthBridge(), "AlberthAndroid");

        // WebChromeClient con concesión directa de permisos de Micrófono y Cámara
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

        // WebViewClient para mantener la navegación inmersiva y controlar el estado
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
        String[] permissions = new String[]{
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.CAMERA,
                Manifest.permission.MODIFY_AUDIO_SETTINGS
        };

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
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQ_CODE) {
            boolean allGranted = true;
            for (int r : grantResults) {
                if (r != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }
            if (allGranted) {
                Toast.makeText(this, "🎙️ Permisos de audio y visión activados", Toast.LENGTH_SHORT).show();
                initNativeVoiceAssistant();
            }
        }
    }

    // ─── Reconocimiento de Voz Nativo & Wake Word ("Alberth") ───────

    private void initNativeVoiceAssistant() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            return;
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return;
        }

        try {
            if (speechRecognizer != null) {
                speechRecognizer.destroy();
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
                    // NO relanzar en bucle continuo: evita que Android emita pitidos constantes y parpadee el icono verde
                }

                @Override
                public void onResults(Bundle results) {
                    isListening = false;
                    processVoiceResults(results);
                    // Sesión completada: no relanzar en bucle para mantener el teléfono en silencio como ChatGPT/Gemini
                }

                @Override
                public void onPartialResults(Bundle partialResults) {
                    processPartialVoiceResults(partialResults);
                }

                @Override
                public void onEvent(int eventType, Bundle params) {}
            });
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private synchronized void startListeningSafely() {
        if (!isAppInForeground || speechRecognizer == null || speechIntent == null) return;
        try {
            speechRecognizer.startListening(speechIntent);
        } catch (Exception ignored) {}
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
                    dispatchVoiceCommandToWeb(cmd);
                } else {
                    notifyWebWakeWordActivated();
                }
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
            if (isWakeWordMatch(lower)) {
                triggerHapticFeedback(60);
                notifyWebWakeWordActivated();
                return;
            }
        }
    }

    private boolean isWakeWordMatch(String text) {
        return text.contains("alberth") || text.contains("alberto") ||
               text.contains("albert")  || text.contains("álbert")  ||
               text.contains("álberth") || text.contains("alverth") ||
               text.contains("alverto");
    }

    private String extractCommand(String text) {
        return text.replaceAll("^.*?(alberth|alberto|albert|álbert|álberth|alverth|alverto)\\s*", "").trim();
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

    private void notifyWebWakeWordActivated() {
        runOnUiThread(() -> {
            if (webView != null) {
                webView.evaluateJavascript("if (window.onNativeWakeWord) { window.onNativeWakeWord(); }", null);
            }
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        isAppInForeground = true;
    }

    @Override
    protected void onPause() {
        super.onPause();
        isAppInForeground = false;
        voiceHandler.removeCallbacksAndMessages(null);
        if (speechRecognizer != null) {
            try {
                speechRecognizer.stopListening();
                speechRecognizer.cancel();
            } catch (Exception ignored) {}
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
            return "6.1-Quantum";
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
        public void restartVoiceAssistant() {
            runOnUiThread(() -> {
                if (isAppInForeground) {
                    startListeningSafely();
                }
            });
        }
    }
}
