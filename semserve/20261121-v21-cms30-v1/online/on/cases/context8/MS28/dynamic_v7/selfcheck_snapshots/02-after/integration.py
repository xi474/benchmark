from fractions import Fraction
from itertools import combinations


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md.

    left  : {assignment_id: [demand, [valid slot ids]]} for deadline assignments only.
    right : list of per-withdrawal remaining slot maps {slot_id: [day, capacity]}.
    """
    assignments = payload["assignments"]
    # Order of deadline assignments as they appear in the input.
    deadline_ids = [a[0] for a in assignments if a[1] is not None]

    results = []
    for remaining in right:
        # Remaining slots available in this scenario.
        slot_cap = {sid: cap for sid, (_day, cap) in remaining.items()}

        # Determine valid slots per deadline assignment in this scenario.
        # left already filtered by the 7-day window and original serviceable list.
        served = {}
        unserved = []
        for aid in deadline_ids:
            demand, valid_ids = left[aid]
            available = [sid for sid in valid_ids if sid in slot_cap]
            if not available:
                unserved.append(aid)
            else:
                served[aid] = (demand, available)

        if not deadline_ids:
            results.append({"empty": True})
            continue
        if unserved:
            results.append({"unserved": sorted(unserved)})
            continue

        # Build per-assignment demand and per-slot capacity.
        demands = {aid: served[aid][0] for aid in served}
        # Union capacity of a set S = sum of capacities of slots in union of their valid slots.
        # Compute for each assignment its valid slot set.
        valid_sets = {aid: set(served[aid][1]) for aid in served}

        # Enumerate all non-empty subsets of served assignments.
        ids = sorted(served.keys())
        n = len(ids)
        best = None
        tight_sets = []
        for r in range(1, n + 1):
            for combo in combinations(ids, r):
                total_demand = sum(demands[a] for a in combo)
                union_slots = set()
                for a in combo:
                    union_slots |= valid_sets[a]
                total_cap = sum(slot_cap[s] for s in union_slots)
                ratio = Fraction(total_demand, total_cap)
                if best is None or ratio > best:
                    best = ratio
                    tight_sets = [set(combo)]
                elif ratio == best:
                    tight_sets.append(set(combo))

        # peak as reduced fraction.
        peak = [best.numerator, best.denominator]
        count = len(tight_sets)

        # minimal tight sets (by inclusion).
        minimal = []
        for s in tight_sets:
            if not any(other < s for other in tight_sets):
                minimal.append(sorted(s))
        minimal.sort(key=lambda x: (len(x), x))

        # implies: for each assignment appearing in at least one tight set.
        appears = set()
        for s in tight_sets:
            appears |= s
        implies = []
        for aid in sorted(appears):
            others = set()
            for s in tight_sets:
                if aid in s:
                    others |= (s - {aid})
            implies.append([aid, sorted(others)])

        results.append({
            "peak": peak,
            "count": count,
            "minimal": minimal,
            "implies": implies,
        })

    return results
