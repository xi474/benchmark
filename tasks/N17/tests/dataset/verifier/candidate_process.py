"""Launch a blind-task probe inside its disposable work copy."""
import itertools
import os
from pathlib import Path
import shutil
import subprocess
import time

_ids=itertools.count(51000)
_deadline=time.monotonic()+1450


def candidate_run(cmd,*,cwd,**kwargs):
    remaining=_deadline-time.monotonic()
    if remaining<=0:
        raise subprocess.TimeoutExpired(cmd,0)
    kwargs["timeout"]=min(kwargs["timeout"],remaining)
    cwd=Path(cwd)
    run=cwd.parent if cwd.name=="work" else cwd
    run.parent.chmod(0o711)
    if Path(cmd[1]).name=="probe.py":
        copy=run/"probe.py"
        shutil.copyfile(cmd[1],copy)
        cmd=[cmd[0],str(copy),*cmd[2:]]
    uid=next(_ids)
    for p in [run,*run.rglob("*")]:
        os.chown(p,uid,uid,follow_symlinks=False)
    run.chmod(0o700)
    def demote():
        os.setgroups([])
        os.setgid(uid)
        os.setuid(uid)
    return subprocess.run(cmd,cwd=cwd,preexec_fn=demote,**kwargs)
