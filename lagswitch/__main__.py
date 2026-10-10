"""lagswitch CLI: hotkey-toggled packet drop and added latency."""
import argparse
import os
import subprocess
import sys

from . import beep, config, firewall, info, keys, netem


def _pid_of(name):
    r = subprocess.run(["pgrep", "-xo", name], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"no process named '{name}'")
    return int(r.stdout)


def run(args):
    cfg = config.load()
    pid = args.pid or (_pid_of(args.name) if args.name else None)
    iface = netem.default_iface()
    ping = args.ping or cfg.get("ping", 200)
    keymap = {"cut": keys.keycode(args.key or cfg.get("key", "f8")),
              "lag": keys.keycode(args.ping_key or cfg.get("ping_key", "f9"))}
    state = {"cut": False, "lag": False, "dropped": 0, "log": [], "prompt": "",
             "scope": f"pid {pid}" if pid else "global", "direction": args.direction, "ping": ping}
    beeper = beep.Beeper(enabled=not args.no_beep)
    hk = keys.Hotkeys()

    def say(msg):
        state["log"].append(msg)
        if args.plain:
            print(msg)

    def toggle_cut():
        state["cut"] = not state["cut"]
        if state["cut"]:
            state["dropped"] = 0
            firewall.enable(args.direction, cgroup=bool(pid))
            say(f"[CUT ] {args.direction} {state['scope']}")
        else:
            state["dropped"] = firewall.dropped()
            firewall.disable()
            say(f"[LIVE] connection restored ({state['dropped']} packets dropped)")
        beeper.play("cut", state["cut"])

    def toggle_lag():
        state["lag"] = not state["lag"]
        (netem.enable(iface, ping) if state["lag"] else netem.disable(iface))
        say(f"[LAG ] +{ping}ms on {iface}" if state["lag"] else "[LAG ] off")
        beeper.play("lag", state["lag"])

    actions = {"cut": toggle_cut, "lag": toggle_lag}

    def bind(action, code):
        hk.actions = {c: f for c, f in hk.actions.items() if f is not actions[action]}
        keymap[action] = code
        hk.actions[code] = actions[action]

    def rebind(action):
        """Detect the next physical key press and assign it to `action`."""
        state["prompt"] = f"Press the new key for {action.upper()}...  (Esc cancels)"

        def got(code):
            state["prompt"] = ""
            other = next((a for a, c in keymap.items() if c == code and a != action), None)
            if code == 1:
                say("rebind cancelled")
            elif other:
                say(f"{keys.keyname(code)} is already the {other.upper()} key; try another")
            else:
                bind(action, code)
                config.save({"key": keys.keyname(keymap["cut"]), "ping_key": keys.keyname(keymap["lag"]),
                             "ping": ping})
                say(f"{action.upper()} key is now {keys.keyname(code)}")
        hk.capture = got

    for action, code in keymap.items():
        bind(action, code)

    def hints():
        return (f"[{keys.keyname(keymap['cut'])}] cut  [{keys.keyname(keymap['lag'])}] lag   "
                "window: c l = toggle, 1 2 = change key, q = quit")

    firewall.disable()
    if pid:
        firewall.attach(pid)
    try:
        if args.plain:
            print(f"ready: {hints()}. Ctrl-C to quit.")
            hk.listen()
        else:
            import curses
            from . import ui
            window_keys = {ord("c"): toggle_cut, ord("l"): toggle_lag,
                           ord("1"): lambda: rebind("cut"), ord("2"): lambda: rebind("lag")}
            curses.wrapper(lambda scr: hk.listen(tick=ui.make_tick(scr, state, window_keys, hints)))
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
    # ponytail: bare `lagswitch` (or only flags) means `run`
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-") and argv[0] not in ("-h", "--help"):
        argv.insert(0, "run")
    r = sub.add_parser("run", help="start the hotkey listener (needs root)")
    r.add_argument("-k", "--key", help="cut-off key (default f8, or last saved)")
    r.add_argument("-d", "--direction", choices=["in", "out", "both"], default="both")
    g = r.add_mutually_exclusive_group()
    g.add_argument("-p", "--pid", type=int, help="only cut this process")
    g.add_argument("-n", "--name", help="only cut the oldest process with this exact name")
    r.add_argument("--ping-key", help="latency key (default f9, or last saved)")
    r.add_argument("--ping", type=int, metavar="MS", help="added latency (default 200)")
    r.add_argument("--plain", action="store_true", help="no status panel, just log lines")
    r.add_argument("--no-beep", action="store_true", help="disable on/off sounds")
    r.set_defaults(fn=run)
    i = sub.add_parser("info", help="show network diagnostics")
    i.add_argument("-p", "--pid", type=int, help="filter sockets to this pid")
    i.set_defaults(fn=lambda a: info.show(a.pid))
    sub.add_parser("reset", help="remove all rules/qdiscs/cgroups left behind").set_defaults(fn=reset)
    args = p.parse_args(argv)
    if os.geteuid() != 0:
        sys.exit("lagswitch needs root: sudo lagswitch ...")
    args.fn(args)


main()
