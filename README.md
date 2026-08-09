# I'm Not AI — English

I'm Not AI — English is a portable agent skill for editing AI-assisted English without losing the writer's meaning, voice, technical precision, or natural rhythm. It is meant for the ordinary places where assisted writing needs a careful editorial pass: a quick message, a technical explanation, or an article that needs better movement between ideas.

This is an independent English adaptation inspired by [`epoko77-ai/im-not-ai`](https://github.com/epoko77-ai/im-not-ai) and the maintainer's Korean fork, [`hyeonsangjeon/im-not-ai`](https://github.com/hyeonsangjeon/im-not-ai). It retains language-neutral ideas such as conservative editing, protected meaning, progressive disclosure, and regression checks. Its English editorial rules, fixtures, and verifier behavior were developed independently rather than translated from the Korean rules.

The goal is not to make prose perform “humanness.” It is to help the original writer sound more like themselves on a clear day.

## What it protects

- Facts, commitments, qualifications, uncertainty, attribution, and logical relationships
- Numbers, citations, links, quotations, code, identifiers, and domain terminology
- The writer's register and recognizable habits of cadence, directness, warmth, or restraint
- Functional structure such as headings, lists, tables, and deliberate technical repetition

I'm Not AI — English does not promise AI-detector bypass, classify authorship, insert fake imperfections, invent personal experience, or optimize detector scores. It diagnoses phrasing in context and leaves clean, characteristic prose alone.

## Profiles

| Profile | Best for | Editorial focus |
| --- | --- | --- |
| `concise` | Messages, replies, issue and PR comments, email snippets | Immediate clarity and social calibration |
| `standard` | Technical explanations, posts, ordinary documents | Information hierarchy, precision, and flow |
| `long-form` | Essays and articles | Paragraph cadence, transitions, and sustained attention |

An optional register cue—`workplace`, `technical`, `conversational`, or `publication`—guides the edit without creating a grid of modes. If no cues are supplied, the skill infers them from the text and request.

## Install

The current GitHub CLI preview can install the skill for Codex, GitHub Copilot, or Claude Code. These examples use personal scope; replace `user` with `project` to install in the current repository.

```bash
gh skill install hyeonsangjeon/im-not-ai-en im-not-ai-en --agent codex --scope user
gh skill install hyeonsangjeon/im-not-ai-en im-not-ai-en --agent github-copilot --scope user
gh skill install hyeonsangjeon/im-not-ai-en im-not-ai-en --agent claude-code --scope user
```

For a manual installation, copy or link the canonical [`im-not-ai-en/`](im-not-ai-en) folder to one of these host paths:

| Host | Project location | Personal location |
| --- | --- | --- |
| OpenAI Codex | `.agents/skills/im-not-ai-en` | `~/.agents/skills/im-not-ai-en` |
| GitHub Copilot | `.agents/skills/im-not-ai-en` | `~/.agents/skills/im-not-ai-en` |
| Claude Code | `.claude/skills/im-not-ai-en` | `~/.claude/skills/im-not-ai-en` |

The shared core follows the [Agent Skills specification](https://agentskills.io/specification). `agents/openai.yaml` is a thin OpenAI metadata sidecar; the editorial instructions do not depend on it. See the official host documentation for [Codex skills](https://learn.chatgpt.com/docs/build-skills), [GitHub Copilot agent skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills), and [Claude Code skills](https://code.claude.com/docs/en/skills).

No global installation is performed by this repository.

### Deprecated Copilot plugin compatibility

The root [`plugin.json`](plugin.json) also supports the older direct-repository Copilot plugin route:

```bash
copilot plugins install hyeonsangjeon/im-not-ai-en
```

Copilot CLI warns that direct plugin installs from repositories are deprecated. Treat this as compatibility for existing workflows, not the primary install path or a promise of future marketplace availability.

## Use

Invoke the skill with `$` in Codex:

```text
Use $im-not-ai-en with the concise workplace profile. Make this message copy-ready, but keep my direct tone.
```

Invoke it with `/` in GitHub Copilot or Claude Code:

```text
Use /im-not-ai-en on this technical explanation. Preserve every identifier, number, and caveat. Return the revision first, then brief notes.
```

The revised text comes first. Copy-ready and most concise requests return only the edit; notes stay brief unless you ask for an explanation or the source contains a material ambiguity.

## Repository layout

```text
im-not-ai-en/
├── README.md
├── im-not-ai-en/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/editorial-guide.md
│   └── scripts/verify_fidelity.py
├── plugin.json
├── evals/
└── tests/
```

The installable skill stays lean. Evaluation fixtures and forward-test evidence live outside it.

## Evaluation

The evaluation suite covers short workplace prose, medium technical explanations, a long-form publication excerpt, and quoted instruction-like data. All fixture contents—including every name, endpoint, vendor, date, metric, incident, and anecdote—are synthetic. They were written for this repository and are not copied, adapted, or derived from any employer, customer, internal system, production incident, or production data.

See the [evaluation protocol](evals/README.md) and [v0.1.1 evaluation notes](evals/results-v0.1.1.md). The recorded `10/10` scores are exploratory, self-reported subjective assessments; the notes identify the artifacts that were not preserved and therefore cannot be independently reproduced.

`im-not-ai-en/scripts/verify_fidelity.py` adds deterministic checks for supported literals, declared protected spans, common Markdown structure, and copy-ready wrappers. Its output redacts protected values by default; use `--show-values` only when reviewing trusted, non-sensitive text. The verifier is tested on Python 3.11 and 3.12. The machine-readable [`evals/manifest.json`](evals/manifest.json) binds fixtures to their outputs and contracts. Change rate is reported, but no universal pass threshold is imposed.

These checks test editorial behavior. They do not prove semantic equivalence, classify authorship, or measure detector scores.

## License

I'm Not AI — English is available under the [MIT License](LICENSE). The license retains attribution to `epoko77-ai` and `hyeonsangjeon`.
