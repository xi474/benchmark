from runtime import build,read
from references import solve
def transform(payload,contract):return solve(contract["op"],payload,contract)
def load_payload(path):return read(path)
def build_component(root,contract):return build(root,contract,transform)
