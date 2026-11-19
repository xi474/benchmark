# Scheduling causal reviews across available sessions

sessions is the number of successive review sessions. Each event in events has a unique id, a list of parents in an acyclic causal history, a nonnegative integer value, and slots, the sessions in which the evidence is available (numbered from 1). Empty slots means the event cannot itself be reviewed; its causal relationships still apply.

A review schedule assigns some events to one available session each. If selected event a is an ancestor of selected event b along any path, a must be reviewed in a strictly earlier session than b. Omitted intermediate events still transmit ancestry. Events unrelated by causality can be reviewed together; no limit is imposed on such parallel work. The benefit is the sum of the selected events' values, counted once per event.

Return {schedule:{event_id:session}} for any feasible maximum-benefit plan. The evaluator checks the assignment and its attained benefit. Unselected events are omitted. There is no required ordering or tie-break between optimal schedules.

Instances can contain up to 90 causally related events, four sessions, and dependencies crossing between multiple evidence chains.
