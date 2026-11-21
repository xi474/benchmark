"""Component renderer: read inputs, transform, and write the contract output.

``build_component`` reads the contract and every input relative to ``root``,
calls ``transform``, writes the wrapped result to ``contract["output"]`` and
returns that same wrapped result.  The module also works as a CLI: running
``python3 <component_dir>/render.py`` locates the sibling ``contract.json``
and the workspace root from ``__file__`` so it works from any current
directory.
"""

import json
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    """Read inputs under ``root``, transform them, write and return the result.

    ``root`` is the workspace root against which ``contract["inputs"]`` and
    ``contract["output"]`` are resolved.  ``contract_path`` points at the
    component's ``contract.json``.
    """
    root = Path(root)
    contract_path = Path(contract_path)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    result = transform(payloads, contract)
    out_path = root / contract["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _main():
    here = Path(__file__).resolve().parent
    contract_path = here / "contract.json"
    # Components live at <root>/<domain>/<name>/render.py, so the workspace
    # root is two levels above the component directory.
    root = here.parents[1]
    build_component(root, contract_path)


if __name__ == "__main__":
    _main()
