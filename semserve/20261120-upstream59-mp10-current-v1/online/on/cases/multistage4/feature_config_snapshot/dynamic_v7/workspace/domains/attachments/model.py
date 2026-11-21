import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from model import load_payload as _load_payload  # noqa: E402

load_payload = _load_payload
