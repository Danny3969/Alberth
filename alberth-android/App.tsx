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
  Switch,
  Alert,
  Animated,
  Easing,
  Dimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Haptics from 'expo-haptics';
import * as Speech from 'expo-speech';
import { useAudioRecorder, AudioModule, RecordingPresets } from 'expo-audio';
import {
  Mic,
  Send,
  Settings as SettingsIcon,
  Check,
  RefreshCw,
  Volume2,
  VolumeX,
  AlertCircle,
  Cpu,
  ShieldCheck,
  Eye,
  Play,
  Sparkles,
  Smartphone,
  Radio,
  Terminal,
  Activity,
  User,
} from 'lucide-react-native';
import { androidSystemHelper } from './android_system_helper';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// ─── CONFIGURACIÓN PREDETERMINADA DE FÁBRICA ─────────────────────────────────
const DEFAULT_SERVER_URL = 'https://knee-valium-vegetarian-ethernet.trycloudflare.com';
const DEFAULT_GATEWAY_TOKEN = 'token-seguro-1781561473';
const MAX_RETRIES = 5;
const RETRY_DELAY_MS = 2500;

interface Message {
  id: string;
  role: 'user' | 'alberth' | 'system';
  content: string;
  ts: string;
}

type AssistantState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING';

export default function App() {
  const insets = useSafeAreaInsets();

  // Estados de Servidor y Credenciales
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER_URL);
  const [gatewayToken, setGatewayToken] = useState(DEFAULT_GATEWAY_TOKEN);
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Iniciando Quantum Core...');
  const [assistantState, setAssistantState] = useState<AssistantState>('IDLE');

  // Estados de Permisos y Sistema OS
  const [isAccessibilityActive, setIsAccessibilityActive] = useState(false);
  const [isDefaultAssistActive, setIsDefaultAssistActive] = useState(false);

  // Chat y Mensajes
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'alberth',
      content: '⚡ Quantum Core en línea, Señor Danny. Alberth v4.0 listo como su Asistente de Sistema total. Conexión automática establecida.',
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Animaciones Quantum Reactor
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const [waveHeights, setWaveHeights] = useState([12, 8, 20, 6, 24, 10, 16, 8, 18, 14]);

  // Referencias de control
  const ws = useRef<WebSocket | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  const audioRecorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const waveTimer = useRef<any>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<any>(null);
  const responseTimeout = useRef<any>(null);
  const lastUserMessage = useRef<string>('');

  // ─── ANIMACIONES DE REACTOR ──────────────────────────────────────────────────
  useEffect(() => {
    // Rotación constante del HUD Reactor
    Animated.loop(
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 12000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();
  }, []);

  useEffect(() => {
    if (assistantState === 'LISTENING' || assistantState === 'THINKING' || assistantState === 'SPEAKING') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.22,
            duration: assistantState === 'LISTENING' ? 400 : 700,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1.0,
            duration: assistantState === 'LISTENING' ? 400 : 700,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      Animated.timing(pulseAnim, {
        toValue: 1.0,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [assistantState]);

  // Visualizador dinámico de ondas de audio
  useEffect(() => {
    if (isRecording || assistantState === 'SPEAKING' || assistantState === 'THINKING') {
      waveTimer.current = setInterval(() => {
        setWaveHeights(prev =>
          prev.map(() => {
            const min = isRecording ? 10 : 6;
            const max = isRecording ? 45 : assistantState === 'SPEAKING' ? 35 : 20;
            return Math.floor(Math.random() * (max - min + 1)) + min;
          })
        );
      }, 90);
    } else {
      if (waveTimer.current) clearInterval(waveTimer.current);
      setWaveHeights([8, 8, 8, 8, 8, 8, 8, 8, 8, 8]);
    }
    return () => {
      if (waveTimer.current) clearInterval(waveTimer.current);
    };
  }, [isRecording, assistantState]);

  // ─── CARGA INICIAL DE CONFIGURACIÓN Y SERVICIOS DEL SISTEMA ─────────────────
  useEffect(() => {
    async function initializeApp() {
      try {
        // Cargar o autoconfigurar URL del servidor
        let storedUrl = await AsyncStorage.getItem('@alberth_server_url');
        if (!storedUrl || storedUrl.trim() === '') {
          storedUrl = DEFAULT_SERVER_URL;
          await AsyncStorage.setItem('@alberth_server_url', DEFAULT_SERVER_URL);
        }
        setServerUrl(storedUrl);

        // Cargar o autoconfigurar Token de Gateway
        let storedToken = await AsyncStorage.getItem('@alberth_gateway_token');
        if (!storedToken || storedToken.trim() === '') {
          storedToken = DEFAULT_GATEWAY_TOKEN;
          await AsyncStorage.setItem('@alberth_gateway_token', DEFAULT_GATEWAY_TOKEN);
        }
        setGatewayToken(storedToken);

        const storedMute = await AsyncStorage.getItem('@alberth_mute');
        if (storedMute !== null) setIsMuted(storedMute === 'true');

        // Permisos de micrófono
        const perm = await AudioModule.requestRecordingPermissionsAsync();
        if (!perm.granted) {
          console.warn('[Perm] Permiso de audio no concedido de inmediato');
        }

        // Verificar estado de Asistente de IA y Accesibilidad
        checkSystemServices();

        // Conectar WebSocket con URL y Token precargados
        connectWebSocket(storedUrl, storedToken);
      } catch (err) {
        console.error('Error al inicializar app:', err);
      }
    }

    initializeApp();
  }, []);

  const checkSystemServices = async () => {
    const isAcc = await androidSystemHelper.isAccessibilityEnabled();
    setIsAccessibilityActive(isAcc);

    const isDef = await androidSystemHelper.isDefaultAssistant();
    setIsDefaultAssistActive(isDef);
  };

  // ─── WEBSOCKET QUANTUM GATEWAY ─────────────────────────────────────────────
  const connectWebSocket = useCallback((urlToUse?: string, tokenToUse?: string) => {
    const targetUrl = urlToUse ?? serverUrl;
    const targetToken = tokenToUse ?? gatewayToken;

    if (!targetUrl) return;

    if (retryTimer.current) {
      clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }

    if (ws.current) {
      ws.current.onclose = null;
      ws.current.close();
      ws.current = null;
    }

    setStatusMessage('Sincronizando Core...');
    setAssistantState('THINKING');

    let wsProto = targetUrl.startsWith('https://') ? 'wss://' : 'ws://';
    let cleanHost = targetUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');

    try {
      const socketUrl = `${wsProto}${cleanHost}/ws?token=${encodeURIComponent(targetToken)}`;
      console.log('[WS] Conectando a:', socketUrl);
      const socket = new WebSocket(socketUrl);
      ws.current = socket;

      socket.onopen = () => {
        console.log('[WS] Conexión establecida con éxito');
        retryCount.current = 0;
        setIsConnected(true);
        setStatusMessage('🟢 NÚCLEO EN LÍNEA');
        setAssistantState('IDLE');
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      };

      socket.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data);

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
            };

            setMessages(prev => [...prev, msg]);
            setAssistantState('IDLE');

            if (msg.role === 'alberth') {
              await executeSystemCommandsAndSpeak(msg.content);
            }
          } else if (data.type === 'thinking') {
            setAssistantState(data.active ? 'THINKING' : 'IDLE');
          } else if (data.type === 'history') {
            if (data.messages?.length > 0) {
              const loaded = data.messages.map((m: any, idx: number) => ({
                id: `hist_${idx}`,
                role: m.role,
                content: m.content,
                ts: m.ts || '',
              }));
              setMessages(loaded);
            }
          }
        } catch (e) {
          console.error('[WS] Error al procesar mensaje:', e);
        }
      };

      socket.onerror = (e) => {
        console.error('[WS] Error:', e);
        setIsConnected(false);
        setStatusMessage('🔴 Error de comunicación');
        setAssistantState('IDLE');
      };

      socket.onclose = (e) => {
        console.log('[WS] Cerrado código:', e.code, e.reason);
        setIsConnected(false);
        setAssistantState('IDLE');

        if (retryCount.current < MAX_RETRIES) {
          retryCount.current += 1;
          const delay = RETRY_DELAY_MS * retryCount.current;
          setStatusMessage(`🟡 Reconectando (${retryCount.current}/${MAX_RETRIES})...`);
          retryTimer.current = setTimeout(() => {
            connectWebSocket();
          }, delay);
        } else {
          setStatusMessage('🔴 Sin conexión al Servidor');
        }
      };
    } catch (err: any) {
      console.error('[WS] Error de inicialización:', err);
      setIsConnected(false);
      setStatusMessage('🔴 Error de Socket');
      setAssistantState('IDLE');
    }
  }, [serverUrl, gatewayToken]);

  // ─── PROCESADOR DE COMANDOS DEL SISTEMA Y VOZ ──────────────────────────────
  const executeSystemCommandsAndSpeak = async (content: string) => {
    // Detectar comandos [PHONE_CMD: {...}]
    const cmdRegex = /\[PHONE_CMD:\s*(\{.*?\})\]/g;
    let match: RegExpExecArray | null;
    let cleanSpeech = content.replace(/\[PHONE_CMD:\s*\{.*?\}\]/g, '').trim();

    while ((match = cmdRegex.exec(content)) !== null) {
      try {
        const cmd = JSON.parse(match[1]);
        appendSystemLog(`Comando OS recibido: ${cmd.action?.toUpperCase()}`);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        if (cmd.action === 'launch_app' || cmd.action === 'open_app') {
          const res = await androidSystemHelper.launchApp(cmd.appName || cmd.packageName);
          appendSystemLog(res.output);
        } else if (cmd.action === 'play_media' || cmd.action === 'play_song' || cmd.action === 'play_video') {
          const res = await androidSystemHelper.playMedia(cmd.query || cmd.title, cmd.mediaType || 'auto');
          appendSystemLog(res.output);
        } else if (cmd.action === 'read_screen') {
          const res = await androidSystemHelper.readScreenText();
          appendSystemLog(`Pantalla leída: ${res.output.slice(0, 100)}...`);
          cleanSpeech += `. En la pantalla veo lo siguiente: ${res.output}`;
        } else if (cmd.action === 'click_text') {
          const res = await androidSystemHelper.clickTextOnScreen(cmd.text);
          appendSystemLog(res.output);
        } else if (cmd.action === 'click_coords') {
          const res = await androidSystemHelper.performClick(cmd.x, cmd.y);
          appendSystemLog(res.output);
        } else if (cmd.action === 'swipe') {
          const res = await androidSystemHelper.performSwipe(cmd.x1, cmd.y1, cmd.x2, cmd.y2, cmd.duration || 300);
          appendSystemLog(res.output);
        } else if (cmd.action === 'home') {
          await androidSystemHelper.pressHome();
          appendSystemLog('Presionado botón Inicio');
        } else if (cmd.action === 'back') {
          await androidSystemHelper.pressBack();
          appendSystemLog('Presionado botón Atrás');
        } else if (cmd.action === 'recents') {
          await androidSystemHelper.pressRecents();
          appendSystemLog('Mostrando apps recientes');
        } else if (cmd.action === 'notifications') {
          await androidSystemHelper.pressNotifications();
          appendSystemLog('Desplegando notificaciones');
        } else if (cmd.action === 'call') {
          const res = await androidSystemHelper.makeCall(cmd.phoneNumber);
          appendSystemLog(res.output);
        } else if (cmd.action === 'sms') {
          const res = await androidSystemHelper.sendSMS(cmd.phoneNumber, cmd.message);
          appendSystemLog(res.output);
        } else if (cmd.action === 'search_contact') {
          const res = await androidSystemHelper.searchContact(cmd.contactName);
          appendSystemLog(res.output);
        }
      } catch (err: any) {
        appendSystemLog(`Error ejecutando comando: ${err.message}`);
      }
    }

    // Reproducir voz si no está silenciado
    if (!isMuted && cleanSpeech) {
      Speech.stop();
      setAssistantState('SPEAKING');
      Speech.speak(cleanSpeech, {
        language: 'es-ES',
        rate: 1.0,
        pitch: 1.0,
        onDone: () => setAssistantState('IDLE'),
        onError: () => setAssistantState('IDLE'),
      });
    }
  };

  const appendSystemLog = (text: string) => {
    setMessages(prev => [
      ...prev,
      {
        id: Math.random().toString(),
        role: 'system',
        content: text,
        ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // ─── ENVÍO DE MENSAJES Y ACCIONES DE USUARIO ────────────────────────────────
  const handleSendMessage = (textToSend?: string) => {
    const message = (textToSend ?? inputText).trim();
    if (!message) return;

    if (!isConnected) {
      Alert.alert('Núcleo Desconectado', 'Verifique que el servidor Alberth esté en línea o revise la URL en Ajustes.');
      return;
    }

    // Interceptar atajos rápidos directos de voz
    handleLocalDirectIntents(message);

    setInputText('');
    const userMsg: Message = {
      id: Math.random().toString(),
      role: 'user',
      content: message,
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    lastUserMessage.current = message;
    setMessages(prev => [...prev, userMsg]);
    setAssistantState('THINKING');

    if (responseTimeout.current) clearTimeout(responseTimeout.current);
    responseTimeout.current = setTimeout(() => {
      setAssistantState('IDLE');
      appendSystemLog('⏱️ Tiempo de espera agotado. El servidor está procesando en segundo plano.');
    }, 15000);

    ws.current?.send(JSON.stringify({ type: 'text', text: message }));
  };

  // Comandos de ejecución instantánea local
  const handleLocalDirectIntents = async (text: string) => {
    const lower = text.toLowerCase();

    if (lower.startsWith('abre ') || lower.startsWith('abrir ')) {
      const appName = lower.replace(/^(abre|abrir)\s+/, '').trim();
      androidSystemHelper.launchApp(appName);
    } else if (lower.includes('pon la canción ') || lower.includes('pon musica ') || lower.includes('en spotify')) {
      const query = lower.replace(/.*(pon la canción|pon musica|reproduce)\s+/, '').replace(/\s+en spotify.*/, '').trim();
      androidSystemHelper.playMedia(query, 'spotify');
    } else if (lower.includes('pon el video ') || lower.includes('en youtube')) {
      const query = lower.replace(/.*(pon el video|busca en youtube|pon)\s+/, '').replace(/\s+en youtube.*/, '').trim();
      androidSystemHelper.playMedia(query, 'youtube');
    } else if (lower.includes('lee la pantalla') || lower.includes('que hay en mi pantalla') || lower.includes('que ves en pantalla')) {
      const screen = await androidSystemHelper.readScreenText();
      if (screen.ok && screen.output) {
        ws.current?.send(
          JSON.stringify({
            type: 'text',
            text: `[PANTALLA_ACTUAL]: ${screen.output}\n\nEl usuario solicita que analices lo que hay en su pantalla y le respondas de forma concisa.`,
          })
        );
      }
    }
  };

  // ─── GRABACIÓN DE AUDIO CON EXPO-AUDIO ──────────────────────────────────────
  const startVoiceRecording = async () => {
    try {
      Speech.stop();
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);

      const perm = await AudioModule.requestRecordingPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Micrófono requerido', 'Permita el acceso al micrófono para interactuar con Alberth.');
        return;
      }

      await audioRecorder.prepareToRecordAsync(RecordingPresets.HIGH_QUALITY);
      audioRecorder.record();
      setIsRecording(true);
      setAssistantState('LISTENING');
    } catch (err: any) {
      console.error('[Audio] Error al iniciar grabación:', err);
      Alert.alert('Error Micrófono', err.message);
    }
  };

  const stopVoiceRecording = async () => {
    if (!isRecording) return;
    setIsRecording(false);
    setAssistantState('THINKING');
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

    try {
      await audioRecorder.stop();
      const uri = audioRecorder.uri;
      if (!uri) {
        setAssistantState('IDLE');
        return;
      }
      await uploadVoiceAudio(uri);
    } catch (err: any) {
      console.error('[Audio] Error al detener:', err);
      setAssistantState('IDLE');
    }
  };

  const uploadVoiceAudio = async (fileUri: string) => {
    if (!isConnected) {
      setAssistantState('IDLE');
      Alert.alert('Desconectado', 'No hay enlace al servidor para transmitir audio.');
      return;
    }

    try {
      const cleanUrl = serverUrl.replace(/\/$/, '');
      const uploadUrl = `${cleanUrl}/audio?token=${encodeURIComponent(gatewayToken)}`;

      const formData = new FormData();
      const filename = fileUri.split('/').pop() || 'voice.m4a';
      const ext = filename.split('.').pop()?.toLowerCase() || 'm4a';
      const mime = ext === 'wav' ? 'audio/wav' : 'audio/m4a';

      formData.append('file', {
        uri: fileUri,
        name: `alberth_voice.${ext}`,
        type: mime,
      } as any);

      appendSystemLog('🎙️ Audio cuántico transmitido. Analizando voz...');

      const response = await fetch(uploadUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${gatewayToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      if (!data.ok) throw new Error('Transcripción fallida');
    } catch (err: any) {
      console.error('[Audio] Error de subida:', err);
      setAssistantState('IDLE');
      appendSystemLog(`Error de voz: ${err.message}`);
    }
  };

  // ─── ACCIONES DE AJUSTES ───────────────────────────────────────────────────
  const saveSettingsAndReconnect = async (newUrl: string, newToken: string) => {
    let clean = newUrl.trim();
    if (clean && !clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = 'https://' + clean;
    }
    const cleanToken = newToken.trim();

    try {
      await AsyncStorage.setItem('@alberth_server_url', clean);
      await AsyncStorage.setItem('@alberth_gateway_token', cleanToken);
    } catch {}

    setServerUrl(clean);
    setGatewayToken(cleanToken);
    retryCount.current = 0;
    setShowSettings(false);
    connectWebSocket(clean, cleanToken);
  };

  const restoreFactoryDefaults = async () => {
    setServerUrl(DEFAULT_SERVER_URL);
    setGatewayToken(DEFAULT_GATEWAY_TOKEN);
    await AsyncStorage.setItem('@alberth_server_url', DEFAULT_SERVER_URL);
    await AsyncStorage.setItem('@alberth_gateway_token', DEFAULT_GATEWAY_TOKEN);
    retryCount.current = 0;
    connectWebSocket(DEFAULT_SERVER_URL, DEFAULT_GATEWAY_TOKEN);
    Alert.alert('Restaurado', 'Credenciales y URL de fábrica reestablecidas con éxito.');
  };

  const toggleMute = () => {
    const next = !isMuted;
    setIsMuted(next);
    AsyncStorage.setItem('@alberth_mute', next ? 'true' : 'false');
    if (next) Speech.stop();
  };

  // Interpolación de rotación para reactor HUD
  const spin = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  // ─── RENDER PRINCIPAL // QUANTUM COCKPIT HUD ───────────────────────────────
  return (
    <View style={[styles.cockpitContainer, { paddingBottom: insets.bottom }]}>
      <StatusBar style="light" />

      {/* Fondos de Nebulosa Cuántica */}
      <View style={styles.neonGlowTop} />
      <View style={styles.neonGlowBottom} />

      {/* ── TOP HUD COCKPIT BAR ────────────────────────────────────────── */}
      <View style={[styles.hudTopBar, { paddingTop: insets.top + 8 }]}>
        <View style={styles.hudBrandCol}>
          <View style={styles.hudBrandRow}>
            <Cpu size={16} color="#00F0FF" style={{ marginRight: 6 }} />
            <Text style={styles.hudBrandTitle}>ALBERTH CORE</Text>
            <View style={[styles.statusPill, { backgroundColor: isConnected ? '#00FFA3' : '#FF0055' }]}>
              <Text style={styles.statusPillText}>{isConnected ? 'ONLINE' : 'OFFLINE'}</Text>
            </View>
          </View>
          <Text style={styles.hudBrandSubtitle}>QUANTUM AI // OS ASSISTANT v4.0</Text>
        </View>

        <View style={styles.hudControlsRow}>
          <TouchableOpacity
            onPress={() => {
              retryCount.current = 0;
              connectWebSocket();
            }}
            style={styles.hudIconButton}
          >
            <RefreshCw size={18} color="#00F0FF" />
          </TouchableOpacity>
          <TouchableOpacity onPress={toggleMute} style={styles.hudIconButton}>
            {isMuted ? <VolumeX size={18} color="#FF0055" /> : <Volume2 size={18} color="#00FFA3" />}
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setShowSettings(true)} style={styles.hudIconButton}>
            <SettingsIcon size={18} color="#E0E7FF" />
          </TouchableOpacity>
        </View>
      </View>

      {/* ── TELEMETRÍA Y ESTADO DE SERVICIOS OS ────────────────────────── */}
      <View style={styles.telemetryBar}>
        <TouchableOpacity onPress={() => androidSystemHelper.openAssistantSettings()} style={styles.telemetryBadge}>
          <Sparkles size={12} color={isDefaultAssistActive ? '#00FFA3' : '#FFB800'} style={{ marginRight: 4 }} />
          <Text style={styles.telemetryText}>
            ASISTENTE: <Text style={{ color: isDefaultAssistActive ? '#00FFA3' : '#FFB800' }}>{isDefaultAssistActive ? 'ACTIVO' : 'CONFIG'}</Text>
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => androidSystemHelper.openAccessibilitySettings()} style={styles.telemetryBadge}>
          <ShieldCheck size={12} color={isAccessibilityActive ? '#00FFA3' : '#FFB800'} style={{ marginRight: 4 }} />
          <Text style={styles.telemetryText}>
            CONTROL: <Text style={{ color: isAccessibilityActive ? '#00FFA3' : '#FFB800' }}>{isAccessibilityActive ? 'TOTAL' : 'ACTIVAR'}</Text>
          </Text>
        </TouchableOpacity>

        <View style={styles.telemetryBadge}>
          <Radio size={12} color="#00F0FF" style={{ marginRight: 4 }} />
          <Text style={styles.telemetryText}>{statusMessage}</Text>
        </View>
      </View>

      {/* ── QUANTUM ARC REACTOR ORB ────────────────────────────────────── */}
      <View style={styles.reactorSection}>
        <Animated.View
          style={[
            styles.reactorOuterRing,
            {
              transform: [{ rotate: spin }, { scale: pulseAnim }],
              borderColor:
                assistantState === 'LISTENING'
                  ? '#00F0FF'
                  : assistantState === 'THINKING'
                  ? '#BD00FF'
                  : assistantState === 'SPEAKING'
                  ? '#00FFA3'
                  : 'rgba(0, 240, 255, 0.35)',
            },
          ]}
        >
          <View style={styles.reactorTachometerTickTop} />
          <View style={styles.reactorTachometerTickBottom} />
          <View style={styles.reactorTachometerTickLeft} />
          <View style={styles.reactorTachometerTickRight} />
        </Animated.View>

        <TouchableOpacity
          activeOpacity={0.85}
          onPressIn={startVoiceRecording}
          onPressOut={stopVoiceRecording}
          style={[
            styles.reactorCoreOrb,
            {
              shadowColor:
                assistantState === 'LISTENING'
                  ? '#00F0FF'
                  : assistantState === 'THINKING'
                  ? '#BD00FF'
                  : assistantState === 'SPEAKING'
                  ? '#00FFA3'
                  : '#00F0FF',
            },
          ]}
        >
          {assistantState === 'LISTENING' ? (
            <Mic size={36} color="#00F0FF" />
          ) : assistantState === 'THINKING' ? (
            <ActivityIndicator size="large" color="#BD00FF" />
          ) : assistantState === 'SPEAKING' ? (
            <Activity size={36} color="#00FFA3" />
          ) : (
            <Cpu size={36} color="#FFFFFF" />
          )}
          <Text style={styles.reactorCoreLabel}>
            {assistantState === 'LISTENING'
              ? 'ESCUCHANDO...'
              : assistantState === 'THINKING'
              ? 'PROCESANDO'
              : assistantState === 'SPEAKING'
              ? 'HABLANDO'
              : 'ALBERTH'}
          </Text>
        </TouchableOpacity>

        {/* Dynamic Waveform Reactor Bands */}
        <View style={styles.reactorWaveformContainer}>
          {waveHeights.map((h, i) => (
            <View
              key={i}
              style={[
                styles.reactorWaveBar,
                {
                  height: h,
                  backgroundColor:
                    assistantState === 'LISTENING'
                      ? '#00F0FF'
                      : assistantState === 'SPEAKING'
                      ? '#00FFA3'
                      : '#BD00FF',
                },
              ]}
            />
          ))}
        </View>
      </View>

      {/* ── BOTONES DE ACCIÓN RÁPIDA OS // COCKPIT CONTROLS ────────────── */}
      <View style={styles.quickActionsBar}>
        <TouchableOpacity
          style={styles.quickActionBtn}
          onPress={async () => {
            const res = await androidSystemHelper.readScreenText();
            if (res.ok && res.output) {
              handleSendMessage(`Analiza lo que hay en mi pantalla: ${res.output}`);
            } else {
              Alert.alert('Accesibilidad Requerida', 'Active el Servicio de Accesibilidad para que Alberth pueda ver su pantalla.', [
                { text: 'Activar Ahora', onPress: () => androidSystemHelper.openAccessibilitySettings() },
                { text: 'Cancelar' },
              ]);
            }
          }}
        >
          <Eye size={16} color="#00F0FF" />
          <Text style={styles.quickActionText}>VER PANTALLA</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionBtn}
          onPress={() => handleSendMessage('Pon música de rock en Spotify')}
        >
          <Play size={16} color="#00FFA3" />
          <Text style={styles.quickActionText}>SPOTIFY</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionBtn}
          onPress={() => handleSendMessage('Pon videos de inteligencia artificial en YouTube')}
        >
          <Play size={16} color="#FF0055" />
          <Text style={styles.quickActionText}>YOUTUBE</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionBtn}
          onPress={() => androidSystemHelper.openAssistantSettings()}
        >
          <Smartphone size={16} color="#BD00FF" />
          <Text style={styles.quickActionText}>ASISTENTE OS</Text>
        </TouchableOpacity>
      </View>

      {/* ── HISTORIAL DE INTERACCIÓN // QUANTUM TERMINAL ───────────────── */}
      <ScrollView
        ref={scrollViewRef}
        style={styles.terminalScroll}
        contentContainerStyle={styles.terminalContent}
        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((m) => {
          if (m.role === 'system') {
            return (
              <View key={m.id} style={styles.systemLogCard}>
                <Terminal size={12} color="#00F0FF" style={{ marginRight: 6 }} />
                <Text style={styles.systemLogText}>{m.content}</Text>
              </View>
            );
          }

          const isUser = m.role === 'user';
          return (
            <View key={m.id} style={[styles.bubbleWrapper, isUser ? styles.userBubbleWrapper : styles.alberthBubbleWrapper]}>
              <View style={styles.bubbleHeader}>
                {isUser ? (
                  <User size={12} color="#00F0FF" style={{ marginRight: 4 }} />
                ) : (
                  <Cpu size={12} color="#00FFA3" style={{ marginRight: 4 }} />
                )}
                <Text style={[styles.bubbleSender, { color: isUser ? '#00F0FF' : '#00FFA3' }]}>
                  {isUser ? 'SEÑOR DANNY' : 'ALBERTH AI'}
                </Text>
                <Text style={styles.bubbleTime}>{m.ts}</Text>
              </View>

              <View style={[styles.bubbleCard, isUser ? styles.userBubbleCard : styles.alberthBubbleCard]}>
                <Text style={styles.bubbleText}>
                  {m.content.replace(/\[PHONE_CMD:\s*\{.*?\}\]/g, '')}
                </Text>
              </View>
            </View>
          );
        })}
      </ScrollView>

      {/* ── COCKPIT INPUT BAR ──────────────────────────────────────────── */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.inputCockpitBar}>
          <TextInput
            style={styles.cockpitInput}
            placeholder="Comando para Alberth o presione el reactor..."
            placeholderTextColor="#64748B"
            value={inputText}
            onChangeText={setInputText}
            onSubmitEditing={() => handleSendMessage()}
          />
          <TouchableOpacity
            onPress={() => handleSendMessage()}
            style={styles.cockpitSendBtn}
          >
            <Send size={18} color="#040711" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* ── MODAL DE CONFIGURACIÓN Y DIAGNÓSTICO ───────────────────────── */}
      <Modal visible={showSettings} animationType="fade" transparent>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCockpitCard}>
            <View style={styles.modalHeaderRow}>
              <Cpu size={22} color="#00F0FF" style={{ marginRight: 8 }} />
              <Text style={styles.modalTitle}>CONFIGURACIÓN DE ALBERTH</Text>
            </View>
            <Text style={styles.modalSubtitle}>Sincronización Cuántica de Servidor y Control OS</Text>

            {/* URL del Servidor */}
            <View style={styles.modalFieldGroup}>
              <Text style={styles.modalFieldLabel}>DIRECCIÓN DEL SERVIDOR (URL):</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="https://su-tunel.trycloudflare.com"
                placeholderTextColor="#64748B"
                value={serverUrl}
                onChangeText={setServerUrl}
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            {/* Token de Gateway */}
            <View style={styles.modalFieldGroup}>
              <Text style={styles.modalFieldLabel}>TOKEN DE ACCESO GATEWAY:</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="token-seguro-..."
                placeholderTextColor="#64748B"
                value={gatewayToken}
                onChangeText={setGatewayToken}
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            {/* Modo Silencioso */}
            <View style={styles.modalSwitchRow}>
              <Text style={styles.modalFieldLabel}>MODO SILENCIOSO (VOZ DESACTIVADA):</Text>
              <Switch
                value={isMuted}
                onValueChange={toggleMute}
                trackColor={{ false: '#1E293B', true: '#00FFA3' }}
                thumbColor={isMuted ? '#64748B' : '#040711'}
              />
            </View>

            {/* Accesos directos a Ajustes de Android */}
            <View style={styles.modalOsSettingsGroup}>
              <TouchableOpacity
                style={styles.modalOsBtn}
                onPress={() => {
                  androidSystemHelper.openAssistantSettings();
                  checkSystemServices();
                }}
              >
                <Smartphone size={16} color="#00FFA3" style={{ marginRight: 6 }} />
                <Text style={styles.modalOsBtnText}>Configurar como Asistente Predeterminado</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.modalOsBtn}
                onPress={() => {
                  androidSystemHelper.openAccessibilitySettings();
                  checkSystemServices();
                }}
              >
                <ShieldCheck size={16} color="#00F0FF" style={{ marginRight: 6 }} />
                <Text style={styles.modalOsBtnText}>Activar Accesibilidad (Control de Pantalla)</Text>
              </TouchableOpacity>
            </View>

            {/* Acciones del Modal */}
            <View style={styles.modalButtonsRow}>
              <TouchableOpacity
                onPress={restoreFactoryDefaults}
                style={[styles.modalActionBtn, styles.modalBtnSecondary]}
              >
                <Text style={styles.modalBtnSecondaryText}>Restaurar Defaults</Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={() => saveSettingsAndReconnect(serverUrl, gatewayToken)}
                style={[styles.modalActionBtn, styles.modalBtnPrimary]}
              >
                <Check size={18} color="#040711" style={{ marginRight: 6 }} />
                <Text style={styles.modalBtnPrimaryText}>Conectar</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity onPress={() => setShowSettings(false)} style={styles.modalCloseBtn}>
              <Text style={styles.modalCloseBtnText}>CERRAR</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// ─── ESTILOS CYBERPUNK HUD // QUANTUM COCKPIT ─────────────────────────────────
const styles = StyleSheet.create({
  cockpitContainer: {
    flex: 1,
    backgroundColor: '#040711',
  },
  neonGlowTop: {
    position: 'absolute',
    top: -50,
    left: SCREEN_WIDTH / 2 - 150,
    width: 300,
    height: 300,
    borderRadius: 150,
    backgroundColor: '#00F0FF',
    opacity: 0.08,
  },
  neonGlowBottom: {
    position: 'absolute',
    bottom: -80,
    right: -50,
    width: 320,
    height: 320,
    borderRadius: 160,
    backgroundColor: '#BD00FF',
    opacity: 0.07,
  },

  // ── HUD Header
  hudTopBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0, 240, 255, 0.15)',
    backgroundColor: 'rgba(6, 11, 25, 0.95)',
  },
  hudBrandCol: {
    flexDirection: 'column',
  },
  hudBrandRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  hudBrandTitle: {
    fontSize: 17,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: 1.5,
  },
  hudBrandSubtitle: {
    fontSize: 8,
    fontWeight: '700',
    color: '#00F0FF',
    letterSpacing: 1,
    marginTop: 2,
  },
  statusPill: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginLeft: 8,
  },
  statusPillText: {
    fontSize: 8,
    fontWeight: '900',
    color: '#040711',
    letterSpacing: 0.5,
  },
  hudControlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  hudIconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },

  // ── Telemetry Bar
  telemetryBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 6,
    backgroundColor: 'rgba(4, 7, 17, 0.85)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  telemetryBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
  },
  telemetryText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#94A3B8',
    letterSpacing: 0.5,
  },

  // ── Central Quantum Reactor Section
  reactorSection: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    position: 'relative',
  },
  reactorOuterRing: {
    position: 'absolute',
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 2,
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
  },
  reactorTachometerTickTop: {
    position: 'absolute',
    top: 2,
    width: 4,
    height: 8,
    backgroundColor: '#00F0FF',
  },
  reactorTachometerTickBottom: {
    position: 'absolute',
    bottom: 2,
    width: 4,
    height: 8,
    backgroundColor: '#00F0FF',
  },
  reactorTachometerTickLeft: {
    position: 'absolute',
    left: 2,
    width: 8,
    height: 4,
    backgroundColor: '#00F0FF',
  },
  reactorTachometerTickRight: {
    position: 'absolute',
    right: 2,
    width: 8,
    height: 4,
    backgroundColor: '#00F0FF',
  },
  reactorCoreOrb: {
    width: 104,
    height: 104,
    borderRadius: 52,
    backgroundColor: 'rgba(10, 20, 45, 0.95)',
    borderWidth: 2,
    borderColor: 'rgba(0, 240, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 18,
    elevation: 12,
  },
  reactorCoreLabel: {
    fontSize: 9,
    fontWeight: '900',
    color: '#00F0FF',
    letterSpacing: 1.5,
    marginTop: 4,
  },
  reactorWaveformContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 24,
    marginTop: 8,
  },
  reactorWaveBar: {
    width: 4,
    borderRadius: 2,
    marginHorizontal: 3,
  },

  // ── Quick Actions Bar
  quickActionsBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.1)',
    backgroundColor: 'rgba(6, 12, 28, 0.6)',
  },
  quickActionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  quickActionText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#E2E8F0',
    letterSpacing: 0.8,
    marginLeft: 5,
  },

  // ── Terminal Scroll
  terminalScroll: {
    flex: 1,
  },
  terminalContent: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  systemLogCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 240, 255, 0.04)',
    borderLeftWidth: 3,
    borderLeftColor: '#00F0FF',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 4,
    marginVertical: 4,
  },
  systemLogText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#67E8F9',
    letterSpacing: 0.3,
    flex: 1,
  },
  bubbleWrapper: {
    marginVertical: 6,
    maxWidth: '86%',
  },
  userBubbleWrapper: {
    alignSelf: 'flex-end',
  },
  alberthBubbleWrapper: {
    alignSelf: 'flex-start',
  },
  bubbleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
    paddingHorizontal: 4,
  },
  bubbleSender: {
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1,
  },
  bubbleTime: {
    fontSize: 8,
    color: '#64748B',
    marginLeft: 6,
  },
  bubbleCard: {
    padding: 12,
    borderRadius: 12,
  },
  userBubbleCard: {
    backgroundColor: 'rgba(0, 240, 255, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.4)',
    borderTopRightRadius: 2,
  },
  alberthBubbleCard: {
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    borderWidth: 1,
    borderColor: 'rgba(0, 255, 163, 0.3)',
    borderTopLeftRadius: 2,
  },
  bubbleText: {
    fontSize: 13,
    lineHeight: 19,
    color: '#F8FAFC',
    fontWeight: '500',
  },

  // ── Cockpit Input Bar
  inputCockpitBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: 'rgba(6, 11, 25, 0.95)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(0, 240, 255, 0.15)',
  },
  cockpitInput: {
    flex: 1,
    height: 42,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 21,
    paddingHorizontal: 16,
    color: '#FFFFFF',
    fontSize: 12,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.25)',
  },
  cockpitSendBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#00F0FF',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 10,
    shadowColor: '#00F0FF',
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 6,
  },

  // ── Modal Styles
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  modalCockpitCard: {
    width: '100%',
    backgroundColor: '#0A0F24',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    padding: 20,
    shadowColor: '#00F0FF',
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 20,
  },
  modalHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: 1,
  },
  modalSubtitle: {
    fontSize: 10,
    color: '#67E8F9',
    marginBottom: 16,
    marginTop: 2,
  },
  modalFieldGroup: {
    marginBottom: 12,
  },
  modalFieldLabel: {
    fontSize: 9,
    fontWeight: '800',
    color: '#94A3B8',
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  modalInput: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#FFFFFF',
    fontSize: 12,
  },
  modalSwitchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 10,
  },
  modalOsSettingsGroup: {
    marginVertical: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
  },
  modalOsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.2)',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    marginBottom: 8,
  },
  modalOsBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#E2E8F0',
  },
  modalButtonsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  modalActionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 8,
    marginHorizontal: 4,
  },
  modalBtnSecondary: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  modalBtnSecondaryText: {
    color: '#94A3B8',
    fontSize: 11,
    fontWeight: '800',
  },
  modalBtnPrimary: {
    backgroundColor: '#00FFA3',
  },
  modalBtnPrimaryText: {
    color: '#040711',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  modalCloseBtn: {
    alignSelf: 'center',
    marginTop: 14,
    padding: 6,
  },
  modalCloseBtnText: {
    fontSize: 10,
    fontWeight: '800',
    color: '#64748B',
    letterSpacing: 1,
  },
});
