# R1 — Recall & Candidate Generation

**You own the ceiling.** No downstream model can recover a true match that never entered the candidate set. You also
own the `candidate_pairs.tsv` artefact the organisers audit for blocking quality (recall ceiling and reduction ratio).

**Your metrics:**
| Metric | Day-1 target | Final target |
|---|---|---|
| pair recall @ ≤30 candidates/S1 (validation) | ≥ 0.88 | **≥ 0.95** |
| candidates per S1 (mean) | ≤ 40 | ≤ 30 |
| full test-set candidate generation wall-clock | ≤ 3 h | **≤ 90 min** |
| recall on the non-Latin-name subset | measure it | ≥ 0.85 |
| recall on the empty-address subset | measure it | ≥ 0.80 |

Report all five at every checkpoint, **broken down by country**, and always include France-as-seen-in-test even
though you cannot score recall there (report candidate counts and eyeball 50 sets by hand instead).

---

## Start here (R1-0, 30 min)

Port the throwaway profiling scripts into `src/analysis/` so they are re-runnable:
`profile_gt.py`, `profile_scripts.py`, `bench_blocking.py`. The blocking benchmark harness is the single most useful
tool you will build — it measures exact pair recall cheaply using the trick from `01_DATA_PROFILE.md` §6
(corpus = all true matches ∪ hash-sampled 1/10 of the pool, so recall is exact while candidate counts scale by ~10).
**Every blocking change gets measured on it in under 3 minutes.** Do not iterate by intuition.

## R1-1 Normalisation (`src/common/normalize.py`)

Implement §4 of `02_TECHNICAL_SPEC.md` exactly — the output schema is a frozen contract that R2 reads.

Traps found in the real data, all of which will cost you recall if you get them wrong:
- **Do not ASCII-fold Indic scripts into mush.** Keep `name_script` and emit a separate transliterated variant.
- **Do not split digit-internal `/` and `-`.** `21/152` and `6-208` are Indian plot numbers and they are among the
  most discriminative tokens in the dataset. Emit both `21/152` and `21`,`152`.
- **French accents must fold** (`Président` → `president`) because the S2/S3 side may drop them. That is the
  2.35% non-ASCII in test S1.
- Junk prefixes are real: `-- Holloway Peak Inc Seafood`, `<< Team Ecole`. Strip leading/trailing non-alphanumerics.
- DBA wrappers (`Wexpyrahalo D.B.A. Murphy Space, Inc.`) must produce **two** name variants; index both.
- Domain-style names are 3–4% of S2/S3 (`silverinfotechprivate.com`). Strip the TLD and also index the raw string
  as char n-grams — that alone catches most of them.
- **Stop/legal tokens are computed per country from the corpus, never hard-coded.** This is what makes France work
  without French training data. Verify it by printing the learned French stop list — you should see `sarl`, `sas`,
  `rue`, `avenue`, `boulevard` appear automatically. If you do not, your DF threshold is wrong.

## R1-2 Mined maps (`src/block/mine_maps.py`)

Build `abbrev.tsv`, `state.tsv`, `translit.tsv`, `translit_char.json`, `stopdf.tsv` per §5 of the spec. You have
7,638,365 labelled pairs to mine from — including ~550K cross-script pairs where the S1 side is Latin and the
S2/S3 side is Devanagari. An IBM-Model-1 EM alignment over those pairs gives a better token dictionary than any
public transliteration table, and it is unambiguously rule-compliant because it never leaves the provided data.

Acceptance: ≥300 abbreviations, ≥45 US states, ≥25 Indian states, ≥2,000 transliteration entries, deterministic
output. Then **re-measure recall with and without the maps** so you can quantify what they bought — that number goes
in the methodology document.

## R1-3 Candidate generators

Build in this order, measuring after each. Expected recall contribution based on the profile:

| Order | Generator | Why this order |
|---|---|---|
| 1 | **G3 key joins** | cheapest, highest precision, no linear algebra. `(country, postal, addr_num)` and `(country, addr_num, rarest street token)` — 75.6% of true pairs share a numeric address token |
| 2 | **G2 address token TF-IDF top-40** | only 4.4% of true pairs share zero address tokens, and address is the discriminator for the 39.5% ambiguous-name entities |
| 3 | **G1 name char 3+4-gram TF-IDF top-40** | catches typos, suffix noise, transpositions and domain-style names that token keys miss |
| 4 | **G4 embedding kNN** — *only* for records with no lexical hook | the residual: non-Latin names, empty addresses, <3 candidates from G1–G3. ~15% of the pool, so ~1.5M records to embed, not 12M |

Then pre-score with the benchmarked formula and prune to `K_MAX=30`, **but always retain the top-1 from each
generator** regardless of prune rank.

### Engineering constraints you cannot ignore
- 7.9 GB RAM. Per-country partitioning is mandatory; sub-partition India further if needed. Write parquet per
  chunk and never hold two full sparse matrices at once.
- Pure Python will not finish: the benchmark took 73 s for 20k probes against a 1.09M corpus. Full scale is ~87×
  the probes against ~9× the corpus. Use `scipy.sparse` + `sparse_dot_topn.sp_matmul_topn` (multi-threaded, this is
  the tool built for exactly this problem) and `n_threads=12`.
- Make every stage **resumable**. If a 90-minute run dies at minute 80 on day 3, you need to restart from chunk 40,
  not chunk 0.

## R1-4 The two subsets that will decide whether you hit 0.95

1. **Non-Latin names (15–19% of the S2/S3 pool).** Their name-token Jaccard with the Latin S1 name is 0 by
   construction. Paths: mined transliteration → then lexical retrieval; address-only retrieval (their addresses are
   usually Latin); embedding kNN. Measure recall on this slice separately — it is probably your worst bucket.
2. **Empty addresses (~2.7% of test S2/S3).** Name-only retrieval, and the model must know it (the `has_addr` flag
   is in the contract). These are also the pairs where a false positive is most likely, so do not over-retrieve:
   flag them and let R3's decision layer be conservative.

## R1-5 Hand off to the audit

`candidate_pairs.tsv` must be the **last** candidate set before model inference — the organisers explicitly say so
and they compute reduction ratio and recall ceiling from it. Two invariants R3 will assert:
`matching_results.tsv ⊆ candidate_pairs.tsv`, and one row per test S1 entity (1,732,544).

## Definition of done

- [ ] `make candidates SPLIT=val` and `SPLIT=test` both run clean from a fresh checkout
- [ ] recall/candidate-count report committed for every config tried, per country and per subset
- [ ] mined maps committed with their support counts
- [ ] a written paragraph for the methodology doc: blocking strategy, keys used, recall ceiling, reduction ratio
- [ ] a ranked list of **missed true pairs** (blocking failures) handed to R2 as diagnostics
