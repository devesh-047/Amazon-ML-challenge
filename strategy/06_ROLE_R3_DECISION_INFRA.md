# R3 — Decision Layer, Evaluation Harness, Infrastructure & Submissions

**You own the score.** R1 and R2 own upstream quality metrics; you own the only number that counts — macro
F<sub>0.5</sub> — and every artefact the organisers actually receive. You are also the integrator: the pipeline runs
end-to-end because you make it, and the submission is never rejected because you validate it.

**Your metrics:**
| Metric | Target |
|---|---|
| end-to-end val macro F<sub>0.5</sub> | 0.72 (D2 10:00) → 0.80 (D2 16:00) → 0.84 (D2 22:30) → 0.86+ (D3) |
| rejected submissions | **0** |
| gain from expected-F<sub>0.5</sub> selection alone vs the best global threshold | ≥ +0.01 (verified +0.0165 in the simulation inside `select_matches.py --selftest`) |
| additional gain from mutual exclusivity | measure it on val — unknown until real scores exist |
| full end-to-end rerun from clean checkout | works, ≤ 4 h, documented |
| AWS spend | < $25 of $100+ credits, zero forgotten resources |

---

## Why this role is not "just ops"

Two of the highest-value findings in the profile are yours to exploit, and both are decision-layer work, not modelling:

1. **Every S2/S3 record belongs to at most one S1 entity** — verified across all 7,638,365 matched IDs in the ground
   truth, zero exceptions. So if two S1 entities both claim a record, at most one is right. A global resolution pass
   is free precision.
2. **The metric is macro per-entity and precision-weighted, so the optimal *number* of predictions varies per
   entity.** Measured: for an entity with 1 true match, predicting 2 (one right) scores **0.556** instead of 1.000;
   for a true singleton, a single false positive costs the **entire** 1.0. A global probability threshold cannot
   express "this entity is probably a singleton" — expected-F<sub>0.5</sub> selection can, and 5.58% of entities are
   singletons.

Expect the decision layer to be worth more than a day of model tuning. Build it early (day 1 evening), not last.

## R3-1 First 90 minutes — unblock everyone

1. `ber/` repo, `python3 -m venv .venv` (verified working on this box), pinned `requirements.txt` from
   `02_TECHNICAL_SPEC.md` §2. **Note `pip` is not installed system-wide — the venv's ensurepip path is the one that
   works.** No `sudo`, so no apt.
2. Consider raising the WSL memory cap first: 7.9 GB is the binding constraint on this whole project. If the Windows
   host has ≥16 GB, put `[wsl2]` / `memory=12GB` / `processors=12` in `%UserProfile%\.wslconfig` and
   `wsl --shutdown`. Cheapest speedup available, ten minutes.
3. Copy `strategy/reference_code/*` into `src/eval/` and `src/decide/`. They are tested and stdlib-only.
4. **Build the validation split and publish the entity ID lists** so R1/R2 can never accidentally train on
   validation entities. Split by S1 entity, deterministic hash, country-stratified.
5. Stand up the scoring report: overall macro F<sub>0.5</sub>, plus breakdowns by country, by true cardinality
   (0,1,2,3,4,5+), by `has_addr`, and by name-script. **Also report a test-mix-reweighted score** (weights
   US 0.383 / India 0.468 / France 0.150) so model comparisons reflect the test distribution, not train's 60/40.
6. Ship the hand-weighted baseline end-to-end tonight so submission #1 exists.

## R3-2 Validation split design (get this right once)

- Split on **S1 entity**, never on pairs.
- Candidate pool for validation must be the **full train S2/S3 corpus** (all 10.3M records), not just the matches of
  validation entities. Otherwise you measure precision against an artificially sparse pool and every threshold you
  tune will be too aggressive on test.
- Size: 150–250K entities is plenty (standard error on a macro mean over 200K entities is tiny) and keeps iteration
  fast. Keep a second, smaller 25K "fast val" for minute-by-minute iteration.
- Stratify by country **and** by true cardinality so the singleton bucket is well represented.
- Remember the test pool is ~23% denser in distractors per entity (5.75 vs 4.68 S2+S3 per S1). Expect test precision
  slightly below val at the same threshold; that is what the δ safety margin is for.

## R3-3 Mutual exclusivity (`src/decide/exclusivity.py`)

Greedy pass: for each candidate ID claimed by multiple S1 entities, the highest-`p` claim keeps its score, the
losers get `p *= DEMOTE` (start at 0.25, tune on val). **Soft demotion, not hard deletion** — the winner may still be
dropped by set selection, and `p` is imperfect. One optional swap-improvement round afterwards. Skip full
bipartite optimisation: 10M nodes, and greedy + one swap round captures nearly all of the gain.

Enforce the observed caps: **≤5 S2 and ≤6 S3 per entity** (train maxima; 99%+ of entities have ≤4 of each).

## R3-4 Expected-F<sub>0.5</sub> selection (`src/decide/select.py`)

Implemented and tested in `reference_code/select_matches.py`. Per entity, with `p` sorted descending:

- `E[F(0)] = Π(1 − pᵢ)` — the probability the entity really is a singleton.
- For `k ≥ 1`, plug-in estimate with `T̂ = Σ all pᵢ`, `H = Σ_{i≤k} pᵢ`, `P̂ = H/k`, `R̂ = H/max(T̂,H)`.
- Pick `argmax k`, subject to the caps.

Validate the plug-in against the Monte-Carlo variant (200 Bernoulli draws, exact F<sub>0.5</sub> per draw) on the
fast-val split. The self-test already shows they agree to 0.0002 on simulated calibrated scores, and that both beat
the best global threshold by **+0.016** there — but **calibration is the precondition**: with uncalibrated scores
this method can *lose* to a plain threshold. If R2's reliability plot is not flat, fix calibration before trusting
the selector. If plug-in and Monte Carlo disagree materially on real data, use Monte Carlo for the final run —
1.7M entities × 200 draws is cheap and embarrassingly parallel.

Then tune, per country group, on validation: `DEMOTE`, the cap, and a **safety margin** `p ← p − δ` (or a
multiplicative shrink). Grid-search these on validation only — **never** on the leaderboard, you have 15 probes total.

Ablation to run and record (it goes straight into the methodology document):

| Config | val F<sub>0.5</sub> |
|---|---|
| best global threshold | … |
| + mutual exclusivity | … |
| + expected-F<sub>0.5</sub> selection | … |
| + per-country δ | … |

## R3-5 Emission & validation (`src/decide/emit.py`)

Hard invariants, asserted in code before any upload:
- exactly **1,732,544** data rows + header, one per test S1 entity, no duplicates, no missing entity
- `matched_entity_ids`: comma-joined, **no spaces**, no quoting, empty for singletons, no duplicates within a list
- only `S2-`/`S3-` IDs, and every ID must exist in the test files
- `matching_results.tsv` ⊆ `candidate_pairs.tsv`
- tab-separated with the exact column names

Then run the organisers' validator every single time — it is free and it catches a rejection before it costs a
submission:
```bash
cd amazon-ml-challenge-dataset/student_resource
python3 utils/validate_submission.py --matching output/matching_results.tsv \
    --candidate output/candidate_pairs.tsv --test-dir dataset/test
```
Expect `PASS` and exit 0.

## R3-6 Infrastructure & cost

Local first: 12 cores, 7.9 GB, 948 GB disk, no GPU. Chunk everything, parquet between stages, make every stage
resumable. `duckdb` for out-of-core joins and aggregations, `polars` lazy/streaming for scans.

AWS only for what local cannot do, from the $100 (+ up to $100 bonus) credits:
- **GPU embedding pass** (only if R1 adopts G4): `g4dn.xlarge` ≈ $0.53/h, 2–3 h ≈ **$1.60**.
- **Memory-heavy full-scale run**: `r6i.4xlarge` (128 GB) ≈ $1.01/h, 10–15 h ≈ **$15**.
- Use **Batch Transform, never a live endpoint**, for any SageMaker inference — endpoints bill $0.12/h continuously
  and are the standard way teams lose their credits.
- Day-1 chores: check credits (Billing → Credits) and **set a cost budget/alert** — the alert itself is worth $20 in
  bonus credits, and the other bonus activities (EC2 launch, Bedrock playground, Lambda web app) are ~$80 more if
  anyone has spare minutes.
- **Cleanup checklist after every AWS session:** delete endpoint → delete endpoint config → delete model → stop
  JupyterLab space → confirm nothing is running in EC2.

Uploading ~2 GB of data to S3 is only worth doing if you actually commit to the cloud run; otherwise keep everything
local and skip the transfer time.

## R3-7 Run discipline

`runs/RUNLOG.md`, one row per experiment and per submission: run id · git SHA · config diff · val F<sub>0.5</sub>
(overall + per country + test-mix-weighted) · mean candidates/S1 · public LB score · notes. The guidelines
*require* version history, and the val↔LB delta is the only information you will get about the public/private split.

Own the submission budget (5/day) and the schedule in `03_TIMELINE_AND_CHECKPOINTS.md`. Say no to unvalidated
probes. **Never tune on the public leaderboard** — it is a subset, the private board decides, and 15 probes is not a
validation set.

## R3-8 Final package (start at 19:00 on day 3, not 23:00)

See [`09_SUBMISSION_CHECKLIST.md`](09_SUBMISSION_CHECKLIST.md). You also own the reproducibility claim: extract the
zip into `/tmp`, follow your own README as a stranger would, and confirm both TSVs regenerate. The top teams'
packages are reviewed in detail before final rankings are confirmed — a great score with an unreproducible pipeline
is a disqualification risk, not a win.

## Definition of done

- [ ] validation split + scorer published and used by both other roles
- [ ] decision-layer ablation table filled in
- [ ] zero rejected submissions, RUNLOG complete
- [ ] final zip verified by extraction and a clean-room rerun
- [ ] AWS resources destroyed, spend confirmed in Billing
