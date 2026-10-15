package com.novasyscom.alberth;

import android.service.voice.VoiceInteractionService;

/**
 * AlberthVoiceInteractionService — Registra a Alberth como el Asistente Digital Oficial del teléfono
 * Permite configurarlo en Ajustes > Aplicaciones Predeterminadas > Asistencia Digital
 */
public class AlberthVoiceInteractionService extends VoiceInteractionService {
    @Override
    public void onReady() {
        super.onReady();
    }
}
