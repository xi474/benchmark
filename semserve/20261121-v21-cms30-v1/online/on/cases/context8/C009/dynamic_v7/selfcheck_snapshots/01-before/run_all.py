import argparse,json
from pathlib import Path
import solution
PUBLIC_INPUT={'vehicles': [{'id': 'v1', 'type': 'bulk', 'capacity': 3, 'cost': 1}, {'id': 'v2', 'type': 'bulk', 'capacity': 2, 'cost': 2}], 'drivers': [{'id': 'd1', 'types': ['bulk'], 'max_work': 4, 'max_continuous': 2, 'break': 1}, {'id': 'd2', 'types': ['bulk'], 'max_work': 3, 'max_continuous': 3, 'break': 2}], 'suppliers': [{'id': 's1', 'stock': 4, 'close': 5, 'unit_cost': 2}, {'id': 's2', 'stock': 4, 'close': 4, 'unit_cost': 3}], 'events': [{'id': 'e1', 'visible': 1, 'kind': 'request', 'job': {'id': 'j1', 'type': 'bulk', 'quantity': 2, 'release': 3, 'deadline': 4, 'duration': 2, 'revenue': 20, 'suppliers': ['s1', 's2']}}, {'id': 'e2', 'visible': 2, 'kind': 'request', 'job': {'id': 'j2', 'type': 'bulk', 'quantity': 2, 'release': 2, 'deadline': 5, 'duration': 2, 'revenue': 22, 'suppliers': ['s1']}}, {'id': 'e3', 'visible': 3, 'kind': 'request', 'job': {'id': 'j3', 'type': 'bulk', 'quantity': 1, 'release': 3, 'deadline': 6, 'duration': 1, 'revenue': 14, 'suppliers': ['s1', 's2']}}, {'id': 'e4', 'visible': 4, 'kind': 'cancel', 'job': 'j1'}], 'rounds': [{'cutoff': 1, 'commit': True}, {'cutoff': 3, 'commit': True}, {'cutoff': 4, 'commit': False}]}
PUBLIC_EXPECTED={'rounds': [{'cutoff': 1, 'assignments': [], 'profit': 0, 'cancelled': [], 'ignored_cancellations': []}, {'cutoff': 3, 'assignments': [{'job': 'j2', 'vehicle': 'v1', 'driver': 'd1', 'supplier': 's1', 'start': 3, 'end': 5, 'quantity': 2, 'profit': 16}, {'job': 'j3', 'vehicle': 'v1', 'driver': 'd2', 'supplier': 's1', 'start': 5, 'end': 6, 'quantity': 1, 'profit': 11}], 'profit': 27, 'cancelled': [], 'ignored_cancellations': []}, {'cutoff': 4, 'assignments': [{'job': 'j2', 'vehicle': 'v1', 'driver': 'd1', 'supplier': 's1', 'start': 3, 'end': 5, 'quantity': 2, 'profit': 16}, {'job': 'j3', 'vehicle': 'v1', 'driver': 'd2', 'supplier': 's1', 'start': 5, 'end': 6, 'quantity': 1, 'profit': 11}], 'profit': 27, 'cancelled': ['j1'], 'ignored_cancellations': []}]}
TOLERANCE=0
def equivalent(a,b):
 if type(a) in (int,float) and type(b) in (int,float):return abs(a-b)<=TOLERANCE
 if isinstance(a,dict) and isinstance(b,dict):return set(a)==set(b) and all(equivalent(a[k],b[k]) for k in a)
 if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
 return type(a)==type(b) and a==b
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',default='public_input.json');p.add_argument('--output',default='outputs/result.json');p.add_argument('--check',action='store_true');a=p.parse_args()
 if a.check:
  assert equivalent(solution.transform(PUBLIC_INPUT),PUBLIC_EXPECTED)
  print('public check passed')
 else:
  solution.build_component(a.input,a.output)
  print(a.output)
if __name__=='__main__':main()
