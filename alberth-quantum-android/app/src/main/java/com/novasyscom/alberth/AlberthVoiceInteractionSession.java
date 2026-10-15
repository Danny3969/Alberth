package com.novasyscom.alberth;

import android.app.assist.AssistContent;
import android.app.assist.AssistStructure;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;

public class AlberthVoiceInteractionSession extends VoiceInteractionSession {

    public AlberthVoiceInteractionSession(Context context) {
        super(context);
    }

    @Override
    public void onHandleAssist(Bundle data, AssistStructure structure, AssistContent content) {
        super.onHandleAssist(data, structure, content);
        // Al invocarse como asistente predeterminado (botón power o gesto de esquina), abrir Alberth al frente
        Intent intent = new Intent(getContext(), MainActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        intent.putExtra("TRIGGER_WAKE_WORD", true);
        intent.putExtra("HEARD_PHRASE", "alberth");
        getContext().startActivity(intent);
        hide();
    }

    @Override
    public void onHandleScreenshot(Bitmap screenshot) {
        super.onHandleScreenshot(screenshot);
    }
}
