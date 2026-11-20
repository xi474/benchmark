"""Author solutions only; excluded from agent environments and verifier code."""
import copy
import re

def matrix(node):
    if node['kind']=='leaf':return node['matrix']
    return combine(matrix(node['left']),matrix(node['right']),node['kind'])

def combine(a,b,kind):
    if kind=='parallel':return [row+[0]*len(b[0]) for row in a]+[[0]*len(a[0])+row for row in b]
    return [[int(any(b[i][k] and a[k][j] for k in range(len(a)))) for j in range(len(a[0]))] for i in range(len(b))]

def solve(op,p,c):
    if op=='model_matrix':return matrix(p['model'])
    if op=='join_models':
        m=combine(p['left'],p['right'],p['kind'])
        return dict(matrix=m,input_count=len(m[0]),output_count=len(m),separable=[sum(row)==1 and sum(m[k][row.index(1)] for k in range(len(m)))==1 for row in m])
    if op=='group_increments':
        groups={}
        for i,item in enumerate(p['operations']):
            k,m=item['key'],item['member']
            groups.setdefault((k,m),dict(key=k,member=m,initial=p['initial'].get(k,{}).get(m,0),operations=[]))['operations'].append(dict(index=i,delta=item['delta']))
        return [groups[k] for k in sorted(groups)]
    if op=='fold_increments':
        out=[]
        for group in p['groups']:
            score=group['initial'];items=[]
            for item in group['operations']:
                score+=item['delta'];items.append(dict(index=item['index'],score=score))
            out.append(dict(key=group['key'],member=group['member'],final=score,results=items))
        return out
    if op=='assemble_increments':
        scores=[None]*p['count'];sets=copy.deepcopy(p['initial'])
        for group in p['folds']:
            sets.setdefault(group['key'],{})[group['member']]=group['final']
            for item in group['results']:scores[item['index']]=item['score']
        return dict(scores=scores,sets=sets)
    if op=='split_url':
        match=re.fullmatch(r'([^:]+)://([^/?#]*)([^?#]*)(?:\?([^#]*))?(?:#(.*))?',p['url'])
        scheme,authority,path,query,anchor=match.groups()
        host,sep,port=authority.rpartition(':')
        if not sep:host,port=authority,None
        return dict(scheme=scheme,host=host,port=port,path=path,query=query,anchor=anchor)
    if op=='url_target':
        found=None
        for name in ['host','port','path','query','anchor']:
            text=p['parts'][name]
            if name not in p['segments'] or text is None:continue
            masked=list(text)
            for match in re.finditer(r'%[0-9a-fA-F]{2}',text):masked[match.start():match.end()]=[' ']*3
            for match in re.finditer(r'[0-9]+',''.join(masked)):
                found=dict(segment=name,start=match.start(),end=match.end(),text=text[match.start():match.end()])
        return found
    if op=='rewrite_url':
        parts=copy.deepcopy(p['parts']);target=p['target'];old=target['text']
        number=int(old)+(p['count'] if p['operation']=='increment' else -p['count'])
        replacement=str(number)
        if len(old)>1 and old.startswith('0'):replacement=replacement.zfill(len(old))
        name=target['segment'];parts[name]=parts[name][:target['start']]+replacement+parts[name][target['end']:]
        return parts['scheme']+'://'+parts['host']+(':'+parts['port'] if parts['port'] is not None else '')+parts['path']+('?'+parts['query'] if parts['query'] is not None else '')+('#'+parts['anchor'] if parts['anchor'] is not None else '')
    if op=='parse_accounts':return [dict(id=p['text'][i:i+4],name=p['text'][i+4:i+24].rstrip(),balance=int(p['text'][i+24:i+34])) for i in range(0,len(p['text']),34)]
    if op=='parse_books':return [dict(id=p['text'][i:i+4],title=p['text'][i+4:i+24].rstrip(),owner=p['text'][i+24:i+28]) for i in range(0,len(p['text']),28)]
    if op=='parse_orders':return [dict(buyer=x[:4],seller=x[4:8],book=x[8:12],amount=int(x[12:22])) for x in p['orders']]
    if op=='settle_books':
        accounts=copy.deepcopy(p['accounts']);books=copy.deepcopy(p['books']);journal=p['journal'];statuses=[]
        for order in p['orders']:
            item=next(x for x in books if x['id']==order['book'])
            if item['owner']!=order['seller']:statuses.append('rejected');continue
            for account in accounts:
                if account['id']==order['buyer']:account['balance']-=order['amount']
                if account['id']==order['seller']:account['balance']+=order['amount']
            item['owner']=order['buyer'];statuses.append('accepted')
            journal+=order['book']+str(order['amount']).zfill(10)+order['seller']+order['buyer']
        return dict(accounts=''.join(x['id']+x['name'].ljust(20)+str(x['balance']).zfill(10) for x in accounts),books=''.join(x['id']+x['title'].ljust(20)+x['owner'] for x in books),journal=journal,statuses=statuses)
    from references_extra import extra_solve
    return extra_solve(op,p,c)
