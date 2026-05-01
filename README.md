# ADP Downloader (Docker Edition)

This project builds on the original [adp_downloader](https://github.com/nicksinger/adp_downloader) by nicksinger and wraps it with additional scripts for automated headless login, SMB file copy, and a simple HTTP status API — all packaged as a Docker container.

## What's new compared to the original

| Script | Description |
|---|---|
| `login.py` | Headless Chromium login via Playwright — extracts the `EMEASMSESSION` cookie automatically and saves it to `config.ini` |
| `downloader.py` | Unchanged from the original |
| `smb_copy.py` | Copies downloaded PDFs to an SMB share (e.g. a Paperless-ngx consume folder) |
| `handler.py` | Orchestrates the full pipeline and exposes a small HTTP API for triggering runs and checking status |

---

## Requirements

- Docker
- Docker Compose

---

## Installation

```bash
git clone https://github.com/The-May/adp_downloader_docker.git
cd adp_downloader_docker
```

---

## Configuration

Create a `config.ini` in the project directory:

```ini
[credentials]
username = changeme
password = changeme
cookie = thiswillautomaticallybechanged

[smb]
username = smbuser1
password = smbpassword
server   = 192.168.1.2
share    = path\to\folder\consume
```

> The `cookie` value is automatically updated by `login.py` after each successful login — you do not need to set it manually.

`status.json` and `download_history.db` are created automatically on first run.

---

## Running

```bash
# First time or after code changes
docker compose up -d --build

# After only editing config.ini
docker compose restart
```

---

## HTTP API

The container exposes a small API on port `8765`:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Heartbeat — returns pipeline and copy status |
| `/start` | GET | Triggers a full run (login → download → SMB copy) |

### Example `/health` response

```json
{
  "alive": true,
  "running": false,
  "time": "2026-05-01T10:11:54",
  "pipeline": {
    "last_run": "2026-05-01T10:11:53",
    "status": "success"
  },
  "copy": {
    "last_copy": "2026-05-01T10:11:54",
    "status": "success",
    "last_files": [
      "20260401_1000100_01009680_VERD_Verdienstabrechnung_20260410.pdf"
    ],
    "error": null
  }
}
```

Copy statuses: `success`, `nothing_to_copy`, `failed`.

---

## Automating with cron

To trigger a run automatically, e.g. on the 1st of every month at 8am with simple cron or just visit the webserver on your browser with http://ip.of.your.server:8765/start

```bash
crontab -e
```

```
0 8 1 * * curl -s http://localhost:8765/start
```

---

## License

MIT — see LICENSE file for details.

Original project by [nicksinger](https://github.com/nicksinger/adp_downloader).
