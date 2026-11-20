"""Verify a checkout or extracted ZIP. Runs offline using stdlib."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/"scoring"))
from score_attempt import evaluate
from workspace_reward import POLICY_SHA256

def main():
    read=lambda p:json.loads((root/p).read_bytes())
    cat=read("catalog.json")
    ids={r["id"] for r in cat["tasks"]}
    assert len(ids)==len(cat["tasks"])==59 and ids=={p.name for p in (root/"tasks").iterdir() if p.is_dir()}
    control=read("validation/offline.json")
    assert {t["task"] for t in control["tasks"]}==ids and len(control["tasks"])==len(ids)
    sums={}
    for line in (root/"SHA256SUMS").read_text(encoding="utf8").splitlines():
        wanted,name=line.split("  ",1)
        assert name not in sums and sha256((root/name).read_bytes()).hexdigest()==wanted,name
        sums[name]=wanted
    counts=Counter()
    for t in control["tasks"]:
        h=sha256()
        for name in sorted(n for n in sums if n.startswith("tasks/"+t["task"]+"/")):
            h.update(name.encode()+b'\0'+bytes.fromhex(sums[name]))
        assert h.hexdigest()==t["package_checksum"]
        assert t["answers"]["reference"]["strict_pass"] and not t["answers"]["starter"]["strict_pass"]
    for row in cat["tasks"]:
        tid=row["id"]
        assert row["upstream"] and all(s["id"] and s["url"] for s in row["upstream"])
        assert sums[row["registry"]]==row["registry_sha256"]
        tests=root/row["task_path"]/"tests"
        for f in ("score_attempt.py","workspace_reward.py","reward-policy-v1.0.json"):
            assert (tests/f).read_bytes()==(root/"scoring"/f).read_bytes()
        reg=read(row["registry"])
        assert reg["task"]==tid and len(reg["units"])==row["total_verifiers"]
        assert len({u["id"] for u in reg["units"]})==len(reg["units"])
        assert sum(u["group"]=="P" for u in reg["units"])==1
        assert Counter(u["group"] for u in reg["units"])==row["counts"]
        trials=read(row["historical_and_standard_scores"])
        assert [t["round"] for t in trials]==[1,2,3,4,5]
        for trial in trials:
            hist=trial["historical"]
            assert sums[hist["score"]]==hist["sha256"]
            actual=evaluate(reg,read(hist["score"]))
            assert dict((k,v) for k,v in actual.items() if k!="checks")==trial["standard"]
            counts[trial["standard"]["status"]]+=1
    assert counts==cat["historical_replay"] and sum(counts.values())==295
    assert cat["policy_sha256"]==POLICY_SHA256
    assert sum(r["max_reward"] for r in cat["tasks"])==cat["max_total_reward"]
    print(f"OK: {len(ids)} tasks, {sum(counts.values())} historical receipts, {len(sums)} file hashes")

if __name__=="__main__":
    main()
