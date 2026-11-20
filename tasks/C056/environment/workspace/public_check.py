import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

def same(actual, expected, tolerance):
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, (float,int)) and isinstance(actual, (float,int)):
        return math.isfinite(actual) and abs(actual-expected) <= tolerance
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same(actual[k], expected[k], tolerance) for k in expected)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a,e,tolerance) for a,e in zip(actual,expected))
    return type(actual) is type(expected) and actual == expected

if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / 'result.json'
        subprocess.run([sys.executable,'run_all.py','--input','public_input.json','--output',str(output)],check=True)
        load = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
        if not same(load(output),load('public_expected.json'),load('contract.json')['tolerance']):
            raise SystemExit('公开样例输出不一致')
        print('公开检查通过')
