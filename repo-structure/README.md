# Amazon ML Challenge - Entity Value Extraction

## Team Structure & Roles

### R1: Data Preprocessing & Augmentation
**Owner:** TBD  
**Location:** `src/preprocessing/`  
**Responsibilities:**
- Clean and validate train.csv dataset
- Handle missing values and data quality issues
- Augment training data if needed
- Create train/validation splits
- Prepare data for R2 and R3

**Outputs:**
- `data/processed/train_clean.csv`
- `data/processed/val_clean.csv`
- Data quality report

---

### R2: Text-Based Feature Extraction
**Owner:** TBD  
**Location:** `src/text_extraction/`  
**Responsibilities:**
- Extract entity values from product titles
- Use regex patterns for structured extraction
- Implement NLP-based extraction (NER, pattern matching)
- Handle unit conversions and normalization
- Generate text-based features

**Outputs:**
- `data/features/text_features.csv`
- Extracted patterns and rules

---

### R3: Block-Level Visual Extraction & Encoding
**Owner:** Aarya  
**Location:** `ber/` and `src/block_extraction/`  
**Responsibilities:**
- Detect and extract visual blocks from product images
- Generate embeddings using vision models (CLIP/ViT)
- Create visual feature representations
- Handle different image layouts

**Outputs:**
- `data/interim/image_blocks/`
- `data/embeddings/block_embeddings.pkl`
- Block detection metadata

---

### R4: Visual-Text Matching & Fusion
**Owner:** TBD  
**Location:** `src/matching/`  
**Responsibilities:**
- Match text features with visual blocks
- Fuse multimodal information
- Create combined feature representations
- Cross-modal attention mechanisms

**Outputs:**
- `data/features/multimodal_features.pkl`
- Matching scores and confidence metrics

---

### R5: Model Training & Ensemble
**Owner:** TBD  
**Location:** `src/ensemble/`  
**Responsibilities:**
- Train classification/regression models
- Implement ensemble methods
- Hyperparameter tuning
- Generate final predictions
- Create submission files

**Outputs:**
- `data/models/` - Trained model checkpoints
- `data/submissions/submission.csv`
- Model performance reports

---

## Project Structure

```
Amazon-ML-challenge/
├── data/
│   ├── raw/              # Original dataset (train.csv, test.csv, images/)
│   ├── processed/        # Cleaned and processed data (R1 output)
│   ├── interim/          # Intermediate processing results (R3 blocks)
│   ├── embeddings/       # Visual embeddings (R3 output)
│   ├── features/         # Extracted features (R2, R4 output)
│   ├── models/           # Trained models (R5 output)
│   └── submissions/      # Final submission files (R5 output)
│
├── src/
│   ├── preprocessing/    # R1: Data cleaning and preparation
│   ├── text_extraction/  # R2: Text-based feature extraction
│   ├── block_extraction/ # R3: Visual block extraction
│   ├── matching/         # R4: Visual-text matching
│   ├── ensemble/         # R5: Model training and ensemble
│   └── utils/            # Shared utilities
│
├── ber/                  # R3: Block Extraction & Encoding workspace
│   ├── src/
│   ├── data/
│   └── .venv/
│
├── configs/              # Configuration files
├── notebooks/            # Jupyter notebooks for exploration
├── tests/                # Unit tests
├── scripts/              # Utility scripts
└── docs/                 # Documentation

```

## Workflow Pipeline

1. **R1** → Cleans data → Outputs to `data/processed/`
2. **R2** → Processes text → Outputs to `data/features/text_features.csv`
3. **R3** → Extracts image blocks → Outputs to `data/embeddings/`
4. **R4** → Matches text + visual → Outputs to `data/features/multimodal_features.pkl`
5. **R5** → Trains models → Outputs to `data/submissions/`

## Getting Started

### Prerequisites
- Python 3.14+
- Git

### Setup
```bash
# Clone repository
git clone <repo-url>
cd Amazon-ML-challenge

# Each role should create their own virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (role-specific)
pip install -r requirements.txt
```

### Role-Specific Setup
See individual README files in each role's directory:
- `src/preprocessing/README.md` - R1 setup
- `src/text_extraction/README.md` - R2 setup
- `ber/README.md` - R3 setup
- `src/matching/README.md` - R4 setup
- `src/ensemble/README.md` - R5 setup

## Data Dependencies

| Role | Needs Input From | Provides Output To |
|------|------------------|-------------------|
| R1   | Raw data         | R2, R3            |
| R2   | R1               | R4, R5            |
| R3   | R1               | R4, R5            |
| R4   | R2, R3           | R5                |
| R5   | R2, R3, R4       | Final submission  |

## Communication & Coordination

- **Data Formats:** All teams should document their output formats
- **Dependencies:** Check `data/` folder for required inputs before starting
- **Updates:** Notify team when your outputs are ready
- **Issues:** Create GitHub issues for blockers or questions

## Current Status

- [x] Repository structure created
- [x] R3 environment setup in progress
- [ ] R1 setup
- [ ] R2 setup
- [ ] R4 setup
- [ ] R5 setup

## Contact

- **R1:** TBD
- **R2:** TBD
- **R3:** Aarya
- **R4:** TBD
- **R5:** TBD

---

Last Updated: 2026-09-25
