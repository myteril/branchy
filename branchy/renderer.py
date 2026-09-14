from __future__ import annotations

import os
import sys
import threading
import time

from . import compat
from .style import Style
from .symbols import Symbols


class Renderer:
    def __init__(self, stream=None):
        self.stream = stream or sys.stdout
        self.lock = threading.Lock()
        self.prev_rows = 0
        self.spinner = 0
        self._thread = None
        self.roots: list = []
        self._finalized: set[int] = set()
        self.style = Style(self.stream)
        self.symbols = Symbols(self.stream)
        self.use_ansi = self._ansi_ok()

    def _ansi_ok(self) -> bool:
        if os.environ.get("TERM") == "dumb":
            return False
        try:
            return self.stream.isatty()
        except Exception:
            return False

    def register(self, node):
        if node.parent is None:
            self.roots.append(node)

    def start_node(self, node):
        with self.lock:
            node.state = "running"
            if self.use_ansi:
                self._ensure_animator()
                self._draw_live()
            else:
                self._static_event("start", node)

    def log(self, node, _message):
        with self.lock:
            if self.use_ansi:
                self._draw_live()
            else:
                self._static_log(node, _message)

    def set_state(self, node, state=None):
        with self.lock:
            if state is not None:
                if state == "done":
                    node.logs.clear()
                node.state = state
            if self.use_ansi:
                self._draw_live()
                if not self._any_active():
                    self.spinner = 0
            else:
                if node.state in ("done", "failed"):
                    self._static_event("terminal", node)

    def leave_cursor(self):
        with self.lock:
            if self.use_ansi:
                self.stream.write("\033[?25h\n")
                self.stream.flush()
            for root in self.roots:
                if root.state != "running":
                    self._finalized.add(id(root))
            self.prev_rows = 0
            self.spinner = 0
    def _is_active(self, node) -> bool:
        if node.state == "running":
            return True
        return any(self._is_active(c) for c in node.children)

    def _any_active(self) -> bool:
        return any(self._is_active(r) for r in self.roots)

    def _ensure_animator(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def _animate(self):
        while True:
            time.sleep(0.08)
            with self.lock:
                if not self._any_active():
                    break
                self.spinner += 1
                self._draw_live()

    def _static_event(self, kind, node):
        width = compat.get_terminal_width(self.stream, 80)
        indent = "  " * node.depth
        prefix_len = node.depth * 2 + 2
        content_width = max(0, width - prefix_len)
        label = compat.truncate(node.label, content_width)
        if kind == "start":
            glyph = self.symbols.glyph("running", static=True)
        else:
            glyph = self.symbols.glyph(node.state, static=True)
        self.stream.write(f"{indent}{glyph} {label}\n")
        self.stream.flush()

    def _static_log(self, node, message):
        width = compat.get_terminal_width(self.stream, 80)
        desc_col = (node.depth + 1) * 2
        log_width = max(1, width - desc_col)
        prefix = " " * desc_col
        for part in compat.wrap_text(message, log_width):
            self.stream.write(f"{prefix}{part}\n")
        self.stream.flush()

    def _build_rows(self):
        rows = []
        for root in self.roots:
            if id(root) in self._finalized:
                continue
            if self._is_active(root) or root.state in ("done", "failed"):
                self._append_node(rows, root)
        return rows

    def _append_node(self, rows, node):
        width = compat.get_terminal_width(self.stream, 80)
        indent = "  " * node.depth
        prefix_len = node.depth * 2 + 2
        content_width = max(0, width - prefix_len)

        glyph = self.symbols.glyph(node.state, self.spinner)
        if node.state == "failed" and self.style.color:
            glyph = self.style.fail(glyph)

        label = compat.truncate(node.label, content_width)
        styled_label = self.style.summary(label, node.depth)
        rows.append(f"{indent}{glyph} {styled_label}")

        if node.state in ("running", "failed"):
            desc_col = (node.depth + 1) * 2
            log_width = max(1, width - desc_col)
            prefix = " " * desc_col
            for msg in node.logs:
                for part in compat.wrap_text(msg, log_width):
                    rows.append(self.style.log(f"{prefix}{part}", node.depth))
            for child in node.children:
                self._append_node(rows, child)

    def _draw_live(self):
        rows = self._build_rows()
        out = ["\033[?25l"]
        if self.prev_rows:
            out.append(f"\033[{self.prev_rows}A")
        else:
            out.append("\r")
        for line in rows:
            out.append(line)
            out.append("\033[K\n")
        for _ in range(self.prev_rows - len(rows)):
            # otag: relies on standard ANSI Delete Line (\033[M); terminals without DL would keep ghost lines.
            out.append("\033[M")
        self.stream.write("".join(out))
        self.stream.flush()
        self.prev_rows = len(rows)
