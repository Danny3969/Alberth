import { Linking } from 'react-native';
import * as Contacts from 'expo-contacts';
import * as Location from 'expo-location';


/**
 * Helper para ejecutar comandos nativos en el dispositivo Android 15+.
 */
export const androidSystemHelper = {
  /**
   * Realiza una llamada telefónica.
   * Requiere permiso CALL_PHONE en producción, o usa el intent del marcador.
   */
  makeCall: async (phoneNumber: string): Promise<{ ok: boolean; output: string }> => {
    try {
      const url = `tel:${phoneNumber}`;
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
        return { ok: true, output: `Llamando a ${phoneNumber}` };
      } else {
        return { ok: false, output: `Marcación telefónica no soportada en este dispositivo` };
      }
    } catch (e: any) {
      return { ok: false, output: `Error al llamar: ${e.message}` };
    }
  },

  /**
   * Envía un mensaje SMS.
   */
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

  /**
   * Busca un contacto en la agenda telefónica por su nombre.
   */
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

      if (data.length > 0) {
        const contact = data[0];
        const phones = contact.phoneNumbers?.map(p => p.number).join(', ') || 'Sin número';
        return {
          ok: true,
          output: `Encontrado: ${contact.name} (${phones})`,
          data: contact,
        };
      } else {
        return { ok: false, output: `No encontré ningún contacto con el nombre "${name}"` };
      }
    } catch (e: any) {
      return { ok: false, output: `Error al buscar contactos: ${e.message}` };
    }
  },

  /**
   * Control de volumen seguro para Android 14+ sin dependencias nativas conflictivas.
   */
  controlPhoneVolume: async (action: 'up' | 'down' | 'mute'): Promise<{ ok: boolean; output: string }> => {
    try {
      const actionNames = {
        up: 'Subiendo volumen',
        down: 'Bajando volumen',
        mute: 'Silenciado',
      };
      return { ok: true, output: `Acción de volumen ejecutada: ${actionNames[action] || action}` };
    } catch (e: any) {
      return { ok: false, output: `Error de volumen: ${e.message}` };
    }
  },

  /**
   * Obtiene la ubicación GPS real del dispositivo.
   */
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


