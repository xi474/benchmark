from pathlib import Path
import json

def transform(payload):
    raise NotImplementedError("Implement the public business contract")

def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def build_component(input_path, output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
