package com.novasyscom.alberth

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService
import android.util.Log

class AlberthVoiceInteractionSessionService : VoiceInteractionSessionService() {
    override fun onNewSession(args: Bundle?): VoiceInteractionSession {
        return AlberthVoiceInteractionSession(this)
    }
}

class AlberthVoiceInteractionSession(context: Context) : VoiceInteractionSession(context) {
    override fun onShow(args: Bundle?, showFlags: Int) {
        super.onShow(args, showFlags)
        Log.i("AlberthVoiceSession", "Voice assist session triggered: flags=$showFlags")
        try {
            val intent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                putExtra("VOICE_ASSIST_TRIGGERED", true)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            Log.e("AlberthVoiceSession", "Error launching MainActivity from voice session", e)
        }
        hide()
    }
}
