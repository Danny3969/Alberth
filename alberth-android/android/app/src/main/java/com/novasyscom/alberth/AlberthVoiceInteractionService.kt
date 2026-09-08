package com.novasyscom.alberth

import android.service.voice.VoiceInteractionService
import android.util.Log

class AlberthVoiceInteractionService : VoiceInteractionService() {
    companion object {
        private const val TAG = "AlberthVoiceService"
        var isActive: Boolean = false
    }

    override fun onReady() {
        super.onReady()
        isActive = true
        Log.i(TAG, "AlberthVoiceInteractionService is ready as system assistant")
    }

    override fun onShutdown() {
        isActive = false
        super.onShutdown()
        Log.i(TAG, "AlberthVoiceInteractionService shutdown")
    }
}
