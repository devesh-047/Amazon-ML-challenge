# R2: Text-Based Feature Extraction

## Owner
TBD

## Responsibilities
- Extract entity values from product titles and descriptions
- Implement regex patterns for structured data extraction
- Use NLP techniques (NER, pattern matching)
- Handle unit conversions and standardization
- Generate text-based confidence scores

## Setup

```bash
cd src/text_extraction
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy regex spacy transformers
python -m spacy download en_core_web_sm
```

## Input Data
- `../../data/processed/train_clean.csv` (from R1)
- `../../data/processed/val_clean.csv` (from R1)

## Expected Outputs

### 1. Text Features
- `../../data/features/text_features_train.csv`
- `../../data/features/text_features_val.csv`

Format:
```csv
index,extracted_value,confidence_score,extraction_method,normalized_value,unit
123,500,0.95,regex,500,gram
124,1.5,0.87,ner,1.5,litre
```

### 2. Extraction Patterns
- `../../configs/extraction_patterns.json`
  - Regex patterns per entity type
  - Unit conversion rules
  - Common variations

### 3. Extraction Report
- `../../docs/text_extraction_report.md`
  - Success rate per entity type
  - Pattern coverage
  - Edge cases identified

## Key Tasks

### Task 1: Pattern-Based Extraction
- Create regex patterns for each entity_name:
  - `item_weight`: r'(\d+\.?\d*)\s*(kg|kilogram|gram|g|pound|lb)'
  - `item_volume`: r'(\d+\.?\d*)\s*(litre|liter|ml|millilitre|gallon)'
  - `voltage`: r'(\d+\.?\d*)\s*(volt|v|volts)'
  - etc.

### Task 2: NLP-Based Extraction
- Use spaCy for Named Entity Recognition
- Extract quantities and measurements
- Context-aware extraction

### Task 3: Unit Normalization
- Convert all weights to grams
- Convert all volumes to litres
- Standardize units per entity type
- Handle ranges (take average or midpoint)

### Task 4: Confidence Scoring
- Exact pattern match: 0.9-1.0
- Partial match: 0.5-0.9
- NER extraction: 0.6-0.8
- No match: 0.0

### Task 5: Entity-Specific Handlers
- Create specialized extractors for:
  - Numeric values (weight, volume, voltage)
  - Categorical values (color, size)
  - Dimensions (length x width x height)
  - Multi-value entities

## Sample Code Structure

```python
# src/text_extraction/extractor.py
class TextExtractor:
    def __init__(self):
        self.patterns = self.load_patterns()
        self.nlp = spacy.load('en_core_web_sm')
    
    def extract(self, text, entity_name):
        # Try regex first
        result = self.regex_extract(text, entity_name)
        if result['confidence'] < 0.5:
            # Fallback to NLP
            result = self.nlp_extract(text, entity_name)
        return result
    
    def normalize_unit(self, value, unit, target_unit):
        # Unit conversion logic
        pass
```

## Dependencies
- **Depends on:** R1 (needs clean data)
- **Provides to:** R4 (text features for matching), R5 (direct text features)

## Entity Types to Handle
Common entity types in Amazon product data:
- item_weight
- item_volume
- voltage
- wattage
- item_height
- item_width
- item_depth
- maximum_weight_recommendation
- etc.

## Checklist
- [ ] Setup environment
- [ ] Load cleaned data from R1
- [ ] Implement regex patterns for top 10 entity types
- [ ] Implement NLP extraction
- [ ] Create unit normalization module
- [ ] Generate confidence scores
- [ ] Test on validation set
- [ ] Save text features
- [ ] Document extraction patterns
- [ ] Notify R4 and R5 that features are ready

## Timeline
- Setup: Day 1
- Pattern Development: Day 2-3
- NLP Implementation: Day 3-4
- Testing & Optimization: Day 4-5
- Handoff: End of Day 5

## Performance Goals
- Extract values for 70%+ of training samples
- High-confidence (>0.8) for 50%+ of extractions
- Properly handle all major units

## Contact
Owner: TBD
