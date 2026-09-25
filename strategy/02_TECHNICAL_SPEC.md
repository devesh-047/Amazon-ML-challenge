# Technical Specification

This is the contract document. If three people are going to work on one pipeline in 55 hours without blocking each
other, the interfaces have to be frozen first. **Interfaces here are frozen; internals are each owner's business.**

---

## 1. Repository layout

```
Amazon-ML-challenge/
├── amazon-ml-challenge-dataset/student_resource/     # provided, read-only
├── strategy/                                        # these docs + reference_code/
└── ber/                                             # ← the actual pipeline repo (create this)
    ├── .venv/
    ├── requirements.txt                             # pinned, R3 owns
    ├── Makefile                                     # one target per stage
    ├── conf/
    │   └── default.yaml                             # all thresholds/paths, no magic numbers in code
    ├── src/
    │   ├── common/
    │   │   ├── io.py            # tsv/parquet readers, chunk helpers   (R3)
    │   │   ├── normalize.py     # STAGE 0                             (R1)
    │   │   └── maps.py          # mined abbrev/translit/state maps     (R1)
    │   ├── block/
    │   │   ├── mine_maps.py     # learn maps from GT                   (R1)
    │   │   ├── build_index.py   # per-country TF-IDF / key indexes     (R1)
    │   │   ├── generate.py      # → candidates.parquet                 (R1)
    │   │   └── embed_recall.py  # optional embedding kNN               (R1)
    │   ├── model/
    │   │   ├── features.py      # → features.parquet                   (R2)
    │   │   ├── sample.py        # negative sampling / train matrix      (R2)
    │   │   ├── train.py         # LightGBM + calibration                (R2)
    │   │   └── predict.py       # → scored.parquet                     (R2)
    │   ├── decide/
    │   │   ├── exclusivity.py   # global one-to-one resolution          (R3)
    │   │   ├── select.py        # expected-F0.5 subset selection        (R3)
    │   │   └── emit.py          # → matching_results.tsv + candidate_pairs.tsv (R3)
    │   └── eval/
    │       ├── split.py         # validation split                      (R3)
    │       ├── f05.py           # the official metric                   (R3)
    │       └── report.py        # slice metrics (country, cardinality)   (R3)
    ├── data/                    # gitignored
    │   ├── interim/             # parquet intermediates
    │   └── out/                 # submissions, one dir per run id
    └── runs/RUNLOG.md           # every experiment: run id, config, val score, LB score
```

Git: one repo, `main` protected-by-convention, each role works on `r1/*`, `r2/*`, `r3/*` branches and merges
often (at least at every checkpoint). Do **not** commit data or parquet files.

## 2. Pinned dependencies (`requirements.txt`)

```
polars==1.44.2
pyarrow==17.0.0
numpy==2.1.1
scipy==1.14.1
scikit-learn==1.5.2
sparse-dot-topn==1.1.5
lightgbm==4.5.0
duckdb==1.1.1
unidecode==1.3.8          # pure-code transliteration helper, MIT
tqdm==4.66.5
# optional (R1 embedding path, only if used):
# sentence-transformers==3.1.1 ; torch==2.4.1
```

Licences for the compliance section of the methodology doc: LightGBM **MIT**, scikit-learn **BSD-3**,
polars **MIT**, scipy/numpy **BSD**, sparse-dot-topn **Apache-2.0**, unidecode **GPL-compatible (Artistic/GPL) —
if this worries the reviewer, replace it with our own `unicodedata.normalize('NFKD', …)` fold, which is 10 lines.**
Embedding models if used: `intfloat/multilingual-e5-small` **MIT** (118M params), `sentence-transformers/LaBSE`
**Apache-2.0** (471M), `paraphrase-multilingual-MiniLM-L12-v2` **Apache-2.0** (118M). All ≤8B. ✔

> **Decision:** prefer the stdlib `unicodedata` fold over `unidecode` to keep the licence story trivially clean.

## 3. Stage contracts (frozen)

All intermediates are **parquet**, partitioned by `country`, written under `data/interim/<stage>/<split>/`.
`split ∈ {train, val, test}`.

### 3.1 `normalized/` — R1 → everyone

| column | type | meaning |
|---|---|---|
| `entity_id` | str | unchanged |
| `src` | u8 | 1, 2 or 3 |
| `country` | str | unchanged, **open set** |
| `name_raw`, `addr_raw` | str | unchanged input |
| `name_norm` | str | space-joined normalised name tokens (legal suffixes kept) |
| `name_core` | str | name_norm minus per-country stop/legal tokens |
| `name_toks` | list[str] | tokens of `name_core` |
| `addr_norm` | str | normalised address |
| `addr_toks` | list[str] | tokens of `addr_norm` |
| `addr_nums` | list[str] | numeric tokens (house/plot/PIN), longest-first |
| `addr_geo` | list[str] | tokens judged to be city/state/region (high DF within country) |
| `name_script` | str | `latin` / `devanagari` / `kannada` / … |
| `has_addr` | bool | `addr_raw != ""` |

### 3.2 `candidates/` — R1 → R2, and also the submitted `candidate_pairs.tsv`

| column | type | meaning |
|---|---|---|
| `s1_id` | str | |
| `cand_id` | str | S2- or S3- id |
| `country` | str | equal for both by construction |
| `blk_src` | u8 bitmask | which generators fired: 1=name-ngram, 2=addr-token, 4=key-join, 8=embedding |
| `blk_rank_name` | i16 | rank in the name-retrieval list (-1 if absent) |
| `blk_rank_addr` | i16 | rank in the address-retrieval list (-1 if absent) |
| `blk_score` | f32 | the cheap pre-score used for top-K pruning |

**Invariants R2 and R3 may rely on:** every test `s1_id` appears ≥0 times; no duplicate `(s1_id, cand_id)`;
`cand_id` prefix ∈ {`S2-`,`S3-`}; ≤ `K_MAX` rows per `s1_id` (config, default 30).

### 3.3 `scored/` — R2 → R3

| column | type |
|---|---|
| `s1_id`, `cand_id`, `country` | str |
| `p` | f32 — **calibrated** probability that the pair is a true match |
| `raw_score` | f32 — uncalibrated model output (for debugging) |

### 3.4 Submission files — R3

Exactly as specified by the organisers: tab-separated, header row, one row per test S1 entity
(**1,732,544 rows + header**), `matched_entity_ids` comma-joined with no spaces and no quoting, empty for
singletons, subset of `candidate_pairs.tsv`.

## 4. Stage 0 — normalisation spec (R1)

Order matters. Apply to both name and address, with the differences noted.

1. **Unicode fold:** `unicodedata.normalize('NFKC', s)`, then for accent folding produce *both* the accented and
   the ASCII-folded form (NFKD + strip combining marks). Keep the original script separately — do not destroy
   Devanagari by folding.
2. **Lowercase**, replace `&` → `and`, `@` → `at`, `+` → ` `, collapse `'`/`’`, strip `"`, map `/`, `-`, `.`, `,`
   to space **except** keep digit-internal `/` and `-` (Indian plot numbers like `21/152`, `6-208` are high-value
   features — emit both the joined and split forms).
3. **Strip junk prefixes/suffixes** seen in the data: leading `--`, `<<`, `>>`, `**`, and the wrapper phrases
   `d.b.a.`, `dba`, `formerly`, `formerly known as`, `shri`, `m/s`. When a wrapper is found, emit **two** name
   variants (with and without the wrapper's left part) and let retrieval use both.
4. **Domain-style names** (`silverinfotechprivate.com`): strip the TLD, then split the remaining string into
   tokens by (a) matching the longest known tokens from the corpus vocabulary greedily, and (b) leaving the raw
   string as a char-n-gram key. ~3–4% of S2/S3 — worth the 20 lines.
5. **Abbreviation expansion via the mined map** (see §5), applied token-wise, both directions recorded (we index
   the expanded form for everything, so `rd`/`road` collide by construction).
6. **Per-country stop/legal token list, computed from the corpus**, not hard-coded: within each country, take
   tokens with document frequency > 0.5% of records in that country *and* length ≤ 12 → candidate stop tokens;
   keep them in `name_norm`, remove them from `name_core`. For US this yields `llc, inc, corp, the, and, company`;
   for India `private, limited, pvt, ltd, llp, india`; for France it will yield `sarl, sas, sasu, eurl, société,
   rue, avenue, boulevard` automatically. **This is the France strategy in one paragraph.**
7. **Address structuring (heuristic, no geocoding):** classify each address token as
   `numeric` (all digits, or digits+letter like `41st`), `geo` (DF within country above a threshold, e.g. city/state
   names, and 2-letter US state codes recognised via the mined state map), or `street` (the rest). Do **not** try
   to parse a full address grammar — components are reordered arbitrarily in this data, so bag-of-typed-tokens is
   both simpler and more robust.
8. **PIN/ZIP:** capture 6-digit (India) and 5-digit (US) and 5-digit-French numbers as a separate `postal` slot
   when present — exact postal agreement is one of the strongest features available.

## 5. Mined maps (R1) — the rule-compliant substitute for external data

All learned from `train_ground_truth.tsv` + the source files. Nothing downloaded.

| Map | How | Example output |
|---|---|---|
| `abbrev.tsv` | For every true pair, align name/address token multisets; for tokens present on one side only, propose `(a,b)` if `a` is a prefix/subsequence of `b` or edit distance ≤2 after the first 2 chars; keep pairs with support ≥ 50 and precision-like ratio ≥ 0.9 | `rd→road`, `st→street`, `ltd→limited`, `pvt→private`, `blvd→boulevard`, `apt→apartment` |
| `state.tsv` | Same alignment restricted to address tokens where one side is a 2-letter token and the other is a multi-word high-DF geo phrase | `nc→north carolina`, `ka→karnataka`, `tx→texas` |
| `translit.tsv` (token level) | Restrict to pairs where the S2/S3 name is non-Latin and the S1 name is Latin; run IBM-Model-1 style EM over token alignments (2–3 iterations is enough with 550K pairs) | `प्राइवेट→private`, `लिमिटेड→limited`, `मार्केटिंग→marketing` |
| `translit_char.json` | From the aligned proper-noun tokens above, learn character/cluster mappings to transliterate **unseen** Indic tokens | `रा→ra`, `म→m` … |
| `stopdf.tsv` | Per-country token DF tables over **train ∪ test** source files (test is provided data; using its distribution is not external lookup) | France legal/street stop tokens |

Acceptance: `abbrev.tsv` ≥ 300 entries, `state.tsv` covers ≥ 45 US states + ≥ 25 Indian states,
`translit.tsv` ≥ 2,000 entries. Re-run must be deterministic (fixed seed, sorted output).

## 6. Stage 1 — candidate generation (R1)

Run **per country** (hard partition, verified safe). Within country, if a partition is still too large for RAM,
sub-partition by a coarse geo token with a catch-all bucket for records whose geo token is missing.

Four generators, unioned:

| # | Generator | Implementation | Targets |
|---|---|---|---|
| **G1** | name char 3+4-gram TF-IDF cosine, top-40 | `TfidfVectorizer(analyzer='char_wb', ngram_range=(3,4), min_df=3)` + `sparse_dot_topn.sp_matmul_topn` | typos, suffix noise, transpositions, domain-style names |
| **G2** | address token TF-IDF cosine (sublinear tf, IDF), top-40 | same machinery on `addr_toks` | the 39.5% ambiguous-name entities; Indic-script names with Latin addresses |
| **G3** | exact key joins | keys: `(country, postal, longest addr_num)`, `(country, addr_num, rarest street token)`, `(country, sorted top-2 rarest name_core tokens)`, `(country, name_core token, geo token)` | high-precision cheap recall, catches what cosine truncation misses |
| **G4** | embedding kNN (optional, timeboxed) | multilingual-e5-small / LaBSE, FAISS or `hnswlib` per country; **only for the subset with no lexical hook**: non-Latin name, or empty address, or G1∪G2∪G3 returned <3 candidates | the residual ~11% |

Then **pre-score and prune**: `blk_score = 0.65·wJaccard(name_core, IDF) + 0.35·wJaccard(addr_toks, IDF)`
(the benchmarked formula) plus a bonus for `postal`/`addr_num` exact agreement; keep top `K_MAX=30` per S1 entity.
Measured: top-40 retains 99.3% of retrieved recall, top-20 retains 98.8%. **Start at K=30.**

Targets: **pair recall ≥ 0.95** on the validation split at ≤30 candidates/S1, full-test pass ≤ 90 min.

Belt-and-braces: always keep the single best candidate from *each* generator even if it falls below top-K, so the
model gets a shot at the odd-one-out cases.

## 7. Stage 2 — pairwise verification (R2)

### 7.1 Feature families (~60 features; all computed from the pair + its block context)

**Name similarity (12)** — on `name_core` and `name_norm`:
Jaccard, IDF-weighted Jaccard, containment (both directions), token-sort ratio, token-set ratio,
char 3-gram cosine, normalised Levenshtein, Jaro-Winkler on the concatenated core, longest-common-token-subsequence
length / min-len, count of shared tokens, count of tokens unique to S1, count unique to candidate, max IDF of a
shared token, max IDF of an unshared token (**this one is the chain-killer**).

**Address similarity (14)** — on `addr_toks`, `addr_nums`, `addr_geo`, `postal`:
token Jaccard, IDF-weighted Jaccard, containment both directions, char 3-gram cosine,
`postal_exact` (3-state: equal / differ / missing), `num_exact_any`, `num_exact_all`, count of shared numerics,
`num_edit1` (one numeric differs by ≤1 edit — catches `2902`→`290`), `geo_exact` (shared city/state token after
state-map expansion), `geo_conflict` (both have geo tokens and none shared — a strong negative), street-token
Jaccard, `has_addr` flags for each side, length difference.

**Cross-field (4):** name-tokens ∩ address-tokens (businesses named after their street), S1 name tokens found in
candidate address and vice versa, and the pair's `addr_only` / `name_only` evidence indicator.

**Script / language (5):** candidate `name_script`, `script_mismatch`, transliterated-name Jaccard (using the mined
`translit` maps), embedding cosine (if G4 ran, else −1), `is_domain_style`.

**Block context (8) — the features most people forget and they are worth a lot:**
`blk_rank_name`, `blk_rank_addr`, `blk_src` bitmask, `blk_score`,
`blk_score − max(blk_score) over this S1` (margin to the best sibling),
`blk_score / max(blk_score)`, number of candidates for this S1, rank of this candidate by `blk_score`.
These tell the model "is this the obvious winner or one of eight look-alikes" — exactly the signal needed to avoid
merging chain branches.

**Entity context (6):** number of candidates for this S1 with `blk_score` within 10% of this one; number of *other*
S1 entities that also retrieved this candidate (**contention count — directly encodes the mutual-exclusivity
constraint as a feature**); candidate's own retrieval degree; S1 name token count; candidate name token count;
S1 `name_core` DF (is this a chain-style generic name?).

**Do not** feed `country` as a categorical. Feed only country-*relative* quantities (IDF-weighted stats), otherwise
the model cannot generalise to France.

### 7.2 Training set construction

- Use **only the train split entities** assigned to `train` by `src/eval/split.py` (R3 owns the split; never train
  on validation entities).
- **Run R1's real blocker on train entities and train on that candidate distribution.** Training on random negatives
  is the classic way to lose this competition: the model must learn to separate *near* misses, not easy ones.
- Positives: blocked candidates present in GT. Negatives: blocked candidates absent from GT (these are hard by
  construction). Keep all positives; subsample negatives to ~1:8 if the matrix gets too big, with weights restored.
- Also mine **"impossible" positives** (true matches that blocking missed) into a separate diagnostics file — that is
  R1's improvement backlog, not training data.
- Suggested scale: 400–600K train S1 entities × ~25 candidates ≈ 10–15M rows × 60 float32 features ≈ 3.6 GB →
  chunk to parquet and train LightGBM from a `Dataset` built out-of-core, or train on a 5M-row stratified sample
  first (it converges fine) and scale later if time permits.

### 7.3 Model

- LightGBM `objective=binary`, `metric=average_precision`, `num_leaves≈255`, `min_data_in_leaf≈200`,
  `learning_rate=0.05`, `feature_fraction=0.8`, `bagging_fraction=0.8`, early stopping on the validation slice.
- Consider `lambdarank` grouped by `s1_id` as a **second** model — the task is per-entity ranking, and a ranker
  often beats a binary classifier at choosing *which* candidate wins. Ensemble by averaging ranks/probabilities.
- **Calibrate** with isotonic regression fit on a held-out slice, **fit separately per country-group**
  (`US`, `India`, and — crucially — evaluate the `India`-fitted calibrator on France; see LOCO below).
- **Leave-one-country-out (LOCO) validation is mandatory:** train on US only → evaluate on India, and vice versa.
  This is our only estimate of France performance. If LOCO transfer loses more than ~0.05 F<sub>0.5</sub>, drop the
  features that are causing it (usually anything with absolute DF/length scales instead of country-relative ones).

## 8. Stage 3 — decision layer (R3)

### 8.1 Global mutual exclusivity

Verified fact: each S2/S3 id belongs to at most one S1 entity. So:

```
for each cand_id claimed by more than one s1_id:
    keep the claim with the highest p
    for the losers: set p *= DEMOTE   (DEMOTE ≈ 0.25, tuned)   # soft, not hard-delete
```
Soft demotion beats hard deletion because the winner may itself be dropped later by set selection, and because our
`p` is imperfect. Then optionally one round of **local swap improvement**: if demoting a claim would let a
higher-total-expected-F<sub>0.5</sub> assignment emerge, take it. Full bipartite optimisation (auction/Hungarian) is
overkill at 10M nodes — a single greedy pass plus one swap round captures nearly all of the gain.

Also enforce cardinality caps from the profile: **≤5 S2 and ≤6 S3 per entity**.

### 8.2 Per-entity expected-F<sub>0.5</sub> subset selection

This is the highest-leverage 40 lines of code in the project. Given calibrated `p₁ ≥ p₂ ≥ … ≥ p_m` for one S1 entity:

```
E[F0.5(k)]  for the prefix {1..k}:
    expected true count  T̂ = Σ_{i=1..m} p_i        (estimate of |ground truth|)
    expected hits        H  = Σ_{i=1..k} p_i
    P̂ = H / k ,  R̂ = H / max(T̂, H, ε)
    F̂(k) = 1.25·P̂·R̂ / (0.25·P̂ + R̂)
E[F0.5(0)] = Π_{i=1..m} (1 − p_i)          # the probability the entity is genuinely a singleton
choose k* = argmax over k ∈ {0..min(m, CAP)}
```

Use the Monte-Carlo variant (200 samples of the Bernoulli vector, exact F<sub>0.5</sub> per sample) to sanity-check
the plug-in formula on validation; in the tested simulation the two agree to 0.0002 and both beat the best global
threshold by +0.0165. **This only works if the probabilities are calibrated** — with miscalibrated scores, expected-
F<sub>0.5</sub> selection can be worse than a plain threshold, which is why R2's isotonic calibration is a hard
dependency, not a nicety.

Why this matters, from the measured metric behaviour: for a true singleton, one false positive costs the **full
1.0** on that entity; for `T=1`, predicting 2 records scores 0.556 instead of 1.000. A global threshold cannot
express "this entity is probably a singleton" — expected-F<sub>0.5</sub> selection can, and it recovers most of the
5.58% singleton mass.

Add one tunable **safety margin** `p ← p − δ_country` (or a multiplicative shrink) fitted on validation per country
group, to handle the fact that the test pool is ~23% denser in distractors than train.

### 8.3 Emission

- One row per test S1 entity, **always** (1,732,544 + header). Entities with no candidates or `k*=0` get an empty field.
- `candidate_pairs.tsv` must be the **post-pruning** candidate set actually scored by the model (the organisers are
  explicit: the last stage before inference), and `matching_results.tsv` ⊆ it.
- Always run the provided validator before uploading:
  ```bash
  python3 utils/validate_submission.py --matching output/matching_results.tsv \
      --candidate output/candidate_pairs.tsv --test-dir dataset/test
  ```

## 9. Compute plan

**Local (primary):** 12 cores / 7.9 GB. Everything must be chunked. Per-country, per-chunk sparse matmul with
`sparse_dot_topn` (multi-threaded) is the workhorse; write parquet after every stage so any step can be resumed.
Raise the WSL memory cap to 12 GB in the first hour if the host allows.

**AWS (burst, from the $100 + up-to-$100 bonus credits):** use it for the two things local cannot do —
(a) the full-test embedding pass if G4 is adopted: one `g4dn.xlarge` (~$0.53/h) or SageMaker `ml.g4dn.xlarge`,
~2–3 h ≈ $1.60; (b) a memory-heavy full-scale run: one `r6i.4xlarge` (128 GB, ~$1.01/h) for 10–15 h ≈ $15.
Use **SageMaker Batch Transform, not endpoints**, if any SageMaker inference is needed — endpoints bill $0.12/h and
are the classic way to burn credits. Stop JupyterLab spaces and delete endpoints the moment you are done
(checklist in `08_RISKS_RULES_COST.md`). Set a billing alert on day 1 (it also earns $20 in credits).

**Total projected spend: under $25 of $100+.** Cost is not the constraint here; wall-clock is.

## 10. Reference implementations

Working, tested code for the three pieces everything else depends on is in
[`reference_code/`](reference_code/):

| File | What |
|---|---|
| `f05_score.py` | the official macro F<sub>0.5</sub>, plus per-slice breakdown — **use this, do not re-implement the metric** |
| `make_val_split.py` | deterministic hash-based entity split with country-stratified stats |
| `select_matches.py` | expected-F<sub>0.5</sub> subset selection (plug-in + Monte-Carlo) and the mutual-exclusivity pass |

They are deliberately dependency-free (stdlib only) so they run before the venv exists.
