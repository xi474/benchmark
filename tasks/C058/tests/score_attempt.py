"""Score a frozen verifier receipt with the release registry. Uses only stdlib."""
import argparse
import json
from pathlib import Path
from workspace_reward import POLICY, SCORING_REVISION, task_reward


def evaluate(reg, raw):
    units = reg["units"]
    n = len(units)
    weight = reg["reward_difficulty"]
    identity = reg["task"]
    unknown = dict(task=identity, benchmark_version="2.0.0", scoring_revision=SCORING_REVISION,
                   reward_difficulty=weight, empirical_difficulty=reg["empirical_difficulty"],
                   max_reward=POLICY["difficulty_max_reward"][weight], total_verifiers=n,
                   integrity_ok=None, public_pass=None, strict_pass=None, passed_verifiers=None,
                   core_transform_cases_total=sum(u["group"]=="A" for u in units),
                   core_transform_cases_passed=None, core_transform_case_pass_rate=None,
                   reward=None, robustness_all_passed=None, full_spec_pass=None, checks=None)
    if raw is None:
        return dict(unknown,status="missing_receipt")
    legacy_name={"benchmark.partial-reward.v2":"medium/","adapted6.core-reward.v3":"core6/"}.get(raw.get("schema"))
    if reg["family"]=="modular" and legacy_name and raw.get("task")==legacy_name+identity:
        if raw.get("integrity_ok") is not False:
            return dict(unknown,status="incompatible_historical_evidence",
                        reason="Legacy probes do not separately establish both clean builds and direct transform outcomes.")
        raw=dict(task=identity,schema="upstream59.modular-probes.v1",integrity_ok=False,checks=[])
    if raw.get("task") != identity:
        raise ValueError("Receipt belongs to a different task or verifier version")
    if reg["family"]=="modular" and raw.get("schema")!="upstream59.modular-probes.v1":
        raise ValueError("This release requires independent modular probe evidence")
    integrity = raw.get("integrity_ok", raw.get("integrity_pass"))
    if type(integrity) is not bool or not isinstance(raw.get("checks"),list):
        return dict(unknown,status="missing_scoring_evidence")
    if integrity and not raw["checks"]:
        return dict(unknown,status="missing_scoring_evidence")
    if reg["family"]=="blind" and integrity and raw.get("registry_sha256")!=reg["native_registry_sha256"]:
        raise ValueError("Blind verifier registry mismatch")
    known = {k for u in units for k in u["inputs"]}
    observed = {}
    for item in raw["checks"]:
        name = item["id"]
        if name in observed or name not in known or type(item["passed"]) is not bool:
            raise ValueError("Invalid, duplicate or unregistered check: "+name)
        observed[name]=item["passed"]
    results = [dict(id=u["id"],category=u["group"],passed=integrity and
                    all(observed.get(k,False) for k in u["inputs"])) for u in units]
    passed=sum(x["passed"] for x in results)
    strict=integrity and passed==n
    public=next(x["passed"] for x in results if x["category"]=="P")
    a=sum(x["passed"] for x in results if x["category"]=="A")
    reward=task_reward(difficulty=weight,passed=passed,total=n,strict_pass=strict,integrity_ok=integrity)
    robust=raw.get("robustness_all_passed")
    return dict(unknown,status="scored",integrity_ok=integrity,public_pass=public,strict_pass=strict,
                passed_verifiers=passed,core_transform_cases_passed=a,
                core_transform_case_pass_rate=a/unknown["core_transform_cases_total"],
                reward=str(reward),checks=results,robustness_all_passed=robust,
                full_spec_pass=None if robust is None else strict and robust)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry",type=Path,required=True)
    parser.add_argument("--receipt",type=Path,required=True)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    raw=json.loads(args.receipt.read_bytes()) if args.receipt.is_file() else None
    data=evaluate(json.loads(args.registry.read_bytes()),raw)
    text=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    if args.out:
        args.out.write_text(text,encoding="utf-8")
    else:
        print(text,end="")


if __name__=="__main__":
    main()
