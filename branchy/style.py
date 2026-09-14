import os
import sys


class Style:
    def __init__(self, stream=None):
        stream = stream or sys.stdout
        no_color = os.environ.get("NO_COLOR") is not None
        dumb = os.environ.get("TERM") == "dumb"
        try:
            tty = stream.isatty()
        except Exception:
            tty = False
        self.color = tty and not no_color and not dumb

    def _gray(self, depth: int) -> int:
        return max(238, 255 - depth * 7)

    def summary(self, text: str, depth: int) -> str:
        if not self.color:
            return text
        gray = self._gray(depth)
        codes = [f"38;5;{gray}"]
        if depth == 0:
            codes.insert(0, "1")
        return f"\033[{';'.join(codes)}m{text}\033[0m"

    def log(self, text: str, depth: int) -> str:
        if not self.color:
            return text
        gray = self._gray(depth + 1)
        return f"\033[2;38;5;{gray}m{text}\033[0m"

    def fail(self, text: str) -> str:
        if not self.color:
            return text
        return f"\033[1;31m{text}\033[0m"

