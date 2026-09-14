#!/usr/bin/env python3
# =============================================================================
# ALBERTH MUSIC PLAYER — Motor de Streaming y Gestión de Playlists de YouTube Music
# Compatible con Echo Music / YouTube Music para reproducción autónoma en Mac
# =============================================================================

import os
import sys
import json
import time
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

WORKSPACE_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = WORKSPACE_DIR / "memory"
PLAYLISTS_FILE = MEMORY_DIR / "alberth_playlists.json"

# Ruta del binario yt-dlp en el venv local
VENV_YT_DLP = WORKSPACE_DIR / "venv" / "bin" / "yt-dlp"
YT_DLP_BIN = str(VENV_YT_DLP) if VENV_YT_DLP.exists() else "yt-dlp"

# Caché en memoria para URLs de stream: {track_id: (stream_url, timestamp)}
# Las URLs de YouTube expiran usualmente a las 6 horas; mantenemos 4 horas de validez
_STREAM_CACHE: Dict[str, tuple] = {}
CACHE_TTL = 4 * 3600

# Caché de pistas de playlist en memoria
_PLAYLIST_CACHE: Dict[str, Any] = {
    "url": None,
    "title": "Mi Playlist Echo",
    "updated_at": 0,
    "tracks": []
}

def _ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def load_stored_playlist_config() -> dict:
    _ensure_memory_dir()
    if PLAYLISTS_FILE.exists():
        try:
            with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[MusicPlayer] Error al cargar configuración: {e}", file=sys.stderr)
    return {
        "active_playlist_url": "https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
        "playlist_name": "Mi Playlist Echo Music",
        "updated_at": None,
        "custom_tracks": []
    }

def save_stored_playlist_config(config: dict):
    _ensure_memory_dir()
    try:
        with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[MusicPlayer] Error al guardar configuración: {e}", file=sys.stderr)

class AlberthMusicPlayer:
    def __init__(self):
        self.config = load_stored_playlist_config()
        self.active_url = self.config.get("active_playlist_url")
        self.playlist_name = self.config.get("playlist_name", "Mi Playlist Echo Music")

    def set_playlist(self, url_or_id: str, name: Optional[str] = None) -> dict:
        url = url_or_id.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            # Puede ser solo el ID de la lista (ej. PL...)
            url = f"https://www.youtube.com/playlist?list={url}"
        
        self.active_url = url
        if name:
            self.playlist_name = name
        
        self.config["active_playlist_url"] = self.active_url
        self.config["playlist_name"] = self.playlist_name
        self.config["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_stored_playlist_config(self.config)

        # Invalidar caché de playlist
        _PLAYLIST_CACHE["updated_at"] = 0
        return self.get_playlist_tracks(force_refresh=True)

    def get_playlist_tracks(self, force_refresh: bool = False) -> dict:
        now = time.time()
        # Si está en caché y tiene menos de 1 hora de antigüedad, retornar de memoria
        if not force_refresh and _PLAYLIST_CACHE["url"] == self.active_url and (now - _PLAYLIST_CACHE["updated_at"] < 3600) and _PLAYLIST_CACHE["tracks"]:
            return {
                "ok": True,
                "title": _PLAYLIST_CACHE["title"],
                "url": self.active_url,
                "count": len(_PLAYLIST_CACHE["tracks"]),
                "tracks": _PLAYLIST_CACHE["tracks"],
                "cached": True
            }

        if not self.active_url:
            return {"ok": False, "error": "No hay playlist configurada", "tracks": []}

        cmd = [
            YT_DLP_BIN,
            "--flat-playlist",
            "--dump-single-json",
            "--no-warnings",
            "--quiet",
            self.active_url
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if res.returncode != 0 or not res.stdout.strip():
                # Si falló, intentar devolver lo que haya en caché
                if _PLAYLIST_CACHE["tracks"]:
                    return {
                        "ok": True,
                        "title": _PLAYLIST_CACHE["title"],
                        "url": self.active_url,
                        "count": len(_PLAYLIST_CACHE["tracks"]),
                        "tracks": _PLAYLIST_CACHE["tracks"],
                        "cached": True,
                        "warning": "Usando versión en caché"
                    }
                return {"ok": False, "error": res.stderr or "No se pudo extraer la lista", "tracks": []}

            data = json.loads(res.stdout)
            raw_entries = data.get("entries", [])
            playlist_title = data.get("title") or self.playlist_name

            tracks = []
            for i, item in enumerate(raw_entries):
                track_id = item.get("id")
                if not track_id:
                    continue
                title = item.get("title") or "Canción desconocida"
                uploader = item.get("uploader") or item.get("channel") or "Artista Desconocido"
                
                # Intentar limpiar título si viene como "Artista - Canción"
                if " - " in title and uploader == "Artista Desconocido":
                    parts = title.split(" - ", 1)
                    uploader = parts[0].strip()
                    title = parts[1].strip()

                duration = item.get("duration") or 0
                
                # Obtener la mejor miniatura disponible
                thumbnails = item.get("thumbnails") or []
                thumbnail_url = thumbnails[-1].get("url") if thumbnails else f"https://img.youtube.com/vi/{track_id}/hqdefault.jpg"

                tracks.append({
                    "index": i,
                    "id": track_id,
                    "title": title,
                    "artist": uploader,
                    "duration": duration,
                    "duration_str": f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "--:--",
                    "thumbnail": thumbnail_url,
                    "url": f"https://www.youtube.com/watch?v={track_id}"
                })

            _PLAYLIST_CACHE["url"] = self.active_url
            _PLAYLIST_CACHE["title"] = playlist_title
            _PLAYLIST_CACHE["updated_at"] = now
            _PLAYLIST_CACHE["tracks"] = tracks

            return {
                "ok": True,
                "title": playlist_title,
                "url": self.active_url,
                "count": len(tracks),
                "tracks": tracks,
                "cached": False
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "tracks": []}

    def get_stream_url(self, track_id: str) -> dict:
        """Obtiene la URL directa de audio para reproducir en el navegador."""
        now = time.time()
        if track_id in _STREAM_CACHE:
            cached_url, ts, meta = _STREAM_CACHE[track_id]
            if now - ts < CACHE_TTL:
                return {"ok": True, "stream_url": cached_url, "track_id": track_id, "cached": True, **meta}

        cmd = [
            YT_DLP_BIN,
            "--extractor-args", "youtube:player_client=android,web",
            "-f", "bestaudio/best",
            "-g",
            f"https://www.youtube.com/watch?v={track_id}"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            lines = res.stdout.strip().split("\n")
            stream_url = None
            for line in lines:
                line = line.strip()
                if line.startswith("https://"):
                    stream_url = line

            if not stream_url:
                return {"ok": False, "error": "No se pudo generar el stream de audio", "details": res.stderr}

            meta = {"track_id": track_id}
            _STREAM_CACHE[track_id] = (stream_url, now, meta)
            return {"ok": True, "stream_url": stream_url, "track_id": track_id, "cached": False}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def search_song(self, query: str) -> dict:
        """Busca una canción individual en YouTube Music y retorna metadatos + stream directo."""
        clean_q = re.sub(r'\b(pon|reproduce|cancion|musica|de|el|la|en youtube|en echo music)\b', ' ', query, flags=re.IGNORECASE)
        clean_q = " ".join(clean_q.split()).strip()
        if not clean_q:
            clean_q = "Top Music"

        cmd = [
            YT_DLP_BIN,
            "--extractor-args", "youtube:player_client=android,web",
            f"ytsearch1:{clean_q}",
            "--dump-single-json",
            "--no-warnings",
            "--quiet"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode != 0 or not res.stdout.strip():
                return {"ok": False, "error": f"No se encontró la canción '{clean_q}'"}

            data = json.loads(res.stdout)
            entries = data.get("entries", [data])
            if not entries:
                return {"ok": False, "error": f"Sin resultados para '{clean_q}'"}

            item = entries[0]
            track_id = item.get("id")
            title = item.get("title") or clean_q
            artist = item.get("uploader") or item.get("channel") or "Artista"
            duration = item.get("duration") or 0
            thumbnails = item.get("thumbnails") or []
            thumbnail_url = thumbnails[-1].get("url") if thumbnails else f"https://img.youtube.com/vi/{track_id}/hqdefault.jpg"

            # Obtener stream
            stream_res = self.get_stream_url(track_id)
            if not stream_res.get("ok"):
                return stream_res

            return {
                "ok": True,
                "id": track_id,
                "title": title,
                "artist": artist,
                "duration": duration,
                "duration_str": f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "--:--",
                "thumbnail": thumbnail_url,
                "stream_url": stream_res["stream_url"]
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

# Instancia global única
music_player = AlberthMusicPlayer()

if __name__ == "__main__":
    player = AlberthMusicPlayer()
    print("Obteniendo canciones de la playlist activa...")
    tracks = player.get_playlist_tracks()
    print(f"Resultado: {tracks.get('ok')}, Total canciones: {tracks.get('count')}")
    if tracks.get("tracks"):
        first = tracks["tracks"][0]
        print(f"Primera pista: {first['title']} ({first['id']})")
        print("Obteniendo stream...")
        stream = player.get_stream_url(first['id'])
        print(f"Stream OK: {stream.get('ok')}, URL: {bool(stream.get('stream_url'))}")
