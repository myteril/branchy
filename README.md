# branchy

Live, hierarchical console process trees for Python, with zero dependencies.

[![PyPI](https://img.shields.io/pypi/v/branchy.svg)](https://pypi.org/project/branchy/) [![Python versions](https://img.shields.io/badge/python-3.8%2B-blue)]() [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

## Visual sample

A successful run collapses to a calm, depth-styled tree:

```text
✓ Deploy
  ✓ Validate
  ✓ Build
    ✓ Compile
    ✓ Link
```

A failed run keeps the transient logs visible:

```text
✗ Publish
  starting upload
  ✗ Sign package
    private key not found
```

## Installation

```bash
pip install branchy
```

## Quick start

```python
from branchy import process
import time

with process("Build") as build:
    with build.child("Compile") as c:
        c.log("gcc main.c")
        time.sleep(0.5)
    with build.child("Link") as l:
        l.log("ld -o app")
        time.sleep(0.3)
```

## API usage

`process(label)` starts a root context. Inside the body:

- `p.log(message)` appends transient output under the current node.
- `p.child(label)` creates a nested process.
- Clean exit marks the node done and clears its transient logs.
- Exception exit marks the node failed, keeps the logs, appends the exception message, and re-raises the exception.

Both `process` and `child` are context managers.

## Output lifecycle

Logs are temporary detail. They disappear once a branch succeeds, but remain visible on failure so the reason can be seen.

During a running branch:

```text
⠋ Build
  compiling…
    ⠙ Compile
      gcc main.c
```

After success:

```text
✓ Build
  ✓ Compile
```

After failure:

```text
✗ Build
  compiling…
    ✗ Compile
      gcc main.c
      error: implicit declaration
```

## Environment / behavior

| Variable / condition | Effect |
|---|---|
| `NO_COLOR` set | No color styling; cursor movement still works in a TTY. |
| `TERM=dumb` | Plain ASCII output, no ANSI cursor control. |
| stdout not a TTY | Static output; no animation; transient logs are not erased. |
| `COLUMNS` | Fallback terminal width when it cannot be queried from the OS. |

## Examples

### Nested success tree

```python
from branchy import process
import time

with process("Deploy") as deploy:
    with deploy.child("Validate") as v:
        v.log("schema ok")
        time.sleep(0.2)

    with deploy.child("Build") as b:
        with b.child("Compile") as c:
            c.log("gcc -O2 main.c")
            time.sleep(0.3)
        with b.child("Link") as l:
            l.log("ld -o app")
            time.sleep(0.3)
```

### Failure handling

```python
from branchy import process

try:
    with process("Publish") as p:
        p.log("starting upload")
        with p.child("Sign package") as s:
            s.log("private key not found")
            raise RuntimeError("signing failed")
except RuntimeError as exc:
    print(f"Expected failure captured: {exc}")
```

## Limitations

- Designed for small trees; rendering is `O(number of live rows)` per frame.
- Wide-character widths are best-effort via Unicode East Asian Width and combining-mark handling.
- The library intentionally does not persist logs, show progress percentages, or provide pluggable themes.