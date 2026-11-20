import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TITLE='API 文档的签名、参数与继承信息聚合'
def main():
    core=json.loads((ROOT/'outputs/core_manifest.json').read_text(encoding='utf-8')); attention=[]
    for name,r in core['components'].items():
        if r.get('blocked') is True or any(r.get(k) is False for k in ['complete','checkout','committed','ok']) or any(bool(r.get(k)) for k in ['unavailable','missing','conflicts','unreachable']):attention.append(name)
    report=dict(title=TITLE,component_count=len(core['components']),sha256=hashlib.sha256(json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),attention=sorted(attention))
    (ROOT/'outputs/final_report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
if __name__=='__main__':main()
