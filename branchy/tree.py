from __future__ import annotations

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

    def __post_init__(self):
        self.depth = (self.parent.depth if self.parent else -1) + 1
        if self.parent:
            self.parent.children.append(self)
        if self.renderer:
            self.renderer.register(self)

    def start(self):
        self.state = "running"
        if self.renderer:
            self.renderer.start_node(self)

    def log(self, message: str):
        self.logs.append(message)
        if self.renderer:
            self.renderer.log(self, message)

    def complete(self):
        self.logs.clear()
        self.state = "done"
        if self.renderer:
            self.renderer.set_state(self)

    def fail(self, reason: str = ""):
        if reason:
            self.logs.append(reason)
        self.state = "failed"
        if self.renderer:
            self.renderer.set_state(self)
