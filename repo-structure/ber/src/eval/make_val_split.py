#!/usr/bin/env python3
"""Deterministic, country-stratified validation split over Source-1 entities.

Splits the TRAIN Source-1 entities into train / val / fastval / calib by a stable hash of the
entity_id, so the split is reproducible without storing state and identical for all three
engineers. Writes one id-per-line file per split plus a stats report.

IMPORTANT (see strategy/07_EVALUATION_PROTOCOL.md):
  * the split is on S1 ENTITY, never on pairs;
  * the candidate pool used when evaluating `val` must remain the FULL train S2+S3 corpus,
    not merely the true matches of the val entities, otherwise precision is inflated and
    every threshold tuned on it will be too loose on the test set;
  * `fastval` is a subset of `val` for minute-by-minute iteration;
  * `calib` is disjoint from train and val and is used only to fit probability calibration.

Usage
-----
    python3 make_val_split.py \
        --source1 .../dataset/train/train_source1.tsv \
        --truth   .../dataset/train/train_ground_truth.tsv \
        --outdir  ber/data/splits

Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from collections import Counter, defaultdict

csv.field_size_limit(10 ** 7)

# hash bands out of 1000. train gets the rest.
BANDS = {
    "val": range(0, 100),        # 10%  ~220k entities
    "calib": range(100, 125),    # 2.5% ~55k entities
}
FASTVAL_BAND = range(0, 12)      # subset of val, ~1.2% ~26k entities
SEED = "amlc2026"


def band(entity_id: str) -> int:
    h = hashlib.blake2b((SEED + entity_id).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big") % 1000


def assign(entity_id: str) -> str:
    b = band(entity_id)
    for name, rng in BANDS.items():
        if b in rng:
            return name
    return "train"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source1", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)

    truth_card = {}
    with open(a.truth, newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh, delimiter="\t")
        next(rd, None)
        for row in rd:
            if row:
                ids = [x for x in (row[1] if len(row) > 1 else "").split(",") if x]
                truth_card[row[0]] = len(ids)

    files = {n: open(os.path.join(a.outdir, f"{n}_ids.txt"), "w", encoding="utf-8")
             for n in ("train", "val", "calib", "fastval")}
    stats = defaultdict(Counter)
    card_stats = defaultdict(Counter)

    with open(a.source1, newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh, delimiter="\t")
        next(rd, None)
        for row in rd:
            if len(row) < 4:
                continue
            eid, country = row[0], row[3]
            split = assign(eid)
            files[split].write(eid + "\n")
            stats[split][country] += 1
            card_stats[split][min(truth_card.get(eid, 0), 5)] += 1
            if split == "val" and band(eid) in FASTVAL_BAND:
                files["fastval"].write(eid + "\n")
                stats["fastval"][country] += 1
                card_stats["fastval"][min(truth_card.get(eid, 0), 5)] += 1

    for f in files.values():
        f.close()

    print(f"wrote splits to {a.outdir}\n")
    for split in ("train", "val", "fastval", "calib"):
        tot = sum(stats[split].values())
        mix = "  ".join(f"{c}={n:,} ({100*n/tot:.1f}%)" for c, n in sorted(stats[split].items()))
        print(f"{split:<8} {tot:>9,} entities   {mix}")
        cards = card_stats[split]
        ct = sum(cards.values())
        print("         cardinality: " + "  ".join(
            f"T={k}:{100*cards[k]/ct:.2f}%" for k in sorted(cards)))
    print("\nSanity: singleton share (T=0) should be ~5.58% in every split; country mix should "
          "match the parent file (~US 60% / India 40% for train data).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
