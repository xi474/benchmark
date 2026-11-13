import json
import sys
from pathlib import Path
from .engine import evaluate

def main():
    source, target = map(Path, sys.argv[1:3])
    data = json.loads(source.read_text(encoding="utf-8"))
    target.write_text(json.dumps(evaluate(data), sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
