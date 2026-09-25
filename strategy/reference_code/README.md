# Reference code

Three tested, **stdlib-only** scripts (no venv needed) covering the pieces everything else depends on.
Copy them into `ber/src/eval/` and `ber/src/decide/` and build on them — do not re-implement the metric.

| File | Purpose | Verified |
|---|---|---|
| `f05_score.py` | the official macro F<sub>0.5</sub> + slice reporting | `--selftest` → `SELFTEST PASS`, matches the official worked example (P=2/3, R=1.0, **F=0.714**) |
| `make_val_split.py` | deterministic, country-stratified entity split (train/val/fastval/calib) | ran on the real 2.2M-row train file in 12 s; every split reproduces the 5.58% singleton rate and the 60/40 country mix |
| `select_matches.py` | mutual-exclusivity demotion + per-entity expected-F<sub>0.5</sub> set selection | `--selftest` → `SELFTEST PASS`; beats the best global threshold by **+0.0165** on a calibrated simulation, plug-in vs Monte-Carlo agree to 0.0002 |

## Verification transcript

```
$ python3 f05_score.py --selftest
  [ok] README example: got 0.714286 want 0.714286
  [ok] README example == 0.714 (3dp): got 0.714000 want 0.714000
  [ok] singleton predicted empty: got 1.000000 want 1.000000
  [ok] singleton with 1 FP: got 0.000000 want 0.000000
  [ok] has truth, predicted empty: got 0.000000 want 0.000000
  [ok] perfect / disjoint / T=3 asymmetry / T=1 over-prediction / macro / missing-row
SELFTEST PASS

$ python3 select_matches.py --selftest
  [ok] confident singleton -> k=0
  [ok] one confident match -> k=1
  [ok] three confident -> k=3
  [ok] borderline second candidate rejected (k=1)
  [ok] S2 cap = 5
  simulation: best global threshold 0.45 -> 0.6551
  simulation: expected-F0.5 plug-in      -> 0.6716  (delta +0.0165)
  simulation: expected-F0.5 Monte-Carlo  -> 0.6714  (delta +0.0163)
  [ok] plug-in is within 0.005 of Monte-Carlo
  [ok] one claim demoted
SELFTEST PASS
```

End-to-end check on the real files (`train_ground_truth.tsv` scored against itself over the val split):
macro F<sub>0.5</sub> = **1.00000** over 220,551 entities, mean predictions 3.460 (truth mean 3.461), empty share
0.0557 (truth 0.0558). A degraded variant (15% of true IDs dropped, a false positive injected into 10% of entities)
scores **0.92334** with pair P/R = 0.9667/0.8490 — consistent with the F<sub>0.5</sub> table in
`../07_EVALUATION_PROTOCOL.md`, and the loss concentrates in the T=0 (0.898) and T=1 (0.813) buckets exactly as the
metric analysis predicts.

## Quick start

```bash
D=amazon-ml-challenge-dataset/student_resource/dataset

# 0. verify the tools
python3 f05_score.py --selftest
python3 select_matches.py --selftest

# 1. build the splits (12 s)
python3 make_val_split.py --source1 $D/train/train_source1.tsv \
    --truth $D/train/train_ground_truth.tsv --outdir ber/data/splits

# 2. score a prediction file on the validation entities, with slices
python3 f05_score.py --pred preds.tsv --truth $D/train/train_ground_truth.tsv \
    --source1 $D/train/train_source1.tsv --ids ber/data/splits/val_ids.txt

# 3. turn calibrated pair probabilities into a submission
#    scored.tsv: s1_id <TAB> cand_id <TAB> p
python3 select_matches.py --scored scored.tsv --out output/matching_results.tsv \
    --all-s1 $D/test/test_source1.tsv --demote 0.25 --mode plugin
```

## Caveat that matters

`select_matches.py` assumes **calibrated** probabilities. With uncalibrated scores, expected-F<sub>0.5</sub>
selection can perform *worse* than a plain global threshold — the first version of this self-test appeared to show
exactly that, because its simulated "probabilities" were not calibrated. Fit the isotonic calibrator on the `calib`
split and check the reliability plot before trusting the selector.
