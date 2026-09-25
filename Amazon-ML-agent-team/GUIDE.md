# 🚀 Amazon ML Agent Team — Plain-English Guide

> **What is this?** A pre-built "team of AI specialists" (Claude Code agents) that run inside your repo during the Amazon ML Challenge. Each agent has a specific job, and a set of quality gates prevents broken or leaky code from sneaking through under deadline pressure.

---

## 🗂️ What's in This Folder?

```
Amazon-ML-agent-team/
│
├── CLAUDE.md                  → The "operating agreement" every Claude session reads automatically
├── README.md                  → Full technical docs
├── GUIDE.md                   → ← You are here (plain-English overview)
├── amazon-guide-agent.md      → ML challenge reference (AWS setup, XGBoost rules, tips)
│
├── scripts/
│   └── verify-setup.sh        → Run this to check everything is wired up correctly
│
└── .claude/
    ├── agents/                → The 8 specialist AI agents
    ├── skills/workflow/       → The routing logic (who handles what)
    └── commands/              → Slash commands you can type in Claude Code
```

---

## 👥 The 8 Specialist Agents (Who Does What)

Think of these like job roles on a real engineering team:

| Agent | Job | Can Edit Code? |
|---|---|---|
| 🔍 **researcher** | Investigates the data, algorithms, and any "suspicious" metrics before anyone writes code | Research notes only |
| 📋 **planner** | Breaks work into clear sub-tasks with acceptance criteria — the blueprint the coder follows | Plan docs only |
| 💻 **coder** | Writes the actual code — exactly what the plan says, nothing more | ✅ Yes |
| 🧪 **tester** | Independently checks the code (happy path, edge cases, failures) — returns PASS / PARTIAL / FAIL | Test files only |
| 🕵️ **reviewer** | Senior code review — returns ACCEPTED / MINOR / MAJOR / REJECTED | ❌ Read-only |
| 📊 **ml-reviewer** | Checks for data leakage, dodgy metrics, and wrong methodology — returns SOUND / CONCERNS / UNSOUND | ❌ Read-only |
| 📝 **documentation** | Keeps the README, architecture docs, and experiment logs accurate | Docs only |
| 🔗 **integrator** | Merges teammates' branches safely, finds hidden conflicts, never pushes | Merge resolution |

> **Why are reviewer and ml-reviewer read-only?** So the agent judging the work is structurally unable to quietly "fix" it to make it look better. Independence is enforced by the tool configuration, not just instructions.

---

## ⚙️ How Work Flows (The Pipeline)

Every task is first **classified** by size/risk, then sent through the right pipeline. Bigger risk = more gates.

```
MICRO    → Lead handles it directly             (typos, comments, formatting)
TRIVIAL  → coder → tester                       (small, obvious changes)
STANDARD → planner → coder → tester → reviewer  (real features or bug fixes)
ML STD   → researcher → planner → coder → tester → reviewer → ml-reviewer
COMPLEX  → same as ML STD + documentation
```

### 🚨 Automatic Upgrades (Promotion Triggers)
These seemingly small changes are **always** treated as ML STANDARD, no matter how tiny:
- Anything touching train / validation / test splitting
- Changes to how metrics are calculated
- Changes to preprocessing that could "see" the test set
- Adding / removing dependencies
- Touching secrets or authentication

> A one-line change to a split function is ML STANDARD. Full stop.

---

## 🚦 Quality Gates (Blocking)

A gate **blocks progress** until it is passed. The lead cannot wave it through.

| Gate | Required For | Pass Condition |
|---|---|---|
| **Testing** | TRIVIAL and above | `tester` returns `PASS` |
| **Code Review** | STANDARD and above | `reviewer` returns `ACCEPTED` or `MINOR` (with fixes applied) |
| **ML Review** | Every ML change | `ml-reviewer` returns `SOUND` or `CONCERNS` (with corrections) |
| **Documentation** | COMPLEX work | `documentation` confirms docs match reality |

### 🛑 UNSOUND = Hard Stop
If `ml-reviewer` returns `UNSOUND`:
1. **Stop all implementation immediately.**
2. Discard any results or scores based on that work.
3. Return to planning. Do not submit that score.

---

## 🔄 Rework Rules (Preventing Infinite Loops)

| What Happened | What to Do |
|---|---|
| tester → FAIL/PARTIAL | coder fixes → tester reruns |
| reviewer → MINOR/MAJOR | coder fixes → tester reruns → reviewer rechecks |
| reviewer → REJECTED | Return to **planner** — the approach is wrong |
| ml-reviewer → CONCERNS | coder applies corrections → retest → ml-reviewer rechecks |
| ml-reviewer → UNSOUND | **Full stop** — back to planner/researcher |

**Maximum 3 rework cycles per task.** On the 4th attempt, stop and ask a human.
**Maximum 2 planning resets per task.** If the same failure recurs twice, the diagnosis — not the patch — is wrong.

---

## ⌨️ Slash Commands

Type these directly in Claude Code:

| Command | What It Does |
|---|---|
| `/workflow <describe your task>` | Classifies the task and runs the right pipeline |
| `/ml-audit <target>` | Runs an independent leakage + methodology audit (run before trusting any score!) |
| `/integrate <branch1> <branch2> ...` | Safely prepares a multi-branch merge (never pushes) |
| `/experiment-log <result>` | Records a verified experiment to `docs/experiments.md` |

---

## 📚 The ML Challenge Reference (`amazon-guide-agent.md`)

This file contains everything from the official Best Practices Virtual Session. Quick summary:

### AWS & Credits
- You start with **$100 in AWS credits**. Complete 5 activities to earn another $100.
- **Endpoints cost ~$0.12/hr** — always delete them when done.
- Training jobs auto-stop. S3 storage is essentially free.

### The ML Workflow
```
Upload Data to S3
  → EDA (check distribution, missing values, types)
  → Feature Engineering (drop IDs, encode categoricals)
  → Format for XGBoost ← CRITICAL RULES BELOW
  → Split data (67% train / 22% val / 11% test)
  → Upload splits to S3
  → Train with SageMaker
  → Tune Hyperparameters
  → Evaluate (match the leaderboard metric — often F1, not just accuracy)
  → Batch Transform for predictions (cheaper than a live endpoint)
  → Submit
  → DELETE ALL RESOURCES
```

### ⚠️ XGBoost Formatting Rules (Top Source of Errors)
1. **No column headers** in the CSV
2. **Target column must be FIRST** (column 0)
3. **Everything must be numeric** (encode all text first)

### Data Splitting
- Never look at your test set until training is completely done.
- Use a fixed `random_state` (e.g. `42`) for reproducible splits.

### Evaluation Metrics
| Metric | Plain English |
|---|---|
| Accuracy | % of all predictions correct |
| Precision | When I predict positive, am I right? |
| Recall | Did I catch all the actual positives? |
| F1 Score | Balance of precision and recall |

> **Check which metric the leaderboard uses.** Don't just optimize accuracy.

### SageMaker Features Worth Knowing
- **Batch Transform** — generate predictions from a file (no live endpoint needed, cheaper)
- **Autopilot** — auto-tries multiple algorithms for a quick baseline
- **Hyperparameter Tuning Jobs** — parallel search over hyperparameter ranges
- **Experiments** — track and compare model runs

---

## 🏃 Getting Started

### 1. Copy into your competition repo
```sh
cp -r /path/to/amazon-ml-agent-team/.claude .
cp    /path/to/amazon-ml-agent-team/CLAUDE.md .
cat   /path/to/amazon-ml-agent-team/.gitignore >> .gitignore
git add .claude CLAUDE.md .gitignore
git commit -m "Add shared Claude Code agent team and workflow"
```

### 2. Verify it's wired up
```sh
sh scripts/verify-setup.sh
```

### 3. Launch Claude Code from the repo root
```sh
cd /path/to/your/repo
claude
```

### 4. Start working
- Describe your task, and the team lead (main Claude session) will classify and route it.
- Or type `/workflow <task>` to force explicit pipeline routing.

---

## 🔒 Git Safety Rules

Agents will **never** automatically:
- `git push` (or force push)
- `git reset --hard` or `git clean -f`
- Delete branches
- Rewrite history (`rebase`, `amend`)
- Commit secrets, `.env` files, or large data files

Read-only git commands (`status`, `log`, `diff`) are always fine. **You own the remote and the final merge.**

---

## 🧑‍🤝‍🧑 Working as a Human Team

1. Everyone clones the repo — they all get the same agents automatically.
2. Work on your own branch, never commit to `main`.
3. **Declare file ownership** in team chat before starting (avoid two people editing the same file).
4. Log every experiment with `/experiment-log` so teammates don't re-run dead ends.
5. **Run `/ml-audit` before trusting any score.** A leaked score misleads the whole team.
6. Keep data files out of git (the `.gitignore` handles this).
7. Use `/integrate` when combining branches — it catches "semantic conflicts" that git merges cleanly but that break the model.
8. A human does the final merge and push — never the agents.

---

## ❓ Common Problems

| Problem | Fix |
|---|---|
| Agents don't appear / `/agents` lists nothing | Start `claude` from the repo root (the folder with `.claude/` in it) |
| `CLAUDE.md` seems ignored | It must be at the repo root, not a subdirectory |
| A slash command isn't found | Check `.claude/commands/<name>.md` exists and has valid `---` frontmatter |
| Reviewer tried to edit code | Correct — it can't. Route the fix to `coder`. |
| Pipeline running on a typo | Say "this is MICRO" explicitly |
| Rework looping past 3 cycles | Interrupt and escalate to a human — the diagnosis is wrong, not the latest patch |
