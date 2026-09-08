import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Modal,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Image,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Haptics from 'expo-haptics';
import * as Speech from 'expo-speech';
import { Audio } from 'expo-av';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { WebView } from 'react-native-webview';
import {
  Mic,
  Send,
  Settings as SettingsIcon,
  Check,
  RefreshCw,
  Volume2,
  VolumeX,
  AlertCircle,
  Phone,
  MessageSquare,
  User,
  Laptop,
  Camera,
  MapPin,
  Circle,
} from 'lucide-react-native';

interface Message {
  id: string;
  role: 'user' | 'alberth' | 'system';
  content: string;
  ts: string;
  audio_url?: string;
  image_url?: string;
}

// ─── Default Configuration & Tunnels ───────────────────────────────────────
const DEFAULT_SERVER_URL = 'https://af3d1d560697b0.lhr.life';
const DEFAULT_TOKEN = 'token-seguro-1781561473';

// ─── HTML5 / Three.js 3D Quantum Core Particle Sphere HTML ───────────────
const THREE_HTML = `
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<style>
  * { margin:0; padding:0; box-sizing:border-box; overflow:hidden; }
  body, html { width:100%; height:100%; background-color:#040711; }
  #canvas-container { width:100%; height:100%; position:relative; }
  canvas { width:100%; height:100%; display:block; }
  
  .blueprint-grid {
    position: fixed; inset: 0;
    background-image: 
      linear-gradient(rgba(0, 240, 255, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0, 240, 255, 0.04) 1px, transparent 1px);
    background-size: 24px 24px;
    pointer-events: none; z-index: 1;
  }
  .ambient-flare {
    position: fixed; left: 50%; top: 50%;
    transform: translate(-50%, -50%);
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(0, 240, 255, 0.22) 0%, rgba(0, 100, 255, 0.08) 50%, transparent 75%);
    pointer-events: none; z-index: 1; filter: blur(20px);
  }
</style>
</head>
<body>
<div class="blueprint-grid"></div>
<div class="ambient-flare"></div>
<div id="canvas-container"></div>

<script>
  let scene, camera, renderer, particlesMesh, ringMesh1, ringMesh2, coreMesh;
  const PARTICLE_COUNT = 1800;
  let particlePositions, particleBasePos, particleColors;
  let animState = "idle"; // idle, listening, thinking, speaking

  function init() {
    const container = document.getElementById("canvas-container");
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.z = 210;

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 1. Fibonacci Sphere Particles
    const geometry = new THREE.BufferGeometry();
    particlePositions = new Float32Array(PARTICLE_COUNT * 3);
    particleBasePos = new Float32Array(PARTICLE_COUNT * 3);
    particleColors = new Float32Array(PARTICLE_COUNT * 3);

    const radius = 58;
    const phi = Math.PI * (3 - Math.sqrt(5));

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const y = 1 - (i / (PARTICLE_COUNT - 1)) * 2;
      const rad = Math.sqrt(1 - y * y);
      const theta = phi * i;

      const rNoise = radius * (0.88 + Math.random() * 0.24);
      const x = Math.cos(theta) * rad * rNoise;
      const posY = y * rNoise;
      const z = Math.sin(theta) * rad * rNoise;

      const idx = i * 3;
      particlePositions[idx] = x;
      particlePositions[idx + 1] = posY;
      particlePositions[idx + 2] = z;

      particleBasePos[idx] = x;
      particleBasePos[idx + 1] = posY;
      particleBasePos[idx + 2] = z;

      const isBright = Math.random() > 0.85;
      particleColors[idx] = isBright ? 0.9 : 0.0;
      particleColors[idx + 1] = isBright ? 1.0 : 0.94;
      particleColors[idx + 2] = 1.0;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    // Particle Texture
    const pTexCanvas = document.createElement('canvas');
    pTexCanvas.width = 64; pTexCanvas.height = 64;
    const pCtx = pTexCanvas.getContext('2d');
    const pGrad = pCtx.createRadialGradient(32, 32, 0, 32, 32, 32);
    pGrad.addColorStop(0, 'rgba(255,255,255,1)');
    pGrad.addColorStop(0.3, 'rgba(0,240,255,0.85)');
    pGrad.addColorStop(0.7, 'rgba(0,180,255,0.25)');
    pGrad.addColorStop(1, 'rgba(0,0,0,0)');
    pCtx.fillStyle = pGrad; pCtx.fillRect(0, 0, 64, 64);

    const particleTexture = new THREE.CanvasTexture(pTexCanvas);

    const material = new THREE.PointsMaterial({
      size: 4.2,
      map: particleTexture,
      vertexColors: true,
      transparent: true,
      opacity: 0.88,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    particlesMesh = new THREE.Points(geometry, material);
    scene.add(particlesMesh);

    // 2. Gimbal Rings
    const ringGeo1 = new THREE.RingGeometry(76, 78, 64);
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: 0x00f0ff, side: THREE.DoubleSide, transparent: true, opacity: 0.35, wireframe: true
    });
    ringMesh1 = new THREE.Mesh(ringGeo1, ringMat1);
    ringMesh1.rotation.x = Math.PI / 4;
    scene.add(ringMesh1);

    const ringGeo2 = new THREE.RingGeometry(86, 87.5, 48);
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x00b4d8, side: THREE.DoubleSide, transparent: true, opacity: 0.25, wireframe: true
    });
    ringMesh2 = new THREE.Mesh(ringGeo2, ringMat2);
    ringMesh2.rotation.y = Math.PI / 3;
    scene.add(ringMesh2);

    // 3. Inner Core Sphere
    const coreGeo = new THREE.SphereGeometry(24, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff, transparent: true, opacity: 0.55, wireframe: true
    });
    coreMesh = new THREE.Mesh(coreGeo, coreMat);
    scene.add(coreMesh);

    window.addEventListener('resize', onWindowResize);
    animate(0);
  }

  function onWindowResize() {
    const container = document.getElementById("canvas-container");
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  function animate(time) {
    requestAnimationFrame(animate);
    const t = time * 0.001;

    let rotSpeed = 0.004;
    let pulseScale = 1.0;

    if (animState === "listening") {
      rotSpeed = 0.015;
      pulseScale = 1.0 + Math.sin(t * 8) * 0.12;
    } else if (animState === "thinking") {
      rotSpeed = 0.025;
      pulseScale = 1.0 + Math.sin(t * 12) * 0.18;
    } else if (animState === "speaking") {
      rotSpeed = 0.012;
      pulseScale = 1.0 + Math.sin(t * 6) * 0.15;
    } else {
      pulseScale = 1.0 + Math.sin(t * 2) * 0.04;
    }

    if (particlesMesh) {
      particlesMesh.rotation.y += rotSpeed;
      particlesMesh.rotation.x = Math.sin(t * 0.5) * 0.15;
      particlesMesh.scale.set(pulseScale, pulseScale, pulseScale);
    }
    if (ringMesh1) {
      ringMesh1.rotation.z += rotSpeed * 1.5;
      ringMesh1.rotation.y += rotSpeed * 0.8;
    }
    if (ringMesh2) {
      ringMesh2.rotation.z -= rotSpeed * 1.2;
      ringMesh2.rotation.x += rotSpeed * 0.9;
    }
    if (coreMesh) {
      coreMesh.rotation.y -= rotSpeed * 2.0;
      coreMesh.scale.set(pulseScale, pulseScale, pulseScale);
    }

    renderer.render(scene, camera);
  }

  window.setState = function(state) {
    animState = state;
  };

  init();
</script>
</body>
</html>
`;

export default function App() {
  const insets = useSafeAreaInsets();

  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER_URL);
  const [accessToken, setAccessToken] = useState(DEFAULT_TOKEN);
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Desconectado');
  const [hudState, setHudState] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'alberth',
      content: '¡Hola Señor Danny! Soy Alberth. Su interfaz móvil Quantum HUD 3D está en línea. ¿En qué le puedo asistir hoy?',
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Cámara / Visión
  const [showCamera, setShowCamera] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const cameraRef = useRef<any>(null);
  const webViewRef = useRef<any>(null);

  const ws = useRef<WebSocket | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const currentUrl = useRef(DEFAULT_SERVER_URL);
  const currentToken = useRef(DEFAULT_TOKEN);
  const responseTimeout = useRef<any>(null);
  const lastUserMessage = useRef<string>('');

  // ─── Load Settings ────────────────────────────────────────────────────────
  useEffect(() => {
    async function loadSettings() {
      try {
        const storedUrl = await AsyncStorage.getItem('@alberth_server_url');
        const initialUrl = storedUrl && storedUrl.trim() ? storedUrl.trim() : DEFAULT_SERVER_URL;
        setServerUrl(initialUrl);
        currentUrl.current = initialUrl;

        const storedToken = await AsyncStorage.getItem('@alberth_token');
        const initialToken = storedToken && storedToken.trim() ? storedToken.trim() : DEFAULT_TOKEN;
        setAccessToken(initialToken);
        currentToken.current = initialToken;

        const storedMute = await AsyncStorage.getItem('@alberth_mute');
        if (storedMute !== null) setIsMuted(storedMute === 'true');
      } catch (e) {
        console.error('Error loading settings:', e);
      }
    }
    loadSettings();
  }, []);

  // ─── Audio Setup ──────────────────────────────────────────────────────────
  useEffect(() => {
    async function setupAudio() {
      try {
        const status = await Audio.requestPermissionsAsync();
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });
        if (!status.granted) {
          Alert.alert('Permiso Requerido', 'Alberth necesita acceso al micrófono para interactuar por voz.');
        }
      } catch (e) {
        console.warn('[Audio setup error]', e);
      }
    }
    setupAudio();
  }, []);

  // Update 3D WebView state
  const update3DState = (stateName: string) => {
    if (webViewRef.current) {
      webViewRef.current.injectJavaScript(`if(window.setState) window.setState('${stateName}'); true;`);
    }
  };

  useEffect(() => {
    if (isRecording) {
      setHudState('listening');
      update3DState('listening');
    } else if (isThinking) {
      setHudState('thinking');
      update3DState('thinking');
    } else {
      setHudState('idle');
      update3DState('idle');
    }
  }, [isRecording, isThinking]);

  // ─── WebSocket Connection ────────────────────────────────────────────────
  const connectWebSocket = useCallback((url?: string) => {
    const targetUrl = url ?? currentUrl.current;
    if (!targetUrl) return;

    if (ws.current) {
      ws.current.onclose = null;
      ws.current.close();
      ws.current = null;
    }

    setStatusMessage('Conectando...');

    let wsProto = 'ws://';
    let cleanUrl = targetUrl.replace(/^(https?:\/\/)/, '');
    if (targetUrl.startsWith('https://')) wsProto = 'wss://';
    cleanUrl = cleanUrl.replace(/\/$/, '');
    const token = currentToken.current;

    try {
      const socketUrl = `${wsProto}${cleanUrl}/ws?token=${encodeURIComponent(token)}`;
      console.log('[WS] Connecting to:', socketUrl);
      const socket = new WebSocket(socketUrl);
      ws.current = socket;

      socket.onopen = () => {
        console.log('[WS] Connected successfully');
        setIsConnected(true);
        setStatusMessage('🟢 EN LÍNEA');
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      };

      socket.onmessage = async (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'message') {
            if (responseTimeout.current) {
              clearTimeout(responseTimeout.current);
              responseTimeout.current = null;
            }
            const incoming = data.message;
            const content = incoming.content;

            if (incoming.role === 'user' && content === lastUserMessage.current) {
              lastUserMessage.current = '';
              return;
            }

            const msg: Message = {
              id: Math.random().toString(),
              role: incoming.role === 'user' ? 'user' : 'alberth',
              content,
              ts: incoming.ts || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              audio_url: incoming.audio_url,
              image_url: incoming.image_url,
            };
            setMessages(prev => [...prev, msg]);
            setIsThinking(false);

            if (msg.role === 'alberth') {
              setHudState('speaking');
              update3DState('speaking');
              setTimeout(() => { setHudState('idle'); update3DState('idle'); }, 4000);

              if (msg.audio_url && !isMuted) {
                try {
                  if (soundRef.current) {
                    await soundRef.current.unloadAsync();
                    soundRef.current = null;
                  }
                  const { sound } = await Audio.Sound.createAsync(
                    { uri: msg.audio_url },
                    { shouldPlay: true }
                  );
                  soundRef.current = sound;
                } catch (audioErr) {
                  console.warn('[Audio] Remote playback fallback to TTS:', audioErr);
                  await handleVoiceAndCommands(msg.content);
                }
              } else {
                await handleVoiceAndCommands(msg.content);
              }
            }
          } else if (data.type === 'thinking') {
            setIsThinking(data.active);
          }
        } catch (err) {
          console.error('[WS] Parse error:', err);
        }
      };

      socket.onerror = (err) => {
        console.warn('[WS] Connection error');
        setIsConnected(false);
        setStatusMessage('🔴 Error de Conexión');
      };

      socket.onclose = () => {
        console.log('[WS] Closed');
        setIsConnected(false);
        setStatusMessage('🔴 Desconectado');
      };
    } catch (err) {
      console.error('[WS] Error initializing WebSocket:', err);
      setIsConnected(false);
      setStatusMessage('🔴 Error en URL');
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws.current) ws.current.close();
    };
  }, [connectWebSocket]);

  // ─── Voice & Text Execution ──────────────────────────────────────────────
  const handleVoiceAndCommands = async (text: string) => {
    if (isMuted) return;
    Speech.stop();
    Speech.speak(text, { language: 'es-ES', rate: 1.0, pitch: 1.0 });
  };

  const handleSendText = () => {
    if (!inputText.trim()) return;
    const text = inputText.trim();
    setInputText('');
    lastUserMessage.current = text;

    const userMsg: Message = {
      id: Math.random().toString(),
      role: 'user',
      content: text,
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsThinking(true);

    if (responseTimeout.current) clearTimeout(responseTimeout.current);
    responseTimeout.current = setTimeout(() => {
      setIsThinking(false);
      setStatusMessage('⚠️ Sin respuesta');
    }, 12_000);

    ws.current?.send(JSON.stringify({ type: 'text', text }));
  };

  // ─── Audio Recording (expo-av) ────────────────────────────────────────────
  const startRecording = async () => {
    try {
      Speech.stop();
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);

      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Sin permiso', 'Habilite el micrófono en Ajustes del sistema.');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      recordingRef.current = recording;
      setIsRecording(true);
      console.log('[Audio] Recording started');
    } catch (err: any) {
      console.error('[Audio] Start error:', err);
      Alert.alert('Error', `No se pudo iniciar la grabación: ${err.message}`);
    }
  };

  const stopRecording = async () => {
    if (!isRecording || !recordingRef.current) return;
    setIsRecording(false);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

    try {
      const recording = recordingRef.current;
      recordingRef.current = null;
      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      const uri = recording.getURI();
      console.log('[Audio] Saved at:', uri);

      if (!uri) {
        Alert.alert('Error', 'No se pudo obtener el archivo de audio.');
        return;
      }
      await uploadAudio(uri);
    } catch (err: any) {
      console.error('[Audio] Stop error:', err);
      Alert.alert('Error', `Error al finalizar la grabación: ${err.message}`);
    }
  };

  const uploadAudio = async (fileUri: string) => {
    if (!isConnected) {
      Alert.alert('Desconectado', 'No hay conexión al servidor para enviar audio.');
      return;
    }
    try {
      setIsThinking(true);
      const cleanUrl = currentUrl.current.replace(/\/$/, '');
      const uploadUrl = `${cleanUrl}/audio`;

      const formData = new FormData();
      formData.append('file', {
        uri: fileUri,
        type: 'audio/m4a',
        name: 'recording.m4a',
      } as any);

      const res = await fetch(uploadUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentToken.current}`,
          'Accept': 'application/json',
        },
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error subiendo audio');
    } catch (err: any) {
      setIsThinking(false);
      Alert.alert('Error de Audio', err.message);
    }
  };

  // ─── Camera Vision ────────────────────────────────────────────────────────
  const takePictureAndUpload = async () => {
    if (!cameraPermission?.granted) {
      const perm = await requestCameraPermission();
      if (!perm.granted) {
        Alert.alert('Sin Permiso', 'Se requiere acceso a la cámara.');
        return;
      }
    }
    if (!cameraRef.current) return;

    try {
      setIsUploadingImage(true);
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.7, base64: true });
      setShowCamera(false);

      const userMsg: Message = {
        id: Math.random().toString(),
        role: 'user',
        content: '📷 [Captura de cámara enviada]',
        ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        image_url: photo.uri,
      };
      setMessages(prev => [...prev, userMsg]);
      setIsThinking(true);

      const cleanUrl = currentUrl.current.replace(/\/$/, '');
      const uploadUrl = `${cleanUrl}/upload-vision`;
      const formData = new FormData();
      formData.append('file', {
        uri: photo.uri,
        type: 'image/jpeg',
        name: 'vision_capture.jpg',
      } as any);

      const res = await fetch(uploadUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentToken.current}`,
          'Accept': 'application/json',
        },
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error subiendo imagen');
    } catch (err: any) {
      setIsThinking(false);
      Alert.alert('Error de Visión', err.message);
    } finally {
      setIsUploadingImage(false);
    }
  };

  // ─── Settings Modal ───────────────────────────────────────────────────────
  const saveSettings = async () => {
    try {
      const cleanUrl = serverUrl.trim().replace(/\/$/, '');
      const cleanToken = accessToken.trim();

      await AsyncStorage.setItem('@alberth_server_url', cleanUrl);
      await AsyncStorage.setItem('@alberth_token', cleanToken);
      await AsyncStorage.setItem('@alberth_mute', String(isMuted));

      currentUrl.current = cleanUrl;
      currentToken.current = cleanToken;

      setShowSettings(false);
      connectWebSocket(cleanUrl);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e) {
      Alert.alert('Error', 'No se pudieron guardar los ajustes.');
    }
  };

  const resetDefaults = async () => {
    setServerUrl(DEFAULT_SERVER_URL);
    setAccessToken(DEFAULT_TOKEN);
    currentUrl.current = DEFAULT_SERVER_URL;
    currentToken.current = DEFAULT_TOKEN;
    await AsyncStorage.setItem('@alberth_server_url', DEFAULT_SERVER_URL);
    await AsyncStorage.setItem('@alberth_token', DEFAULT_TOKEN);
    Alert.alert('Valores Restablecidos', 'Se han restaurado la URL y el Token predeterminados.');
  };

  useEffect(() => {
    scrollViewRef.current?.scrollToEnd({ animated: true });
  }, [messages, isThinking]);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" backgroundColor="#040711" />

      {/* ─── Top Header Bar ───────────────────────────────────────────────── */}
      <View style={styles.header}>
        <View style={styles.brandContainer}>
          <Text style={styles.brandTitle}>ALBERTH</Text>
          <Text style={styles.brandSub}>QUANTUM HUD 3D</Text>
        </View>

        <View style={styles.headerRight}>
          <TouchableOpacity
            style={[styles.statusBadge, isConnected ? styles.statusOnline : styles.statusOffline]}
            onPress={() => connectWebSocket()}
          >
            <Circle size={8} fill={isConnected ? '#00ffaa' : '#ff2a5f'} color={isConnected ? '#00ffaa' : '#ff2a5f'} />
            <Text style={styles.statusBadgeText}>{statusMessage}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.iconBtn} onPress={() => setIsMuted(!isMuted)}>
            {isMuted ? <VolumeX size={20} color="#ff2a5f" /> : <Volume2 size={20} color="#00f0ff" />}
          </TouchableOpacity>

          <TouchableOpacity style={styles.iconBtn} onPress={() => setShowSettings(true)}>
            <SettingsIcon size={20} color="#00f0ff" />
          </TouchableOpacity>
        </View>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        {/* ─── 3D Holographic Model Viewer (Three.js WebGL WebView) ─────── */}
        <View style={styles.modelContainer}>
          <WebView
            ref={webViewRef}
            originWhitelist={['*']}
            source={{ html: THREE_HTML }}
            style={styles.webView}
            scrollEnabled={false}
            overScrollMode="never"
            bounces={false}
          />
          <View style={styles.modelOverlay}>
            <View style={styles.statePill}>
              <View style={[styles.stateDot, isRecording && styles.dotRecording, isThinking && styles.dotThinking]} />
              <Text style={styles.stateText}>
                {isRecording ? 'ESCUCHANDO ORDEN' : isThinking ? 'PROCESANDO RESPUESTA' : 'EN LÍNEA · ESPERANDO ORDEN'}
              </Text>
            </View>
          </View>
        </View>

        {/* ─── Sci-Fi Chat Console ────────────────────────────────────────── */}
        <View style={styles.consoleContainer}>
          <ScrollView
            ref={scrollViewRef}
            contentContainerStyle={styles.messagesContainer}
            showsVerticalScrollIndicator={false}
          >
            {messages.map(msg => (
              <View
                key={msg.id}
                style={[
                  styles.msgRow,
                  msg.role === 'user' ? styles.userRow : styles.alberthRow,
                ]}
              >
                <View
                  style={[
                    styles.msgBubble,
                    msg.role === 'user' ? styles.userBubble : styles.alberthBubble,
                  ]}
                >
                  <Text style={styles.msgRoleText}>
                    {msg.role === 'user' ? 'SEÑOR DANNY' : 'ALBERTH'} · {msg.ts}
                  </Text>
                  {msg.image_url ? (
                    <Image source={{ uri: msg.image_url }} style={styles.msgImage} />
                  ) : null}
                  <Text style={styles.msgContentText}>{msg.content}</Text>
                </View>
              </View>
            ))}

            {isThinking && (
              <View style={[styles.msgRow, styles.alberthRow]}>
                <View style={[styles.msgBubble, styles.alberthBubble, styles.thinkingBubble]}>
                  <ActivityIndicator size="small" color="#00f0ff" />
                  <Text style={[styles.msgContentText, { marginLeft: 8, color: '#00f0ff' }]}>
                    Alberth procesando...
                  </Text>
                </View>
              </View>
            )}
          </ScrollView>
        </View>

        {/* ─── Bottom Voice & Action Toolbar ─────────────────────────────── */}
        <View style={styles.toolbar}>
          <TouchableOpacity
            style={styles.quickBtn}
            onPress={() => {
              if (cameraPermission?.granted) {
                setShowCamera(true);
              } else {
                requestCameraPermission();
              }
            }}
          >
            <Camera size={18} color="#00f0ff" />
            <Text style={styles.quickBtnText}>VERME</Text>
          </TouchableOpacity>

          <View style={styles.inputBox}>
            <TextInput
              style={styles.textInput}
              value={inputText}
              onChangeText={setInputText}
              placeholder="Transmitir comando o hablar con Alberth..."
              placeholderTextColor="#51627b"
              onSubmitEditing={handleSendText}
              returnKeyType="send"
            />
            <TouchableOpacity style={styles.sendBtn} onPress={handleSendText}>
              <Send size={18} color="#040711" />
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={[styles.micBtn, isRecording && styles.micBtnRecording]}
            onPressIn={startRecording}
            onPressOut={stopRecording}
          >
            <Mic size={24} color={isRecording ? '#040711' : '#00f0ff'} />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* ─── Settings Modal ───────────────────────────────────────────────── */}
      <Modal visible={showSettings} animationType="slide" transparent={true}>
        <View style={styles.modalBg}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>CONFIGURACIÓN ALBERTH</Text>
            <Text style={styles.modalSub}>Ajustes de Conexión y Gateway</Text>

            <Text style={styles.inputLabel}>URL del Servidor / Túnel HTTPS</Text>
            <TextInput
              style={styles.modalInput}
              value={serverUrl}
              onChangeText={setServerUrl}
              autoCapitalize="none"
              keyboardType="url"
            />

            <Text style={styles.inputLabel}>Token de Acceso (Bearer)</Text>
            <TextInput
              style={styles.modalInput}
              value={accessToken}
              onChangeText={setAccessToken}
              autoCapitalize="none"
              secureTextEntry={false}
            />

            <TouchableOpacity style={styles.resetBtn} onPress={resetDefaults}>
              <RefreshCw size={16} color="#f0c060" />
              <Text style={styles.resetBtnText}>Restablecer Valores Predeterminados</Text>
            </TouchableOpacity>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setShowSettings(false)}>
                <Text style={styles.cancelBtnText}>Cancelar</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.saveBtn} onPress={saveSettings}>
                <Check size={18} color="#040711" />
                <Text style={styles.saveBtnText}>Guardar y Conectar</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ─── Camera Modal for Vision ──────────────────────────────────────── */}
      <Modal visible={showCamera} animationType="fade" transparent={false}>
        <SafeAreaView style={{ flex: 1, backgroundColor: '#000' }}>
          {cameraPermission?.granted ? (
            <CameraView style={{ flex: 1 }} facing="front" ref={cameraRef}>
              <View style={styles.cameraOverlay}>
                <TouchableOpacity style={styles.closeCamBtn} onPress={() => setShowCamera(false)}>
                  <Text style={styles.closeCamText}>CERRAR</Text>
                </TouchableOpacity>

                <TouchableOpacity style={styles.captureBtn} onPress={takePictureAndUpload}>
                  <View style={styles.captureInner} />
                </TouchableOpacity>
              </View>
            </CameraView>
          ) : (
            <View style={styles.centerContainer}>
              <Text style={{ color: '#fff', marginBottom: 12 }}>Se requiere permiso de cámara</Text>

              <TouchableOpacity style={styles.saveBtn} onPress={requestCameraPermission}>
                <Text style={styles.saveBtnText}>Conceder Permiso</Text>
              </TouchableOpacity>
            </View>
          )}
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

// ─── Sci-Fi Quantum HUD Styles ───────────────────────────────────────────────
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#040711',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justify: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0, 240, 255, 0.2)',
    backgroundColor: '#060c1a',
  },
  brandContainer: {
    flexDirection: 'column',
  },
  brandTitle: {
    fontFamily: Platform.OS === 'ios' ? 'Orbitron' : 'sans-serif-medium',
    fontWeight: '900',
    fontSize: 18,
    color: '#00f0ff',
    letterSpacing: 2,
  },
  brandSub: {
    fontSize: 9,
    color: '#8b9bb4',
    letterSpacing: 1.5,
    marginTop: -2,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    borderWidth: 1,
    gap: 6,
  },
  statusOnline: {
    borderColor: 'rgba(0, 255, 170, 0.4)',
    backgroundColor: 'rgba(0, 255, 170, 0.08)',
  },
  statusOffline: {
    borderColor: 'rgba(255, 42, 95, 0.4)',
    backgroundColor: 'rgba(255, 42, 95, 0.08)',
  },
  statusBadgeText: {
    fontSize: 11,
    color: '#f0f6fc',
    fontWeight: '600',
  },
  iconBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.2)',
  },

  // 3D Model Container
  modelContainer: {
    height: 240,
    width: '100%',
    position: 'relative',
    backgroundColor: '#040711',
  },
  webView: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  modelOverlay: {
    position: 'absolute',
    bottom: 8,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  statePill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.4)',
    backgroundColor: 'rgba(4, 7, 17, 0.85)',
    gap: 8,
  },
  stateDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#00f0ff',
  },
  dotRecording: {
    backgroundColor: '#ff2a5f',
  },
  dotThinking: {
    backgroundColor: '#f0c060',
  },
  stateText: {
    fontSize: 11,
    color: '#00f0ff',
    fontWeight: '700',
    letterSpacing: 1,
  },

  // Console Chat
  consoleContainer: {
    flex: 1,
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  messagesContainer: {
    paddingBottom: 16,
    gap: 10,
  },
  msgRow: {
    width: '100%',
    flexDirection: 'row',
  },
  userRow: {
    justifyContent: 'flex-end',
  },
  alberthRow: {
    justifyContent: 'flex-start',
  },
  msgBubble: {
    maxWidth: '85%',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
  },
  userBubble: {
    backgroundColor: 'rgba(240, 192, 96, 0.1)',
    borderColor: 'rgba(240, 192, 96, 0.4)',
  },
  alberthBubble: {
    backgroundColor: 'rgba(6, 12, 26, 0.85)',
    borderColor: 'rgba(0, 240, 255, 0.3)',
  },
  thinkingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  msgRoleText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#8b9bb4',
    marginBottom: 4,
    letterSpacing: 1,
  },
  msgContentText: {
    fontSize: 14,
    color: '#f0f6fc',
    lineHeight: 20,
  },
  msgImage: {
    width: 200,
    height: 140,
    borderRadius: 8,
    marginBottom: 6,
  },

  // Toolbar
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 8,
    backgroundColor: '#060c1a',
    borderTopWidth: 1,
    borderTopColor: 'rgba(0, 240, 255, 0.2)',
  },
  quickBtn: {
    alignItems: 'center',
    justify: 'center',
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    backgroundColor: 'rgba(0, 240, 255, 0.06)',
  },
  quickBtnText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#00f0ff',
    marginTop: 2,
  },
  inputBox: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(4, 7, 17, 0.9)',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    paddingHorizontal: 12,
  },
  textInput: {
    flex: 1,
    color: '#f0f6fc',
    fontSize: 13,
    paddingVertical: 8,
  },
  sendBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#00f0ff',
    alignItems: 'center',
    justify: 'center',
    marginLeft: 6,
  },
  micBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0, 240, 255, 0.12)',
    borderWidth: 1.5,
    borderColor: '#00f0ff',
    alignItems: 'center',
    justify: 'center',
  },
  micBtnRecording: {
    backgroundColor: '#ff2a5f',
    borderColor: '#ff2a5f',
  },

  // Modal
  modalBg: {
    flex: 1,
    backgroundColor: 'rgba(2, 4, 9, 0.85)',
    justify: 'center',
    paddingHorizontal: 20,
  },
  modalCard: {
    backgroundColor: '#060c1a',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#00f0ff',
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '900',
    color: '#00f0ff',
    letterSpacing: 1.5,
  },
  modalSub: {
    fontSize: 11,
    color: '#8b9bb4',
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 11,
    color: '#f0f6fc',
    fontWeight: '600',
    marginTop: 10,
    marginBottom: 4,
  },
  modalInput: {
    backgroundColor: '#040711',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    borderRadius: 8,
    color: '#f0f6fc',
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13,
  },
  resetBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 14,
    gap: 6,
  },
  resetBtnText: {
    fontSize: 11,
    color: '#f0c060',
    fontWeight: '600',
  },
  modalActions: {
    flexDirection: 'row',
    justify: 'flex-end',
    marginTop: 20,
    gap: 10,
  },
  cancelBtn: {
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  cancelBtnText: {
    color: '#8b9bb4',
    fontSize: 13,
  },
  saveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#00f0ff',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  saveBtnText: {
    color: '#040711',
    fontWeight: '700',
    fontSize: 13,
  },

  // Camera Modal
  cameraOverlay: {
    flex: 1,
    justify: 'space-between',
    padding: 20,
  },
  closeCamBtn: {
    alignSelf: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  closeCamText: {
    color: '#00f0ff',
    fontWeight: '700',
    fontSize: 12,
  },
  captureBtn: {
    width: 70,
    height: 70,
    borderRadius: 35,
    borderWidth: 4,
    borderColor: '#00f0ff',
    alignSelf: 'center',
    alignItems: 'center',
    justify: 'center',
  },
  captureInner: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: '#00f0ff',
  },
  centerContainer: {
    flex: 1,
    alignItems: 'center',
    justify: 'center',
  },
});
