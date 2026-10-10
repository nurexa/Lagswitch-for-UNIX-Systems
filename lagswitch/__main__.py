"""lagswitch CLI: hotkey-toggled packet drop and added latency."""
import argparse
import os
import subprocess
import sys

from . import beep, firewall, info, keys, netem


def _pid_of(name):
    r = subprocess.run(["pgrep", "-xo", name], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"no process named '{name}'")
    return int(r.stdout)


def run(args):
    pid = args.pid or (_pid_of(args.name) if args.name else None)
    iface = netem.default_iface()
    state = {"cut": False, "lag": False, "dropped": 0, "log": []}
    beeper = beep.Beeper(enabled=not args.no_beep)
    scope = f"pid {pid}" if pid else "global"

    def say(msg):
        state["log"].append(msg)
        if not args.ui:
            print(msg)

    def toggle_cut():
        state["cut"] = not state["cut"]
        if state["cut"]:
            state["dropped"] = 0
            firewall.enable(args.direction, cgroup=bool(pid))
            say(f"[CUT ] {args.direction} {scope}")
        else:
            state["dropped"] = firewall.dropped()
            firewall.disable()
            say(f"[LIVE] connection restored ({state['dropped']} packets dropped)")
        beeper.play("cut", state["cut"])

    def toggle_lag():
        state["lag"] = not state["lag"]
        (netem.enable(iface, args.ping) if state["lag"] else netem.disable(iface))
        say(f"[LAG ] +{args.ping}ms on {iface}" if state["lag"] else "[LAG ] off")
        beeper.play("lag", state["lag"])

    toggles = {"cut": toggle_cut}
    binds = {keys.keycode(args.key): toggle_cut}
    hints = f"[{args.key}] cut"
    if args.ping_key:
        toggles["lag"] = toggle_lag
        binds[keys.keycode(args.ping_key)] = toggle_lag
        hints += f"   [{args.ping_key}] lag"
    hints += "   (window: c / l)   [q] quit"

    firewall.disable()
    if pid:
        firewall.attach(pid)
    try:
        if args.ui:
            import curses
            from . import ui
            curses.wrapper(lambda scr: keys.listen(
                binds, tick=ui.make_tick(scr, state, toggles, scope, args.direction, args.ping, hints)))
        else:
            print(f"ready: {hints}. Ctrl-C to quit.")
            keys.listen(binds)
    except KeyboardInterrupt:
        pass
    finally:
        beeper.close()
        reset()


def reset(_=None):
    firewall.disable()
    firewall.detach()
    try:
        netem.disable(netem.default_iface())
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser(prog="lagswitch", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="start the hotkey listener (needs root)")
    r.add_argument("-k", "--key", default="f8", help="toggle cut key (default f8)")
    r.add_argument("-d", "--direction", choices=["in", "out", "both"], default="both")
    g = r.add_mutually_exclusive_group()
    g.add_argument("-p", "--pid", type=int, help="only cut this process")
    g.add_argument("-n", "--name", help="only cut the oldest process with this exact name")
    r.add_argument("--ping-key", help="key that toggles added latency (off if unset)")
    r.add_argument("--ping", type=int, default=200, metavar="MS", help="added latency (default 200)")
    r.add_argument("--ui", action="store_true", help="show a live status panel in the terminal")
    r.add_argument("--no-beep", action="store_true", help="disable on/off sounds")
    r.set_defaults(fn=run)
    i = sub.add_parser("info", help="show network diagnostics")
    i.add_argument("-p", "--pid", type=int, help="filter sockets to this pid")
    i.set_defaults(fn=lambda a: info.show(a.pid))
    sub.add_parser("reset", help="remove all rules/qdiscs/cgroups left behind").set_defaults(fn=reset)
    args = p.parse_args()
    if os.geteuid() != 0:
        sys.exit("lagswitch needs root: sudo lagswitch ...")
    args.fn(args)


main()
