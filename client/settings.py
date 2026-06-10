import json
import os
import sys

# Locate settings.json in the same directory as the executable/script
if hasattr(sys, "frozen") or getattr(sys, "frozen", False):
    # Running as compiled binary
    base_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    # Running from python source
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SETTINGS_FILE = os.path.join(base_dir, "settings.json")

DEFAULT_SETTINGS = {
    "server_hostname": "localhost",
    "server_port": 8765,
    "use_cloudflare": False,
    "cloudflare_url": ""
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            # Merge with default settings to ensure all keys exist
            settings = DEFAULT_SETTINGS.copy()
            settings.update(data)
            return settings
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception:
        return False
