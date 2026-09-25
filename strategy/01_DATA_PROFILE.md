# Data Profile — measured facts

Every number below was measured on the actual files on 25 Sep 2026, before any modelling. Reproduce with the
snippets at the bottom. **Do not re-derive these; build on them.**

Dataset root: `amazon-ml-challenge-dataset/student_resource/dataset/`

---

## 1. Volumes

| File | Rows (excl. header) | Size |
|---|---:|---:|
| `train/train_source1.tsv` | 2,206,821 | 210 MB |
| `train/train_source2.tsv` | 5,034,616 | 489 MB |
| `train/train_source3.tsv` | 5,285,603 | 504 MB |
| `train/train_ground_truth.tsv` | 2,206,821 | 127 MB |
| `test/test_source1.tsv` | **1,732,544** | 175 MB |
| `test/test_source2.tsv` | 4,887,273 | 509 MB |
| `test/test_source3.tsv` | 5,082,316 | 506 MB |

- Candidate pool per S1 entity: train **4.68** S2+S3 records per S1, test **5.75**. The test pool is ~23% denser in
  distractors per entity → **expect slightly worse precision on test than on validation at the same threshold.**
- `train` and `test` entity IDs are **disjoint** (verified: 0 overlap for S1 and for S2). No leakage shortcut, and
  no mixing pools.
- Schema is identical in all 6 source files: `entity_id  business_name  business_address  country` (tab-separated).
  Ground truth: `source1_entity_id  matched_entity_ids` (comma-separated ID list, empty for singletons).

## 2. Ground-truth structure

| Property | Value |
|---|---|
| S1 entities | 2,206,821 |
| **Singletons (no match)** | **123,247 = 5.58%** |
| Mean matches per entity | 3.461 |
| Total matched S2 IDs | 3,693,619 |
| Total matched S3 IDs | 3,944,746 |
| **Matched S2/S3 IDs used by >1 S1 entity** | **0 of 7,638,365** ← mutual exclusivity holds globally |
| Unmatched ("distractor") S2 records | 1,340,997 = **26.6% of S2** |
| Unmatched ("distractor") S3 records | 1,340,857 = **25.4% of S3** |

Match-count histogram (per S1 entity):

| #matches | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| share | 5.58% | 5.40% | 17.00% | 24.05% | 21.94% | 14.59% | 7.47% | 2.90% | 0.85% | 0.19% | 0.02% | ~0% |

Per-source cardinality (hard caps observed in train):

| # S2 matches | 0 | 1 | 2 | 3 | 4 | 5 | **max = 5** |
|---|---|---|---|---|---|---|---|
| share | 13.04% | 35.76% | 29.58% | 15.13% | 5.40% | 1.09% | |

| # S3 matches | 0 | 1 | 2 | 3 | 4 | 5 | 6 | **max = 6** |
|---|---|---|---|---|---|---|---|---|
| share | 12.07% | 32.46% | 30.29% | 16.88% | 6.58% | 1.60% | 0.13% | |

**Exploitable:** never emit more than 5 S2 or 6 S3 IDs for one entity; 99%+ of entities have ≤4 of each.
The match-count distribution is also a usable prior for the set-size decision (see `07_EVALUATION_PROTOCOL.md`).

## 3. Country

| File | US | India | France |
|---|---:|---:|---:|
| train S1 | 1,323,633 (60.0%) | 883,188 (40.0%) | — |
| train S2 | 3,016,817 (59.9%) | 2,017,799 (40.1%) | — |
| train S3 | 3,170,056 (60.0%) | 2,115,547 (40.0%) | — |
| **test S1** | 663,106 (38.3%) | 809,986 (46.8%) | **259,452 (15.0%)** |
| test S2 | 1,871,330 (38.3%) | 2,312,565 (47.3%) | 703,378 (14.4%) |
| test S3 | 1,945,701 (38.3%) | 2,405,000 (47.3%) | 731,615 (14.4%) |

- **Zero true pairs cross country** (207,310 pairs checked). Country is a hard partition.
- **France is 15% of the score with zero training data.** If France scores 0.40 while US/India score 0.90, the
  total is 0.82 — i.e. France alone can cost ~7.5 points. Treat it as a first-class workstream, not an afterthought.
- Because India is 40% of train but 47% of test, weight validation metrics by the *test* country mix when comparing
  models (R3 owns this in the scorer harness).

## 4. Noise characteristics

Measured on true pairs (69,144 pairs from 20,000 sampled S1 entities), after lowercasing + punctuation stripping:

| Signal | p05 | p25 | median | mean | fraction == 0 |
|---|---|---|---|---|---|
| name token Jaccard | 0.00 | 0.50 | 0.67 | 0.61 | **14.5%** |
| address token Jaccard | 0.12 | 0.43 | 0.67 | 0.61 | **4.4%** |

- share ≥1 name token: **85.49%** → a name-token-only blocker caps recall at 85.5%.
- share ≥1 *rare* name token (df < N/1000): 54.63%.
- share ≥1 numeric address token: **75.56%** → house/plot numbers are a strong, cheap key.
- **Empty `business_address`:** train S2 3.36%, train S3 3.33%, test S2 2.65%, test S3 2.68%. S1 is never empty.
  These records can only be matched on name → they need their own retrieval path and their own model treatment.
- `business_name` is never empty anywhere.

### Script / transliteration

| File | non-ASCII names | domain-style names (`*.com`, `.in`, …) | dominant scripts |
|---|---:|---:|---|
| train S1 | 0.00% | 0.00% | — |
| train S2 | **15.19%** | 4.00% | Devanagari 479,500; Kannada 66,637; Telugu 65,393; Tamil 60,220; Gujarati 54,763; Bengali 54,757 |
| train S3 | **11.48%** | 3.99% | Devanagari 394,374; Kannada 55,457; Telugu 52,500; Tamil 49,864; Bengali 45,061; Gujarati 45,006 |
| test S1 | 2.35% (French accents) | 0.00% | Latin |
| test S2 | **18.99%** | 3.19% | Devanagari 550,530; Kannada 78,006; Telugu 75,238; Tamil 69,865; Bengali 63,445; Gujarati 63,211 |
| test S3 | **14.51%** | 3.23% | Devanagari 454,885; Kannada 64,518; Telugu 60,471; Tamil 57,708; Gujarati 52,233; Bengali 51,991 |

**S1 names are always Latin; 15–19% of S2/S3 names are in Indic scripts.** Those pairs have name-Jaccard 0 by
construction — they are most of the 14.5% zero-overlap bucket. Two legitimate fixes, both self-contained:
1. **Mine a transliteration/translation table from the ground truth itself.** Train has ~550K Devanagari S2 records
   whose S1 partner is Latin → align tokens (co-occurrence / IBM-Model-1 style) to learn
   `प्राइवेट → private`, `लिमिटेड → limited`, and proper-noun character mappings. Free, rule-compliant, and
   tuned to this corpus.
2. **Multilingual embeddings** (LaBSE / multilingual-e5) for the residual.
Their addresses are usually Latin, so **address retrieval is the reliable path for Indic-script records.**

### Observed noise patterns (real examples from the data)

| Pattern | Example |
|---|---|
| component reordering (address) | `2902 Deer Run, Tombstone, AZ` ↔ `290 Deer Run, Tombstone, Arizona` |
| state code ↔ full name | `NC` ↔ `North Carolina` |
| token transposition (name) | `Engineering Pr Services Private Limited` ↔ `Private Engineering Pr Services Limited` |
| legal-suffix noise | `Moran Signature Ameren, LLC` ↔ `Moran Signature Ameren, L.L.C.` |
| DBA / "formerly" prefixes | `Murphy Space, Inc.` ↔ `Wexpyrahalo D.B.A. Murphy Space, Inc.` |
| domain-name variant | `Silver Infotech Private Limited` ↔ `Shri silverinfotechprivate.com` |
| suffix added/removed | `Trapani & Alvarez Shreya` ↔ `Trapani & Alvarez Shreya Corporation` |
| house-number corruption | `2902` → `290`, `803 23rd St` → `78 23rd St` |
| empty address | `Niseor LLC / 131 Burns Terrace, Penn Yan, NY` ↔ `Niseor  LLC / ''` |
| landmark addresses (India) | `Opp. Ex-M.L.A. House Indira Gandhi Street, Patancheru` |
| junk prefixes | `-- Holloway Peak Inc Seafood`, `<< Team Ecole` |
| Indic script name, Latin address | `राम मार्केटिंग प्राइवेट लिमिटेड / KH NO. -570/13, NEW DELHI, WEST DELHI, Delhi` |
| Indic script *inside* address | `… Jayanagar, Bengaluru Urban, Bangalore, ಕರ್ನಾಟಕ` |

## 5. Ambiguity — why address is the discriminator

- Distinct sorted name-token-sets in train S1: 1,516,714 out of 2,206,821 records.
- **872,465 S1 entities (39.53%) share their name-token-set with at least one other S1 entity.**
- Most frequent collisions are chains/medical practices: `care group primary` ×259, `ear group nose throat` ×254,
  `group pediatric` ×225, `group physical therapy` ×221, `group health womens` ×220.
- Most frequent name tokens (train S1): `limited` 522,340 · `private` 432,394 · `llc` 355,736 · `inc` 238,309 ·
  `ltd` 148,598 · `pvt` 121,462 · `india` 59,420 · `and` 57,296 · `care` 52,891 · `associates` 42,804 ·
  `group` 40,358 · `llp` 39,726 · `center` 35,261 · `partners` 34,952 · `corp` 34,738.

**Consequence:** a model that weights name similarity heavily will confidently merge two different branches of the
same chain — the single most expensive error class under F<sub>0.5</sub>. Address agreement (especially the numeric
component) must dominate the decision. Stop-tokens / IDF must be computed **per country from the corpus**, which
also auto-handles French legal forms (`SARL`, `SAS`, `EURL`) and street words (`rue`, `boulevard`).

## 6. Blocking micro-benchmark (already run — this is your baseline to beat)

Setup: 20,000 sampled train S1 entities as probes. Corpus = all their true matches ∪ a hash-sampled 1/10 of
train S2+S3 (1,093,071 records), so **pair recall is exactly measurable** while candidate counts are measured at
1/10 density (multiply by ~10 for full scale).

Keys used: `(country, rare name token)` ×3 · `(country, rare numeric addr token, rare addr word)` ×4 ·
`(country, rare name token, rare addr word)`; blocks larger than 300 discarded.

| Configuration | Pair recall | Candidates kept / S1 |
|---|---:|---:|
| union of token keys (no pruning) | **0.8877** | 79.2 @1/10 density (≈790 @full) |
| + cheap IDF-weighted top-K, K=40 | 0.8814 | 22.0 |
| + K=20 | 0.8766 | 13.0 |
| + K=10 | 0.8690 | 7.5 |
| + K=5 | 0.8167 | 4.3 |

Read this carefully — it is the most actionable result in this document:

1. A plain token-key blocker reaches **88.8% pair recall**, so the recall ceiling is already survivable.
2. **Cheap pre-scoring then top-K pruning is almost free**: K=20 keeps 98.8% of the retrieved recall while cutting
   candidates by 6×. Two-stage candidate generation is therefore the right design, and the model only needs to
   score ~20–30 pairs per entity (≈35–50M pairs for the full test set — tractable on CPU with LightGBM).
3. The missing ~11% is *not* in the pruning, it is in the retrieval: Indic-script names, empty addresses,
   domain-style names, heavy typos. Those need char-n-gram TF-IDF and embedding kNN — that is R1's improvement path.
4. Runtime for this benchmark: 73 s for 20k probes against a 1.09M corpus in pure Python. Full test scale is
   ~87× more probes against ~9× the corpus → **pure Python will not finish. Vectorise (sparse matmul) from day 1.**

## 7. Environment (verified on this machine)

| Item | Status |
|---|---|
| Python | 3.12.3 |
| `pip` / `pandas` / `numpy` | **not installed** — but `python3 -m venv .venv` works and `pip install polars` succeeded (polars 1.44.2) |
| `sudo` | requires a password → assume **no apt installs** |
| CPU / RAM | 12 cores / **7.9 GB** (WSL2 default) |
| Disk | 948 GB free |
| GPU | none |
| Network / PyPI | reachable |

**RAM is the binding constraint**: a naive pandas load of the 6 source files will OOM. Mandated tooling:
`polars` (streaming/lazy), `duckdb` (out-of-core joins/aggregations), `scipy.sparse` + `sparse_dot_topn` for
top-K cosine, chunked parquet intermediates. If the Windows host has ≥16 GB, raise the WSL limit via
`%UserProfile%\.wslconfig` (`[wsl2]` / `memory=12GB` / `processors=12`) and `wsl --shutdown` — do this in the
first hour, it is the cheapest speedup available.

## 8. Reproduce these numbers

```bash
D=amazon-ml-challenge-dataset/student_resource/dataset

# volumes
for f in $D/train/*.tsv $D/test/*.tsv; do echo "$f $(( $(wc -l < $f) - 1 ))"; done

# GT distribution + singleton rate
awk -F'\t' 'NR>1{n=($2==""?0:split($2,a,","));h[n]++;s+=n;r++}
  END{printf "rows=%d avg=%.3f\n",r,s/r; for(k=0;k<=11;k++) printf "%d:%.2f%%\n",k,100*h[k]/r}' $D/train/train_ground_truth.tsv

# mutual exclusivity (every matched id used exactly once)
awk -F'\t' 'NR>1&&$2!=""{n=split($2,a,",");for(i=1;i<=n;i++)print a[i]}' $D/train/train_ground_truth.tsv \
  | sort -S1G --parallel=8 | uniq -c | awk '{h[$1]++}END{for(k in h)print k,h[k]}'

# country mix + empty address rate
for f in $D/train/*source*.tsv $D/test/*source*.tsv; do echo "== $f";
  awk -F'\t' 'NR>1{c[$4]++;if($3=="")e++;n++}END{for(k in c)printf "  %s %.1f%%\n",k,100*c[k]/n;
  printf "  empty_addr %.2f%%\n",100*e/n}' $f; done
```

The similarity, script, and blocking-benchmark measurements were produced by throwaway scripts; R1 should port them
into `src/analysis/` as permanent, re-runnable diagnostics (see `04_ROLE_R1_RECALL_BLOCKING.md` task R1-0).
