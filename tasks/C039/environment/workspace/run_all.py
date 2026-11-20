import argparse,json
from pathlib import Path
import solution
PUBLIC_INPUT={'nodes': ['U', 'X', 'Y', 'Z'], 'covariance': [[1, 0.7, 0.3, 0.2], [0.7, 1.49, 0.81, 0.54], [0.3, 0.81, 1.45, 0.8], [0.2, 0.54, 0.8, 1.45]], 'mean': [1, 2, 3, 4], 'sample_size': 100, 'allowed': [['U', 'X'], ['U', 'Y'], ['U', 'Z'], ['X', 'Y'], ['X', 'Z'], ['Y', 'X'], ['Y', 'Z'], ['Z', 'X'], ['Z', 'Y']], 'root': 'U', 'edge_count': 3, 'max_parents': 2, 'intervention': {'node': 'X', 'value': 0}}
PUBLIC_EXPECTED={'feasible': True, 'edges': [['U', 'X'], ['X', 'Y'], ['Y', 'Z']], 'score': 15.635688, 'coefficients': [['U', 'X', 0.7], ['X', 'Y', 0.543624], ['Y', 'Z', 0.551724]], 'intervened_edges': [['X', 'Y'], ['Y', 'Z']], 'mean': [1, 0, 1.912752, 3.400139]}
TOLERANCE=1e-05
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
