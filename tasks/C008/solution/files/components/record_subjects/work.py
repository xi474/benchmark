def compute(p):
    return [[r['table'],r['id'],r['time'],[r['tenant'],r['subject']]] for r in p['records']]
