import os
import sys
import time
import json
import asyncio
import fnmatch
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

import httpx
import psutil
from fastapi import FastAPI, Request, BackgroundTasks, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# --- CONSTANTS ---
VERSION = "1.0.0"
CONFIG_FILE = "/config/config.json"
LOG_FILE = "/config/preloader.log"
HISTORY_FILE = "/config/history.json"

# --- TRANSLATIONS ---
TRANSLATIONS = {
    "en": {
        "title": "Video Preloader",
        "subtitle": "Smart caching for Plex & Jellyfin with Tautulli integration",
        "status": "Status",
        "loaded": "Loaded",
        "total_cached": "Total Cached",
        "duration": "Duration",
        "last_run": "Last Run",
        "run_now": "Run Preloader Now",
        "running": "Running...",
        "history": "History",
        "live_logs": "Live Logs",
        "paths": "Paths",
        "video_paths": "Video Paths (comma-separated)",
        "priority_paths": "Priority Paths (loaded first)",
        "exclude_patterns": "Exclude Patterns (will be skipped)",
        "preload_settings": "Preload Settings",
        "head_preload": "Head Preload (MB)",
        "tail_preload": "Tail Preload (MB)",
        "file_start": "File start",
        "file_end": "File end",
        "min_file_size": "Min. File Size (MB)",
        "ignore_smaller": "Ignore smaller",
        "max_files_per_run": "Max. Files per Run",
        "cache_threshold": "Cache Threshold (ms)",
        "faster_cached": "Faster = cached",
        "max_ram_usage": "Max RAM Usage",
        "video_extensions": "Video Extensions",
        "auto_scheduler": "Auto-Scheduler",
        "cron_schedule": "Cron Schedule",
        "cron_format": "Format: min hour day month weekday",
        "time_profiles": "Time Profiles (different sizes)",
        "day": "Day (6-18h)",
        "evening": "Evening (18-23h)",
        "night": "Night (23-6h)",
        "test_connection": "Test connection",
        "save_all": "Save all settings",
        "quick_info": "Quick Info",
        "paths_mapped": "Paths mapped to",
        "plex_webhook": "Plex Webhook",
        "config_saved_in": "Config saved in",
        "tautulli_loads": "Tautulli loads most-watched movies + next episodes",
        "ram_usage": "RAM Usage",
        "next": "Next",
        "scheduler_active": "Scheduler active",
        "no_history": "No history yet",
        "loading_history": "Loading history...",
        "waiting_logs": "Waiting for logs...",
        "api_key": "API Key",
        "top_movies_count": "Top Movies Count",
        "next_episodes_count": "Next Episodes Count",
        "language": "Language",
        "tautulli_integration": "Tautulli Integration",
        "tautulli_url": "Tautulli URL",
        "your_api_key": "Your API Key",
        "top_movies": "Top Movies",
        "next_episodes": "Next Episodes",
        "plex_integration": "Plex Integration",
        "plex_url": "Plex URL",
        "plex_token": "X-Plex-Token",
        "info_paths": "Paths mapped to",
        "info_webhook": "Plex Webhook:",
        "info_config": "Config saved in",
        "info_tautulli": "Tautulli loads most-watched movies + next episodes",
        "live_monitoring": "Live Monitoring",
        "live_monitoring_enabled": "Enable Live Monitoring",
        "live_check_interval": "Check Interval (seconds)",
        "live_episodes_count": "Episodes to preload",
        "live_monitoring_desc": "Automatically caches next episodes when someone is watching a series",
        "path_mappings": "Path Mappings",
        "path_mappings_desc": "Plex to Container (e.g. /media:/data)",
        "path_mappings_hint": "Format: plex_path:container_path, one mapping per line",
    },
    "de": {
        "title": "Video Preloader",
        "subtitle": "Intelligentes Caching für Plex & Jellyfin mit Tautulli-Integration",
        "status": "Status",
        "loaded": "Geladen",
        "total_cached": "Gesamt gecacht",
        "duration": "Dauer",
        "last_run": "Letzter Lauf",
        "run_now": "Preloader jetzt starten",
        "running": "Läuft...",
        "history": "Verlauf",
        "live_logs": "Live-Logs",
        "paths": "Pfade",
        "video_paths": "Video-Pfade (kommagetrennt)",
        "priority_paths": "Prioritäts-Pfade (werden zuerst geladen)",
        "exclude_patterns": "Exclude-Patterns (werden übersprungen)",
        "preload_settings": "Preload-Einstellungen",
        "head_preload": "Head-Preload (MB)",
        "tail_preload": "Tail-Preload (MB)",
        "file_start": "Dateianfang",
        "file_end": "Dateiende",
        "min_file_size": "Min. Dateigröße (MB)",
        "ignore_smaller": "Kleinere ignorieren",
        "max_files_per_run": "Max. Dateien pro Lauf",
        "cache_threshold": "Cache-Schwelle (ms)",
        "faster_cached": "Schneller = gecacht",
        "max_ram_usage": "Max RAM-Nutzung",
        "video_extensions": "Video-Erweiterungen",
        "auto_scheduler": "Auto-Scheduler",
        "cron_schedule": "Cron-Schedule",
        "cron_format": "Format: Min Std Tag Monat Wochentag",
        "time_profiles": "Zeit-Profile (unterschiedliche Größen)",
        "day": "Tag (6-18h)",
        "evening": "Abend (18-23h)",
        "night": "Nacht (23-6h)",
        "test_connection": "Verbindung testen",
        "save_all": "Alle Einstellungen speichern",
        "quick_info": "Kurzinfo",
        "paths_mapped": "Pfade gemappt auf",
        "plex_webhook": "Plex Webhook",
        "config_saved_in": "Config gespeichert in",
        "tautulli_loads": "Tautulli lädt meistgesehene Filme + nächste Folgen",
        "ram_usage": "RAM-Nutzung",
        "next": "Nächster",
        "scheduler_active": "Scheduler aktiv",
        "no_history": "Noch kein Verlauf",
        "loading_history": "Lade Verlauf...",
        "waiting_logs": "Warte auf Logs...",
        "api_key": "API-Key",
        "top_movies_count": "Top-Filme Anzahl",
        "next_episodes_count": "Nächste Folgen Anzahl",
        "language": "Sprache",
        "tautulli_integration": "Tautulli-Integration",
        "tautulli_url": "Tautulli URL",
        "your_api_key": "Dein API-Key",
        "top_movies": "Top-Filme",
        "next_episodes": "Nächste Folgen",
        "plex_integration": "Plex-Integration",
        "plex_url": "Plex URL",
        "plex_token": "X-Plex-Token",
        "info_paths": "Pfade gemappt auf",
        "info_webhook": "Plex Webhook:",
        "info_config": "Config gespeichert in",
        "info_tautulli": "Tautulli lädt meistgesehene Filme + nächste Folgen",
        "live_monitoring": "Live-Monitoring",
        "live_monitoring_enabled": "Live-Monitoring aktivieren",
        "live_check_interval": "Prüf-Intervall (Sekunden)",
        "live_episodes_count": "Episoden zum Vorladen",
        "live_monitoring_desc": "Cached automatisch nächste Episoden wenn jemand eine Serie schaut",
        "path_mappings": "Pfad-Mappings",
        "path_mappings_desc": "Plex zu Container (z.B. /media:/data)",
        "path_mappings_hint": "Format: plex_pfad:container_pfad, ein Mapping pro Zeile",
    }
}

# --- LOGGING SETUP ---
def setup_logging() -> logging.Logger:
    """Konfiguriert Dual-Logging für Console und Datei."""
    log = logging.getLogger("preloader")
    log.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    # Console Handler (für docker logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    return log

logger = setup_logging()

# --- SCHEDULER ---
scheduler = AsyncIOScheduler()

# Templates mit absolutem Pfad (Container-kompatibel)
TEMPLATE_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# --- DATA MODELS ---

class ScheduleProfile(BaseModel):
    """Zeitbasiertes Profil für unterschiedliche Preload-Größen."""
    start_hour: int = 0
    end_hour: int = 24
    preload_head_mb: int = 60


class Config(BaseModel):
    """Konfigurationsmodell für den Video Preloader."""
    # Basis-Pfade
    video_paths: List[str] = ["/data/movies", "/data/tv"]
    priority_paths: List[str] = []  # Diese werden zuerst geladen
    exclude_patterns: List[str] = ["*/Samples/*", "*/Extras/*", "*/Featurettes/*"]

    # Preload-Einstellungen
    min_size_mb: int = 500
    preload_head_mb: int = 60
    preload_tail_mb: int = 1
    ram_max_usage_percent: int = 80
    video_extensions: List[str] = ["mkv", "mp4", "avi", "mov", "wmv", "m4v"]
    cache_threshold_ms: int = 150
    max_files_per_run: int = 50

    # Scheduler
    scheduler_enabled: bool = False
    cron_schedule: str = "0 */2 * * *"  # Alle 2 Stunden

    # Zeitbasierte Profile (z.B. mehr laden zur Prime-Time)
    time_profiles: List[ScheduleProfile] = [
        ScheduleProfile(start_hour=6, end_hour=18, preload_head_mb=30),
        ScheduleProfile(start_hour=18, end_hour=23, preload_head_mb=100),
    ]
    use_time_profiles: bool = False

    # Plex Integration
    plex_url: str = ""
    plex_token: str = ""
    plex_enabled: bool = False

    # Tautulli Integration
    tautulli_url: str = ""
    tautulli_api_key: str = ""
    tautulli_enabled: bool = False
    tautulli_top_movies_count: int = 10  # Top X meistgesehene Filme
    tautulli_next_episodes_count: int = 5  # Nächste X Folgen pro Serie

    # Live-Monitoring: Echtzeit-Caching wenn jemand eine Serie schaut
    live_monitoring_enabled: bool = False
    live_check_interval_seconds: int = 60  # Wie oft prüfen
    live_episodes_to_preload: int = 3  # Wie viele nächste Episoden cachen

    # Pfad-Mapping: Plex-Pfade zu Container-Pfaden
    # Format: "plex_pfad:container_pfad" z.B. "/media:/data"
    path_mappings: List[str] = []

    # UI-Einstellungen
    language: str = "de"  # "de" oder "en"

    def map_path(self, plex_path: str) -> str:
        """
        Konvertiert einen Plex-Pfad zu einem Container-Pfad.

        Args:
            plex_path: Der Pfad wie Plex/Tautulli ihn sieht

        Returns:
            Der gemappte Container-Pfad
        """
        if not plex_path:
            return plex_path

        for mapping in self.path_mappings:
            if ':' in mapping:
                plex_prefix, container_prefix = mapping.split(':', 1)
                if plex_path.startswith(plex_prefix):
                    return plex_path.replace(plex_prefix, container_prefix, 1)

        return plex_path

    @classmethod
    def load(cls) -> "Config":
        """Lädt die Konfiguration aus der JSON-Datei."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    # Konvertiere time_profiles falls vorhanden
                    if 'time_profiles' in data:
                        data['time_profiles'] = [
                            ScheduleProfile(**p) if isinstance(p, dict) else p
                            for p in data['time_profiles']
                        ]
                    return cls(**data)
            except Exception as e:
                logger.error(f"Config load error: {e}")
        return cls()

    def save(self):
        """Speichert die Konfiguration in die JSON-Datei."""
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.model_dump(), f, indent=4)

    def get_current_preload_size(self) -> int:
        """Gibt die aktuelle Preload-Größe basierend auf Zeitprofil zurück."""
        if not self.use_time_profiles:
            return self.preload_head_mb

        current_hour = datetime.now().hour
        for profile in self.time_profiles:
            if profile.start_hour <= current_hour < profile.end_hour:
                return profile.preload_head_mb

        return self.preload_head_mb


class PreloadHistoryEntry(BaseModel):
    """Ein Eintrag in der Preload-Historie."""
    timestamp: str
    preloaded: int
    skipped: int
    duration_seconds: int
    source: str = "manual"  # manual, scheduler, tautulli, plex
    files_processed: List[str] = []


# --- GLOBAL STATE (Thread-Safe) ---
class AppState:
    """Thread-sicherer Anwendungszustand mit Historie."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_running: bool = False
        self.last_run_stats: dict = {
            "preloaded": 0,
            "skipped": 0,
            "total_cached": 0,
            "duration": 0,
            "last_run": "Never"
        }
        self.current_action: str = "Idle"
        self.history: List[PreloadHistoryEntry] = self._load_history()

    @property
    def is_running(self) -> bool:
        """Thread-sicherer Getter für is_running."""
        with self._lock:
            return self._is_running

    @is_running.setter
    def is_running(self, value: bool):
        """Thread-sicherer Setter für is_running."""
        with self._lock:
            self._is_running = value

    def _load_history(self) -> List[PreloadHistoryEntry]:
        """Lädt die Historie aus der JSON-Datei."""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    return [PreloadHistoryEntry(**entry) for entry in data[-100:]]
            except Exception as e:
                logger.error(f"History load error: {e}")
        return []

    def add_history_entry(self, entry: PreloadHistoryEntry):
        """Fügt einen Eintrag zur Historie hinzu und speichert."""
        self.history.append(entry)
        # Nur die letzten 100 Einträge behalten
        self.history = self.history[-100:]
        self._save_history()

    def _save_history(self):
        """Speichert die Historie in die JSON-Datei."""
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, 'w') as f:
                json.dump([e.model_dump() for e in self.history], f, indent=2)
        except Exception as e:
            logger.error(f"History save error: {e}")


state = AppState()
config = Config.load()

# --- HELPER FUNCTIONS ---

def get_ram_usage() -> dict:
    """Gibt RAM-Informationen des Hosts zurück."""
    mem = psutil.virtual_memory()
    return {
        "total": f"{mem.total / (1024**3):.2f} GB",
        "available": f"{mem.available / (1024**3):.2f} GB",
        "percent": mem.percent
    }


def is_video_file(filename: str, extensions: List[str]) -> bool:
    """Prüft effizient ob eine Datei eine Video-Datei ist."""
    ext_tuple = tuple(f".{ext.lower()}" for ext in extensions)
    return filename.lower().endswith(ext_tuple)


def matches_exclude_pattern(filepath: str, patterns: List[str]) -> bool:
    """Prüft ob ein Pfad einem Exclude-Pattern entspricht."""
    for pattern in patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
    return False


def read_file_chunk(filepath: str, size_mb: int, offset_from_end: bool = False) -> float:
    """Liest einen Teil der Datei um sie in den System-Cache zu laden."""
    size_bytes = size_mb * 1024 * 1024
    try:
        with open(filepath, "rb") as f:
            if offset_from_end:
                f.seek(0, 2)
                file_size = f.tell()
                if file_size < size_bytes:
                    f.seek(0)
                else:
                    f.seek(-size_bytes, 2)

            start_t = time.perf_counter()
            f.read(size_bytes)
            end_t = time.perf_counter()
            return (end_t - start_t) * 1000
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return 0


def read_log_tail(filepath: str, num_lines: int = 20) -> str:
    """Liest effizient die letzten N Zeilen einer Log-Datei."""
    if not os.path.exists(filepath):
        return "No logs yet."

    try:
        with open(filepath, "rb") as f:
            f.seek(0, 2)
            file_size = f.tell()
            if file_size == 0:
                return "No logs yet."

            buffer_size = min(file_size, num_lines * 150)
            f.seek(max(0, file_size - buffer_size))
            lines = f.read().decode('utf-8', errors='replace').splitlines()
            return '\n'.join(lines[-num_lines:])
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return f"Error reading logs: {e}"


def check_file_cached(filepath: str, size_mb: int = 1) -> bool:
    """Prüft ob eine Datei bereits im Cache ist (schnelle Lesezeit)."""
    duration = read_file_chunk(filepath, size_mb)
    return duration < config.cache_threshold_ms


# --- TAUTULLI API CLIENT ---

async def fetch_tautulli_data() -> Dict[str, List[str]]:
    """
    Holt Daten von Tautulli: Meistgesehene Filme und nächste Episoden.

    Returns:
        Dict mit 'top_movies' und 'next_episodes' Pfadlisten.
    """
    result = {"top_movies": [], "next_episodes": []}

    if not config.tautulli_enabled or not config.tautulli_url or not config.tautulli_api_key:
        return result

    base_url = config.tautulli_url.rstrip('/')

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. Meistgesehene Filme (letzte 30 Tage)
            movies_resp = await client.get(
                f"{base_url}/api/v2",
                params={
                    "apikey": config.tautulli_api_key,
                    "cmd": "get_home_stats",
                    "stat_id": "top_movies",
                    "stats_count": config.tautulli_top_movies_count,
                    "time_range": 30
                }
            )

            if movies_resp.status_code == 200:
                data = movies_resp.json()
                if data.get("response", {}).get("result") == "success":
                    rows = data.get("response", {}).get("data", {}).get("rows", [])
                    for movie in rows:
                        if "file" in movie:
                            result["top_movies"].append(movie["file"])
                        elif "grandparent_title" in movie:
                            # Suche Datei über Metadaten
                            file_path = await _find_media_file(client, base_url, movie.get("rating_key"))
                            if file_path:
                                result["top_movies"].append(file_path)

            # 2. Kürzlich angesehene Serien - hole nächste ungesehene Folgen
            recently_watched_resp = await client.get(
                f"{base_url}/api/v2",
                params={
                    "apikey": config.tautulli_api_key,
                    "cmd": "get_history",
                    "media_type": "episode",
                    "length": 50
                }
            )

            if recently_watched_resp.status_code == 200:
                data = recently_watched_resp.json()
                if data.get("response", {}).get("result") == "success":
                    history = data.get("response", {}).get("data", {}).get("data", [])

                    # Sammle einzigartige Serien
                    seen_shows: Dict[str, dict] = {}
                    for entry in history:
                        show_key = entry.get("grandparent_rating_key")
                        if show_key and show_key not in seen_shows:
                            seen_shows[show_key] = {
                                "title": entry.get("grandparent_title"),
                                "last_season": entry.get("parent_media_index", 0),
                                "last_episode": entry.get("media_index", 0)
                            }

                    # Für jede Serie: Finde nächste Folgen
                    for show_key, show_info in list(seen_shows.items())[:config.tautulli_next_episodes_count]:
                        next_eps = await _find_next_episodes(
                            client, base_url, show_key,
                            show_info["last_season"],
                            show_info["last_episode"]
                        )
                        result["next_episodes"].extend(next_eps)

            logger.info(f"Tautulli: {len(result['top_movies'])} top movies, {len(result['next_episodes'])} next episodes")

        except Exception as e:
            logger.error(f"Tautulli API error: {e}")

    return result


async def _find_media_file(client: httpx.AsyncClient, base_url: str, rating_key: str) -> Optional[str]:
    """
    Findet den Dateipfad für ein Medium über rating_key.

    Konvertiert Plex-Pfade zu Container-Pfaden falls nötig.
    """
    try:
        resp = await client.get(
            f"{base_url}/api/v2",
            params={
                "apikey": config.tautulli_api_key,
                "cmd": "get_metadata",
                "rating_key": rating_key
            }
        )
        if resp.status_code == 200:
            data = resp.json()
            metadata = data.get("response", {}).get("data", {})

            file_path = None

            # Prüfe verschiedene Pfad-Felder
            for field in ["file", "file_path", "media_info"]:
                if field in metadata:
                    if field == "media_info" and isinstance(metadata[field], list):
                        for media in metadata[field]:
                            for part in media.get("parts", []):
                                if "file" in part:
                                    file_path = part["file"]
                                    break
                            if file_path:
                                break
                    else:
                        file_path = metadata[field]
                    if file_path:
                        break

            if file_path:
                original_path = file_path

                # 1. Versuche konfiguriertes Pfad-Mapping
                mapped_path = config.map_path(file_path)
                if mapped_path != file_path and os.path.exists(mapped_path):
                    logger.debug(f"Pfad gemappt (config): {original_path} -> {mapped_path}")
                    return mapped_path

                # 2. Prüfe ob der Original-Pfad existiert
                if os.path.exists(file_path):
                    return file_path

                # 3. Versuche automatisches Pfad-Mapping über video_paths
                for video_path in config.video_paths:
                    path_parts = file_path.replace('\\', '/').split('/')
                    for i in range(len(path_parts)):
                        test_path = os.path.join(video_path, *path_parts[i:])
                        if os.path.exists(test_path):
                            logger.debug(f"Pfad gemappt (auto): {original_path} -> {test_path}")
                            return test_path

                logger.warning(f"Pfad nicht gefunden: {file_path} (Tipp: Pfad-Mapping in Einstellungen konfigurieren)")

    except Exception as e:
        logger.debug(f"Could not find file for rating_key {rating_key}: {e}")
    return None


async def _find_next_episodes(
    client: httpx.AsyncClient,
    base_url: str,
    show_key: str,
    last_season: int,
    last_episode: int,
    max_episodes: int = 3
) -> List[str]:
    """
    Findet die nächsten ungesehenen Episoden einer Serie.

    Args:
        client: HTTP Client
        base_url: Tautulli Base URL
        show_key: Rating Key der Serie
        last_season: Aktuelle Staffelnummer
        last_episode: Aktuelle Episodennummer
        max_episodes: Maximale Anzahl zu findender Episoden

    Returns:
        Liste der Dateipfade für nächste Episoden
    """
    episodes = []

    logger.debug(f"Suche nächste Episoden: show_key={show_key}, S{last_season:02d}E{last_episode:02d}")

    try:
        # Hole alle Staffeln der Serie
        resp = await client.get(
            f"{base_url}/api/v2",
            params={
                "apikey": config.tautulli_api_key,
                "cmd": "get_children_metadata",
                "rating_key": show_key
            }
        )

        if resp.status_code != 200:
            logger.warning(f"Tautulli API Fehler: Status {resp.status_code}")
            return episodes

        data = resp.json()

        if data.get("response", {}).get("result") != "success":
            logger.warning(f"Tautulli API Fehler: {data.get('response', {}).get('message', 'Unknown')}")
            return episodes

        seasons = data.get("response", {}).get("data", {}).get("children_list", [])
        logger.debug(f"Gefundene Staffeln: {len(seasons)}")

        # Konvertiere last_season und last_episode zu int (falls String)
        last_season = int(last_season) if last_season else 0
        last_episode = int(last_episode) if last_episode else 0

        for season in seasons:
            # Konvertiere zu int (API kann Strings zurückgeben)
            season_num = int(season.get("media_index", 0) or 0)

            # Überspringe frühere Staffeln
            if season_num < last_season:
                continue

            # Hole Episoden dieser Staffel
            season_key = season.get("rating_key")
            season_resp = await client.get(
                f"{base_url}/api/v2",
                params={
                    "apikey": config.tautulli_api_key,
                    "cmd": "get_children_metadata",
                    "rating_key": season_key
                }
            )

            if season_resp.status_code != 200:
                continue

            ep_data = season_resp.json()
            eps = ep_data.get("response", {}).get("data", {}).get("children_list", [])
            logger.debug(f"Staffel {season_num}: {len(eps)} Episoden")

            for ep in eps:
                # Konvertiere zu int
                ep_num = int(ep.get("media_index", 0) or 0)

                # Nur Folgen nach der aktuell geschauten
                if season_num == last_season and ep_num <= last_episode:
                    continue

                # Finde Dateipfad
                file_path = await _find_media_file(client, base_url, ep.get("rating_key"))
                if file_path:
                    logger.debug(f"Gefunden: S{season_num:02d}E{ep_num:02d} -> {file_path}")
                    episodes.append(file_path)
                    if len(episodes) >= max_episodes:
                        return episodes

    except Exception as e:
        logger.warning(f"Fehler beim Finden nächster Episoden: {e}")

    return episodes


# --- LIVE ACTIVITY MONITORING ---

async def fetch_current_activity() -> List[Dict[str, Any]]:
    """
    Holt aktuell laufende Wiedergaben von Tautulli.

    Returns:
        Liste von aktiven Serien-Wiedergaben mit Show-Info.
    """
    sessions = []

    if not config.tautulli_enabled or not config.tautulli_url or not config.tautulli_api_key:
        return sessions

    base_url = config.tautulli_url.rstrip('/')

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{base_url}/api/v2",
                params={
                    "apikey": config.tautulli_api_key,
                    "cmd": "get_activity"
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("response", {}).get("result") == "success":
                    activity = data.get("response", {}).get("data", {})
                    for session in activity.get("sessions", []):
                        # Nur Serien-Episoden sind interessant
                        if session.get("media_type") == "episode":
                            sessions.append({
                                "show_key": session.get("grandparent_rating_key"),
                                "show_title": session.get("grandparent_title"),
                                "season": int(session.get("parent_media_index", 1)),
                                "episode": int(session.get("media_index", 1)),
                                "user": session.get("friendly_name", "Unknown")
                            })

                    if sessions:
                        logger.info(f"Live Activity: {len(sessions)} Serien-Streams aktiv")

        except Exception as e:
            logger.debug(f"Activity fetch error: {e}")

    return sessions


async def preload_next_episodes_for_session(session: Dict[str, Any]) -> int:
    """
    Lädt die nächsten Episoden einer laufenden Serie in den Cache.

    Args:
        session: Session-Info mit show_key, season, episode.

    Returns:
        Anzahl der geladenen Episoden.
    """
    if not config.tautulli_url or not config.tautulli_api_key:
        return 0

    base_url = config.tautulli_url.rstrip('/')
    loaded_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            next_eps = await _find_next_episodes(
                client,
                base_url,
                session["show_key"],
                session["season"],
                session["episode"]
            )

            # Limitiere auf konfigurierte Anzahl
            next_eps = next_eps[:config.live_episodes_to_preload]

            preload_size = config.get_current_preload_size()

            if not next_eps:
                logger.info(f"Live-Monitoring: Keine nächsten Episoden gefunden für '{session['show_title']}'")
            else:
                logger.info(f"Live-Monitoring: {len(next_eps)} Episoden gefunden für '{session['show_title']}'")

                for filepath in next_eps:
                    filename = os.path.basename(filepath)

                    if not os.path.exists(filepath):
                        logger.warning(f"Live-Monitoring: Datei nicht gefunden: {filepath}")
                        continue

                    # Prüfe ob schon gecached
                    duration = read_file_chunk(filepath, 1)  # Quick check
                    if duration < config.cache_threshold_ms:
                        logger.info(f"⚡ Live-Cache: {filename} (bereits im Cache)")
                        continue

                    # Preload - höchste Priorität!
                    logger.info(f"📦 Live-Preload: {filename} (User: {session['user']})")
                    read_file_chunk(filepath, preload_size)
                    read_file_chunk(filepath, config.preload_tail_mb, offset_from_end=True)
                    loaded_count += 1
                    logger.info(f"✅ Live-Preload fertig: {filename}")

        except Exception as e:
            logger.warning(f"Live-Monitoring Error: {e}")

    return loaded_count


async def live_monitoring_task():
    """
    Hintergrund-Task der regelmäßig aktive Streams prüft
    und nächste Episoden preloaded.
    """
    while True:
        try:
            if config.live_monitoring_enabled and config.tautulli_enabled:
                sessions = await fetch_current_activity()

                for session in sessions:
                    # Prüfe RAM vor jedem Preload
                    if psutil.virtual_memory().percent > config.ram_max_usage_percent:
                        logger.warning("Live-Monitoring: RAM-Limit erreicht, pausiere")
                        break

                    loaded = await preload_next_episodes_for_session(session)
                    if loaded > 0:
                        logger.info(
                            f"Live-Preload für '{session['show_title']}' "
                            f"S{session['season']:02d}E{session['episode']:02d}: "
                            f"{loaded} Episoden gecached"
                        )

        except Exception as e:
            logger.debug(f"Live monitoring error: {e}")

        # Warte bis zum nächsten Check
        await asyncio.sleep(config.live_check_interval_seconds)


# --- PLEX API CLIENT ---

async def fetch_plex_on_deck() -> List[str]:
    """
    Holt 'On Deck' (Continue Watching) Inhalte von Plex.

    Returns:
        Liste von Dateipfaden.
    """
    files = []

    if not config.plex_enabled or not config.plex_url or not config.plex_token:
        return files

    base_url = config.plex_url.rstrip('/')
    headers = {
        "X-Plex-Token": config.plex_token,
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # On Deck Endpoint
            resp = await client.get(
                f"{base_url}/library/onDeck",
                headers=headers
            )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("MediaContainer", {}).get("Metadata", [])

                for item in items:
                    # Hole Mediendaten
                    for media in item.get("Media", []):
                        for part in media.get("Part", []):
                            if "file" in part:
                                files.append(part["file"])

                logger.info(f"Plex On Deck: {len(files)} files found")

        except Exception as e:
            logger.error(f"Plex API error: {e}")

    return files


# --- PRELOAD LOGIC ---

def discover_files() -> List[tuple]:
    """
    Entdeckt Video-Dateien basierend auf Konfiguration.

    Returns:
        Liste von (priority, mtime, filepath) Tupeln.
    """
    global state
    files = []
    min_size_bytes = config.min_size_mb * 1024 * 1024
    scanned_count = 0

    def scan_path(path: str, priority: int = 0):
        nonlocal scanned_count
        if not os.path.exists(path):
            logger.warning(f"Path not found: {path}")
            return

        for root, _, filenames in os.walk(path):
            for filename in filenames:
                scanned_count += 1

                # Update Status alle 100 Dateien
                if scanned_count % 100 == 0:
                    state.current_action = f"Scanning... ({scanned_count} files)"

                if not is_video_file(filename, config.video_extensions):
                    continue

                full_path = os.path.join(root, filename)

                # Exclude-Pattern prüfen
                if matches_exclude_pattern(full_path, config.exclude_patterns):
                    continue

                try:
                    fsize = os.path.getsize(full_path)
                    if fsize >= min_size_bytes:
                        mtime = os.path.getmtime(full_path)
                        files.append((priority, mtime, full_path))
                except OSError:
                    pass

    # Priority-Pfade zuerst (höhere Priorität = niedrigere Zahl)
    for i, path in enumerate(config.priority_paths):
        scan_path(path, priority=i)

    # Normale Pfade
    for path in config.video_paths:
        scan_path(path, priority=100)

    logger.info(f"Filesystem scan: {len(files)} video files found ({scanned_count} total scanned)")
    return files


async def run_preload(source: str = "manual"):
    """
    Führt den Preload-Prozess aus.

    Args:
        source: Quelle des Aufrufs (manual, scheduler, webhook).
    """
    global state, config

    if state.is_running:
        logger.warning("Preload already running, skipping.")
        return

    state.is_running = True
    state.current_action = "Starting Preload..."
    stats = {"preloaded": 0, "skipped": 0, "start_time": time.time(), "files": []}

    logger.info(f"Starting Preload Run (source: {source})")

    try:
        # RAM Check
        mem = psutil.virtual_memory()
        if mem.percent > config.ram_max_usage_percent:
            logger.warning(f"RAM usage high ({mem.percent}%), aborting.")
            state.current_action = f"Aborted: RAM High ({mem.percent}%)"
            return

        # Sammle Dateien aus verschiedenen Quellen
        files_to_check: List[str] = []

        # 1. Tautulli-Daten (höchste Priorität)
        if config.tautulli_enabled:
            state.current_action = "Fetching Tautulli data..."
            tautulli_data = await fetch_tautulli_data()
            files_to_check.extend(tautulli_data["top_movies"])
            files_to_check.extend(tautulli_data["next_episodes"])

        # 2. Plex On Deck
        if config.plex_enabled:
            state.current_action = "Fetching Plex On Deck..."
            plex_files = await fetch_plex_on_deck()
            files_to_check.extend(plex_files)

        # 3. Filesystem-Scan
        state.current_action = "Scanning filesystem..."
        fs_files = discover_files()
        # Sortieren: erst nach Priorität, dann nach mtime (neueste zuerst)
        fs_files.sort(key=lambda x: (x[0], -x[1]))
        files_to_check.extend([f[2] for f in fs_files])

        # Duplikate entfernen (behalte Reihenfolge)
        seen = set()
        unique_files = []
        for f in files_to_check:
            if f not in seen and os.path.exists(f):
                seen.add(f)
                unique_files.append(f)

        # Limitieren
        unique_files = unique_files[:config.max_files_per_run]

        state.current_action = f"Processing {len(unique_files)} candidates..."
        logger.info(f"Found {len(unique_files)} files to check")

        # Zeitbasierte Preload-Größe
        preload_size = config.get_current_preload_size()

        for filepath in unique_files:
            filename = os.path.basename(filepath)
            state.current_action = f"Checking: {filename}"

            # Preload Head
            duration = read_file_chunk(filepath, preload_size)

            if duration < config.cache_threshold_ms:
                stats["skipped"] += 1
                logger.info(f"Cached: {filename} ({duration:.2f}ms)")
            else:
                stats["preloaded"] += 1
                stats["files"].append(filename)
                logger.info(f"Loaded: {filename} ({duration:.2f}ms)")
                # Preload Tail
                read_file_chunk(filepath, config.preload_tail_mb, offset_from_end=True)

            # RAM-Check während des Laufs
            if psutil.virtual_memory().percent > config.ram_max_usage_percent:
                logger.warning("RAM limit reached during preload, stopping.")
                break

        # Stats aktualisieren
        duration_secs = int(time.time() - stats["start_time"])
        total_cached = stats["preloaded"] + stats["skipped"]
        state.last_run_stats = {
            "preloaded": stats["preloaded"],
            "skipped": stats["skipped"],
            "total_cached": total_cached,
            "duration": duration_secs,
            "last_run": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Historie speichern
        history_entry = PreloadHistoryEntry(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            preloaded=stats["preloaded"],
            skipped=stats["skipped"],
            duration_seconds=duration_secs,
            source=source,
            files_processed=stats["files"][:20]  # Max 20 Dateien speichern
        )
        state.add_history_entry(history_entry)

        logger.info(f"Preload finished: {stats['preloaded']} loaded, {stats['skipped']} cached, {duration_secs}s")

    except Exception as e:
        logger.error(f"Preload task error: {e}")
        state.current_action = f"Error: {e}"
    finally:
        state.current_action = "Idle"
        state.is_running = False


def preload_task():
    """Synchroner Wrapper für run_preload (für Background-Tasks)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_preload("manual"))
    finally:
        loop.close()


def scheduled_preload_task():
    """Task für den Scheduler."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_preload("scheduler"))
    finally:
        loop.close()

# --- SCHEDULER MANAGEMENT ---

def setup_scheduler():
    """Richtet den Scheduler basierend auf der Konfiguration ein."""
    global scheduler

    # Alle bestehenden Jobs entfernen
    scheduler.remove_all_jobs()

    if config.scheduler_enabled and config.cron_schedule:
        try:
            trigger = CronTrigger.from_crontab(config.cron_schedule)
            scheduler.add_job(
                scheduled_preload_task,
                trigger=trigger,
                id="preload_job",
                replace_existing=True
            )
            logger.info(f"Scheduler enabled: {config.cron_schedule}")
        except Exception as e:
            logger.error(f"Invalid cron schedule: {e}")


# --- APP LIFECYCLE ---

# Globaler Task-Handle für Live-Monitoring
_live_monitoring_task_handle: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle-Manager für FastAPI App."""
    global _live_monitoring_task_handle

    # Startup
    logger.info("Video Preloader starting...")
    setup_scheduler()
    if not scheduler.running:
        scheduler.start()
    logger.info("Scheduler started")

    # Live-Monitoring Task starten
    if config.live_monitoring_enabled:
        _live_monitoring_task_handle = asyncio.create_task(live_monitoring_task())
        logger.info(f"Live-Monitoring gestartet (Intervall: {config.live_check_interval_seconds}s)")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Live-Monitoring stoppen
    if _live_monitoring_task_handle and not _live_monitoring_task_handle.done():
        _live_monitoring_task_handle.cancel()
        try:
            await _live_monitoring_task_handle
        except asyncio.CancelledError:
            pass
        logger.info("Live-Monitoring gestoppt")

    scheduler.shutdown()


# --- APP INITIALIZATION ---
app = FastAPI(title="Unraid Video Preloader", lifespan=lifespan)


# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Rendert die Hauptseite mit Konfiguration und Status."""
    lang = config.language if config.language in TRANSLATIONS else "en"
    t = TRANSLATIONS[lang]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": config,
            "state": state,
            "version": VERSION,
            "t": t,
            "lang": lang
        }
    )


@app.get("/api/stats")
async def get_stats():
    """Gibt aktuelle System-Statistiken als JSON zurück."""
    mem = get_ram_usage()
    return JSONResponse({
        "ram_percent": mem['percent'],
        "ram_text": f"{mem['available']} available",
        "status": state.current_action,
        "is_running": state.is_running,
        "last_run": state.last_run_stats,
        "scheduler_enabled": config.scheduler_enabled,
        "next_run": _get_next_run_time()
    })


def _get_next_run_time() -> Optional[str]:
    """Gibt die nächste geplante Ausführungszeit zurück."""
    try:
        job = scheduler.get_job("preload_job")
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None


@app.get("/api/logs")
async def get_logs():
    """
    Gibt die letzten 20 Log-Zeilen formatiert als HTML zurück.

    Formatierung:
    - Zeitstempel in grau
    - INFO in blau, WARNING in gelb, ERROR in rot
    - Dateinamen hervorgehoben
    - Zeiten in grün
    """
    raw_logs = read_log_tail(LOG_FILE, num_lines=20)
    if not raw_logs:
        return {"logs": "", "html": "<div class='text-gray-500'>Keine Logs vorhanden...</div>"}

    import re
    formatted_lines = []

    for line in raw_logs.split('\n'):
        if not line.strip():
            continue

        # Parse: 2025-12-02 19:06:45 - INFO - Message
        match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (\w+) - (.*)$', line)

        if match:
            timestamp, level, message = match.groups()

            # Level-Farben
            level_colors = {
                'INFO': 'text-blue-400',
                'WARNING': 'text-yellow-400',
                'ERROR': 'text-red-400',
                'DEBUG': 'text-gray-500'
            }
            level_class = level_colors.get(level, 'text-gray-400')

            # Icons für verschiedene Nachrichten
            icon = ""
            msg_class = "text-gray-300"

            if "Loaded:" in message:
                icon = "📦 "
                # Extrahiere Dateiname und Zeit
                file_match = re.match(r'Loaded: (.+) \((\d+\.\d+)ms\)', message)
                if file_match:
                    filename, duration = file_match.groups()
                    message = f'<span class="text-white">{filename}</span> <span class="text-emerald-400">({duration}ms)</span>'
                    icon = "📦 "
            elif "Skipped:" in message or "cached" in message.lower():
                icon = "⚡ "
                msg_class = "text-emerald-400"
            elif "Preload finished" in message:
                icon = "✅ "
                msg_class = "text-emerald-400 font-semibold"
            elif "Starting Preload" in message:
                icon = "🚀 "
                msg_class = "text-blue-300 font-semibold"
            elif "Scheduler" in message:
                icon = "⏰ "
            elif "Tautulli" in message:
                icon = "📊 "
            elif "Plex" in message:
                icon = "🎬 "
            elif "Live" in message:
                icon = "📡 "
                msg_class = "text-purple-400"
            elif "Error" in message or "error" in message:
                icon = "❌ "
                msg_class = "text-red-400"
            elif "Warning" in message or "warning" in message:
                icon = "⚠️ "
                msg_class = "text-yellow-400"
            elif "starting" in message.lower():
                icon = "🔄 "
            elif "Shutting" in message:
                icon = "🛑 "
                msg_class = "text-orange-400"

            # Formatierte Zeile
            formatted = (
                f'<div class="flex gap-2 py-0.5 border-b border-slate-800/50">'
                f'<span class="text-gray-500 shrink-0">{timestamp.split(" ")[1]}</span>'
                f'<span class="{level_class} shrink-0 w-12">{level}</span>'
                f'<span class="{msg_class}">{icon}{message}</span>'
                f'</div>'
            )
            formatted_lines.append(formatted)
        else:
            # Unformatierte Zeile
            formatted_lines.append(f'<div class="text-gray-400 py-0.5">{line}</div>')

    html_output = ''.join(formatted_lines)
    return {"logs": raw_logs, "html": html_output}


@app.get("/api/history")
async def get_history():
    """Gibt die Preload-Historie zurück."""
    return JSONResponse({
        "history": [entry.model_dump() for entry in state.history[-20:]]
    })


@app.post("/start")
async def start_preload(background_tasks: BackgroundTasks):
    """Startet den Preload-Task als Background-Prozess."""
    if not state.is_running:
        background_tasks.add_task(preload_task)
        return {"status": "Started"}
    return {"status": "Already running"}


@app.post("/api/preload")
async def preload_single_file(
    path: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    """
    Lädt eine einzelne Datei in den Cache.

    Args:
        path: Pfad zur Video-Datei.
    """
    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    if not is_video_file(path, config.video_extensions):
        return JSONResponse({"error": "Not a video file"}, status_code=400)

    preload_size = config.get_current_preload_size()
    duration = read_file_chunk(path, preload_size)
    read_file_chunk(path, config.preload_tail_mb, offset_from_end=True)

    cached = duration < config.cache_threshold_ms

    return JSONResponse({
        "path": path,
        "duration_ms": round(duration, 2),
        "was_cached": cached,
        "status": "already_cached" if cached else "loaded"
    })


@app.get("/api/cache-status")
async def check_cache_status(path: str = Query(...)):
    """
    Prüft ob eine Datei im Cache ist.

    Args:
        path: Pfad zur Video-Datei.
    """
    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    duration = read_file_chunk(path, 1)  # 1MB Probe
    cached = duration < config.cache_threshold_ms

    return JSONResponse({
        "path": path,
        "cached": cached,
        "read_time_ms": round(duration, 2)
    })


@app.post("/api/webhook/plex")
async def plex_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Empfängt Webhooks von Plex und triggert Preload bei Bedarf.

    Reagiert auf 'media.play' Events.
    """
    try:
        # Plex sendet multipart/form-data
        form = await request.form()
        payload_str = form.get("payload", "{}")
        payload = json.loads(payload_str)

        event = payload.get("event", "")

        if event == "media.play":
            # Jemand schaut etwas - preloade verwandte Inhalte
            logger.info(f"Plex webhook: {event}")
            if not state.is_running:
                background_tasks.add_task(preload_task)
                return {"status": "Preload triggered"}

        return {"status": "OK", "event": event}

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/save_config_all")
async def save_config_all(
    # Pfade
    video_paths: str = Form(...),
    priority_paths: str = Form(""),
    exclude_patterns: str = Form(""),
    # Preload-Einstellungen
    preload_head_mb: int = Form(60),
    preload_tail_mb: int = Form(1),
    min_size_mb: int = Form(500),
    max_files_per_run: int = Form(50),
    cache_threshold_ms: int = Form(150),
    ram_max_usage_percent: int = Form(80),
    video_extensions: str = Form("mkv, mp4, avi, mov, wmv, m4v"),
    # Scheduler
    scheduler_enabled: bool = Form(False),
    cron_schedule: str = Form("0 */2 * * *"),
    use_time_profiles: bool = Form(False),
    profile_day_mb: int = Form(30),
    profile_evening_mb: int = Form(100),
    profile_night_mb: int = Form(60),
    # Tautulli
    tautulli_enabled: bool = Form(False),
    tautulli_url: str = Form(""),
    tautulli_api_key: str = Form(""),
    tautulli_top_movies_count: int = Form(10),
    tautulli_next_episodes_count: int = Form(5),
    # Live-Monitoring
    live_monitoring_enabled: bool = Form(False),
    live_check_interval_seconds: int = Form(60),
    live_episodes_to_preload: int = Form(3),
    path_mappings: str = Form(""),
    # Plex
    plex_enabled: bool = Form(False),
    plex_url: str = Form(""),
    plex_token: str = Form(""),
    # UI
    language: str = Form("de")
):
    """Speichert alle Konfigurationseinstellungen aus dem Webformular."""

    # Pfade
    config.video_paths = [p.strip() for p in video_paths.split(',') if p.strip()]
    config.priority_paths = [p.strip() for p in priority_paths.split(',') if p.strip()]
    config.exclude_patterns = [p.strip() for p in exclude_patterns.split(',') if p.strip()]

    # Preload-Einstellungen
    config.preload_head_mb = preload_head_mb
    config.preload_tail_mb = preload_tail_mb
    config.min_size_mb = min_size_mb
    config.max_files_per_run = max_files_per_run
    config.cache_threshold_ms = cache_threshold_ms
    config.ram_max_usage_percent = ram_max_usage_percent
    config.video_extensions = [ext.strip().lower() for ext in video_extensions.split(',') if ext.strip()]

    # Scheduler
    old_scheduler_state = config.scheduler_enabled
    config.scheduler_enabled = scheduler_enabled
    config.cron_schedule = cron_schedule
    config.use_time_profiles = use_time_profiles

    # Zeit-Profile aktualisieren
    config.time_profiles = [
        ScheduleProfile(start_hour=6, end_hour=18, preload_head_mb=profile_day_mb),
        ScheduleProfile(start_hour=18, end_hour=23, preload_head_mb=profile_evening_mb),
        ScheduleProfile(start_hour=23, end_hour=6, preload_head_mb=profile_night_mb),
    ]

    # Tautulli
    config.tautulli_enabled = tautulli_enabled
    config.tautulli_url = tautulli_url
    config.tautulli_api_key = tautulli_api_key
    config.tautulli_top_movies_count = tautulli_top_movies_count
    config.tautulli_next_episodes_count = tautulli_next_episodes_count

    # Live-Monitoring
    old_live_monitoring = config.live_monitoring_enabled
    config.live_monitoring_enabled = live_monitoring_enabled
    config.live_check_interval_seconds = live_check_interval_seconds
    config.live_episodes_to_preload = live_episodes_to_preload
    # Pfad-Mappings (Zeilen-separiert)
    config.path_mappings = [p.strip() for p in path_mappings.split('\n') if p.strip() and ':' in p]

    # Plex
    config.plex_enabled = plex_enabled
    config.plex_url = plex_url
    config.plex_token = plex_token

    # UI
    config.language = language

    config.save()

    # Scheduler neu einrichten wenn sich was geändert hat
    if old_scheduler_state != scheduler_enabled or scheduler_enabled:
        setup_scheduler()

    # Live-Monitoring Task neu starten wenn nötig
    global _live_monitoring_task_handle
    if old_live_monitoring != live_monitoring_enabled:
        if _live_monitoring_task_handle and not _live_monitoring_task_handle.done():
            _live_monitoring_task_handle.cancel()
        if live_monitoring_enabled and tautulli_enabled:
            _live_monitoring_task_handle = asyncio.create_task(live_monitoring_task())
            logger.info(f"Live-Monitoring gestartet (Intervall: {live_check_interval_seconds}s)")
        else:
            logger.info("Live-Monitoring gestoppt")

    logger.info(f"All config saved: {len(config.video_paths)} paths, scheduler={'on' if scheduler_enabled else 'off'}, live-monitoring={'on' if live_monitoring_enabled else 'off'}")
    msg = "✓ Settings saved!" if language == "en" else "✓ Einstellungen gespeichert!"
    return HTMLResponse(f'<span class="text-green-500">{msg}</span>')


@app.get("/api/test-tautulli")
async def test_tautulli():
    """Testet die Tautulli-Verbindung."""
    if not config.tautulli_url or not config.tautulli_api_key:
        return JSONResponse({"status": "error", "message": "Tautulli not configured"})

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{config.tautulli_url.rstrip('/')}/api/v2",
                params={
                    "apikey": config.tautulli_api_key,
                    "cmd": "get_server_info"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("response", {}).get("result") == "success":
                    return JSONResponse({"status": "success", "message": "Connected to Tautulli!"})
        return JSONResponse({"status": "error", "message": "Invalid response from Tautulli"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/test-plex")
async def test_plex():
    """Testet die Plex-Verbindung."""
    if not config.plex_url or not config.plex_token:
        return JSONResponse({"status": "error", "message": "Plex not configured"})

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{config.plex_url.rstrip('/')}/",
                headers={
                    "X-Plex-Token": config.plex_token,
                    "Accept": "application/json"
                }
            )
            if resp.status_code == 200:
                return JSONResponse({"status": "success", "message": "Connected to Plex!"})
        return JSONResponse({"status": "error", "message": f"HTTP {resp.status_code}"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/test-live-monitoring")
async def test_live_monitoring():
    """
    Testet das Live-Monitoring und zeigt aktive Streams.

    Gibt detaillierte Infos zurück für Debugging.
    """
    if not config.tautulli_enabled:
        return JSONResponse({
            "status": "error",
            "message": "Tautulli nicht aktiviert"
        })

    if not config.live_monitoring_enabled:
        return JSONResponse({
            "status": "warning",
            "message": "Live-Monitoring ist deaktiviert"
        })

    try:
        # Hole aktive Sessions
        sessions = await fetch_current_activity()

        if not sessions:
            return JSONResponse({
                "status": "info",
                "message": "Keine aktiven Serien-Streams",
                "sessions": []
            })

        # Für jede Session: Finde nächste Episoden
        results = []
        for session in sessions:
            base_url = config.tautulli_url.rstrip('/')
            async with httpx.AsyncClient(timeout=30.0) as client:
                next_eps = await _find_next_episodes(
                    client,
                    base_url,
                    session["show_key"],
                    session["season"],
                    session["episode"],
                    max_episodes=config.live_episodes_to_preload
                )

            results.append({
                "show": session["show_title"],
                "current": f"S{session['season']:02d}E{session['episode']:02d}",
                "user": session["user"],
                "next_episodes_found": len(next_eps),
                "next_episodes": [os.path.basename(p) for p in next_eps],
                "paths_exist": [os.path.exists(p) for p in next_eps]
            })

        return JSONResponse({
            "status": "success",
            "message": f"{len(sessions)} aktive Serien-Streams gefunden",
            "sessions": results
        })

    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })