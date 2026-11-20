import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
sys.path.insert(0,str(root/'verifier/partial_reward'))
import score,adapters
manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'));seals=json.loads((root/'verifier/protected_hashes.json').read_text(encoding='utf-8'));tasks={}
for e in manifest['entries']:
    key='core6/'+e['task_id'];row=dict(adapter='medium',entry_id=e['entry_id'],focused_folders=[],difficulty='M',
        dataset_version='3.0.0',dataset_path='',source_task='tasks/'+e['entry_id'],previous_task_key='medium/'+e['task_id'])
    seal=seals[e['entry_id']]
    row['protected_initial']={k:[v] for k,v in seal['initial'].items()}
    row['protected_generated']={k:[v] for k,v in seal['generated'].items()}
    core=adapters.checks(root,row);robust=adapters.robustness_checks(root,row)
    assert not any(c['id'].endswith('/nonfinite-ignored-field') for c in core)
    assert len(robust)==8*e['core_component_count']
    row.update(verifier_count=len(core),checks_sha256=score.check_digest(core),verifiers=[{k:c[k] for k in ['id','category','kind']} for c in core],
               robustness_verifier_count=len(robust),robustness_checks_sha256=score.check_digest(robust),
               robustness_verifiers=[{k:c[k] for k in ['id','category','kind']} for c in robust])
    tasks[key]=row
    print(key,'core',len(core),'robustness',len(robust))
catalog=dict(schema='benchmark.verifier-catalog.v3',dataset_id='adapted6-core-v3',dataset_version='3.0.0',
             primary_scope='core',difficulty_role='historical_reward_weight_not_empirical_grade',optional_robustness_affects_core_reward=False,tasks=tasks)
(root/'verifier/partial_reward/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest['core_verifier_count']=sum(t['verifier_count'] for t in tasks.values())
manifest['optional_robustness_verifier_count']=sum(t['robustness_verifier_count'] for t in tasks.values())
for e in manifest['entries']:
    r=tasks['core6/'+e['task_id']];e['core_verifier_count']=r['verifier_count'];e['optional_robustness_verifier_count']=r['robustness_verifier_count']
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert len(tasks)==6 and sum(t['verifier_count'] for t in tasks.values())==196 and sum(t['robustness_verifier_count'] for t in tasks.values())==168
