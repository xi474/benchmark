from pathlib import Path

def resolve_export(base, tenant, relative):
    return Path(base) / tenant / relative
