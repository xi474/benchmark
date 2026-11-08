"""Core business cases and separately evaluated optional robustness probes."""
import copy

# Only fields actually consumed by these operations are targeted. Pure path,
# text and set operations do not receive invented numeric business requirements.
NUMERIC_FIELDS={
 'panel_slots':(0,['duration']),
 'supply_selection':(0,['products',0,'price_cents']),
 'panel_commit':(0,['result','slots',0,'start']),
 'dinner_date':(0,['weekday']),
 'recent_contact':(0,['conversations',0,'ts']),
 'dinner_checkout':(0,['variants',0,'price_cents']),
 'meeting_cancel_plan':(0,['events',0,'start']),
 'seminar_ride':(0,['lead_minutes']),
 'book_purchase':(0,['book_query','max_price_cents']),
 'university_query':(2,['result','counts','a']),
}

def business_nonfinite_case(t,c,available):
    rule=NUMERIC_FIELDS.get(c['operation'])
    if rule is None:return []
    index,path=rule
    a=available(t,t['fixture'](47));p=[copy.deepcopy(a[x]) for x in c['inputs']]
    at=p[index]
    for key in path[:-1]:at=at[key]
    at[path[-1]]=float('nan')
    return [dict(label='domain-nonfinite-used-field',payloads=p,contract=copy.deepcopy(c))]

def optional_cases(t,c,available):
    a=available(t,t['fixture'](47));base=[copy.deepcopy(a[x]) for x in c['inputs']]
    out=[]
    values=[('finite',0),('nan',float('nan')),('positive-infinity',float('inf')),('negative-infinity',-float('inf'))]
    for nesting in ('direct','nested'):
        for name,value in values:
            p=copy.deepcopy(base);target=p[0]
            # Preserve the exact name/result envelope. A finite-value control
            # verifies that the probe does not create a schema error by itself.
            if type(target) is dict and set(target)=={'name','result'}:target=target['result']
            assert type(target) is dict and '_robustness_extra' not in target
            target['_robustness_extra']=value if nesting=='direct' else {'nested':[value]}
            out.append(dict(label='optional-extra-'+nesting+'-'+name,payloads=p,contract=copy.deepcopy(c),
                            optional_expected='value' if name=='finite' else 'ValueError',
                            robustness_family='finite-control' if name=='finite' else 'nonfinite-extra'))
    return out
