"""Aggregate a single 59-task cohort from Harbor verifier receipts."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
from score_attempt import evaluate


def summarize(catalog, outcomes):
    valid=[r for r in outcomes if r["reward"] is not None]
    covered=len(valid)
    strict=sum(r["strict_pass"] for r in valid)
    earned=sum((Decimal(r["reward"]) for r in valid),Decimal("0.000000"))
    a=sum(r["core_transform_cases_passed"] for r in valid)
    n=sum(r["core_transform_cases_total"] for r in valid)
    complete=covered==len(catalog["tasks"])
    return dict(version=catalog["version"],scoring_revision=catalog["scoring_revision"],
                total_tasks=len(catalog["tasks"]),scored_tasks=covered,
                unknown_ids=[r["task"] for r in outcomes if r["reward"] is None],
                public_pass_count=sum(r["public_pass"] for r in valid),strict_pass_count=strict,
                strict_pass_rate=strict/covered if complete else None,
                strict_pass_rate_on_scored=strict/covered if covered else None,
                reward_total=str(earned) if complete else None,reward_sum_on_scored=str(earned),
                max_reward_on_scored=sum(r["max_reward"] for r in valid),max_reward_total=catalog["max_total_reward"],
                core_transform_passed_on_scored=a,core_transform_total_on_scored=n,
                core_transform_micro_rate_on_scored=a/n if n else None)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort",type=Path,help="One harness/model/repeat job directory containing raw-checks.json files")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if not args.cohort.is_dir():
        parser.error("Cohort directory does not exist")
    root=Path(__file__).resolve().parent.parent
    cat=json.loads((root/"catalog.json").read_bytes())
    allowed={r["id"] for r in cat["tasks"]}
    receipts={}
    for path in sorted(args.cohort.rglob("raw-checks.json")):
        raw=json.loads(path.read_bytes())
        tid=raw.get("task")
        if tid not in allowed:parser.error(f"Unexpected task in {path}")
        if tid in receipts:parser.error(f"Duplicate {tid}; select a single cohort or repeat")
        receipts[tid]=raw
    rows=[]
    for task in cat["tasks"]:
        reg=json.loads((root/task["registry"]).read_bytes())
        result=evaluate(reg,receipts.get(task["id"]))
        rows.append({k:v for k,v in result.items() if k!="checks"})
    output=json.dumps(dict(summary=summarize(cat,rows),tasks=rows),ensure_ascii=False,indent=2)+"\n"
    if args.out:args.out.write_text(output,encoding="utf8")
    else:print(output,end="")


if __name__=="__main__":
    main()
