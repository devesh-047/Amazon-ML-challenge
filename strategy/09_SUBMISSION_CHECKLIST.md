# Submission Checklist

Owner: **R3**. Two separate deliverables — the **leaderboard upload** (during the challenge) and the **final zip
package** (required from every team; the top teams' packages are reviewed in detail before final rankings).

---

## A. Every leaderboard upload

```bash
# 1. regenerate (or reuse) the two outputs
make submit RUN=<run_id>            # writes data/out/<run_id>/{matching_results.tsv,candidate_pairs.tsv}

# 2. structural assertions (in emit.py, but verify by eye once per day)
wc -l data/out/<run_id>/matching_results.tsv        # must be 1732545  (1,732,544 rows + header)
head -1 data/out/<run_id>/matching_results.tsv     # must be: source1_entity_id<TAB>matched_entity_ids
head -1 data/out/<run_id>/candidate_pairs.tsv      # must be: source1_entity_id<TAB>candidate_entity_ids

# 3. the organisers' validator — never skip, it is free
cd amazon-ml-challenge-dataset/student_resource
python3 utils/validate_submission.py \
    --matching  <path>/matching_results.tsv \
    --candidate <path>/candidate_pairs.tsv \
    --test-dir  dataset/test
# must print PASS and exit 0
```

- [ ] exactly one row per test S1 entity (**1,732,544** + header), no duplicates, none missing
- [ ] tab-separated, exact column names, no quoting
- [ ] ID lists comma-joined with **no spaces**; empty string for singletons
- [ ] only `S2-`/`S3-` IDs, all existing in the test files, no self-matches to `S1-`
- [ ] no duplicate IDs within a single list
- [ ] `matching_results.tsv` ⊆ `candidate_pairs.tsv`
- [ ] `candidate_pairs.tsv` is the **last** candidate set before model inference (what the model actually scored),
      not an earlier blocking pass
- [ ] sanity histogram: fraction of empty predictions ≈ 5–8% (train singleton rate is 5.58%); mean predictions per
      entity ≈ 2.5–3.5 (train mean is 3.461). Wildly outside these ranges = a threshold bug, not a breakthrough
- [ ] no entity with >5 `S2-` IDs or >6 `S3-` IDs (observed train maxima)
- [ ] logged in `runs/RUNLOG.md`: run id, git SHA, config diff, val F<sub>0.5</sub> (overall / per country /
      test-mix-weighted), mean candidates per S1, public LB score once known
- [ ] submissions used today ≤ 5

## B. Final zip package

Structure required by the organisers:

```
<team_name>_submission.zip
├── output/
│   ├── matching_results.tsv          # identical to the final leaderboard upload
│   └── candidate_pairs.tsv           # the blocking candidate set fed to the model
├── code/
│   └── business_entity_resolution/
│       ├── src/                      # all source
│       ├── README.md                 # exact end-to-end reproduction instructions
│       └── requirements.txt          # pinned versions
└── Documentation_template.md         # filled in (.md or .pdf export)
```

- [ ] `output/` contains **both** TSVs, and `matching_results.tsv` is byte-identical to what was uploaded
- [ ] `src/` is self-contained: data → normalise → mine maps → block → features → train → predict → decide → emit
- [ ] `requirements.txt` pins exact versions (see `02_TECHNICAL_SPEC.md` §2)
- [ ] `README.md` gives literal commands, expected runtimes, expected RAM, and where to put the dataset
- [ ] no data files, no parquet, no model binaries larger than necessary; no credentials, no `.env`, no AWS keys
- [ ] **reproducibility test:** `unzip` into `/tmp/repro`, follow the README as a stranger, confirm both TSVs
      regenerate (or at minimum that every stage starts and the first chunk matches)
- [ ] fixed seeds everywhere; the split is deterministic and its definition ships in the code

## C. Methodology document — mapping to the provided template

Fill `Documentation_template.md`. Who writes what:

| Template section | Content | Author |
|---|---|---|
| 1. Executive Summary | hybrid blocking + GBDT verifier + constrained decision layer; core innovation = global mutual-exclusivity resolution plus per-entity expected-F<sub>0.5</sub> set selection, and corpus-mined abbreviation/transliteration maps in place of any external data | R3 |
| 2.1 Problem Analysis | the measured EDA from `01_DATA_PROFILE.md`: 5.58% singletons, mean 3.46 matches, mutual exclusivity across all 7,638,365 matched IDs, same-country matching, 39.53% ambiguous S1 name-token-sets, 14.5% of true pairs with zero shared name tokens vs 4.4% for addresses, 15–19% Indic-script names, ~2.7% empty addresses, the France zero-shot country | R1 |
| 2.2 Solution Strategy | Approach Type: **Hybrid (multi-generator blocking + GBDT pairwise classifier + constrained global assignment + decision-theoretic set selection)** | R3 |
| 3. Candidate Generation | the four generators, keys, the two-stage prune (measured: top-20 retains 98.8% of retrieved recall while cutting candidates 6×), total candidate pairs, recall ceiling, reduction ratio, how true matches were protected (per-generator top-1 retention) | R1 |
| 4. Matching Model | ~60 features by family, why address dominates name, block/entity-context features, training on real blocked candidates, LightGBM + lambdarank ensemble, isotonic calibration, LOCO country-shift results, **threshold selection = per-entity expected-F<sub>0.5</sub> maximisation, not a global cut** | R2 |
| 5. Results & Error Analysis | best val macro F<sub>0.5</sub> with the slice table, decision-layer ablation, top false-positive classes (chain branches, transposed names) and false-negative classes (cross-script, empty address, corrupted house numbers) | R2 + R3 |
| 6. Conclusion | what mattered most: the decision layer and the precision/recall asymmetry | R3 |
| Appendix A | code structure and entry points | R3 |
| Appendix B | reliability plot, recall@K curve, cardinality histogram (predicted vs true), feature importances, ablation table | R2 |
| — add a section — | **Compliance:** every dictionary mined from provided data, no external lookups/geocoding, and a licence + parameter-count table for every model used | R3 |

Also required per the guidelines: a **1–2 page document** explaining the ML approach, models, experiments and
conclusion, and **commented source code** for experiments/training/inference. The filled template plus a clean `src/`
covers both — make sure the functions actually carry docstrings.

## D. Final-hours order of operations (day 3)

1. **16:00** code freeze — only threshold/δ selection from already-computed scores after this
2. **16:00–18:30** clean-checkout full test run → both TSVs → validator → `PASS`
3. **18:30–19:30** final leaderboard upload, logged
4. **19:30–22:00** methodology document
5. **22:00–23:00** build zip, extract to `/tmp`, reproducibility read-through
6. **23:00–23:59** buffer — nothing scheduled, portals are slow in the last hour
