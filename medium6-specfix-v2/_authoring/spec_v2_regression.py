"""Independent examples for clarified public scope plus actual verifier negatives."""
import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);args=parser.parse_args()
    root=args.root.resolve();work=args.work.resolve();sys.path.insert(0,str(root/'_authoring'))
    from reference import TASKS,evaluate
    tests=[]
    def run(task_id,op,payloads,expected,label):
        t=next(t for t in TASKS if t['id']==task_id);c=next(c for _,c in t['components'] if c['operation']==op)
        source=copy.deepcopy(payloads);contract=copy.deepcopy(c)
        actual=evaluate(payloads,c)
        assert actual=={'name':c['name'],'result':expected},(label,actual,expected)
        assert payloads==source and c==contract,label
        tests.append({'task':task_id,'check':label,'passed':True})
        return actual
    def wrapped(value):return {'name':'upstream','result':value}

    expected={'records':[{'id':'10','name':'A'},{'id':'2','name':'B'}]}
    for op,payload,empty in [
      ('users_json',{'json_text':'[{"id":2,"name":"B"},{"id":10,"name":"A"}]'},{'json_text':'[]'}),
      ('users_csv',{'csv_text':'id,name\n2,B\n10,A\n'},{'csv_text':''}),
      ('users_jsonl',{'jsonl_text':'{"id":2,"name":"B"}\n{"id":10,"name":"A"}\n'},{'jsonl_text':''})]:
        run('MP04',op,[payload],expected,op+':array_schema_and_lexical_id_order')
        run('MP04',op,[empty],{'records':[]},op+':empty_is_array')
    photos={'files':[{'path':'album/photo.jpg','hex':'00'},{'path':'notes.txt','hex':'ff'}],
            'photos':[{'path':'album/photo.jpg','festival':'winter'}],'festivals':['summer','winter'],
            'destination':'saved','recipient':'friend'}
    classified=run('MP08','photo_classification',[photos],{'selected':[{'path':'album/photo.jpg','festival':'winter'}],'missing':['summer']},'metadata_preselected_no_filename_year_parsing')
    migrated=run('MP08','photo_migration',[photos,classified],{'moves':[{'from':'album/photo.jpg','to':'saved/album/photo.jpg','festival':'winter'}],
                 'files':[{'path':'notes.txt','hex':'ff'},{'path':'saved/album/photo.jpg','hex':'00'}]},'preserve_unselected_files_and_move_bytes')
    run('MP08','photo_outbox',[photos,classified,migrated],{'to':'friend','attachments':['saved/album/photo.jpg'],'missing':['summer'],'message':'Missing: summer'},'outbox_uses_migrated_paths')
    slots=run('MP09','panel_slots',[{'now':0,'windows':[{'id':'w','start':0,'end':20}],'busy':[],'duration':3,'gap':1}],
              {'slots':[{'start':0,'end':3},{'start':4,'end':7}],'complete':True},'two_earliest_parameterized_slots')
    group=run('MP09','panel_invitees',[{'namespace':'n','groups':[{'id':'g','members':['a','a','b']}],'invite_groups':['g'],'exclude':['b']}],
              {'members':['a'],'group_id':'n-panel'},'explicit_group_ids_and_member_union')
    supplies=run('MP09','supply_selection',[{'products':[{'id':'expensive','category':'cups','stock':5,'price_cents':1000,'rating':1},{'id':'rated','category':'cups','stock':5,'price_cents':100,'rating':9}],
                                         'requirements':[{'category':'cups','quantity':2}]}],
                 {'items':[{'category':'cups','id':'rated','quantity':2,'total_cents':200}],'unavailable':[]},'rating_priority_not_most_expensive')
    run('MP09','panel_commit',[slots,group,supplies],{'events':[{'id':'n-panel-1','start':0,'end':3,'members':['a']},{'id':'n-panel-2','start':4,'end':7,'members':['a']}],
        'notification':{'group_id':'n-panel','members':['a'],'event_ids':['n-panel-1','n-panel-2']},'purchase':supplies['result']},'commit_consumes_all_three_outputs')
    who=run('MP10','recent_contact',[{'topic':'dinner','conversations':[{'id':'old','contact_id':'a','ts':1,'topic':'Dinner'},{'id':'new','contact_id':'b','ts':2,'topic':'Dinner'}]}],
            {'contact_id':'b','conversation_id':'new'},'one_primary_contact')
    dinner=wrapped({'start':'2026-11-08T19:00','guest_count':2})
    shopping={'wanted':[{'kind':'plate','attributes':{}},{'kind':'cup','attributes':{}}],
              'variants':[{'id':'p','kind':'plate','attributes':{},'stock':5,'price_cents':200},{'id':'c','kind':'cup','attributes':{},'stock':5,'price_cents':100}]}
    run('MP10','dinner_checkout',[shopping,dinner,who],{'items':[{'id':'c','kind':'cup','quantity':2},{'id':'p','kind':'plate','quantity':2}],
        'total_cents':600,'checkout':True,'recipient':'b','start':'2026-11-08T19:00','unavailable':[]},'items_sorted_by_kind_not_wanted_order')
    unavailable=copy.deepcopy(shopping)
    for v in unavailable['variants']:v['stock']=0
    run('MP10','dinner_checkout',[unavailable,dinner,who],{'items':[],'total_cents':0,'checkout':False,'recipient':'b','start':'2026-11-08T19:00','unavailable':['cup','plate']},'unavailable_lexical_order')
    run('MP11','seminar_ride',[{'events':[{'id':'s','start':100,'end':120,'kind':'seminar','organizer':'x','attendees':[]}],'seminar_id':'s','lead_minutes':15,'destination':'hall'}],
        {'event_id':'s','pickup':85,'destination':'hall'},'lead_minutes_is_parameter_not_fixed_30')
    run('MP11','book_purchase',[{'books':[{'id':'a','title':'Target book','language':'en','price_cents':100,'rating':1},{'id':'b','title':'Target book','language':'en','price_cents':150,'rating':9}],
        'book_query':{'keyword':'target','language':'en','max_price_cents':200}}],{'book_id':'b','price_cents':150},'book_fields_without_binding')
    uni={'departments':[{'id':'a','country':'DE'},{'id':'b','country':'US'},{'id':'c','country':'FR'}],
         'professors':[{'id':'p','departments':['a']},{'id':'q','departments':['b','c']}],
         'students':[{'id':f'{dept}{i}','enrolments':[{'department':dept,'start':'2020-01-01','end':None}]} for dept,n in [('a',11),('b',6),('c',6)] for i in range(n)],
         'as_of':'2025-08-16','eu':['DE','FR']}
    eu=run('MP24','eu_professors',[uni],{'ids':['p','q']},'preselected_professor_pool_without_rank_field')
    students=run('MP24','department_students',[uni],{'counts':{'a':11,'b':6,'c':6}},'count_each_department_distinctly')
    countries=run('MP24','employment_countries',[uni],{'countries':{'p':['DE'],'q':['FR','US']}},'include_all_employment_countries')
    run('MP24','university_query',[uni,eu,students,countries],{'professors':[{'id':'p','countries':['DE'],'eligible_departments':['a']}]},'two_six_student_departments_do_not_qualify')

    spec=importlib.util.spec_from_file_location('spec_v2_verifier',root/'verifier/verify.py');verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    negatives=[]
    for task_id,component,mutation in [
      ('MP04','json_users',"r['result']['records']={x['id']:x for x in r['result']['records']}"),
      ('MP10','shopping',"r['result']['items'].reverse(); r['result']['unavailable'].reverse()")]:
        t=next(t for t in TASKS if t['id']==task_id);folder,c=next((folder,c) for folder,c in t['components'] if c['name']==component)
        w=work/task_id;path=w/folder/'transform.py';before=path.read_bytes()
        old=before.decode('utf-8');prefix=old.split('\ndef transform',1)[0]
        try:
            path.write_text(prefix+'\ndef transform(payloads,contract):\n    r=evaluate(payloads,contract)\n    '+mutation+'\n    return r\n',encoding='utf-8')
            rejected=False
            try:verifier.probe(w,t,only=component)
            except AssertionError:rejected=True
            assert rejected,task_id
            negatives.append({'task':task_id,'mutation':'wrong records container' if task_id=='MP04' else 'wrong result array order','rejected':True})
        finally:path.write_bytes(before)
    result={'status':'passed','examples_passed':len(tests),'tasks_covered':sorted({t['task'] for t in tests}),
            'examples':tests,'actual_verifier_mutations_rejected':negatives,'model_calls':0,'runtime_business_semantics_changed':False}
    (root/'review/spec_v2_regression.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['examples']},ensure_ascii=False))


if __name__=='__main__':main()
