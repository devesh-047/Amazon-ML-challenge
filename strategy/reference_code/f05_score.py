#!/usr/bin/env python3
"""Official macro-F0.5 scorer for the Amazon ML Challenge 2026 Business Entity Resolution task.

This is the ONE number the competition is decided on. Do not re-implement it elsewhere;
import `f05`, `score_files` or `score_dicts` from here.

Metric definition (from the challenge README):
    F_0.5 = (1.25 * P * R) / (0.25 * P + R),  computed per Source-1 entity, then averaged
    over ALL Source-1 entities in the evaluation set (macro average, singletons included).
    A singleton (no true matches) scores 1.0 when predicted empty and 0.0 otherwise.

Usage
-----
    # score a prediction file against a ground-truth file
    python3 f05_score.py --pred preds.tsv --truth train_ground_truth.tsv

    # add slice breakdowns (needs a source1 file for country, and uses true cardinality)
    python3 f05_score.py --pred preds.tsv --truth gt.tsv --source1 train_source1.tsv

    # restrict the evaluation to a subset of entity ids (e.g. the validation split)
    python3 f05_score.py --pred preds.tsv --truth gt.tsv --ids val_ids.txt

    # verify the implementation
    python3 f05_score.py --selftest

Stdlib only, so it runs before any virtualenv exists.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict

csv.field_size_limit(10 ** 7)

BETA_SQ = 0.25  # beta = 0.5


def f05(pred: set, truth: set) -> float:
    """F_0.5 for a single Source-1 entity. Handles the singleton cases explicitly."""
    if not truth:
        return 1.0 if not pred else 0.0
    if not pred:
        return 0.0
    tp = len(pred & truth)
    if tp == 0:
        return 0.0
    p = tp / len(pred)
    r = tp / len(truth)
    denom = BETA_SQ * p + r
    return 0.0 if denom == 0 else (1.0 + BETA_SQ) * p * r / denom


def read_id_map(path: str, id_col: int = 0, list_col: int = 1) -> dict:
    """Read a `<id>\\t<comma,separated,ids>` TSV (with header) into {id: set(ids)}."""
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh, delimiter="\t")
        header = next(rd, None)
        if header is None:
            return out
        for row in rd:
            if not row:
                continue
            key = row[id_col]
            raw = row[list_col] if len(row) > list_col else ""
            out[key] = {x for x in raw.split(",") if x}
    return out


def score_dicts(pred: dict, truth: dict, ids=None, meta: dict | None = None) -> dict:
    """Macro F0.5 over `ids` (default: all truth keys), with optional slice breakdowns.

    `meta` maps entity_id -> dict of slice values, e.g. {"country": "US"}.
    Entities present in `truth` but missing from `pred` are scored as an empty prediction,
    which is exactly how the leaderboard would treat a missing row if it were allowed.
    """
    keys = list(truth.keys()) if ids is None else list(ids)
    total = 0.0
    n = 0
    n_missing_pred = 0
    n_empty_pred = 0
    pred_sizes = 0
    by_country = defaultdict(lambda: [0.0, 0])
    by_card = defaultdict(lambda: [0.0, 0])
    # pair-level aggregates
    tp = fp = fn = 0
    for k in keys:
        t = truth.get(k, set())
        if k in pred:
            p = pred[k]
        else:
            p = set()
            n_missing_pred += 1
        s = f05(p, t)
        total += s
        n += 1
        if not p:
            n_empty_pred += 1
        pred_sizes += len(p)
        inter = len(p & t)
        tp += inter
        fp += len(p) - inter
        fn += len(t) - inter
        card = min(len(t), 5)
        by_card[card][0] += s
        by_card[card][1] += 1
        if meta is not None:
            c = meta.get(k, {}).get("country", "?")
            by_country[c][0] += s
            by_country[c][1] += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "macro_f05": total / n if n else 0.0,
        "n_entities": n,
        "n_missing_pred_rows": n_missing_pred,
        "frac_empty_pred": n_empty_pred / n if n else 0.0,
        "mean_pred_size": pred_sizes / n if n else 0.0,
        "pair_precision": prec,
        "pair_recall": rec,
        "by_country": {k: (v[0] / v[1], v[1]) for k, v in sorted(by_country.items())},
        "by_true_cardinality": {k: (v[0] / v[1], v[1]) for k, v in sorted(by_card.items())},
    }


def read_meta(source1_path: str) -> dict:
    meta = {}
    with open(source1_path, newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh, delimiter="\t")
        next(rd, None)
        for row in rd:
            if len(row) >= 4:
                meta[row[0]] = {"country": row[3]}
    return meta


def score_files(pred_path: str, truth_path: str, source1_path: str | None = None,
                ids_path: str | None = None) -> dict:
    pred = read_id_map(pred_path)
    truth = read_id_map(truth_path)
    ids = None
    if ids_path:
        with open(ids_path, encoding="utf-8") as fh:
            ids = [ln.strip() for ln in fh if ln.strip()]
    meta = read_meta(source1_path) if source1_path else None
    return score_dicts(pred, truth, ids=ids, meta=meta)


def _report(res: dict, test_mix: bool = True) -> None:
    print(f"macro F0.5            : {res['macro_f05']:.5f}   over {res['n_entities']:,} entities")
    print(f"pair precision/recall : {res['pair_precision']:.4f} / {res['pair_recall']:.4f}")
    print(f"mean predictions/ent  : {res['mean_pred_size']:.3f}   (train truth mean = 3.461)")
    print(f"fraction empty preds  : {res['frac_empty_pred']:.4f}  (train singleton rate = 0.0558)")
    if res["n_missing_pred_rows"]:
        print(f"!! {res['n_missing_pred_rows']:,} evaluated entities had NO prediction row")
    if res["by_country"]:
        print("by country:")
        for c, (s, n) in res["by_country"].items():
            print(f"   {c:<8} {s:.5f}  ({n:,} entities)")
        if test_mix:
            # reweight to the measured TEST country mix: US .383 / India .468 / France .150
            w = {"US": 0.383, "India": 0.468, "France": 0.150}
            avail = {c: w[c] for c in res["by_country"] if c in w}
            if avail:
                z = sum(avail.values())
                mixed = sum(res["by_country"][c][0] * wt / z for c, wt in avail.items())
                print(f"   test-mix-reweighted ({'/'.join(avail)}): {mixed:.5f}")
    print("by true cardinality (5 = 5+):")
    for k, (s, n) in res["by_true_cardinality"].items():
        print(f"   T={k}  {s:.5f}  ({n:,} entities)")


def _selftest() -> int:
    ok = True

    def check(name, got, want, tol=1e-9):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"  [{'ok' if good else 'FAIL'}] {name}: got {got:.6f} want {want:.6f}")

    # 1. the worked example from the official README:
    #    pred {S2-00047, S2-00193, S3-00812} vs truth {S2-00047, S3-00812}
    #    P = 2/3, R = 1.0 -> F0.5 = 0.714
    check("README example",
          f05({"S2-00047", "S2-00193", "S3-00812"}, {"S2-00047", "S3-00812"}),
          1.25 * (2 / 3) * 1.0 / (0.25 * (2 / 3) + 1.0))
    check("README example == 0.714 (3dp)",
          round(f05({"S2-00047", "S2-00193", "S3-00812"}, {"S2-00047", "S3-00812"}), 3),
          0.714)
    # 2. singleton rules
    check("singleton predicted empty", f05(set(), set()), 1.0)
    check("singleton with 1 FP", f05({"S2-1"}, set()), 0.0)
    check("has truth, predicted empty", f05(set(), {"S2-1"}), 0.0)
    # 3. perfect and disjoint
    check("perfect", f05({"S2-1", "S3-2"}, {"S2-1", "S3-2"}), 1.0)
    check("disjoint", f05({"S2-9"}, {"S2-1"}), 0.0)
    # 4. the asymmetry that governs our thresholds (T=3)
    check("T=3, 1 FP added", f05({"a", "b", "c", "d"}, {"a", "b", "c"}), 0.7894736842105263)
    check("T=3, 1 match missed", f05({"a", "b"}, {"a", "b", "c"}), 0.9090909090909091)
    check("T=1, predicted 2 (1 right)", f05({"a", "x"}, {"a"}), 0.5555555555555556)
    # 5. macro averaging incl. singletons
    truth = {"e1": {"a", "b"}, "e2": set(), "e3": {"c"}}
    pred = {"e1": {"a", "b"}, "e2": set(), "e3": {"z"}}
    res = score_dicts(pred, truth)
    check("macro over 3 entities (1+1+0)/3", res["macro_f05"], 2 / 3)
    # 6. a missing prediction row is scored as an empty prediction
    res2 = score_dicts({"e1": {"a", "b"}, "e2": set()}, truth)
    check("missing row == empty pred", res2["macro_f05"], 2 / 3)
    assert res2["n_missing_pred_rows"] == 1
    print("SELFTEST PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="macro F0.5 scorer")
    ap.add_argument("--pred", help="prediction TSV (source1_entity_id, matched_entity_ids)")
    ap.add_argument("--truth", help="ground-truth TSV")
    ap.add_argument("--source1", help="source1 TSV, enables per-country slices")
    ap.add_argument("--ids", help="file with one entity_id per line: restrict evaluation to these")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not (a.pred and a.truth):
        ap.error("--pred and --truth are required (or use --selftest)")
    _report(score_files(a.pred, a.truth, a.source1, a.ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
