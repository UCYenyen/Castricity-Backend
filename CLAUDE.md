# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Castricity** is an electricity demand forecasting system for Indonesian national grid using a **Hybrid AI Architecture** that combines three specialized models to capture different aspects of energy consumption complexity:

1. **Prophet** (Meta) — time-series patterns, seasonality, and long-term trends
2. **LightGBM** (Microsoft) — learns residuals by correlating with exogenous features (weather, macro factors)
3. **Isolation Forest** — detects and replaces grid anomalies/corrupted spikes

The entire pipeline is jointly tuned using **Optuna Bayesian Optimization**.

## Quick Start Commands

### Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r Notebook/requirements.txt
pip install streamlit plotly holidays
```

### Training & Optimization
```bash
# Train the hybrid model (Prophet + LightGBM + Isolation Forest)
# Runs 30 Optuna trials, tunes all three models jointly
python Scripts/hybrid_model.py

# Set number of tuning trials via environment variable
OPTUNA_TRIALS=50 python Scripts/hybrid_model.py
```

### Data Preparation
```bash
# Build training/validation/test datasets from raw data sources
python Scripts/build_real_datasets.py

# Integrate BMKG (Indonesian weather) data
python Scripts/integrate_bmkg.py
```

### Dashboard & Visualization
```bash
# Launch the interactive Streamlit dashboard (requires trained models)
# Features: historical validation, anomaly marking, SHAP explanations, what-if forecasting
streamlit run dashboard.py
```

### Jupyter Notebooks
- `Notebook/training.ipynb` — exploration-oriented training pipeline
- `Notebook/inference.ipynb` — inference and prediction examples

## Architecture: The Three-Component Hybrid

### 1. Prophet Baseline (Long-term + Seasonality)
- Captures calendar patterns, holidays (Lunar/Hijriah shifts), and long-term trends
- Input: `Demand_MWh`, `Date`, holiday calendar
- Output: baseline forecast + trend/seasonal decomposition

### 2. LightGBM Residual Learner (Exogenous Correlation)
- Trained on Prophet's forecast errors (residuals)
- Learns how weather (`Avg_Temp`, `Rainfall`) and macro factors correlate with deviations
- Input: 18 engineered features (lags, rolling windows, temporal features, exogenous variables)
- Output: residual adjustment to Prophet's forecast

### 3. Isolation Forest Guardrail (Anomaly Detection)
- Detects corrupted/anomalous spikes in raw time series
- Replaces detected anomalies via 7-day rolling mean imputation
- Runs as preprocessing step before Prophet training
- Contamination level is jointly tuned with other hyperparameters

### Joint Optimization
- **Optuna** simultaneously tunes:
  - Prophet: `seasonality_mode`, `changepoint_prior_scale`, `seasonality_prior_scale`
  - LightGBM: learning rate, depth, λ_l1, λ_l2, λ_ort
  - Isolation Forest: contamination level
- Metric: minimizes validation RMSE on the final hybrid ensemble

## Key Modules & Data Flow

### Data Pipeline
```
Raw Data/
  ├── BPS_Electricity/         (yearly PLN distribution by province)
  ├── World_Bank_Macro/        (GDP, population, industrial output)
  ├── BMKG_Weather/            (temperature, rainfall)
  └── PLN_Daily_Demand.csv     (actual daily load in MWh)
      ↓
Scripts/build_real_datasets.py
      ↓
train_data/dataset_daily_train.csv
test_data/dataset_daily_val.csv
test_data/dataset_daily_test.csv
```

### Training & Model Export
```
Scripts/hybrid_model.py
  ├─ Loads train/val/test CSVs
  ├─ KNN Imputation (fit on train, apply to all)
  ├─ Feature engineering (lags, rolling windows, temporal, exogenous)
  ├─ Isolation Forest preprocessing (anomaly replacement)
  ├─ Optuna optimization (30 trials by default)
  ├─ Train final Prophet + LightGBM on best hyperparams
  └─ Export:
      Models/
        ├── prophet_model.joblib
        ├── lgbm_model.joblib
        ├── iso_forest.joblib
        ├── knn_imputer.joblib
        └── best_hybrid_params.json
      Outputs/
        ├── dataset_daily_with_predictions.csv
        ├── fig_*.png (visualizations)
        └── shap_*.png (SHAP explanations)
```

### Dashboard & Inference
```
dashboard.py
  ├─ Loads trained models from Models/
  ├─ Loads processed data + predictions from Outputs/
  ├─ Streamlit UI with 3 main tabs:
  │   ├─ Historical Validation (actual vs. predicted)
  │   ├─ Anomaly Explorer (grid spikes flagged by Isolation Forest)
  │   └─ What-If Forecaster (future scenarios with SHAP breakdowns)
  └─ Local SHAP explanations for each prediction
```

## Core Files & Responsibilities

| File | Purpose |
|------|---------|
| `Scripts/hybrid_model.py` | **Heartbeat of the project.** Loads data, engineers features, runs Optuna optimization, trains final ensemble, exports models and visualizations. ~1000 lines. |
| `Scripts/build_real_datasets.py` | **Data aggregation.** Parses raw CSVs (BPS yearly, World Bank macro, BMKG weather, PLN daily), normalizes units, aligns dates, splits into train/val/test. |
| `Scripts/integrate_bmkg.py` | **Weather integration.** Fetches or processes BMKG (Badan Meteorologi, Klimatologi, dan Geofisika) weather data. |
| `dashboard.py` | **User interface.** Streamlit app displaying predictions, anomalies, and SHAP local explanations. Caches model loads for performance. |
| `Notebook/training.ipynb` | **Exploratory training** with inline visualization and debugging. |
| `Notebook/inference.ipynb` | **Inference examples** — how to load models and make predictions. |

## Explainable AI (XAI)

The project uses **SHAP (SHapley Additive exPlanations)** to explain predictions:

- **Global Impact**: Feature importance across all predictions (which features drive overall model behavior)
- **Local Explanation**: For every single forecast, SHAP breaks down *why* that specific MWh value was predicted
- Visualizations exported to `Outputs/fig*_shap_*.png` and displayed in the dashboard

## Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPTUNA_TRIALS` | `50` | Number of Bayesian optimization trials |
| `RETUNE_EVERY_DAYS` | `30` | (Reserved) days before automatic retuning |
| `FORCE_RETUNE` | `True` | Force re-optimization even if params exist |

Set via: `OPTUNA_TRIALS=100 python Scripts/hybrid_model.py`

## Working with Models & Artifacts

### Loading Pre-Trained Models
```python
import joblib

prophet_model = joblib.load('Models/prophet_model.joblib')
lgbm_model = joblib.load('Models/lgbm_model.joblib')
iso_forest = joblib.load('Models/iso_forest.joblib')
knn_imputer = joblib.load('Models/knn_imputer.joblib')
best_params = json.load(open('Models/best_hybrid_params.json'))
```

### Making Predictions
See `Notebook/inference.ipynb` for end-to-end example.

### Retraining
1. Update raw data in `Raw Data/` folders
2. Run `python Scripts/build_real_datasets.py` to regenerate train/val/test CSVs
3. Run `python Scripts/hybrid_model.py` to retrain (will re-optimize hyperparameters)

## Documentation References

- **[Hybrid Architecture](./Documentation/hybrid_model_architecture.md)** — high-level system design
- **[Full Technical Whitepaper](./Documentation/AI_Project_Documentation.md)** — algorithmic logic (Bahasa Indonesia)
- **[Comprehensive Tech Spec](./Documentation/full_technical_documentation.md)** — implementation details
- **[Data Dictionary](./Documentation/dataset_documentation.md)** — feature definitions and interactions

## Development Notes

### Path Resolution
All scripts use `os.path.dirname(os.path.abspath(__file__))` to locate project root, making them runnable from any working directory.

### Data Splits
- **Train**: fitted to for imputation, feature scaling, model training
- **Validation**: Optuna objective metric (RMSE on validation set)
- **Test**: held-out evaluation (if available; check `test_data/dataset_daily_test.csv`)

### Feature Engineering
Key features in LightGBM input:
- Temporal: `Month`, `DayOfYear`, `WeekOfYear`, `Trend`
- Autoregressive: `Lag_1`, `Lag_2`, `Lag_7`, `Lag_14`, `Lag_30`
- Rolling: `Rolling_7`, `Rolling_14`, `Rolling_30`
- Exogenous: `Avg_Temp`, `Rainfall`, `Temp_Lag_1`
- Categorical: `Day_of_Week`, `Is_Weekend`, `Is_Holiday`

See `Scripts/hybrid_model.py` lines 79-100 for full feature list.

### Model Serialization
- **Prophet**: `joblib` (binary pickle)
- **LightGBM**: `joblib` (binary pickle)
- **Isolation Forest**: `joblib` (binary pickle)
- **KNN Imputer**: `joblib` (for feature preprocessing on new data)
- **Hyperparameters**: `best_hybrid_params.json` (JSON for inspection)

### Anomaly Imputation Strategy
Isolation Forest detects spikes; detected anomalies are replaced with 7-day rolling mean. This runs *before* Prophet training to ensure clean baseline signals.

---

**Key Principle**: Transparent, explainable forecasting. Every prediction is decomposable into feature-level contributions via SHAP.
