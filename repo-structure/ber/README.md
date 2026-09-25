# R3: Block-Level Visual Extraction & Encoding

## Owner
Aarya

## Responsibilities
- Detect and extract visual blocks from product images
- Generate embeddings using pre-trained vision models (CLIP, ViT)
- Create visual feature representations for each image block
- Handle various image layouts and quality levels
- Provide embeddings to R4 for visual-text matching

## Setup

```bash
cd ../../ber
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision transformers pillow pandas numpy scikit-learn tqdm opencv-python
```

**Status:** ✅ Environment setup in progress (packages installing)

## Input Data
- `../../data/processed/train_clean.csv` (from R1)
- `../../data/raw/images/` (product images)

## Expected Outputs

### 1. Image Blocks
- `../../data/interim/image_blocks/{image_id}/block_{n}.jpg`
  - Extracted visual blocks from each image
  - Multiple blocks per image (title area, product photo, specs, etc.)

### 2. Block Embeddings
- `../../data/embeddings/block_embeddings_train.pkl`
```python
{
    'image_123': {
        'block_0': np.array([768-dim embedding]),
        'block_1': np.array([768-dim embedding]),
        'block_2': np.array([768-dim embedding])
    },
    ...
}
```

### 3. Block Metadata
- `../../data/interim/block_metadata.json`
```json
{
    "image_123": {
        "num_blocks": 3,
        "block_types": ["title", "product", "specs"],
        "block_coords": [[x1,y1,x2,y2], ...]
    }
}
```

### 4. Extraction Report
- `../../docs/block_extraction_report.md`
  - Number of blocks per image (statistics)
  - Failed extractions
  - Embedding model details

## Key Tasks

### Task 1: Block Detection
Two approaches:
1. **Simple Grid-Based:**
   - Divide image into N x M grid
   - Extract fixed-size blocks
   - Fast but less intelligent

2. **Smart Detection:**
   - Use edge detection / segmentation
   - Identify text regions, product regions
   - More accurate but slower

Start with approach 1, upgrade to 2 if needed.

### Task 2: Visual Encoding
```python
from transformers import CLIPProcessor, CLIPModel

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# For each block:
inputs = processor(images=block_image, return_tensors="pt")
embeddings = model.get_image_features(**inputs)
```

### Task 3: Batch Processing Pipeline
```python
for image_path in tqdm(image_paths):
    # 1. Load image
    img = load_image(image_path)
    
    # 2. Detect blocks
    blocks = detect_blocks(img)
    
    # 3. Generate embeddings
    embeddings = encode_blocks(blocks)
    
    # 4. Save
    save_blocks(blocks, embeddings, metadata)
```

### Task 4: Quality Control
- Skip corrupted images
- Handle various image sizes
- Ensure embeddings are normalized
- Save processing logs

## Module Structure

```
ber/
├── src/
│   ├── common/
│   │   ├── config.py          # Configuration settings
│   │   └── utils.py           # Utility functions
│   ├── block/
│   │   ├── detector.py        # Block detection logic
│   │   └── extractor.py       # Block extraction
│   ├── model/
│   │   ├── encoder.py         # Vision encoder (CLIP/ViT)
│   │   └── embedder.py        # Embedding generation
│   └── pipeline/
│       └── process.py         # Main processing pipeline
├── data/
│   ├── interim/               # Intermediate results
│   └── out/                   # Final outputs
└── runs/                      # Experiment logs
```

## Sample Code

### Block Detector (Simple Grid)
```python
def detect_blocks_grid(image, grid_size=(3, 3)):
    """Divide image into grid blocks."""
    h, w = image.shape[:2]
    block_h, block_w = h // grid_size[0], w // grid_size[1]
    
    blocks = []
    for i in range(grid_size[0]):
        for j in range(grid_size[1]):
            y1, y2 = i * block_h, (i + 1) * block_h
            x1, x2 = j * block_w, (j + 1) * block_w
            block = image[y1:y2, x1:x2]
            blocks.append({
                'image': block,
                'coords': [x1, y1, x2, y2],
                'block_id': f'block_{i}_{j}'
            })
    return blocks
```

### Embedding Generator
```python
class BlockEmbedder:
    def __init__(self, model_name='openai/clip-vit-base-patch32'):
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()
    
    def encode(self, image):
        """Generate embedding for an image block."""
        inputs = self.processor(images=image, return_tensors="pt")
        with torch.no_grad():
            features = self.model.get_image_features(**inputs)
        return features.cpu().numpy().flatten()
```

## Dependencies
- **Depends on:** R1 (needs cleaned data with valid image links)
- **Provides to:** R4 (block embeddings for matching), R5 (visual features)

## Performance Considerations
- Use GPU if available: `torch.cuda.is_available()`
- Batch processing for efficiency
- Consider image resizing for faster processing
- Estimated time: ~2-5 seconds per image

## Checklist
- [x] Setup environment (in progress)
- [ ] Load cleaned data from R1
- [ ] Implement block detection (grid-based)
- [ ] Setup CLIP/ViT encoder
- [ ] Create batch processing pipeline
- [ ] Generate embeddings for train set
- [ ] Save blocks and embeddings
- [ ] Generate metadata
- [ ] Test on sample images
- [ ] Document block format
- [ ] Notify R4 that embeddings are ready

## Timeline
- Setup: Day 1 (TODAY - in progress)
- Block Detection Implementation: Day 2
- Encoder Integration: Day 2-3
- Pipeline & Batch Processing: Day 3-4
- Testing & Optimization: Day 4-5
- Handoff: End of Day 5

## Current Status
- ✅ Directory structure created
- ✅ Virtual environment created
- ⏳ Package installation in progress (90% complete)
- ⏳ Waiting for R1 to provide cleaned data

## Contact
Owner: Aarya
