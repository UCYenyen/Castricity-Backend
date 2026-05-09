# Technical Code Walkthrough: Castricity

This document provides a highly technical, deep-dive breakdown of the core components in the Castricity codebase: `build_real_datasets.py`, `hybrid_model.py`, and `dashboard.py`.

## 1. `build_real_datasets.py`: The Synthesized Organic Dataset

The data generation pipeline employs a "Synthesized Organic Dataset" strategy. This means that while the exogenous features (temperature, rainfall, holidays, macroeconomic indicators) are sourced from real-world data (BPS, BMKG, World Bank), the target variable (`Demand_MWh`) is mathematically synthesized from aggregate annual totals down to a daily resolution. This ensures the target maintains a physically realistic relationship with the features.

### Daily Weighting Mathematical Formula
To allocate the annual demand (`Smooth_Yearly_MWh`) into daily bins, the script calculates a `Daily_Weight` for each day based on calendar and weather events:

```python
Daily_Weight = 1.0 - 0.2 * Is_Weekend - 0.3 * Is_Holiday + 0.05 * (Avg_Temp - 27)
```

- **Base Weight:** Starts at `1.0`.
- **Weekend Penalty (-0.2):** Reduces demand on Saturdays and Sundays to reflect decreased industrial and commercial activity.
- **Holiday Penalty (-0.3):** Applies a steeper reduction for national holidays (e.g., Eid al-Fitr, Independence Day).
- **Temperature Premium (+0.05):** For every degree above the baseline of 27°C, the weight increases by 0.05. This models the cooling demand (increased AC usage) due to hotter weather.

The continuous base demand is then calculated proportionally:
```python
base_demand_continuous = (Smooth_Yearly_MWh / 365.25) * (Daily_Weight / avg_daily_weight)
```

### Gaussian Stochastic Noise Injection
If the target were generated using only the deterministic formula above, the machine learning models would suffer from **target leakage**—they would essentially reverse-engineer the formula perfectly, resulting in 0% error but failing to learn generalizable patterns. To prevent this, two layers of Gaussian stochastic noise are injected:

1. **Multiplicative Noise:** `np.random.normal(0, 0.0005)` introduces a 0.05% relative variance per day, scaling with the magnitude of the demand.
2. **Additive Noise:** `np.random.normal(0, base_demand_mean * 0.0005)` introduces a flat variance representing measurement uncertainty across the grid.

These noise layers act as a light regularization mechanism, forcing the model to learn the underlying patterns rather than memorizing the exact formula.

---

## 2. `hybrid_model.py`: Hybrid Trinity & Zero Data Leakage

The modeling script orchestrates the core predictive engine, utilizing a combination of Prophet (for temporal baselines), LightGBM (for exogenous residuals), and Isolation Forest (for anomaly detection).

### Strict "Fit-Only-On-Train" Protocol (KNNImputer)
To ensure **Zero Data Leakage**—a critical requirement for time-series validation—the data is split into Train (70%), Validation (15%), and Test (15%) sequentially *before* any imputation occurs. 

When handling missing weather data using `KNNImputer`:
```python
imputer.fit(train_df[features_to_impute]) # Fit ONLY on training data
train_df[...] = imputer.transform(train_df[...])
val_df[...] = imputer.transform(val_df[...])
test_df[...] = imputer.transform(test_df[...])
```
The imputer learns the spatial/temporal distribution strictly from the training set. Applying `transform` without re-fitting on validation/test sets guarantees that no future information bleeds into the past, preserving statistical validity.

### IsolationForest Anomaly Imputation (7-Day Lookback)
Instead of dropping anomalous rows (which creates holes in the time series and breaks autoregressive features like `Lag_7` or `Rolling_14`), the script uses an `IsolationForest` combined with an IQR statistical check to detect anomalies. 

When an anomaly is flagged, it is imputed using the mean of the **7 previous clean days**:
```python
lookback_start = max(0, idx - 7)
lookback_mask = ~is_anomaly[lookback_start:idx]
clean_window = train_df[target_col].iloc[lookback_start:idx][lookback_mask]
```
This 7-day lookback is deliberate: it perfectly captures exactly one full weekly operational cycle, maintaining the physical continuity of the grid data.

### Joint Bayesian Optimization (Optuna)
Because Prophet and LightGBM operate in a decoupled ensemble where LightGBM predicts the *residuals* of Prophet, optimizing them separately is suboptimal. A change in Prophet's flexibility (`changepoint_prior_scale`) fundamentally alters the distribution of the residuals that LightGBM must learn.

The script uses `Optuna` with a `TPESampler` to perform a **Joint Bayesian Optimization** across both models simultaneously. In a single objective function, it searches the hyperparameter space for Prophet (e.g., seasonality prior scale), LightGBM (e.g., learning rate, max depth, L1/L2 regularization), and Isolation Forest (contamination rate) to minimize the MAE on the validation set.

---

## 3. `dashboard.py`: Streamlit Architecture & Explainable AI

The dashboard provides the interactive interface for the system, strictly operating fully offline via localhost.

### Memory Management via `@st.cache_resource`
Machine learning models (especially ensemble trees) carry a significant memory footprint and high I/O latency when loaded from disk. Streamlit reruns the entire script from top to bottom on every user interaction. To prevent the `.joblib` models from reloading on every click, the dashboard utilizes the `@st.cache_resource` decorator:

```python
@st.cache_resource
def load_models(_prophet_mtime, _lgbm_mtime, _iso_mtime):
    # Loads models into global memory cache
```
By passing the file modification times (`mtime`) as arguments, Streamlit knows to keep the models cached in RAM indefinitely, only re-reading from disk if the underlying `.joblib` files are retrained and updated.

### Local XAI Narrations via SHAP TreeExplainer
To fulfill the "Explainable Oracle" requirement, the dashboard features a Local XAI engine that runs at inference time. When the user inputs parameters:
1. A single-row DataFrame is constructed.
2. `shap.TreeExplainer` calculates the exact Shapley values for that specific prediction against the LightGBM model.
3. The script sorts the features by absolute impact:
```python
feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
top_3_impacts = feature_impacts[:3]
```
4. Finally, it translates the mathematical SHAP values into a **natural language narration**. Positive SHAP values are mapped to "Meningkatkan Prediksi (Positif 📈)" and negative values to "Menurunkan Prediksi (Negatif 📉)", outputting human-readable sentences that explain *exactly* why the model made its decision in MWh units.
