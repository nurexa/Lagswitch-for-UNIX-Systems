"""Add artificial latency to outgoing packets with tc netem."""
import re
import subprocess


def default_iface():
    out = subprocess.run(["ip", "route", "get", "1.1.1.1"],
                         capture_output=True, text=True, check=True).stdout
    return re.search(r"dev (\S+)", out).group(1)


def enable(iface, ms):
    # ponytail: replaces the root qdisc; egress only, so RTT grows by `ms`
    subprocess.run(["tc", "qdisc", "replace", "dev", iface, "root", "netem",
                    "delay", f"{ms}ms"], check=True)


def disable(iface):
    subprocess.run(["tc", "qdisc", "del", "dev", iface, "root"], capture_output=True)
