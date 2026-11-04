import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES=('track_access', 'rail_crews', 'rail_spares')
def main():
    for name in NAMES:subprocess.run([sys.executable,'engines/'+name+'/check_module.py'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'run_all.py'],cwd=ROOT,check=True)
    final=json.loads((ROOT/'outputs/final_report.json').read_text());assert set(final)==set(NAMES)
    for name in NAMES:assert json.loads((ROOT/'outputs'/(name+'.json')).read_text())==dict(name=name,result=final[name])
    print('LOCAL_CHECKS_PASSED')
if __name__=='__main__':main()
