"""Combine the two component JSON values under the business contract in TASK.md."""


def combine(payload, left, right):
    tiers = left          # student -> tier (P/D/N)
    room_ids = right      # ranked list of selected event ids

    rooms = payload["rooms"]
    prefs = payload["prefs"]
    cancel_scenarios = payload["cancel"]

    # Build per-room tier preference: tiers list from most to least preferred,
    # each group is a tie. A student is acceptable to a room iff their tier is
    # listed. Rank = index of the group containing the tier.
    def room_rank(room_id, tier):
        ts = rooms[room_id]["tiers"]
        for i, group in enumerate(ts):
            if tier in group:
                return i
        return None

    results = []
    for cancel in cancel_scenarios:
        closed = set(cancel)
        open_rooms = [r for r in room_ids if r not in closed]

        # Students with at least one valid grade (all students in tiers).
        students = sorted(tiers.keys())

        # Acceptability: student accepts room if room appears in prefs; room
        # accepts student if student's tier is listed in room tiers.
        # Build student preference rank over open rooms.
        def student_rank(s, room_id):
            for i, group in enumerate(prefs[s]):
                if room_id in group:
                    return i
            return None

        # Enumerate all stable matchings via brute force over assignments.
        # Each student assigned to at most one open room, each room within capacity.
        # A matching is a dict student -> room_id (or None).
        # Weak stability: no unmatched student s and open room w such that
        # s strictly prefers w to current assignment AND (w has free seat OR
        # w strictly prefers s to some assigned student).
        #
        # We enumerate all valid matchings and filter for weak stability.

        # For each student, candidate rooms = open rooms acceptable to both.
        candidates = {}
        for s in students:
            cands = []
            for w in open_rooms:
                sr = student_rank(s, w)
                rr = room_rank(w, tiers[s])
                if sr is not None and rr is not None:
                    cands.append(w)
            candidates[s] = cands

        # Enumerate all matchings (student -> room or None) respecting capacity.
        capacities = {w: rooms[w]["capacity"] for w in open_rooms}

        matchings = []

        def rec(idx, assignment, used):
            if idx == len(students):
                matchings.append(dict(assignment))
                return
            s = students[idx]
            # option: unassigned
            assignment[s] = None
            rec(idx + 1, assignment, used)
            for w in candidates[s]:
                if used[w] < capacities[w]:
                    used[w] += 1
                    assignment[s] = w
                    rec(idx + 1, assignment, used)
                    used[w] -= 1
            assignment.pop(s)

        rec(0, {}, {w: 0 for w in open_rooms})

        def is_stable(matching):
            for s in students:
                cur = matching.get(s)
                cur_rank = student_rank(s, cur) if cur is not None else None
                for w in candidates[s]:
                    w_rank = student_rank(s, w)
                    # s strictly prefers w over current
                    if cur_rank is None or w_rank < cur_rank:
                        # w has free seat?
                        assigned = [t for t, r in matching.items() if r == w]
                        if len(assigned) < capacities[w]:
                            return False
                        # w strictly prefers s over some assigned student
                        s_rr = room_rank(w, tiers[s])
                        for t in assigned:
                            t_rr = room_rank(w, tiers[t])
                            if s_rr < t_rr:
                                return False
            return True

        stable = [m for m in matchings if is_stable(m)]

        # sizes: [assigned_count, number_of_matchings], sorted by count asc
        from collections import Counter
        size_counts = Counter()
        for m in stable:
            cnt = sum(1 for s in students if m.get(s) is not None)
            size_counts[cnt] += 1
        sizes = [[cnt, size_counts[cnt]] for cnt in sorted(size_counts)]

        max_cnt = max((cnt for cnt in size_counts), default=0)
        max_matchings = [m for m in stable
                         if sum(1 for s in students if m.get(s) is not None) == max_cnt]

        # forced: [student, room] pairs present in ALL max matchings, sorted asc
        forced = []
        for s in students:
            for w in open_rooms:
                if all(m.get(s) == w for m in max_matchings):
                    forced.append([s, w])
        forced.sort()

        # example: lexicographically smallest vector of assigned rooms by
        # student id ascending; unassigned -> ""
        def vector(m):
            return [m.get(s) or "" for s in students]

        example = min((vector(m) for m in max_matchings), default=[""] * len(students))

        results.append({
            "sizes": sizes,
            "forced": forced,
            "example": example,
        })

    return results
