# Standard technical: sentence-level copyedit

> Synthetic evaluation fixture. The parser, worker, scheduler, test, limits, and identifiers are fictional and were not derived from production code or data.

- Profile: `standard`
- Register: `technical`

## Source

~~~text
At a high level, the parser allocate an worker to each batch. Both the request ID and the trace ID is copied into `job_meta`. We observed 12 retry during a 30-minute soak test. The parser sends the normalized record to the scheduler, and it stores the timestamp. In this path, the scheduler, not the parser, owns that timestamp. Using the fallback path, the delay is capped at 800 ms by the worker. The cap depends of `retry_budget_ms`; it does not replace `Retry-After`. This distinction is important because it is worth noting that the two limits are not the same thing.
~~~

## Immutable spans

- `parser`
- `worker`
- `scheduler`
- `request ID`
- `trace ID`
- `` `job_meta` ``
- `12`
- `30-minute soak test`
- `normalized record`
- `timestamp`
- `fallback path`
- `800 ms`
- `` `retry_budget_ms` ``
- `` `Retry-After` ``
- `does not replace`

## Targeted copyedits

- Repair `parser allocate`, `an worker`, `trace ID is copied`, and `12 retry`.
- Resolve `it stores the timestamp` to the already identified scheduler rather than guessing.
- Repair the dangling `Using the fallback path` construction without inventing an actor; the source already identifies the worker.
- Repair `depends of` and remove only genuinely empty framing.

## Assertions

- **Fidelity:** Preserve one worker per batch; both copied IDs; the 12 retries and 30-minute test; the record's path to the scheduler; scheduler ownership of the timestamp; the worker's 800 ms fallback cap; and the fact that `retry_budget_ms` does not replace `Retry-After`.
- **Naturalness:** Repair the sentence-level errors and remove padded explanation without flattening the technical relationships.
- **Register:** Read as a compact implementation note, not product copy or beginner documentation.
- **Voice preservation:** Keep the matter-of-fact technical register and explicit contrast between scheduler and parser.
- **Non-invention:** Add no test outcome, reason for the cap, storage system, performance claim, owner, deployment state, or causal explanation.

## Common failures

- Leave a targeted grammar, reference, or modifier error in place.
- Assign the timestamp to the parser or the fallback path to a new actor.
- Change 12 retries into 12 requests or turn the 30-minute test into a guarantee.
- Claim that `retry_budget_ms` overrides or replaces `Retry-After`.
