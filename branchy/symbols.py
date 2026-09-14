import os
import sys


class Symbols:
    def __init__(self, stream=None):
        stream = stream or sys.stdout
        if self._unicode_ok(stream):
            self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            self.done = "✓"
            self.failed = "✗"
        else:
            self.frames = ["-", "\\", "|", "/"]
            self.done = "+"
            self.failed = "x"

    def _unicode_ok(self, stream) -> bool:
        if os.environ.get("TERM") == "dumb":
            return False
        try:
            encoding = (stream.encoding or "").lower()
        except Exception:
            return False
        return encoding.startswith("utf")

    def glyph(self, state: str, phase: int = 0, static: bool = False) -> str:
        if state == "running":
            if static:
                return "*"
            return self.frames[phase % len(self.frames)]
        if state == "done":
            return self.done
        if state == "failed":
            return self.failed
        return " "

