import tempfile
from pathlib import Path
from exports.tenant import valid_tenant
from exports.safe_path import below
from exports.paths import resolve_export
def main():
 assert valid_tenant('acme_1') and not valid_tenant('../x') and not valid_tenant('A C')
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); assert below(root,root/'a') and not below(root,root/'..'/'x')
  assert resolve_export(root,'acme','reports/a.json')==root/'acme'/'reports'/'a.json'
  for bad in ('../x','/x','a/../../x'):
   try: resolve_export(root,'acme',bad)
   except ValueError: pass
   else: raise AssertionError(bad)
