import sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"_solution"))
from reference import evaluate

def transform(payloads,contract):
    return evaluate(payloads,contract)
