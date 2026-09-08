import { Linking, NativeModules, Platform } from 'react-native';
import * as Contacts from 'expo-contacts';
import * as Location from 'expo-location';

const { AlberthAssistantModule } = NativeModules;

// Diccionario de paquetes de apps comunes en Android
const KNOWN_PACKAGES: { [alias: string]: string } = {
  youtube: 'com.google.android.youtube',
  spotify: 'com.spotify.music',
  whatsapp: 'com.whatsapp',
  chrome: 'com.android.chrome',
  maps: 'com.google.android.apps.maps',
  google_maps: 'com.google.android.apps.maps',
  camara: 'com.android.camera',
  camera: 'com.android.camera',
  galeria: 'com.android.gallery3d',
  gallery: 'com.android.gallery3d',
  fotos: 'com.google.android.apps.photos',
  photos: 'com.google.android.apps.photos',
  gmail: 'com.google.android.gm',
  reloj: 'com.google.android.deskclock',
  clock: 'com.google.android.deskclock',
  calculadora: 'com.google.android.calculator',
  calculator: 'com.google.android.calculator',
  ajustes: 'com.android.settings',
  configuracion: 'com.android.settings',
  settings: 'com.android.settings',
  tiktok: 'com.zhiliaoapp.musically',
  instagram: 'com.instagram.android',
  facebook: 'com.facebook.katana',
  netflix: 'com.netflix.mediaclient',
  playstore: 'com.android.vending',
  telegram: 'org.telegram.messenger',
  twitter: 'com.twitter.android',
  x: 'com.twitter.android',
};

/**
 * Helper maestro para automatización y control total del sistema Android OS por Alberth.
 */
export const androidSystemHelper = {
  // ================= ACCESIBILIDAD Y CONTROL DE PANTALLA =================

  isAccessibilityEnabled: async (): Promise<boolean> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) return false;
    try {
      return await AlberthAssistantModule.isAccessibilityEnabled();
    } catch {
      return false;
    }
  },

  openAccessibilitySettings: async (): Promise<boolean> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) return false;
    try {
      return await AlberthAssistantModule.openAccessibilitySettings();
    } catch {
      return false;
    }
  },

  isDefaultAssistant: async (): Promise<boolean> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) return false;
    try {
      return await AlberthAssistantModule.isDefaultAssistant();
    } catch {
      return false;
    }
  },

  openAssistantSettings: async (): Promise<boolean> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) return false;
    try {
      return await AlberthAssistantModule.openAssistantSettings();
    } catch {
      return false;
    }
  },

  performClick: async (x: number, y: number): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Módulo nativo de control no disponible' };
    }
    try {
      await AlberthAssistantModule.performClick(x, y);
      return { ok: true, output: `Toque realizado en (${x}, ${y})` };
    } catch (e: any) {
      return { ok: false, output: `Fallo al tocar: ${e.message}` };
    }
  },

  performSwipe: async (
    x1: number,
    y1: number,
    x2: number,
    y2: number,
    durationMs: number = 300
  ): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Módulo nativo no disponible' };
    }
    try {
      await AlberthAssistantModule.performSwipe(x1, y1, x2, y2, durationMs);
      return { ok: true, output: `Deslizamiento de (${x1}, ${y1}) a (${x2}, ${y2})` };
    } catch (e: any) {
      return { ok: false, output: `Error al deslizar: ${e.message}` };
    }
  },

  pressHome: async (): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Plataforma no compatible' };
    }
    try {
      await AlberthAssistantModule.pressHome();
      return { ok: true, output: 'Inicio presionado' };
    } catch (e: any) {
      return { ok: false, output: `Error: ${e.message}` };
    }
  },

  pressBack: async (): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Plataforma no compatible' };
    }
    try {
      await AlberthAssistantModule.pressBack();
      return { ok: true, output: 'Atrás presionado' };
    } catch (e: any) {
      return { ok: false, output: `Error: ${e.message}` };
    }
  },

  pressRecents: async (): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Plataforma no compatible' };
    }
    try {
      await AlberthAssistantModule.pressRecents();
      return { ok: true, output: 'Apps recientes mostradas' };
    } catch (e: any) {
      return { ok: false, output: `Error: ${e.message}` };
    }
  },

  pressNotifications: async (): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Plataforma no compatible' };
    }
    try {
      await AlberthAssistantModule.pressNotifications();
      return { ok: true, output: 'Panel de notificaciones desplegado' };
    } catch (e: any) {
      return { ok: false, output: `Error: ${e.message}` };
    }
  },

  /**
   * Lee la jerarquía visual de la pantalla activa mediante AccessibilityService.
   */
  readScreenText: async (): Promise<{ ok: boolean; output: string; raw?: any }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Módulo nativo no disponible en esta plataforma' };
    }
    try {
      const resultJson = await AlberthAssistantModule.readScreenText();
      const parsed = JSON.parse(resultJson);
      return {
        ok: true,
        output: parsed.summary || 'Pantalla analizada sin texto legible',
        raw: parsed,
      };
    } catch (e: any) {
      return { ok: false, output: `No se pudo leer la pantalla: ${e.message}` };
    }
  },

  /**
   * Hace clic en un elemento de pantalla que contenga el texto buscado.
   */
  clickTextOnScreen: async (text: string): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Módulo nativo no disponible' };
    }
    try {
      await AlberthAssistantModule.clickTextOnScreen(text);
      return { ok: true, output: `Clic realizado en el elemento con texto "${text}"` };
    } catch (e: any) {
      return { ok: false, output: `Error al hacer clic en "${text}": ${e.message}` };
    }
  },

  // ================= APLICACIONES Y MULTIMEDIA =================

  /**
   * Abre cualquier aplicación instalada por nombre común o nombre de paquete.
   */
  launchApp: async (appNameOrPackage: string): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Módulo nativo no disponible' };
    }
    try {
      const cleanName = appNameOrPackage.toLowerCase().trim().replace(/\s+/g, '_');
      const targetPackage = KNOWN_PACKAGES[cleanName] || appNameOrPackage;

      await AlberthAssistantModule.launchApp(targetPackage);
      return { ok: true, output: `Abriendo aplicación: ${appNameOrPackage}` };
    } catch (e: any) {
      // Intento de fallback: buscar coincidencia en aplicaciones instaladas
      try {
        const appsJson = await AlberthAssistantModule.getInstalledApps();
        const apps = JSON.parse(appsJson);
        const match = apps.find((app: any) =>
          app.label.toLowerCase().includes(appNameOrPackage.toLowerCase())
        );
        if (match) {
          await AlberthAssistantModule.launchApp(match.package);
          return { ok: true, output: `Abriendo ${match.label}` };
        }
      } catch {}
      return { ok: false, output: `No se pudo abrir ${appNameOrPackage}: ${e.message}` };
    }
  },

  /**
   * Reproduce música o videos en YouTube o Spotify.
   */
  playMedia: async (
    query: string,
    service: 'youtube' | 'spotify' | 'auto' = 'auto'
  ): Promise<{ ok: boolean; output: string }> => {
    if (Platform.OS !== 'android' || !AlberthAssistantModule) {
      return { ok: false, output: 'Módulo nativo no disponible' };
    }
    try {
      let mediaType = service;
      if (service === 'auto') {
        if (query.toLowerCase().includes('video') || query.toLowerCase().includes('youtube')) {
          mediaType = 'youtube';
        } else {
          mediaType = 'spotify';
        }
      }
      await AlberthAssistantModule.playMedia(query, mediaType);
      return { ok: true, output: `Reproduciendo "${query}" en ${mediaType.toUpperCase()}` };
    } catch (e: any) {
      return { ok: false, output: `Error al reproducir: ${e.message}` };
    }
  },

  // ================= TELEFONÍA Y CONTACTOS =================

  makeCall: async (phoneNumber: string): Promise<{ ok: boolean; output: string }> => {
    try {
      const url = `tel:${phoneNumber}`;
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
        return { ok: true, output: `Llamando a ${phoneNumber}` };
      } else {
        return { ok: false, output: `Marcación telefónica no soportada` };
      }
    } catch (e: any) {
      return { ok: false, output: `Error al llamar: ${e.message}` };
    }
  },

  sendSMS: async (phoneNumber: string, message: string): Promise<{ ok: boolean; output: string }> => {
    try {
      const url = `sms:${phoneNumber}${message ? `?body=${encodeURIComponent(message)}` : ''}`;
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
        return { ok: true, output: `Abriendo SMS para ${phoneNumber}` };
      } else {
        return { ok: false, output: `Envío de SMS no soportado` };
      }
    } catch (e: any) {
      return { ok: false, output: `Error al enviar SMS: ${e.message}` };
    }
  },

  searchContact: async (name: string): Promise<{ ok: boolean; output: string; data?: any }> => {
    try {
      const { status } = await Contacts.requestPermissionsAsync();
      if (status !== 'granted') {
        return { ok: false, output: 'Permiso de contactos denegado' };
      }

      const { data } = await Contacts.getContactsAsync({
        name,
        fields: [Contacts.Fields.PhoneNumbers, Contacts.Fields.Emails],
      });

      if (data && data.length > 0) {
        const contact = data[0];
        const phones = contact.phoneNumbers?.map((p) => p.number).join(', ') || 'Sin número';
        return {
          ok: true,
          output: `Contacto: ${contact.name} (${phones})`,
          data: contact,
        };
      } else {
        return { ok: false, output: `No encontré ningún contacto con el nombre "${name}"` };
      }
    } catch (e: any) {
      return { ok: false, output: `Error al buscar contactos: ${e.message}` };
    }
  },

  getLocation: async (): Promise<{ ok: boolean; output: string; data?: any }> => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        return { ok: false, output: 'Permiso de ubicación denegado' };
      }
      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      return {
        ok: true,
        output: `Ubicación: Lat ${loc.coords.latitude.toFixed(5)}, Lon ${loc.coords.longitude.toFixed(5)}`,
        data: {
          latitude: loc.coords.latitude,
          longitude: loc.coords.longitude,
          altitude: loc.coords.altitude,
        },
      };
    } catch (e: any) {
      return { ok: false, output: `Error al obtener ubicación: ${e.message}` };
    }
  },
};
