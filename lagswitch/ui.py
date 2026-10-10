"""Curses status panel. Works over sudo/SSH, no display server needed."""
import curses
import time

from . import firewall


def make_tick(scr, state, toggles, scope, direction, ping_ms, hints):
    """Return a callable that handles window keypresses and redraws."""
    curses.curs_set(0)
    scr.nodelay(True)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    last = [0.0]

    def tick():
        ch = scr.getch()
        if ch == ord("q"):
            raise KeyboardInterrupt
        if ch == ord("c"):
            toggles["cut"]()
        if ch == ord("l") and "lag" in toggles:
            toggles["lag"]()
        if time.time() - last[0] > 1:  # ponytail: polls nft once a second
            state["dropped"] = firewall.dropped() if state["cut"] else state["dropped"]
            last[0] = time.time()
        scr.erase()
        try:
            draw()
        except curses.error:
            pass  # terminal too small to fit; redraws on resize
        scr.refresh()

    def draw():
        scr.addstr(0, 1, "LAGSWITCH", curses.A_BOLD)
        cut = state["cut"]
        scr.addstr(2, 1, "Connection : ")
        scr.addstr("CUT " if cut else "LIVE", curses.color_pair(2 if cut else 1) | curses.A_BOLD)
        scr.addstr(3, 1, f"Scope      : {scope} ({direction})")
        lag = state["lag"]
        scr.addstr(4, 1, f"Latency    : {'+%dms' % ping_ms if lag else 'off'}")
        scr.addstr(5, 1, f"Dropped    : {state['dropped']} packets")
        scr.addstr(7, 1, hints)
        for i, line in enumerate(state["log"][-5:]):
            scr.addstr(9 + i, 1, line[: scr.getmaxyx()[1] - 3])

    return tick
