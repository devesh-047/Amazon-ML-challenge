# Timeline & Checkpoints

All times **IST**. Deadline: **27 Sep 23:59 IST**. Submission cap: **5 per day**, and the day-1 budget is already
partly spent by the clock — plan for ~3 uploads today, 5 tomorrow, 5 on day 3.

**Rule for every checkpoint:** the gate is a *number on the validation split*, not "it runs". If the number is
missing at the gate, take the fallback and move on. Nobody blocks on anybody else's stage — the file contracts in
`02_TECHNICAL_SPEC.md` mean each role can work against a stubbed input.

---

## Day 1 — 25 Sep, from now to midnight

| Time | R1 (recall) | R2 (model) | R3 (decision/infra) |
|---|---|---|---|
| **17:00–18:30** | `normalize.py` v1 (unicode fold, punct, digit-preserving split, junk-prefix strip) | feature extractor skeleton against the frozen candidate schema; test it on the benchmark candidate file | repo + venv + pinned deps; port `reference_code/` into `src/eval/`; build **val split**; wire `make` targets |
| **18:30–21:00** | token-key blocker (the benchmarked one) productionised with `scipy.sparse`; run on val subset | features v1 (name + address families) computed on val candidates; correlation/sanity check vs labels | F<sub>0.5</sub> harness reporting overall + per-country + per-cardinality; **hand-weighted baseline scorer** so an end-to-end number exists tonight |
| **21:00–22:30** | **G1+G2+G3 full test pass started** (chunked, per country) | LightGBM v0 trained on a 2M-row sample of val-split-excluded entities | mutual exclusivity + expected-F<sub>0.5</sub> selection implemented and unit-tested |
| **22:30–23:45** | recall report: pair recall @K for K∈{10,20,30,40}, per country | first PR-AUC number, feature importances | **emit + validate + upload SUBMISSION #1 (M0)**; record in `runs/RUNLOG.md` |

**CP-1 gate @ 21:00** — val pair recall ≥ 0.88 at ≤40 candidates/S1.
*Fallback if missed:* ship the exact benchmark configuration from `01_DATA_PROFILE.md` §6 (known 0.8877) and move on.

**CP-2 gate @ 23:45** — a **validated** `matching_results.tsv` uploaded, any score. Getting a legal submission on the
board today de-risks the entire weekend: it proves the format, the row count (1,732,544), and the portal flow.
*Fallback:* upload a name-exact-match-only result. Even a 0.40 is worth more than an untested pipeline.

| 23:45–01:30 | R1: char-n-gram TF-IDF (G1) tuning + empty-address path | R2: hard-negative analysis — inspect the top-50 false positives by score, list the features that would kill them | R3: slice report (which countries/cardinalities lose the most), decide δ-margin scaffolding |

**Sleep, staggered — this is a scheduled task, not optional.** 48h hackathons are lost on day 3 by teams who did
not sleep on day 1. R1 00:00–07:00 · R3 01:30–08:30 · R2 02:30–09:00.

---

## Day 2 — 26 Sep (the day the score is actually made)

| Time | R1 | R2 | R3 |
|---|---|---|---|
| **07:00–10:00** | mine `abbrev.tsv` / `state.tsv` from GT; re-run blocking with expansion | full-scale training matrix from real blocked candidates (400–600K entities); LightGBM v1 + isotonic calibration | integrate v1 scores → exclusivity → expected-F<sub>0.5</sub>; report val F<sub>0.5</sub>; **SUBMISSION #2 (M1)** |
| **10:00–13:00** | `translit.tsv` (IBM-M1 over 550K cross-script pairs) + char-level fallback; recall re-measure | add block-context + entity-context features (contention count, margin-to-best) → v2 | tune `DEMOTE`, `CAP`, δ per country on val; Monte-Carlo vs plug-in check; **SUBMISSION #3** |
| **13:00–16:00** | G4 embedding kNN for the no-lexical-hook subset (timeboxed, on AWS GPU if needed) | **LOCO experiment**: train US → eval India, train India → eval US. Remove features that break transfer | France-specific audit: per-country stop tokens actually learned? sample 50 French candidate sets by hand |
| **16:00–19:00** | final blocking config frozen; full test candidate generation for the final run | lambdarank model as a second view; rank-average ensemble with v2 | **SUBMISSION #4** with the best config; slice report to hand R1/R2 their biggest remaining loss buckets |
| **19:00–22:30** | regenerate `candidate_pairs.tsv` for the frozen config; verify subset invariant | retrain on train+val-minus-holdout once the config is frozen | full end-to-end test run; **SUBMISSION #5 (M2 target)** |

**CP-3 gate @ 10:00** — end-to-end **val macro F<sub>0.5</sub> ≥ 0.72** with the GBDT in the loop.
*Fallback:* the model is not the problem — check calibration and the decision layer first; a well-calibrated weak
model plus expected-F<sub>0.5</sub> selection beats a strong model with a global 0.5 threshold.

**CP-4 gate @ 16:00** — **val macro F<sub>0.5</sub> ≥ 0.80** *and* LOCO transfer loss ≤ 0.05.
*Fallback if LOCO transfer is bad:* strip the model down to country-relative features only and retrain; France is
15% of the score and a country-overfit model will quietly cost more than any feature you would add instead.

**CP-5 gate @ 22:30** — decision layer fully integrated (exclusivity + expected-F<sub>0.5</sub> + caps), val ≥ 0.84.

Sleep: R1 23:00–06:00 · R2 00:00–07:00 · R3 00:30–07:30.

---

## Day 3 — 27 Sep (hardening, then stop)

| Time | Who | What |
|---|---|---|
| **06:30–10:00** | all | attack the biggest loss buckets from the CP-5 slice report — one experiment each, strictly timeboxed to 90 min, measured on val before anyone touches the test set |
| **10:00–12:00** | R3 | **SUBMISSION #6** (first of day 3) with the best validated config; compare LB delta vs val delta to detect overfitting to val |
| **12:00–15:00** | R1/R2 | last model improvements: ensemble weights, per-country calibration, residual recall for cross-script. **No new feature families after 15:00.** |
| **15:00–16:00** | R3 | **SUBMISSION #7** |
| **16:00** | all | 🔒 **CODE FREEZE.** No pipeline changes after this point, only threshold/δ selection from already-computed scores. |
| **16:00–18:30** | R3 (R1/R2 assist) | final full test run end-to-end from a clean checkout, with the exact pinned config. Produce both TSVs. Run `validate_submission.py`. |
| **18:30–19:30** | R3 | **SUBMISSION #8 = the final leaderboard upload.** Keep ~2 submissions in reserve for δ variants only. |
| **19:30–22:00** | R2 (lead) + all | methodology write-up into `Documentation_template.md`: methodology, blocking strategy, model architecture & features, licences + param counts, ablation table |
| **22:00–23:00** | R3 | build `<team_name>_submission.zip`: `output/` (both TSVs), `code/business_entity_resolution/{src,README.md,requirements.txt}`, filled `Documentation_template.md`. Verify the zip by extracting it into `/tmp` and reading the README as a stranger would. |
| **23:00–23:59** | all | buffer. Do not schedule anything here. Portals get slow and crowded in the last hour. |

**Hard rule: the last *pipeline* change lands at 16:00 IST on day 3.** The final 8 hours are for the run, the
package, and the document — all three are required artefacts, and a great score with a missing methodology doc
does not make the top 100.

---

## Submission budget & protocol

| Day | Budget | Planned use |
|---|---|---|
| 25 Sep | 5 | #1 M0 baseline (must happen). Keep the rest — a submission spent on an unvalidated idea is a wasted probe. |
| 26 Sep | 5 | #2 M1, #3 decision-layer tuning, #4 best config, #5 M2. One spare. |
| 27 Sep | 5 | #6 best validated, #7 improvement, #8 final. Two spares for δ variants. |

Every upload gets a row in `runs/RUNLOG.md`: run id · git SHA · config diff · val F<sub>0.5</sub> (overall + per
country) · candidates/S1 · public LB score. The guidelines require version history, and the LB↔val delta is the only
signal we get about the public/private split.

**Never let the public leaderboard drive design.** It is a subset of the test set, the private board decides the
final ranking, and with 15 total probes there is no statistical room to tune on it. Trust the validation split;
use the LB only to confirm that val and test agree in direction.

## If you fall behind — cut in this order

1. Drop **G4 embeddings** (recall path). Costs a few points of recall, saves hours.
2. Drop the **lambdarank ensemble**. The single binary GBDT is 90% of the value.
3. Drop the **swap-improvement round** in exclusivity; keep the greedy pass.
4. Reduce the training matrix to 200K entities. The model saturates earlier than you think.

**Never cut:** the F<sub>0.5</sub> scorer, the validation split, mutual exclusivity, expected-F<sub>0.5</sub>
selection, the submission validator, or the methodology document.
