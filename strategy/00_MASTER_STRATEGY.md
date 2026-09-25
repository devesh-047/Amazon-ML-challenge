# Master Strategy — Amazon ML Challenge 2026: Business Entity Resolution

**Team size:** 3 ML engineers · **Window:** 25 Sep 00:00 IST → 27 Sep 23:59 IST · **Metric:** macro-averaged F<sub>0.5</sub> per Source-1 entity

Everything in this document is grounded in measurements taken on the actual dataset. The raw numbers are in
[`01_DATA_PROFILE.md`](01_DATA_PROFILE.md) — read that before arguing with any design decision here.

---

## 1. What the task actually is

For each of **1,732,544 test Source-1 entities**, output the subset of **9,969,589 Source-2/Source-3 test records**
that refer to the same real business. Score = F<sub>0.5</sub> computed *per S1 entity* and then averaged over all
entities (singletons included, worth 1.0 each when correctly left empty).

This is a **retrieval + verification + set-selection** problem, not a classification problem. Three separable
sub-problems, which is exactly how we split the work:

| Sub-problem | What determines the score | Owner |
|---|---|---|
| **Candidate generation (recall ceiling)** | You cannot match what you never retrieve | **R1** |
| **Pairwise verification (precision)** | Distinguishing "same business" from "same-looking business" | **R2** |
| **Set selection + global constraints (the actual metric)** | Converting probabilities into the subset that maximises expected F<sub>0.5</sub> | **R3** |

## 2. The five facts that decide our design

1. **F<sub>0.5</sub> is brutally precision-weighted, and it is macro per entity.**
   Measured: `P=0.95,R=0.85 → 0.9282` but `P=0.85,R=0.95 → 0.8683`. For an entity with 3 true matches,
   *missing one* costs 0.091 while *adding one false positive* costs 0.211 — **a false positive is ~2.3× worse
   than a false negative**. For an entity with 1 true match, predicting 2 records (1 right) scores **0.556**
   versus 1.000 for predicting just the right one.
   → **We tune for precision and we select per-entity set sizes by expected-F<sub>0.5</sub>, not by a single global threshold.**

2. **Each Source-2/Source-3 record belongs to at most ONE Source-1 entity.** Verified over all 7,638,365 matched
   IDs in the ground truth: every single one appears in exactly one S1 entity's list.
   → **A global mutual-exclusivity / assignment pass is legitimate and is free precision.** If two S1 entities both
   claim the same S2 record, at most one is right.

3. **Matches never cross country.** 207,310 true pairs checked, zero cross-country.
   → **`country` is a hard partition key.** Never generate a cross-country candidate. This also cuts the search
   space by ~2.6×.

4. **The test set has a country we have never seen: France, 259,452 S1 entities (15.0%).** Train is US+India only.
   Country mix also shifts (train US 60/India 40 → test US 38 / India 47 / France 15).
   → **No country one-hots, no country-specific hard-coded rules as the primary path.** Every statistic (IDF,
   stop-tokens, abbreviation maps) must be *computed per country from the provided corpus itself*, so France gets
   its own automatically. We validate this with a leave-one-country-out experiment (train US → test India).

5. **Names alone cap recall at 85.5%, and 39.5% of S1 entities share their name-token-set with another S1 entity.**
   14.5% of true pairs share **zero** name tokens (Indic-script names, domain-style names, DBA renames), but only
   4.4% share zero address tokens. Meanwhile "Primary Care Group" appears 259 times in S1.
   → **Candidate generation must be a union of name-based and address-based retrieval**, and **the address is the
   discriminator, not the name.** Any model that leans on name similarity alone will over-merge chains.

## 3. Architecture

```
                 ┌──────────────────────────────────────────────────────────┐
                 │ STAGE 0  Normalisation (shared, R1 owns)                 │
                 │ unicode fold · case · punct · learned abbrev./translit.  │
                 │ maps mined from the 7.6M labelled GT pairs               │
                 └──────────────────────────────────────────────────────────┘
                                        │
   ┌────────────────────────────────────┴─────────────────────────────────────┐
   │ STAGE 1  Candidate generation, partitioned by country     (R1)           │
   │  a. char 3–4-gram TF-IDF cosine top-K on name      (typos, translit.)    │
   │  b. token TF-IDF cosine top-K on address           (the discriminator)   │
   │  c. exact/near key joins: (street-number, rare street token, city)       │
   │  d. multilingual embedding kNN — ONLY for records with no lexical hook    │
   │     (Indic-script names, empty address, domain-style names) ≈15% of pool  │
   │  → union, then cheap IDF-weighted pre-score, keep top ~30/S1             │
   │  → THIS IS candidate_pairs.tsv                                           │
   └──────────────────────────────────────────────────────────────────────────┘
                                        │  ~30–50M pairs
   ┌────────────────────────────────────┴─────────────────────────────────────┐
   │ STAGE 2  Pairwise verification                              (R2)         │
   │  ~60 hand-built features (name sim family, address sim family,           │
   │  numeric/house-number agreement, geo-token agreement, IDF-weighted       │
   │  rarity overlap, source-specific flags, block-context features)          │
   │  → LightGBM binary ranker, trained on the SAME blocking distribution     │
   │  → isotonic calibration per country-group                                │
   └──────────────────────────────────────────────────────────────────────────┘
                                        │  calibrated p(match)
   ┌────────────────────────────────────┴─────────────────────────────────────┐
   │ STAGE 3  Decision layer                                     (R3)         │
   │  a. global mutual exclusivity: each S2/S3 id → best-scoring S1 only      │
   │  b. per-entity expected-F0.5 subset selection (incl. the empty set)       │
   │  c. per-country-group safety margin tuned on held-out validation         │
   │  → matching_results.tsv → validate_submission.py → upload                │
   └──────────────────────────────────────────────────────────────────────────┘
```

Rationale for this shape: it is the standard high-performing ER pipeline (blocking → learned pairwise matcher →
constrained global resolution), every stage is independently measurable, and each of the three engineers owns one
stage with a **file-based contract** between them (see [`02_TECHNICAL_SPEC.md`](02_TECHNICAL_SPEC.md) §Contracts),
so nobody blocks anybody.

## 4. Why not just fine-tune a big transformer cross-encoder

We have no GPU locally (12 cores / 7.9 GB RAM), ~$100–200 of AWS credits, and 55 hours. Scoring 30–50M pairs with a
cross-encoder is possible on a rented GPU but it consumes the entire budget and the entire schedule, and a
cross-encoder on *noisy short strings* rarely beats a well-featured GBDT on this kind of data. Our plan:

- **GBDT on engineered string features is the primary model** (LightGBM, MIT licence — compliant).
- **Pretrained multilingual embeddings are used surgically**, only where lexical features are blind: Indic-script
  names (15–19% of the S2/S3 pool), empty addresses (~2.7%), domain-style names (~3%). Model candidates, all
  licence-compliant and ≤8B params: `intfloat/multilingual-e5-small` (MIT), `sentence-transformers/LaBSE`
  (Apache-2.0), `paraphrase-multilingual-MiniLM-L12-v2` (Apache-2.0).
- A cross-encoder is a **stretch goal only**, applied to the ~5% of pairs sitting in the decision-boundary band.

## 5. Score model — what we are aiming for

| Milestone | What it is | Expected leaderboard F<sub>0.5</sub> |
|---|---|---|
| **M0 baseline** (D1 evening) | blocking + hand-weighted score + fixed threshold | 0.55 – 0.68 |
| **M1** (D2 morning) | + LightGBM verifier, calibrated, global threshold | 0.72 – 0.80 |
| **M2** (D2 night) | + mutual exclusivity + expected-F<sub>0.5</sub> selection | 0.80 – 0.86 |
| **M3** (D3) | + learned abbreviation/transliteration maps, embedding recall for cross-script, per-country margins, ensemble | 0.86 – 0.90 |

These are engineering targets, not promises. The point is the *ordering*: the decision layer (M2) is worth more
than any extra model capacity, because the metric is macro per-entity and precision-weighted. **Build M2 before
you tune hyperparameters.**

## 6. Non-negotiables (rule compliance — disqualification risk)

- **No external data, APIs, geocoders, business registries, or internet augmentation.** Every dictionary
  (abbreviations, state-name↔code, transliteration, stop-tokens, city lists) must be **mined from the provided
  train/test files**. This is not just compliance — a map mined from 7.6M labelled pairs is *better* than a
  generic list. Pretrained open-source models are explicitly permitted; we log their licence and parameter count.
- **Final model MIT/Apache-2.0, ≤8B params.** Record licence + param count for every artefact in the methodology doc.
- **5 submissions/day max, version history maintained.** R3 owns the submission log.
- One device per participant, no simultaneous logins on the portal.

## 7. Team split (details in the role docs)

| Role | Owns | Primary metric they are judged on | Doc |
|---|---|---|---|
| **R1 — Recall / Candidate generation** | normalisation, mined maps, blocking, `candidate_pairs.tsv`, cross-script retrieval | **pair recall @ ≤30 candidates/S1**, wall-clock of a full test pass | [`04_ROLE_R1_RECALL_BLOCKING.md`](04_ROLE_R1_RECALL_BLOCKING.md) |
| **R2 — Verification model** | pair features, LightGBM, negative sampling, calibration, LOCO country-shift validation | **PR-AUC and precision@fixed-recall on held-out entities** | [`05_ROLE_R2_MODEL_FEATURES.md`](05_ROLE_R2_MODEL_FEATURES.md) |
| **R3 — Decision layer, infra, submissions** | validation splits, exact F<sub>0.5</sub> scorer, mutual exclusivity, expected-F<sub>0.5</sub> selection, AWS, packaging, docs | **end-to-end macro F<sub>0.5</sub> on validation, and zero rejected submissions** | [`06_ROLE_R3_DECISION_INFRA.md`](06_ROLE_R3_DECISION_INFRA.md) |

Suggested assignment: **Piyush → R3** (owns the machine, the AWS account, and the submission portal),
the other two take R1 and R2. Swap freely, but do not blur the ownership boundaries — the file contracts are what
let three people work in parallel on one pipeline.

## 8. First 90 minutes (all three, in parallel)

1. **R3:** create the repo skeleton + venv (`python3 -m venv .venv`, pip works via ensurepip — verified), pin
   deps, build the validation split and the F<sub>0.5</sub> scorer from `reference_code/`. Nothing else can be
   measured until the scorer exists.
2. **R1:** implement `normalize.py` + the token-key blocking already benchmarked (88.8% pair recall) and run it on
   the validation split. That is the recall baseline to beat.
3. **R2:** implement the feature extractor against the contract in `02_TECHNICAL_SPEC.md` using R1's *benchmark*
   candidate file, so you are not waiting for the full-scale run.

Then follow [`03_TIMELINE_AND_CHECKPOINTS.md`](03_TIMELINE_AND_CHECKPOINTS.md).
