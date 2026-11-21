import json
import re
from pathlib import Path


def _parse_yaml(yaml_text, source_name, trusted):
    """Parse the flat YAML subset into a list of definitions."""
    defs = []
    lines = yaml_text.split('\n')
    for idx, line in enumerate(lines):
        line_no = idx + 1
        if line == '' or line == '---':
            continue
        m = re.match(r'^([a-z]+): (.*)$', line)
        if not m:
            continue
        key = m.group(1)
        rest = m.group(2)
        col = len(key) + 3  # 1-based column of value start
        is_vault = False
        anchor = None
        alias = None
        value = rest
        if rest.startswith('&'):
            m2 = re.match(r'^&([A-Za-z0-9_]+) (.*)$', rest)
            if m2:
                anchor = m2.group(1)
                value = m2.group(2)
        elif rest.startswith('*'):
            m2 = re.match(r'^\*([A-Za-z0-9_]+)$', rest)
            if m2:
                alias = m2.group(1)
                value = None
        if value is not None and value.startswith('!vault'):
            is_vault = True
            if value.startswith('!vault '):
                value = value[len('!vault '):]
            else:
                value = value[len('!vault'):]
        defs.append({
            'key': key,
            'value': value,
            'line': line_no,
            'col': col,
            'is_vault': is_vault,
            'anchor': anchor,
            'alias': alias,
            'source': source_name,
            'trusted': trusted,
        })
    return defs


def transform(payload):
    sources = payload['sources']
    tags = payload.get('tags', False)
    keys = payload.get('keys', {})

    all_defs = []
    for src in sources:
        name = src['name']
        trusted = src['trusted']
        defs = _parse_yaml(src['yaml'], name, trusted)
        anchors = {}
        for d in defs:
            if d['anchor'] is not None:
                anchors[d['anchor']] = d
            if d['alias'] is not None:
                a = anchors.get(d['alias'])
                if a is not None:
                    d['value'] = a['value']
                    d['is_vault'] = a['is_vault']
                    d['value_line'] = a['line']
                    d['value_col'] = a['col']
                    d['value_source'] = a['source']
                    d['value_trusted'] = a['trusted']
        all_defs.extend(defs)

    final = {}
    for d in all_defs:
        final[d['key']] = d

    entries = []
    for key in sorted(final.keys()):
        d = final[key]
        key_origin = [d['source'], d['line'], 1]
        if d.get('value_source') is not None:
            value_origin = [d['value_source'], d['value_line'], d['value_col']]
        else:
            value_origin = [d['source'], d['line'], d['col']]
        entries.append((key, d, key_origin, value_origin))

    final_vaults = [d for _, d, _, _ in entries if d['is_vault']]
    if not tags:
        for d in final_vaults:
            if d['value'] not in keys:
                return {"status": "sealed"}

    # Render: trusted normal value or unsealed value expands ${key} recursively.
    # Untrusted normal value keeps its original text (no expansion).
    # Recursion happens only through render_value of referenced keys, not by
    # re-scanning the substituted text.
    def render_value(d):
        if d['is_vault']:
            if tags:
                return "[sealed]"
            return keys[d['value']]
        if d['trusted']:
            return _render_template(d['value'])
        return d['value']

    def _render_template(text):
        def repl(m):
            k = m.group(1)
            if k in final:
                return render_value(final[k])
            return m.group(0)
        return re.sub(r'\$\{([a-z]+)\}', repl, text)

    result_entries = []
    for key, d, key_origin, value_origin in entries:
        trusted = d['trusted'] if not d['is_vault'] else (not tags)
        render = render_value(d)
        result_entries.append([key, key_origin, value_origin, trusted, render])

    dump_lines = []
    for key, d, key_origin, value_origin in entries:
        if d['is_vault']:
            if tags:
                text = d['value']
                dump_lines.append('{}: !vault {}'.format(key, json.dumps(text)))
            else:
                text = keys[d['value']]
                dump_lines.append('{}: {}'.format(key, json.dumps(text)))
        else:
            dump_lines.append('{}: {}'.format(key, json.dumps(d['value'])))
    dump = '\n'.join(dump_lines) + '\n'

    return {"status": "ok", "entries": result_entries, "dump": dump}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
