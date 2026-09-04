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
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
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
  Phone,
  MessageSquare,
  User,
  Laptop,
} from 'lucide-react-native';
import { androidSystemHelper } from './android_system_helper';

interface Message {
  id: string;
  role: 'user' | 'alberth' | 'system';
  content: string;
  ts: string;
}

// ─── Reconnect config ────────────────────────────────────────────────────────
const MAX_RETRIES = 5;
const RETRY_DELAY_MS = 3000;

export default function App() {
  const insets = useSafeAreaInsets();

// Server URL is loaded from AsyncStorage; start empty so we can force the user to input it
const [serverUrl, setServerUrl] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Desconectado');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'alberth',
      content: '¡Hola Señor! Soy Alberth. Su interfaz móvil premium está lista. ¿En qué le puedo asistir hoy?',
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Waveform animation helpers
  const [waveHeights, setWaveHeights] = useState([20, 10, 15, 8, 22, 14, 18, 9]);

  const ws = useRef<WebSocket | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  const audioRecorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const waveTimer = useRef<any>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<any>(null);
  const currentUrl = useRef(serverUrl);
  // Timer to detect server response timeout
  const responseTimeout = useRef<any>(null);
  // Keep the last user message to avoid echo duplicates
  const lastUserMessage = useRef<string>('');

  // ─── Load settings ─────────────────────────────────────────────────────────
  // Load persisted settings (URL and mute) on mount. If the URL is missing we open the Settings modal.
  useEffect(() => {
    async function loadSettings() {
      try {
        const storedUrl = await AsyncStorage.getItem('@alberth_server_url');
        if (storedUrl) {
          setServerUrl(storedUrl);
        } else {
          // No URL stored – force user to configure it
          setShowSettings(true);
        }
        const storedMute = await AsyncStorage.getItem('@alberth_mute');
        if (storedMute !== null) setIsMuted(storedMute === 'true');
      } catch (e) {
        console.error('Error loading settings:', e);
      }
    }
    loadSettings();
  }, []);

  // ─── Audio permission ───────────────────────────────────────────────────────
  useEffect(() => {
    async function getPermission() {
      const status = await AudioModule.requestRecordingPermissionsAsync();
      if (!status.granted) {
        Alert.alert(
          'Permiso Requerido',
          'Alberth necesita acceso al micrófono para interactuar por voz.'
        );
      }
    }
    getPermission();
  }, []);

  // ─── Waveform animation ─────────────────────────────────────────────────────
  useEffect(() => {
    if (isRecording || isThinking) {
      waveTimer.current = setInterval(() => {
        setWaveHeights(prev =>
          prev.map(() => {
            const min = isRecording ? 15 : 8;
            const max = isRecording ? 80 : 35;
            return Math.floor(Math.random() * (max - min + 1)) + min;
          })
        );
      }, 100);
    } else {
      if (waveTimer.current) clearInterval(waveTimer.current);
      setWaveHeights([8, 8, 8, 8, 8, 8, 8, 8]);
    }
    return () => { if (waveTimer.current) clearInterval(waveTimer.current); };
  }, [isRecording, isThinking]);

  // ─── WebSocket ──────────────────────────────────────────────────────────────
  const connectWebSocket = useCallback((url?: string) => {
    const targetUrl = url ?? currentUrl.current;
    if (!targetUrl) return;

    // Clear any pending retry
    if (retryTimer.current) {
      clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }

    // Close existing connection
    if (ws.current) {
      ws.current.onclose = null; // prevent retry loop on manual reconnect
      ws.current.close();
      ws.current = null;
    }

    setStatusMessage('Conectando...');

    // Build WS URL
    let wsProto = 'ws://';
    let cleanUrl = targetUrl.replace(/^(https?:\/\/)/, '');
    if (targetUrl.startsWith('https://')) wsProto = 'wss://';
    cleanUrl = cleanUrl.replace(/\/$/, '');

    try {
      const socketUrl = `${wsProto}${cleanUrl}/ws`;
      console.log('[WS] Connecting to:', socketUrl);
      const socket = new WebSocket(socketUrl);
      ws.current = socket;

      socket.onopen = () => {
        console.log('[WS] Connected');
        retryCount.current = 0;
        setIsConnected(true);
        setStatusMessage('🟢 En línea');
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      };

      socket.onmessage = async (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'message') {
            // Clear any pending timeout when a message arrives
            if (responseTimeout.current) {
              clearTimeout(responseTimeout.current);
              responseTimeout.current = null;
            }
            const incoming = data.message;
            const content = incoming.content;
            // Avoid echoing the user's own message back (some servers repeat it)
            if (incoming.role === 'user' && content === lastUserMessage.current) {
              // Reset the stored last message and ignore
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
            setIsThinking(false);
            if (msg.role === 'alberth') await handleVoiceAndCommands(msg.content);
          } else if (data.type === 'thinking') {
            setIsThinking(data.active);
          } else if (data.type === 'history') {
            if (data.messages?.length > 0) {
              const loadedHistory = data.messages.map((m: any, idx: number) => ({
                id: `hist_${idx}`,
                role: m.role,
                content: m.content,
                ts: m.ts || '',
              }));
              setMessages(loadedHistory);
            }
          }
        } catch (err) {
          console.error('[WS] Parse error:', err);
        }
      };

      socket.onerror = (e) => {
        console.error('[WS] Error:', e);
        setIsConnected(false);
        setStatusMessage('🔴 Error de conexión');
      };

      socket.onclose = (e) => {
        console.log('[WS] Closed. Code:', e.code);
        setIsConnected(false);

        // Auto-reconnect with exponential backoff
        if (retryCount.current < MAX_RETRIES) {
          retryCount.current += 1;
          const delay = RETRY_DELAY_MS * retryCount.current;
          setStatusMessage(`🟡 Reconectando (${retryCount.current}/${MAX_RETRIES})...`);
          retryTimer.current = setTimeout(() => {
            connectWebSocket();
          }, delay);
        } else {
          setStatusMessage('🔴 Sin conexión — abra Ajustes para reconectar');
        }
      };
    } catch (err) {
      console.error('[WS] Connection error:', err);
      setIsConnected(false);
      setStatusMessage('🔴 Desconectado');
    }
  }, []);

  // Connect on URL change
  // Establish WebSocket connection only when we have a non‑empty server URL.
  useEffect(() => {
    if (!serverUrl) {
      // No URL – we stay disconnected and wait for the user to provide one.
      setIsConnected(false);
      setStatusMessage('URL del servidor no configurada');
      return;
    }
    currentUrl.current = serverUrl;
    retryCount.current = 0;
    connectWebSocket(serverUrl);
    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [serverUrl]);

  const disconnectWebSocket = () => {
    if (retryTimer.current) clearTimeout(retryTimer.current);
    retryCount.current = MAX_RETRIES; // stop retries
    if (ws.current) {
      ws.current.onclose = null;
      ws.current.close();
      ws.current = null;
    }
    setIsConnected(false);
    setStatusMessage('Desconectado');
  };

  // ─── Handlers ───────────────────────────────────────────────────────────────
  const handleVoiceAndCommands = async (content: string) => {
    const cmdRegex = /\[PHONE_CMD:\s*(\{.*?\})\]/;
    const match = content.match(cmdRegex);
    let speechText = content.replace(cmdRegex, '').trim();

    if (match) {
      try {
        const cmdData = JSON.parse(match[1]);
        appendSystemMessage(`Ejecutando en teléfono: ${cmdData.action.toUpperCase()}...`);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        let result;
        if (cmdData.action === 'call') result = await androidSystemHelper.makeCall(cmdData.phoneNumber);
        else if (cmdData.action === 'sms') result = await androidSystemHelper.sendSMS(cmdData.phoneNumber, cmdData.message);
        else if (cmdData.action === 'search_contact') {
          result = await androidSystemHelper.searchContact(cmdData.contactName);
          if (result.ok && result.data) {
            speechText += `. Encontré el contacto ${result.data.name}.`;
            appendSystemMessage(`Contacto encontrado: ${result.data.name}`);
          } else {
            speechText += `. No pude encontrar el contacto.`;
            appendSystemMessage(`Búsqueda fallida: ${result.output}`);
          }
        } else if (cmdData.action === 'volume') result = await androidSystemHelper.controlPhoneVolume(cmdData.volumeAction);
        if (result) appendSystemMessage(result.output);
      } catch (e: any) {
        appendSystemMessage(`Error de comando: ${e.message}`);
      }
    }

    if (!isMuted && speechText) {
      Speech.stop();
      Speech.speak(speechText, { language: 'es-ES', rate: 0.95, pitch: 1.0 });
    }
  };

  const appendSystemMessage = (text: string) => {
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

  const saveSettings = async (url: string) => {
    let clean = url.trim();
    if (clean && !clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = 'https://' + clean;
    }
    try {
      await AsyncStorage.setItem('@alberth_server_url', clean);
    } catch (e) {}
    retryCount.current = 0;
    setServerUrl(clean);
    setShowSettings(false);
  };

  const handleSendMessage = () => {
    if (!inputText.trim()) return;
    if (!isConnected) {
      Alert.alert('Desconectado', 'Espere la conexión o verifique la URL del servidor en Ajustes.');
      return;
    }
    const text = inputText.trim();
    setInputText('');
    const userMsg: Message = {
      id: Math.random().toString(),
      role: 'user',
      content: text,
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    // Record the last user message to prevent echo when server repeats it
    lastUserMessage.current = text;
    setMessages(prev => [...prev, userMsg]);
    setIsThinking(true);
    // Start a timeout guard – if no reply within 12 s we show a warning
    if (responseTimeout.current) clearTimeout(responseTimeout.current);
    responseTimeout.current = setTimeout(() => {
      setIsThinking(false);
      appendSystemMessage('⏱️ Tiempo de espera agotado. El servidor no respondió a tiempo.');
      setStatusMessage('⚠️ Sin respuesta');
    }, 12_000);
    ws.current?.send(JSON.stringify({ type: 'text', text }));
  };

  // ─── Audio recording ────────────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      Speech.stop();
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);

      // Request permission again in case it was denied
      const perm = await AudioModule.requestRecordingPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Sin permiso', 'Habilite el micrófono en Ajustes del sistema.');
        return;
      }

      await audioRecorder.prepareToRecordAsync(RecordingPresets.HIGH_QUALITY);
      audioRecorder.record();
      setIsRecording(true);
      console.log('[Audio] Recording started');
    } catch (err: any) {
      console.error('[Audio] Start error:', err);
      Alert.alert('Error', `No se pudo iniciar la grabación: ${err.message}`);
    }
  };

  const stopRecording = async () => {
    if (!isRecording) return;
    setIsRecording(false);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

    try {
      await audioRecorder.stop();
      const uri = audioRecorder.uri;
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
      Alert.alert('Desconectado', 'No hay conexión al servidor para enviar el audio.');
      return;
    }
    setIsThinking(true);
    try {
      const cleanUrl = serverUrl.replace(/\/$/, '');
      const uploadUrl = `${cleanUrl}/audio`;
      console.log('[Audio] Uploading to:', uploadUrl);

      const formData = new FormData();
      // expo-audio recordings are typically .m4a on Android too
      const filename = fileUri.split('/').pop() || 'voice.m4a';
      const ext = filename.split('.').pop()?.toLowerCase() || 'm4a';
      const mime = ext === 'wav' ? 'audio/wav' : ext === 'caf' ? 'audio/x-caf' : 'audio/m4a';

      formData.append('file', {
        uri: fileUri,
        name: `alberth_voice.${ext}`,
        type: mime,
      } as any);

      const response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('[Audio] Upload response:', data);

      if (!data.ok) throw new Error('Server transcription failed');
      appendSystemMessage('🎙️ Audio enviado. Procesando voz...');
    } catch (err: any) {
      console.error('[Audio] Upload error:', err);
      setIsThinking(false);
      Alert.alert('Error de Envío', `No se pudo enviar el audio: ${err.message}`);
    }
  };

  const toggleMute = () => {
    const nextVal = !isMuted;
    setIsMuted(nextVal);
    AsyncStorage.setItem('@alberth_mute', nextVal ? 'true' : 'false');
    if (nextVal) Speech.stop();
  };

  const clearChat = () => {
    setMessages([{
      id: 'welcome',
      role: 'alberth',
      content: 'Chat reiniciado. ¿En qué le puedo asistir, Señor?',
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }]);
  };

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <View style={[styles.outerContainer, { paddingBottom: insets.bottom }]}>
      <StatusBar style="light" />

      {/* Background glowing decorations */}
      <View style={styles.neonBlobBlue} />
      <View style={styles.neonBlobPurple} />

      {/* Main Glass Header — respects status bar */}
      <View style={[styles.glassHeader, { paddingTop: insets.top + 10 }]}>
        <View style={styles.headerTitleRow}>
          <Text style={styles.headerTitle}>ALBERTH</Text>
          <Text style={styles.headerSubtitle}>V3.0 MOBILE</Text>
        </View>

        <View style={styles.headerActions}>
          <TouchableOpacity onPress={() => { retryCount.current = 0; connectWebSocket(); }} style={styles.headerButton}>
            <RefreshCw size={18} color="#5BC0BE" />
          </TouchableOpacity>
          <TouchableOpacity onPress={toggleMute} style={styles.headerButton}>
            {isMuted ? <VolumeX size={20} color="#ff4a4a" /> : <Volume2 size={20} color="#5BC0BE" />}
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setShowSettings(true)} style={styles.headerButton}>
            <SettingsIcon size={20} color="#a0aec0" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Status Bar */}
      <View style={styles.statusBar}>
        <View style={[styles.statusDot, { backgroundColor: isConnected ? '#5BC0BE' : '#ff4a4a' }]} />
        <Text style={styles.statusText}>{statusMessage}</Text>
        {serverUrl && <Text style={styles.serverHost} numberOfLines={1}>{serverUrl.replace(/https?:\/\//, '')}</Text>}
      </View>

      {/* Chat History */}
      <ScrollView
        ref={scrollViewRef}
        style={styles.chatScroll}
        contentContainerStyle={styles.chatContent}
        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((m) => {
          if (m.role === 'system') {
            return (
              <View key={m.id} style={styles.systemBubble}>
                <AlertCircle size={12} color="#5BC0BE" style={{ marginRight: 6 }} />
                <Text style={styles.systemText}>{m.content}</Text>
              </View>
            );
          }
          const isUser = m.role === 'user';
          return (
            <View key={m.id} style={[styles.messageContainer, isUser ? styles.userContainer : styles.alberthContainer]}>
              <View style={styles.bubbleRoleRow}>
                {isUser
                  ? <User size={12} color="#a0aec0" style={{ marginRight: 4 }} />
                  : <Laptop size={12} color="#9f7aea" style={{ marginRight: 4 }} />}
                <Text style={styles.bubbleRoleText}>{isUser ? 'Señor' : 'Alberth'}</Text>
                <Text style={styles.bubbleTime}>{m.ts}</Text>
              </View>
              <View style={[styles.bubble, isUser ? styles.userBubble : styles.alberthBubble]}>
                <Text style={styles.bubbleText}>{m.content.replace(/\[PHONE_CMD:.*?\]/g, '')}</Text>
              </View>
            </View>
          );
        })}
        {isThinking && (
          <View style={styles.thinkingContainer}>
            <ActivityIndicator color="#9f7aea" size="small" style={{ marginRight: 8 }} />
            <Text style={styles.thinkingText}>Alberth está pensando...</Text>
          </View>
        )}
      </ScrollView>

      {/* Waveform */}
      {(isRecording || isThinking) && (
        <View style={styles.waveformContainer}>
          {waveHeights.map((h, i) => (
            <View key={i} style={[styles.waveBar, { height: h, backgroundColor: isRecording ? '#5BC0BE' : '#9f7aea' }]} />
          ))}
        </View>
      )}

      {/* Footer — stays above navigation bar */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.glassFooter}>
          <View style={styles.voiceSection}>
            <TouchableOpacity
              onPressIn={startRecording}
              onPressOut={stopRecording}
              style={[styles.micButton, isRecording && styles.micButtonActive]}
            >
              <Mic size={32} color={isRecording ? '#060a14' : '#5BC0BE'} />
            </TouchableOpacity>
            <Text style={styles.micHelpText}>
              {isRecording ? 'Suelte para enviar' : 'Mantenga presionado para hablar'}
            </Text>
          </View>

          <View style={styles.inputRow}>
            <TextInput
              style={styles.textInput}
              placeholder="Escriba un mensaje..."
              placeholderTextColor="#718096"
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={handleSendMessage}
            />
            <TouchableOpacity onPress={handleSendMessage} style={styles.sendButton}>
              <Send size={18} color="#060a14" />
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>

      {/* Settings Modal */}
      <Modal visible={showSettings} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Configuración Alberth</Text>

            <View style={styles.settingGroup}>
              <Text style={styles.settingLabel}>URL del Servidor (Mac):</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="https://su-tunel.trycloudflare.com"
                placeholderTextColor="#718096"
                value={serverUrl}
                onChangeText={setServerUrl}
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            <View style={styles.settingRow}>
              <Text style={styles.settingLabel}>Modo Silencioso (No hablar):</Text>
              <Switch
                value={isMuted}
                onValueChange={toggleMute}
                trackColor={{ false: '#4a5568', true: '#5BC0BE' }}
                thumbColor={isMuted ? '#a0aec0' : '#060a14'}
              />
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity onPress={clearChat} style={[styles.modalButton, styles.buttonDanger]}>
                <Text style={styles.buttonText}>Limpiar Chat</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={() => saveSettings(serverUrl)} style={[styles.modalButton, styles.buttonSuccess]}>
                <Check size={18} color="#fff" style={{ marginRight: 6 }} />
                <Text style={styles.buttonText}>Conectar</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity onPress={() => setShowSettings(false)} style={styles.closeModalButton}>
              <Text style={styles.closeModalText}>Cerrar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  outerContainer: {
    flex: 1,
    backgroundColor: '#060a14',
  },
  neonBlobBlue: {
    position: 'absolute',
    top: 50,
    left: -50,
    width: 250,
    height: 250,
    borderRadius: 125,
    backgroundColor: '#00bfff',
    opacity: 0.1,
  },
  neonBlobPurple: {
    position: 'absolute',
    bottom: 100,
    right: -50,
    width: 280,
    height: 280,
    borderRadius: 140,
    backgroundColor: '#8a2be2',
    opacity: 0.1,
  },
  glassHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
    backgroundColor: 'rgba(10, 15, 30, 0.9)',
  },
  headerTitleRow: { flexDirection: 'column' },
  headerTitle: { fontSize: 20, fontWeight: '900', color: '#fff', letterSpacing: 2 },
  headerSubtitle: { fontSize: 9, fontWeight: '600', color: '#5BC0BE', letterSpacing: 1, marginTop: 2 },
  headerActions: { flexDirection: 'row', alignItems: 'center' },
  headerButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 8,
    backgroundColor: 'rgba(5, 8, 16, 0.8)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.04)',
  },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 8 },
  statusText: { fontSize: 12, color: '#e2e8f0', fontWeight: '500' },
  serverHost: { fontSize: 10, color: '#718096', marginLeft: 'auto', maxWidth: '60%' },
  chatScroll: { flex: 1, backgroundColor: 'transparent' },
  chatContent: { padding: 16, paddingBottom: 30 },
  messageContainer: { marginBottom: 16, maxWidth: '85%' },
  userContainer: { alignSelf: 'flex-end' },
  alberthContainer: { alignSelf: 'flex-start' },
  bubbleRoleRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4, paddingHorizontal: 4 },
  bubbleRoleText: { fontSize: 11, color: '#a0aec0', fontWeight: '600' },
  bubbleTime: { fontSize: 10, color: '#718096', marginLeft: 6 },
  bubble: { borderRadius: 16, paddingHorizontal: 16, paddingVertical: 12, borderWidth: 1 },
  userBubble: { backgroundColor: 'rgba(28, 37, 65, 0.7)', borderColor: 'rgba(91, 192, 190, 0.3)', borderTopRightRadius: 2 },
  alberthBubble: { backgroundColor: 'rgba(15, 23, 42, 0.85)', borderColor: 'rgba(159, 122, 234, 0.25)', borderTopLeftRadius: 2 },
  bubbleText: { fontSize: 15, color: '#f7fafc', lineHeight: 22 },
  systemBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    backgroundColor: 'rgba(91, 192, 190, 0.1)',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 6,
    marginVertical: 10,
    borderWidth: 1,
    borderColor: 'rgba(91, 192, 190, 0.2)',
    maxWidth: '90%',
  },
  systemText: { fontSize: 11, color: '#5BC0BE', fontWeight: '500', textAlign: 'center' },
  thinkingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  thinkingText: { fontSize: 13, color: '#a0aec0', fontStyle: 'italic' },
  waveformContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 100,
    paddingHorizontal: 20,
    backgroundColor: 'rgba(6, 10, 20, 0.5)',
  },
  waveBar: { width: 6, borderRadius: 3, marginHorizontal: 3 },
  glassFooter: {
    backgroundColor: 'rgba(10, 15, 30, 0.95)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
    paddingTop: 15,
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  voiceSection: { alignItems: 'center', marginBottom: 15 },
  micButton: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: 'rgba(91, 192, 190, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#5BC0BE',
    shadowColor: '#5BC0BE',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 6,
  },
  micButtonActive: {
    backgroundColor: '#5BC0BE',
    borderColor: '#fff',
    transform: [{ scale: 1.1 }],
    shadowColor: '#fff',
    shadowOpacity: 0.6,
    shadowRadius: 15,
  },
  micHelpText: { fontSize: 11, color: '#a0aec0', marginTop: 6, fontWeight: '500' },
  inputRow: { flexDirection: 'row', alignItems: 'center' },
  textInput: {
    flex: 1,
    height: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: 20,
    paddingHorizontal: 16,
    color: '#fff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#5BC0BE',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(2, 4, 8, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    width: '100%',
    backgroundColor: '#0c1020',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    padding: 24,
    elevation: 20,
  },
  modalTitle: { fontSize: 18, fontWeight: 'bold', color: '#fff', marginBottom: 20, textAlign: 'center', letterSpacing: 1 },
  settingGroup: { marginBottom: 16 },
  settingRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, paddingVertical: 8 },
  settingLabel: { fontSize: 14, color: '#cbd5e0', marginBottom: 8 },
  modalInput: {
    height: 46,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    paddingHorizontal: 16,
    color: '#fff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  modalActions: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  modalButton: { flex: 1, height: 46, borderRadius: 12, justifyContent: 'center', alignItems: 'center', flexDirection: 'row', marginHorizontal: 5 },
  buttonSuccess: { backgroundColor: '#5BC0BE' },
  buttonDanger: { backgroundColor: 'rgba(255, 74, 74, 0.1)', borderWidth: 1, borderColor: '#ff4a4a' },
  buttonText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  closeModalButton: { marginTop: 20, alignSelf: 'center' },
  closeModalText: { fontSize: 13, color: '#718096', fontWeight: '500' },
});
