from collections import defaultdict


def compute(payload):
    """为每个查询逐时隙列出当时可见且实际不可用的域名数组，升序。

    可见 = 收录时刻 <= as_of。每个时隙 t 取生效时刻 <= t 的最新记录，
    同一生效时刻取最后收录的版本。down 与 degraded 均视为不可用。
    """
    queries = payload["queries"]
    log = payload["log"]
    results = []
    for q in queries:
        as_of = q["as_of"]
        start = q["start"]
        end = q["end"]
        visible = [r for r in log if r[2] <= as_of]
        by_domain = defaultdict(list)
        for r in visible:
            by_domain[r[0]].append((r[1], r[2], r[3]))
        for records in by_domain.values():
            records.sort()
        slots = []
        for t in range(start, end):
            down = []
            for domain in sorted(by_domain):
                best = None
                for eff, seen, status in by_domain[domain]:
                    if eff <= t:
                        best = status
                    else:
                        break
                if best in ("down", "degraded"):
                    down.append(domain)
            slots.append(down)
        results.append(slots)
    return results
