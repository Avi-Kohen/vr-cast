# vr-cast

## v1 scope
- Windows + macOS (Apple Silicon)
- USB only
- 1 device at a time
- Read-only: `--no-control`
- PC audio always off: `--no-audio`
- scrcpy bundled
- ADB (platform-tools) user-supplied:
  - Place `platform-tools/` next to the app, or browse to it.

## Dev run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS:   source .venv/bin/activate
pip install -e .
python -m loginvrcast


---

# 3) Package code

## `src/loginvrcast/__init__.py`

```python
__all__ = ["__version__"]
__version__ = "0.1.0"