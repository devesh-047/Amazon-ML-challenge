# Evaluation Protocol

Owner: **R3**. Everyone reads it. If a change is not measured with this protocol, it did not happen.

---

## 1. The metric, exactly

Per Source-1 entity, with `pred` = predicted ID set and `truth` = ground-truth ID set:

```
if truth == ∅ and pred == ∅ :  F = 1.0        # correct singleton — full credit
if truth == ∅ and pred ≠ ∅ :  F = 0.0        # any false merge on a singleton loses the whole entity
if truth ≠ ∅ and pred == ∅ :  F = 0.0
else:
    P = |pred ∩ truth| / |pred|
    R = |pred ∩ truth| / |truth|
    F = 0 if P+R == 0 else 1.25·P·R / (0.25·P + R)

score = mean(F over ALL Source-1 entities in the evaluation set)      # macro, singletons included
```

Implementation: `reference_code/f05_score.py` (tested — see §6). **Nobody re-implements this.**

## 2. What the metric's shape implies (measured)

Global trade-off at a fixed "budget":

| P | R | F<sub>0.5</sub> |
|---|---|---|
| 1.00 | 0.75 | **0.9375** |
| 0.98 | 0.80 | **0.9378** |
| 0.95 | 0.85 | 0.9282 |
| 0.90 | 0.90 | 0.9000 |
| 0.85 | 0.95 | 0.8683 |
| 0.80 | 0.98 | 0.8305 |
| 0.75 | 1.00 | 0.7895 |

Per-entity, with `T` true matches and `k` predictions (all correct up to `T`):

| T | k=0 | k=1 | k=2 | k=3 | k=4 | k=5 | k=6 |
|---|---|---|---|---|---|---|---|
| 1 | 0.000 | **1.000** | 0.556 | 0.385 | | | |
| 2 | 0.000 | 0.833 | **1.000** | 0.714 | 0.556 | | |
| 3 | 0.000 | 0.714 | 0.909 | **1.000** | 0.789 | 0.652 | |
| 4 | 0.000 | 0.625 | 0.833 | 0.938 | **1.000** | 0.833 | 0.714 |

Three conclusions that should govern every threshold decision:
1. **Over-prediction is punished harder than under-prediction.** At T=3, missing one match → 0.909; adding one false
   positive → 0.789.
2. **Predicting one fewer than the truth is cheap; predicting one more is expensive.** Lean conservative.
3. **Predicting nothing when there is something scores 0** — so do not become so conservative that you output empty
   sets for entities that have matches. 5.58% of entities are true singletons; if you emit far more empties than
   that, you have over-corrected.

## 3. Splits

| Split | Size | Purpose |
|---|---|---|
| `train` | remaining ~1.8M S1 entities | feature extraction + model fitting |
| `val` | 150–250K S1 entities | all reported numbers, all threshold tuning |
| `fastval` | 25K subset of `val` | minute-by-minute iteration |
| `calib` | 50K disjoint from both | isotonic calibration fitting only |

Rules:
- Split **on S1 entity**, deterministic (`hash(entity_id) % 1000` band), country-stratified, seed recorded.
- The validation candidate pool is the **full train S2+S3 corpus (10.3M records)**, not just the true matches of
  validation entities. Anything smaller inflates precision and every threshold you tune will be too loose on test.
- Entity IDs for each split are published as files by R3. R1 and R2 read them; nobody re-derives a split.
- Never train on `val`. Once the config is frozen on day 3, retraining on `train ∪ val` minus `fastval` is allowed —
  but only after the final thresholds are chosen.

## 4. Required reporting slices

Every reported result includes:

1. **overall macro F<sub>0.5</sub>**
2. **test-mix-reweighted F<sub>0.5</sub>** — weight country scores by the *test* mix (US 0.383 / India 0.468 /
   France 0.150; for validation, apply US/India weights renormalised) because train is 60/40 and test is not
3. per-country (US, India)
4. per true cardinality: 0, 1, 2, 3, 4, 5+ — the singleton row and the T=1 row are where decision-layer bugs show up
5. per `has_addr` (candidate side) and per name-script (latin vs non-latin)
6. pair-level precision / recall / PR-AUC, plus **mean predictions per entity** and **fraction of empty predictions**
   (compare that fraction against the 5.58% singleton prior — it is the fastest calibration sanity check you have)

## 5. Mandatory experiments

| Experiment | Question it answers | Owner |
|---|---|---|
| **Blocking recall @K** for K ∈ {10,20,30,40}, per country and per subset | where the ceiling is | R1 |
| **LOCO**: train US → eval India, train India → eval US | will France work? | R2 |
| **Calibration transfer**: fit isotonic on US, apply to India | is one calibrator enough for France? | R2 |
| **Decision-layer ablation**: threshold → +exclusivity → +expected-F<sub>0.5</sub> → +per-country δ | is the decision layer earning its complexity? | R3 |
| **Plug-in vs Monte-Carlo** expected-F<sub>0.5</sub> | is the cheap estimator good enough? | R3 |
| **Feature-family ablation** | what to write in the methodology doc | R2 |
| **Cardinality prior check**: predicted vs true match-count distribution | systematic over/under-prediction | R3 |

The cardinality-prior check is underrated: the true distribution is known (5.58% / 5.40% / 17.00% / 24.05% / 21.94% /
14.59% / 7.47% … for 0,1,2,3,4,5,6 matches). If your predicted distribution is shifted left or right of that, you
have a systematic threshold error worth several points, visible in one histogram.

## 6. Verification of the reference scorer

`reference_code/f05_score.py` was checked against the worked example in the official README
(pred = {S2-00047, S2-00193, S3-00812}, truth = {S2-00047, S3-00812} → P=2/3, R=1.0, **F=0.714**) and against the
singleton rules. Run the built-in self-test:

```bash
python3 strategy/reference_code/f05_score.py --selftest
```

It must print `SELFTEST PASS`. If you modify the scorer, the self-test must still pass — this is the one number the
entire competition is decided on, so treat it as frozen code.

## 7. Leaderboard hygiene

- 15 total submissions across 3 days. That is not a validation set; it is a smoke test. **Never tune on it.**
- Log every upload's public score against its val score in `runs/RUNLOG.md`. You are looking for *consistent
  direction*, not agreement in absolute value: if val goes up and the public LB goes down twice in a row, suspect
  the val pool density or a country-mix artefact, not noise.
- Final rankings come from the **private** leaderboard. A config that is only marginally better on the public board
  but worse on validation is the wrong choice.
