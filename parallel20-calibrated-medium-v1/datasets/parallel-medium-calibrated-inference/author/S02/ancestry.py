"""Count compatible histories of minimum total transition cost on a rooted tree."""
from itertools import product


def solve(request, independent=False, join_marginals=False):
    states = range(len(request["cost"]))
    cost = request["cost"]
    allowed = request["observed"]
    children = request["children"]
    root = request["root"]
    nodes, edges = [], []

    def visit(node):
        nodes.append(node)
        for child in children.get(node, []):
            edges.append((node, child))
            visit(child)

    visit(root)
    if (independent or join_marginals) and len(nodes)>10:
        # Enumerate costs, not histories. Coefficients multiply across siblings.
        def histogram(n, pin=None, change=None):
            tables = {c:histogram(c,pin,change) for c in children.get(n, [])}
            result = {}
            for a in allowed.get(n,states):
                if pin and pin[0]==n and pin[1]!=a:
                    continue
                distribution = {0:1}
                for child, child_states in tables.items():
                    branch = {}
                    for b, weights in child_states.items():
                        if change==child and a==b:
                            continue
                        for w,k in weights.items():
                            price = w+cost[a][b]
                            branch[price] = branch.get(price,0)+k
                    combined = {}
                    for x,nx in distribution.items():
                        for y,ny in branch.items():
                            combined[x+y] = combined.get(x+y,0)+nx*ny
                    distribution = combined
                result[a] = distribution
            return result
        tables = histogram(root)
        loss = min(w for table in tables.values() for w in table)
        def count(tables):
            return sum(t.get(loss,0) for t in tables.values())
        histories = count(tables)
        if join_marginals:
            supports = {node:{a for a in states if count(histogram(root,pin=(node,a)))} for node in nodes}
            changed = {c:histories if supports[p].isdisjoint(supports[c]) else 0 for p,c in edges}
        else:
            changed = {c:count(histogram(root,change=c)) for _,c in edges}
        return {"loss":loss,"histories":histories,"change_count":changed}
    if independent or join_marginals:
        best = None
        count = 0
        changed, supports = {}, {}
        for labels in product(*(allowed.get(node, states) for node in nodes)):
            assignment = dict(zip(nodes, labels))
            score = sum(cost[assignment[p]][assignment[c]] for p, c in edges)
            if best is None or score < best:
                best, count = score, 0
                changed = {c: 0 for _, c in edges}
                supports = {n: set() for n in nodes}
            if score == best:
                count += 1
                for p, c in edges:
                    changed[c] += assignment[p] != assignment[c]
                for n in nodes:
                    supports[n].add(assignment[n])
        if join_marginals:
            # Erroneously infer obligatory change from overlap of node supports.
            changed = {c: count if supports[p].isdisjoint(supports[c]) else 0 for p, c in edges}
        return {"loss": best, "histories": count, "change_count": changed}

    def optimum(forced_edge=None):
        scores = {}
        for n in reversed(nodes):
            table = {}
            for a in allowed.get(n, states):
                subtotal, multiplicity = 0, 1
                for child in children.get(n, []):
                    options = [(sc + cost[a][b], ways) for b, (sc, ways) in scores[child].items()
                               if child != forced_edge or b != a]
                    if not options:
                        break
                    minimum = min(s for s, _ in options)
                    subtotal += minimum
                    multiplicity *= sum(k for s, k in options if s == minimum)
                else:
                    table[a] = subtotal, multiplicity
            scores[n] = table
        choices = list(scores[root].values())
        if not choices:
            return None, 0
        lowest = min(s for s, _ in choices)
        return lowest, sum(k for s, k in choices if s == lowest)

    loss, histories = optimum()
    changed = {}
    for _, child in edges:
        conditional, count = optimum(child)
        changed[child] = count if conditional == loss else 0
    return {"loss": loss, "histories": histories, "change_count": changed}
