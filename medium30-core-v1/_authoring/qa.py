"""Reference, business-mutant, clean-interface, and integrity control checks."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT/'release/medium30-core-v1'
sys.path.insert(0,str(PACKAGE/'verifier'))
from score import grade,read,write

def install(work):
    for name in ['references.py','references_extra.py','references_more.py','references_final.py','references_storage.py']:
        path=ROOT/'authoring'/name
        if path.exists():shutil.copyfile(path,work/name)
    workflow=read(work/'workflow.json')
    for c in workflow['components']:
        path=work/c['folder']/'engine.py'
        path.write_text('from runtime import build,read\nfrom references import solve\ndef transform(payload,contract):return solve(contract["op"],payload,contract)\ndef load_payload(path):return read(path)\ndef build_component(root,contract):return build(root,contract,transform)\n',encoding='utf-8')

MUTANTS={
 'N01':('dependency_report',"value['matrix']=[[1 for _ in row] for row in value['matrix']]"),
 'N02':('variable_plan',"payload['dataset']['variables'][next(iter(payload['dataset']['variables']))]['dims'].append('leaked')"),
 'N03':('effective_marks',"value['marks']=value['marks'][:-1]"),
 'N04':('fallback_values',"value['sql']=value['sql'].replace(' % 2 = 1',' = 1')"),
 'N05':('backend_a',"value=[{'id':r['id'],'date':r['local'].split('T')[0]} for r in payload['rows']]"),
 'N06':('combined_query',"value['branches'][1][0]['value']='renamed_literal'"),
 'N07':('expression_ast',"value=['div',['div',value[1],value[2][1]],value[2][2]] if value[0]=='div' and value[2][0]=='div' else value"),
 'N08':('restored_report',"value['restored']=payload['capture']['state']"),
 'N09':('meeting',"value['start']=payload['alice'][0][0]"),
 'N10':('homomorphism',"value['valid']=True"),
 'N11':('squared',"value=[[0 if b['data'] is None else b for b in row] for row in value]"),
 'N12':('form_choices',"value=[{'id':e['id'],'label':e['name']} for mid in payload['matches'] for e in payload['candidates'] if e['id']==mid]"),
 'N13':('moderation',"\n for row in value['published']+value['queue']:\n  original=next((x for x in payload['queue']+payload['events'] if x.get('id')==row['id'] and 'tid' in x),None)\n  if original:row['tid']=original['tid']"),
 'N14':('bulk_result',"value['scores']=[next(g['final'] for g in payload['folds'] if any(r['index']==i for r in g['results'])) for i in range(payload['count'])]"),
 'N15':('member_plan',"value['members']=[{'name':r['name'],'type':'file','content':''} if r['type']=='symlink' else r for r in value['members']]"),
 'N16':('notes',"\n if payload['old']!=payload['new'] and payload['new'] in payload['rows']:\n  value['rows'].pop(payload['old']);value['stats']={'rows_changed':0,'rows_deleted':1,'failed_deletes':0}"),
 'N17':('template_dependencies',"\n for name,text in payload['templates'].items():\n  if 'notconf.' in text:value[name]=sorted(set(value[name]+['hints.min_chars']))"),
 'N18':('modified_url',"from urllib.parse import unquote; value=unquote(value)"),
 'N19':('transaction_view',"value['reads'][0]=None"),
 'N20':('directory_resources',"value=sorted(set(value+[name for name in payload['files'] if name.endswith('html')]))"),
 'N22':('cleaned_repo',"value['bundle']=payload['bundle']"),
 'N23':('recovered',"value['records']=payload['base']"),
 'N24':('settlement',"value['journal']=''"),
 'N25':('deployment_hook',"value=value.replace('site/dev','site/main')"),
 'N26':('distribution',"value=[1/payload['model']['n']]*payload['model']['n']"),
 'N27':('rental_report',"value['notifications'] += [{'to':payload['friend'],'property':x,'at':0} for x in payload['saved']]"),
 'N28':('gift_checkout',"value['order']['quantity']=len(payload['replies'])"),
 'N29':('threshold_actions',"\n if len(payload['messages'])>=payload['threshold']:\n  value['trigger_at']=sorted(payload['messages'],key=lambda x:x['at'])[payload['threshold']-1]['at']"),
 'N30':('recipients',"\n keep={x['id'] for x in payload['people'] if not x['former']}\n value['messages']=[x for x in value['messages'] if x in keep]\n value['fallback_email']=[x for x in value['fallback_email'] if x in keep]"),
}

def main(ids):
    naive=ROOT/'authoring/fixtures/original_naive.sql'
    MUTANTS['N21']=('optimized_query','value='+repr(naive.read_text(encoding='utf-8')))
    catalog=read(PACKAGE/'verifier/catalog.json');results=[];started=time.time()
    with tempfile.TemporaryDirectory(prefix='medium30-author-qa-') as td:
        base=Path(td)
        for ident in ids:
            row=catalog['tasks'][ident];work=base/ident;shutil.copytree(PACKAGE/row['entry']/'workspace',work);install(work)
            reference=grade(PACKAGE,ident,work);write(ROOT/'qa-results'/f'{ident}-reference.json',reference)
            assert reference['strict_pass'],(ident,'reference',[(x['id'],x['detail']) for x in reference['checks'] if not x['passed']])
            name,mutation=MUTANTS.get(ident,(read(work/'workflow.json')['components'][-1]['name'],"value=None"))
            component=next(c for c in read(work/'workflow.json')['components'] if c['name']==name);engine=work/component['folder']/'engine.py';original=engine.read_text()
            engine.write_text('from runtime import build,read\nfrom references import solve\ndef transform(payload,contract):\n value=solve(contract["op"],payload,contract)\n '+mutation+'\n return value\ndef load_payload(path):return read(path)\ndef build_component(root,contract):return build(root,contract,transform)\n',encoding='utf-8')
            compile(engine.read_text(encoding='utf-8'),str(engine),'exec')
            bad=grade(PACKAGE,ident,work);write(ROOT/'qa-results'/f'{ident}-business-mutant.json',bad);assert not bad['strict_pass'] and bad['integrity_ok']
            engine.write_text(original,encoding='utf-8')
            # Transform remains correct, but builder assumes the output already exists.
            engine.write_text(original+'\ndef build_component(root,contract):\n from pathlib import Path\n return read(Path(root)/contract["output"])\n',encoding='utf-8')
            broken=grade(PACKAGE,ident,work);write(ROOT/'qa-results'/f'{ident}-broken-builder.json',broken)
            assert broken['core_transform_case_pass_rate']==1 and not broken['strict_pass']
            engine.write_text(original,encoding='utf-8')
            (work/'README.md').write_text('tampered',encoding='utf-8')
            integrity=grade(PACKAGE,ident,work);assert integrity['reward']==0 and not integrity['integrity_ok']
            control=dict(task=ident,registry_sha256=row['registry_sha256'],scorer_sha256=__import__('hashlib').sha256((PACKAGE/'verifier/score.py').read_bytes()).hexdigest(),probe_sha256=__import__('hashlib').sha256((PACKAGE/'verifier/probe.py').read_bytes()).hexdigest(),reference_strict_pass=True,reference_reward=reference['reward'],core_units=reference['total_verifiers'],business_mutant_rejected=True,mutation_component=name,broken_builder_rejected_with_core_rate_100=True,integrity_gate_zero=True)
            results.append(control);write(ROOT/'qa-results'/f'{ident}-controls.json',control)
            print('QA',ident,'PASS',flush=True)
    merged={}
    for path in (ROOT/'qa-results').glob('*-controls.json'):
        control=read(path);ident=control['task']
        if ident in catalog['tasks'] and control.get('registry_sha256')==catalog['tasks'][ident]['registry_sha256'] and control.get('scorer_sha256')==__import__('hashlib').sha256((PACKAGE/'verifier/score.py').read_bytes()).hexdigest() and control.get('probe_sha256')==__import__('hashlib').sha256((PACKAGE/'verifier/probe.py').read_bytes()).hexdigest():merged[ident]=control
    report=dict(status='passed',task_count=len(merged),elapsed_seconds=round(time.time()-started,1),results=[merged[k] for k in sorted(merged)],scope='author_controls_not_model_results')
    write(ROOT/'qa-results/validation.json',report)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='*');a=p.parse_args();ids=a.ids or list(read(PACKAGE/'verifier/catalog.json')['tasks']);main(ids)
