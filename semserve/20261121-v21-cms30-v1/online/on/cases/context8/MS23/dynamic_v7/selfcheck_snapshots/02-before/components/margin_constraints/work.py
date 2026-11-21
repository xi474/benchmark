def compute(payload):
    """为每个快照输出 [ab 与 ac 各 a 总量是否相容,按 a,c 行优先展开的 ac 配额]。"""
    out = []
    for snap in payload["snapshots"]:
        ab = snap["ab"]
        ac = snap["ac"]
        compatible = True
        for a in range(len(ab)):
            if sum(ab[a]) != sum(ac[a]):
                compatible = False
                break
        quota = [ac[a][c] for a in range(len(ac)) for c in range(len(ac[a]))]
        out.append([compatible, quota])
    return out
