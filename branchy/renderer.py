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
        self._in_live = False
        self._paused = False
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

    def pause(self) -> bool:
        with self.lock:
            if not self.use_ansi or not self._in_live:
                return False
            self._paused = True
            self.stream.write("\033[?25h")
            self.stream.flush()
            return True

    def resume(self):
        with self.lock:
            if not self._paused:
                return
            self._paused = False
            # one full redraw wipes the prompt and the echoed answer
            self._draw_live()

    def register(self, node):
        if node.parent is None:
            self.roots.append(node)

    def start_node(self, node):
        with self.lock:
            node.state = "running"
            if self.use_ansi:
                self._ensure_animator()
                self._draw_live()

    def log(self, node, _message):
        with self.lock:
            if self.use_ansi:
                self._draw_live()

    def rename(self, node):
        with self.lock:
            root = node
            while root.parent is not None:
                root = root.parent
            if not any(root is r for r in self.roots):
                # tree already finalized and deregistered; a redraw here
                # would re-enter the alternate screen with an empty tree.
                return
            # otag: static (non-TTY) mode has no live frames, so rename
            # stays silent; the final static render prints the last-set
            # label. Ceiling: intermediate renames are unobservable there.
            # Upgrade: emit rename events if static output ever streams.
            if self.use_ansi:
                self._draw_live()

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

    def leave_cursor(self):
        with self.lock:
            if self.use_ansi:
                self._draw_live()
                # otag: after restoring the main screen, clear the shell's
                # prompt line so the previously typed command does not stay
                # visible as the current input. Ceiling: relies on ANSI
                # erase-in-line (ESC[2K) and cursor-horizontal-absolute
                # (ESC[G); these are universally supported alongside the
                # alternate-screen sequence ESC[?1049. Upgrade: use DECSC/DECRC
                # or terminal capability queries if a target terminal breaks.
                self.stream.write("\033[?1049l\033[?25h\033[2K\033[G")
                self.stream.flush()
                self._in_live = False
                self._render_static_final()
            else:
                self._render_static_final()
            for root in self.roots:
                if root.state != "running":
                    self._finalized.add(id(root))
            self.prev_rows = 0
            self.spinner = 0
            self._in_live = False
            self.roots.clear()
            self._finalized.clear()
    def _is_active(self, node) -> bool:
        if node.state == "running":
            return True
        return any(self._is_active(c) for c in node.children)

    def _any_active(self) -> bool:
        return any(self._is_active(r) for r in self.roots)
    def _has_active_sibling_after(self, children, idx):
        return any(self._is_active(c) for c in children[idx + 1 :])



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
                if self._paused:
                    continue
                self.spinner += 1
                self._draw_live()

    def _render_static_final(self):
        rows = self._build_rows()
        if rows:
            self.stream.write("\n".join(rows) + "\n")
            self.stream.flush()
    def _build_rows(self):
        rows = []
        for i, root in enumerate(self.roots):
            if id(root) in self._finalized:
                continue
            if self._is_active(root) or root.state in ("done", "failed"):
                omit_logs = (
                    root.state in ("done", "failed")
                    and self._has_active_sibling_after(self.roots, i)
                )
                self._append_node(rows, root, omit_logs=omit_logs)
        return rows

    def _append_node(self, rows, node, omit_logs: bool = False):
        width = compat.get_terminal_width(self.stream, 80)
        indent = "  " * node.depth
        prefix_len = node.depth * 2 + 2
        content_width = max(0, width - prefix_len)

        glyph = self.symbols.glyph(node.state, self.spinner)
        if node.state == "failed" and self.style.color:
            glyph = self.style.fail(glyph)

        suffix = ""
        if node.show_elapsed and node.state != "pending":
            if node.state == "running":
                elapsed = time.monotonic() - node.started
                suffix = compat.format_duration(elapsed, False)
            else:
                suffix = compat.format_duration(node.duration, True)
        budget = content_width
        if suffix:
            budget -= compat.str_width(suffix) + 1  # + 1: separating space
        if suffix and budget <= 0:
            # otag: documented narrow-terminal degenerate case - the label is
            # dropped so the row is glyph + suffix only; truncate() would
            # print "..." in a zero-width budget. Upgrade: steal width back
            # from the suffix before dropping the label.
            label = ""
        else:
            label = compat.truncate(node.label, budget)
        styled_label = self.style.summary(label, node.depth)
        row = f"{indent}{glyph} {styled_label}"
        if suffix:
            row += " " + self.style.log(suffix, node.depth)
        rows.append(row)

        if not omit_logs and node.state in ("running", "failed"):
            desc_col = (node.depth + 1) * 2
            log_width = max(1, width - desc_col)
            prefix = " " * desc_col
            for msg in node.logs:
                for part in compat.wrap_text(msg, log_width):
                    rows.append(self.style.log(f"{prefix}{part}", node.depth))

        if node.state != "pending":
            for i, child in enumerate(node.children):
                child_omit_logs = (
                    child.state in ("done", "failed")
                    and self._has_active_sibling_after(node.children, i)
                )
                self._append_node(rows, child, child_omit_logs)

    def _draw_live(self):
        if self._paused:
            return
        rows = self._build_rows()
        out = []
        if self._in_live:
            out.append("\033[H\033[J")
        else:
            # alternate-screen boundary; assumes xterm/VT-compatible
            # support for ESC[?1049h and ED0. TERM=dumb bypasses this path.
            out.append("\033[?1049h\033[H\033[J")
            self._in_live = True
        out.append("\033[?25l")
        for line in rows:
            out.append("\033[2K")
            out.append(line)
            out.append("\n")
        self.stream.write("".join(out))
        self.stream.flush()
        self.prev_rows = len(rows)