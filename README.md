# I'm Not AI — English

I'm Not AI — English is a portable agent skill for editing AI-assisted English without losing the writer's meaning, voice, technical precision, or natural rhythm. It is meant for the ordinary places where assisted writing needs a careful editorial pass: a quick message, a technical explanation, or an article that needs better movement between ideas.

This is an independent English adaptation inspired by [`epoko77-ai/im-not-ai`](https://github.com/epoko77-ai/im-not-ai) and the maintainer's Korean fork, [`hyeonsangjeon/im-not-ai`](https://github.com/hyeonsangjeon/im-not-ai). It retains language-neutral ideas such as conservative editing, protected meaning, progressive disclosure, and regression checks. The English-language instructions, fixtures, and verifier were written for this repository rather than translated from the Korean rules. Its sentence-level copyediting design was also informed by the public projects listed in [Acknowledgments](ACKNOWLEDGMENTS.md).

The goal is not to make prose perform “humanness.” It is to help the original writer sound more like themselves on a clear day.

Alongside structural and voice editing, the skill asks the host agent to inspect common sentence-level issues such as article choice, countability and agreement, idiomatic prepositions and collocations, pronoun reference, modifier placement, contractions, punctuation, and dialect consistency. These are contextual editing instructions, not an exhaustive grammar engine or a guarantee that every error will be detected.

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
| OpenAI Codex | `.agents/skills/im-not-ai-en` | `~/.codex/skills/im-not-ai-en` |
| GitHub Copilot | `.github/skills/im-not-ai-en` | `~/.copilot/skills/im-not-ai-en` |
| Claude Code | `.claude/skills/im-not-ai-en` | `~/.claude/skills/im-not-ai-en` |

The shared core follows the [Agent Skills specification](https://agentskills.io/specification). `agents/openai.yaml` is a thin OpenAI metadata sidecar; the editorial instructions do not depend on it. See the official host documentation for [Codex skills](https://learn.chatgpt.com/docs/build-skills), [GitHub Copilot agent skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills), and [Claude Code skills](https://code.claude.com/docs/en/skills).

No global installation is performed by this repository.

### Copilot plugin compatibility

A byte-identical mirror under [`.claude/skills/im-not-ai-en/`](.claude/skills/im-not-ai-en) and its [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) manifest support Copilot runtimes that discover plugin skills through the Claude-compatible layout. A regression test prevents the mirror from drifting from the canonical [`im-not-ai-en/`](im-not-ai-en) skill.

For a Copilot plugin install, register the repository's [marketplace manifest](.claude-plugin/marketplace.json), then install the plugin from it:

```bash
copilot plugin marketplace add hyeonsangjeon/im-not-ai-en
copilot plugin install im-not-ai-en@im-not-ai-en
```

The adapter also supports the older direct-repository route:

```bash
copilot plugin install hyeonsangjeon/im-not-ai-en
```

Copilot CLI warns that direct plugin installs from repositories are deprecated. Treat that command as compatibility for existing workflows; use the marketplace commands for plugin-managed installation or `gh skill install` for a host-native personal or project skill. If a running session predates the install, use `/skills reload` or restart the Copilot/ACP process.

Maintainers can run the opt-in live regression after publishing a revision. It installs into a temporary Copilot home, confirms the plugin registry path, and then starts a fresh ACP stdio session and requires `im-not-ai-en` in the authoritative `available_commands_update` notification:

```bash
python3 tests/copilot_acp_smoke.py --install-mode direct --require-direct-deprecation-warning
python3 tests/copilot_acp_smoke.py --install-mode marketplace
```

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
├── ACKNOWLEDGMENTS.md
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── .claude/skills/im-not-ai-en/  # byte-identical Copilot compatibility mirror
├── im-not-ai-en/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/
│   │   ├── editorial-guide.md
│   │   └── sentence-copyediting.md
│   └── scripts/verify_fidelity.py
├── evals/
└── tests/
```

The canonical installable skill stays lean. Evaluation fixtures and forward-test evidence live outside it, while tests keep the Copilot compatibility mirror byte-identical to the canonical skill.

## Evaluation

The evaluation suite covers short workplace prose, medium technical explanations, long-form publication excerpts, quoted instruction-like data, focused sentence-level copyediting, mixed-dialect repair, and an already natural no-op case. All fixture contents—including every name, endpoint, vendor, date, metric, incident, and anecdote—are synthetic. They were written for this repository and are not copied, adapted, or derived from any employer, customer, internal system, production incident, or production data.

See the [evaluation protocol](evals/README.md), the [v0.1.2 copyediting evaluation notes](evals/results-v0.1.2.md), and the historical [v0.1.1 notes](evals/results-v0.1.1.md). Recorded grader scores are exploratory observations from fresh agents, not independent benchmark results; the notes identify the preserved artifacts and reproducibility limits.

`im-not-ai-en/scripts/verify_fidelity.py` adds deterministic checks for supported literals, declared protected spans, common Markdown structure, and copy-ready wrappers. Its output redacts protected values by default; use `--show-values` only when reviewing trusted, non-sensitive text. The verifier is tested on Python 3.11 and 3.12. The machine-readable [`evals/manifest.json`](evals/manifest.json) binds fixtures to their outputs and contracts. Change rate is reported, but no universal pass threshold is imposed.

These checks test editorial behavior. The verifier checks only the listed deterministic invariants; it does not evaluate grammar, naturalness, voice, or semantic equivalence, classify authorship, or measure detector scores.

## License

I'm Not AI — English is available under the [MIT License](LICENSE). The license retains attribution to `epoko77-ai` and `hyeonsangjeon`. [Acknowledgments](ACKNOWLEDGMENTS.md) records conceptual design references that are not bundled dependencies.
