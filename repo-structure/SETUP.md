# Project Setup Guide

## Quick Start for All Team Members

### 1. Clone Repository
```bash
git clone <repo-url>
cd Amazon-ML-challenge
```

### 2. Check Your Role
- **R1 (Data Preprocessing):** See `src/preprocessing/README.md`
- **R2 (Text Extraction):** See `src/text_extraction/README.md`
- **R3 (Visual Extraction):** See `ber/README.md`
- **R4 (Visual-Text Matching):** See `src/matching/README.md`
- **R5 (Model Training):** See `src/ensemble/README.md`

### 3. Initial Setup (All Roles)

```bash
# Create your virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install base dependencies
pip install pandas numpy scikit-learn matplotlib seaborn tqdm jupyter
```

### 4. Role-Specific Dependencies

#### R1: Data Preprocessing
```bash
# Uses base dependencies only
```

#### R2: Text Extraction
```bash
pip install spacy transformers regex nltk
python -m spacy download en_core_web_sm
```

#### R3: Visual Extraction (Aarya)
```bash
cd ber
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision transformers pillow opencv-python
```

#### R4: Visual-Text Matching
```bash
cd src/matching
python3 -m venv .venv
source .venv/bin/activate
pip install torch transformers scipy pandas numpy scikit-learn
```

#### R5: Model Training
```bash
cd src/ensemble
python3 -m venv .venv
source .venv/bin/activate
pip install xgboost lightgbm catboost optuna torch pandas numpy scikit-learn
```

## Data Flow

```
Raw Data → R1 → Cleaned Data
                     ↓
         ┌──────────┴──────────┐
         ↓                     ↓
    R2 (Text)            R3 (Visual)
         ↓                     ↓
         └──────────┬──────────┘
                    ↓
               R4 (Fusion)
                    ↓
            R5 (Model Training)
                    ↓
             Final Submission
```

## Getting Started Today

### For R1 (Data Preprocessing)
1. Download the competition dataset
2. Place files in:
   - `data/raw/train.csv`
   - `data/raw/test.csv`
   - `data/raw/images/` (image folder)
3. Start with data exploration
4. Read `src/preprocessing/README.md`

### For R2 (Text Extraction)
1. Wait for R1 to provide cleaned data
2. Meanwhile: Set up environment and explore sample data
3. Design regex patterns for common entity types
4. Read `src/text_extraction/README.md`

### For R3 (Visual Extraction) - Aarya
1. ✅ Environment setup in progress
2. Wait for installation to complete
3. Wait for R1 to provide cleaned data
4. Meanwhile: Design block detection strategy
5. Read `ber/README.md`

### For R4 (Visual-Text Matching)
1. Wait for R2 and R3 to provide features
2. Meanwhile: Set up environment
3. Design fusion strategy
4. Read `src/matching/README.md`

### For R5 (Model Training)
1. Wait for R2, R3, R4 to provide features
2. Meanwhile: Set up environment
3. Explore baseline models
4. Read `src/ensemble/README.md`

## Collaboration

### Communication Channels
- Create a team chat/Slack channel
- Use GitHub Issues for questions
- Document your progress in your role's README

### Data Handoffs
When you complete your work:
1. Save outputs to the specified `data/` folders
2. Update your README with completion status
3. Notify dependent roles
4. Document any issues or edge cases

### Git Workflow
```bash
# Create a branch for your role
git checkout -b r1-preprocessing  # or r2-text, r3-visual, etc.

# Make changes and commit
git add .
git commit -m "R1: Implement data cleaning pipeline"

# Push your branch
git push origin r1-preprocessing

# Create Pull Request for review
```

## Troubleshooting

### Virtual Environment Issues
```bash
# If venv creation fails on Ubuntu/Debian
sudo apt update
sudo apt install python3-venv

# Recreate virtual environment
rm -rf .venv
python3 -m venv .venv
```

### Package Installation Issues
```bash
# Use --no-cache-dir if running out of space
pip install --no-cache-dir package_name

# Upgrade pip first
pip install --upgrade pip
```

### CUDA/GPU Issues (R3, R4, R5)
```bash
# Check if CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# If False, models will use CPU (slower but works)
```

## Timeline Overview

| Day | R1 | R2 | R3 | R4 | R5 |
|-----|----|----|----|----|-----|
| 1-2 | Data cleaning | Setup | Setup + Block detection | Setup | Setup |
| 3-4 | DONE ✓ | Pattern extraction | Encoding pipeline | Feature alignment | Baseline models |
| 5-6 | - | NLP extraction | Batch processing | Fusion methods | Multimodal models |
| 7-8 | - | DONE ✓ | DONE ✓ | DONE ✓ | Ensemble + tuning |
| 9-10 | - | - | - | - | Final submission |

## Current Status (2026-09-25)

- [x] Repository structure created
- [x] README files for all roles
- [x] R3 environment setup in progress
- [ ] Dataset downloaded and placed in `data/raw/`
- [ ] R1 started
- [ ] R2 started
- [ ] R4 started
- [ ] R5 started

## Questions?

Refer to the README in your role's directory, or contact:
- Project Lead: TBD
- R1 Owner: TBD
- R2 Owner: TBD
- R3 Owner: Aarya
- R4 Owner: TBD
- R5 Owner: TBD
