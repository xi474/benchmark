from pathlib import Path
import json
from fractions import Fraction
from itertools import product


def _transitive_closure(n, edges):
    reach = [[False] * n for _ in range(n)]
    for i in range(n):
        reach[i][i] = True
    for a, b in edges:
        reach[a][b] = True
    for k in range(n):
        for i in range(n):
            if reach[i][k]:
                row_i = reach[i]
                row_k = reach[k]
                for j in range(n):
                    if row_k[j]:
                        row_i[j] = True
    return reach


def transform(payload):
    rubrics = payload["rubrics"]
    courses = payload["courses"]

    old_labels = sorted(rubrics.keys())
    new_label_set = set()
    for v in rubrics.values():
        new_label_set.update(v)
    new_labels = sorted(new_label_set)

    allowed = {o: set(rubrics[o]) for o in old_labels}

    prefixes = set()
    for code in courses:
        if code.endswith("-2013J"):
            prefixes.add(code[:-len("-2013J")])
    prefixes = sorted(p for p in prefixes if (p + "-2013J") in courses and (p + "-2014J") in courses)

    prefix_data = {}
    for p in prefixes:
        old_code = p + "-2013J"
        new_code = p + "-2014J"
        old_items = courses[old_code]["items"]
        new_items = courses[new_code]["items"]
        old_edges = courses[old_code].get("edges", [])
        new_edges = courses[new_code].get("edges", [])

        old_ids = [it[0] for it in old_items]
        new_ids = [it[0] for it in new_items]
        old_idx = {iid: i for i, iid in enumerate(old_ids)}
        new_idx = {iid: i for i, iid in enumerate(new_ids)}

        old_edges_idx = [(old_idx[a], old_idx[b]) for a, b in old_edges]
        new_edges_idx = [(new_idx[a], new_idx[b]) for a, b in new_edges]

        old_reach = _transitive_closure(len(old_ids), old_edges_idx)
        new_reach = _transitive_closure(len(new_ids), new_edges_idx)

        prefix_data[p] = {
            "old_items": old_items,
            "new_items": new_items,
            "old_reach": old_reach,
            "new_reach": new_reach,
        }

    candidates = []
    for p in prefixes:
        d = prefix_data[p]
        for oit in d["old_items"]:
            oid = oit[0]
            if not any(s is not None for s in oit[2]):
                continue
            for nit in d["new_items"]:
                nid = nit[0]
                if not any(s is not None for s in nit[2]):
                    continue
                candidates.append((p, oid, nid))

    n_labels = len(old_labels)
    bijections = []

    def gen_bijection(assigned_new, used_new):
        if len(assigned_new) == n_labels:
            bijections.append(tuple(assigned_new))
            return
        o = old_labels[len(assigned_new)]
        for nl in new_labels:
            if nl not in used_new and nl in allowed[o]:
                used_new.add(nl)
                assigned_new.append(nl)
                gen_bijection(assigned_new, used_new)
                assigned_new.pop()
                used_new.discard(nl)

    gen_bijection([], set())

    prefix_cands = {}
    for p in prefixes:
        d = prefix_data[p]
        lst = []
        for (pp, oid, nid) in candidates:
            if pp != p:
                continue
            oi = next(i for i, it in enumerate(d["old_items"]) if it[0] == oid)
            ni = next(i for i, it in enumerate(d["new_items"]) if it[0] == nid)
            lst.append((oid, nid, oi, ni))
        prefix_cands[p] = lst

    prefix_compat = {}
    for p in prefixes:
        d = prefix_data[p]
        lst = prefix_cands[p]
        m = len(lst)
        compat = [[True] * m for _ in range(m)]
        for i in range(m):
            for j in range(m):
                oi1, ni1 = lst[i][2], lst[i][3]
                oi2, ni2 = lst[j][2], lst[j][3]
                if d["old_reach"][oi1][oi2] != d["new_reach"][ni1][ni2]:
                    compat[i][j] = False
                if d["old_reach"][oi2][oi1] != d["new_reach"][ni2][ni1]:
                    compat[i][j] = False
        prefix_compat[p] = compat

    cand_support = {}
    for (p, oid, nid) in candidates:
        d = prefix_data[p]
        oit = next(it for it in d["old_items"] if it[0] == oid)
        nit = next(it for it in d["new_items"] if it[0] == nid)
        oc = sum(1 for s in oit[2] if s is not None)
        nc = sum(1 for s in nit[2] if s is not None)
        cand_support[(p, oid, nid)] = min(oc, nc)

    best_pairs = -1
    best_support = -1
    best_alignments = []

    for bij in bijections:
        mapping = {old_labels[i]: bij[i] for i in range(n_labels)}
        per_prefix_valid = {}
        for p in prefixes:
            lst = prefix_cands[p]
            valid_idx = []
            for i, (oid, nid, oi, ni) in enumerate(lst):
                ol = next(it[1] for it in prefix_data[p]["old_items"] if it[0] == oid)
                nl = next(it[1] for it in prefix_data[p]["new_items"] if it[0] == nid)
                if mapping[ol] == nl:
                    valid_idx.append(i)
            per_prefix_valid[p] = valid_idx

        prefix_matchings = {}
        for p in prefixes:
            lst = prefix_cands[p]
            compat = prefix_compat[p]
            valid_idx = per_prefix_valid[p]
            matchings = []
            n = len(valid_idx)
            for mask in range(1 << n):
                chosen = [valid_idx[k] for k in range(n) if (mask >> k) & 1]
                used_old = set()
                used_new = set()
                ok = True
                for ci in chosen:
                    oid, nid, oi, ni = lst[ci]
                    if oid in used_old or nid in used_new:
                        ok = False
                        break
                    used_old.add(oid)
                    used_new.add(nid)
                if not ok:
                    continue
                ok = True
                for a in range(len(chosen)):
                    for b in range(a + 1, len(chosen)):
                        if not compat[chosen[a]][chosen[b]]:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    continue
                matchings.append(tuple(chosen))
            prefix_matchings[p] = matchings

        prefix_lists = [prefix_matchings[p] for p in prefixes]
        for combo in product(*prefix_lists):
            total_pairs = 0
            total_support = 0
            chosen_set = set()
            for p, chosen in zip(prefixes, combo):
                lst = prefix_cands[p]
                for ci in chosen:
                    oid, nid, oi, ni = lst[ci]
                    chosen_set.add((p, oid, nid))
                    total_pairs += 1
                    total_support += cand_support[(p, oid, nid)]
            if total_pairs > best_pairs or (total_pairs == best_pairs and total_support > best_support):
                best_pairs = total_pairs
                best_support = total_support
                best_alignments = [frozenset(chosen_set)]
            elif total_pairs == best_pairs and total_support == best_support:
                best_alignments.append(frozenset(chosen_set))

    unique_alignments = set(best_alignments)
    ways = len(unique_alignments)

    if unique_alignments:
        common = set.intersection(*[set(a) for a in unique_alignments])
    else:
        common = set()
    forced = sorted(common)

    if best_pairs == 0:
        drift = None
    else:
        drifts = []
        for al in unique_alignments:
            old_vals = []
            new_vals = []
            for (p, oid, nid) in al:
                d = prefix_data[p]
                oit = next(it for it in d["old_items"] if it[0] == oid)
                nit = next(it for it in d["new_items"] if it[0] == nid)
                old_vals.extend(s for s in oit[2] if s is not None)
                new_vals.extend(s for s in nit[2] if s is not None)
            old_mean = sum(old_vals) / len(old_vals)
            new_mean = sum(new_vals) / len(new_vals)
            drifts.append(Fraction(new_mean - old_mean).limit_denominator())
        drift_min = min(drifts)
        drift_max = max(drifts)
        drift = [[drift_min.numerator, drift_min.denominator],
                 [drift_max.numerator, drift_max.denominator]]

    return {
        "pairs": best_pairs,
        "support": best_support,
        "ways": ways,
        "forced": forced,
        "drift": drift,
    }


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
