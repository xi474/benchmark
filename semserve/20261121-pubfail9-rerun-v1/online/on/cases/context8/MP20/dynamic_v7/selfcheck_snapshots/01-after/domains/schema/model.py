import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "root_model", _ROOT / "model.py"
)
_root_model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_model)


def load_payload(path):
    return _root_model.load_payload(path)
