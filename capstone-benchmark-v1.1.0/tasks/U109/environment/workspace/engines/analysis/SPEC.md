# Bundle-auction clearing and all-optimum payment audit

items is a list of distinct {id,reserve} goods, each reserve a nonnegative integer. bidders is a list of distinct {id,budget} bidders with nonnegative integer budgets. bids is a list of distinct {id,bidder,items,value} bids. bidder names a bidder; items is a nonempty list of distinct good IDs and value is a nonnegative integer. A bid is eligible exactly when its value is at most its bidder's budget and at least the sum of the reserves of its items. Ineligible bids cannot win. At most 16 goods, 18 bidders and 144 bids occur; all IDs are ordinary strings and all references are valid. Duplicate economic bids with different IDs are allowed and remain distinct bids. No floating point or malformed-input behavior is required.

A feasible allocation is a SET OF BID IDs containing only eligible bids. Its bundles are pairwise disjoint, and at most one bid of each bidder can win. The empty allocation is feasible. Optimize these objectives lexicographically: first MAXIMIZE the sum of winning bid values (welfare), then MAXIMIZE the number of allocated goods, then MINIMIZE the number of winning bids. There is no further ID tie-break. Audit ALL allocations tied on all three objectives. Distinct sets of bid IDs count once each, regardless of any processing order.

For each bidder p, counterfactual_welfare[p] is the maximum welfare achievable after removing ALL bids of p; other bidders and eligibility rules are unchanged. Only welfare matters in this counterfactual, so a secondary tie never changes its numeric result. In any globally optimal allocation let W be its welfare. A winning bidder p with winning bid b pays counterfactual_welfare[p] - (W - value[b]). A losing bidder pays zero. These are nonnegative integers, and there is no extra payment cap beyond the bid eligibility rule. payment_range includes all payments to that bidder across all globally tied optima, including zero whenever the bidder loses in some optimum.

Return exactly these fields:
- score:{welfare,allocated_items,winning_bids}: the three optimal integer objective values, with winning_bids reported as a nonnegative count.
- optimal_allocations: the exact integer number of tied optimal allocations (no modulus).
- selected_in: a map from EVERY bid ID, including ineligible bids, to the number of optimal allocations that contain it.
- ineligible_bids: all ineligible bid IDs, in any order.
- counterfactual_welfare: a map for EVERY bidder to its excluded-bidder maximum welfare.
- bidders: a map for EVERY bidder to {winning_in,payment_range:[minimum,maximum]}; winning_in counts optimal allocations in which this bidder wins.

Map order is irrelevant. All numeric answers are exact. The empty allocation by itself counts as one allocation; a bidder that never wins has winning_in:0 and payment_range:[0,0].

Public example: two goods A and B, each reserve 1; bidders P and Q each have budget 20. P bids PA:A:7, PB:B:5, PAB:AB:10. Q bids QA:A:6 and QB:B:4. The two optima are {PA,QB} and {PB,QA}; both have welfare 11, coverage 2 and two winning bids. optimal_allocations is 2; selected_in is PA:1,PB:1,PAB:0,QA:1,QB:1. Counterfactual welfare is P:6,Q:10. Both bidders win in two optima; P's payment range is [0,2] and Q's is [3,5]. Taking only PAB greedily gives welfare 10. Removing only the currently winning bid instead of all bids of its bidder gives the wrong counterfactual.
