import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    if (ROOT/'materialize.py').is_file():subprocess.run([sys.executable,str(ROOT/'materialize.py')],cwd=ROOT,check=True)
    pending=[p for p in ROOT.rglob('contract.json') if 'outputs' not in p.relative_to(ROOT).parts]
    done=set()
    # Only outputs produced by this invocation satisfy a dependency.
    while pending:
        progress=False
        for cp in pending[:]:
            c=json.loads(cp.read_text(encoding='utf-8'))
            if not all((ROOT/x).is_file() and (not x.startswith('outputs/') or x in done) for x in c['inputs']):continue
            subprocess.run([sys.executable,str(cp.with_name('render.py'))],cwd=ROOT,check=True,timeout=30)
            done.add(c['output']);pending.remove(cp);progress=True
        if not progress:raise ValueError('missing dependency or cyclic contracts')
    subprocess.run([sys.executable,str(ROOT/'integrate.py')],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'final_report.py')],cwd=ROOT,check=True)
if __name__=='__main__':main()
