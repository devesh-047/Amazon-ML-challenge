---
description: Record a completed experiment in the experiment log, verified against the actual code
argument-hint: <what was tried and the result>
---

Record this experiment:

**$ARGUMENTS**

Use the `documentation` agent. Append an entry to `docs/experiments.md`
(create the file if it does not exist) using the experiment record format from
the agent definition:

```
### EXP-<n> <short title>   (<date>)
- hypothesis:
- change from baseline:
- setup: data / features / model / seed
- metric: <name> = <value>   (validation), <value> (leaderboard if known)
- conclusion: kept | rejected | inconclusive
- artefacts: path(s)
```

Verify the setup details against the actual code and configs rather than taking
my description at face value — seed, model parameters, feature set and metric
implementation should come from the source. If my description conflicts with
what the code does, record what the code does and tell me about the discrepancy.

Number the entry sequentially after the last existing one. Do not rewrite
previous entries. If a value I gave you is unverifiable from the repository,
record it and mark it `(unverified)`.
