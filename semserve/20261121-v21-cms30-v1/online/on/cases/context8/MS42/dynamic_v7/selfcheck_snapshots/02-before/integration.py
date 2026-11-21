from fractions import Fraction
from itertools import combinations


def _gcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def _simplify(num, den):
    if den < 0:
        num, den = -num, -den
    g = _gcd(num, den)
    return [num // g, den // g]


def combine(payload, left, right):
    total_mask = left[0]
    old_to_new_mask = left[1]
    courses = right

    prefixes = set()
    for code in courses:
        if code.endswith("-2013J") or code.endswith("-2014J"):
            prefixes.add(code.rsplit("-", 1)[0])

    comparable = []
    for p in sorted(prefixes):
        if (p + "-2013J") in courses and (p + "-2014J") in courses:
            comparable.append(p)

    prefix_info = {}
    for p in comparable:
        old_stats, old_reach = courses[p + "-2013J"]
        new_stats, new_reach = courses[p + "-2014J"]
        old_items = [(r[0], r[1], r[3], r[2][0], r[2][1]) for r in old_stats]
        new_items = [(r[0], r[1], r[3], r[2][0], r[2][1]) for r in new_stats]
        prefix_info[p] = {
            "old_items": old_items,
            "new_items": new_items,
            "old_reach": old_reach,
            "new_reach": new_reach,
        }

    cand_mask = {}
    by_prefix = {}
    for p in comparable:
        info = prefix_info[p]
        by_prefix[p] = []
        for (oid, olab, ocnt, osum, oden) in info["old_items"]:
            if ocnt == 0:
                continue
            for (nid, nlab, ncnt, nsum, nden) in info["new_items"]:
                if ncnt == 0:
                    continue
                c = (p, oid, nid)
                cand_mask[c] = old_to_new_mask[olab][nlab]
                by_prefix[p].append(c)

    def reach_set(reach, iid):
        return set(reach.get(iid, []))

    prefix_subsets = {}
    for p in comparable:
        info = prefix_info[p]
        old_reach = info["old_reach"]
        new_reach = info["new_reach"]
        cands = by_prefix.get(p, [])
        n = len(cands)
        valid = []
        for sub in range(1 << n):
            chosen = [cands[i] for i in range(n) if (sub >> i) & 1]
            if not chosen:
                continue
            old_ids = set()
            new_ids = set()
            ok = True
            for (pp, oid, nid) in chosen:
                if oid in old_ids or nid in new_ids:
                    ok = False
                    break
                old_ids.add(oid)
                new_ids.add(nid)
            if not ok:
                continue
            ok = True
            for (a, b) in combinations(chosen, 2):
                (_, oa, na) = a
                (_, ob, nb) = b
                old_rel = (oa in reach_set(old_reach, ob)) or (ob in reach_set(old_reach, oa))
                new_rel = (na in reach_set(new_reach, nb)) or (nb in reach_set(new_reach, na))
                if old_rel != new_rel:
                    ok = False
                    break
            if not ok:
                continue
            mask = None
            for c in chosen:
                m = cand_mask[c]
                mask = m if mask is None else (mask & m)
            if mask == 0:
                continue
            valid.append((chosen, mask))
        prefix_subsets[p] = valid

    prefix_list = comparable
    best_pairs = -1
    best_support = -1
    best_alignments = []

    def rec(idx, chosen_pairs, mask, pairs_count, support):
        nonlocal best_pairs, best_support, best_alignments
        if idx == len(prefix_list):
            if pairs_count > best_pairs:
                best_pairs = pairs_count
                best_support = support
                best_alignments = [(frozenset(chosen_pairs), mask)]
            elif pairs_count == best_pairs:
                if support > best_support:
                    best_support = support
                    best_alignments = [(frozenset(chosen_pairs), mask)]
                elif support == best_support:
                    best_alignments.append((frozenset(chosen_pairs), mask))
            return
        p = prefix_list[idx]
        rec(idx + 1, chosen_pairs, mask, pairs_count, support)
        for (chosen, m) in prefix_subsets[p]:
            new_mask = mask & m
            if new_mask == 0:
                continue
            new_pairs = pairs_count + len(chosen)
            new_support = support
            for c in chosen:
                (pp, oid, nid) = c
                info = prefix_info[pp]
                ocnt = None
                ncnt = None
                for (iid, lab, cnt, s, d) in info["old_items"]:
                    if iid == oid:
                        ocnt = cnt
                        break
                for (iid, lab, cnt, s, d) in info["new_items"]:
                    if iid == nid:
                        ncnt = cnt
                        break
                new_support += min(ocnt, ncnt)
            rec(idx + 1, chosen_pairs + list(chosen), new_mask, new_pairs, new_support)

    rec(0, [], total_mask, 0, 0)

    if best_pairs == -1:
        best_pairs = 0
        best_support = 0
        best_alignments = [(frozenset(), total_mask)]

    pairs = best_pairs
    support = best_support
    ways = len(best_alignments)

    if best_alignments:
        forced_set = set(best_alignments[0][0])
        for (s, m) in best_alignments[1:]:
            forced_set &= s
        forced = sorted(forced_set)
    else:
        forced = []

    if pairs == 0:
        drift = None
    else:
        drifts = []
        for (s, m) in best_alignments:
            old_sum = 0
            old_cnt = 0
            new_sum = 0
            new_cnt = 0
            for (pp, oid, nid) in s:
                info = prefix_info[pp]
                for (iid, lab, cnt, ssum, dden) in info["old_items"]:
                    if iid == oid:
                        old_sum += ssum
                        old_cnt += cnt
                        break
                for (iid, lab, cnt, ssum, dden) in info["new_items"]:
                    if iid == nid:
                        new_sum += ssum
                        new_cnt += cnt
                        break
            old_mean = Fraction(old_sum, old_cnt)
            new_mean = Fraction(new_sum, new_cnt)
            drifts.append(new_mean - old_mean)
        drift_min = min(drifts)
        drift_max = max(drifts)
        drift = [_simplify(drift_min.numerator, drift_min.denominator),
                 _simplify(drift_max.numerator, drift_max.denominator)]

    return {
        "pairs": pairs,
        "support": support,
        "ways": ways,
        "forced": forced,
        "drift": drift,
    }
