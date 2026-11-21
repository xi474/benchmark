import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TITLE = 'API 文档的签名、参数与继承信息聚合'


def _attention(components):
    names = set()
    for name, result in components.items():
        if not isinstance(result, dict):
            continue
        if result.get('blocked') is True:
            names.add(name)
        for key in ('complete', 'checkout', 'committed', 'ok'):
            if result.get(key) is False:
                names.add(name)
        for key in ('unavailable', 'missing', 'conflicts', 'unreachable'):
            v = result.get(key)
            if v is not None and v != [] and v != {} and v != '' and v != 0:
                names.add(name)
    return sorted(names)


def main():
    core_path = ROOT / 'outputs' / 'core_manifest.json'
    core = json.loads(core_path.read_text(encoding='utf-8'))
    components = core['components']

    serialized = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
        allow_nan=False,
    ).encode('utf-8')
    sha256 = hashlib.sha256(serialized).hexdigest()

    report = {
        'title': TITLE,
        'component_count': len(components),
        'sha256': sha256,
        'attention': _attention(components),
    }

    out = ROOT / 'outputs' / 'final_report.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
