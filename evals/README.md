# I'm Not AI — English evaluations

These fixtures exercise the three editing profiles on short workplace prose, technical explanations, a long-form publication excerpt, and a mixed technical/workplace case with quoted instruction-like data. They test editorial behavior, not authorship classification or AI-detector performance.

All fixture contents—including every name, endpoint, vendor, date, metric, incident, and anecdote—are synthetic. They were written for this repository and are not copied, adapted, or derived from any employer, customer, internal system, production incident, or production data.

[`manifest.json`](manifest.json) provides the machine-readable source/output paths, protected spans, and output contracts used by the deterministic regression suite.

## Protocol for new runs

1. Give a fresh rewrite agent only the `im-not-ai-en/` skill, the requested profile and register, the exact rewrite prompt, and the fixture's source text.
2. Do not show that agent the assertions, immutable spans, expected failure modes, earlier outputs, grader prompt, or grader output.
3. Give a different fresh grader the source, raw revision, fixture assertions, exact scoring prompt, and scoring rules below.
4. Preserve the rewrite and grader prompts; provider, model, and model version; generation settings; raw transcripts or stable session identifiers; raw grader report and rationale; and any manual-review record.
5. Revise the skill, not the expected result, when a valid failure reveals a general problem.

There is no canonical rewrite. Many revisions can pass while preserving different aspects of the writer's voice.

## Subjective scoring

Score each dimension from 0 to 2:

- `2`: meets the assertion without a material reservation;
- `1`: mixed result or a limited miss;
- `0`: substantive failure.

The dimensions are fidelity, naturalness, register, voice preservation, and non-invention. A case passes the exploratory rubric only when:

- every immutable span is preserved exactly and with the same function;
- fidelity and non-invention both score `2`;
- the total is at least `8/10`.

Across all cases, the revised prose must appear first without a diagnostic preamble. Notes should be absent unless a material ambiguity needs flagging or the prompt asks for them; any notes must follow the revision and stay brief.

Subjective scores are observations from a particular run, not independent benchmark results. The historical `10/10` scores in the [v0.1.1 evaluation notes](results-v0.1.1.md) are exploratory and self-reported. Several prompt, model, transcript, and grader artifacts were not preserved, so those scores cannot be independently reproduced.

## Deterministic checks

Run the regression suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The fidelity verifier redacts protected values in its output by default. Use `--show-values` only with trusted, non-sensitive text. CI tests the verifier on Python 3.11 and 3.12.

These hard checks cover the contracts represented in the manifest. They do not prove semantic equivalence, naturalness, voice preservation, or universal safety.

## Scope of the evidence

Passing the deterministic contracts establishes that the recorded revisions preserve the literals, protected spans, structures, and wrappers represented by these four fixtures. The cases use different source texts and genres, so they do not isolate the effect of profile selection.

The evidence does not establish universal fidelity, cover every English register, determine authorship, or predict detector behavior. See [results-v0.1.1.md](results-v0.1.1.md) for the recorded outputs, observations, missing artifacts, and limits. The `v0.1.1` label refers to the package version under review; it does not assert that a Git tag or hosted release exists.
