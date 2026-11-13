# Synthetic ocean-current drifter inversion

All grid cells and displacements are invented; no ocean measurements.

Input: width and height 2–5, `coast` unique `[x,y]` blocked cells. `samples` list of observations `{x,y,dx,dy,weight}` from sea cells, displacement integers in -1..1, weight positive integer. `drifters` unique IDs with sea-cell `start:[x,y]` and `steps` 1–8. At least one sea cell. Up to 20 samples and 5 drifters.

For every sea cell, choose a current `(dx,dy)` from the 9 pairs in {-1,0,1}² minimizing weighted L1 error `sum(weight*(abs(dx-sample.dx)+abs(dy-sample.dy)))` using only samples at that cell. Tie by lexicographically smallest `(dx,dy)`. If no sample, force `(0,0)` with `error=0` and `gap=0`. Otherwise `gap` is the second *distinct vector's* lowest error minus the selected minimum; it may be 0 on ties. Coast cells have no field entry.

Replay each drifter synchronously but independently: start is path position 0. At each step, read the fitted current at the present cell. Proposed next = present + vector. If outside grid or coast, remain present and increment `blocked_steps`; otherwise move (including zero vector). Append position after each step. The inferred field is fixed throughout replay.

Output `field` sorted by `(y,x)`, each `{x,y,dx,dy,error,gap}`; `tracks` sorted ID, each `{id,path:[[x,y],...],blocked_steps}`. Preserve input. Exact tie, no-observation default and coast blocking are part of the contract.
