from __future__ import annotations

import time

from dataclasses import dataclass, field


@dataclass
class TreeNode:
    label: str
    parent: TreeNode | None = None
    renderer: object | None = None
    state: str = "pending"
    depth: int = field(init=False)
    children: list = field(default_factory=list)
    logs: list = field(default_factory=list)
    show_elapsed: bool = False
    started: float | None = None
    duration: float | None = None

    def __post_init__(self):
        self.depth = (self.parent.depth if self.parent else -1) + 1
        if self.parent:
            self.parent.children.append(self)
        if self.renderer:
            self.renderer.register(self)

    def start(self):
        self.state = "running"
        self.started = time.monotonic()
        if self.renderer:
            self.renderer.start_node(self)

    def log(self, message: str):
        self.logs.append(message)
        if self.renderer:
            self.renderer.log(self, message)

    def rename(self, label: str):
        if self.state in ("done", "failed"):
            return
        self.label = label
        if self.renderer:
            self.renderer.rename(self)

    def complete(self):
        self.duration = time.monotonic() - self.started
        self.logs.clear()
        self.state = "done"
        if self.renderer:
            self.renderer.set_state(self)

    def fail(self, reason: str = ""):
        if reason:
            self.logs.append(reason)
        self.duration = time.monotonic() - self.started
        self.state = "failed"
        if self.renderer:
            self.renderer.set_state(self)
