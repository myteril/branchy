# Contributing

Thanks for considering contributing to branchy.

## Development setup

```bash
git clone <repo-url>
cd branchy
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Running the demo

```bash
python demo.py
```

## Style guidance

- Keep changes small and focused on one thing.
- Prefer the standard library; do not add new dependencies unless required.
- Avoid introducing abstractions, fixtures, or boilerplate.
- Non-trivial logic should include the smallest runnable self-check.

## Submitting changes

Open an issue to discuss larger changes. For small fixes, open a pull request with a clear description of the problem and the fix.
