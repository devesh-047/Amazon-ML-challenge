# R2 — Features & Verification Model

**You own precision.** Under F<sub>0.5</sub> a false positive is ~2.3× more expensive than a false negative
(measured: for an entity with 3 true matches, one FP costs 0.211, one miss costs 0.091). Your job is not "classify
pairs" — it is **rank the right candidate above its look-alikes and produce probabilities that are actually
calibrated**, because R3's decision layer consumes probabilities, not scores.

**Your metrics:**
| Metric | Day-2 morning | Final |
|---|---|---|
| PR-AUC on held-out blocked candidates | ≥ 0.90 | ≥ 0.95 |
| precision @ recall 0.85 | ≥ 0.90 | ≥ 0.95 |
| calibration error (reliability plot, 10 bins) | — | ≤ 0.02 mean abs |
| **LOCO transfer loss** (train US → eval India, and reverse) | measure | **≤ 0.05 F<sub>0.5</sub>** |
| per-entity top-1 accuracy on entities with ≥1 match | ≥ 0.92 | ≥ 0.96 |

---

## The problem you are actually solving

**39.53% of S1 entities share their name-token-set with another S1 entity.** `care group primary` appears 259 times;
`ear group nose throat` 254 times. These are chain branches and medical practices, and they are the reason this
competition is precision-weighted. A model that leans on name similarity will merge two branches of the same chain
with high confidence — the most expensive error class available.

So: **address agreement, especially numeric agreement, must dominate; name similarity is corroboration.** Two
features do most of the work here and both are easy to forget:
- `max IDF of an unshared token` — one rare token present on only one side is strong evidence of *different* entities.
- `geo_conflict` — both sides have geo tokens and share none. Near-fatal for a match.

And two features encode the global structure the model otherwise cannot see:
- **margin-to-best-sibling** (`blk_score − max blk_score for this S1`): "is this the obvious winner or one of eight
  look-alikes?"
- **contention count** (how many *other* S1 entities also retrieved this candidate): this is the mutual-exclusivity
  constraint, verified globally true in the ground truth, expressed as a feature.

## R2-1 Feature extractor (`src/model/features.py`)

Implement the ~60 features in §7.1 of `02_TECHNICAL_SPEC.md`. Notes from the data:

- Compute IDF **per country from the corpus**, never globally and never hard-coded — this is what carries the model
  to France. Any feature with an absolute scale (raw DF, raw token counts, raw string length) is a country-shift
  liability; prefer ratios, ranks and IDF-weighted quantities.
- `postal_exact` must be **three-state** (equal / differs / missing). Two-state collapses "no evidence" into
  "disagreement" and you will lose the ~2.7% empty-address and the many partial-address records.
- `num_edit1` matters: real corruptions in the data are `2902`→`290` and `803`→`78`. A strict numeric equality
  feature alone throws those matches away.
- Word-order transposition is common (`Engineering Pr Services Private Limited` ↔ `Private Engineering Pr Services
  Limited`), so token-**set** similarity must be present alongside any sequence-based measure.
- Feed the transliterated-name similarity as a feature, not as a replacement for the raw name similarity. Let the
  model decide how much to trust it.
- Output float32, one parquet per country per chunk. 10–15M rows × 60 features ≈ 3.6 GB — chunk it, you have 7.9 GB.

## R2-2 Training-set construction (`src/model/sample.py`) — the step people get wrong

**Train on R1's real blocked candidates, not on random negatives.** If your negatives are easy, your model will be
confident and wrong exactly where it matters. Concretely:

1. Take the `train` entities from R3's split (never validation entities — R3 owns the split; ask, do not invent).
2. Run R1's blocker on them. Positives = blocked candidates present in GT. Negatives = blocked candidates absent
   from GT. These negatives are hard by construction: same city, similar name, wrong branch.
3. Keep every positive. Subsample negatives to ~1:8 if needed and restore `scale_pos_weight` / sample weights so
   probabilities stay calibratable.
4. Log the **blocking-missed positives** separately as diagnostics for R1 — they are not trainable signal for you.
5. Start with 200–400K entities. The model saturates earlier than you expect, and a fast loop on day 2 is worth more
   than a marginally better model on day 3.

## R2-3 Models

- **Primary:** LightGBM binary, `metric=average_precision`, `num_leaves≈255`, `min_data_in_leaf≈200`, `lr=0.05`,
  `feature_fraction=0.8`, early stopping. MIT-licensed → compliant.
- **Second view:** LightGBM `lambdarank` grouped by `s1_id`. The task *is* per-entity ranking and the ranker often
  picks the winner better. Ensemble by rank-averaging or probability-averaging; validate that the ensemble actually
  helps end-to-end F<sub>0.5</sub>, not just PR-AUC.
- **Calibration is not optional.** R3's expected-F<sub>0.5</sub> selection is only as good as your probabilities.
  Fit isotonic regression on a held-out slice, per country group. Then produce a reliability plot and put it in the
  methodology doc.
- Skip neural cross-encoders unless everything else is done and CP-5 is green. If you do: `multilingual-e5-small`
  (MIT, 118M) or `LaBSE` (Apache-2.0, 471M), applied **only** to pairs in the decision-boundary band
  (p ∈ [0.2, 0.8]), which is ~5% of pairs. Document licence and parameter count.

## R2-4 The France experiment (mandatory, do not skip)

France is 259,452 test S1 entities = **15.0% of the final score**, with **zero training data**. If France scores
0.40 while US/India score 0.90, your total is 0.82 — France alone costs ~7.5 points.

You cannot measure France. You can measure transfer:

```
train on US only          → evaluate on India   → record F0.5 loss vs in-domain
train on India only       → evaluate on US      → record F0.5 loss vs in-domain
```

If transfer loss > 0.05, you have country-specific features. Find them (feature importance diff between the two
models is a fast diagnostic) and remove or normalise them. Then hand-audit 50 French candidate sets from the test
set: are the learned French stop tokens sane, do accents fold, does `SARL`/`SAS` get down-weighted, do street words
(`rue`, `boulevard`, `avenue`) behave like `street`/`road` do in the US?

Also check: **is the calibrator transferable?** Fit on US, apply to India, re-plot reliability. If it is not, R3
needs a country-agnostic fallback calibrator for France.

## R2-5 Error analysis ritual (every checkpoint, 20 minutes)

Print the 50 highest-scoring false positives and the 50 highest-scoring false negatives, with both records side by
side. Every checkpoint. This is the highest-information-per-minute activity available in an entity resolution task,
and it will hand you the next feature directly. Expect to find, in order: chain branches with identical names,
transposed-token names, house-number corruption, empty addresses, transliteration failures.

## Definition of done

- [ ] `make features` and `make train` reproducible from a clean checkout with a fixed seed
- [ ] feature importance table + reliability plot committed
- [ ] LOCO results committed with the conclusion written out
- [ ] ablation table for the methodology doc: which feature family bought what
- [ ] model artefacts + licence/param-count note for the compliance section
