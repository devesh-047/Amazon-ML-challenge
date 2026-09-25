---
description: Run an independent ML methodology and data-leakage audit on a target
argument-hint: <file, branch, notebook, or "why is score X suspiciously high">
---

Run an ML methodology audit on:

**$ARGUMENTS**

Use the `ml-reviewer` agent. If the target is not yet understood well enough to
audit — unfamiliar data, unclear pipeline, or an unexplained score change —
delegate to `researcher` first to establish the facts, then hand those findings
to `ml-reviewer`.

Require the audit to actually verify, not merely inspect:

- Compute the intersection between train/validation/test splits rather than
  reading the split code and concluding it looks correct.
- Check where each preprocessing step is **fitted**, not just where it is applied.
- Recompute the reported metric independently against a small known example.
- Treat any large unexplained improvement as a leakage hypothesis until it has
  been ruled out, and name the most likely cause.

Report the verdict (`SOUND` / `CONCERNS` / `UNSOUND`) with evidence for every
finding, and list the checks that could not be performed.

If the verdict is `UNSOUND`, stop all related implementation work, tell me which
results are now untrustworthy, and recommend where the work should restart.
