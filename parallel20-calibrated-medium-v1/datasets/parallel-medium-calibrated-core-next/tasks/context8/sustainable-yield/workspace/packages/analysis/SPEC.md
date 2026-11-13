# Sustainable yield of a production line

stations lists process states. Each directed transition {from,to,gain} consumes exactly one time unit and adds its integer gain; gains may be negative. A controller may choose successive transitions freely. For each start state, find the largest long-run mean gain per time unit it can sustain forever. Equivalently maximize the mean gain of any nonempty directed cycle reachable from this start. A finite approach route affects reachability and contributes nothing to the long-run mean. A state cannot benefit from an unreachable cycle. Loops of one transition are cycles.

Return {sustainable:{station_id:[numerator,denominator] or null}}, with an exact integer fraction of positive denominator, or null if no infinite walk is possible from the station. Equivalent exact fractions are accepted.
