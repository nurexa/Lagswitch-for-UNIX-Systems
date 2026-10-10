"""Remember settings (keys, latency) between runs in ~/.config/lagswitch.json."""
import json
import os


def _path():
    user = os.environ.get("SUDO_USER")  # we run as root; settings belong to the invoking user
    return os.path.join(os.path.expanduser(f"~{user}" if user else "~"), ".config", "lagswitch.json")


def load():
    try:
        with open(_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(settings):
    try:
        with open(_path(), "w") as f:
            json.dump(settings, f)
        if os.environ.get("SUDO_UID"):
            os.chown(_path(), int(os.environ["SUDO_UID"]), int(os.environ.get("SUDO_GID", -1)))
    except OSError:
        pass  # settings just won't persist
