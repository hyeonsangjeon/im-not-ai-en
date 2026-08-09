# Concise workplace: sentence-level copyedit

> Synthetic evaluation fixture. The people, migration, schedule, and technical details are fictional and were not derived from workplace data.

- Profile: `concise`
- Register: `workplace`

## Source

~~~text
Quick update: The migration isn’t ready for today’s review, I got an useful summary from three tester, but each follow-up check take about 20 minutes. The team needs more informations before it can sign off. I spoke with Rowan in Monday, and they said API depends of the new cache key. Could we move the review to Friday? I don’t want to cancel it.
~~~

## Immutable spans

- `migration`
- `today’s review`
- `three`
- `about 20 minutes`
- `Rowan`
- `Monday`
- `API`
- `new cache key`
- `Friday`
- `cancel it`

## Targeted copyedits

- Repair the comma splice plus `an useful`, `three tester`, and `check take` without changing the quantities or actors.
- Repair the countability error in `more informations`.
- Repair the missing article before `API`, `in Monday`, and `depends of` with idiomatic local changes.

## Assertions

- **Fidelity:** Keep the migration unready for today's review, the three testers' summary, the duration and purpose of the checks, the team's need for more information, Rowan's statement about the API dependency, and the request to move rather than cancel the review.
- **Naturalness:** Make every sentence grammatical and idiomatic without turning the update into a polished memo.
- **Register:** Sound like a direct, ordinary teammate asking for a schedule change.
- **Voice preservation:** Keep the quick opener, first person, contractions, and proportionate request.
- **Non-invention:** Add no migration status, test result, owner, reason for the dependency, replacement time, or claim that Rowan confirmed a root cause.

## Common failures

- Leave a targeted grammar or usage error in place.
- Replace the three testers with three tests or change the 20-minute duration.
- Turn Rowan's statement into an independently verified fact.
- Cancel the review or invent a time on Friday.
