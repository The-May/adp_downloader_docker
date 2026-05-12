#!/usr/bin/env python3
import configparser
import json
import sys
from datetime import datetime
from pathlib import Path

import smbclient

STATUS_FILE = "status.json"
DOWNLOADS_DIR = Path("downloads")


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


def update_copy_status(status, files=None, error=None):
    data = load_status()
    entry = {
        "last_copy": now(),
        "status": status,           # "success" | "failed" | "nothing_to_copy"
        "last_files": files or [],
    }
    if error:
        entry["error"] = error
    data["smb_copy.py"] = entry
    save_status(data)


def load_smb_config():
    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")
    section = config["smb"]
    return (
        section["username"],
        section["password"],
        section["server"],
        section["share"],
    )


def main():
    try:
        username, password, server, share = load_smb_config()
    except KeyError as e:
        msg = f"Missing SMB config key: {e}"
        print(msg)
        update_copy_status("failed", error=msg)
        sys.exit(1)

    if not DOWNLOADS_DIR.exists():
        update_copy_status("nothing_to_copy")
        print("Downloads folder does not exist, nothing to copy.")
        sys.exit(0)

    pdfs = list(DOWNLOADS_DIR.glob("*.pdf"))
    if not pdfs:
        update_copy_status("nothing_to_copy")
        print("No PDF files found in downloads/, nothing to copy.")
        sys.exit(0)

    smbclient.register_session(server, username=username, password=password)

    copied = []
    try:
        for pdf in pdfs:
            remote_path = f"\\\\{server}\\{share}\\{pdf.name}"
            print(f"Copying {pdf.name} → {remote_path} … ", end="")
            with open(pdf, "rb") as local_f:
                with smbclient.open_file(remote_path, mode="wb") as remote_f:
                    remote_f.write(local_f.read())
            copied.append(pdf)
            print("done.")
    except Exception as e:
        msg = str(e)
        print(f"failed: {msg}")
        update_copy_status("failed", files=[p.name for p in copied], error=msg)
        sys.exit(1)

    # Only delete after all copies succeeded, uses pdf.unlink, but works just like os.remove(pdf) 
    for pdf in copied:
        pdf.unlink()
        print(f"Deleted {pdf.name}")

    update_copy_status("success", files=[p.name for p in copied])
    print(f"Copied and cleaned up {len(copied)} file(s) successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
