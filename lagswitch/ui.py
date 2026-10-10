"""Curses status panel. Works over sudo/SSH, no display server needed."""
import curses
import time

from . import firewall


def make_tick(scr, state, window_keys, hints, pick):
    """Return a callable that handles window keypresses and redraws.
    window_keys: {ord(char): fn}; hints(): footer text (may hold newlines);
    pick(pid_or_None): called when the process picker (state["picker"]) is confirmed."""
    curses.curs_set(0)
    scr.nodelay(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    last = [0.0]

    def draw():
        scr.addstr(0, 1, "LAGSWITCH", curses.A_BOLD)
        cut = state["cut"]
        scr.addstr(2, 1, "Connection : ")
        scr.addstr("CUT " if cut else "LIVE", curses.color_pair(2 if cut else 1) | curses.A_BOLD)
        scr.addstr(3, 1, f"Scope      : {state['scope']}")
        scr.addstr(4, 1, f"Direction  : {state['direction_label']}")
        scr.addstr(5, 1, f"Latency    : {'+%dms' % state['ping'] if state['lag'] else 'off'}")
        scr.addstr(6, 1, f"Dropped    : {state['dropped']} packets")
        width = scr.getmaxyx()[1] - 3
        pk = state["picker"]
        if pk:
            scr.addstr(8, 1, "Pick a process:  Up/Down move, Enter select, Esc cancel",
                       curses.color_pair(3) | curses.A_BOLD)
            top = max(0, pk["i"] - 7)
            for row, (_, label) in enumerate(pk["items"][top:top + 8]):
                mark = curses.A_REVERSE if top + row == pk["i"] else 0
                scr.addstr(10 + row, 1, label[:width], mark)
            return
        if state["prompt"]:
            scr.addstr(8, 1, state["prompt"], curses.color_pair(3) | curses.A_BOLD)
        else:
            for i, line in enumerate(hints().split("\n")):
                scr.addstr(8 + i, 1, line[:width])
        for i, line in enumerate(state["log"][-5:]):
            scr.addstr(11 + i, 1, line[:width])

    def tick():
        ch = scr.getch()
        pk = state["picker"]
        if pk:  # picker is modal for window keys; hotkeys keep working
            if ch == curses.KEY_UP:
                pk["i"] = max(0, pk["i"] - 1)
            elif ch == curses.KEY_DOWN:
                pk["i"] = min(len(pk["items"]) - 1, pk["i"] + 1)
            elif ch in (10, 13, curses.KEY_ENTER):
                state["picker"] = None
                pick(*pk["items"][pk["i"]][:1])
            elif ch in (27, ord("q"), ord("p")):
                state["picker"] = None
        elif ch == ord("q"):
            raise KeyboardInterrupt
        elif ch in window_keys:
            window_keys[ch]()
        if time.time() - last[0] > 1:  # ponytail: polls nft once a second
            if state["cut"]:
                state["dropped"] = firewall.dropped()
            last[0] = time.time()
        scr.erase()
        try:
            draw()
        except curses.error:
            pass  # terminal too small to fit; redraws on resize
        scr.refresh()

    return tick
