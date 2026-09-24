---
description: Classify a task and run it through the appropriate quality-gated pipeline
argument-hint: <task description>
---

Apply the project engineering workflow (see `.claude/skills/workflow/SKILL.md`)
to this task:

**$ARGUMENTS**

Act as the team lead. Do this in order:

1. **Classify** the task as MICRO, TRIVIAL, STANDARD, ML STANDARD or COMPLEX.
   Check the promotion triggers — anything touching train/validation/test
   splitting, metric computation, preprocessing fit boundaries, secrets, or a
   public interface is promoted regardless of apparent size.
2. **State the classification and the pipeline you will run**, in one short
   block, before delegating anything. If you are deliberately skipping a stage,
   say which and why.
3. **Delegate** to the specialist agents for that class, in order. Give each one
   the context it needs and its file ownership. Only parallelise agents that
   cannot write the same file.
4. **Enforce the gates.** Do not advance past a failed gate and do not pass a
   gate on an agent's behalf.
5. **Apply the bounded rework rules.** Track the cycle count explicitly
   (`rework cycle n/3`) and escalate to me on the 4th failure instead of
   attempting another fix.
6. **Report** at the end: what changed, what was verified, what was not
   verified, and anything I need to decide.

If the task is MICRO, just do it and say so — do not spin up the pipeline.
