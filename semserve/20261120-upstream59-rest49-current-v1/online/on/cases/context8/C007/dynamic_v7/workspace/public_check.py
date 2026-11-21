import json
from pathlib import Path
from solution import transform
p=json.loads(Path('public_input.json').read_text());e=json.loads(Path('public_expected.json').read_text());v=transform(p)
from public_quality import accepted
assert accepted(v,e)
print('public check passed')
