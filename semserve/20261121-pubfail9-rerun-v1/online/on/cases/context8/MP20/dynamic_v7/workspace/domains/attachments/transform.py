import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "root_transform", _ROOT / "transform.py"
)
_root_transform = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_transform)


def transform(payloads, contract):
    return _root_transform.transform(payloads, contract)
