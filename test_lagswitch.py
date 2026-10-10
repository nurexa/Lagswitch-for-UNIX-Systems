"""Run: python3 test_lagswitch.py  (no root needed)."""
import os
import struct
import tempfile
import wave

from lagswitch import beep, firewall, info, keys

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
# Hotkeys: action fires, next press is captured (not fired), release ignored
with tempfile.TemporaryDirectory() as d:
    fifo = f"{d}/kbd"
    os.mkfifo(fifo)
    wfd = os.open(fifo, os.O_RDWR)
    keys._keyboards = lambda: [fifo]
    seen, grabbed, hk = [], [], keys.Hotkeys()
    hk.actions[66] = lambda: (seen.append(66), setattr(hk, "capture", grabbed.append))
    for code, value in ((66, 1), (30, 1), (30, 0), (66, 1)):
        os.write(wfd, keys.EVENT.pack(0, 0, keys.EV_KEY, code, value))
    ticks = []
    def tick():
        ticks.append(1)
        if len(ticks) > 6:
            raise KeyboardInterrupt
    try:
        hk.listen(tick=tick, interval=0.01)
    except KeyboardInterrupt:
        pass
    assert seen == [66, 66] and grabbed == [30], (seen, grabbed)
assert keys.keyname(66) == "f8" and keys.keyname(999) == "999"
sample = ('tcp ESTAB 0 0 10.0.0.2:5000 1.1.1.1:443 users:(("firefox",pid=1234,fd=50),("firefox",pid=1234,fd=51))\n'
          'udp UNCONN 0 0 *:68 *:* users:(("dhcpcd",pid=77,fd=5))\n')
assert info.parse_ss(sample) == [(1234, "firefox", 2), (77, "dhcpcd", 1)]
print("ok")
