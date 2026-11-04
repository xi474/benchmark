"""Load the author-only operation catalogue."""
from common import *
import algorithms_a, algorithms_b, algorithms_c, algorithms_d
from pathlib import Path
metadata=Path(__file__).with_name('candidate_metadata.json')
if metadata.is_file():
    by_id={x['id']:x for x in json.loads(metadata.read_text(encoding='utf-8'))['candidates']}
    for t in TASKS:t.update(title=by_id[t['id']]['title'],source_metadata=by_id[t['id']])
