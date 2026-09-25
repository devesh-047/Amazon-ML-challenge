# Amazon ML Challenge - Pipeline Makefile
# Each target corresponds to one pipeline stage
# Usage: make <target>

.PHONY: help clean split normalize mine_maps block features train predict decide submit validate

# Python interpreter from venv
PYTHON := .venv/bin/python3

# Config file
CONFIG := conf/default.yaml

# Dataset paths (override with DATASET_ROOT=/path/to/dataset)
DATASET_ROOT := ../../6ab10eb3b23ba_student_resource/student_resource/dataset
TRAIN_DIR := $(DATASET_ROOT)/train
TEST_DIR := $(DATASET_ROOT)/test

help:
	@echo "Amazon ML Challenge Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  split       - Create validation split (R3)"
	@echo "  normalize   - Normalize train/test data (R1)"
	@echo "  mine_maps   - Mine transliteration/abbrev maps from GT (R1)"
	@echo "  block       - Generate candidate pairs (R1)"
	@echo "  features    - Extract features from candidates (R2)"
	@echo "  train       - Train LightGBM model with calibration (R2)"
	@echo "  predict     - Score all candidates (R2)"
	@echo "  decide      - Apply decision layer (exclusivity + selection) (R3)"
	@echo "  submit      - Emit final TSV files (R3)"
	@echo "  validate    - Run validation scoring (R3)"
	@echo "  clean       - Remove interim files"
	@echo ""
	@echo "Full pipeline: make split normalize mine_maps block features train predict decide submit"

# R3: Create validation split
split:
	@echo "==> Creating validation split..."
	$(PYTHON) src/eval/make_val_split.py \
		--source1 $(TRAIN_DIR)/train_source1.tsv \
		--truth $(TRAIN_DIR)/train_ground_truth.tsv \
		--outdir data/splits

# R1: Normalize all source files
normalize:
	@echo "==> Normalizing train/test data..."
	$(PYTHON) src/common/normalize.py \
		--config $(CONFIG) \
		--train-dir $(TRAIN_DIR) \
		--test-dir $(TEST_DIR) \
		--outdir data/interim/normalized

# R1: Mine transliteration/abbreviation maps from ground truth
mine_maps:
	@echo "==> Mining transliteration/abbreviation maps..."
	$(PYTHON) src/block/mine_maps.py \
		--config $(CONFIG) \
		--normalized data/interim/normalized \
		--truth $(TRAIN_DIR)/train_ground_truth.tsv \
		--outdir data/interim/maps

# R1: Generate candidate pairs (blocking)
block:
	@echo "==> Generating candidate pairs..."
	$(PYTHON) src/block/generate.py \
		--config $(CONFIG) \
		--normalized data/interim/normalized \
		--maps data/interim/maps \
		--splits data/splits \
		--outdir data/interim/candidates

# R2: Extract features from candidate pairs
features:
	@echo "==> Extracting features..."
	$(PYTHON) src/model/features.py \
		--config $(CONFIG) \
		--candidates data/interim/candidates \
		--normalized data/interim/normalized \
		--outdir data/interim/features

# R2: Train model (LightGBM + calibration)
train:
	@echo "==> Training model..."
	$(PYTHON) src/model/train.py \
		--config $(CONFIG) \
		--features data/interim/features \
		--truth $(TRAIN_DIR)/train_ground_truth.tsv \
		--splits data/splits \
		--outdir data/interim/models

# R2: Generate predictions (scores)
predict:
	@echo "==> Scoring candidates..."
	$(PYTHON) src/model/predict.py \
		--config $(CONFIG) \
		--features data/interim/features \
		--model data/interim/models \
		--outdir data/interim/scored

# R3: Apply decision layer (exclusivity + expected-F0.5 selection)
decide:
	@echo "==> Applying decision layer..."
	$(PYTHON) src/decide/select.py \
		--config $(CONFIG) \
		--scored data/interim/scored \
		--outdir data/interim/decisions

# R3: Emit final submission files
submit:
	@echo "==> Emitting submission files..."
	$(PYTHON) src/decide/emit.py \
		--config $(CONFIG) \
		--decisions data/interim/decisions \
		--outdir data/out \
		--run-id $(shell date +%Y%m%d_%H%M%S)

# R3: Validate submission and compute scores
validate:
	@echo "==> Validating submission..."
	$(PYTHON) src/eval/f05_score.py \
		--config $(CONFIG) \
		--predictions data/out/latest \
		--truth $(TRAIN_DIR)/train_ground_truth.tsv \
		--splits data/splits

# Clean interim files
clean:
	@echo "==> Cleaning interim files..."
	rm -rf data/interim/*
	@echo "Done. Splits and output preserved."

# Clean everything (use with caution)
clean-all: clean
	@echo "==> Cleaning splits and outputs..."
	rm -rf data/splits/* data/out/*
	@echo "Done. All data cleaned."
