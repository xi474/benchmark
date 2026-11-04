import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES=('plant_crews', 'line_shutdown', 'plant_resilience')
def main():
    rs={}
    for name in NAMES:
        s=importlib.util.spec_from_file_location('render_'+name,ROOT/'engines'/name/'render.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);rs[name]=m.build()
    p=ROOT/'outputs/final_report.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(rs,sort_keys=True,allow_nan=False,indent=2)+'\n')
if __name__=='__main__':main()
