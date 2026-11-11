import base64
from collections import Counter
import copy
import posixpath

def storage_expected(kind,p):
    if kind=='archive_virtual_graph':
        members=[];rejected=[]
        for n in p['nodes']:
            parts=[];outside=False
            for piece in n['path'].split('/'):
                if piece=='..':
                    if parts:parts.pop()
                    else:outside=True
                elif piece not in ['','.']:parts.append(piece)
            if outside:rejected.append(n['path']);continue
            name='/'.join(parts)
            if n['kind']=='file':members.append(dict(name=name,type='file',content=n['content']))
            elif n['kind']=='dir':members.append(dict(name=name,type='dir'))
            else:
                target=posixpath.normpath(posixpath.join('/collection',posixpath.dirname(name),n['target']))
                if target=='/collection' or target.startswith('/collection/'):members.append(dict(name=name,type='symlink',linkname=posixpath.relpath(target,'/collection/'+posixpath.dirname(name))))
                else:members.append(dict(name=name,type='file',content=p['external_files'][target]))
        return dict(members=sorted(members,key=lambda x:x['name']),rejected=sorted(rejected))
    if kind=='relational_python':
        t=p['tables'];rows=[]
        for word in t['words']:
            senses=[r for r in t['senses'] if r['wordid']==word['wordid']];ids=set(r['synsetid'] for r in senses);syn=[r for r in t['synsets'] if r['synsetid'] in ids];domains=set(r['domainid'] for r in syn);poses=set(r['posid'] for r in syn)
            if len(ids)<2 or len(domains)<2 or len(senses)<2:continue
            frequency=Counter(r['synsetid'] for r in senses);winner=sorted(frequency,key=lambda s:(-frequency[s],s))[0];rows.append([word['wordid'],word['word'],len(ids),len(senses),len(domains),len(poses),winner,frequency[winner]])
        rows.sort(key=lambda r:(-r[3],-r[2],-r[4],r[0]));return dict(columns=['word_id','word','total_synsets','total_senses','distinct_domains','distinct_posids','top_synsetid','top_synset_sense_count'],rows=rows[:500])
    if kind in ['git_fixture_gold','wal_fixture_gold']:
        from storage_fixtures import fixtures
        group='git' if kind.startswith('git') else 'wal';fixture=next(x for x in fixtures()[group] if x['request']==p)
        if group=='git':return copy.deepcopy(fixture['expected'])
        base_count=5 if len(fixture['expected'])==11 else len([r for r in fixture['expected'] if r['name'].startswith('item')])
        return dict(records=fixture['expected'],base_count=base_count,database=p['base_b64'],wal=fixture['original_wal_b64'])
    if kind=='deploy_snapshots':
        state={}
        for batch in p['batches']:
            for update in batch:
                root=p['routes'].get('refs/heads/'+update['branch'])
                if root is None:continue
                state={k:v for k,v in state.items() if not k.startswith(root+'/')};state.update({root+'/'+name:value for name,value in update['files'].items()})
        return dict(files=state)
    if kind=='distribution_feasible':
        # This task has infinitely many valid outputs; independent acceptance is
        # mathematical, not a unique reference vector or exact statistic tuple.
        return {'semantic_acceptance':'positive_normalized_dual_kl'}
    raise ValueError(kind)
