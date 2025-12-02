<p align="center">
  <img src="https://raw.githubusercontent.com/hoktaar/unraid-video-preloader/main/icon.png" alt="Video Preloader Logo" width="128" height="128">
</p>

<h1 align="center">🎬 Unraid Video Preloader</h1>

<p align="center">
  <a href="https://hub.docker.com/r/derbarnimer/unraid-video-preloader"><img src="https://img.shields.io/docker/v/derbarnimer/unraid-video-preloader?label=Docker%20Hub&logo=docker" alt="Docker Image"></a>
  <a href="https://hub.docker.com/r/derbarnimer/unraid-video-preloader"><img src="https://img.shields.io/docker/pulls/derbarnimer/unraid-video-preloader?logo=docker" alt="Docker Pulls"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <b>Smart video caching for Plex & Jellyfin</b> | <b>Intelligentes Video-Caching für Plex & Jellyfin</b>
</p>

---

<details>
<summary>🇬🇧 <b>English</b></summary>

## What is this?

Unraid Video Preloader is a Docker application that intelligently preloads video files into RAM cache. This eliminates buffering when starting videos on Plex, Jellyfin, or other media servers.

### ✨ Features

- **Smart Preloading** - Loads beginning and end of video files into cache
- **Tautulli Integration** - Preloads most-watched movies and next episodes of currently watching series
- **Plex Integration** - Preloads "On Deck" / Continue Watching content
- **Auto-Scheduler** - Cron-based automatic preloading
- **Time Profiles** - Different preload sizes for day/evening/night
- **Web Interface** - Beautiful UI for configuration and monitoring
- **Plex Webhooks** - React to play events in real-time
- **RAM Protection** - Automatically stops when RAM usage is high

### 🚀 Quick Start

```yaml
# docker-compose.yml
services:
  video-preloader:
    image: derbarnimer/unraid-video-preloader:latest
    container_name: video-preloader
    restart: unless-stopped
    cap_add:
      - SYS_PTRACE
    ports:
      - "8080:8000"
    volumes:
      - ./config:/config
      - /mnt/user:/data:ro  # Your media library (read-only)
    environment:
      - TZ=Europe/Berlin
```

```bash
docker-compose up -d
```

Then open **http://YOUR_IP:8080** in your browser.

### ⚙️ Configuration

All settings are available in the web interface:

| Setting | Description |
|---------|-------------|
| **Video Paths** | Directories to scan (e.g., `/data/movies, /data/tv`) |
| **Priority Paths** | Loaded first (e.g., `/data/tv/Currently Watching`) |
| **Exclude Patterns** | Skip files matching pattern (e.g., `*/Samples/*`) |
| **Preload Size** | MB to load from start/end of files |
| **Max RAM Usage** | Stop preloading above this percentage |
| **Scheduler** | Cron expression for automatic runs |
| **Tautulli** | URL and API key for integration |
| **Plex** | URL and token for On Deck feature |

### 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Current status and RAM usage |
| `/api/logs` | GET | Last 20 log lines |
| `/api/history` | GET | Preload run history |
| `/api/preload` | POST | Preload a single file |
| `/api/cache-status` | GET | Check if file is cached |
| `/api/webhook/plex` | POST | Receive Plex webhooks |
| `/api/test-tautulli` | GET | Test Tautulli connection |
| `/api/test-plex` | GET | Test Plex connection |

### 📡 Plex Webhook Setup

1. Go to Plex → Settings → Webhooks
2. Add: `http://YOUR_PRELOADER_IP:8080/api/webhook/plex`
3. The preloader will now react to play events

</details>

---

<details open>
<summary>🇩🇪 <b>Deutsch</b></summary>

## Was ist das?

Unraid Video Preloader ist eine Docker-Anwendung, die Video-Dateien intelligent in den RAM-Cache lädt. Das eliminiert Buffering beim Starten von Videos auf Plex, Jellyfin oder anderen Media-Servern.

### ✨ Features

- **Intelligentes Preloading** - Lädt Anfang und Ende von Video-Dateien in den Cache
- **Tautulli-Integration** - Preloadet meistgesehene Filme und nächste Folgen aktueller Serien
- **Plex-Integration** - Preloadet "On Deck" / Weiterschauen-Inhalte
- **Auto-Scheduler** - Cron-basiertes automatisches Preloading
- **Zeit-Profile** - Unterschiedliche Preload-Größen für Tag/Abend/Nacht
- **Web-Interface** - Schöne UI für Konfiguration und Monitoring
- **Plex Webhooks** - Reagiert in Echtzeit auf Wiedergabe-Events
- **RAM-Schutz** - Stoppt automatisch bei hoher RAM-Auslastung

### 🚀 Schnellstart

```yaml
# docker-compose.yml
services:
  video-preloader:
    image: derbarnimer/unraid-video-preloader:latest
    container_name: video-preloader
    restart: unless-stopped
    cap_add:
      - SYS_PTRACE
    ports:
      - "8080:8000"
    volumes:
      - ./config:/config
      - /mnt/user:/data:ro  # Deine Medienbibliothek (nur lesen)
    environment:
      - TZ=Europe/Berlin
```

```bash
docker-compose up -d
```

Dann öffne **http://DEINE_IP:8080** im Browser.

### ⚙️ Konfiguration

Alle Einstellungen sind im Web-Interface verfügbar:

| Einstellung | Beschreibung |
|-------------|--------------|
| **Video-Pfade** | Verzeichnisse zum Scannen (z.B. `/data/movies, /data/tv`) |
| **Prioritäts-Pfade** | Werden zuerst geladen (z.B. `/data/tv/Aktuell`) |
| **Exclude-Patterns** | Dateien überspringen (z.B. `*/Samples/*`) |
| **Preload-Größe** | MB vom Anfang/Ende der Dateien laden |
| **Max RAM-Nutzung** | Preloading stoppen über diesem Prozentsatz |
| **Scheduler** | Cron-Ausdruck für automatische Durchläufe |
| **Tautulli** | URL und API-Key für Integration |
| **Plex** | URL und Token für On Deck Feature |

### 🔌 API-Endpunkte

| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/stats` | GET | Aktueller Status und RAM-Nutzung |
| `/api/logs` | GET | Letzte 20 Log-Zeilen |
| `/api/history` | GET | Preload-Verlauf |
| `/api/preload` | POST | Einzelne Datei preloaden |
| `/api/cache-status` | GET | Prüfen ob Datei gecacht ist |
| `/api/webhook/plex` | POST | Plex-Webhooks empfangen |
| `/api/test-tautulli` | GET | Tautulli-Verbindung testen |
| `/api/test-plex` | GET | Plex-Verbindung testen |

### 📡 Plex Webhook einrichten

1. Gehe zu Plex → Einstellungen → Webhooks
2. Hinzufügen: `http://PRELOADER_IP:8080/api/webhook/plex`
3. Der Preloader reagiert nun auf Wiedergabe-Events

</details>

---

## 📸 Screenshots

<p align="center">
  <i>Screenshots coming soon / Screenshots folgen</i>
</p>

---

## 🛠️ Development

```bash
# Clone
git clone https://github.com/hoktaar/unraid-video-preloader.git
cd unraid-video-preloader

# Run locally
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## 📄 License / Lizenz

MIT License - see [LICENSE](LICENSE)