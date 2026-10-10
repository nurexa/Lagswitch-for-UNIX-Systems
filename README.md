# Lagswitch for UNIX Systems

Hotkey-toggled network cut-off (in / out / both) for the whole machine or a single process,
plus an optional hotkey that adds fake latency. Also a small network-diagnostics command.
For network debugging and resilience testing on **your own** machine.

Linux · Python 3 (stdlib only) · `nftables`, `iproute2` · root

## Install

```sh
git clone https://github.com/nurexa/Lagswitch-for-UNIX-Systems
cd Lagswitch-for-UNIX-Systems
./install.sh            # ./install.sh uninstall to remove
```

## Use

```sh
sudo lagswitch
```

That's it: a live panel opens, **F8** cuts/restores the connection, **F9** toggles +200ms latency.

**Change a key from the panel:** press `1` (cut) or `2` (latency), then press the key you want on
your keyboard. It is detected automatically, checked for conflicts, and remembered next time
(`~/.config/lagswitch.json`). `Esc` cancels. `c` / `l` toggle from the window, `q` quits.

```sh
sudo lagswitch -n firefox -d out    # only that process (by name), outgoing only
sudo lagswitch -p 1234              # only that PID
sudo lagswitch --ping 300           # +300ms instead of +200ms
sudo lagswitch --plain --no-beep    # log lines only, no sounds
sudo lagswitch info [-p PID]        # diagnostics
sudo lagswitch reset                # clean up after a crash
```

Ctrl-C / `q` stops it and removes every rule, qdisc and cgroup it created.

| Flag | Meaning |
|---|---|
| `-k, --key` | cut-off key: `f1`-`f12`, `a`-`z`, `0`-`9`, `space`, `pause`, `scrolllock`, … or a raw evdev code (default `f8`, or last saved) |
| `--ping-key`, `--ping` | latency key (default `f9`) and milliseconds (default 200) |
| `-d, --direction` | `in`, `out`, `both` (default) |
| `-p / -n` | restrict to a PID / exact process name |
| `--plain` | no status panel, just log lines |
| `--no-beep` | disable sounds |

## Sounds

Every toggle plays a tone so you can tell the state without looking:

| | ON | OFF |
|---|---|---|
| Cut-off | one high beep | one low beep |
| Latency | two high beeps | two low beeps |

Played as your own user via `pw-play` / `paplay` / `aplay`; falls back to the terminal bell.

## `info`

Interface + address, link error counters, default route, DNS servers, RTT (3 pings),
active qdisc, packets dropped by the switch, and open sockets (optionally filtered to a PID).
Dropped-packet counts are also printed each time the switch is turned off.

## How it works

```
lagswitch/
  __main__.py   CLI + toggle logic
  keys.py       global hotkeys via /dev/input (X11 and Wayland)
  firewall.py   nftables table (priority -300) + per-process cgroup
  netem.py      tc netem latency
  beep.py       on/off tones
  ui.py         curses status panel
  config.py     remembers your keys
  info.py       diagnostics
```

- **Cut-off:** an `inet lagswitch` nft table drops packets; loopback is always allowed.
- **Per process:** the PID is moved into cgroup `/sys/fs/cgroup/lagswitch` (children follow) and
  the rules match `socket cgroupv2`. It is moved back on exit.
- **Latency:** `tc qdisc replace ... netem delay` on the default interface.

## Limitations

- Linux only (needs cgroup v2 and nftables; kernel ≥ 5.13 for per-process). No macOS/BSD yet.
- Added latency is egress-only and applies to the whole interface, not per process. It replaces the
  interface's root qdisc while on (restored to the default when off).
- Per-process *inbound* matching depends on the kernel associating the packet with a socket;
  outgoing cut-off is what reliably stalls a process.
- Key reading assumes a 64-bit system.
- Do not use against online games or services whose rules forbid it.

## Test

`python3 test_lagswitch.py`
