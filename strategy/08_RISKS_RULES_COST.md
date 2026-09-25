# Risks, Rules & Cost Control

---

## 1. Disqualification risks — read once, obey always

| Rule | What it means for us |
|---|---|
| **No external data lookup.** No entity-resolution APIs, no business registries, no government databases, no geocoding APIs, no internet data augmentation. Violation = immediate disqualification, and all pipelines are reviewed. | Every dictionary we use — abbreviations, state codes, transliteration, stop tokens, city/geo tokens — is **mined from the provided train/test files**. No `pip install us-states`, no offline gazetteer, no copy-pasted list of Indian PIN codes, no `geopy`. If someone is unsure whether a resource is allowed, the answer is: derive it from the data instead. It is also *better* — we have 7.6M labelled pairs. |
| **Final model must be MIT/Apache-2.0 licensed and ≤8B parameters.** | LightGBM (MIT) ✔, scikit-learn (BSD-3) ✔, scipy/numpy (BSD) ✔, polars (MIT) ✔, sparse-dot-topn (Apache-2.0) ✔. If embeddings are used: `intfloat/multilingual-e5-small` MIT/118M ✔, `LaBSE` Apache-2.0/471M ✔, `paraphrase-multilingual-MiniLM-L12-v2` Apache-2.0/118M ✔. **Avoid** anything CC-BY-NC, Llama-community-licensed, or >8B. Record licence + param count for every artefact in the methodology doc. |
| Pretrained open-source models are allowed; they are a *model*, not an external lookup. | Using LaBSE to embed the provided strings is fine. Using an API to look up "is this business real" is not. |
| **Max 5 submissions/day, version history required.** | R3 owns `runs/RUNLOG.md` and the submission schedule. |
| One device per participant, no simultaneous portal logins. | Only R3 drives the portal. Do not log in from two machines. |
| No multiple accounts / plagiarism. | n/a — but do not paste a public solution wholesale; the packages of top teams are reviewed in detail. |
| Top-100 teams must submit methodology, blocking strategy, model architecture & feature engineering. | Write it as you go, not at 23:00 on day 3. Each role produces their own section at each checkpoint. |

**Borderline call, decided:** using the *test* source files to compute corpus statistics (per-country IDF, stop
tokens, DF-based geo-token detection) is **allowed** — the test data is provided to us and this is transductive
feature computation, not external lookup. It is also the mechanism that makes France work. Document it explicitly in
the methodology doc so a reviewer sees the reasoning rather than guessing.

## 2. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| 1 | **France collapses** (15% of the score, zero training data) | High | ~7 pts | corpus-derived per-country stats instead of hard-coded rules; no country one-hots; country-relative features only; LOCO validation; hand-audit 50 French candidate sets | R2 + R1 |
| 2 | **OOM on 7.9 GB RAM** | High | hours lost | per-country partitioning, chunked parquet, polars/duckdb streaming, raise WSL cap to 12 GB, resumable stages | R3 |
| 3 | **Full test pass does not finish in time on day 3** | Medium | fatal | measure wall-clock on day 1 and extrapolate; every stage resumable and checkpointed; code freeze at 16:00 D3 leaving 2.5 h for the run; AWS `r6i.4xlarge` as the escape hatch | R3 |
| 4 | **Over-merging destroys precision** (39.5% of S1 names are ambiguous chains) | High | 5–15 pts | address-dominant features; `geo_conflict` and `max-unshared-IDF` features; mutual exclusivity; expected-F<sub>0.5</sub> selection; conservative δ | R2 + R3 |
| 5 | Submission rejected on format | Medium | a submission slot | assert invariants in `emit.py`, then always run `utils/validate_submission.py`; the 1,732,544-row check | R3 |
| 6 | Training on easy/random negatives → confident false positives | Medium | 5+ pts | train on R1's real blocked candidates only | R2 |
| 7 | Val/test mismatch (test pool is 23% denser in distractors) | High | 1–3 pts | full-corpus validation pool + per-country δ safety margin; compare val↔LB direction | R3 |
| 8 | Leaderboard overfitting with 15 probes | Medium | ranking loss | never tune on LB; private board decides | R3 |
| 9 | Embedding path (G4) eats the schedule | Medium | opportunity cost | strictly timeboxed, applied only to the no-lexical-hook subset, first item on the cut list | R1 |
| 10 | Calibration drift → expected-F<sub>0.5</sub> selection misfires | Medium | 3–5 pts | separate `calib` split, reliability plots, plug-in vs Monte-Carlo cross-check | R2 + R3 |
| 11 | Methodology doc / reproducible zip missing or thin | Low | top-100 exclusion | start at 19:00 D3; each role drafts their section at each checkpoint; verify the zip by extraction | all |
| 12 | Someone works 48 h straight and breaks the pipeline at hour 40 | High | unbounded | the staggered sleep schedule in `03_TIMELINE_AND_CHECKPOINTS.md` is a deliverable, not a suggestion | all |
| 13 | Two people edit the same module | Medium | merge pain | frozen file contracts + role-owned directories; branch per role; merge at every checkpoint | all |
| 14 | Portal slowness / upload failure in the final hour | Medium | fatal | final upload at 18:30–19:30 D3, ~4.5 h of buffer; nothing scheduled after 23:00 | R3 |

## 3. Cost control (AWS)

Credits: **$100** on activation, plus up to **$100** more from five onboarding activities ($20 each: launch an EC2
instance, use a model in the Bedrock playground, **set a cost budget/alert**, create a Lambda web app, and the fifth
listed in the console). Check at Billing & Cost Management → Credits.

Planned spend — this project is wall-clock-bound, not cost-bound:

| Item | Instance | Rate | Hours | Cost |
|---|---|---|---|---|
| GPU embedding pass (only if G4 adopted) | `g4dn.xlarge` | ~$0.53/h | 3 | ~$1.60 |
| Memory-heavy full-scale run (escape hatch) | `r6i.4xlarge` (128 GB) | ~$1.01/h | 15 | ~$15 |
| S3 storage for ~4 GB of data + artefacts | S3 | ~$0.023/GB-mo | — | <$1 |
| **Total** | | | | **< $25** |

Hard rules, straight from the official best-practices session:
- **Use Batch Transform, not live endpoints,** for any SageMaker inference. Endpoints bill **$0.12/h**
  continuously — one forgotten over a weekend is ~$6, over a month ~$90.
- Training jobs auto-terminate; endpoints and JupyterLab spaces do not.
- Set the cost budget/alert on day 1 (it is also worth $20 in credits).

**Cleanup checklist — run at the end of every AWS session:**
- [ ] delete the SageMaker endpoint
- [ ] delete the endpoint configuration
- [ ] delete the model resource
- [ ] stop the JupyterLab space (Studio → JupyterLab → Stop)
- [ ] confirm nothing is running in the EC2 dashboard
- [ ] check Billing → Credits for unexpected burn

## 4. Things that look clever and will cost you the competition

- **Chasing recall.** The metric weights precision 2×. `P=1.00, R=0.75` scores 0.9375; `P=0.75, R=1.00` scores 0.7895.
- **A single global probability threshold.** It cannot express "this entity is probably a singleton", and 5.58% of
  entities are singletons worth a full 1.0 each.
- **Fine-tuning a big transformer cross-encoder over 35–50M pairs** on a $100 budget with no local GPU and 55 hours.
- **Training on random negatives.** Your blocked candidates are the hard negatives; use them.
- **One-hot encoding `country`.** France has zero training rows. The README explicitly warns about this.
- **Hard-coding US state or Indian PIN lists.** Mine them from the ground truth — and stay on the right side of the
  external-data rule.
- **Tuning on the public leaderboard** with 15 probes while the private board decides the ranking.
- **Leaving the methodology document and the reproducible zip to the last hour.** Both are required artefacts.
