# Package solver contract (project-defined)

This is a synthetic dependency format, not npm, pip, Cargo or another registry's version semantics. Invoke `python -m project.cli --input DIR --output FILE`. Input requires `config.json` and `catalog.json`; unrelated files are ignored. Each is JSON. Output is one JSON object plus a newline. Do not mutate input. Repeated runs must produce identical output bytes.

## Strict input

`config.json` has exactly `roots`, `features`, `prior`. `roots` is a list of objects with exactly `package,min,max`; no package may repeat. `features` is a list of unique nonempty strings. `prior` is an object mapping known package names to versions. `catalog.json` is a list of objects with exactly `package,versions`. Package names are nonempty unique strings. Each nonempty `versions` list contains objects with exactly `version,deps`, with no duplicate version within a package. Each `deps` list contains objects with exactly `package,min,max,kind,feature`; referenced packages must exist, `kind` is `required` or `peer`, and `feature` is null or a nonempty string.

A version is exactly a three-element JSON integer array `[major,minor,patch]`, each 0–9; JSON booleans are invalid. A bound is null or such an array. If both `min` and `max` are non-null, `min < max`. The interval predicate is `min <= version < max`, ignoring null endpoints. Roots need not have any satisfying version; such a well-formed request produces `blocked`. Prior versions may be absent from the current catalog but must have valid syntax. Wrong fields/types, duplicate IDs, invalid bounds, unknown references and duplicate feature labels invalidate the whole input: exit nonzero without output.

## Feasible selection

For each catalog package choose either no version or exactly one offered version. Roots must be selected and satisfy their bounds. A dependency is active when `feature=null` or that feature is enabled. Start with the root package set and repeatedly add targets of active `required` dependencies from packages already in the set. Each added target must be selected at a version within every active required constraint. A `peer` dependency does **not** add its target: its target must already belong to the resulting required closure, be selected and meet its interval. No gratuitous package may be selected outside the required closure. Active dependency edges include both required and peer rows from all selected packages. Cycles are allowed if all constraints hold. Candidate version objects are chosen only by their three-part value, not catalog row order.

For an active edge output `{source,target,kind,feature}`. Sort edges by `(source,target,kind,feature)`, with null feature sorted like an empty string. Selected packages are sorted by name as `{package,version}`. `feasible_count` is the number of distinct feasible complete assignments over all catalog packages, including unselected options.

## Optimal lockfile and conflict

For a feasible assignment, `changes` counts each selected package whose version differs from `prior.get(package)` plus each prior package now unselected. `freshness` is the sum over selected versions of `100*major+10*minor+patch`. Choose the assignment minimizing `(changes,-freshness,signature)`, where `signature` is the lexicographically sorted tuple of `(package,version tuple)` pairs. Output `score:{changes,freshness}`. `prior_deltas` contains rows `{package,prior,selected}` for names in the union of prior and selected with differing values, sorted by package; a missing side is JSON null.

If no assignment is feasible, output status `blocked`, empty selected/edges/deltas, score null and feasible_count zero. Also output the lexicographically first, smallest-cardinality subset of root requests that is itself infeasible when treated as the entire root list; report its package names sorted. The empty root subset is always feasible (select nothing), so a blocked full request has a nonempty conflict. A feasible result uses status `ready` and `minimal_root_conflict:[]`.

Output has exactly seven keys: `status`, `selected`, `active_dependencies`, `prior_deltas`, `score`, `feasible_count`, `minimal_root_conflict`. The hidden suite varies catalog size, package IDs, dependency topology, features, peer requirements, prior locks and constraint intervals. No external package solver is necessary.
