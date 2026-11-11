"""Independent small-instance semantic models. Does not import author solutions."""
import copy
import re

def expected(kind,p):
    if kind=='model_sets':
        def dependencies(n):
            if n['kind']=='leaf':return len(n['matrix'][0]),[{j for j,x in enumerate(row) if x} for row in n['matrix']]
            a,aa=dependencies(n['left']);b,bb=dependencies(n['right'])
            if n['kind']=='parallel':return a+b,aa+[{j+a for j in row} for row in bb]
            return a,[set().union(*(aa[j] for j in row)) if row else set() for row in bb]
        count,rows=dependencies(dict(kind=p['kind'],left=p['left'],right=p['right']))
        return dict(matrix=[[int(j in row) for j in range(count)] for row in rows],input_count=count,output_count=len(rows),separable=[len(row)==1 and sum(bool(row&other) for other in rows)==1 for row in rows])
    if kind=='sequential_increments':
        state=copy.deepcopy(p['initial']);scores=[]
        for item in p['operations']:
            bucket=state.setdefault(item['key'],{});bucket[item['member']]=bucket.get(item['member'],0)+item['delta'];scores.append(bucket[item['member']])
        return dict(scores=scores,sets=state)
    if kind=='raw_url_scan':
        url=p['url'];scheme_end=url.index('://')+3;authority_end=min([x for x in [url.find('/',scheme_end),url.find('?',scheme_end),url.find('#',scheme_end),len(url)] if x>=0]);authority=url[scheme_end:authority_end]
        q=url.find('?',authority_end);h=url.find('#',authority_end)
        if h>=0 and q>h:q=-1
        colon=authority.rfind(':');spans={'host':(scheme_end,scheme_end+colon if colon>=0 else authority_end),'port':(scheme_end+colon+1,authority_end) if colon>=0 else None,'path':(authority_end,min(x for x in [q,h,len(url)] if x>=0)),'query':(q+1,h if h>=0 else len(url)) if q>=0 else None,'anchor':(h+1,len(url)) if h>=0 else None}
        chosen=None
        for name,span in spans.items():
            if name not in p['segments'] or span is None:continue
            i,end=span
            while i<end:
                if url[i]=='%' and i+2<end and all(c in '0123456789abcdefABCDEF' for c in url[i+1:i+3]):i+=3;continue
                if url[i].isdigit():
                    j=i+1
                    while j<end and url[j].isdigit():j+=1
                    chosen=i,j;i=j
                else:i+=1
        i,j=chosen;old=url[i:j];value=int(old)+(p['count'] if p['operation']=='increment' else -p['count']);new=str(value)
        if len(old)>1 and old[0]=='0':new=new.zfill(len(old))
        return url[:i]+new+url[j:]
    if kind=='fixed_record_machine':
        # Operate directly on fixed-width buffers, rather than decoded object lists.
        accounts=[list(p['accounts'][i:i+34]) for i in range(0,len(p['accounts']),34)];books=[list(p['books'][i:i+28]) for i in range(0,len(p['books']),28)];journal=p['journal'];status=[]
        for order in p['orders']:
            buyer,seller,bid,amount=order[:4],order[4:8],order[8:12],int(order[12:])
            target=next(row for row in books if ''.join(row[:4])==bid)
            if ''.join(target[24:])!=seller:status.append('rejected');continue
            for row in accounts:
                ident=''.join(row[:4]);delta=amount if ident==seller else -amount if ident==buyer else 0
                row[24:]=list(f"{int(''.join(row[24:]))+delta:010d}")
            target[24:]=list(buyer);journal+=bid+f'{amount:010d}'+seller+buyer;status.append('accepted')
        return dict(accounts=''.join(''.join(x) for x in accounts),books=''.join(''.join(x) for x in books),journal=journal,statuses=status)
    from oracles_extra import extra_expected
    return extra_expected(kind,p)
