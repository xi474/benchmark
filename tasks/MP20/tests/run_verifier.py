"""Shared Harbor verifier entrypoint. Writes the official weighted reward."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from score_attempt import evaluate


def write(path, text):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(text,encoding="utf-8")
    tmp.replace(path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,default=Path("/app"))
    parser.add_argument("--logs",type=Path,default=Path("/logs/verifier"))
    args=parser.parse_args()
    here=Path(__file__).resolve().parent
    here.chmod(0o700)
    reg=json.loads((here/"release-registry.json").read_bytes())
    args.logs.mkdir(parents=True,exist_ok=True)
    for name in ("reward.txt","score.json","raw-checks.json"):
        (args.logs/name).unlink(missing_ok=True)
    violations=[str(p.relative_to(args.workspace)) for p in args.workspace.rglob("*") if p.is_symlink()]
    if reg["family"]=="component":
        protected=json.loads((here/"registry.json").read_bytes())["protected"]
    elif reg["family"]=="blind":
        protected=json.loads((here/"dataset/verifier/catalog.json").read_bytes())["tasks"][reg["task"]]["protected"]
    else:
        protected={}
    for name,digest in protected.items():
        p=args.workspace/name
        if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
            violations.append(name)
    if violations:
        raw=dict(task=reg["task"],integrity_ok=False,checks=[],protected_violations=sorted(set(violations)),
                 schema="upstream59.modular-probes.v1" if reg["family"]=="modular" else "upstream59.integrity.v1")
    elif reg["family"]=="modular":
        from mp_grade import grade
        raw=grade(here,args.workspace.resolve(),json.loads((here/"vectors.json").read_bytes()))
    else:
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"raw.json"
            if reg["family"]=="component":
                cmd=[here/"score.py","--registry",here/"registry.json","--cases",here/"cases.json"]
            else:
                cmd=[here/"dataset/verifier/score.py","--package",here/"dataset","--task",reg["task"]]
            subprocess.run([sys.executable,*cmd,"--workspace",args.workspace,"--json-output",path,
                            "--reward-output",Path(temp)/"native.txt"],check=True)
            raw=json.loads(path.read_bytes())
    result=evaluate(reg,raw)
    if result["status"]!="scored":
        raise ValueError("Incomplete verifier receipt")
    for name,obj in (("raw-checks.json",raw),("score.json",result)):
        write(args.logs/name,json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    write(args.logs/"reward.txt",result["reward"]+"\n")


if __name__=="__main__":
    main()
