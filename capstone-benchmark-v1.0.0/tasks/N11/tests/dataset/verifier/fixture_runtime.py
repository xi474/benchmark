"""Visible task I/O helpers. This file contains no answer implementation."""
import importlib.util
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pointer(value, path):
    for part in path.strip("/").split("/") if path.strip("/") else []:
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def payload_for(root, contract):
    result = {}
    for key, binding in contract["bindings"].items():
        filename, _, fragment = binding.partition("#")
        result[key] = pointer(read(Path(root) / filename), fragment)
    if contract.get("runtime_root"):
        result["_root"] = str(Path(root).resolve())
    return result


def emit(root, contract, value):
    root = Path(root)
    target = root / contract["output"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+"\n", encoding="utf-8")
    for name, item in contract.get("emit", {}).items():
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = pointer(value, item["pointer"])
        if item["format"] == "text":
            dest.write_text(content, encoding="utf-8", newline="")
        elif item["format"] == "base64":
            import base64
            dest.write_bytes(base64.b64decode(content))
        elif item["format"] == "npy":
            import numpy as np
            np.save(dest, np.asarray(content, dtype=float))
        elif item["format"] == "json":
            dest.write_text(json.dumps(content, ensure_ascii=False, allow_nan=False, indent=2)+"\n",encoding="utf-8")
        elif item["format"] == "ics":
            lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Medium30//EN','BEGIN:VEVENT','DTSTART:'+content['start'],'DTEND:'+content['end'],'SUMMARY:'+content['summary']]
            lines += ['ATTENDEE:mailto:'+x for x in content['attendees']]
            dest.write_text('\n'.join(lines+['END:VEVENT','END:VCALENDAR'])+'\n',encoding='utf-8')
    return value


def build(root, contract, transform):
    return emit(root, contract, transform(payload_for(root, contract), contract))


def module(root, name):
    filename = Path(root) / name
    spec = importlib.util.spec_from_file_location("candidate_"+str(abs(hash(str(filename)))), filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def execute(root):
    root = Path(root)
    config = read(root / "workflow.json")
    results = {}
    for component in config["components"]:
        contract = read(root / component["folder"] / "contract.json")
        api = module(root, component["folder"]+"/engine.py")
        results[component["name"]] = api.build_component(root, contract)
    report = {"task":config["id"], "results":results, "result":results[config["components"][-1]["name"]]}
    (root/"outputs").mkdir(exist_ok=True)
    (root/"outputs/final_report.json").write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2)+"\n",encoding="utf-8")
    return report


def run_deploy(hook, routes, batches):
    """Local Git test plumbing. Routing/deployment behavior comes from hook."""
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    with tempfile.TemporaryDirectory(prefix='medium30-git-deploy-') as td:
        base=Path(td);bare=base/'remote.git';work=base/'working';deployment=base/'deployed';work.mkdir();deployment.mkdir()
        def git(args,cwd):
            result=subprocess.run(['git',*args],cwd=cwd,capture_output=True,text=True,env={**os.environ,'MEDIUM30_DEPLOY_ROOT':str(deployment)})
            if result.returncode:raise RuntimeError('Git plumbing: '+result.stderr[-1200:])
            return result.stdout
        git(['init','--bare','-q',str(bare)],base);git(['init','-q'],work);git(['config','user.name','Fixture'],work);git(['config','user.email','fixture@example.invalid'],work)
        script=bare/'hooks/business.py';script.write_text(hook,encoding='utf-8')
        shim=bare/'hooks/post-receive';shim.write_text('#!/bin/sh\nexec "'+sys.executable+'" "'+str(script)+'"\n',encoding='utf-8');shim.chmod(0o755)
        known=set()
        for batch in batches:
            names=[]
            for update in batch:
                branch=update['branch']
                git(['checkout','-q',branch] if branch in known else ['checkout','-q','--orphan',branch],work);known.add(branch)
                for child in work.iterdir():
                    if child.name=='.git':continue
                    if child.is_dir() and not child.is_symlink():
                        assert child.resolve().is_relative_to(work.resolve())
                        shutil.rmtree(child)
                    else:child.unlink()
                for name,content in update['files'].items():
                    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8')
                git(['add','-A'],work);git(['commit','-q','--allow-empty','-m','update '+branch],work);names.append(branch)
            git(['push','-q',str(bare),*[name+':refs/heads/'+name for name in names]],work)
        return dict(files={p.relative_to(deployment).as_posix():p.read_text(encoding='utf-8') for p in deployment.rglob('*') if p.is_file()})
