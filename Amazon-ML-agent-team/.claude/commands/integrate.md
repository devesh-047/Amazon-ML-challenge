---
description: Inspect and prepare the integration of multiple branches or PRs (never pushes)
argument-hint: <branch names, PR numbers, or "all open teammate branches">
---

Integrate these contributions:

**$ARGUMENTS**

Use the `integrator` agent and follow the integration procedure in
`.claude/skills/workflow/SKILL.md`.

Before merging anything, capture the **pre-integration baseline** test result so
regressions can be attributed.

Look for semantic conflicts, not only textual ones: contributions that merge
cleanly but assume different function signatures, config keys, column names,
data schemas, seeds, or directory layouts. Those are the ones git will not warn
about.

Produce the full 8-section integration report, ending with status `READY`,
`READY WITH CAVEATS` or `BLOCKED`.

**Git safety applies absolutely.** Inspect and verify only. Do not push, force
push, reset `--hard`, `clean -f`, rebase, amend, delete branches, rewrite
history, or overwrite anyone's branch. Do not commit secrets, `.env` files, or
large data artefacts. Do not create commits unless I explicitly ask in this
conversation. If you used `git merge --no-commit` to probe conflicts, say so
prominently so I know the working tree state.

If a contribution is unsound, conflicts irreconcilably, or lacks tests,
recommend sending it back to its author rather than merging it.
