"""Global hotkeys by reading /dev/input directly (X11 and Wayland, stdlib only)."""
import glob
import os
import re
import select
import struct

EVENT = struct.Struct("llHHi")  # ponytail: 64-bit layout (sec, usec, type, code, value)
EV_KEY, PRESS = 1, 1

KEYS = {f"f{i}": 58 + i for i in range(1, 11)}
KEYS.update(f11=87, f12=88, space=57, scrolllock=70, pause=119, insert=110,
            home=102, end=107, pageup=104, pagedown=109)
for _row, _start in (("1234567890", 2), ("qwertyuiop", 16), ("asdfghjkl", 30), ("zxcvbnm", 44)):
    KEYS.update({c: _start + i for i, c in enumerate(_row)})


def keycode(name):
    """'f8' -> 66; a bare number is taken as a raw evdev code (see `evtest`)."""
    name = name.lower()
    if name.isdigit():
        return int(name)
    if name not in KEYS:
        raise ValueError(f"unknown key '{name}' (try f1-f12, a-z, 0-9, or a raw code)")
    return KEYS[name]


def _keyboards():
    text = open("/proc/bus/input/devices").read()
    for block in text.split("\n\n"):
        if re.search(r"Handlers=.*\bkbd\b", block):
            for ev in re.findall(r"\bevent\d+\b", block):
                yield f"/dev/input/{ev}"


def listen(binds, tick=None, interval=0.2):
    """Block forever; call binds[code]() on each press of a bound key.
    If given, tick() runs every `interval` seconds (and after each event)."""
    files = [open(p, "rb", buffering=0) for p in _keyboards()]
    if not files:
        raise RuntimeError("no keyboard found in /dev/input (are you root?)")
    while True:
        ready, _, _ = select.select(files, [], [], interval if tick else None)
        for f in ready:
            data = os.read(f.fileno(), EVENT.size)
            if len(data) < EVENT.size:
                continue
            _, _, etype, code, value = EVENT.unpack(data)
            if etype == EV_KEY and value == PRESS and code in binds:
                binds[code]()
        if tick:
            tick()
