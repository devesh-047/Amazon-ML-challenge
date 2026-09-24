---
name: workflow
description: "Engineering workflow for this Amazon ML Challenge project: how to classify a task, which specialist agents to delegate to, when to parallelise, the testing/review/ML-review quality gates, bounded rework rules, integration procedure and human escalation rules. Use whenever a task involves implementation, ML/data work, debugging a suspicious result, or combining multiple contributions."
---

# Engineering Workflow

This skill tells the **lead session** how to route work. It does not replace the
lead's judgement and it does not replace native delegation — it constrains it so
the team gets quality gates without burning the time budget on ceremony.

## The one rule that matters most

**Cost must match risk.** Running a six-agent pipeline on a typo is as much a
failure as pushing an unreviewed model change. Classify first, then spend.

---

## 1. Task classification

Classify every incoming request before acting. When a task sits between two
classes, pick the **higher** one only if the cost of being wrong is real
(correctness, data integrity, security, leaderboard validity); otherwise pick the
lower one.

| Class | Looks like | Pipeline |
|---|---|---|
| **MICRO** | Typo, comment, rename in one place, formatting, docstring. No logic change. | Lead handles directly. No delegation. |
| **TRIVIAL** | Small isolated implementation in one file; obvious approach; low blast radius. | `coder` → `tester` |
| **STANDARD** | A meaningful feature or non-obvious bug fix; multiple files; real design choices. | `planner` → `coder` → `tester` → `reviewer` |
| **ML STANDARD** | Any change to data handling, features, training, evaluation, or inference. | `researcher` → `planner` → `coder` → `tester` → `reviewer` → `ml-reviewer` |
| **COMPLEX** | Architecture, major feature, significant ML pipeline, or security-sensitive work. | `researcher` → `planner` → `coder` → `tester` → `reviewer` → `ml-reviewer` → `documentation` |

**Promotion triggers** — upgrade the class regardless of apparent size if the
task touches: train/validation/test splitting, metric computation, preprocessing
fit boundaries, authentication, secrets, dependency versions, or a public
interface other code depends on. A one-line change to a split function is
`ML STANDARD`, not `MICRO`.

**Non-implementation tasks** route directly — skip the pipeline:

| Request | Route |
|---|---|
| "Why is the validation score suspiciously high?" | `researcher` → `ml-reviewer` |
| "Explain how X works" | Lead reads and answers. No delegation. |
| "Review this branch" | `reviewer` (+ `ml-reviewer` if ML) |
| "Combine three teammates' branches" | `integrator` |
| "Document the experiment we just ran" | `documentation` |

---

## 2. When to research

**Do** delegate to `researcher` when: the data is not yet understood; the correct
algorithm/library/API is genuinely open; a result looks implausible; or an
external specification must be confirmed.

**Do not** when: the repository already answers the question; the task is a
mechanical change; or research would just restate common knowledge. Reading two
files yourself is faster than a research cycle.

## 3. When to plan

Plan for `STANDARD` and above, and for anything spanning more than about three
files or involving a design choice that would be expensive to reverse.

Skip planning for `MICRO`/`TRIVIAL`. A plan for a one-file change is overhead.

An approved plan is the **contract** for the coder. If the coder reports the plan
is wrong, return to the planner — do not let the coder improvise a new design.

## 4. When to delegate vs. act directly

Use **ordinary subagents** when the task is small, work is sequential, only one
specialist is needed, there is little benefit from inter-agent communication, or
creating a full team would add unnecessary overhead.

Use **Claude Code Agent Teams** when multiple independent tasks can run
concurrently, multiple specialists need separate context windows, specialists
need to communicate with each other, the task is sufficiently complex to justify
team overhead, or parallel research or implementation provides a meaningful
benefit. Do not create an Agent Team merely because multiple agents exist.

Examples:

- **"Fix a typo"** → the main Claude Code session handles it directly.
- **"Add a small API endpoint"** → `planner` → `coder` → `tester`, using ordinary
  subagent delegation if appropriate.
- **"Improve the ML model and investigate why validation performance is poor"** →
  an Agent Team may be appropriate: `researcher`, data/ML specialist, `planner`,
  and `ml-reviewer`. Continue through the normal quality pipeline.

Delegate when the work benefits from **independence** (testing, review), from
**focus** (a large implementation), or from a **separate context budget** (broad
research).

Act directly for `MICRO` work, for questions, and for reading/summarising. A
subagent has to rediscover context you already hold; that is a real cost.

**Independence is structural, not optional.** The agent that wrote the code must
never be the agent that approves it. Never review your own implementation as the
lead either — that is what `reviewer` and `ml-reviewer` exist for.

Agent Teams are a runtime Claude Code capability. The project repository provides
the specialist definitions and workflow rules; it does not define a persistent
team configuration.

---

## 5. Parallelisation

### Safe to run concurrently

- Independent research questions
- Independent documentation tasks
- Independent analysis or audits (a `reviewer` and an `ml-reviewer` reading the
  same finished diff is safe — both are read-only)
- Tests that touch separate test files
- Implementation subtasks with **explicitly disjoint file ownership**, as
  declared in the plan

### Never run concurrently

- Two agents that may write the same file
- A task that depends on another's output
- Work that mutates shared state (a config file, a registry, a checkpoint dir, a
  migration sequence)
- Database or schema changes — always sequential
- Anything requiring a **single architectural decision**; two agents deciding
  independently produces two incompatible halves
- Training runs competing for the same GPU or memory

### Before parallelising, confirm

1. Each agent's file ownership is written down and the sets do not intersect.
2. No agent needs another's result.
3. Merging the outputs requires no judgement call.

If any answer is unclear, run sequentially. A serial pipeline that works beats a
parallel one that corrupts state at 3am before the deadline.

---

## 6. Quality gates

A gate is **blocking**. Work does not advance past a gate that has not been
passed, and the lead does not pass a gate on the agent's behalf.

### Testing gate
Required for every `TRIVIAL`+ change. `tester` must return `PASS`.
`PARTIAL`/`FAIL` → rework. A `PASS` claimed without executed tests is not a pass;
if tests could not run, treat it as `PARTIAL` and escalate the environment
problem to the human.

### Review gate
Required for `STANDARD`+. `reviewer` must return `ACCEPTED` (or `MINOR` with the
fixes applied and retested). The reviewer is read-only by design; route its fixes
to `coder`.

### ML review gate
Required for **every** `ML STANDARD`+ change, and any time a metric moves
unexpectedly. `ml-reviewer` must return `SOUND` (or `CONCERNS` with corrections
applied).

`UNSOUND` is a **hard stop**: halt implementation progression immediately and
return to `planner`/`researcher`. Do not continue optimising a number that has
been shown to be invalid, and do not report that score to teammates or submit it.

### Documentation gate
Required for `COMPLEX` work and for any experiment whose result the team will
rely on later.

---

## 7. Rework rules (bounded)

| Trigger | Action |
|---|---|
| `tester` → `FAIL` or `PARTIAL` | `coder` fixes → `tester` reruns |
| `reviewer` → `MINOR` | `coder` fixes → `tester` reruns → `reviewer` rechecks |
| `reviewer` → `MAJOR` | `coder` fixes → `tester` reruns → `reviewer` rechecks |
| `reviewer` → `REJECTED` | Return to `planner` — the approach itself is wrong. Do not patch the diff. |
| `ml-reviewer` → `CONCERNS` | `coder` applies corrections → `tester` reruns → `ml-reviewer` rechecks |
| `ml-reviewer` → `UNSOUND` | **Stop.** Return to `planner`/`researcher`. Discard affected results. |

### Loop termination — mandatory

**What counts as a cycle.** A rework cycle is **any return of the task to `coder`
for a fix**, no matter which gate sent it back and no matter how short the loop.
A `tester` `FAIL` → `coder` → `tester` round trip is one cycle, exactly like a
full fix → retest → review recheck. There is no rework path that does not
increment the counter.

- **Maximum 3 rework cycles** per task.
- On the **4th** time the task would return to `coder`, **stop and escalate to the
  human.** Do not start a 4th fix attempt.
- **Track the count in your response every time**, as `rework cycle n/3`. If you
  cannot state the current count — because context was compacted, or because you
  have lost track — treat the count as **exhausted** and escalate. Guessing low
  is how loops happen.
- If the same failure recurs twice, stop tweaking: the diagnosis is wrong, not
  the patch. Re-examine the root cause or return to the planner. Two failed
  attempts at the same fix means the model of the problem is wrong.
- A `REJECTED` or `UNSOUND` verdict **resets to the planning stage** and does not
  itself consume a rework cycle — but it does **not** zero the counter either.
  The count carries across planning resets, so total fix attempts on one task can
  never exceed 3.
- **At most 2 planning resets** per task. The second `REJECTED`/`UNSOUND` on the
  same task is itself an escalation trigger, independent of the cycle count.

Together these give a hard bound: at most 3 fix attempts and at most 2 planning
resets before a human is involved. Infinite loops are a failure mode to design
against, not an edge case. When in doubt, escalate early — a human decision costs
minutes; a loop costs the deadline.

---

## 8. Integration procedure

Use `integrator` when contributions from multiple humans, branches, or agent
teams must be combined.

1. Record the **pre-integration baseline** test result. Without it, regressions
   cannot be attributed.
2. `integrator` enumerates contributions and builds the file-overlap map.
3. Identify textual **and semantic** conflicts. Clean merges with incompatible
   assumptions are the real risk.
4. Establish merge order: foundational/shared changes first.
5. Run the full relevant suite on the integrated state.
6. Compare against the baseline; investigate every new failure.
7. Confirm documentation still matches the combined state.
8. Produce the 8-section integration report.

The integrator prepares and verifies. **The human performs the push and the final
merge.** Status is `READY`, `READY WITH CAVEATS` or `BLOCKED` — never "merged".

---

## 9. Human escalation rules

Stop and ask the human when:

- The 3-cycle rework limit is reached.
- `ml-reviewer` returns `UNSOUND`, or leakage/contamination is confirmed.
- `reviewer` returns `REJECTED` twice on the same task.
- The plan has `Blocking unknowns` that only the human can resolve.
- A required change is **destructive or irreversible**: git history rewrite,
  force push, branch deletion, dropping data, deleting checkpoints or artefacts.
- Scope would have to expand meaningfully beyond what was requested.
- A dependency must be added, upgraded, or removed.
- Anything touches secrets, credentials, `.env`, or access control.
- The work would alter another teammate's branch or shared state.
- Submitting to the competition leaderboard, or anything externally visible.
- Two specialists disagree and the resolution is a judgement call about
  priorities rather than a fact.
- The remaining time budget will not fit the correct approach, so a trade-off
  must be chosen deliberately.

When escalating, give the human: what happened, what you tried, the specific
decision you need, and the options with their trade-offs. "It failed, please
advise" is not an escalation.

---

## 10. Lead session checklist

For every non-trivial request:

- [ ] Classified the task, and stated the class and pipeline in my response
- [ ] Checked promotion triggers (splits, metrics, preprocessing, secrets, APIs)
- [ ] Skipped stages that add no value for this class
- [ ] Gave each delegated agent the context it needs and its file ownership
- [ ] Did not parallelise agents that could write the same file
- [ ] Did not approve a gate on an agent's behalf
- [ ] Tracked the rework cycle count
- [ ] Escalated rather than looping
- [ ] Reported what was verified, and what was not
