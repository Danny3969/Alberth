#!/usr/bin/env python3
# =============================================================================
# ALBERTH MUSIC PLAYER — Motor Multi-Playlist y Streaming de YouTube Music
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
_STREAM_CACHE: Dict[str, tuple] = {}
CACHE_TTL = 4 * 3600

# Caché de pistas por cada playlist: {playlist_id: {"title": ..., "tracks": [...], "updated_at": ...}}
_PLAYLISTS_CACHE: Dict[str, Any] = {}

def _ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def _normalize_playlist_url(url_or_id: str) -> str:
    url = url_or_id.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://www.youtube.com/playlist?list={url}"

def _slugify(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower()).strip('_')
    return slug or f"pl_{int(time.time())}"

def load_stored_playlist_config() -> dict:
    _ensure_memory_dir()
    default_config = {
        "active_playlist_id": "rock_classics",
        "playlists": [
            {
                "id": "rock_classics",
                "name": "Rock Classics",
                "url": "https://www.youtube.com/playlist?list=PL4fGSIFgk54G7i5w_Yp9h5iZ5s_9V7d3d",
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "pop_hits",
                "name": "Pop Hits",
                "url": "https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
    }

    if PLAYLISTS_FILE.exists():
        try:
            with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migración de versión previa simple a multi-playlist
                if "active_playlist_url" in data and "playlists" not in data:
                    active_url = data["active_playlist_url"]
                    active_name = data.get("playlist_name", "Mi Playlist Echo")
                    pid = _slugify(active_name)
                    data = {
                        "active_playlist_id": pid,
                        "playlists": [
                            {
                                "id": pid,
                                "name": active_name,
                                "url": active_url,
                                "updated_at": data.get("updated_at") or time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                        ]
                    }
                    save_stored_playlist_config(data)
                return data
        except Exception as e:
            print(f"[MusicPlayer] Error al cargar configuración: {e}", file=sys.stderr)
    return default_config

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

    @property
    def playlists(self) -> List[Dict[str, Any]]:
        return self.config.get("playlists", [])

    @property
    def active_id(self) -> str:
        aid = self.config.get("active_playlist_id")
        if not aid and self.playlists:
            aid = self.playlists[0]["id"]
            self.config["active_playlist_id"] = aid
        return aid

    def get_active_playlist_meta(self) -> Optional[Dict[str, Any]]:
        for pl in self.playlists:
            if pl["id"] == self.active_id:
                return pl
        if self.playlists:
            return self.playlists[0]
        return None

    def get_all_playlists(self) -> dict:
        """Devuelve la lista completa de playlists registradas con el ID activo."""
        active_meta = self.get_active_playlist_meta()
        return {
            "ok": True,
            "active_id": self.active_id,
            "active_name": active_meta["name"] if active_meta else "Sin Playlist",
            "active_url": active_meta["url"] if active_meta else "",
            "playlists": self.playlists
        }

    def add_or_update_playlist(self, name: str, url_or_id: str, set_active: bool = True) -> dict:
        """Agrega una nueva playlist o actualiza una existente."""
        name = name.strip() or "Nueva Playlist"
        url = _normalize_playlist_url(url_or_id)
        pid = _slugify(name)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        existing = None
        for pl in self.playlists:
            if pl["id"] == pid or pl["name"].lower() == name.lower():
                existing = pl
                break

        if existing:
            existing["url"] = url
            existing["name"] = name
            existing["updated_at"] = now_str
            target_id = existing["id"]
        else:
            new_pl = {
                "id": pid,
                "name": name,
                "url": url,
                "updated_at": now_str
            }
            self.playlists.append(new_pl)
            target_id = pid

        if set_active:
            self.config["active_playlist_id"] = target_id

        save_stored_playlist_config(self.config)
        
        # Invalidar caché de esta playlist
        if target_id in _PLAYLISTS_CACHE:
            del _PLAYLISTS_CACHE[target_id]

        tracks_res = self.get_playlist_tracks(force_refresh=True)
        return {
            "ok": True,
            "message": f"Playlist '{name}' guardada exitosamente.",
            "all_playlists": self.get_all_playlists(),
            **tracks_res
        }

    def switch_playlist(self, id_or_name: str) -> dict:
        """Cambia la playlist activa por ID o por nombre."""
        target = None
        search = id_or_name.strip().lower()

        # Búsqueda exacta por ID
        for pl in self.playlists:
            if pl["id"] == id_or_name:
                target = pl
                break

        # Búsqueda por nombre si no se encontró por ID
        if not target:
            for pl in self.playlists:
                if pl["name"].lower() == search or search in pl["name"].lower():
                    target = pl
                    break

        if not target:
            return {"ok": False, "error": f"No se encontró la playlist '{id_or_name}'"}

        self.config["active_playlist_id"] = target["id"]
        save_stored_playlist_config(self.config)

        tracks_res = self.get_playlist_tracks()
        return {
            "ok": True,
            "switched_to": target,
            "playlist_id": target["id"],
            "playlist_name": target["name"],
            "all_playlists": self.get_all_playlists(),
            **tracks_res
        }

    def cycle_next_playlist(self) -> dict:
        """Alterna a la siguiente playlist registrada en ciclo circular."""
        if not self.playlists:
            return {"ok": False, "error": "No hay playlists registradas"}

        current_idx = 0
        for i, pl in enumerate(self.playlists):
            if pl["id"] == self.active_id:
                current_idx = i
                break

        next_idx = (current_idx + 1) % len(self.playlists)
        next_pl = self.playlists[next_idx]
        return self.switch_playlist(next_pl["id"])

    def delete_playlist(self, playlist_id: str) -> dict:
        """Elimina una playlist. Conserva al menos una."""
        if len(self.playlists) <= 1:
            return {"ok": False, "error": "No puedes eliminar la única playlist existente"}

        self.config["playlists"] = [pl for pl in self.playlists if pl["id"] != playlist_id]
        if self.active_id == playlist_id:
            self.config["active_playlist_id"] = self.playlists[0]["id"]

        save_stored_playlist_config(self.config)
        if playlist_id in _PLAYLISTS_CACHE:
            del _PLAYLISTS_CACHE[playlist_id]

        return {
            "ok": True,
            "message": "Playlist eliminada",
            "all_playlists": self.get_all_playlists(),
            **self.get_playlist_tracks()
        }

    def get_playlist_tracks(self, force_refresh: bool = False) -> dict:
        """Extrae o retorna en caché las canciones de la playlist actualmente activa."""
        active_meta = self.get_active_playlist_meta()
        if not active_meta:
            return {"ok": False, "error": "No hay playlist activa configurada", "tracks": []}

        pid = active_meta["id"]
        url = active_meta["url"]
        now = time.time()

        # Si está en caché y tiene menos de 1 hora de antigüedad, retornar de memoria
        if not force_refresh and pid in _PLAYLISTS_CACHE:
            cached = _PLAYLISTS_CACHE[pid]
            if (now - cached["updated_at"] < 3600) and cached["tracks"]:
                return {
                    "ok": True,
                    "playlist_id": pid,
                    "playlist_name": active_meta["name"],
                    "title": cached["title"],
                    "url": url,
                    "count": len(cached["tracks"]),
                    "tracks": cached["tracks"],
                    "cached": True
                }

        cmd = [
            YT_DLP_BIN,
            "--flat-playlist",
            "--dump-single-json",
            "--no-warnings",
            "--quiet",
            url
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            if res.returncode != 0 or not res.stdout.strip():
                if pid in _PLAYLISTS_CACHE and _PLAYLISTS_CACHE[pid]["tracks"]:
                    cached = _PLAYLISTS_CACHE[pid]
                    return {
                        "ok": True,
                        "playlist_id": pid,
                        "playlist_name": active_meta["name"],
                        "title": cached["title"],
                        "url": url,
                        "count": len(cached["tracks"]),
                        "tracks": cached["tracks"],
                        "cached": True,
                        "warning": "Usando versión en caché previa"
                    }
                return {"ok": False, "error": res.stderr or "No se pudo extraer la lista", "tracks": []}

            data = json.loads(res.stdout)
            raw_entries = data.get("entries", [])
            playlist_title = data.get("title") or active_meta["name"]

            tracks = []
            for i, item in enumerate(raw_entries):
                track_id = item.get("id")
                if not track_id:
                    continue
                title = item.get("title") or "Canción desconocida"
                uploader = item.get("uploader") or item.get("channel") or "Artista Desconocido"
                
                if " - " in title and uploader == "Artista Desconocido":
                    parts = title.split(" - ", 1)
                    uploader = parts[0].strip()
                    title = parts[1].strip()

                duration = item.get("duration") or 0
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

            _PLAYLISTS_CACHE[pid] = {
                "title": playlist_title,
                "tracks": tracks,
                "updated_at": now
            }

            return {
                "ok": True,
                "playlist_id": pid,
                "playlist_name": active_meta["name"],
                "title": playlist_title,
                "url": url,
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
    print("Playlists disponibles:", player.get_all_playlists())
    print("Pistas activas:", player.get_playlist_tracks().get("count"))
