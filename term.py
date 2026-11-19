"""终端底座：raw 输入、替换屏幕、尺寸和按键解析。"""

from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import tty


class Terminal:
    def __init__(self):
        self.fd_in = sys.stdin.fileno()
        self.fd_out = sys.stdout.fileno()
        self.old = None
        self._entered = False

    def __enter__(self):
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise RuntimeError("需要一个真正的终端（TTY）才能玩。")
        self.old = termios.tcgetattr(self.fd_in)
        tty.setcbreak(self.fd_in)
        self.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[2J\x1b[H")
        self.flush()
        self._entered = True
        return self

    def __exit__(self, *exc):
        if self._entered:
            self.write("\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l")
            self.flush()
            try:
                termios.tcsetattr(self.fd_in, termios.TCSADRAIN, self.old)
            except termios.error:
                pass
            self._entered = False
        return False

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def size(self) -> tuple[int, int]:
        s = shutil.get_terminal_size(fallback=(100, 30))
        return s.columns, s.lines

    def clear(self) -> None:
        self.write("\x1b[2J\x1b[H")

    def read_keys(self, timeout: float) -> list[str]:
        ready, _, _ = select.select([self.fd_in], [], [], max(0.0, timeout))
        if not ready:
            return []
        try:
            data = os.read(self.fd_in, 4096)
        except OSError:
            return []
        if not data:
            return []
        keys: list[str] = []
        i = 0
        while i < len(data):
            b = data[i]
            if b == 0x1B:
                if i + 2 < len(data) and data[i + 1] in (0x5B, 0x4F):
                    final = data[i + 2]
                    name = {0x41: "up", 0x42: "down", 0x43: "right", 0x44: "left"}.get(final)
                    if name:
                        keys.append(name)
                    i += 3
                    continue
                keys.append("esc")
                i += 1
                continue
            if b in (0x0A, 0x0D):
                keys.append("enter")
            elif b in (0x08, 0x7F):
                keys.append("backspace")
            elif b == 0x09:
                keys.append("tab")
            elif b == 0x03:
                keys.append("ctrl-c")
            elif 0x20 <= b <= 0x7E:
                keys.append(chr(b))
            i += 1
        return keys
