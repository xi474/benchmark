import argparse,json
from pathlib import Path
import solution

p=argparse.ArgumentParser()
p.add_argument('--check',action='store_true')
p.add_argument('--input',default='public_input.json')
p.add_argument('--output',default='output.json')
a=p.parse_args()
if a.check:
    value=json.loads(Path('public_input.json').read_text(encoding='utf-8'))
    expected=json.loads(Path('public_expected.json').read_text(encoding='utf-8'))
    assert solution.transform(value)==expected
    print('public check passed')
else:
    solution.build_component(a.input,a.output)
