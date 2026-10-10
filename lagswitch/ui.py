"""Curses status panel. Works over sudo/SSH, no display server needed."""
import curses
import time

from . import firewall


def make_tick(scr, state, window_keys, hints):
    """Return a callable that handles window keypresses and redraws.
    window_keys: {ord(char): fn}; hints(): the footer text."""
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
        scr.addstr(3, 1, f"Scope      : {state['scope']} ({state['direction']})")
        scr.addstr(4, 1, f"Latency    : {'+%dms' % state['ping'] if state['lag'] else 'off'}")
        scr.addstr(5, 1, f"Dropped    : {state['dropped']} packets")
        if state["prompt"]:
            scr.addstr(7, 1, state["prompt"], curses.color_pair(3) | curses.A_BOLD)
        else:
            scr.addstr(7, 1, hints())
        width = scr.getmaxyx()[1] - 3
        for i, line in enumerate(state["log"][-5:]):
            scr.addstr(9 + i, 1, line[:width])

    def tick():
        ch = scr.getch()
        if ch == ord("q"):
            raise KeyboardInterrupt
        if ch in window_keys:
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
