import argparse,json
from pathlib import Path
import solution
PUBLIC_INPUT={'run_id': 'run-0', 'freeze': 1, 'changeover': 1, 'lines': [{'id': 'L1', 'qualified': ['A', 'B'], 'windows': [[1, 8]]}, {'id': 'L2', 'qualified': ['A'], 'windows': [[2, 5], [6, 9]]}], 'bom': {'A': {'sub': 1, 'M': 1}, 'sub': {'N': 1}, 'B': {'M': 2}}, 'released': ['A', 'B'], 'routing': {'A': {'setup': 1, 'per_unit': 1}, 'B': {'setup': 1, 'per_unit': 1}}, 'substitutes': {'M': ['M', 'ALT'], 'N': ['N']}, 'lots': [{'id': 'm1', 'material': 'M', 'qty': 3, 'status': 'PASS', 'expiry': 5}, {'id': 'm2', 'material': 'ALT', 'qty': 2, 'status': 'PASS', 'expiry': 9}, {'id': 'n1', 'material': 'N', 'qty': 2, 'status': 'PASS', 'expiry': 4}, {'id': 'bad', 'material': 'M', 'qty': 10, 'status': 'HOLD', 'expiry': 20}], 'orders': [{'id': 'o1', 'sku': 'A', 'qty': 1, 'priority': 1, 'due': 5}, {'id': 'o2', 'sku': 'B', 'qty': 1, 'priority': 2, 'due': 6}, {'id': 'o3', 'sku': 'A', 'qty': 1, 'priority': 1, 'due': 8}], 'wip': [{'id': 'w0', 'sku': 'B', 'qty': 1, 'line': 'L1', 'start': 1, 'end': 2, 'due': 3}]}
PUBLIC_EXPECTED={'selected': ['o1', 'o2'], 'erp': {'run': {'id': 'run-0', 'freeze': 1}, 'orders': [{'wo': 'o1', 'run': 'run-0', 'sku': 'A', 'qty': 1, 'due': 5, 'start': 2, 'end': 4, 'line': 'L2', 'status': 'PLANNED', 'parent': 'o1'}, {'wo': 'o2', 'run': 'run-0', 'sku': 'B', 'qty': 1, 'due': 6, 'start': 3, 'end': 5, 'line': 'L1', 'status': 'PLANNED', 'parent': 'o2'}, {'wo': 'w0', 'run': 'run-0', 'sku': 'B', 'qty': 1, 'due': 3, 'start': 1, 'end': 2, 'line': 'L1', 'status': 'WIP_CONT', 'parent': None}]}, 'mes': [{'run': 'run-0', 'line': 'L1', 'seq': 1, 'wo': 'w0', 'qty': 1, 'start': 1, 'end': 2, 'status': 'WIP_CONT'}, {'run': 'run-0', 'line': 'L1', 'seq': 2, 'wo': 'o2', 'qty': 1, 'start': 3, 'end': 5, 'status': 'PLANNED'}, {'run': 'run-0', 'line': 'L2', 'seq': 1, 'wo': 'o1', 'qty': 1, 'start': 2, 'end': 4, 'status': 'PLANNED'}], 'wms': [{'reservation': 'r0001', 'run': 'run-0', 'wo': 'o1', 'component': 'M', 'lot': 'm1', 'qty': 1, 'status': 'RESERVED'}, {'reservation': 'r0002', 'run': 'run-0', 'wo': 'o1', 'component': 'N', 'lot': 'n1', 'qty': 1, 'status': 'RESERVED'}, {'reservation': 'r0003', 'run': 'run-0', 'wo': 'o2', 'component': 'M', 'lot': 'm1', 'qty': 1, 'status': 'RESERVED'}, {'reservation': 'r0004', 'run': 'run-0', 'wo': 'o2', 'component': 'M', 'lot': 'm2', 'qty': 1, 'status': 'RESERVED'}]}
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
