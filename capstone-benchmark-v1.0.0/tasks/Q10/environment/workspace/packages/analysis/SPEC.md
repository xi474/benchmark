# Synthetic precinct ballot reconciliation

All counts are invented arithmetic; this task concerns no real election, vote, or procedure. `precincts` (1–6) each `{id,initial_stock,reported}` has unique ASCII ID, nonnegative initial_stock, and reported object with integer nonnegative `valid`, `spoiled`, `provisional_accepted`. `events` (0–40) have unique integer `seq`, positive integer `qty`, and type:
- `issue` `{precinct}`: stock -= qty, outstanding += qty.
- `return` `{precinct,outcome}` with outcome `valid|spoiled`: outstanding -= qty, appropriate return count += qty.
- `provisional_cast` `{precinct}`: pending provisional += qty.
- `adjudicate` `{precinct,outcome}` with outcome `accepted|rejected`: pending provisional -= qty, appropriate provisional count += qty.
- `transfer` `{from,to}` between distinct precincts: source stock -= qty, destination stock += qty.
Process events in ascending seq regardless of input order. Negative stock/outstanding/pending is retained in the ledger, rather than truncating; event alerts are emitted at the **decrement** that leaves the value negative: `stock_deficit:<seq>`, `return_excess:<seq>`, `provisional_excess:<seq>`. A later unrelated event does not repeat the alert. No event is rejected or rolled back.

For each precinct compare computed valid/spoiled/provisional_accepted to its reported fields. Discrepancies are sorted field names that differ. Precinct `balanced` iff stock, outstanding and provisional_pending are all nonnegative, alerts empty and discrepancies empty. Output `{precincts,totals,balanced_count}`. Precinct rows sorted ID, each `{id,stock,outstanding,valid,spoiled,provisional_pending,provisional_accepted,provisional_rejected,alerts,discrepancies,balanced}`; alerts follow seq order. Totals object sums the seven numeric ledger fields across precincts and has `alert_count` and `discrepancy_count` sums. `balanced_count` counts true precincts.
