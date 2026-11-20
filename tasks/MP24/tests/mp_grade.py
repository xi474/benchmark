"""Run registered probes in temporary candidate workspaces under separate Linux UIDs."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

DEADLINE_SECONDS=1450


def equal(a,b):
    if type(a) in (int,float) and type(b) in (int,float):
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)
    if type(a)!=type(b):
        return False
    if isinstance(a,dict):
        return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,list):
        return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b


def protected(w, spec, generated_required=False):
    for key, accepted in spec["protected_initial"].items():
        p=w/key
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() not in accepted:
            return False
    for key, accepted in spec["protected_generated"].items():
        p=w/key
        if p.is_symlink() or ((generated_required or p.exists()) and
            (not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() not in accepted)):
            return False
    return True


def own(w,uid):
    for p in [w,*w.rglob("*")]:
        os.chown(p,uid,uid,follow_symlinks=False)
    w.chmod(0o700)


def invoke(w,uid,script,deadline,packet=None):
    def demote():
        os.setgroups([])
        os.setgid(uid)
        os.setuid(uid)
    remaining=deadline-time.monotonic()
    if remaining<=0:
        return False,None
    try:
        p=subprocess.run([sys.executable,"-B",str(script)],cwd=w,env={"PATH":os.defpath,"HOME":str(w),
            "PYTHONIOENCODING":"utf-8"},input=json.dumps(packet,ensure_ascii=False) if packet else None,
            capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=min(remaining,220 if packet is None else 45),
            preexec_fn=demote)
        if p.returncode:
            return False,None
        return True,json.loads(p.stdout) if packet else None
    except (ValueError,OSError,subprocess.TimeoutExpired):
        return False,None


def grade(tests, workspace, spec):
    deadline=time.monotonic()+DEADLINE_SECONDS
    uid=60101
    checks=[]
    optional=[]
    intact=not any(p.is_symlink() for p in workspace.rglob("*")) and protected(workspace,spec)
    with tempfile.TemporaryDirectory(prefix="upstream59-") as name:
        tmp=Path(name)
        tmp.chmod(0o711)
        probe=tmp/"invoke.py"
        shutil.copyfile(tests/"mp_probe.py",probe)
        probe.chmod(0o444)
        clean=tmp/"clean"
        if intact:
            shutil.copytree(workspace,clean,ignore=shutil.ignore_patterns("outputs","__pycache__",".git"))
            own(clean,uid)
            if (clean/"materialize.py").is_file():
                invoke(clean,uid,clean/"materialize.py",deadline)
            intact=protected(clean,spec,True)
        public=False
        if intact:
            delivery=tmp/"delivery"
            shutil.copytree(clean,delivery)
            own(delivery,uid+1)
            public=invoke(delivery,uid+1,delivery/"check.py",deadline)[0]
            intact=protected(delivery,spec,True)
        for c in sorted(spec["checks"],key=lambda c:bool(c.get("optional"))):
            kind=c["kind"]
            ok=False
            if intact and kind in ("api","io") and time.monotonic()<deadline:
                answers=[]
                for case,expected in c["vectors"]:
                    uid+=2
                    with tempfile.TemporaryDirectory(dir=tmp) as dst:
                        w=Path(dst)
                        shutil.copytree(clean,w,dirs_exist_ok=True)
                        own(w,uid)
                        success,value=invoke(w,uid,probe,deadline,dict(kind=kind,case=json.loads(case),folder=c["folder"],suite=c["suite"]))
                        answers.append(success and equal(value,expected))
                        if not protected(w,spec,True):
                            answers[-1]=False
                            if not c.get("optional"):
                                intact=False
                            break
                ok=intact and all(answers)
            elif intact and kind=="output":
                f=delivery/c["path"]
                try:
                    if f.is_file() and not f.is_symlink() and delivery in f.resolve().parents:
                        contents=f.read_text(encoding="utf-8")
                        v=json.loads(contents)
                        ok=equal(v,c["expected"]) and contents==json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+"\n"
                except (ValueError,OSError):
                    pass
            elif kind=="public":
                ok=public
            dest=optional if c.get("optional") else checks
            dest.append(dict(id=c["id"],passed=bool(ok)))
    return dict(schema="upstream59.modular-probes.v1", task=spec["task"],integrity_ok=intact,
        checks=checks,robustness_checks=optional,
        robustness_all_passed=bool(intact and all(x["passed"] for x in optional)) if optional else None)
