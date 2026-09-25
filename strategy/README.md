# Amazon ML Challenge 2026 — Team Strategy

Business Entity Resolution · 3 engineers · deadline **27 Sep 2026, 23:59 IST** · metric **macro F<sub>0.5</sub>**

Everything here is grounded in measurements taken on the actual dataset, not in generic hackathon advice.

## Read in this order

| # | Doc | Who | Why |
|---|---|---|---|
| 0 | [`00_MASTER_STRATEGY.md`](00_MASTER_STRATEGY.md) | **everyone, first** | the five facts that decide the design, the architecture, the team split, milestones |
| 1 | [`01_DATA_PROFILE.md`](01_DATA_PROFILE.md) | everyone | every measured number. Do not re-derive these |
| 2 | [`02_TECHNICAL_SPEC.md`](02_TECHNICAL_SPEC.md) | everyone | repo layout, pinned deps, **frozen stage contracts**, normalisation spec, feature list, algorithms |
| 3 | [`03_TIMELINE_AND_CHECKPOINTS.md`](03_TIMELINE_AND_CHECKPOINTS.md) | everyone | hour-by-hour plan, CP-1…CP-5 gates, submission schedule, sleep rota, cut order |
| 4 | [`04_ROLE_R1_RECALL_BLOCKING.md`](04_ROLE_R1_RECALL_BLOCKING.md) | R1 | normalisation, mined maps, blocking, `candidate_pairs.tsv` |
| 5 | [`05_ROLE_R2_MODEL_FEATURES.md`](05_ROLE_R2_MODEL_FEATURES.md) | R2 | features, LightGBM, calibration, the France/LOCO experiment |
| 6 | [`06_ROLE_R3_DECISION_INFRA.md`](06_ROLE_R3_DECISION_INFRA.md) | R3 | splits, scorer, exclusivity, set selection, AWS, submissions |
| 7 | [`07_EVALUATION_PROTOCOL.md`](07_EVALUATION_PROTOCOL.md) | everyone | the metric, the splits, required slices, mandatory experiments |
| 8 | [`08_RISKS_RULES_COST.md`](08_RISKS_RULES_COST.md) | everyone | disqualification rules, licences, risk register, AWS cost, anti-patterns |
| 9 | [`09_SUBMISSION_CHECKLIST.md`](09_SUBMISSION_CHECKLIST.md) | R3 | per-upload checks, final zip, methodology-doc authoring map |
| — | [`reference_code/`](reference_code/) | R3 → all | **tested** F<sub>0.5</sub> scorer, split maker, decision layer |

## The 60-second version

**Problem.** For each of 1,732,544 test Source-1 entities, pick its matching subset of 9,969,589 Source-2/3 records.
Score is F<sub>0.5</sub> per entity, averaged over all entities, singletons included.

**Five measured facts that drive everything:**
1. F<sub>0.5</sub> punishes a false positive ~2.3× harder than a missed match, and a false merge on a true singleton
   (5.58% of entities) costs the full 1.0 for that entity.
2. Every Source-2/3 record belongs to **exactly one** Source-1 entity — verified across all 7,638,365 matched IDs.
   Global mutual exclusivity is free precision.
3. Matches never cross country (0 of 207,310 pairs) → country is a hard partition key.
4. **France is 15.0% of the test set with zero training data** → every statistic must be corpus-derived per country,
   never hard-coded.
5. Names alone cap recall at 85.5% and 39.5% of Source-1 entities share a name-token-set with another entity
   (chains) → retrieval must union name *and* address; **the address is the discriminator**.

**Architecture.** normalise → multi-generator blocking per country (char-n-gram TF-IDF on name + token TF-IDF on
address + exact key joins + embedding kNN for the cross-script residual) → prune to ~30 candidates/entity →
~60-feature LightGBM verifier trained on the real blocked candidates → calibrate → **global exclusivity + per-entity
expected-F<sub>0.5</sub> set selection** → validate → submit.

**Split of work.** R1 owns recall, R2 owns precision, R3 owns the score and every artefact the organisers receive.
The stage contracts in `02_TECHNICAL_SPEC.md` are what let three people work in parallel without blocking.

**Already measured for you:** a token-key blocker reaches **88.77%** pair recall, and cheap top-K pruning to 20
candidates retains 98.8% of that. The two-stage design is validated; the remaining recall gap is Indic-script names
(15–19% of the pool), empty addresses (~2.7%) and heavy typos.

**Suggested people mapping:** Piyush → R3 (owns the machine, the AWS account and the portal); the other two take R1
and R2. Swap freely — but keep the ownership boundaries.

## Start now

```bash
# verify the tooling works before anything else (stdlib only, no venv needed)
python3 strategy/reference_code/f05_score.py --selftest        # -> SELFTEST PASS
python3 strategy/reference_code/select_matches.py --selftest   # -> SELFTEST PASS
```

Then go to `03_TIMELINE_AND_CHECKPOINTS.md` → "Day 1, 17:00–18:30" and start your role's first task.

**Two things that will lose this competition if ignored:** chasing recall instead of precision, and leaving the
methodology document plus the reproducible zip to the last hour. Both are in the checklist for a reason.
