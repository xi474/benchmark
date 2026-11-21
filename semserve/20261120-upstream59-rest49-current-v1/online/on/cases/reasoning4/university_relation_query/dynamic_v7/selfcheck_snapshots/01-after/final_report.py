import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    core_path = ROOT / "outputs" / "core_manifest.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))
    components = core["components"]

    attention = []
    for name in sorted(components):
        result = components[name]
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
                if isinstance(v, (list, dict, str)) and len(v) > 0:
                    attention.append(name)
                    break

    serialized = json.dumps(
        core, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    sha = hashlib.sha256(serialized).hexdigest()

    report = {
        "title": "大学任职、在读人数与国家集合查询",
        "component_count": len(components),
        "sha256": sha,
        "attention": sorted(set(attention)),
    }

    out = ROOT / "outputs" / "final_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
