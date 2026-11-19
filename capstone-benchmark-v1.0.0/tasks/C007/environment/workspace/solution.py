from engine import run
def transform(payload):return run(payload)
from pathlib import Path
import json
def load_payload(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def build_component(input_path,output_path):
 value=transform(load_payload(input_path));out=Path(output_path);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');return value
