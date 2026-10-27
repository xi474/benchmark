from decimal import Decimal
from billing.money import cents,amount
from billing.events import unique_events
from billing.service import invoice
def main():
 assert cents('1.005')==Decimal('1.01') and amount(3,'0.125')==Decimal('0.375')
 ev=[{'id':'b'},{'id':'a'},{'id':'b'}]; assert [x['id'] for x in unique_events(ev)]==['a','b']
 got=invoice([{'id':'b','tenant':'acme','kind':'cpu','units':3},{'id':'a','tenant':'acme','kind':'io','units':2},{'id':'b','tenant':'acme','kind':'cpu','units':3}],{'acme':{'cpu':'0.125','io':'0.055','credit':'0.10'}})
 assert got['total']=='0.39' and [x['event_id'] for x in got['lines']]==['a','b']
