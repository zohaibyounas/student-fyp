Islamic Dream Training Dataset
==============================

Place your training CSV here (the file used to train models/*.pkl).

Best location (recommended):
  fyp_fixed/data/Dataset.csv
  or fyp_fixed/data/dataset.csv

Also searched automatically:
  - data/*.csv (any name)
  - __pycache__/data/dataset.csv (if you added it there)

Or set environment variable:
  DREAM_DATASET_PATH=C:\path\to\your_dataset.csv

Required columns (your file format is supported):
  - Dream          (dream text)
  - meaning        (interpretation shown to user)
  - islamic_analysis  (rahmani / shaitani / nafsani)
  - sentiment_analysis (positive / negative / neutral)

Dream Analyzer and Pattern Correlation both use /analyze-dream,
which matches your dream to the closest row in this CSV first.

On server start you should see:
  Dream dataset loaded: 2636 dreams from ...\data\Dataset.csv

Without CSV, the app falls back to ML models and keyword rules.
