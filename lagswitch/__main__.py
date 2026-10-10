"""lagswitch CLI: hotkey-toggled packet drop and added latency."""
import argparse
import os
import subprocess
import sys

from . import firewall, info, keys, netem


def _pid_of(name):
    r = subprocess.run(["pgrep", "-xo", name], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"no process named '{name}'")
    return int(r.stdout)


def run(args):
    pid = args.pid or (_pid_of(args.name) if args.name else None)
    iface = netem.default_iface()
    state = {"cut": False, "lag": False}

    def toggle_cut():
        state["cut"] = not state["cut"]
        if state["cut"]:
            firewall.enable(args.direction, cgroup=bool(pid))
            print(f"[CUT ] {args.direction} {'pid ' + str(pid) if pid else 'global'}")
        else:
            n = firewall.dropped()
            firewall.disable()
            print(f"[LIVE] connection restored ({n} packets dropped)")

    def toggle_lag():
        state["lag"] = not state["lag"]
        (netem.enable(iface, args.ping) if state["lag"] else netem.disable(iface))
        print(f"[LAG ] +{args.ping}ms on {iface}" if state["lag"] else "[LAG ] off")

    binds = {keys.keycode(args.key): toggle_cut}
    if args.ping_key:
        binds[keys.keycode(args.ping_key)] = toggle_lag

    firewall.disable()
    if pid:
        firewall.attach(pid)
    print(f"ready: {args.key} = cut{f', {args.ping_key} = +{args.ping}ms' if args.ping_key else ''}. Ctrl-C to quit.")
    try:
        keys.listen(binds)
    except KeyboardInterrupt:
        pass
    finally:
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
