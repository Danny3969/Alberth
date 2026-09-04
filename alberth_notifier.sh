#!/bin/bash
# =============================================================================
# ALBERTH NOTIFIER — Sistema de Notificaciones Nativas de macOS
# Muestra alertas del sistema usando osascript (AppleScript).
# Uso: ./alberth_notifier.sh "Título" "Subtítulo" "Mensaje"
# =============================================================================

TITLE="${1:-Alberth}"
SUBTITLE="${2:-Aviso}"
MESSAGE="${3:-Sin mensaje.}"

# Notificación nativa del sistema macOS
osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\" subtitle \"$SUBTITLE\" sound name \"Ping\""
