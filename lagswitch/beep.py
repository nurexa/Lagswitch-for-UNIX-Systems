"""Audible on/off cue. Tones are generated at startup and played as the invoking user."""
import array
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave

RATE = 22050
PLAYER = next((p for p in ("pw-play", "paplay", "aplay") if shutil.which(p)), None)


def make_tone(path, freq, count=1):
    """Write `count` 0.12s sine beeps at `freq` Hz to a mono 16-bit wav."""
    beep = [int(12000 * math.sin(2 * math.pi * freq * i / RATE)) for i in range(int(RATE * 0.12))]
    pcm = array.array("h", (beep + [0] * int(RATE * 0.06)) * count)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


class Beeper:
    """cut: ON=high, OFF=low. lag: same pitches, doubled."""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.dir = tempfile.mkdtemp(prefix="lagswitch-")
        os.chmod(self.dir, 0o755)  # readable by the sudo user
        for name, freq, n in (("cut_on", 880, 1), ("cut_off", 330, 1),
                              ("lag_on", 880, 2), ("lag_off", 330, 2)):
            make_tone(f"{self.dir}/{name}.wav", freq, n)

    def play(self, kind, on):
        if not self.enabled:
            return
        path = f"{self.dir}/{kind}_{'on' if on else 'off'}.wav"
        cmd = [PLAYER, path] if PLAYER else None
        uid, user = os.environ.get("SUDO_UID"), os.environ.get("SUDO_USER")
        if cmd and uid and user:  # root has no audio session; borrow the user's
            cmd = ["runuser", "-u", user, "--", "env", f"XDG_RUNTIME_DIR=/run/user/{uid}", *cmd]
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (TypeError, OSError):
            sys.stdout.write("\a")  # no player: terminal bell
            sys.stdout.flush()

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)
