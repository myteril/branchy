import sys

from .renderer import Renderer


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

    def __enter__(self):
        self._node.start()
        return self

    def __exit__(self, exc_type, exc, tb):
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
