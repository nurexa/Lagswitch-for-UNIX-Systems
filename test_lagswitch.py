"""Run: python3 test_lagswitch.py  (no root needed)."""
import tempfile
import wave

from lagswitch import beep, firewall, keys

assert keys.keycode("F8") == 66 and keys.keycode("q") == 16 and keys.keycode("30") == 30
try:
    keys.keycode("nope")
    raise SystemExit("expected ValueError")
except ValueError:
    pass

out = firewall.ruleset("out")
assert "hook output" in out and "hook input" not in out and "socket cgroupv2" not in out
both = firewall.ruleset("both", cgroup=True)
assert "hook input" in both and 'socket cgroupv2 level 1 "lagswitch"' in both
with tempfile.TemporaryDirectory() as d:
    beep.make_tone(f"{d}/t.wav", 880, 2)
    with wave.open(f"{d}/t.wav") as w:
        assert w.getnframes() == 2 * int(beep.RATE * 0.18)
print("ok")
