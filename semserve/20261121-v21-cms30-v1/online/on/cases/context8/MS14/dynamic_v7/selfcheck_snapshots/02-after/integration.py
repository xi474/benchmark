def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    domains = payload["domains"]
    services = payload["services"]
    queries = payload["queries"]

    # right: {service_id: [need, inputs]}
    quorums = right

    # Build service dependency graph (acyclic). inputs may be domains or services.
    # left: per query, per slot, list of domains that are actually down (visible).
    results = []
    for qi, q in enumerate(queries):
        start = q["start"]
        end = q["end"]
        targets = q["targets"]
        slots_down = left[qi]  # list per slot of down domain names

        # For each slot, compute availability of every service and domain.
        # A domain is available iff not in the down set (and not forced).
        # A service is available iff at least need distinct direct inputs available.
        # We need to know, per slot, which targets are unavailable.
        # Then merge adjacent slots into incidents per target.

        # Precompute topological order of services.
        # services is acyclic; inputs reference domains or earlier services.
        # Build adjacency and indegree.
        service_ids = [s["id"] for s in services]
        id_to_service = {s["id"]: s for s in services}
        # Determine order via Kahn's algorithm using only service->service edges.
        indeg = {sid: 0 for sid in service_ids}
        children = {sid: [] for sid in service_ids}
        for s in services:
            for inp in s["inputs"]:
                if inp in id_to_service:
                    indeg[s["id"]] += 1
                    children[inp].append(s["id"])
        order = []
        from collections import deque
        dq = deque([sid for sid in service_ids if indeg[sid] == 0])
        while dq:
            sid = dq.popleft()
            order.append(sid)
            for c in children[sid]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    dq.append(c)

        # For each slot compute availability.
        # availability map: name -> bool
        target_unavailable = {t: [] for t in targets}  # list of slots where unavailable

        for t in range(start, end):
            down_set = set(slots_down[t - start])
            avail = {}
            for d in domains:
                avail[d] = d not in down_set
            for sid in order:
                s = id_to_service[sid]
                cnt = 0
                for inp in s["inputs"]:
                    if avail.get(inp, False):
                        cnt += 1
                avail[sid] = cnt >= s["need"]
            for tgt in targets:
                if not avail.get(tgt, False):
                    target_unavailable[tgt].append(t)

        # Build incidents: merge adjacent slots per target.
        incidents = []
        for tgt in targets:
            slots = target_unavailable[tgt]
            if not slots:
                continue
            # merge consecutive
            seg_start = slots[0]
            prev = slots[0]
            for s in slots[1:]:
                if s == prev + 1:
                    prev = s
                else:
                    incidents.append([tgt, seg_start, prev + 1])
                    seg_start = s
                    prev = s
            incidents.append([tgt, seg_start, prev + 1])

        # Sort incidents by target id then start.
        incidents.sort(key=lambda x: (x[0], x[1]))

        # Compute minimal repairs.
        repairs = compute_repairs(domains, services, quorums, targets, start, end, slots_down)

        results.append({"incidents": incidents, "repairs": repairs})

    return results


def compute_repairs(domains, services, quorums, targets, start, end, slots_down):
    """Find all inclusion-minimal sets of domains that, when forced up every slot,
    make all targets available for the whole window."""
    id_to_service = {s["id"]: s for s in services}
    service_ids = [s["id"] for s in services]

    # topological order
    from collections import deque
    indeg = {sid: 0 for sid in service_ids}
    children = {sid: [] for sid in service_ids}
    for s in services:
        for inp in s["inputs"]:
            if inp in id_to_service:
                indeg[s["id"]] += 1
                children[inp].append(s["id"])
    order = []
    dq = deque([sid for sid in service_ids if indeg[sid] == 0])
    while dq:
        sid = dq.popleft()
        order.append(sid)
        for c in children[sid]:
            indeg[c] -= 1
            if indeg[c] == 0:
                dq.append(c)

    n = len(domains)
    domain_index = {d: i for i, d in enumerate(domains)}

    # For each slot, compute which domains are down (from slots_down).
    # slots_down is list per slot of down domain names.
    slot_down_sets = [set(s) for s in slots_down]

    # A repair set R forces those domains up. Check feasibility for a given R.
    def feasible(R):
        Rset = set(R)
        for t in range(start, end):
            down_set = slot_down_sets[t - start]
            avail = {}
            for d in domains:
                avail[d] = (d in Rset) or (d not in down_set)
            for sid in order:
                s = id_to_service[sid]
                cnt = 0
                for inp in s["inputs"]:
                    if avail.get(inp, False):
                        cnt += 1
                avail[sid] = cnt >= s["need"]
            for tgt in targets:
                if not avail.get(tgt, False):
                    return False
        return True

    # Enumerate subsets by increasing size; collect minimal feasible sets.
    # n <= 40, but repairs are sparse. Use BFS over subsets.
    # Start from empty; if feasible, return [[]].
    if feasible([]):
        return [[]]

    minimal = []
    # We need all inclusion-minimal feasible sets. Enumerate by size.
    # Use itertools combinations by size, but prune supersets of already-minimal.
    import itertools
    found = False
    for size in range(1, n + 1):
        for combo in itertools.combinations(domains, size):
            # skip if combo is a superset of an already found minimal set
            if any(set(m) <= set(combo) for m in minimal):
                continue
            if feasible(combo):
                minimal.append(list(combo))
                found = True
        if found:
            break

    # Sort: by size then lexicographic member sequence.
    minimal.sort(key=lambda x: (len(x), x))
    return minimal
