#!/usr/bin/env python3
"""Decision layer: global mutual-exclusivity resolution + per-entity expected-F0.5 set selection.

Why this file exists
--------------------
The metric is a MACRO average of a precision-weighted F0.5 per Source-1 entity, so the optimal
*number* of predictions differs per entity and a single global probability threshold cannot express
"this entity is probably a singleton". Measured on the metric:

    T=1 true match: predicting the 1 right record = 1.000, predicting 2 (1 right) = 0.556
    T=3 true match: missing one = 0.909, adding one false positive = 0.789
    true singleton: predicting anything at all = 0.000  (5.58% of entities are singletons)

Two facts verified on the training ground truth make this layer possible:
  1. every matched S2/S3 id belongs to EXACTLY ONE S1 entity (all 7,638,365 of them)
     -> contested claims can be demoted;
  2. at most 5 S2 and 6 S3 matches per entity -> hard caps.

Usage
-----
    # scored.tsv: s1_id <TAB> cand_id <TAB> p     (header optional, calibrated probabilities)
    python3 select_matches.py --scored scored.tsv --out matching_results.tsv \
        --all-s1 test_source1.tsv [--demote 0.25] [--margin 0.0] [--mode plugin|mc]

    python3 select_matches.py --selftest

Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict

csv.field_size_limit(10 ** 7)

BETA_SQ = 0.25
CAP_S2 = 5      # observed maxima in train ground truth
CAP_S3 = 6
CAP_TOTAL = 11


def f05(tp: int, n_pred: int, n_true: int) -> float:
    if n_true == 0:
        return 1.0 if n_pred == 0 else 0.0
    if n_pred == 0 or tp == 0:
        return 0.0
    p = tp / n_pred
    r = tp / n_true
    return (1.0 + BETA_SQ) * p * r / (BETA_SQ * p + r)


# ---------------------------------------------------------------- selection


def select_plugin(probs: list[float]) -> int:
    """Return k* = number of top-ranked candidates to keep, maximising a plug-in E[F0.5].

    `probs` must be sorted descending. k=0 (predict nothing) is evaluated as the probability
    that the entity is genuinely a singleton, which is what recovers singleton credit.
    """
    if not probs:
        return 0
    t_hat = sum(probs)
    # k = 0 : we are right only if none of the candidates is a true match
    best_k, best_v = 0, 1.0
    for p in probs:
        best_v *= (1.0 - p)
    h = 0.0
    for k in range(1, min(len(probs), CAP_TOTAL) + 1):
        h += probs[k - 1]
        p_hat = h / k
        r_hat = h / max(t_hat, h, 1e-12)
        denom = BETA_SQ * p_hat + r_hat
        v = 0.0 if denom <= 0 else (1.0 + BETA_SQ) * p_hat * r_hat / denom
        if v > best_v:
            best_k, best_v = k, v
    return best_k


def select_mc(probs: list[float], n_samples: int = 200, rng: random.Random | None = None) -> int:
    """Monte-Carlo version: sample the Bernoulli truth vector and score exact F0.5 per prefix.

    Slower but assumption-free; use it to validate `select_plugin` on the fastval split, and for
    the final run if the two disagree materially.
    """
    if not probs:
        return 0
    rng = rng or random.Random(0)
    m = min(len(probs), CAP_TOTAL)
    totals = [0.0] * (m + 1)
    for _ in range(n_samples):
        truth = [rng.random() < p for p in probs]
        n_true = sum(truth)
        tp = 0
        totals[0] += 1.0 if n_true == 0 else 0.0
        for k in range(1, m + 1):
            if truth[k - 1]:
                tp += 1
            totals[k] += f05(tp, k, n_true)
    return max(range(m + 1), key=lambda k: totals[k])


def apply_caps(cands: list[tuple[str, float]], k: int) -> list[str]:
    """Take the top-k while respecting the per-source cardinality caps observed in train."""
    out, n2, n3 = [], 0, 0
    for cid, _ in cands:
        if len(out) >= k:
            break
        if cid.startswith("S2-"):
            if n2 >= CAP_S2:
                continue
            n2 += 1
        elif cid.startswith("S3-"):
            if n3 >= CAP_S3:
                continue
            n3 += 1
        out.append(cid)
    return out


# ---------------------------------------------------------------- exclusivity


def demote_contested(by_s1: dict[str, list[tuple[str, float]]], demote: float = 0.25) -> int:
    """Soft global mutual exclusivity.

    Each S2/S3 id may belong to at most one S1 entity (verified on the full ground truth). For
    every contested candidate, the highest-probability claim keeps its score and the losers are
    multiplied by `demote`. Soft rather than hard deletion, because the winning claim may itself
    be dropped by set selection and because p is imperfect. Returns the number of demoted claims.
    """
    best: dict[str, tuple[float, str]] = {}
    for s1, lst in by_s1.items():
        for cid, p in lst:
            cur = best.get(cid)
            if cur is None or p > cur[0]:
                best[cid] = (p, s1)
    n = 0
    for s1, lst in by_s1.items():
        for i, (cid, p) in enumerate(lst):
            if best[cid][1] != s1:
                lst[i] = (cid, p * demote)
                n += 1
        lst.sort(key=lambda t: -t[1])
    return n


# ---------------------------------------------------------------- driver


def decide(by_s1: dict[str, list[tuple[str, float]]], demote: float = 0.25,
           margin: float = 0.0, mode: str = "plugin") -> dict[str, list[str]]:
    for lst in by_s1.values():
        lst.sort(key=lambda t: -t[1])
    if demote < 1.0:
        demote_contested(by_s1, demote)
    chooser = select_plugin if mode == "plugin" else select_mc
    out = {}
    for s1, lst in by_s1.items():
        probs = [max(0.0, min(1.0, p - margin)) for _, p in lst]
        k = chooser(probs)
        out[s1] = apply_caps(lst, k)
    return out


def read_scored(path: str) -> dict[str, list[tuple[str, float]]]:
    by_s1: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh, delimiter="\t")
        for row in rd:
            if len(row) < 3:
                continue
            try:
                p = float(row[2])
            except ValueError:
                continue  # header
            by_s1[row[0]].append((row[1], p))
    return by_s1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", help="TSV: s1_id, cand_id, calibrated_probability")
    ap.add_argument("--out", help="output matching_results.tsv")
    ap.add_argument("--all-s1", help="source1 TSV: guarantees one output row per S1 entity")
    ap.add_argument("--demote", type=float, default=0.25)
    ap.add_argument("--margin", type=float, default=0.0)
    ap.add_argument("--mode", choices=("plugin", "mc"), default="plugin")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not (a.scored and a.out and a.all_s1):
        ap.error("--scored, --out and --all-s1 are required (or use --selftest)")

    by_s1 = read_scored(a.scored)
    chosen = decide(by_s1, a.demote, a.margin, a.mode)

    n_rows = n_empty = n_ids = 0
    with open(a.all_s1, newline="", encoding="utf-8") as fh, \
            open(a.out, "w", newline="", encoding="utf-8") as out:
        rd = csv.reader(fh, delimiter="\t")
        next(rd, None)
        out.write("source1_entity_id\tmatched_entity_ids\n")
        for row in rd:
            if not row:
                continue
            eid = row[0]
            ids = chosen.get(eid, [])
            out.write(f"{eid}\t{','.join(ids)}\n")
            n_rows += 1
            n_ids += len(ids)
            if not ids:
                n_empty += 1
    print(f"rows={n_rows:,}  empty={n_empty:,} ({100*n_empty/max(n_rows,1):.2f}%)  "
          f"mean_ids={n_ids/max(n_rows,1):.3f}")
    print("sanity: empty share should land near the 5.58% train singleton rate, "
          "mean_ids near the 3.461 train mean.")
    return 0


# ---------------------------------------------------------------- selftest


def _selftest() -> int:
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    # 1. a confident singleton must be predicted empty
    check("confident singleton -> k=0", select_plugin([0.05, 0.03, 0.01]) == 0,
          f"(k={select_plugin([0.05, 0.03, 0.01])})")
    # 2. one confident match -> exactly one
    check("one confident match -> k=1", select_plugin([0.97, 0.04, 0.02]) == 1,
          f"(k={select_plugin([0.97, 0.04, 0.02])})")
    # 3. three confident matches -> three
    check("three confident -> k=3", select_plugin([0.95, 0.93, 0.9, 0.05]) == 3,
          f"(k={select_plugin([0.95, 0.93, 0.9, 0.05])})")
    # 4. a borderline extra candidate must NOT be added (precision-weighted metric)
    k = select_plugin([0.95, 0.35])
    check("borderline second candidate rejected", k == 1, f"(k={k})")
    # 5. caps respected
    picked = apply_caps([(f"S2-{i}", 0.9) for i in range(8)], 8)
    check("S2 cap = 5", len(picked) == 5, f"(got {len(picked)})")

    # 6. end-to-end simulation: expected-F0.5 selection must beat the BEST global threshold.
    #    The simulation must be *calibrated* to be meaningful: labels are drawn FROM the
    #    probabilities (label_i ~ Bernoulli(p_i)). A mix of "easy" entities (sharply bimodal
    #    scores) and "hard" chain-like entities (mushy mid-range scores) is what makes a single
    #    global threshold suboptimal, which is exactly the situation in this dataset where
    #    39.5% of S1 entities share a name-token-set with another S1 entity.
    rng = random.Random(3)
    truth, by_s1 = {}, {}
    for e in range(6000):
        s1 = f"S1-{e}"
        hard = rng.random() < 0.35
        cands, tset = [], set()
        for i in range(rng.randint(3, 12)):
            p = rng.betavariate(1.5, 2.5) if hard else rng.betavariate(0.25, 0.7)
            cid = f"S2-{e}-{i}" if i % 2 else f"S3-{e}-{i}"
            cands.append((cid, p))
            if rng.random() < p:
                tset.add(cid)
        by_s1[s1] = cands
        truth[s1] = tset

    def macro(pred: dict) -> float:
        tot = 0.0
        for s1, t in truth.items():
            p = set(pred.get(s1, []))
            tot += f05(len(p & t), len(p), len(t))
        return tot / len(truth)

    best_thr, best_score = None, -1.0
    for thr in [i / 100 for i in range(5, 100, 5)]:
        pred = {s1: [c for c, p in lst if p >= thr] for s1, lst in by_s1.items()}
        s = macro(pred)
        if s > best_score:
            best_thr, best_score = thr, s
    sel = macro(decide({k2: list(v) for k2, v in by_s1.items()}, demote=1.0, mode="plugin"))
    selmc = macro(decide({k2: list(v) for k2, v in by_s1.items()}, demote=1.0, mode="mc"))
    print(f"  simulation: best global threshold {best_thr} -> {best_score:.4f}")
    print(f"  simulation: expected-F0.5 plug-in      -> {sel:.4f}  (delta {sel-best_score:+.4f})")
    print(f"  simulation: expected-F0.5 Monte-Carlo  -> {selmc:.4f}  (delta {selmc-best_score:+.4f})")
    check("plug-in selection beats the best global threshold", sel > best_score)
    check("Monte-Carlo selection beats the best global threshold", selmc > best_score)
    check("plug-in is within 0.005 of Monte-Carlo (cheap estimator is good enough)",
          abs(sel - selmc) < 0.005, f"(|delta|={abs(sel-selmc):.4f})")

    # 7. exclusivity demotes the loser of a contested claim
    by = {"S1-a": [("S2-1", 0.9)], "S1-b": [("S2-1", 0.6)]}
    n = demote_contested(by, 0.25)
    check("one claim demoted", n == 1 and abs(by["S1-b"][0][1] - 0.15) < 1e-9,
          f"(n={n}, p={by['S1-b'][0][1]:.3f})")

    print("SELFTEST PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
