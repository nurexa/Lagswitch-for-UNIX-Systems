"""Network facts a debugger usually wants, in one place."""
import os
import re
import subprocess

from . import firewall, netem


def _run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip() or "(none)"


def parse_ss(text):
    """ss -tunap output -> [(pid, name, socket_count)], busiest first."""
    found = {}
    for line in text.splitlines():
        for name, pid in re.findall(r'\("([^"]+)",pid=(\d+)', line):
            n = found.setdefault(int(pid), [name, 0])
            n[1] += 1
    return sorted(((p, n, c) for p, (n, c) in found.items()), key=lambda r: -r[2])


def processes():
    """Processes that currently own network sockets (excluding ourselves)."""
    out = subprocess.run(["ss", "-tunapH"], capture_output=True, text=True).stdout
    return [r for r in parse_ss(out) if r[0] != os.getpid()]


def show(pid=None):
    iface = netem.default_iface()
    print(f"== Interface ({iface}) ==\n{_run('ip', '-br', 'addr', 'show', iface)}")
    print(f"== Link ==\n{_run('ip', '-s', 'link', 'show', iface)}")
    print(f"== Routes ==\n{_run('ip', 'route', 'show', 'default')}")
    print("== DNS ==")
    print("\n".join(l for l in open("/etc/resolv.conf") if l.startswith("nameserver")).strip() or "(none)")
    print(f"== Latency (3 pings to 1.1.1.1) ==\n{_run('ping', '-c3', '-W1', '1.1.1.1').splitlines()[-1]}")
    print(f"== qdisc ==\n{_run('tc', 'qdisc', 'show', 'dev', iface)}")
    print(f"== Lagswitch drops ==\n{firewall.dropped()} packets")
    sockets = _run("ss", "-tunap")
    if pid:
        sockets = "\n".join(l for l in sockets.splitlines() if f"pid={pid}," in l or l.startswith("Netid"))
    print(f"== Sockets{f' (pid {pid})' if pid else ''} ==\n{sockets}")
