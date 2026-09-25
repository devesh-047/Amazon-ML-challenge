# Validation Split — Entity ID Lists

**Generated:** 2026-09-25  
**Script:** `src/eval/make_val_split.py`  
**Source:** `train_source1.tsv` and `train_ground_truth.tsv`

---

## Overview

This directory contains **deterministic, country-stratified validation splits** of the training S1 entities. The split is hash-based (BLAKE2b with seed `"amlc2026"`), so it's reproducible without storing state and identical across all team members.

**Critical:** The split is on **S1 entities only**, never on pairs. When evaluating validation performance, the candidate pool must remain the **full train S2+S3 corpus** (all 10,319,219 records), not just the matches of validation entities. Otherwise precision is artificially inflated and thresholds tuned on it will be too aggressive on test.

---

## Files

| File | Entities | Purpose |
|------|----------|---------|
| `train_ids.txt` | 1,931,062 (87.5%) | Training entity IDs — use these for model training |
| `val_ids.txt` | 220,551 (10.0%) | Validation entity IDs — for final model evaluation and threshold tuning |
| `fastval_ids.txt` | 26,618 (1.2%) | Fast validation subset (within `val`) — for rapid iteration during development |
| `calib_ids.txt` | 55,208 (2.5%) | Calibration entity IDs — use **only** for fitting probability calibration (e.g., Platt scaling, isotonic regression) |

**Total:** 2,233,439 entities (sum includes `fastval` separately, though it's a subset of `val`)

---

## Split Quality

### Singleton Rate (Entities with 0 matches)
| Split | Singleton % | Expected |
|-------|-------------|----------|
| train | 5.59% | ~5.58% ✓ |
| val | 5.57% | ~5.58% ✓ |
| fastval | 5.51% | ~5.58% ✓ |
| calib | 5.42% | ~5.58% ✓ |

### Country Distribution
| Split | US | India | France |
|-------|-------|-------|--------|
| train | 60.0% | 40.0% | — |
| val | 60.1% | 39.9% | — |
| fastval | 60.3% | 39.7% | — |
| calib | 59.6% | 40.4% | — |

**Note:** France (15% of test set) has zero training data. This is a known challenge and requires special handling.

### Cardinality Distribution (True Matches per Entity)
All splits preserve the cardinality distribution:
- **0 matches:** ~5.6% (singletons)
- **1 match:** ~5.4%
- **2 matches:** ~17.0%
- **3 matches:** ~24.0%
- **4 matches:** ~22.0%
- **5+ matches:** ~26.0%

---

## Usage for R1 (Recall/Blocking) & R2 (Model/Features)

### During Training
```python
# Load the training entity IDs
with open("data/splits/train_ids.txt") as f:
    train_entities = set(line.strip() for line in f)

# Filter ground truth to training entities only
train_pairs = ground_truth[ground_truth['source1_entity_id'].isin(train_entities)]

# Build features/train models ONLY on these entities
```

### During Fast Iteration
```python
# Use fastval for quick experiments (26K entities, ~1-2 min per eval)
with open("data/splits/fastval_ids.txt") as f:
    fastval_entities = set(line.strip() for line in f)

# Score predictions on fastval entities
# Candidate pool: still the FULL S2+S3 corpus
```

### For Final Validation
```python
# Use val for final model selection (220K entities, ~10-15 min per eval)
with open("data/splits/val_ids.txt") as f:
    val_entities = set(line.strip() for line in f)

# Generate predictions for these entities
# Evaluate with src/eval/f05_score.py
```

### For Calibration
```python
# Use calib ONLY for probability calibration fitting
with open("data/splits/calib_ids.txt") as f:
    calib_entities = set(line.strip() for line in f)

# Fit Platt scaling or isotonic regression on these entities
# NEVER use for model training or threshold tuning
```

---

## Important Notes

1. **Candidate Pool:** When scoring validation predictions, always use the **full train S2+S3 corpus** as the candidate pool, not just the true matches of validation entities. The test set has ~23% higher distractor density (5.75 candidates/entity vs 4.68 in train), so validation should measure against realistic distractor levels.

2. **No Leakage:** These entity lists ensure zero overlap between train and validation. Ground truth for validation entities must never be visible during training.

3. **Reproducibility:** The split is deterministic based on entity ID hash. Re-running `make_val_split.py` with the same inputs will produce identical splits.

4. **Test Mix Weighting:** When comparing models, weight validation metrics by test country distribution (US 38.3%, India 46.8%, France 15.0%) rather than train distribution (US 60%, India 40%). R3 owns this in the scoring harness.

5. **France Handling:** Since France has no training data but represents 15% of the test score, validation metrics for France will be 0. Plan accordingly.

---

## Observed Constraints (from Ground Truth Analysis)

- **Max S2 matches per entity:** 5
- **Max S3 matches per entity:** 6
- **Mutual exclusivity:** Every S2/S3 ID belongs to at most one S1 entity (verified across all 7.6M matched IDs, zero exceptions)

These constraints should be enforced in the decision layer (R3).

---

## Regenerating the Split

If needed, regenerate with:
```bash
python3 src/eval/make_val_split.py \
    --source1 /path/to/dataset/train/train_source1.tsv \
    --truth /path/to/dataset/train/train_ground_truth.tsv \
    --outdir data/splits
```

**Do not modify the seed or band ranges** without team agreement, as it would invalidate all prior experiments.

---

## Contact

For questions about the split methodology, see:
- `strategy/06_ROLE_R3_DECISION_INFRA.md` (R3 role definition)
- `strategy/07_EVALUATION_PROTOCOL.md` (evaluation methodology)
- `src/eval/make_val_split.py` (implementation)
