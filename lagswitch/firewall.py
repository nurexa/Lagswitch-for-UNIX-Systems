"""Drop traffic with an nftables table, globally or for one cgroup (process)."""
import os
import re
import subprocess

TABLE = "lagswitch"
CGROUP = "/sys/fs/cgroup/lagswitch"


def _nft(script):
    subprocess.run(["nft", "-f", "-"], input=script, text=True, check=True)


def ruleset(direction="both", cgroup=False):
    """Build the nft script. direction: in | out | both."""
    match = f'socket cgroupv2 level 1 "{os.path.basename(CGROUP)}" ' if cgroup else ""
    chains = {"out": ("output", "oifname"), "in": ("input", "iifname")}
    lines = [f"table inet {TABLE} {{"]
    for d, (hook, ifkw) in chains.items():
        if direction in (d, "both"):
            lines += [f"  chain {d} {{",
                      f"    type filter hook {hook} priority -300; policy accept;",
                      f'    {ifkw} "lo" accept  # keep loopback alive',
                      f"    {match}counter drop",
                      "  }"]
    lines.append("}")
    return "\n".join(lines)


def enable(direction="both", cgroup=False):
    disable()
    _nft(ruleset(direction, cgroup))


def disable():
    subprocess.run(["nft", "delete", "table", "inet", TABLE], capture_output=True)


def dropped():
    """Packets dropped by the current table (0 if not loaded)."""
    out = subprocess.run(["nft", "list", "table", "inet", TABLE],
                         capture_output=True, text=True).stdout
    return sum(int(n) for n in re.findall(r"counter packets (\d+)", out))


def attach(pid):
    """Move a process (and its future children) into the lagswitch cgroup."""
    os.makedirs(CGROUP, exist_ok=True)
    with open(f"{CGROUP}/cgroup.procs", "w") as f:
        f.write(str(pid))


def detach():
    """Return attached processes to the root cgroup and remove ours."""
    try:
        with open(f"{CGROUP}/cgroup.procs") as f:
            pids = f.read().split()
        for pid in pids:
            try:
                with open("/sys/fs/cgroup/cgroup.procs", "w") as f:
                    f.write(pid)
            except OSError:
                pass  # process already gone
        os.rmdir(CGROUP)
    except FileNotFoundError:
        pass
