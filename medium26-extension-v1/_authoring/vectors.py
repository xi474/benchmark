"""Held-out synthetic cases, kept off agent mounts."""
from __future__ import annotations
import copy, json
from reference import TASKS,evaluate

def available(task,case):
    data={'inputs/case.json':copy.deepcopy(case)}
    for folder,contract in task['components']:
        data[contract['output']]=evaluate([data[x] for x in contract['inputs']],contract)
    return data

def variants(t):
    values=[('heldout-'+str(s),t['fixture'](s)) for s in (101,202,303)]
    d=t['fixture'](17); id_=t['id']
    if id_=='MP01':
        d['classes'].reverse(); d['members'][0]['active']=False
        for m in d['members']:
            if m['active']:
                m['predictions'][0]='red'; m['probabilities'][0]=[.95,.05]; m['weight']+=2
    elif id_=='MP02':
        d['columns']=['z','a','b']; d['pieces'].reverse(); d['attribute_policy']='first'; d['pieces'][1]['attrs']['extra']='only'
    elif id_=='MP03':
        d['fstab']=''; d['aix']='/special:\n dev = /dev/d17\n'; d['mount']='/dev/a on /special type xfs (ro)\n/dev/z on /other type ext4 (rw,rw)\n'
    elif id_=='MP04':
        d['json_text']='[{"id":"u","email":null,"name":""},{"id":"u","mail":"a"}]'; d['csv_text']='id,full_name,mail,joined_at\nu,"A\nB",b,31/12/2024\n'; d['jsonl_text']='\n{"id": "hidden", "name":"Z"}\n{"id":"u","email":"c"}\n'
    elif id_=='MP05':
        d['keyword']='unknown'; d['groups'][0]['messages']=['no match']; d['emails'][0]['subject']='UNKNOWN'; d['window']=[100,101]
    elif id_=='MP06':
        d['day']=999; d['contacts'][1]['email']=None; d['contacts'][1]['chat']=None
    elif id_=='MP07':
        d['send_ok']['bob']=False; d['files'].append(dict(path='home/tmp/new.tmp',hex='00ff'))
    elif id_=='MP08':
        d['festivals']=['never']; d['photos']=[]
    elif id_=='MP09':
        d['windows']=[dict(id='tiny',start=30,end=35)]; d['products'][0]['rating']=99; d['products'][0]['stock']=0
    elif id_=='MP10':
        d['conversations']=[]; d['variants'][1]['attributes']['color']='black'; d['guest_count']=20
    elif id_=='MP11':
        d['window']=[500,501]; d['lead_minutes']=0; d['book_query']['max_price_cents']=0
    elif id_=='MP12':
        d['month']='2026-10'; d['extensions']={'.exe':'bin'}; d['reply_text']='Other reply'
    elif id_=='MP13':
        d['records']=[dict(id='x',key='new',value=None,category='red',time=-5),dict(id='y',key='old',value=9,category=None,time=10)]; d['vocabulary']=['other','red','new']
    elif id_=='MP14':
        d['nodes'][2]['cause']=None; d['nodes'][2]['context']='inner'; d['nodes'][2]['suppress_context']=False
    elif id_=='MP15':
        d['source']='import abc\nimport os\nimport json\nx = 0 # type: abc.ABC\ndef f(json):\n    v: "os.PathLike[str]" = None\n    return json\n'
    elif id_=='MP16':
        d['objects'][1]['doc']=':param Item z: child type'; d['overloads']=['f(x=None, *args: int, **kwargs: str) -> None']
    elif id_=='MP17':
        d['fields']['inline']['content']=''; d['files']['data/a.bin']=(bytes(range(256))*2).hex(); d['fields']['zero']=''
    elif id_=='MP18':
        d['manifest']='include *\nglobal-exclude *.py\ninclude plugins/a.py\n'; d['build_ignore']=None
    elif id_=='MP19':
        d['modules']['main.py']='import pkg.b\n'; d['modules']['pkg/__init__.py']=''; d['modules']['pkg/b.py']='import json\n'
    elif id_=='MP20':
        for f in d['flags']:f['rules'][0]['variant']='missing-variant'
        d['flags'][0]['rules'][0]['segment']='missing-segment'
    elif id_=='MP21':
        d['tracks'][2]['duration']=2.5; d['replacement']=['t2']; d['criteria']=dict(filters=[],limit=100)
    elif id_=='MP22':
        d['xml']=d['xml'].replace('gerlat','fraeng').replace('Jesuits.','New Org.').replace('100-01</subfield><subfield code="a">作者','100-99</subfield><subfield code="a">作者')
    elif id_=='MP23':
        d['files']=[dict(path='empty',hex=''),dict(path='blank',hex='0a0a'),dict(path='raw/bytes.bin',hex=bytes(range(256)).hex())]; d['max_entries']=2; d['max_file_bytes']=16
    elif id_=='MP24':
        d['students']=d['students'][:22]; d['students'][0]['enrolments'].append(dict(department='a',start='2025-01-01',end=None))
    elif id_=='MP25':
        d['documents']=[dict(id='one',filename='one.txt',text='INVOICE\nAmount Due: 22.00\nTotal: 0.10\nVAT: 0.02\n'),dict(id='two',filename='two.txt',text='receipt\nAmount Due: 0.20\n')]
    elif id_=='MP26':
        d['today']='2026-11-06'; d['events']=[]
    values.append(('boundary',d))
    if id_=='MP15':values.append(('signature-scope',dict(source='import os\ndef f(os: os.PathLike):\n    return os\n')))
    # An empty collection case is valid for most tasks. Never invent absent defaults.
    empty=t['fixture'](19)
    collection={'MP02':'pieces','MP04':None,'MP05':'events','MP06':'events','MP08':'photos','MP09':'busy','MP10':'variants','MP11':'books','MP12':'files','MP13':'records','MP16':'overloads','MP20':'flags','MP21':'replacement','MP24':'students','MP25':'documents','MP26':'events'}.get(id_)
    if collection is not None:
        empty[collection]=[]; values.append(('empty-collection',empty))
    if id_=='MP03':empty.update(fstab='',aix='',mount='');values.append(('empty-inputs',empty))
    if id_=='MP04':empty.update(json_text='[]',csv_text='',jsonl_text='');values.append(('empty-inputs',empty))
    if id_=='MP17':empty['fields']={};values.append(('empty-parts',empty))
    if id_=='MP18':empty['files']=[];values.append(('empty-files',empty))
    if id_=='MP23':empty['files']=[];values.append(('empty-files',empty))
    return values

def cases_for(t,contract):
    result=[]
    for name,case in variants(t):
        a=available(t,case); result.append(dict(label=name,payloads=[a[x] for x in contract['inputs']],contract=copy.deepcopy(contract)))
    result.append(dict(label='invalid-top-level',payloads=[None]*len(contract['inputs']),contract=copy.deepcopy(contract)))
    a=available(t,t['fixture'](47)); inputs=[copy.deepcopy(a[x]) for x in contract['inputs']]
    inputs[0]['_nonfinite_probe']=float('nan')
    result.append(dict(label='nonfinite-ignored-field',payloads=inputs,contract=copy.deepcopy(contract)))
    # One explicit domain-invalid vector per task, beyond generic JSON guards.
    target,invalid=domain_invalid(t)
    if contract['operation']==target:
        a=available(t,t['fixture'](47)); inputs=[copy.deepcopy(a[x]) for x in contract['inputs']]; require_local=contract['inputs'][0]=='inputs/case.json'
        assert require_local
        inputs[0]=invalid
        try:evaluate(inputs,contract)
        except ValueError:pass
        else:raise AssertionError('invalid vector accepted by author reference: '+t['id'])
        result.append(dict(label='invalid-business-field',payloads=inputs,contract=copy.deepcopy(contract)))
    return result

def domain_invalid(t):
    d=t['fixture'](47);id_=t['id']
    if id_=='MP01':target='fit_members';d['classes']=['red','red']
    elif id_=='MP02':target='segment_index';d['pieces'][1]['coordinates'][0]=d['pieces'][0]['coordinates'][0]
    elif id_=='MP03':target='fstab_parse';d['fstab']='only two\n'
    elif id_=='MP04':target='users_json';d['json_text']='[broken'
    elif id_=='MP05':target='group_candidates';d['groups'][0]['members'].append('unknown')
    elif id_=='MP06':target='cancel_morning';d['events'][0]['social']=1
    elif id_=='MP07':target='attachment_receipts';d['send_ok']['bob']=None
    elif id_=='MP08':target='photo_classification';d['photos'][0]['path']='absent.jpg'
    elif id_=='MP09':target='panel_slots';d['duration']=0
    elif id_=='MP10':target='dinner_date';d['weekday']=7
    elif id_=='MP11':target='seminar_ride';d['lead_minutes']=-1
    elif id_=='MP12':target='mail_trash';d['month']='2026-13'
    elif id_=='MP13':target='numeric_features';d['records'][0]['value']=True
    elif id_=='MP14':target='exception_chain';d['nodes'][-1]['cause']='outer'
    elif id_=='MP15':target='import_usage_join';d['source']='from os import *\n'
    elif id_=='MP16':target='parameter_docs';d['objects'][0]['doc']=':param dict(str x: bad'
    elif id_=='MP17':target='multipart_parts';d['fields']['inline']['mimetype']=''
    elif id_=='MP18':target='manifest_inventory';d['files'][-1]['target']='../escape'
    elif id_=='MP19':target='module_import_scan';d['modules']['main.py']='from pkg import *\n'
    elif id_=='MP20':target='feature_schema';d['flags'][0]['rules'][0]['segment']=1
    elif id_=='MP21':target='playlist_query';d['criteria']['filters'][0]['field']='id; DROP TABLE playlists'
    elif id_=='MP22':target='marc_xml_records';d['xml']='<!DOCTYPE record><record/>'
    elif id_=='MP23':target='reshard_chunks';d['max_file_bytes']=15
    elif id_=='MP24':target='eu_professors';d['professors'][0]['departments'].append('unknown')
    elif id_=='MP25':target='invoice_amounts';d['documents'][0]['text']+='Total: 12.00\n'
    else:target='dinner_calendar_index';d['events'][0]['end']='2026-11-06T20:00'
    return target,d
