"""Describe the existing verifiers. No task semantics or test payloads are edited."""
from __future__ import annotations
import copy,importlib.util,json,sys
from pathlib import Path

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def category(label):
    if label=='invalid-top-level':return 'api_contract_validation'
    if label.startswith('domain-'):return 'domain_validation'
    if label=='invalid-business-field':return 'domain_validation'
    return 'business'
def medium(dataset,entry):
    sys.path.insert(0,str(dataset/'_authoring'));sys.path.insert(0,str(dataset/'verifier'))
    import reference,vectors
    legacy=load(dataset/'verifier/verify.py','medium_legacy_verify');t=next(t for t in reference.TASKS if t['style']+'/'+t['slug']==entry);checks=[]
    values=vectors.available(t,t['fixture'](47))
    for folder,c in t['components']:
        cases=vectors.cases_for(t,c)
        for case in cases:
            try:wanted=dict(kind='value',value=reference.evaluate(case['payloads'],case['contract']))
            except ValueError:wanted=dict(kind='ValueError')
            checks.append(dict(id='api/'+c['name']+'/'+case['label'],category=category(case['label']),kind='api',folder=folder,suite=t['style'],case=case,expected=wanted,flavor='medium'))
        checks.append(dict(id='io/'+c['name'],category='interface',kind='io',folder=folder,suite=t['style'],case=next(x for x in cases if x['label'].startswith('heldout-')),flavor='medium'))
        checks.append(dict(id='output/'+c['name'],category='integration',kind='output',path=c['output'],expected=values[c['output']],flavor='medium'))
    core=dict(components={c['name']:values[c['output']]['result'] for _,c in t['components']})
    checks.append(dict(id='output/core_manifest',category='integration',kind='output',path='outputs/core_manifest.json',expected=core,flavor='medium'))
    checks.append(dict(id='output/final_report',category='integration',kind='report',path='outputs/final_report.json',title=t['title'],flavor='medium'))
    return checks
def hard(dataset,entry):
    sys.path.insert(0,str(dataset/'_authoring'));legacy=load(dataset/'verifier/verify.py','hard_legacy_verify')
    spec=json.loads((dataset/'_authoring/task_specs.json').read_text(encoding='utf-8'))[entry];available,outputs=legacy.expected_outputs(spec);checks=[]
    for s in spec['specs']:
        c=s['contract'];cases=legacy.vectors(spec,s,available)
        for i,case in enumerate(cases):
            try:wanted=dict(kind='value',value=legacy.evaluate(case['payloads'],case['contract']))
            except ValueError:wanted=dict(kind='ValueError')
            checks.append(dict(id='api/'+c['name']+'/'+str(i),category='business' if wanted['kind']=='value' else 'domain_validation',kind='api',folder=s['folder'],suite=spec['suite'],case=dict(case,label=str(i)),expected=wanted,flavor='hard'))
        checks.append(dict(id='io/'+c['name'],category='interface',kind='io',folder=s['folder'],suite=spec['suite'],case=cases[0],flavor='hard'))
    for path,value in sorted(outputs.items()):checks.append(dict(id='output/'+path,category='integration',kind='output',path=path,expected=value,flavor='hard'))
    return checks
def original(row):
    return [dict(id='focused/'+folder,category='business',kind='focused',folder=folder) for folder in row['focused_folders']]+[dict(id='root/integration',category='integration',kind='root')]
def checks(benchmark,row):
    path=benchmark/row['dataset_path']
    if row['adapter']=='medium':return medium(path,row['entry_id'])
    if row['adapter']=='hard':return hard(path,row['entry_id'])
    return original(row)


def robustness_checks(benchmark,row):
    dataset=benchmark/row['dataset_path']
    sys.path.insert(0,str(dataset/'_authoring'))
    import reference,vectors
    t=next(t for t in reference.TASKS if t['style']+'/'+t['slug']==row['entry_id'])
    checks=[]
    for folder,c in t['components']:
        for case in vectors.robustness_cases_for(t,c):
            wanted=dict(kind='value',value=reference.evaluate(case['payloads'],case['contract'])) if case['optional_expected']=='value' else dict(kind='ValueError')
            checks.append(dict(id='optional/'+c['name']+'/'+case['label'],category=case['robustness_family'],kind='api',folder=folder,suite=t['style'],case=case,expected=wanted,flavor='medium'))
    return checks
