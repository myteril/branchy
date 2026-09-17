import sys
import threading

from .renderer import Renderer


class CaptureStream:
    # only intercepts writes made through Python's sys.stdout/sys.stderr
    # objects. Low-level FD writes, C extensions, or native prints bypass it.
    # If that happens, the alternate screen buffer (ESC[?1049h / ESC[?1049l)
    # is the documented fallback.

    _local = threading.local()
    _lock = threading.RLock()
    _active_count = 0
    _orig_stdout = None
    _orig_stderr = None

    def __init__(self, stream):
        self._stream = stream

    @classmethod
    def _active_process(cls):
        stack = getattr(cls._local, "stack", None)
        if stack:
            return stack[-1]
        return None

    def write(self, text):
        proc = self._active_process()
        if proc is None:
            self._stream.write(text)
            return

        buf = getattr(proc, "_capture_buffer", "") + text
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            proc.log(line)
        proc._capture_buffer = buf

    def flush(self):
        proc = self._active_process()
        if proc is not None:
            buf = getattr(proc, "_capture_buffer", "")
            if buf:
                try:
                    proc.log(buf)
                except Exception:
                    pass
                proc._capture_buffer = ""
        self._stream.flush()

    def __getattr__(self, name):
        return getattr(self._stream, name)

    @classmethod
    def _install(cls):
        sys.stdout = cls(cls._orig_stdout)
        sys.stderr = cls(cls._orig_stderr)

    @classmethod
    def _uninstall(cls):
        sys.stdout = cls._orig_stdout
        sys.stderr = cls._orig_stderr

    @classmethod
    def _push(cls, process):
        if not hasattr(cls._local, "stack"):
            cls._local.stack = []
        cls._local.stack.append(process)
        with cls._lock:
            cls._active_count += 1
            if cls._active_count == 1:
                cls._orig_stdout = sys.stdout
                cls._orig_stderr = sys.stderr
                cls._install()

    @classmethod
    def _pop(cls, process):
        stack = getattr(cls._local, "stack", None)
        if stack and process in stack:
            # buffer is owned by the popped process; flush before it leaves
            # the stack so the next sibling starts clean.
            try:
                buf = getattr(process, "_capture_buffer", "")
                if buf:
                    process.log(buf)
            except Exception:
                pass
            finally:
                process._capture_buffer = ""
            if stack[-1] is process:
                stack.pop()
            else:
                stack.remove(process)
            with cls._lock:
                cls._active_count -= 1
                if cls._active_count <= 0:
                    cls._active_count = 0
                    cls._uninstall()


_renderer = None


def _get_renderer():
    global _renderer
    if _renderer is None:
        _renderer = Renderer(sys.stdout)
    return _renderer


class Process:
    def __init__(self, label, parent=None, renderer=None):
        from .tree import TreeNode

        self.renderer = renderer or _get_renderer()
        self._node = TreeNode(label, parent, self.renderer)
        self._capture_buffer = ""

    def __enter__(self):
        CaptureStream._push(self)
        self._capture_buffer = ""
        self._node.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        CaptureStream._pop(self)
        if self._node.state == "running":
            if exc_type:
                self._node.fail(str(exc) if exc else "")
            else:
                self._node.complete()
        if self._node.parent is None:
            self.renderer.leave_cursor()
        return False

    def log(self, message):
        self._node.log(str(message))

    def child(self, label):
        return Process(label, parent=self._node, renderer=self.renderer)