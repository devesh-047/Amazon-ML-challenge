# Amazon ML Challenge 2026 — Project Guide

> Extracted from the official Best Practices Virtual Session (48-min recording).
> Use this as the persistent reference for all hackathon development.

---

## 1. AWS Account & Credits

### Initial Credits
- **$100 AWS credits** are automatically provisioned when you activate your AWS Builder account.
- Check credits: **Billing & Cost Management → Credits** in the AWS Console.

### Earning an Extra $100 (5 activities × $20 each)
Complete these **by 25 March 2027** to earn $20 per activity:

| # | Activity | Reward |
|---|----------|--------|
| 1 | Launch an EC2 instance | $20 |
| 2 | Use a model in Amazon Bedrock Playground | $20 |
| 3 | Set up a Cost Budget (billing alert) | $20 |
| 4 | Create a web app using AWS Lambda | $20 |
| 5 | Complete the 5th onboarding activity (check console) | $20 |

**Total possible credits: $200**

### Cost Management — Critical Rules
- **Running endpoints cost ~$0.12/hour.** Forgetting one over a weekend = ~$6. Over a month = ~$90.
- **Training jobs auto-terminate** — no cleanup needed.
- **Model artifacts in S3** are essentially free (5 GB free storage).
- **Always delete endpoints** when done for the day.
- **Stop JupyterLab spaces** when not actively working (Studio → JupyterLab → Stop).

---

## 2. AWS SageMaker Studio Setup (Builder Center)

### Setup Flow
1. Go to **Amazon SageMaker** in the AWS Console.
2. Open **SageMaker Studio** (or SageMaker Unified Studio).
3. Studio auto-provisions behind the scenes:
   - IAM execution role
   - Default S3 bucket
   - EC2 instances
   - The studio environment itself
4. Go to **JupyterLab** inside Studio.
5. Click **Launch Now** — creates a notebook instance (`ml.t3.medium`, 5 GB, 4 GB RAM by default).
6. Select a **Python 3** notebook.
7. Install SageMaker SDK: `!pip install sagemaker`

### Key SDK Setup (Cell 1–2)
```python
import sagemaker
from sagemaker import Session

session = sagemaker.Session()          # connects to SageMaker service
role = sagemaker.get_execution_role()  # IAM role for S3/compute access
bucket = session.default_bucket()      # auto-created S3 bucket
region = session.boto_region_name
```

---

## 3. ML Workflow — Step by Step

### 3.1 Data Loading
- **Challenge data** will be provided by the Amazon ML Challenge team — upload it to your own S3 bucket.
- The demo used a public AWS dataset; your workflow will differ at the ingestion step.

### 3.2 Exploratory Data Analysis (EDA)
- **Always check target variable distribution first** (balanced vs. skewed).
- Check for **missing values** — challenge data will likely have them.
- Check **column types** (int64, float64, object) — determines encoding strategy.
- **Handle missing data**: fill, drop, or use algorithms that handle it natively.

### 3.3 Feature Engineering
- **Drop unique identifiers** (phone numbers, serial numbers, row IDs) — they add no predictive value.
- **Drop redundant features** (e.g., if `charge = minutes × fixed_rate`, keep only one). Redundancy confuses models.
- **Encode categorical variables**: Yes/No → 1/0; multi-category columns → one-hot encoding (`pd.get_dummies()`).
- **Read your algorithm's documentation** for input format requirements before engineering features.

### 3.4 XGBoost-Specific Formatting Rules
> **These are the #1 source of errors. Memorize them.**

1. **No column headers** in the CSV.
2. **Target column must be the FIRST column** (column index 0).
3. Everything must be **numeric** (encode all text/categorical before training).
4. Google: *"input format XGBoost SageMaker"* — the docs page specifies this exactly.

### 3.5 Data Splitting
| Split | Percentage | Purpose |
|-------|-----------|---------|
| Training | ~67% | Model learns from this |
| Validation | ~22% | Model checks progress (practice test) |
| Test | ~11% | **Final exam** — never shown to model until fully done training |

- Use `random_state=42` (or any fixed seed) for **reproducible splits**.
- **Golden rule: Never touch your test set until you are completely done training.**
- Save each split as a separate CSV and upload to S3.

### 3.6 Model Training (SageMaker Managed)
```python
# Get the pre-built XGBoost container
from sagemaker import image_uris
image = image_uris.retrieve('xgboost', region, version='latest')

# Hyperparameters (starting defaults — TUNE THESE)
hyperparameters = {
    'max_depth': 5,           # tree complexity
    'eta': 0.2,               # learning rate
    'num_round': 100,         # number of boosting rounds
    'objective': 'binary:logistic'  # binary classification
}
```

- Training is **covered by the free tier** for small instances.
- SageMaker provisions machines, trains, and shuts them down automatically.
- **Pro tip: Play with hyperparameters to improve accuracy.**

### 3.7 Model Deployment
SDK V3 deployment = 3 steps:
1. **Create a Model** (from training artifacts)
2. **Create an Endpoint Configuration**
3. **Create an Endpoint** (live REST API)

The endpoint accepts data via API calls and returns predictions in real time.

### 3.8 Predictions & Thresholding
- Model outputs a **probability between 0 and 1** (confidence score).
- Default threshold: **0.5** (above → positive class, below → negative class).
- **Tweak the threshold for the challenge** — 0.5 is safe but not always optimal.
- Higher confidence score = more certain prediction.

---

## 4. Evaluation Metrics

| Metric | What It Measures | Analogy |
|--------|-----------------|---------|
| **Accuracy** | % of all predictions correct | Overall grade |
| **Precision** | Of predicted positives, how many are truly positive | "When I flag someone, am I right?" |
| **Recall** | Of all actual positives, how many did we catch | "Did I catch all real cases?" |
| **F1 Score** | Harmonic mean of precision & recall | "Am I good at both?" |

### Critical for the Challenge
- **Pay close attention to which metric the leaderboard uses.**
- The challenge may weight **precision and recall differently** — don't just optimize accuracy.
- F1 is often the most important metric in practice.

---

## 5. SageMaker Features to Explore

| Feature | What It Does | When to Use |
|---------|-------------|-------------|
| **Batch Transform** | Process an entire file of predictions at once (no live endpoint) | More cost-effective for competition-style workflows |
| **SageMaker Autopilot** | Auto-tries multiple algorithms + feature engineering | Quick baseline — give it data, it finds a good model |
| **Hyperparameter Tuning Jobs** | Define search ranges, SageMaker runs parallel training jobs | Finding the best hyperparameter combination |
| **SageMaker Experiments** | Track model versions, parameters, metrics | Compare runs and iterate systematically |

**Golden rule: Start simple (like the XGBoost demo), then layer on these advanced features to improve your score.**

---

## 6. Pro Tips from the Session

1. **Read the documentation** for every algorithm you use — 5 minutes of reading saves hours of debugging.
2. **Check target distribution** before anything else (balanced vs. skewed changes your approach).
3. **Start simple, iterate** — get a baseline working first, then optimize.
4. **Use Batch Transform** instead of live endpoints for generating competition predictions (cheaper).
5. **Delete endpoints immediately after use** — they cost $0.12/hr.
6. **Stop JupyterLab** when done for the day.
7. **Set up a cost budget/alert** (it's also worth $20 in credits).
8. **Use any IDE** (VS Code, JupyterLab, Bedrock for code generation) — Studio is recommended because it provisions infrastructure automatically.
9. The demo achieved **91.6% accuracy with no tuning** — hyperparameter tuning and better feature engineering will improve this.
10. **Confidence scores matter** — the challenge may involve human review of borderline cases.

---

## 7. Resource Cleanup Checklist

- [ ] Delete SageMaker Endpoint
- [ ] Delete Endpoint Configuration
- [ ] Delete Model resource
- [ ] Stop JupyterLab space (Studio → JupyterLab → Stop)
- [ ] Verify no running instances in EC2 dashboard

---

## 8. Quick Reference Links

- **SageMaker Built-in Algorithms Docs**: Search "Amazon SageMaker [algorithm name] input format"
- **Blog post**: Shared in session chat (check Amazon ML Challenge communications)
- **Support contact**: Session presenter available on LinkedIn and Instagram for AWS/SageMaker operational questions (not solutions)

---

## 9. Development Workflow Summary

```
Upload Data to S3
    → EDA (check distribution, missing values, types)
    → Feature Engineering (drop IDs, encode categoricals, remove redundancy)
    → Format for Algorithm (target first, no headers, all numeric)
    → Split (67% train / 22% val / 11% test)
    → Upload splits to S3
    → Train with SageMaker (XGBoost or other)
    → Tune Hyperparameters
    → Evaluate (precision, recall, F1 — match leaderboard metric)
    → Generate Predictions (Batch Transform or Endpoint)
    → Submit
    → DELETE ALL RESOURCES
```
