from pathlib import Path
import json
from math import gcd


def _solve_scenario(assignments, slots, withdrawn):
    """Compute peak/count/minimal/implies for one withdrawal scenario."""
    slot_cap = {}
    for sid, day, cap in slots:
        if sid not in withdrawn:
            slot_cap[sid] = (day, cap)

    eff = []  # (aid, points, valid_slot_ids)
    unserved = []
    for aid, due, points, slot_ids in assignments:
        if due is None:
            continue
        valid = []
        for sid in slot_ids:
            if sid in slot_cap:
                day, cap = slot_cap[sid]
                if due - 7 <= day < due:
                    valid.append(sid)
        if not valid:
            unserved.append(aid)
        else:
            eff.append((aid, points, valid))

    aid_list = [a for a, _, _ in eff]

    if unserved:
        return {"unserved": sorted(unserved)}

    if not eff:
        return {"empty": True}

    used_slots = set()
    for _, _, valid in eff:
        used_slots.update(valid)

    slot_ids = sorted(used_slots)
    slot_index = {sid: i for i, sid in enumerate(slot_ids)}
    caps = [slot_cap[sid][1] for sid in slot_ids]

    n = len(eff)
    amask = []
    apoints = []
    for aid, points, valid in eff:
        mask = 0
        for sid in valid:
            mask |= 1 << slot_index[sid]
        amask.append(mask)
        apoints.append(points)

    # Connected components over assignments sharing slots.
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    slot_to_assign = {}
    for i in range(n):
        mask = amask[i]
        while mask:
            low = mask & -mask
            j = low.bit_length() - 1
            slot_to_assign.setdefault(j, []).append(i)
            mask ^= low

    for j, lst in slot_to_assign.items():
        for k in range(1, len(lst)):
            union(lst[0], lst[k])

    comps = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)

    all_tight = []
    peak_frac = None

    for root, members in comps.items():
        members = sorted(members)
        cn = len(members)

        local_slots = set()
        for g in members:
            mask = amask[g]
            while mask:
                low = mask & -mask
                local_slots.add(low.bit_length() - 1)
                mask ^= low
        local_slots = sorted(local_slots)
        lslot_index = {s: k for k, s in enumerate(local_slots)}
        cm = len(local_slots)

        lmask = []
        lpoints = []
        for g in members:
            mask = 0
            m0 = amask[g]
            while m0:
                low = m0 & -m0
                s = low.bit_length() - 1
                mask |= 1 << lslot_index[s]
                m0 ^= low
            lmask.append(mask)
            lpoints.append(apoints[g])

        union_cap = [0] * (1 << cm)
        for sm in range(1, 1 << cm):
            low = sm & -sm
            s = low.bit_length() - 1
            union_cap[sm] = union_cap[sm ^ low] + caps[local_slots[s]]

        best_num = 0
        best_den = 1
        tight_local = []
        for sub in range(1, 1 << cn):
            num = 0
            smask = 0
            s = sub
            while s:
                low = s & -s
                k = low.bit_length() - 1
                num += lpoints[k]
                smask |= lmask[k]
                s ^= low
            den = union_cap[smask]
            if num * best_den > best_num * den:
                best_num = num
                best_den = den
                tight_local = [(sub, num, den)]
            elif num * best_den == best_num * den:
                tight_local.append((sub, num, den))

        g = gcd(best_num, best_den)
        best_num //= g
        best_den //= g

        if peak_frac is None:
            peak_frac = (best_num, best_den)
        else:
            a, b = peak_frac
            if best_num * b > a * best_den:
                peak_frac = (best_num, best_den)

        for sub, num, den in tight_local:
            ids = frozenset(aid_list[members[k]] for k in range(cn) if (sub >> k) & 1)
            all_tight.append(ids)

    pn, pd = peak_frac
    tight_sets = []
    for ids in all_tight:
        num = sum(apoints[aid_list.index(a)] for a in ids)
        smask = 0
        for a in ids:
            smask |= amask[aid_list.index(a)]
        den = 0
        s = smask
        while s:
            low = s & -s
            den += caps[low.bit_length() - 1]
            s ^= low
        if num * pd == pn * den:
            tight_sets.append(ids)

    tight_sets = list(set(tight_sets))
    count = len(tight_sets)

    minimal = []
    for ids in tight_sets:
        is_min = True
        for other in tight_sets:
            if other != ids and other < ids:
                is_min = False
                break
        if is_min:
            minimal.append(ids)

    minimal_sorted = sorted(
        (sorted(ids) for ids in minimal),
        key=lambda lst: (len(lst), lst),
    )

    appearing = set()
    for ids in tight_sets:
        appearing.update(ids)

    implies = []
    for aid in sorted(appearing):
        containing = [ids for ids in tight_sets if aid in ids]
        common = None
        for ids in containing:
            if common is None:
                common = set(ids)
            else:
                common &= ids
        common.discard(aid)
        implies.append([aid, sorted(common)])

    return {
        "peak": [pn, pd],
        "count": count,
        "minimal": minimal_sorted,
        "implies": implies,
    }


def transform(payload):
    assignments = payload["assignments"]
    slots = payload["slots"]
    withdrawals = payload["withdrawals"]

    results = []
    for wd in withdrawals:
        withdrawn = set(wd)
        results.append(_solve_scenario(assignments, slots, withdrawn))
    return results


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
