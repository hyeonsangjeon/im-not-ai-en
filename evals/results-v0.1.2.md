# v0.1.2 evaluation notes

- Package version under review: `0.1.2`
- Forward tests and grading recorded: 2026-08-10
- Version status: `v0.1.2` names the package manifest state evaluated on 2026-08-10; it does not assert that a Git tag or hosted release exists

All fixture contents are synthetic. The people, systems, schedules, metrics, identifiers, events, and anecdotes were written for this repository and were not copied, adapted, or derived from an employer, customer, internal system, production incident, or production data.

## Change under test

This iteration adds a conservative sentence-level copyediting pass after the existing structural and voice edit. It covers contextual review of articles and determiners, countability and agreement, pronoun reference and modifier attachment, prepositions and collocations, contractions and punctuation, spelling variety, accidental repetition, and already-correct no-op behavior.

These are host-agent instructions, not a deterministic grammar engine. The bundled verifier continues to check fidelity-related invariants only.

## Preserved evidence

| Case | Source | Raw final revision |
| --- | --- | --- |
| Concise workplace copyedit | [`fixtures/concise-copyedit-workplace.md`](fixtures/concise-copyedit-workplace.md) | [`runs/v0.1.2/concise-copyedit-workplace.md`](runs/v0.1.2/concise-copyedit-workplace.md) |
| Standard technical copyedit | [`fixtures/standard-copyedit-technical.md`](fixtures/standard-copyedit-technical.md) | [`runs/v0.1.2/standard-copyedit-technical.md`](runs/v0.1.2/standard-copyedit-technical.md) |
| Long-form dialect and rhythm | [`fixtures/long-form-dialect-rhythm.md`](fixtures/long-form-dialect-rhythm.md) | [`runs/v0.1.2/long-form-dialect-rhythm.md`](runs/v0.1.2/long-form-dialect-rhythm.md) |
| Clean concise no-op | [`fixtures/concise-clean-voice.md`](fixtures/concise-clean-voice.md) | [`runs/v0.1.2/concise-clean-voice.md`](runs/v0.1.2/concise-clean-voice.md) |

Each rewrite agent received only the installable skill, the requested profile and register, the exact source block, and a request to return a copy-ready revision. It did not receive the fixture assertions, immutable spans, targeted defects, earlier outputs, grader context, or intended answer. The public prompt record replaces the local absolute skill path with `<skill-path>`; no source or revision text is redacted.

The four rewrite instructions were:

```text
Use $im-not-ai-en at <skill-path> to edit the English below with the concise workplace profile. Return only the copy-ready revision.

Use $im-not-ai-en at <skill-path> to edit the English below with the standard technical profile. Return only the copy-ready revision.

Use $im-not-ai-en at <skill-path> to edit the English below with the long-form publication profile and its lightly conversational voice. Return only the copy-ready revision.

Use $im-not-ai-en at <skill-path> to edit the English below with the concise workplace profile. Return only the copy-ready revision.
```

In each run, the corresponding fixture's `Source` block followed the instruction after one blank line.

## Failure-driven iteration

The first pass exposed two general regressions rather than only case-specific mistakes:

- the clean no-op passage was needlessly rewritten, including equivalent punctuation, contraction, and article changes;
- an early long-form revision introduced a new witty bridge and figurative wording while removing scaffolding, and a later pass retained isolated US spellings inside an otherwise British passage.

The skill was revised to make an exact no-op an explicit success, reject equivalent house-style substitutions, prohibit new bridges or imagery, and clarify when multiple cues establish a dominant English variety. A later strict grader also rejected an otherwise correct concise revision for simplifying an already valid phrase while fixing its agreement. The synthetic source was narrowed to isolate the agreement defect, then rewritten and graded again. Fresh agents produced the four final revisions recorded above. The raw failed revisions and full hidden execution transcripts were not committed, so the iteration history is descriptive rather than independently replayable.

## Fresh grader results

A different fresh grader received the source, final revision, case assertions, targeted defects, and the evaluation rubric. Every grader was instructed to score fidelity, naturalness, register, voice preservation, and non-invention from `0` to `2`; require fidelity and non-invention to equal `2`; require at least `8/10`; and fail the targeted-copyediting gate if a listed defect remained, a replacement was incorrect, or a new error appeared.

The raw grader JSON was:

### Concise workplace copyedit

```json
{"scores":{"fidelity":2,"naturalness":2,"workplace_register":2,"voice_preservation":2,"non_invention":2},"total":10,"targeted_copyediting":"pass","overall":"pass","rationale":"All eight targeted defects are correctly fixed, with no unsupported content, unnecessary non-structural changes, or new grammar/usage errors."}
```

### Standard technical copyedit

```json
{"scores":{"fidelity":2,"naturalness":2,"technical_register":2,"voice_preservation":2,"non_invention":2},"total":10,"targeted_copyediting":"pass","overall":"pass","rationale":"All targeted defects are corrected, scheduler ownership is clarified, the dangling modifier and usage errors are resolved, and the concise final sentence preserves the source meaning without invention or new errors."}
```

### Long-form dialect and rhythm

```json
{"scores":{"fidelity":2,"naturalness":2,"publication_register":2,"voice_preservation":2,"non_invention":2},"total":10,"targeted_copyediting":"pass","overall":"pass","rationale":"Faithfully preserves the meaning and understated voice, standardises British English, and replaces the mechanical benefits sequence with a concise, source-grounded sentence. No new claim, awkward wording, or usage error is introduced."}
```

### Clean concise no-op

```json
{"scores":{"fidelity":2,"naturalness":2,"workplace_register":2,"voice_preservation":2,"non_invention":2},"total":10,"targeted_copyediting":"pass","overall":"pass","rationale":"The revision is an exact no-op, preserving the source’s meaning, natural workplace tone, concise voice, and all details without invention."}
```

These are fresh-agent observations, not independent benchmark results. The Codex environment did not expose provider-level model identifiers, model versions, generation settings, or stable transcript identifiers for these subagent runs. The exact grader prompt strings were not committed; the public record preserves their rubric, case targets, and raw JSON results. The final revisions are preserved, but the runs cannot be reproduced exactly from the repository alone. No human reviewer has signed off on the subjective scores.

## Deterministic validation

Manifest schema version `2` binds all eight current fixtures to their recorded outputs. For the four new cases it adds:

- exact protected-literal and declared-span checks;
- common Markdown structure and copy-ready-wrapper checks;
- narrow absence checks for declared defective source strings; and
- an exact identity assertion for the already clean passage.

The absence of a bad source string does not prove that its replacement is grammatical or faithful. That remains part of fresh-grader and human review. The fidelity verifier now also lists sentence-level grammar, reference, attachment, usage, punctuation, and dialect among its manual-review categories; it does not attempt to score them.

## What this establishes

In one recorded final run per case, the skill corrected the represented article, number, agreement, reference, modifier, preposition, collocation, framing, and mixed-dialect issues while preserving the declared facts and technical literals. It also left one already natural workplace passage byte-for-byte unchanged apart from the output file's terminating newline.

The observed failures and retests show that the new instructions affected no-op discipline, non-invention, and dialect handling in these examples. They do not establish comprehensive English grammar coverage, performance across models or hosts, universal fidelity, causal superiority over the earlier version, authorship, or any claim about AI detectors.
