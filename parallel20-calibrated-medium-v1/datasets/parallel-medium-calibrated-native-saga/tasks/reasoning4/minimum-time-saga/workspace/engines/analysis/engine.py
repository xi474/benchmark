from runtime import build, read

def transform(payload, contract):
    """Return the business report described in SPEC.md. Leave caller inputs unchanged."""
    raise NotImplementedError

def load_payload(path):
    return read(path)

def build_component(root, contract):
    return build(root, contract, transform)
