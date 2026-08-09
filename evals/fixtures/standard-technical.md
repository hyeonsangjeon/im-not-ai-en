# Standard technical: webhook retry comment

> Synthetic evaluation fixture. The vendor, implementation, observations, dates, and metrics are fictional and were not derived from workplace data.

- Profile: `standard`
- Register: `technical`

## Source

~~~text
At a high level, this change introduces a robust and scalable retry mechanism for webhook delivery. The key thing to understand is that retries are not simply about trying again; rather, they are about trying again intelligently. The worker now uses exponential backoff with full jitter, capped at 15 minutes, and stops after 8 attempts. We retry only 408, 429, and 5xx responses; other 4xx responses go directly to `dead_letter`. This distinction is important because not all failures are created equal.

There is one caveat worth highlighting. `Retry-After` can be either delta-seconds or an HTTP-date, but this parser currently handles only delta-seconds. That matches all 37 responses in our two-week sample from ExamplePay, although I would not call the HTTP-date form impossible. If the header is missing or malformed, we fall back to the computed delay.

In summary, this approach provides a balanced, resilient, and future-proof foundation while avoiding unnecessary retries. I left the parser small on purpose. I’d rather add HTTP-date support with a fixture from the wild than guess at timezone behavior in this patch.
~~~

## Immutable spans

- `exponential backoff with full jitter`
- `15 minutes`
- `8 attempts`
- `408`, `429`, `5xx`, and `4xx`
- `` `dead_letter` `` and `` `Retry-After` ``
- `delta-seconds` and `HTTP-date`
- `37 responses`
- `two-week`
- `ExamplePay`

## Assertions

- **Fidelity:** Preserve the retry algorithm, cap, attempt count, exact response classes, `dead_letter` behavior, two legal header forms, current parser limitation, sample size/window/source, uncertainty, fallback, and reason for deferring support.
- **Naturalness:** Remove or reshape the generic preamble, canned contrast, empty importance statement, and marketing-style summary without over-compressing the caveat.
- **Register:** Read as a precise PR or implementation comment, not product marketing or beginner documentation.
- **Voice preservation:** Retain the cautious first-person judgment, “small on purpose” stance, preference for a real fixture, and reluctance to guess about timezone behavior.
- **Non-invention:** Add no response codes, algorithms, guarantees, observations, tests, performance claims, issue references, or future delivery date.

## Common failures

- Change the retry classification or algorithm parameters.
- Imply that HTTP-date parsing already works.
- Turn the limited sample into a vendor guarantee.
- Drop the missing-or-malformed-header fallback.
- Flatten the author's deliberate restraint into generic technical prose.
