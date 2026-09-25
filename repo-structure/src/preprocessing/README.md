# R1: Data Preprocessing & Augmentation

## Owner
TBD

## Responsibilities
- Load and validate train.csv and test.csv
- Clean data (handle missing values, duplicates, anomalies)
- Normalize entity values and units
- Create train/validation splits
- Data augmentation if needed
- Generate data quality report

## Setup

```bash
cd src/preprocessing
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy scikit-learn matplotlib seaborn
```

## Input Data
- `../../data/raw/train.csv`
- `../../data/raw/test.csv`

## Expected Outputs

### 1. Cleaned Datasets
- `../../data/processed/train_clean.csv`
- `../../data/processed/val_clean.csv`
- `../../data/processed/test_clean.csv`

### 2. Data Quality Report
- `../../docs/data_quality_report.md`
  - Missing value statistics
  - Entity type distribution
  - Image availability stats
  - Outlier detection results

### 3. Metadata
- `../../data/processed/metadata.json`
  - Dataset statistics
  - Entity categories
  - Split information

## Key Tasks

### Task 1: Data Loading & Validation
```python
# Load train.csv
# Check schema: index, image_link, group_id, entity_name, entity_value
# Validate data types
# Report statistics
```

### Task 2: Data Cleaning
- Handle missing entity_values
- Check for duplicate entries
- Validate image links
- Normalize text fields

### Task 3: Entity Value Normalization
- Standardize units (e.g., "1 kg" → 1.0, "kilogram")
- Handle ranges (e.g., "10-15 cm" → 12.5, "centimetre")
- Clean formatting

### Task 4: Train/Val Split
- Create stratified split by entity_name
- Maintain group_id integrity (all items from same group in same split)
- Typical split: 80/20 or 90/10

### Task 5: Data Augmentation (Optional)
- Text paraphrasing
- Synonym replacement
- Back-translation

## Dependencies for Other Roles
- **R2 (Text Extraction):** Needs `train_clean.csv` with clean text
- **R3 (Visual Extraction):** Needs `train_clean.csv` with valid image links

## Sample Output Format

`train_clean.csv`:
```
index,image_link,group_id,entity_name,entity_value
123,images/123.jpg,456,item_weight,500 gram
124,images/124.jpg,457,item_volume,1.5 litre
```

## Checklist
- [ ] Load raw data
- [ ] Generate data quality report
- [ ] Clean and validate data
- [ ] Normalize entity values
- [ ] Create train/val split
- [ ] Save processed datasets
- [ ] Document data format
- [ ] Notify R2 and R3 that data is ready

## Timeline
- Setup: Day 1
- Implementation: Day 1-2
- Testing & Validation: Day 2
- Handoff: End of Day 2

## Contact
Owner: TBD
