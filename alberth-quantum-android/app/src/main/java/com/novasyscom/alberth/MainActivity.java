package com.novasyscom.alberth;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.DialogInterface;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.Vibrator;
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
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private static final String PREFS_NAME = "AlberthPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_TUNNEL_URL = "https://interact-deeply-asn-tracy.trycloudflare.com/";
    private static final int PERMISSION_REQ_CODE = 101;

    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private LinearLayout offlineOverlay;
    private TextView errorText;
    private SharedPreferences prefs;
    private long backPressedTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Barra de estado y navegación en tema oscuro Sci-Fi
        configureSystemBars();

        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);

        webView = findViewById(R.id.webView);
        swipeRefresh = findViewById(R.id.swipeRefresh);
        offlineOverlay = findViewById(R.id.offlineOverlay);
        errorText = findViewById(R.id.errorText);
        Button btnRetry = findViewById(R.id.btnRetry);
        Button btnConfig = findViewById(R.id.btnConfig);

        setupSwipeRefresh();
        setupWebView();
        requestHardwarePermissions();

        btnRetry.setOnClickListener(v -> loadActiveUrl());
        btnConfig.setOnClickListener(v -> showConfigDialog());

        loadActiveUrl();
    }

    private void configureSystemBars() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            Window window = getWindow();
            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            window.setStatusBarColor(Color.parseColor("#040711"));
            window.setNavigationBarColor(Color.parseColor("#040711"));
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
            }
        }
    }

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

    // Bridge de JavaScript para comunicación bidireccional
    public class AlberthBridge {
        @JavascriptInterface
        public String getAppVersion() {
            return "6.0-Quantum";
        }

        @JavascriptInterface
        public void vibrateDevice(int durationMs) {
            try {
                Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v != null) {
                    v.vibrate(durationMs > 0 ? durationMs : 50);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @JavascriptInterface
        public void openConfig() {
            runOnUiThread(MainActivity.this::showConfigDialog);
        }

        @JavascriptInterface
        public void showNativeToast(String msg) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, msg, Toast.LENGTH_SHORT).show());
        }
    }
}
