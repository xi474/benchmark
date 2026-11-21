import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TITLE = "每日晚餐提醒的去重、冲突取消与通知"


def _load_core():
    path = ROOT / "outputs" / "core_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(core):
    text = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _attention(components):
    names = []
    for name, result in components.items():
        if not isinstance(result, dict):
            continue
        if result.get("blocked") is True:
            names.append(name)
            continue
        for key in ("complete", "checkout", "committed", "ok"):
            if result.get(key) is False:
                names.append(name)
                break
        else:
            for key in ("unavailable", "missing", "conflicts", "unreachable"):
                v = result.get(key)
                if isinstance(v, (list, dict, str)) and v:
                    names.append(name)
                    break
    return sorted(set(names))


def build_report(core):
    components = core["components"]
    return {
        "title": TITLE,
        "component_count": len(components),
        "sha256": _sha256(core),
        "attention": _attention(components),
    }


def main():
    core = _load_core()
    report = build_report(core)
    out = ROOT / "outputs" / "final_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
