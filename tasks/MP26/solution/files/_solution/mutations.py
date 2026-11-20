"""Author-only deliberately wrong implementations for verifier validation."""
import base64,copy
TARGETS={
'MP01':'soft_vote','MP02':'segment_assemble','MP03':'mount_merge','MP04':'users_merge','MP05':'contact_rank','MP06':'cancel_notifications','MP07':'archive_after_send','MP08':'photo_outbox','MP09':'panel_slots','MP10':'recent_contact','MP11':'seminar_ride','MP12':'mail_trash','MP13':'feature_union','MP14':'exception_report','MP15':'import_usage_join','MP16':'api_documentation','MP17':'multipart_body','MP18':'manifest_selection','MP19':'module_zip','MP20':'feature_snapshot','MP21':'playlist_m3u','MP22':'marc_subjects','MP23':'reshard_restore','MP24':'university_query','MP25':'invoice_amounts','MP26':'dinner_change_plan'}
def mutate(id_,result):
    value=copy.deepcopy(result);r=value['result']
    if id_=='MP01':r['probabilities']=[row[::-1] for row in r['probabilities']]
    elif id_=='MP02':r['columns']=sorted(r['columns'])
    elif id_=='MP03':
        for item in r['conflicts']:
            r['records']=[item['evidence'][-1] if x['mount']==item['mount'] else x for x in r['records']]
    elif id_=='MP04':r['conflicts']=[]
    elif id_=='MP05':r['ranking']=r['ranking'][:1]
    elif id_=='MP06':
        for message in r['outbox']:message['requires']=[]
    elif id_=='MP07':r['blocked']=not r['blocked']
    elif id_=='MP08':r['attachments']=[x.removeprefix('holiday/') for x in r['attachments']]
    elif id_=='MP09':
        for slot in r['slots']:slot['start']+=1;slot['end']+=1
    elif id_=='MP10':r['contact_id']='old-contact'
    elif id_=='MP11':r['pickup']+=30
    elif id_=='MP12':r['trash_ids']=[]
    elif id_=='MP13':r['index']=[str(i) for i in range(len(r['index']))]
    elif id_=='MP14':r['text']=r['text'].replace('--- direct cause ---\n','').replace('--- during handling ---\n','')
    elif id_=='MP15':r['unused']=sorted(set(r['unused']+['module:abc']))
    elif id_=='MP16':
        r['namespace']='child'
        for x in r['parameters']:
            if x['type']:x['type']=x['type'].replace('base.Item','child.Item')
    elif id_=='MP17':r['body_hex']=bytes.fromhex(r['body_hex']).replace('é text'.encode(),base64.b64encode('é text'.encode())).hex()
    elif id_=='MP18':r['selected']=sorted(set(r['selected']+['.git/config']))
    elif id_=='MP19':r['paths']=sorted(set(r['paths']+['unused.py']))
    elif id_=='MP20':
        if not r['committed']:r['snapshot']={'partial':True}
    elif id_=='MP21':r['m3u']=r['m3u'].replace('#EXTINF:3,','#EXTINF:2,')
    elif id_=='MP22':
        for record in r['records']:
            for subject in record['subjects']['organizations']:subject['count']*=2
    elif id_=='MP23':
        for f in r['files']:f['hex']=bytes.fromhex(f['hex']).strip().hex()
    elif id_=='MP24':
        if r['professors']:r['professors'].append(dict(id=r['professors'][0]['id'].replace('p','q',1),countries=['DE','FR'],eligible_departments=['a','c']))
    elif id_=='MP25':
        for amount in r['amounts'].values():
            if amount['total'] is not None:amount['total']='12.00'
    elif id_=='MP26':r['cancelled']=sorted(set(r['cancelled']+['edge']))
    return value
