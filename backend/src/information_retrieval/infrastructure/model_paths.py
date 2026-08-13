from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def resolve_model_dir(configured_path: Path) -> Path:
    """Anchor relative model caches to backend so every entry point loads identical artifacts."""
    if configured_path.is_absolute():
        return configured_path.resolve()
    return (_BACKEND_ROOT / configured_path).resolve()
