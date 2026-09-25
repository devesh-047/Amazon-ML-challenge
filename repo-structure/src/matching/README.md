# R4: Visual-Text Matching & Fusion

## Owner
TBD

## Responsibilities
- Match text features (from R2) with visual block embeddings (from R3)
- Implement cross-modal attention mechanisms
- Fuse multimodal information effectively
- Generate combined feature representations
- Provide confidence scores for matches

## Setup

```bash
cd src/matching
python3 -m venv .venv
source .venv/bin/activate
pip install torch transformers pandas numpy scikit-learn scipy
```

## Input Data
- `../../data/features/text_features_train.csv` (from R2)
- `../../data/embeddings/block_embeddings_train.pkl` (from R3)
- `../../data/processed/train_clean.csv` (from R1)

## Expected Outputs

### 1. Multimodal Features
- `../../data/features/multimodal_features_train.pkl`
```python
{
    'sample_123': {
        'fused_embedding': np.array([1024-dim]),
        'text_visual_similarity': 0.85,
        'best_block_idx': 1,
        'confidence': 0.92
    }
}
```

### 2. Match Scores
- `../../data/features/match_scores_train.csv`
```csv
index,text_conf,visual_conf,fusion_conf,selected_block
123,0.87,0.92,0.94,block_1
124,0.65,0.78,0.73,block_0
```

### 3. Matching Report
- `../../docs/matching_report.md`
  - Match success rates
  - Correlation analysis
  - Feature importance

## Key Tasks

### Task 1: Feature Alignment
```python
# Align text and visual embeddings to same space
class FeatureAligner:
    def __init__(self, text_dim=768, visual_dim=768):
        self.text_proj = nn.Linear(text_dim, 512)
        self.visual_proj = nn.Linear(visual_dim, 512)
    
    def align(self, text_feat, visual_feat):
        text_aligned = self.text_proj(text_feat)
        visual_aligned = self.visual_proj(visual_feat)
        return text_aligned, visual_aligned
```

### Task 2: Block Selection
For each sample with N visual blocks:
- Compute similarity between text and each block
- Select most relevant block(s)
- Aggregate information from multiple blocks if needed

```python
def select_best_block(text_features, block_embeddings):
    """Find most relevant visual block for text."""
    similarities = []
    for block_emb in block_embeddings:
        sim = cosine_similarity(text_features, block_emb)
        similarities.append(sim)
    
    best_idx = np.argmax(similarities)
    return best_idx, max(similarities)
```

### Task 3: Feature Fusion
Methods to try:
1. **Concatenation:** `[text_feat, visual_feat]`
2. **Weighted Average:** `α * text_feat + (1-α) * visual_feat`
3. **Attention-based:** Learn attention weights
4. **Gated Fusion:** Use learned gates to control information flow

```python
def fuse_features(text_feat, visual_feat, method='concat'):
    if method == 'concat':
        return np.concatenate([text_feat, visual_feat])
    elif method == 'weighted':
        alpha = compute_weight(text_feat, visual_feat)
        return alpha * text_feat + (1-alpha) * visual_feat
    elif method == 'attention':
        return attention_fusion(text_feat, visual_feat)
```

### Task 4: Confidence Scoring
```python
def compute_fusion_confidence(text_conf, visual_conf, similarity):
    """
    Combine confidences from different modalities.
    
    Args:
        text_conf: Confidence from R2 text extraction
        visual_conf: Confidence from R3 visual quality
        similarity: Text-visual similarity score
    
    Returns:
        Overall confidence score
    """
    return (text_conf * 0.4 + visual_conf * 0.3 + similarity * 0.3)
```

### Task 5: Handle Missing Modalities
- What if text extraction failed? (text_conf = 0)
  → Use pure visual features
- What if image is missing/corrupted?
  → Use pure text features
- Graceful degradation strategy

## Architecture Options

### Option 1: Simple Similarity-Based
```python
# Fast, interpretable
for sample in dataset:
    text_feat = get_text_features(sample)
    blocks = get_visual_blocks(sample)
    
    best_block_idx, similarity = select_best_block(text_feat, blocks)
    fused = concatenate(text_feat, blocks[best_block_idx])
```

### Option 2: Learned Fusion (Advanced)
```python
# Better performance, needs training
class FusionNetwork(nn.Module):
    def __init__(self):
        self.attention = MultiHeadAttention(...)
        self.fusion_layer = nn.Sequential(...)
    
    def forward(self, text_feat, visual_feats):
        # Cross-modal attention
        attended = self.attention(text_feat, visual_feats)
        fused = self.fusion_layer(attended)
        return fused
```

Start with Option 1, upgrade to Option 2 if time permits.

## Module Structure

```
src/matching/
├── align.py              # Feature alignment
├── selector.py           # Block selection logic
├── fusion.py             # Feature fusion methods
├── confidence.py         # Confidence scoring
└── pipeline.py           # Main matching pipeline
```

## Dependencies
- **Depends on:** R2 (text features), R3 (visual embeddings)
- **Provides to:** R5 (multimodal features for training)

## Performance Goals
- Process entire dataset in < 1 hour
- Improve prediction accuracy by 10-15% over text-only baseline
- Generate meaningful confidence scores

## Checklist
- [ ] Setup environment
- [ ] Load text features from R2
- [ ] Load visual embeddings from R3
- [ ] Implement feature alignment
- [ ] Implement block selection
- [ ] Implement fusion methods (try 2-3 variants)
- [ ] Generate confidence scores
- [ ] Handle missing modalities
- [ ] Evaluate on validation set
- [ ] Save multimodal features
- [ ] Document fusion approach
- [ ] Notify R5 that features are ready

## Timeline
- Setup: Day 1
- Feature Loading & Alignment: Day 2
- Block Selection: Day 2-3
- Fusion Implementation: Day 3-4
- Testing & Optimization: Day 4-5
- Handoff: End of Day 5

## Evaluation Metrics
- Text-visual correlation
- Match accuracy (manual inspection on sample)
- Downstream performance improvement (compared to text-only)

## Contact
Owner: TBD
