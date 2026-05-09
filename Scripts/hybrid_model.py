import os # Import the os module for operating system dependent functionality like reading paths and environment variables
import json # Import json for reading and writing configuration files containing hyperparameters
import pandas as pd # Import pandas for data manipulation and analysis, handling the core DataFrame structures
import numpy as np # Import numpy for numerical operations and array manipulations
import matplotlib # Import matplotlib for configuring plotting backends
import optuna # Import optuna for Bayesian hyperparameter optimization
import logging # Import logging to control the output of warnings and logs
import matplotlib.pyplot as plt # Import pyplot for creating static visualizations and plots
from prophet import Prophet # Import the Prophet library to handle the temporal baseline forecasting
from sklearn.ensemble import IsolationForest # Import Isolation Forest for unsupervised anomaly detection
from sklearn.metrics import mean_squared_error, mean_absolute_error # Import error metrics to evaluate model continuous performance
from sklearn.metrics import precision_score, recall_score, f1_score # Import classification metrics to evaluate anomaly detection performance
from sklearn.impute import KNNImputer # Import KNNImputer for filling missing data based on feature similarity
import lightgbm as lgb # Import LightGBM for the residual correction model
import shap # Import SHAP to generate Explainable AI (XAI) feature importance values
import joblib # Import joblib for serializing and deserializing the trained machine learning models
import warnings # Import warnings to manage system warning outputs
import logging # Re-import logging (redundant, but included for completeness)

matplotlib.use('Agg') # Set the matplotlib backend to 'Agg' to generate plots without requiring a graphical display (useful for servers)
warnings.filterwarnings('ignore') # Instruct Python to ignore all warnings to keep standard output clean

# Resolve paths relative to this script's location # Comment defining the path resolution strategy
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Get the absolute path of the directory containing this script
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..') # Define the project root as one level up from the Scripts directory

output_dir = os.path.join(PROJECT_ROOT, 'Outputs') # Construct the path to the 'Outputs' directory where visualizations will be saved
models_dir = os.path.join(PROJECT_ROOT, 'Models') # Construct the path to the 'Models' directory where .joblib files will be saved
os.makedirs(models_dir, exist_ok=True) # Create the Models directory if it does not already exist

params_path = os.path.join(models_dir, 'best_hybrid_params.json') # Define the path for the JSON file that stores optimized hyperparameters

# Tuning control (can be overridden from environment variables) # Comment indicating how optimization constraints are controlled
OPTUNA_TRIALS = int(os.getenv('OPTUNA_TRIALS', '50')) # Set the number of Optuna trials, defaulting to 50 if the env var is not set
RETUNE_EVERY_DAYS = int(os.getenv('RETUNE_EVERY_DAYS', '30')) # Set the retune frequency, defaulting to 30 days
FORCE_RETUNE = True # Set a boolean flag to forcefully execute hyperparameter tuning regardless of age

print("1. Pre-processing: Raw data ingestion...") # Print a status message indicating the start of the data ingestion phase
train_dir = os.path.join(PROJECT_ROOT, 'train_data') # Construct the path to the directory containing training data
test_dir = os.path.join(PROJECT_ROOT, 'test_data') # Construct the path to the directory containing testing and validation data

train_df = pd.read_csv(os.path.join(train_dir, 'dataset_daily_train.csv')) # Read the pre-split daily training dataset
val_df = pd.read_csv(os.path.join(test_dir, 'dataset_daily_val.csv')) # Read the pre-split daily validation dataset
test_df = pd.read_csv(os.path.join(test_dir, 'dataset_daily_test.csv')) # Read the pre-split daily testing dataset

train_df['Date'] = pd.to_datetime(train_df['Date']) # Convert the 'Date' column in the training set to datetime objects
val_df['Date'] = pd.to_datetime(val_df['Date']) # Convert the 'Date' column in the validation set to datetime objects
test_df['Date'] = pd.to_datetime(test_df['Date']) # Convert the 'Date' column in the testing set to datetime objects

print("2. Handling missing values via KNN Imputation (Fit on Train, Apply to all)...") # Print status for the missing value imputation phase
# We use Time_Idx to help the KNN imputer understand seasonality and temporal proximity # Comment explaining the purpose of Time_Idx
for df_part in [train_df, val_df, test_df]: # Loop through each of the three data partitions
    df_part['Time_Idx'] = df_part['Date'].dt.dayofyear # Extract the day of the year (1-365) to give the imputer seasonal context

features_to_impute = ['Time_Idx', 'Demand_MWh', 'Avg_Temp', 'Rainfall'] # Define the list of columns the KNN imputer will look at

imputer = KNNImputer(n_neighbors=5, weights='distance') # Initialize the KNNImputer to look at 5 nearest neighbors, weighting closer ones higher
# 1. FIT STRICTLY ON TRAIN # Crucial comment emphasizing the prevention of data leakage
imputer.fit(train_df[features_to_impute]) # Fit the imputer ONLY on the training data to learn distributions without seeing the future

# 2. APPLY TO ALL PARTITIONS # Comment explaining the transformation phase
train_df[features_to_impute] = imputer.transform(train_df[features_to_impute]) # Impute missing values in the training set
val_df[features_to_impute]   = imputer.transform(val_df[features_to_impute]) # Impute missing values in the validation set using logic learned from training
test_df[features_to_impute]  = imputer.transform(test_df[features_to_impute]) # Impute missing values in the test set using logic learned from training

# Clean up Time_Idx as it's not a final feature # Comment indicating the removal of the temporary imputation feature
for df_part in [train_df, val_df, test_df]: # Loop through the partitions again
    df_part.drop(columns=['Time_Idx'], inplace=True) # Drop the Time_Idx column since it was only needed for KNN

# Save the imputer for inference # Comment indicating the saving of the preprocessor
models_dir = os.path.join(PROJECT_ROOT, 'Models') # Re-declare the models directory path
os.makedirs(models_dir, exist_ok=True) # Ensure the directory exists
joblib.dump(imputer, os.path.join(models_dir, 'knn_imputer.joblib')) # Serialize and save the fitted imputer so the dashboard can use it later

print("3. Feature engineering & cleanup...") # Print status for the feature engineering phase
target_col = 'Demand_MWh' # Define the name of the target variable column

# --- Derive additional temporal and autoregressive features --- # Comment indicating the start of deriving new features
for df_part in [train_df, val_df, test_df]: # Iterate over all three partitions independently to prevent temporal leakage
    df_part['Month']      = df_part['Date'].dt.month # Extract the month number
    df_part['DayOfYear']  = df_part['Date'].dt.dayofyear # Extract the day of the year
    df_part['WeekOfYear'] = df_part['Date'].dt.isocalendar().week.astype(int) # Extract the ISO week number as an integer
    # Continuous trend (days since start) — helps model learn demand growth # Comment explaining the Trend feature
    df_part['Trend'] = (df_part['Date'] - pd.Timestamp('2018-01-01')).dt.days # Calculate the number of days since the start of the dataset
    # Extra lags # Comment indicating new lagged features
    df_part['Lag_2']  = df_part[target_col].shift(2) # Shift demand by 2 days
    df_part['Lag_14'] = df_part[target_col].shift(14) # Shift demand by 14 days (2 weeks)
    # Broader rolling windows # Comment indicating new moving average features
    df_part['Rolling_14'] = df_part[target_col].rolling(window=14, min_periods=1).mean() # Calculate the 14-day rolling average
    df_part['Rolling_30'] = df_part[target_col].rolling(window=30, min_periods=1).mean() # Calculate the 30-day rolling average
    # Temperature momentum (yesterday's temp) # Comment explaining the temperature lag
    df_part['Temp_Lag_1'] = df_part['Avg_Temp'].shift(1) # Shift temperature by 1 day to capture thermal inertia

features = [col for col in [ # Define the complete master list of input features for LightGBM and Isolation Forest
    'Day_of_Week', 'Is_Weekend', 'Is_Holiday', # Calendar flags
    'Month', 'DayOfYear', 'WeekOfYear', 'Trend', # Temporal indicators
    'Avg_Temp', 'Rainfall', 'Temp_Lag_1', # Weather data
    'Lag_1', 'Lag_2', 'Lag_7', 'Lag_14', 'Lag_30', # Historical demand lags
    'Rolling_7', 'Rolling_14', 'Rolling_30', # Historical moving averages
] if col in train_df.columns] # Ensure the feature exists in the training DataFrame before adding it

train_df = train_df.dropna(subset=features + [target_col]).copy() # Drop any rows in the training set that have NaNs in features or target (due to shifts)
val_df = val_df.dropna(subset=features + [target_col]).copy() # Drop NaNs in validation set
test_df = test_df.dropna(subset=features + [target_col]).copy() # Drop NaNs in testing set

# Concatenate back to 'df' for global feature/visualisation usage # Comment explaining the creation of a full dataset view
df = pd.concat([train_df, val_df, test_df]).sort_values('Date').reset_index(drop=True) # Combine, sort, and re-index all partitions for plotting purposes

print(f"   Available features: {features}") # Print the final list of active features

print(f"   Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}") # Print the number of rows in each partition

required_param_keys = { # Define a set of the exact hyperparameter keys expected by the system
    'contamination', # Isolation Forest outlier fraction
    'changepoint_prior_scale', # Prophet trend flexibility
    'seasonality_prior_scale', # Prophet seasonality strength
    'n_changepoints', # Prophet number of potential trend changes
    'learning_rate', # LightGBM step size
    'max_depth', # LightGBM max tree depth
    'num_leaves', # LightGBM max leaves per tree
    'subsample', # LightGBM row sampling fraction
    'colsample_bytree', # LightGBM column sampling fraction
    'min_child_samples', # LightGBM min data points per leaf (regularization)
    'reg_alpha', # LightGBM L1 regularization penalty
    'reg_lambda' # LightGBM L2 regularization penalty
} # Close the set definition

def load_saved_params(path): # Define a function to load previously optimized parameters from disk
    if not os.path.exists(path): # Check if the parameter JSON file exists
        return None # Return None if it doesn't
    try: # Start a try block to handle malformed JSON
        with open(path, 'r', encoding='utf-8') as f: # Open the JSON file for reading
            payload = json.load(f) # Parse the JSON payload
        params = payload.get('best_params', payload) # Extract the 'best_params' dictionary
        if not isinstance(params, dict): # Validate that params is actually a dictionary
            return None # Return None if invalid
        if not required_param_keys.issubset(set(params.keys())): # Check if all required keys are present
            return None # Return None if any parameter is missing
        return payload # Return the fully parsed and validated payload
    except Exception as e: # Catch file reading or parsing errors
        print(f"   Warning: failed to read saved params ({e}).") # Print a warning message
        return None # Return None to trigger a retune

def should_retune(saved_payload): # Define a function to decide whether hyperparameter tuning should run
    if FORCE_RETUNE: # Check the global override flag
        print("   Retune reason: FORCE_RETUNE=1") # Log the reason
        return True # Trigger tuning
    if saved_payload is None: # Check if the loaded payload is empty
        print("   Retune reason: no saved parameter file found.") # Log the reason
        return True # Trigger tuning

    tuned_at = saved_payload.get('last_tuned_at') # Get the timestamp of the last tuning run
    if not tuned_at: # Check if the timestamp is missing
        print("   Retune reason: missing last_tuned_at metadata.") # Log the reason
        return True # Trigger tuning

    try: # Start a try block to parse the timestamp
        tuned_ts = pd.to_datetime(tuned_at) # Convert the timestamp string to a datetime object
        age_days = (pd.Timestamp.now() - tuned_ts).days # Calculate how many days old the parameters are
        if age_days >= RETUNE_EVERY_DAYS: # Check if the age exceeds the threshold
            print(f"   Retune reason: params age {age_days} days >= {RETUNE_EVERY_DAYS} days.") # Log the reason
            return True # Trigger tuning
        print(f"   Using saved params (age: {age_days} days, retune threshold: {RETUNE_EVERY_DAYS} days).") # Log that we are using cached params
        return False # Bypass tuning
    except Exception: # Catch date parsing errors
        print("   Retune reason: invalid last_tuned_at format.") # Log the reason
        return True # Trigger tuning

# ============================================================ # Section separator
# STEP 3.5 & 4: JOINT BAYESIAN OPTIMIZATION (OPTUNA) # Title for the optimization section
# ============================================================ # Section separator
print("3.5 & 4: Joint Bayesian Optimization (Optuna)...") # Print status message

optuna.logging.set_verbosity(optuna.logging.WARNING) # Suppress verbose Optuna logging to clean up terminal output

logger = logging.getLogger('cmdstanpy') # Get the logger for cmdstanpy (used internally by Prophet)
logger.addHandler(logging.NullHandler()) # Add a null handler to suppress cmdstanpy logs
logger.propagate = False # Prevent cmdstanpy logs from bubbling up
logger.setLevel(logging.CRITICAL) # Set the cmdstanpy log level to critical only

df_prophet_val_proxy = val_df[['Date', 'Avg_Temp']].rename(columns={'Date': 'ds'}) # Prepare a minimal dataframe structure required for Prophet validation inference

def objective(trial): # Define the objective function that Optuna will try to minimize
    # 1. Suggest joint parameters # Comment indicating hyperparameter sampling
    contamination = trial.suggest_float('contamination', 0.001, 0.05, log=True) # Suggest an anomaly fraction between 0.1% and 5% (log scale)
    cps = trial.suggest_float('changepoint_prior_scale', 0.001, 0.1, log=True) # Suggest Prophet trend flexibility
    sps = trial.suggest_float('seasonality_prior_scale', 0.01, 1.0, log=True) # Suggest Prophet seasonality strength
    n_cp = trial.suggest_int('n_changepoints', 5, 20) # Suggest number of Prophet trend changepoints
    
    lgb_lr = trial.suggest_float('learning_rate', 0.001, 0.05, log=True) # Suggest LightGBM learning rate
    lgb_depth = trial.suggest_int('max_depth', 2, 4) # Suggest LightGBM max depth (shallow to prevent overfitting)
    lgb_leaves = trial.suggest_int('num_leaves', 4, 15) # Suggest LightGBM max leaves
    lgb_subsample = trial.suggest_float('subsample', 0.4, 0.8) # Suggest LightGBM row subsampling ratio
    lgb_colsample = trial.suggest_float('colsample_bytree', 0.4, 0.8) # Suggest LightGBM column subsampling ratio
    
    # New Regularization Parameters # Comment indicating LightGBM regularization
    lgb_min_child = trial.suggest_int('min_child_samples', 15, 60) # Suggest min data points per leaf
    lgb_reg_alpha = trial.suggest_float('reg_alpha', 0.01, 10.0, log=True) # Suggest L1 regularization weight
    lgb_reg_lambda = trial.suggest_float('reg_lambda', 0.01, 10.0, log=True) # Suggest L2 regularization weight
    
    # 2. Anomaly Detection + Imputation (IQR + Isolation Forest) # Comment indicating anomaly step
    #    Instead of removing anomalous rows (which creates holes), # Note explaining why we don't drop rows
    #    we impute them with the trailing 7-day mean of clean data. # Note explaining the imputation strategy
    temp_forest = IsolationForest(n_estimators=100, max_samples='auto', contamination=contamination, random_state=42, n_jobs=-1) # Initialize Isolation Forest with the suggested contamination rate
    temp_forest.fit(train_df[features]) # Fit IF on the training features
    temp_anomalies = temp_forest.predict(train_df[features]) # Predict anomalies (-1) or normal points (1)
    
    Q1_tmp = train_df[target_col].quantile(0.25) # Calculate the 25th percentile of demand
    Q3_tmp = train_df[target_col].quantile(0.75) # Calculate the 75th percentile of demand
    IQR_tmp = Q3_tmp - Q1_tmp # Calculate the Interquartile Range
    lower_tmp = Q1_tmp - 1.5 * IQR_tmp # Calculate the lower bound for statistical anomalies
    upper_tmp = Q3_tmp + 1.5 * IQR_tmp # Calculate the upper bound for statistical anomalies
    iqr_anomalies_tmp = np.where((train_df[target_col] < lower_tmp) | (train_df[target_col] > upper_tmp), -1, 1) # Flag points outside IQR bounds as -1
    
    is_anomaly_tmp = (temp_anomalies == -1) | (iqr_anomalies_tmp == -1) # Create a combined mask: anomaly if flagged by IF OR IQR
    temp_train_clean = train_df.copy() # Create a temporary copy of the training data to hold clean values
    # Impute each anomalous point with the mean of the last 7 days of clean data # Comment explaining the loop
    for idx in np.where(is_anomaly_tmp)[0]: # Loop through the indices of all flagged anomalies
        lookback_start = max(0, idx - 7) # Calculate the start index for a 7-day lookback window (bounded to 0)
        lookback_mask = ~is_anomaly_tmp[lookback_start:idx] # Create a mask to select only normal (non-anomalous) points in that window
        clean_window = train_df[target_col].iloc[lookback_start:idx][lookback_mask] # Extract the clean demand values from the lookback window
        if len(clean_window) > 0: # If there is at least one clean data point in the 7-day window
            temp_train_clean.iloc[idx, temp_train_clean.columns.get_loc(target_col)] = clean_window.mean() # Impute the anomaly with the window mean
        else: # If the entire 7-day window is anomalous
            # Fallback: use global training mean if no clean data in window # Comment explaining fallback logic
            temp_train_clean.iloc[idx, temp_train_clean.columns.get_loc(target_col)] = train_df[target_col].mean() # Impute using the overall dataset average
        
    # 3. Base Prophet (with temperature regressor for weather-driven demand) # Comment for Prophet training
    df_prophet_temp = temp_train_clean[['Date', target_col, 'Avg_Temp']].rename(columns={'Date': 'ds', target_col: 'y'}) # Format the cleaned training data for Prophet
    m_base = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False, changepoint_prior_scale=cps, seasonality_prior_scale=sps, n_changepoints=n_cp) # Initialize Prophet with suggested parameters
    m_base.add_regressor('Avg_Temp') # Add temperature as an external regressor to Prophet
    m_base.fit(df_prophet_temp) # Fit the Prophet model on the cleaned training data
    
    temp_train_clean['Prophet_Pred'] = m_base.predict(df_prophet_temp)['yhat'].values # Generate predictions for the training set
    preds_val_base = m_base.predict(df_prophet_val_proxy)['yhat'].values # Generate predictions for the validation set
    
    temp_val = val_df.copy() # Create a copy of the validation data
    temp_val['Prophet_Pred'] = preds_val_base # Inject Prophet's predictions into the validation dataframe
    
    # 4. Residual LightGBM # Comment for LightGBM training
    temp_train_clean['Prophet_Residual'] = temp_train_clean[target_col] - temp_train_clean['Prophet_Pred'] # Calculate the training residual (Actual - Baseline)
    temp_val['Prophet_Residual'] = temp_val[target_col] - temp_val['Prophet_Pred'] # Calculate the validation residual (Actual - Baseline)
    
    X_train_temp = temp_train_clean[features] # Define training features for LGBM
    y_train_res_temp = temp_train_clean['Prophet_Residual'] # Define training target (residual) for LGBM
    X_val_temp = temp_val[features] # Define validation features for LGBM
    y_val_res_temp = temp_val['Prophet_Residual'] # Define validation target (residual) for LGBM
    
    lgb_model = lgb.LGBMRegressor( # Initialize the LightGBM Regressor
        learning_rate=lgb_lr, max_depth=lgb_depth, num_leaves=lgb_leaves,  # Apply suggested architectural parameters
        subsample=lgb_subsample, colsample_bytree=lgb_colsample, # Apply suggested sampling parameters
        min_child_samples=lgb_min_child, reg_alpha=lgb_reg_alpha, reg_lambda=lgb_reg_lambda, # Apply suggested regularization parameters
        n_estimators=800, random_state=42, n_jobs=-1, verbose=-1, extra_trees=True # Set fixed parameters (800 trees, random state, extra randomized trees)
    ) # Close the LGBM initialization
    
    lgb_model.fit( # Train the LightGBM model
        X_train_temp, y_train_res_temp, # Train on the calculated residuals
        eval_set=[(X_val_temp, y_val_res_temp)], # Evaluate on the validation set during training
        callbacks=[ # Pass callbacks to monitor training
            lgb.early_stopping(stopping_rounds=20, verbose=False), # Stop early if validation MAE doesn't improve for 20 rounds
            lgb.log_evaluation(period=0) # Suppress iteration logs
        ] # Close callbacks list
    ) # Close fit call
    
    preds_val_res = lgb_model.predict(X_val_temp) # Predict residuals on the validation set
    hybrid_preds = temp_val['Prophet_Pred'] + preds_val_res # Combine Prophet baseline with LGBM residual for final hybrid prediction
    
    return mean_absolute_error(temp_val[target_col], hybrid_preds) # Return the MAE on the validation set (this is what Optuna minimizes)

saved_payload = load_saved_params(params_path) # Attempt to load existing hyperparameters from disk

if should_retune(saved_payload): # Check if the system decided that retuning is necessary
    print(f"   Running Joint Bayesian Search ({OPTUNA_TRIALS} Trials)...") # Print search status
    sampler = optuna.samplers.TPESampler(seed=0) # Initialize the Tree-structured Parzen Estimator sampler for Bayesian search
    study = optuna.create_study(direction='minimize', sampler=sampler) # Create an Optuna study aiming to minimize the returned metric
    study.optimize(objective, n_trials=OPTUNA_TRIALS, show_progress_bar=False) # Run the optimization loop for the specified number of trials

    best_p = study.best_params # Extract the best combination of hyperparameters found during the search
    print(f"   Best Joint Parameters found: {best_p}") # Print the winning parameters

    params_payload = { # Create a dictionary payload to save to disk
        'best_params': best_p, # Store the parameters
        'last_tuned_at': pd.Timestamp.now().isoformat(), # Store the current timestamp
        'n_trials': OPTUNA_TRIALS, # Store the number of trials run
        'retune_every_days': RETUNE_EVERY_DAYS, # Store the retune rule used
        'target_col': target_col, # Store the target column name
        'features': features, # Store the list of features used
    } # Close payload dictionary
    with open(params_path, 'w', encoding='utf-8') as f: # Open the JSON file in write mode
        json.dump(params_payload, f, indent=2) # Dump the payload as formatted JSON
    print(f"   Saved best parameters to: {params_path}") # Confirm save location
else: # If retuning was bypassed
    best_p = saved_payload['best_params'] # Load the best parameters from the cached file
    print(f"   Loaded saved best parameters from: {params_path}") # Confirm load location

# ============================================================ # Section separator
# FINAL ARCHITECTURE TRAINING # Title for final model training phase
# ============================================================ # Section separator
print("   Training Final Champion Architecture...") # Print status message

# 1. Final Anomaly Detection + Imputation (IQR + Isolation Forest) # Comment explaining final imputation
#    Anomalous values are replaced with the trailing 7-day mean of clean data, # Note on strategy
#    so no rows are dropped and the time series remains gap-free. # Note on gap preservation
iso_forest = IsolationForest(n_estimators=300, max_samples='auto', contamination=best_p['contamination'], random_state=42, n_jobs=-1) # Initialize final Isolation Forest with 300 trees and optimized contamination
iso_forest.fit(train_df[features]) # Fit the model on the full training features
train_anomalies = iso_forest.predict(train_df[features]) # Generate anomaly predictions for the training set

# IQR Computation for Demand_MWh # Comment explaining statistical anomaly baseline
Q1 = train_df[target_col].quantile(0.25) # Calculate 25th percentile
Q3 = train_df[target_col].quantile(0.75) # Calculate 75th percentile
IQR_val = Q3 - Q1 # Calculate IQR
lower_bound = Q1 - 1.5 * IQR_val # Calculate lower bound
upper_bound = Q3 + 1.5 * IQR_val # Calculate upper bound
iqr_anomalies = np.where((train_df[target_col] < lower_bound) | (train_df[target_col] > upper_bound), -1, 1) # Flag points outside bounds as -1

# Combined anomaly mask: flagged by IF or IQR # Comment on logical OR masking
is_anomaly = (train_anomalies == -1) | (iqr_anomalies == -1) # Create boolean mask where True means an anomaly was detected
num_anomalies = is_anomaly.sum() # Count the total number of detected anomalies

# Impute each anomalous point with the mean of the last 7 days of clean data # Comment explaining final loop
train_df_clean = train_df.copy() # Copy training data to apply fixes
for idx in np.where(is_anomaly)[0]: # Loop through anomalous indices
    lookback_start = max(0, idx - 7) # Get 7-day lookback start index
    lookback_mask = ~is_anomaly[lookback_start:idx] # Get mask of normal data within the lookback window
    clean_window = train_df[target_col].iloc[lookback_start:idx][lookback_mask] # Extract clean data
    if len(clean_window) > 0: # If clean data exists
        train_df_clean.iloc[idx, train_df_clean.columns.get_loc(target_col)] = clean_window.mean() # Impute with window mean
    else: # If no clean data
        # Fallback: use global training mean if no clean data in window # Comment
        train_df_clean.iloc[idx, train_df_clean.columns.get_loc(target_col)] = train_df[target_col].mean() # Impute with global mean

print(f"   Built final clean dataset using IQR + IF. Imputed {num_anomalies} anomalies (0 rows removed).") # Print anomaly stats

# Evaluate Isolation Forest Precision, Recall, F1 against IQR pseudo-ground truth # Comment for IF metric calculation

y_true_anom = (iqr_anomalies == -1).astype(int) # Convert IQR labels to binary 1/0 (true anomalies)
y_pred_anom = (train_anomalies == -1).astype(int) # Convert IF labels to binary 1/0 (predicted anomalies)
iso_precision = precision_score(y_true_anom, y_pred_anom, zero_division=0) # Calculate precision (how many detected anomalies were real IQR anomalies)
iso_recall = recall_score(y_true_anom, y_pred_anom, zero_division=0) # Calculate recall (how many real IQR anomalies were caught by IF)
iso_f1 = f1_score(y_true_anom, y_pred_anom, zero_division=0) # Calculate the F1 score (harmonic mean)

# Visualize Anomalies # Comment for plotting logic
anomalous_data = train_df[train_anomalies == -1] # Filter dataframe for anomalous points
normal_data = train_df[train_anomalies != -1] # Filter dataframe for normal points

plt.figure(figsize=(15, 6)) # Initialize a large, wide Matplotlib figure
plt.plot(train_df['Date'], train_df[target_col], color='royalblue', label='Normal Demand', alpha=0.6, linewidth=1) # Plot the full demand line in blue
plt.scatter(anomalous_data['Date'], anomalous_data[target_col], color='crimson', label='Detected Anomaly', zorder=5) # Scatter plot the anomalies in red over the line
plt.title('Isolation Forest: Detected Anomalies in Training Data') # Set the plot title
plt.xlabel('Date') # Set X-axis label
plt.ylabel('Electricity Demand (MWh)') # Set Y-axis label
plt.legend() # Display the legend
plt.tight_layout() # Adjust the layout to prevent clipping
anomaly_plot_path = os.path.join(output_dir, 'fig0_anomalies_detected.png') # Define the save path
plt.savefig(anomaly_plot_path, dpi=300) # Save the figure in high resolution
plt.close() # Close the figure to free up memory
print(f"   Saved Anomaly Visualization: {anomaly_plot_path}") # Print save confirmation

# 2. Final Prophet Training (train-only, no val/test exposure) # Comment on Prophet training strategy
#    Mirrors Optuna's evaluation: Prophet sees ONLY training data. # Note on leakage prevention
#    Val and Test are both fully out-of-sample. # Note on leakage prevention
print("   Training Final Prophet (train-only)...") # Status message
df_prophet_train = train_df_clean[['Date', target_col, 'Avg_Temp']].rename( # Prepare training dataframe for Prophet
    columns={'Date': 'ds', target_col: 'y'} # Rename columns to strictly match Prophet requirements
) # Close dataframe preparation
prophet_model = Prophet( # Initialize final Prophet model
    yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False, # Enable yearly and weekly seasonality, disable daily
    changepoint_prior_scale=best_p['changepoint_prior_scale'], # Use optimized prior scale
    seasonality_prior_scale=best_p['seasonality_prior_scale'], # Use optimized seasonality scale
    n_changepoints=best_p['n_changepoints'] # Use optimized number of changepoints
) # Close model initialization
prophet_model.add_regressor('Avg_Temp') # Register temperature as an external regressor
prophet_model.fit(df_prophet_train) # Train Prophet strictly on the cleaned training set

# ONE Prophet model → predictions for ALL splits # Comment explaining inference
for split_df in [train_df_clean, train_df, val_df, test_df]: # Loop through all sets
    future = split_df[['Date', 'Avg_Temp']].rename(columns={'Date': 'ds'}) # Prepare future dataframe with dates and temperature
    split_df['Prophet_Pred'] = prophet_model.predict(future)['yhat'].values # Predict baselines and save them to the dataframe

# 3. Final LightGBM Training (train-only, val as held-out early-stop) # Comment for LightGBM final setup
#    Mirrors Optuna exactly: LightGBM trains on train residuals, # Note on architecture
#    validates on val residuals. Neither model has seen val or test. # Note on leakage prevention
train_df_clean['Prophet_Residual'] = train_df_clean[target_col] - train_df_clean['Prophet_Pred'] # Calculate residuals for the clean training set
train_df['Prophet_Residual'] = train_df[target_col] - train_df['Prophet_Pred'] # Calculate residuals for the original training set
val_df['Prophet_Residual'] = val_df[target_col] - val_df['Prophet_Pred'] # Calculate residuals for the validation set
test_df['Prophet_Residual'] = test_df[target_col] - test_df['Prophet_Pred'] # Calculate residuals for the test set

X_train_final = train_df_clean[features] # Define final training features
y_train_final = train_df_clean['Prophet_Residual'] # Define final training target
X_val = val_df[features] # Define validation features
y_val = val_df['Prophet_Residual'] # Define validation target

model_lgb = lgb.LGBMRegressor( # Initialize final LightGBM Regressor
    learning_rate=best_p['learning_rate'], max_depth=best_p['max_depth'], # Load optimized params
    num_leaves=best_p['num_leaves'], subsample=best_p['subsample'], # Load optimized params
    colsample_bytree=best_p['colsample_bytree'], # Load optimized params
    min_child_samples=best_p['min_child_samples'], # Load optimized params
    reg_alpha=best_p['reg_alpha'], # Load optimized params
    reg_lambda=best_p['reg_lambda'], # Load optimized params
    n_estimators=800, random_state=42, n_jobs=-1, verbose=-1, extra_trees=True # Use fixed configuration parameters
) # Close initialization

model_lgb.fit( # Train final LightGBM model
    X_train_final, y_train_final, # Fit on training residuals
    eval_set=[(X_val, y_val)], # Monitor performance on validation residuals
    callbacks=[ # Define early stopping callbacks
        lgb.early_stopping(stopping_rounds=50, verbose=False), # Stop if validation error doesn't improve for 50 rounds
        lgb.log_evaluation(period=0) # Suppress iteration logs
    ] # Close callbacks list
) # Close fit call

for split_df in [train_df, val_df, test_df]: # Loop over all datasets
    split_df['LGBM_Residual_Pred'] = model_lgb.predict(split_df[features]) # Predict the residual correction

train_df['Final_Pred'] = train_df['Prophet_Pred'] + train_df['LGBM_Residual_Pred'] # Combine for Train
val_df['Final_Pred'] = val_df['Prophet_Pred'] + val_df['LGBM_Residual_Pred'] # Combine for Val
test_df['Final_Pred'] = test_df['Prophet_Pred'] + test_df['LGBM_Residual_Pred'] # Combine for Test
# ============================================================ # Section separator
# STEP 5: COMPREHENSIVE MODEL EVALUATION (RMSE, MAPE, MAE) # Title for evaluation section
# ============================================================ # Section separator
print("5. Evaluating Model Performance (Prophet-Only vs Hybrid)...") # Status message

def calc_mape(actual, predicted): # Define a function to compute Mean Absolute Percentage Error
    """Mean Absolute Percentage Error — avoids division by zero.""" # Docstring
    mask = actual != 0 # Create a boolean mask to filter out rows where actual demand is 0
    return np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100 # Compute MAPE and multiply by 100 for percentage

# --- Prophet-Only Metrics (per split) --- # Comment for baseline metrics
prophet_mae_train  = mean_absolute_error(train_df['Demand_MWh'], train_df['Prophet_Pred']) # Calc MAE on Train
prophet_rmse_train = np.sqrt(mean_squared_error(train_df['Demand_MWh'], train_df['Prophet_Pred'])) # Calc RMSE on Train
prophet_mape_train = calc_mape(train_df['Demand_MWh'].values, train_df['Prophet_Pred'].values) # Calc MAPE on Train

prophet_mae_val  = mean_absolute_error(val_df['Demand_MWh'], val_df['Prophet_Pred']) # Calc MAE on Val
prophet_rmse_val = np.sqrt(mean_squared_error(val_df['Demand_MWh'], val_df['Prophet_Pred'])) # Calc RMSE on Val
prophet_mape_val = calc_mape(val_df['Demand_MWh'].values, val_df['Prophet_Pred'].values) # Calc MAPE on Val

prophet_mae_test  = mean_absolute_error(test_df['Demand_MWh'], test_df['Prophet_Pred']) # Calc MAE on Test
prophet_rmse_test = np.sqrt(mean_squared_error(test_df['Demand_MWh'], test_df['Prophet_Pred'])) # Calc RMSE on Test
prophet_mape_test = calc_mape(test_df['Demand_MWh'].values, test_df['Prophet_Pred'].values) # Calc MAPE on Test

# --- Hybrid (Prophet + LightGBM) Metrics (per split) --- # Comment for hybrid metrics
hybrid_mae_train  = mean_absolute_error(train_df['Demand_MWh'], train_df['Final_Pred']) # Calc MAE on Train
hybrid_rmse_train = np.sqrt(mean_squared_error(train_df['Demand_MWh'], train_df['Final_Pred'])) # Calc RMSE on Train
hybrid_mape_train = calc_mape(train_df['Demand_MWh'].values, train_df['Final_Pred'].values) # Calc MAPE on Train

hybrid_mae_val  = mean_absolute_error(val_df['Demand_MWh'], val_df['Final_Pred']) # Calc MAE on Val
hybrid_rmse_val = np.sqrt(mean_squared_error(val_df['Demand_MWh'], val_df['Final_Pred'])) # Calc RMSE on Val
hybrid_mape_val = calc_mape(val_df['Demand_MWh'].values, val_df['Final_Pred'].values) # Calc MAPE on Val

hybrid_mae_test  = mean_absolute_error(test_df['Demand_MWh'], test_df['Final_Pred']) # Calc MAE on Test
hybrid_rmse_test = np.sqrt(mean_squared_error(test_df['Demand_MWh'], test_df['Final_Pred'])) # Calc RMSE on Test
hybrid_mape_test = calc_mape(test_df['Demand_MWh'].values, test_df['Final_Pred'].values) # Calc MAPE on Test

print("\n" + "=" * 82) # Print a visual separator for the table
print("  MODEL COMPARISON: Prophet-Only vs Hybrid (Prophet + LightGBM)") # Print table title
print("=" * 82) # Print separator
print(f"{'Metric':<12} | {'Prophet-Only (Train)':<22} | {'Hybrid (Train)':<22} | Note") # Print Train table headers
print("-" * 82) # Print separator
print(f"{'MAE':<12} | {prophet_mae_train:>18,.2f} MWh | {hybrid_mae_train:>18,.2f} MWh | In-sample") # Print Train MAE
print(f"{'RMSE':<12} | {prophet_rmse_train:>18,.2f} MWh | {hybrid_rmse_train:>18,.2f} MWh |") # Print Train RMSE
print(f"{'MAPE':<12} | {prophet_mape_train:>17.2f}%     | {hybrid_mape_train:>17.2f}%     |") # Print Train MAPE
print("-" * 82) # Print separator
print(f"{'Metric':<12} | {'Prophet-Only (Val)':<22} | {'Hybrid (Val)':<22} | Note") # Print Val table headers
print("-" * 82) # Print separator
print(f"{'MAE':<12} | {prophet_mae_val:>18,.2f} MWh | {hybrid_mae_val:>18,.2f} MWh | Out-of-sample") # Print Val MAE
print(f"{'RMSE':<12} | {prophet_rmse_val:>18,.2f} MWh | {hybrid_rmse_val:>18,.2f} MWh |") # Print Val RMSE
print(f"{'MAPE':<12} | {prophet_mape_val:>17.2f}%     | {hybrid_mape_val:>17.2f}%     |") # Print Val MAPE
print("-" * 82) # Print separator
print(f"{'Metric':<12} | {'Prophet-Only (Test)':<22} | {'Hybrid (Test)':<22} | Note") # Print Test table headers
print("-" * 82) # Print separator
print(f"{'MAE':<12} | {prophet_mae_test:>18,.2f} MWh | {hybrid_mae_test:>18,.2f} MWh | Out-of-sample") # Print Test MAE
print(f"{'RMSE':<12} | {prophet_rmse_test:>18,.2f} MWh | {hybrid_rmse_test:>18,.2f} MWh |") # Print Test RMSE
print(f"{'MAPE':<12} | {prophet_mape_test:>17.2f}%     | {hybrid_mape_test:>17.2f}%     |") # Print Test MAPE
print("=" * 82) # Print closing separator

# Diagnostic: Overfitting vs Distribution Shift # Comment on model diagnostics
overfit_gap = hybrid_mape_val - hybrid_mape_train  # Train vs Val = overfitting signal # Calculate gap showing overfitting
shift_gap   = hybrid_mape_test - hybrid_mape_val   # Val vs Test  = distribution shift signal # Calculate gap showing concept drift

print(f"\n  >> Hybrid Train MAPE: {hybrid_mape_train:.2f}%") # Print Train MAPE
print(f"  >> Hybrid Val MAPE:   {hybrid_mape_val:.2f}%") # Print Val MAPE
print(f"  >> Hybrid Test MAPE:  {hybrid_mape_test:.2f}%") # Print Test MAPE
print(f"\n  >> Train→Val Gap:  {overfit_gap:.2f}pp  (Overfitting indicator)") # Print overfit gap
print(f"  >> Val→Test Gap:   {shift_gap:.2f}pp  (Distribution Shift indicator)") # Print shift gap

# Overfitting diagnosis (Train vs Val) # Comment for logical evaluation
if overfit_gap < 1.0: # Check if gap is negligible
    print("  >> OVERFIT CHECK:  ✅ Healthy — model generalises well from train to unseen val.") # Print positive result
elif overfit_gap < 2.5: # Check if gap is moderate
    print("  >> OVERFIT CHECK:  ⚠️  Mild overfitting — consider stronger regularisation.") # Print warning
else: # If gap is very large
    print("  >> OVERFIT CHECK:  ❌ Significant overfitting — model memorises training data.") # Print failure

# Distribution shift diagnosis (Val vs Test) # Comment for temporal drift evaluation
if shift_gap < 0.5: # Check if validation and test look similar
    print("  >> SHIFT CHECK:    ✅ Stable — val and test periods have similar demand patterns.") # Print positive result
elif shift_gap < 2.0: # Check if test is drifting away slightly
    print("  >> SHIFT CHECK:    ⚠️  Moderate distribution shift — test period differs from val.") # Print warning
else: # If test has fundamentally different patterns
    print("  >> SHIFT CHECK:    ❌ Large distribution shift — demand patterns changed significantly.") # Print failure

rmse_improvement = ((prophet_rmse_test - hybrid_rmse_test) / prophet_rmse_test) * 100 # Calculate percentage RMSE reduction
mape_improvement = ((prophet_mape_test - hybrid_mape_test) / prophet_mape_test) * 100 # Calculate percentage MAPE reduction
print(f"\n  >> Hybrid improves Test RMSE by {rmse_improvement:.1f}%") # Print RMSE improvement
print(f"  >> Hybrid improves Test MAPE by {mape_improvement:.1f}%\n") # Print MAPE improvement

# ============================================================ # Section separator
# STEP 6b: EXPORT MODELS & PREDICTIONS FOR DASHBOARD # Title for export section
# ============================================================ # Section separator
print("6b. Exporting trained models and predictions...") # Status message

# Save trained models for the dashboard # Comment indicating serialization
joblib.dump(prophet_model, os.path.join(models_dir, 'prophet_model.joblib')) # Save Prophet model to .joblib
joblib.dump(model_lgb, os.path.join(models_dir, 'lgbm_model.joblib')) # Save LightGBM model to .joblib
joblib.dump(iso_forest, os.path.join(models_dir, 'iso_forest.joblib')) # Save Isolation Forest model to .joblib
print(f"   Models saved to: {models_dir}") # Confirm save directory

# Save predictions CSV for the dashboard (combine all splits) # Comment explaining data export
df_all = pd.concat([train_df, val_df, test_df]).sort_values('Date').reset_index(drop=True) # Concatenate all dataframe partitions into one continuous chronological table
df_all.rename(columns={'Final_Pred': 'Hybrid_Prediction'}, inplace=True) # Rename Final_Pred for clarity in the dashboard
predictions_path = os.path.join(output_dir, 'dataset_daily_with_predictions.csv') # Define file path
df_all.to_csv(predictions_path, index=False) # Export the dataframe to a CSV file
print(f"   Predictions saved to: {predictions_path}") # Confirm save location

# Save XAI plot for the dashboard # Comment indicating XAI export
def export_xai_plot(lgbm_model, X_data, output_path): # Define function to build the static SHAP plot
    """Export a feature impact visualization as output_xai.png for the dashboard.""" # Docstring
    try: # Try block to catch SHAP generation errors
        sample_n = min(500, len(X_data)) # Limit the background data size to 500 rows to speed up SHAP calculation
        X_sample = X_data.sample(n=sample_n, random_state=42) if len(X_data) > sample_n else X_data # Subsample the data randomly
        explainer = shap.TreeExplainer(lgbm_model) # Initialize the SHAP explainer for trees
        shap_values = explainer.shap_values(X_sample) # Compute Shapley values
        plt.figure(figsize=(10, 6)) # Initialize Matplotlib figure
        shap.summary_plot(shap_values, X_sample, show=False) # Generate the SHAP beeswarm summary plot, preventing it from immediately displaying
        plt.title('Global SHAP Summary for Exogenous Features') # Set chart title
        plt.tight_layout() # Adjust layout margins
        plt.savefig(output_path, dpi=200) # Save chart to PNG
        plt.close() # Close figure
        print(f"   XAI plot saved to: {output_path}") # Log success
    except Exception as e: # Catch any errors
        print(f"   Warning: SHAP export failed ({e}), using fallback feature importance plot.") # Log fallback activation
        importances = pd.Series(lgbm_model.feature_importances_, index=X_data.columns).sort_values(ascending=True) # Fallback to standard LightGBM feature importance
        plt.figure(figsize=(10, 6)) # Initialize figure
        importances.plot(kind='barh') # Plot a horizontal bar chart
        plt.title('Feature Importance (Fallback)') # Set title
        plt.xlabel('Importance') # Set X-axis label
        plt.tight_layout() # Adjust margins
        plt.savefig(output_path, dpi=200) # Save chart
        plt.close() # Close figure

xai_path = os.path.join(PROJECT_ROOT, 'output_xai.png') # Define output path for the XAI image
export_xai_plot(model_lgb, df[features], xai_path) # Call the export function

# ============================================================ # Section separator
# STEP 7: GENERATE ALL VISUALIZATIONS # Title for dashboard image generation
# ============================================================ # Section separator
print("7. Generating Visualizations...") # Print status message

# Set a clean, professional style # Comment for visual theming
plt.rcParams.update({ # Update global Matplotlib style settings
    'figure.facecolor': '#0f1117', # Set dark theme background color
    'axes.facecolor': '#1a1d29', # Set dark theme plot background
    'axes.edgecolor': '#2d3250', # Set grid line colors
    'axes.labelcolor': '#e0e0e0', # Set label text colors
    'text.color': '#e0e0e0', # Set general text colors
    'xtick.color': '#a0a0a0', # Set tick mark colors
    'ytick.color': '#a0a0a0', # Set tick mark colors
    'grid.color': '#2d3250', # Set grid color
    'grid.alpha': 0.5, # Set grid transparency
    'font.family': 'sans-serif', # Use modern sans-serif fonts
    'font.size': 10, # Set base font size
}) # Close style update dict

# --- FIGURE 1: Actual vs Predicted Time Series (FULL TIMELINE) --- # Comment for Chart 1
all_dates = pd.concat([train_df['Date'], val_df['Date'], test_df['Date']]) # Recombine all dates
all_actual = pd.concat([train_df['Demand_MWh'], val_df['Demand_MWh'], test_df['Demand_MWh']]) # Recombine all actuals
all_prophet = pd.concat([train_df['Prophet_Pred'], val_df['Prophet_Pred'], test_df['Prophet_Pred']]) # Recombine all baselines
all_hybrid = pd.concat([train_df['Hybrid_Prediction'] if 'Hybrid_Prediction' in train_df.columns else train_df['Final_Pred'], # Check column name and extract Train preds
                         val_df['Hybrid_Prediction'] if 'Hybrid_Prediction' in val_df.columns else val_df['Final_Pred'], # Extract Val preds
                         test_df['Hybrid_Prediction'] if 'Hybrid_Prediction' in test_df.columns else test_df['Final_Pred']]) # Extract Test preds

fig1, ax1 = plt.subplots(figsize=(16, 6)) # Initialize figure 1 with subplots
ax1.plot(all_dates, all_actual, color='#4fc3f7', alpha=0.6, linewidth=0.7, label='Actual Demand') # Plot the actual demand as a thin blue line
ax1.plot(all_dates, all_prophet, color='#ff8a65', linewidth=0.9, linestyle='--', alpha=0.7, label='Prophet-Only') # Plot the Prophet baseline as an orange dashed line
ax1.plot(all_dates, all_hybrid, color='#66bb6a', linewidth=1.0, alpha=0.85, label='Hybrid (Prophet+LGB)') # Plot the Hybrid prediction as a solid green line

ax1.axvspan(train_df['Date'].iloc[0], train_df['Date'].iloc[-1], alpha=0.04, color='#4fc3f7', label='Train (70%)') # Shade the background representing the training period
ax1.axvspan(val_df['Date'].iloc[0], val_df['Date'].iloc[-1], alpha=0.08, color='#ffab40', label='Validation (15%)') # Shade the background representing the validation period
ax1.axvspan(test_df['Date'].iloc[0], test_df['Date'].iloc[-1], alpha=0.08, color='#ef5350', label='Test (15%)') # Shade the background representing the test period

ax1.set_title('Electricity Demand: Actual vs Model Predictions (Full Timeline)', fontsize=14, fontweight='bold', pad=15) # Set main title
ax1.set_xlabel('Date') # Label X-axis
ax1.set_ylabel('Demand (MWh)') # Label Y-axis
ax1.legend(loc='upper left', fontsize=8, ncol=3, framealpha=0.3) # Render legend
ax1.grid(True, alpha=0.3) # Turn on background grid
fig1.tight_layout() # Compress margins
fig1_path = os.path.join(output_dir, 'fig1_actual_vs_predicted.png') # Define save path
fig1.savefig(fig1_path, dpi=150, bbox_inches='tight') # Save the plot
plt.close(fig1) # Close figure
print(f"  [1/4] Saved: {fig1_path}") # Log success

# --- FIGURE 2: Model Comparison Bar Chart (MAE, RMSE & MAPE) --- # Comment for Chart 2
fig2, (ax2a, ax2b, ax2c) = plt.subplots(1, 3, figsize=(18, 5)) # Create a figure with 3 side-by-side subplots

models_list = ['Prophet-Only', 'Hybrid\n(Prophet+LGB)'] # Define X-axis labels
colors_bar = ['#ff8a65', '#66bb6a'] # Define colors for bars

mae_improvement = ((prophet_mae_test - hybrid_mae_test) / prophet_mae_test) * 100 # Recalculate MAE improvement

mae_vals = [prophet_mae_test, hybrid_mae_test] # Define Y values for MAE
bars0 = ax2a.bar(models_list, mae_vals, color=colors_bar, width=0.5, edgecolor='white', linewidth=0.5) # Plot MAE bar chart
for bar, val in zip(bars0, mae_vals): # Loop over the drawn bars
    ax2a.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200, f'{val:,.0f}', # Add text label on top of each bar
              ha='center', va='bottom', fontweight='bold', fontsize=11, color='#e0e0e0') # Format text
ax2a.set_title('Test Set MAE', fontsize=13, fontweight='bold', pad=12) # Set title for subplot 1
ax2a.set_ylabel('MAE (MWh)') # Set Y-axis label
ax2a.grid(axis='y', alpha=0.3) # Enable Y-axis grid
if hybrid_mae_test < prophet_mae_test: # If hybrid is better
    ax2a.annotate(f'{mae_improvement:.1f}% better', # Annotate the percentage improvement
                  xy=(1, hybrid_mae_test), fontsize=10, color='#66bb6a', # Place text near the second bar
                  ha='center', va='top', fontweight='bold') # Format annotation

rmse_vals = [prophet_rmse_test, hybrid_rmse_test] # Define Y values for RMSE
bars1 = ax2b.bar(models_list, rmse_vals, color=colors_bar, width=0.5, edgecolor='white', linewidth=0.5) # Plot RMSE bar chart
for bar, val in zip(bars1, rmse_vals): # Loop over bars
    ax2b.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200, f'{val:,.0f}', # Add text
              ha='center', va='bottom', fontweight='bold', fontsize=11, color='#e0e0e0') # Format text
ax2b.set_title('Test Set RMSE', fontsize=13, fontweight='bold', pad=12) # Set title for subplot 2
ax2b.set_ylabel('RMSE (MWh)') # Set Y-axis label
ax2b.grid(axis='y', alpha=0.3) # Enable grid
if hybrid_rmse_test < prophet_rmse_test: # Check improvement
    ax2b.annotate(f'{rmse_improvement:.1f}% better', # Annotate improvement
                  xy=(1, hybrid_rmse_test), fontsize=10, color='#66bb6a', # Placement
                  ha='center', va='top', fontweight='bold') # Format

mape_vals = [prophet_mape_test, hybrid_mape_test] # Define Y values for MAPE
bars2 = ax2c.bar(models_list, mape_vals, color=colors_bar, width=0.5, edgecolor='white', linewidth=0.5) # Plot MAPE bar chart
for bar, val in zip(bars2, mape_vals): # Loop over bars
    ax2c.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, f'{val:.2f}%', # Add text
              ha='center', va='bottom', fontweight='bold', fontsize=11, color='#e0e0e0') # Format
ax2c.set_title('Test Set MAPE', fontsize=13, fontweight='bold', pad=12) # Set title for subplot 3
ax2c.set_ylabel('MAPE (%)') # Label Y-axis
ax2c.grid(axis='y', alpha=0.3) # Enable grid
if hybrid_mape_test < prophet_mape_test: # Check improvement
    ax2c.annotate(f'{mape_improvement:.1f}% better', # Annotate
                  xy=(1, hybrid_mape_test), fontsize=10, color='#66bb6a', # Placement
                  ha='center', va='top', fontweight='bold') # Format

fig2.suptitle('Model Accuracy Comparison: Prophet-Only vs Hybrid', fontsize=15, fontweight='bold', y=1.02, color='#ffffff') # Add an overarching title for the figure
fig2.tight_layout() # Fix margins
fig2_path = os.path.join(output_dir, 'fig2_model_comparison.png') # Define save path
fig2.savefig(fig2_path, dpi=150, bbox_inches='tight') # Save figure
plt.close(fig2) # Close memory
print(f"  [2/4] Saved: {fig2_path}") # Log

# --- FIGURE 3: Residual Distribution (Prophet vs Hybrid) --- # Comment for Chart 3
fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(14, 5)) # Create a 1x2 subplot layout

prophet_residuals_test = test_df['Demand_MWh'] - test_df['Prophet_Pred'] # Calculate raw errors for Prophet
hybrid_residuals_test  = test_df['Demand_MWh'] - (test_df['Hybrid_Prediction'] if 'Hybrid_Prediction' in test_df.columns else test_df['Final_Pred']) # Calculate raw errors for Hybrid

ax3a.hist(prophet_residuals_test, bins=40, color='#ff8a65', alpha=0.8, edgecolor='#1a1d29') # Draw histogram for Prophet
ax3a.axvline(x=0, color='white', linestyle='--', linewidth=1, alpha=0.7) # Draw a white vertical line at 0 error
ax3a.set_title('Prophet-Only Residuals (Test)', fontsize=12, fontweight='bold') # Set subplot title
ax3a.set_xlabel('Residual (MWh)') # Label X-axis
ax3a.set_ylabel('Frequency') # Label Y-axis
ax3a.grid(axis='y', alpha=0.3) # Show grid

ax3b.hist(hybrid_residuals_test, bins=40, color='#66bb6a', alpha=0.8, edgecolor='#1a1d29') # Draw histogram for Hybrid
ax3b.axvline(x=0, color='white', linestyle='--', linewidth=1, alpha=0.7) # Draw line at 0 error
ax3b.set_title('Hybrid Residuals (Test)', fontsize=12, fontweight='bold') # Set subplot title
ax3b.set_xlabel('Residual (MWh)') # Label X-axis
ax3b.set_ylabel('Frequency') # Label Y-axis
ax3b.grid(axis='y', alpha=0.3) # Show grid

max_abs = max(prophet_residuals_test.abs().max(), hybrid_residuals_test.abs().max()) * 1.1 # Calculate maximum error bound to keep axes synchronized
ax3a.set_xlim(-max_abs, max_abs) # Lock X-axis for Prophet
ax3b.set_xlim(-max_abs, max_abs) # Lock X-axis for Hybrid

fig3.suptitle('Residual Distribution - Tighter = More Accurate', fontsize=14, fontweight='bold', y=1.02, color='#ffffff') # Set master title
fig3.tight_layout() # Clean layout
fig3_path = os.path.join(output_dir, 'fig3_residual_distribution.png') # Define path
fig3.savefig(fig3_path, dpi=150, bbox_inches='tight') # Save plot
plt.close(fig3) # Free memory
print(f"  [3/4] Saved: {fig3_path}") # Log

# --- FIGURE 4: SHAP Feature Importance --- # Comment for Chart 4
print("8. Generating XAI SHAP Explanation...") # Status update
X_test = test_df[features] # Get the test features to generate the final SHAP plot
explainer = shap.TreeExplainer(model_lgb) # Initialize TreeExplainer
shap_values = explainer.shap_values(X_test) # Calculate Shapley values for the entire test set
shap.summary_plot(shap_values, X_test, feature_names=features, show=False) # Plot the beeswarm chart
fig4 = plt.gcf() # Get the current matplotlib figure instantiated by SHAP
fig4.set_facecolor('#0f1117') # Force dark background color to match the theme
fig4.set_size_inches(10, 6) # Force explicit figure dimensions
shap_plot_path = os.path.join(output_dir, 'fig4_shap_summary.png') # Define save path
fig4.savefig(shap_plot_path, dpi=150, bbox_inches='tight', facecolor='#0f1117') # Save high resolution figure
plt.close(fig4) # Clean up memory
print(f"  [4/4] Saved: {shap_plot_path}") # Log

print("\n" + "=" * 72) # Print summary border
print("  ALL OUTPUTS SAVED:") # Print section title
print(f"    Models  -> {models_dir}") # Print models location
print(f"    Figures -> {output_dir}") # Print figures location
print("    - fig0_anomalies_detected.png") # List figure
print("    - fig1_actual_vs_predicted.png") # List figure
print("    - fig2_model_comparison.png") # List figure
print("    - fig3_residual_distribution.png") # List figure
print("    - fig4_shap_summary.png") # List figure
print(f"    Predictions -> {predictions_path}") # List prediction CSV location
print(f"    XAI Plot    -> {xai_path}") # List global XAI location
print("=" * 72) # Print closing border
print("\nSUCCESS! Hybrid Architecture Execution Completed.") # Print final termination message
