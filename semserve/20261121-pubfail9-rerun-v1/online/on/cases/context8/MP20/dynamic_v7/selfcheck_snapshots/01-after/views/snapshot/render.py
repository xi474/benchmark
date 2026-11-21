import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "root_render", _ROOT / "render.py"
)
_root_render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_render)


def build_component(root, contract_path):
    return _root_render.build_component(root, contract_path)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    build_component(root, here / "contract.json")
