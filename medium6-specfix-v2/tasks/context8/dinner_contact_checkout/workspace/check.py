import json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    out=ROOT/'outputs'
    if out.is_symlink() or out.resolve().parent!=ROOT: raise ValueError('unsafe outputs')
    if out.exists(): shutil.rmtree(out)
    if (ROOT/'materialize.py').is_file(): subprocess.run([sys.executable,str(ROOT/'materialize.py')],cwd=ROOT,check=True,timeout=30)
    subprocess.run([sys.executable,str(ROOT/'run_all.py')],cwd=ROOT,check=True,timeout=180)
    contracts=[x for x in ROOT.rglob('contract.json') if 'outputs' not in x.relative_to(ROOT).parts]
    assert contracts,'no contracts'
    for cp in contracts: subprocess.run([sys.executable,str(cp.with_name('check_module.py'))],cwd=ROOT,check=True,timeout=30)
    core=json.loads((out/'core_manifest.json').read_text(encoding='utf-8')); report=json.loads((out/'final_report.json').read_text(encoding='utf-8'))
    assert set(core)=={'components'} and len(core['components'])==len(contracts)
    assert set(report)=={'title','component_count','sha256','attention'} and report['component_count']==len(contracts) and len(report['sha256'])==64
    print('LOCAL_CHECKS_PASSED; external verifier determines official correctness')
if __name__=='__main__': main()
