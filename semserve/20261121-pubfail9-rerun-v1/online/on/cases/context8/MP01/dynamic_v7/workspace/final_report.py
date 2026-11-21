import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    p.write_text(text, encoding="utf-8")


def main():
    core_path = ROOT / "outputs" / "core_manifest.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))
    components = core["components"]

    serialized = json.dumps(
        core, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    sha256 = hashlib.sha256(serialized).hexdigest()

    attention = []
    for name, result in components.items():
        if not isinstance(result, dict):
            continue
        if result.get("blocked") is True:
            attention.append(name)
            continue
        for key in ("complete", "checkout", "committed", "ok"):
            if result.get(key) is False:
                attention.append(name)
                break
        else:
            for key in ("unavailable", "missing", "conflicts", "unreachable"):
                v = result.get(key)
                if isinstance(v, (list, dict, str, tuple)) and len(v) > 0:
                    attention.append(name)
                    break

    report = {
        "title": "可关闭成员的硬/软加权投票",
        "component_count": len(components),
        "sha256": sha256,
        "attention": sorted(set(attention)),
    }
    _write_json(ROOT / "outputs" / "final_report.json", report)


if __name__ == "__main__":
    main()
