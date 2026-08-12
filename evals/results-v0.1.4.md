# v0.1.4 evaluation notes

- Package version under review: `0.1.4`
- Evaluation date: 2026-08-12
- Version status: `v0.1.4` names the package manifest state evaluated here; it does not assert that a Git tag or hosted release exists

## Scope

This iteration adds a contextual preference for symbol-light ordinary prose. It asks the editor not to create readability through decorative dashes, backticks around non-code words, or repeated label colons. It explicitly preserves natural author punctuation and functional syntax such as Markdown, code, command flags, lexical hyphens, URLs, times, ratios, citations, and interface labels.

Two synthetic cases were added:

| Case | Fixture | Recorded output |
| --- | --- | --- |
| Decorative scaffolding | [`fixtures/concise-symbol-light-workplace.md`](fixtures/concise-symbol-light-workplace.md) | [`runs/v0.1.4/concise-symbol-light-workplace.md`](runs/v0.1.4/concise-symbol-light-workplace.md) |
| Functional punctuation no-op | [`fixtures/concise-functional-punctuation.md`](fixtures/concise-functional-punctuation.md) | [`runs/v0.1.4/concise-functional-punctuation.md`](runs/v0.1.4/concise-functional-punctuation.md) |

The first case requires removal of `Plan:`, `Next step:`, and a decorative dash while preserving recommendation strength, negation, command syntax, time, ratio, channel, lexical hyphen, and the stated writing goal. The second case requires byte identity because all of its colons, hyphens, backticks, apostrophe, and Markdown list markers are natural or functional.

## Forward-test observations

Fresh rewrite agents received only the skill path, profile, register, source, and a request for a copy-ready revision. They did not receive the fixture assertions or recorded output.

The first attempt removed the targeted scaffolding but introduced a semicolon and rewrote adjacent natural phrasing. A later attempt changed `We should keep` into the imperative `Keep`, strengthening the recommendation. These failures led to three explicit constraints in the core skill:

- do not replace one decorative device with another;
- do not change modal force, negation, or emphasis while removing a label or dash;
- limit symbol edits to the mechanical instance and leave adjacent natural phrasing alone.

The functional technical control was returned byte-for-byte unchanged by fresh agents after the rule was added. Its code spans, command flags, URL, time, ratio, natural colon, apostrophe, header, and Markdown bullets remained intact.

The recorded symbol-light output is a conservative reference revision rather than a raw forward-test transcript. It limits the change to the two labels and the decorative dash:

> We should keep the rollout at 10%, not because the current build is broken, but because we need one more follow-up check. At 10:30, run `deploy --dry-run`, compare the 3:1 canary split, and post the result in `#release-ops`. The goal is clarity, not a polished announcement. One thing matters: don’t guess.

A separate fresh run against the final skill state also preserved every required fact, qualifier, and functional token, but compressed the last two source sentences more than necessary. An independent grader scored that variant `9/10`, with `1/2` for voice preservation and `2/2` for fidelity, naturalness, register, and non-invention. This variation is evidence that the new instruction improves direction but does not guarantee minimal editing in every model run.

## Independent grading

A fresh grader received the source, revision, assertions, and five-dimension rubric, but no expected rewrite. It returned the following raw result for the two recorded cases:

```json
[
  {
    "case": 1,
    "scores": {
      "fidelity": 2,
      "naturalness": 2,
      "register": 2,
      "voice_preservation": 2,
      "non_invention": 2
    },
    "total": 10,
    "immutable_requirements": true,
    "pass": true,
    "rationale": "Only the requested labels and decorative dash were removed; the comma keeps the contrast grammatical. All recommendations, operational details, syntax, writing goal, and final colon sentence remain intact."
  },
  {
    "case": 2,
    "scores": {
      "fidelity": 2,
      "naturalness": 2,
      "register": 2,
      "voice_preservation": 2,
      "non_invention": 2
    },
    "total": 10,
    "immutable_requirements": true,
    "pass": true,
    "rationale": "The revision is byte-identical, preserving every functional punctuation mark, Markdown element, command, URL, ratio, and identifier."
  }
]
```

These scores are fresh-agent observations, not independent benchmark results. Provider-level model identifiers, generation settings, stable transcript identifiers, and human review were not available, so the runs cannot be reproduced exactly from the repository alone.

## Deterministic evidence and limits

Manifest schema version `2` now binds ten fixtures to their recorded outputs. The unit suite establishes that the new recorded outputs preserve their declared spans, satisfy copy-ready structure, remove the three targeted scaffolding strings, and keep the functional punctuation case byte-identical. The canonical skill and Copilot mirror remain byte-identical.

These fixtures do not establish a universal punctuation rule, model-independent minimal editing, or improved authorship classification. They deliberately do not count punctuation or ban characters. Subjective judgment is still required to distinguish decorative scaffolding from grammar, technical syntax, house style, or the writer's natural voice.
