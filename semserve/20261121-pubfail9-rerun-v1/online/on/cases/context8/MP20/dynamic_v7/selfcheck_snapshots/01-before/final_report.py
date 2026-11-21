"""Build the final report from the integrated core manifest.

Reads ``outputs/core_manifest.json`` (the complete core object) and writes
``outputs/final_report.json`` with exactly the fields ``title``,
``component_count``, ``sha256`` and ``attention``.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TITLE = "特性配置的模式、附件与引用一致性"


def _attention(components):
    """Return sorted unique component names that satisfy any attention rule."""
    names = set()
    for name, result in components.items():
        if not isinstance(result, dict):
            continue
        if result.get("blocked") is True:
            names.add(name)
            continue
        for key in ("complete", "checkout", "committed", "ok"):
            if result.get(key) is False:
                names.add(name)
                break
        else:
            for key in ("unavailable", "missing", "conflicts", "unreachable"):
                value = result.get(key)
                if value not in (None, "", [], {}):
                    names.add(name)
                    break
    return sorted(names)


def main():
    core_path = ROOT / "outputs" / "core_manifest.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))
    components = core["components"]

    serialized = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    sha256 = hashlib.sha256(serialized).hexdigest()

    report = {
        "title": TITLE,
        "component_count": len(components),
        "sha256": sha256,
        "attention": _attention(components),
    }

    out_path = ROOT / "outputs" / "final_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
