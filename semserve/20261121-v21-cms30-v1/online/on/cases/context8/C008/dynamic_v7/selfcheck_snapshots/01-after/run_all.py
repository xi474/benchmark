import argparse
from solution import build_component
p=argparse.ArgumentParser();p.add_argument("--input",default="public_input.json");p.add_argument("--output",default="outputs/result.json")
a=p.parse_args();build_component(a.input,a.output)
