"""Verify the published file checksums and sealed task-package byte identities."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['tasks'])==len({t['id'] for t in manifest['tasks']})==20
    count=0
    for line in (ROOT/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        expected,name=line.split('  ',1);path=(ROOT/name).resolve()
        assert path.is_relative_to(ROOT) and path.is_file() and digest(path)==expected,name
        count+=1
    sealed=0
    for folder,hashes in manifest['frozen_packages'].items():
        actual={p.relative_to(ROOT/folder).as_posix():digest(p) for p in (ROOT/folder).rglob('*') if p.is_file()}
        assert actual==hashes,folder
        sealed+=len(actual)
    result=json.loads((ROOT/'_authoring/results/index.json').read_text(encoding='utf-8'))
    assert len(result['rows'])==100
    for r in result['rows']:assert digest(ROOT/r['score'])==r['score_sha256']
    print(json.dumps(dict(status='passed',files=count,sealed_files=sealed,tasks=20,trials=100)))
if __name__=='__main__':main()
