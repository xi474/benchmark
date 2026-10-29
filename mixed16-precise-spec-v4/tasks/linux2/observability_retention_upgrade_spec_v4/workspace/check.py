import json,subprocess,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    out=ROOT/'outputs'
    if out.is_symlink(): raise ValueError('outputs must not be a symlink')
    if out.exists(): shutil.rmtree(out)
    if (ROOT/'materialize.py').exists(): subprocess.run([sys.executable,str(ROOT/'materialize.py')],cwd=ROOT,check=True,timeout=20)
    for name in ['run_all.py','final_report.py']:
        assert (ROOT/name).is_file(), 'missing implementation: '+name
    subprocess.run([sys.executable,str(ROOT/'run_all.py')],cwd=ROOT,check=True,timeout=120)
    contracts=sorted(ROOT.rglob('contract.json'))
    assert contracts, 'no contracts'
    for path in contracts:
        c=json.loads(path.read_text(encoding='utf-8'))
        value=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))
        assert set(value)=={'name','result'} and value['name']==c['name'] and isinstance(value['result'],dict)
        subprocess.run([sys.executable,str(path.with_name('check_module.py'))],cwd=path.parent,check=True,timeout=20)
    report=json.loads((ROOT/'outputs/final_report.json').read_text(encoding='utf-8'))
    assert report['component_count']==len(contracts)
    assert len(report['sha256'])==64 and isinstance(report['attention'],list)
    print('LOCAL_CHECKS_PASSED; official scoring requires the external verifier')
if __name__=='__main__': main()
