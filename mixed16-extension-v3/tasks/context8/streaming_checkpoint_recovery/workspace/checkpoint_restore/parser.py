from .transform import transform
def parse(payloads,contract):
    """Stable package interface; payloads follows contract.inputs order."""
    return transform(payloads,contract)
