from pathlib import Path
import json


def transform(payload):
    topics = payload.get("topics", [])
    papers = payload.get("papers", [])
    graph = payload.get("graph", [])

    topic_index = {t: i for i, t in enumerate(topics)}
    candidates = [[] for _ in topics]
    for pi, paper in enumerate(papers):
        methods = set(paper.get("methods", []))
        best = {}
        for claim in paper.get("claims", []):
            topic, section, quality = claim[0], claim[1], claim[2]
            if section not in methods:
                continue
            if topic not in topic_index:
                continue
            ti = topic_index[topic]
            if ti not in best or quality > best[ti]:
                best[ti] = quality
        for ti, q in best.items():
            candidates[ti].append((pi, q))

    n = len(topics)
    if n == 0:
        return {"review": [], "graph": [list(e) for e in sorted(set(tuple(e) for e in graph))]}

    # Maximize lexicographically: (min quality, total quality, -paper_id_seq)
    # where paper_id_seq is minimized lexicographically. We compare tuples with
    # the paper-id sequence negated so that a smaller sequence wins.
    best = None  # (min_q, total_q, negated_ids_tuple, assign)

    def search(ti, used, min_q, total_q, assign):
        nonlocal best
        if ti == n:
            ids = tuple(papers[a[0]]["id"] for a in assign)
            key = (min_q, total_q, tuple(-ord(c) for c in "".join(ids)))
            if best is None or key > best[0]:
                best = (key, assign[:])
            return
        for pi, q in candidates[ti]:
            if pi in used:
                continue
            used.add(pi)
            assign.append((pi, q))
            new_min = q if min_q is None else min(min_q, q)
            search(ti + 1, used, new_min, total_q + q, assign)
            assign.pop()
            used.remove(pi)

    search(0, set(), None, 0, [])

    if best is None:
        return None

    assign = best[1]
    review = [[topics[ti], papers[pi]["id"], q] for ti, (pi, q) in enumerate(assign)]

    edges = set(tuple(e) for e in graph)
    for ti, (pi, q) in enumerate(assign):
        edges.add((papers[pi]["id"], "supports", topics[ti]))
    sorted_edges = sorted(edges)

    return {"review": review, "graph": [list(e) for e in sorted_edges]}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
