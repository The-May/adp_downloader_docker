import subprocess
import sys
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

STATUS_FILE = "status.json"
STATUS_PORT = 8765


def now():
    return datetime.now().isoformat(timespec="seconds")


def load_status():
    path = Path(STATUS_FILE)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_status(data):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def update_status(script, state):
    data = load_status()
    data[script] = {
        "last_run": now(),
        "status": state,
    }
    save_status(data)


def run_step(script):
    print(f"--- Running {script} ---")
    result = subprocess.run([sys.executable, script])
    if result.returncode == 0:
        update_status(script, "success")
        return True
    else:
        update_status(script, "failed")
        return False


# smb_copy.py manages its own detailed status entry, so we only check its return code here
def run_copy_step():
    print("--- Running smb_copy.py ---")
    result = subprocess.run([sys.executable, "smb_copy.py"])
    # copy.py writes its own status.json entry — return code 0 means success or nothing_to_copy
    return result.returncode == 0


_run_lock = threading.Lock()


def run_pipeline():
    if not _run_lock.acquire(blocking=False):
        print("Pipeline already running, skipping.")
        return False

    try:
        update_status("handler", "running")

        if not run_step("login.py"):
            update_status("handler", "failed — login step")
            return False

        if not run_step("downloader.py"):
            update_status("handler", "failed — downloader step")
            return False

        if not run_copy_step():
            update_status("handler", "failed — smb_copy step")
            return False

        update_status("handler", "success")
        return True
    finally:
        _run_lock.release()


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            all_status = load_status()
            handler_status = all_status.get("handler", {})
            copy_status = all_status.get("smb_copy.py", {})

            body = json.dumps({
                "alive": True,
                "running": _run_lock.locked(),
                "time": now(),
                "pipeline": {
                    "last_run": handler_status.get("last_run"),
                    "status": handler_status.get("status"),
                },
                "copy": {
                    "last_copy": copy_status.get("last_copy"),
                    "status": copy_status.get("status"),       # success | failed | nothing_to_copy
                    "last_files": copy_status.get("last_files", []),
                    "error": copy_status.get("error"),         # only present on failure
                },
            }, indent=2).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/start":
            if _run_lock.locked():
                body = json.dumps({"started": False, "reason": "already running"}).encode("utf-8")
                self.send_response(409)
            else:
                threading.Thread(target=run_pipeline, daemon=True).start()
                body = json.dumps({"started": True}).encode("utf-8")
                self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_status_server():
    server = HTTPServer(("0.0.0.0", STATUS_PORT), StatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Status server running at http://localhost:{STATUS_PORT}/health")
    return server


def main():
    run_on_start = "--run" in sys.argv

    server = start_status_server()

    if run_on_start:
        print("--run flag detected, starting pipeline immediately.")
        threading.Thread(target=run_pipeline, daemon=True).start()

    print("Waiting for requests. Hit /start to trigger a run, /health to check heartbeat.")
    server.serve_forever()


if __name__ == "__main__":
    main()