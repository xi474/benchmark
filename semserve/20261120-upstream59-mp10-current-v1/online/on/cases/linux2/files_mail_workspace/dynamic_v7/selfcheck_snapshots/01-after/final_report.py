import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    core_path = ROOT / "outputs" / "core_manifest.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))

    components = core["components"]
    component_count = len(components)

    serialized = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
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
                if isinstance(v, (list, dict, str)) and len(v) > 0:
                    attention.append(name)
                    break

    attention = sorted(set(attention))

    report = {
        "title": "下载目录归档、邮件清理与目标回复",
        "component_count": component_count,
        "sha256": sha256,
        "attention": attention,
    }

    out = ROOT / "outputs" / "final_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
