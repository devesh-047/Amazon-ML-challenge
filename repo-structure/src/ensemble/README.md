# R5: Model Training & Ensemble

## Owner
TBD

## Responsibilities
- Train machine learning models on multimodal features
- Implement ensemble methods for robust predictions
- Hyperparameter tuning and cross-validation
- Generate final predictions on test set
- Create submission files in required format

## Setup

```bash
cd src/ensemble
python3 -m venv .venv
source .venv/bin/activate
pip install torch pandas numpy scikit-learn xgboost lightgbm catboost optuna matplotlib seaborn
```

## Input Data
- `../../data/features/text_features_train.csv` (from R2)
- `../../data/embeddings/block_embeddings_train.pkl` (from R3)
- `../../data/features/multimodal_features_train.pkl` (from R4)
- `../../data/processed/train_clean.csv`, `test_clean.csv` (from R1)

## Expected Outputs

### 1. Trained Models
- `../../data/models/model_text_only.pkl`
- `../../data/models/model_visual_only.pkl`
- `../../data/models/model_multimodal.pkl`
- `../../data/models/model_ensemble.pkl`

### 2. Predictions
- `../../data/submissions/submission.csv`
```csv
index,prediction
60001,0.45
60002,1200
60003,5.5
```

### 3. Model Reports
- `../../docs/model_performance_report.md`
  - Cross-validation scores
  - Feature importance
  - Model comparison
  - Hyperparameters used

### 4. Training Logs
- `../../runs/experiment_{timestamp}/`
  - Training curves
  - Validation metrics
  - Configuration files

## Key Tasks

### Task 1: Feature Engineering
```python
def prepare_features(text_feat, visual_feat, multimodal_feat):
    """Combine all available features."""
    features = []
    
    # Text-based features from R2
    features.append(text_feat['extracted_value'])
    features.append(text_feat['confidence_score'])
    
    # Visual features from R3 (dimensionality reduction)
    visual_reduced = pca.transform(visual_feat)
    features.extend(visual_reduced)
    
    # Multimodal features from R4
    features.extend(multimodal_feat['fused_embedding'])
    features.append(multimodal_feat['text_visual_similarity'])
    
    return np.array(features)
```

### Task 2: Model Selection
Try multiple model types:

1. **Regression Models** (for numeric entities):
   - Linear Regression
   - Random Forest Regressor
   - XGBoost Regressor
   - LightGBM Regressor

2. **Classification Models** (for categorical entities):
   - Logistic Regression
   - Random Forest Classifier
   - XGBoost Classifier

3. **Neural Networks**:
   - Simple MLP
   - More complex architectures if time permits

```python
models = {
    'rf': RandomForestRegressor(n_estimators=100),
    'xgb': XGBRegressor(n_estimators=100, learning_rate=0.1),
    'lgb': LGBMRegressor(n_estimators=100),
    'nn': MLPRegressor(hidden_layers=(256, 128, 64))
}
```

### Task 3: Entity-Specific Models
Different entity types may need different approaches:
- Numeric (weight, volume): Regression
- Categorical (color, size): Classification
- Consider training separate models per entity_name

```python
entity_models = {}
for entity_name in unique_entities:
    entity_data = data[data['entity_name'] == entity_name]
    model = train_model(entity_data)
    entity_models[entity_name] = model
```

### Task 4: Ensemble Strategy
```python
class EnsemblePredictor:
    def __init__(self, models, weights=None):
        self.models = models
        self.weights = weights or [1/len(models)] * len(models)
    
    def predict(self, X):
        predictions = []
        for model, weight in zip(self.models, self.weights):
            pred = model.predict(X)
            predictions.append(pred * weight)
        
        return np.sum(predictions, axis=0)
```

Methods to try:
1. **Simple Average:** Equal weights
2. **Weighted Average:** Based on validation performance
3. **Stacking:** Train meta-model on base predictions
4. **Voting:** For classification tasks

### Task 5: Hyperparameter Tuning
```python
import optuna

def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
    }
    
    model = XGBRegressor(**params)
    score = cross_val_score(model, X_train, y_train, cv=5)
    return score.mean()

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50)
```

### Task 6: Cross-Validation
```python
from sklearn.model_selection import KFold

kf = KFold(n_splits=5, shuffle=True, random_state=42)
scores = []

for train_idx, val_idx in kf.split(X):
    X_tr, X_val = X[train_idx], X[val_idx]
    y_tr, y_val = y[train_idx], y[val_idx]
    
    model.fit(X_tr, y_tr)
    score = model.score(X_val, y_val)
    scores.append(score)

print(f"CV Score: {np.mean(scores):.4f} ± {np.std(scores):.4f}")
```

## Evaluation Metric
Based on the challenge (check competition rules):
- Likely F1-score or Accuracy for classification
- MAE/MSE/R² for regression
- Custom metric if specified

## Module Structure

```
src/ensemble/
├── features.py           # Feature preparation
├── models.py             # Model definitions
├── train.py              # Training pipeline
├── ensemble.py           # Ensemble methods
├── evaluate.py           # Evaluation metrics
└── predict.py            # Generate predictions
```

## Training Pipeline

```python
# 1. Load all features
text_feat = load_text_features()
visual_feat = load_visual_features()
multimodal_feat = load_multimodal_features()

# 2. Prepare training data
X, y = prepare_features_and_labels(text_feat, visual_feat, multimodal_feat)

# 3. Train multiple models
models = {}
for name, model_class in model_configs.items():
    model = train_with_cv(model_class, X, y)
    models[name] = model

# 4. Create ensemble
ensemble = create_ensemble(models)

# 5. Evaluate
val_score = evaluate(ensemble, X_val, y_val)

# 6. Generate test predictions
test_predictions = ensemble.predict(X_test)

# 7. Save submission
save_submission(test_predictions, 'submission.csv')
```

## Baseline Approach
Start simple, then iterate:
1. **Day 1-2:** Text-only model (R2 features)
2. **Day 3:** Add visual features (R3 embeddings)
3. **Day 4:** Use multimodal features (R4 fusion)
4. **Day 5:** Ensemble multiple models
5. **Day 6:** Hyperparameter tuning
6. **Day 7:** Final submission

## Dependencies
- **Depends on:** R1 (clean data), R2 (text features), R3 (visual features), R4 (multimodal features)
- **Provides to:** Final submission

## Performance Goals
- Beat text-only baseline by 15%+
- Achieve top 20% in competition leaderboard
- Generate reliable confidence scores

## Checklist
- [ ] Setup environment
- [ ] Load all feature sets (R2, R3, R4)
- [ ] Implement feature engineering pipeline
- [ ] Train baseline models (text-only, visual-only)
- [ ] Train multimodal models
- [ ] Implement ensemble strategy
- [ ] Cross-validation
- [ ] Hyperparameter tuning
- [ ] Generate test predictions
- [ ] Create submission file
- [ ] Validate submission format
- [ ] Document model architecture
- [ ] Submit to competition

## Timeline
- Setup & Data Loading: Day 1
- Baseline Models: Day 2-3
- Multimodal Models: Day 4
- Ensemble & Tuning: Day 5-6
- Final Testing: Day 6-7
- Submission: Day 7

## Submission Format
Check competition requirements:
```csv
index,prediction
60001,value1
60002,value2
...
```

## Contact
Owner: TBD
