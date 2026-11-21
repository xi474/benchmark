"""Parse the LLM-proposed frontier width (ready_upsert count) for C/MS handshake reports."""
import json
import pathlib
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
tasks = json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))
cms = [t for t in tasks if t['id'].startswith(('C', 'MS'))]
dist = Counter()
for t in cms:
    case = HERE / 'online' / 'on' / 'cases' / t['entry_id'] / 'dynamic_v7'
    path = case / 'speculative_turns.jsonl'
    st = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()] if path.is_file() else []
    counts = []
    ids_per_turn = []
    for row in st:
        proposals = []
        for msg in (row.get('messages') or []):
            if msg.get('role') != 'assistant':
                continue
            for tc in (msg.get('tool_calls') or []):
                try:
                    args = json.loads(tc['function']['arguments'])
                except Exception:
                    continue
                if isinstance(args, dict) and 'ready_upsert' in args:
                    ru = args['ready_upsert'] or []
                    proposals.append([(u.get('id') or u.get('unit_id') or '?')
                                      for u in ru if isinstance(u, dict)])
        if proposals:
            counts.append(len(proposals[-1]))
            ids_per_turn.append(proposals[-1])
    print(f"{t['id']:6} spec_turns={len(st):2} ready_upsert_counts={counts} "
          f"ids={[i for p in ids_per_turn[:3] for i in p]}")
    for c in counts:
        dist[c] += 1
print()
print('LLM-proposed width distribution across C/MS handshake reports:',
      dict(sorted(dist.items(), key=lambda x: (x[0] is None, x[0] or 0))))
