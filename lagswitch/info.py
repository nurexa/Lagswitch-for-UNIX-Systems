"""Network facts a debugger usually wants, in one place."""
import subprocess

from . import firewall, netem


def _run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip() or "(none)"


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
