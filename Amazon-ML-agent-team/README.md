# Amazon ML Claude Agent Team

A portable, project-level Claude Code agent system for an Amazon ML Challenge
hackathon team. Copy `.claude/` and `CLAUDE.md` into your competition repository,
commit them, and every teammate gets the same specialists, the same quality gates
and the same safety rules.

## Purpose

Hackathons fail in two predictable ways:

1. **Unverified work.** Under deadline pressure, "it probably works" becomes
   "it works", and nobody notices until submission.
2. **Invalid results.** A data leak produces a great validation score, the team
   trusts it, builds on it, and the leaderboard disagrees.

This template addresses both structurally rather than by good intentions: the
agents that verify work are given **no file-editing tools**, and ML methodology
gets a dedicated auditor separate from code review. See
*How far the read-only restriction actually goes* for precisely how much of that
is enforced by configuration and how much by instruction.

## Architecture

Two complementary layers.

### Layer 1 — orchestration (the lead delegates to specialists)

```
                        TEAM LEAD
                    (main Claude session)
                            |
        +-------------------+-------------------+
        |                   |                   |
     RESEARCH          DEVELOPMENT           REVIEW
        |                   |                   |
   researcher            coder              reviewer
                         tester            ml-reviewer
                                           documentation
                                            integrator
```

The main session classifies the task and delegates to the specialists it needs.
It does not do their jobs, and it does not approve their work.

### Layer 2 — quality pipeline (gates that block progression)

```
Research → Plan → Implement → Test → Code Review → ML Review
                                  ↑        |            |
                                  |        v            v
                                  +-- Fix / Retest  (UNSOUND → stop)
                                           |
                                           v
                                    Document → Integrate
```

Gates are blocking. Rework is bounded at **3 cycles**, then a human decides.

## Agent roles

All eight live in `.claude/agents/`.

| Agent | Role | Write access |
|---|---|---|
| `researcher` | Requirements, repo state, datasets, algorithms, evaluation methodology. Separates fact from hypothesis. | Research notes only |
| `planner` | Decomposes into executable subtasks with dependencies, file ownership, acceptance criteria. Flags blocking unknowns instead of inventing them. | Plan docs only |
| `coder` | Implements exactly one assigned task. Minimal diffs, reuses existing abstractions, no silent scope creep. | Yes |
| `tester` | Independent verification: happy path, edge cases, failure cases, regressions. Returns PASS/PARTIAL/FAIL. | Test files only |
| `reviewer` | Independent senior code review with severity-tagged findings. ACCEPTED/MINOR/MAJOR/REJECTED. | **None — read-only** |
| `ml-reviewer` | Independent ML methodology and leakage audit. SOUND/CONCERNS/UNSOUND. | **None — read-only** |
| `documentation` | Keeps README, architecture, experiment and model docs matching reality. | Docs only |
| `integrator` | Combines branches/PRs, finds textual *and semantic* conflicts, verifies, reports. Never pushes. | Merge resolution |

### How far the read-only restriction actually goes

`reviewer` and `ml-reviewer` are declared `tools: Read, Grep, Glob, Bash`. They
have **no `Write` and no `Edit` tool**, so they cannot edit a file through the
normal editing path — that part is enforced by frontmatter, not by instruction.

They do have `Bash`, because they need it for real work: `git diff`, running the
existing suite to observe output, and — for `ml-reviewer` — actually computing the
intersection between data splits rather than eyeballing the split code. A shell
can in principle write files, so their instruction to use `Bash` for read-only
inspection only is a **behavioural** restriction, not a hard one.

In practice this is the right trade: removing `Bash` would make the ML audit
unable to verify anything, which defeats the purpose of the role. If you want
hard enforcement, your Claude Code version's permission settings can deny
specific `Bash` patterns — check `/permissions` in your installed version for the
syntax it supports. Nothing like that is shipped here, because it would be
unverified configuration.

## Workflow

| Class | Trigger | Pipeline |
|---|---|---|
| MICRO | Typo, comment, formatting; no logic change | Lead handles directly |
| TRIVIAL | Small isolated implementation | `coder` → `tester` |
| STANDARD | Meaningful feature or non-obvious fix | `planner` → `coder` → `tester` → `reviewer` |
| ML STANDARD | Any data/feature/training/evaluation/inference change | `researcher` → `planner` → `coder` → `tester` → `reviewer` → `ml-reviewer` |
| COMPLEX | Architecture, major feature, significant ML pipeline, security-sensitive | + `documentation` |

Full rules, parallelisation constraints, rework table and escalation triggers:
`.claude/skills/workflow/SKILL.md`.

## Slash commands

| Command | Does |
|---|---|
| `/workflow <task>` | Classify the task and run the appropriate gated pipeline |
| `/ml-audit <target>` | Independent methodology + leakage audit (use before trusting any score) |
| `/integrate <branches>` | Inspect and prepare an integration; never pushes |
| `/experiment-log <result>` | Append a verified experiment record to `docs/experiments.md` |

## How to copy this into an existing project

Two directories and one file are all that matter.

```sh
# from the root of your competition repo
cp -r /path/to/amazon-ml-agent-team/.claude .
cp    /path/to/amazon-ml-agent-team/CLAUDE.md .

# merge the ignore rules rather than overwriting an existing .gitignore
cat /path/to/amazon-ml-agent-team/.gitignore >> .gitignore

# optional: bring the validator along so teammates can re-check their checkout
mkdir -p scripts && cp /path/to/amazon-ml-agent-team/scripts/verify-setup.sh scripts/

git add .claude CLAUDE.md .gitignore
git commit -m "Add shared Claude Code agent team and workflow"
```

Only `.claude/` and `CLAUDE.md` are required — the workflow has no dependency on
the script or on this folder remaining anywhere on disk.

If the target repo already has a `CLAUDE.md`, merge the two by hand — keep the
project's build/test commands and add the workflow sections from this one.

There is nothing to install, no dependency to add, and no build step. The system
is plain Markdown read by Claude Code at session start.

> `cp`/`cat` assume a POSIX shell (Linux, macOS, WSL, or Git Bash). On native
> Windows PowerShell use `Copy-Item -Recurse .claude .` and
> `Get-Content ... | Add-Content .gitignore`.

> If your existing `.gitignore` already contains a bare `data/` line, delete it
> after appending. A directory excluded by `data/` is never descended into, so the
> appended `!**/data/.gitkeep` negation would silently have no effect.

## How to use it with Claude Code

```sh
cd /path/to/your/repo   # must be the repo root
claude
```

Start from the **repository root** — the directory holding `.claude/` and
`CLAUDE.md`. That is the layout project-level configuration is designed around.
Exactly how far Claude Code searches upward from a subdirectory varies between
versions, so launching from the root removes the variable entirely rather than
relying on discovery behaviour this template could not verify.

Then either describe your task normally (the lead applies `CLAUDE.md`
automatically) or invoke `/workflow <task>` to force explicit classification.

Verify the setup first:

```sh
sh scripts/verify-setup.sh
```

This checks the file structure and frontmatter, and probes your installed Claude
Code for which native features it exposes. Run it on the machine that actually
has Claude Code installed.

## Claude Code Agent Teams

Agent Teams are a native Claude Code runtime capability. They are created
dynamically at runtime by Claude Code; they are not a persistent repository
configuration. The repository provides shared specialist definitions under
`.claude/agents/`, and the main Claude Code session can act as the team lead.

Use Agent Teams selectively for complex or parallel work when multiple
independent specialists need to work concurrently, maintain separate context
windows, or communicate directly. Ordinary subagents remain appropriate for
simple, sequential work where a full team would add unnecessary overhead.

Agent Team runtime state and configuration are not committed to Git. On
installations that require the current experimental enablement mechanism, set:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

This is an environment setting, not repository configuration. Verify the exact
enablement mechanism and team-related commands supported by the Claude Code
version installed on your machine.

## How the CCMA-style quality pipeline works

The staged pipeline, the severity-tagged verdicts and the bounded rework loop are
**inspired by CCMA-style structured engineering workflows**, adapted for this
project. The mechanics:

1. **Classification gates spending.** Five classes; trivial work skips stages.
   Ceremony on a typo costs the same budget as real engineering.
2. **Verification is structurally independent.** `reviewer` and `ml-reviewer` have
   no `Write`/`Edit` tool, so the agent judging the work is not the agent that can
   quietly patch it. That removes the incentive to judge leniently. (See the
   caveat above on `Bash`.)
3. **Verdicts are enumerated, not prose.** `PASS`/`PARTIAL`/`FAIL`,
   `ACCEPTED`/`MINOR`/`MAJOR`/`REJECTED`, `SOUND`/`CONCERNS`/`UNSOUND`. A
   discrete verdict is auditable; "looks good to me" is not.
4. **Rework is bounded.** 3 cycles, tracked explicitly, then human escalation.
   `REJECTED` and `UNSOUND` return to planning rather than patching the diff.
5. **ML methodology is a first-class gate.** Separate from code review, because
   well-written code can still produce a meaningless number.

### This is not the CCMA project

This folder is an **independent, project-specific workflow** that borrows ideas
from CCMA-style structured engineering pipelines. It is not the official CCMA
project, not a fork of it, not affiliated with it, and not a redistribution of
its content. Nothing here was copied from it. Where CCMA-style practice did not
fit a short ML hackathon, it was dropped rather than reproduced for fidelity.

### Provenance — what comes from where

| Layer | What it is | Status |
|---|---|---|
| `.claude/agents/*.md` | Native Claude Code subagent definitions | **Native feature**, our content |
| `.claude/skills/workflow/SKILL.md` | Native Claude Code skill | **Native feature**, our content |
| `.claude/commands/*.md` | Native Claude Code slash commands | **Native feature**, our content |
| `CLAUDE.md` | Native project-instruction file | **Native feature**, our content |
| Task classification, gates, verdict vocabularies, 3-cycle limit | Instructions we wrote | **Our convention**, CCMA-*inspired* |
| Agent Teams coordination | Native, version-dependent | **Unverified here** — see above |
| `scripts/verify-setup.sh` | Our validation script | **Ours**, not a Claude Code feature |

No hooks and no `settings.json` are included. They were not needed for this
workflow, and shipping machine-specific settings into a shared repository risks
breaking teammates' configurations.

## How multiple human teammates should use the repository

The full ten-step procedure is in `CLAUDE.md` → *How to work as a human team*.
The short version:

1. Clone; pull `.claude/` and `CLAUDE.md` — everyone runs identical agents.
2. Work on a dedicated branch; never commit to `main`.
3. Start `claude` from the repo root.
4. Use the lead (or `/workflow`); let the specialists do their roles.
5. Commit focused changes; open small PRs.
6. Use `/integrate` when combining work; a human does the merge and push.

Conventions that prevent the common collisions:

- **Declare file ownership** in team chat before starting, so two people do not
  edit the same module in parallel.
- **Log every experiment** with `/experiment-log` so nobody re-runs a dead end.
- **Never submit a surprising score.** Run `/ml-audit` first.
- **Keep data out of git.** The provided `.gitignore` covers datasets,
  checkpoints and submissions.

## How the integrator is used

When several teammates have branches to combine:

```
/integrate feat/features-v2 feat/lgbm-tuning fix/split-leak
```

The `integrator` will:

1. Record a **pre-integration test baseline** so regressions are attributable.
2. Enumerate each contribution and build a **file-overlap map**.
3. Find **textual and semantic** conflicts. Semantic ones — two branches that
   merge cleanly but assume different column names, config keys, signatures or
   seeds — are the dangerous class, because git issues no warning.
4. Determine merge order, foundational changes first.
5. Run the full suite on the integrated state and compare to baseline.
6. Confirm documentation still matches.
7. Emit an 8-section report ending `READY`, `READY WITH CAVEATS` or `BLOCKED`.

It will not merge unsound work, and it will **never push**. Declining a
contribution and sending it back to its author is a valid outcome.

## Git safety

Agents never perform destructive or remote-affecting git operations
automatically. Prohibited without explicit, per-instance human instruction:

- `git push`, and force push under any circumstances
- `reset --hard`, `clean -f`
- branch deletion
- history rewrites (`rebase`, `commit --amend`, `filter-branch`)
- overwriting another person's branch
- committing secrets, `.env` files, or large data artefacts

Read-only inspection (`status`, `log`, `diff`, `show`, `branch --list`) is always
allowed. **Creating commits requires you to ask for it.** You own the remote and
the final merge.

## OmniRouter compatibility

This template is configuration-inert with respect to model routing:

- **No `model:` key appears in any agent, skill or command.** Every agent runs on
  whatever model your Claude Code installation routes to. No agent requests
  Opus, Sonnet, or any specific Anthropic model, so nothing here assumes a paid
  Anthropic subscription.
- **Nothing touches** API keys, environment variables, OmniRouter configuration,
  model routing, your Claude Code installation, or global Claude config
  (`~/.claude/`). Everything added is project-local Markdown under `.claude/`
  plus `CLAUDE.md`.
- **No `settings.json` and no hooks** are shipped, so there is nothing to
  conflict with your existing setup.

If your installation does support per-agent model selection and you want a
cheaper model for mechanical work, add it yourself — it is one frontmatter line
per agent. It is deliberately left out so the template works on any routed
backend. A reasonable split, if you choose to do it: heavier model for
`researcher`, `planner`, `reviewer`, `ml-reviewer`; lighter for `coder`,
`tester`, `documentation`.

Because routing may point at a non-Anthropic model, treat per-agent instruction
following as the variable to watch. Role boundaries fall into two tiers, and it
matters which is which:

- **Enforced by configuration.** `reviewer` and `ml-reviewer` have no `Write`/`Edit`
  tool, so a weaker model cannot edit files through the editing path even if it
  ignores its instructions.
- **Enforced by prompt only.** Everything else — `tester` limiting itself to test
  files, `planner`/`researcher` writing only under `docs/`, and the reviewers
  using `Bash` read-only — depends on the model actually following instructions.
  `tester` in particular holds full `Write`/`Edit` (it must, to write tests), so
  its "never edit production code to make a test pass" rule is behavioural.

If you route to a weaker model, the practical consequence is: check the tester's
diff. That is where a lenient model is most likely to cross a line, and it is the
one independence gate not backed by tool restrictions.

## Troubleshooting

**Agents do not appear / `/agents` lists nothing.**
Most likely you started `claude` from somewhere other than the repository root.
Relaunch from the directory that contains `.claude/`, and confirm
`.claude/agents/` is present there. Also check the frontmatter parses and that
each agent's `name` matches its filename — `sh scripts/verify-setup.sh` checks
both.

**`CLAUDE.md` seems to be ignored.**
It must be at the repo root, next to `.claude/`. Check you are not in a
subdirectory and that the file is not gitignored.

**A slash command is not found.**
Command name comes from the filename: `.claude/commands/workflow.md` → `/workflow`.
Check the file exists and its frontmatter is valid YAML (`---` delimiters on their
own lines).

**The skill never activates.**
Skills are selected from their `description`. Reference it explicitly — "apply the
workflow skill" — or use `/workflow`, which points at it directly.

**A reviewer tried to edit code.**
It has no `Write`/`Edit` tool, so the normal editing path is blocked (its `Bash`
access is restricted by instruction only — see *How far the read-only restriction
actually goes*). If a reviewer asks you to apply a fix, that is correct
behaviour — route it to `coder`.

**The pipeline runs on trivial changes.**
Say the class explicitly: "this is MICRO, just fix the typo." If it keeps
over-escalating, the promotion triggers in the workflow skill are being read too
broadly — tighten them for your repo.

**Rework is looping.**
It should stop at 3 cycles. If it does not, interrupt and escalate manually, then
check that the lead is tracking `rework cycle n/3`. Repeated identical failures
mean the diagnosis is wrong, not the patch.

**Agent Teams commands do not exist in my version.**
Expected on older builds — see *How Agent Teams fit into the architecture*. The
pipeline runs sequentially instead; no gate is lost.

**Tests "pass" but nothing was run.**
Ask for the exact command and its output. `tester` is instructed that an
unexecuted suite is `PARTIAL`, never `PASS`. Hold it to that.

## Repository layout

```
amazon-ml-agent-team/
├── CLAUDE.md                     # Operating agreement for every session
├── README.md                     # This file
├── .gitignore                    # Secrets, data and artefact exclusions
├── scripts/
│   └── verify-setup.sh           # Structure validation + capability probe
└── .claude/
    ├── agents/
    │   ├── researcher.md
    │   ├── planner.md
    │   ├── coder.md
    │   ├── tester.md
    │   ├── reviewer.md
    │   ├── ml-reviewer.md
    │   ├── documentation.md
    │   └── integrator.md
    ├── skills/
    │   └── workflow/
    │       └── SKILL.md
    └── commands/
        ├── workflow.md
        ├── ml-audit.md
        ├── integrate.md
        └── experiment-log.md
```
