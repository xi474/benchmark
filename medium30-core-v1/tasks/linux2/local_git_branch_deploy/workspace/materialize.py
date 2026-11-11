# Only creates directories; never overwrites submitted modules.
from pathlib import Path
root=Path(__file__).resolve().parent
(root/'outputs').mkdir(exist_ok=True)
