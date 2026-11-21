"""J1: intermediate-artifact decomposition prompt patch, replayed offline on the
archived C/MS handshake inputs (20261120-upstream59-rest49-current-v1).

Control-plane A/B: identical recorded wire inputs (sent_messages + tools, H3A
compressed), identical executor model (deepseek-v4-pro); only the speculation
guidance and the ready_upsert schema change per the intermediate decomposition
design. Measures whether the handshake LLM's proposed frontier width changes.

Patch (J1):
1. System message: replace the "edit the same file -> choose serial" rule with the
   intermediate-artifact ladder (producers under .semserve/scratch/, merge consumer).
2. Tool description: append the J1 guidance.
3. ready_upsert item schema: add optional artifact_kind / scratch_paths properties.
"""

import argparse
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENDPOINT = 'https://api.deepseek.com/v1/chat/completions'
TIMEOUT = 190
WORKERS = 4

OLD_RULE = ("- If candidate tasks still disagree on an interface, need a missing tool result,\n"
            "  edit the same file, or are too small to repay child startup cost, choose serial or\n"
            "  decline with that concrete reason.\n")

J1_RULE = (
    "- If candidate tasks still disagree on an interface, need a missing tool result, or are\n"
    "  too small to repay child startup cost, choose serial or decline with that concrete reason.\n"
    "- A single-file deliverable does not by itself force serial execution (J1). When the\n"
    "  specification splits into independently verifiable sub-results, propose producer units\n"
    "  with artifact_kind=\"intermediate\": each writes disjoint files under\n"
    "  .semserve/scratch/<work_unit_id>/ and carries its own focused_check that validates the\n"
    "  sub-result standalone, without reading any file another live producer writes. The final\n"
    "  assembly into the deliverable is a later serial consumer (artifact_kind=\"final\",\n"
    "  needs listing those producers); report it only after the producers, never as\n"
    "  currently-ready.\n"
    "- Only propose intermediate producers when each sub-result can be checked standalone\n"
    "  (a self-contained contract fragment). If sub-results share mutable state or one\n"
    "  fragment cannot be verified without another's output, stay serial.\n"
)

J1_TOOL_GUIDANCE = (
    " J1: for ready_upsert items you may set artifact_kind (\"final\" for the real deliverable, "
    "\"intermediate\" for producer units writing .semserve/scratch/<work_unit_id>/ files); "
    "intermediate items list their scratch paths in scratch_paths and must be verifiable by "
    "their own focused_check alone."
)

SCHEMA_ADDITION = {
    "artifact_kind": {
        "type": "string", "enum": ["final", "intermediate"],
        "description": "final: unit writes the task's real deliverable; intermediate: unit "
                       "writes producer scratch artifacts under .semserve/scratch/<work_unit_id>/.",
    },
    "scratch_paths": {
        "type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 256},
        "description": "Intermediate-only: disjoint paths under .semserve/scratch/<work_unit_id>/; "
                       "Runtime reclaims them after the consumer completes.",
    },
}


def patch_row(row):
    messages = [dict(m) for m in row['sent_messages']]
    system = messages[0]['content']
    assert OLD_RULE in system, 'serial rule not found'
    messages[0] = dict(messages[0], content=system.replace(OLD_RULE, J1_RULE, 1))
    tools = None
    if row.get('tools'):
        tools = json.loads(json.dumps(row['tools']))
        for tool in tools:
            fn = tool.get('function') or {}
            if fn.get('name') != 'report_frontier_state':
                continue
            fn['description'] = fn.get('description', '') + J1_TOOL_GUIDANCE
            items = fn['parameters']['properties']['ready_upsert']['items']
            for name, spec in SCHEMA_ADDITION.items():
                items['properties'][name] = spec
    return messages, tools


def call_model(messages, tools, key, model):
    body = dict(model=model, messages=messages, stream=False)
    if tools:
        body['tools'] = tools
        body['tool_choice'] = 'auto'
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
        method='POST')
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def parse_report(response):
    message = response['choices'][0]['message']
    calls = []
    for tc in (message.get('tool_calls') or []):
        fn = tc.get('function') or {}
        if fn.get('name') != 'report_frontier_state':
            continue
        try:
            args = json.loads(fn.get('arguments') or '{}')
        except Exception:
            args = {'_parse_error': True}
        calls.append(args)
    usage = response.get('usage') or {}
    return message, calls, usage


def replay_one(job, key):
    task, row, index = job
    messages, tools = patch_row(row)
    last_error = None
    for attempt in range(3):
        try:
            response = call_model(messages, tools, key, row['model'])
            message, calls, usage = parse_report(response)
            report = calls[-1] if calls else {}
            units = report.get('ready_upsert') or []
            kinds = [u.get('artifact_kind') for u in units if isinstance(u, dict)]
            scratch = [p for u in units if isinstance(u, dict)
                       for p in (u.get('scratch_paths') or [])]
            needs = [n for u in units if isinstance(u, dict) for n in (u.get('needs') or [])]
            write_sets = [u.get('write_set') for u in units if isinstance(u, dict)]
            return dict(task_id=task['id'], step=row.get('step'), scope=row.get('scope'),
                        index=index, ok=True, width=len(units), kinds=kinds,
                        scratch_paths=scratch, needs=needs, write_sets=write_sets,
                        finish_reason=response['choices'][0].get('finish_reason'),
                        prompt_tokens=usage.get('prompt_tokens'),
                        completion_tokens=usage.get('completion_tokens'),
                        prompt_cache_hit_tokens=usage.get('prompt_cache_hit_tokens'))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError,
                KeyError, IndexError) as error:
            last_error = f'{type(error).__name__}: {str(error)[:300]}'
            time.sleep(4 * (attempt + 1))
    return dict(task_id=task['id'], step=row.get('step'), index=index, ok=False,
                error=last_error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    plan = json.loads((HERE / 'experiment_plan.json').read_text(encoding='utf-8-sig'))
    profile = plan['arms']['on']['backend']
    sys.path.insert(0, str(ROOT))
    from user_api_credential import user_api_key
    key = user_api_key(profile['credential_source_user_thread'], profile['credential_fingerprint'])
    assert key
    tasks = json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))
    cms = [t for t in tasks if t['id'].startswith(('C', 'MS'))]
    jobs = []
    for task in cms:
        path = HERE / 'online' / 'on' / 'cases' / task['entry_id'] / 'dynamic_v7' / 'handshake_inputs.jsonl'
        rows = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
        for index, row in enumerate(rows):
            jobs.append((task, row, index))
    print(f'J1_REPLAY jobs={len(jobs)} model={profile["executor_model"]}', flush=True)
    results = []
    lock = threading.Lock()
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(replay_one, job, key): job for job in jobs}
        for future in as_completed(futures):
            row = future.result()
            results.append(row)
            with lock:
                done += 1
            if done % 20 == 0 or row['width'] >= 2:
                print(f'J1_ROW {done}/{len(jobs)} {row["task_id"]} step={row.get("step")} '
                      f'width={row.get("width")}', flush=True)
    out = HERE / 'j1_replay_results.jsonl'
    with out.open('w', encoding='utf-8') as stream:
        for row in results:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    ok = [r for r in results if r.get('ok')]
    widths = [r['width'] for r in ok]
    from collections import Counter
    print(f'J1_DONE ok={len(ok)}/{len(results)} width_distribution={dict(Counter(widths))}', flush=True)


if __name__ == '__main__':
    main()
