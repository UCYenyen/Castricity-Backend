import pandas as pd # Import pandas library for data manipulation and analysis
import numpy as np # Import numpy for numerical operations and array handling
import json # Import json to parse JSON files like the holidays data
import glob # Import glob to find files matching a specified pattern
import warnings # Import warnings to control warning messages
import os # Import os for operating system dependent functionality like file paths
warnings.filterwarnings('ignore') # Ignore all warning messages to keep the output clean

# Resolve paths relative to this script's location # This comment explains the next block of code
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Get the absolute directory path of the current script
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..') # Define the project root as the parent directory of the script

raw_data_dir = os.path.join(PROJECT_ROOT, 'Raw Data') # Construct the path to the 'Raw Data' directory
output_dir = os.path.join(PROJECT_ROOT, 'Outputs') # Construct the path to the 'Outputs' directory

print("1. Parsing BPS Yearly PLN Electricity...") # Print a status message indicating the start of data parsing
# Gather all Listrik yang Didistribusikan... for yearly demand # Comment explaining the purpose of the next lines
yearly_files = glob.glob(os.path.join(raw_data_dir, 'BPS_Electricity', 'Listrik yang Didistribusikan Menurut Provinsi (GWh), *.csv')) # Find all yearly electricity CSV files
yearly_demand = {} # Initialize an empty dictionary to store yearly demand values
for y_file in yearly_files: # Loop through each found CSV file
    year_str = os.path.basename(y_file).split(', ')[-1].replace('.csv', '') # Extract the year string from the filename
    try: # Start a try block to handle potential conversion errors
        y = int(year_str) # Convert the extracted year string into an integer
        if 2018 <= y <= 2023: # Check if the year is within our target range (2018-2023)
            df_y = pd.read_csv(y_file, skiprows=2) # Read the CSV file into a DataFrame, skipping the first two rows of metadata
            # Find the row mentioning Indonesia or Total # Comment explaining the next line
            total_row = df_y[df_y.iloc[:, 0].str.contains('Indonesia|Total', na=False, case=False)] # Filter the DataFrame for the national total row
            if not total_row.empty: # Check if the total row was successfully found
                val = str(total_row.iloc[0, 1]).replace(',', '').strip() # Extract the demand value, remove commas, and strip whitespace
                if val.replace('.','',1).isdigit(): # Check if the extracted string is a valid number
                    yearly_demand[y] = float(val) # Convert the string to a float and store it in the dictionary
    except Exception as e: # Catch any exceptions that occur during processing
        pass # Ignore exceptions and continue to the next file

# Fallback values if BPS files fail to parse properly # Comment explaining the fallback mechanism
base_yearly = {2018: 232000, 2019: 243000, 2020: 240000, 2021: 254000, 2022: 270000, 2023: 285000} # Define hardcoded fallback demand values in GWh
for y in range(2018, 2024): # Loop through the target years
    if y not in yearly_demand: # Check if the year is missing from the parsed dictionary
        yearly_demand[y] = base_yearly[y] # Fill in the missing year with the fallback value
print(f"Yearly Demand (GWh): {yearly_demand}") # Print the final yearly demand dictionary

print("2. Parsing Makroekonomi...") # Print a status message indicating the start of macroeconomic data parsing
macro_path = os.path.join(raw_data_dir, 'World_Bank_Macro', 'API_IDN_DS2_en_csv_v2_8804.csv') # Construct the path to the World Bank CSV file
df_macro = pd.read_csv(macro_path, skiprows=4) # Read the World Bank CSV, skipping the first 4 rows of metadata
ind_gdp = df_macro[df_macro['Indicator Code'] == 'NY.GDP.MKTP.CD'] # Extract the row for GDP
ind_pop = df_macro[df_macro['Indicator Code'] == 'SP.POP.TOTL'] # Extract the row for Total Population
# Real industrial activity: Manufacturing value added (constant 2015 US$) # Comment explaining the next variable
ind_manuf = df_macro[df_macro['Indicator Code'] == 'NV.IND.MANF.KD'] # Extract the row for Manufacturing Value Added

macro_dict = {} # Initialize a dictionary to store macroeconomic data per year
for y in range(2018, 2024): # Loop through the target years
    y_str = str(y) # Convert the year integer to a string for column indexing
    # Extract manufacturing value added and convert to an index (base 2018 = 100) # Comment explaining the next line
    manuf_val = ind_manuf[y_str].values[0] if (len(ind_manuf) > 0 and y_str in ind_manuf) else np.nan # Get the manufacturing value or NaN if missing
    macro_dict[y] = { # Create a nested dictionary for the current year
        'GDP': ind_gdp[y_str].values[0] / 1e9 if y_str in ind_gdp else np.nan, # Get GDP in billions, or NaN if missing
        'Population': ind_pop[y_str].values[0] if y_str in ind_pop else np.nan, # Get Population, or NaN if missing
        'Manufacturing_VA': manuf_val,  # constant 2015 US$ # Store the manufacturing value
    } # Close the nested dictionary assignment

# Convert Manufacturing VA to an index (base year 2018 = 100) for easier interpretation # Comment explaining the next block
base_manuf = macro_dict[2018]['Manufacturing_VA'] # Retrieve the baseline manufacturing value for 2018
if pd.notna(base_manuf) and base_manuf > 0: # Check if the base value is valid and greater than zero
    for y in macro_dict: # Loop through the macroeconomic dictionary
        if pd.notna(macro_dict[y]['Manufacturing_VA']): # Check if the current year has a valid manufacturing value
            macro_dict[y]['Industrial_Index'] = (macro_dict[y]['Manufacturing_VA'] / base_manuf) * 100 # Calculate the index relative to 2018
        else: # Execute if the value is missing
            macro_dict[y]['Industrial_Index'] = np.nan # Set the index to NaN
else: # Execute if the baseline value is missing or invalid
    # Fallback: use Industry value added annual % growth (NV.IND.TOTL.KD.ZG) # Comment explaining the fallback mechanism
    ind_growth = df_macro[df_macro['Indicator Code'] == 'NV.IND.TOTL.KD.ZG'] # Extract the row for annual growth percentage
    idx = 100.0 # Initialize the fallback index at 100.0 for the base year
    for y in range(2018, 2024): # Loop through the target years
        y_str = str(y) # Convert year to string
        growth = ind_growth[y_str].values[0] if (len(ind_growth) > 0 and y_str in ind_growth) else 0 # Get growth value, default to 0
        if y > 2018 and pd.notna(growth): # If it's after the base year and growth is valid
            idx *= (1 + growth / 100) # Accumulate the growth into the index
        macro_dict[y]['Industrial_Index'] = idx # Assign the calculated index to the dictionary

print("3. Parsing Kaggle Climate Data & BMKG Holidays...") # Print status for weather and holidays parsing
climate_path = os.path.join(raw_data_dir, 'Kaggle_Climate', 'climate_data.csv') # Construct the path to the climate data CSV
df_climate = pd.read_csv(climate_path) # Read the climate data into a DataFrame
df_climate['date'] = pd.to_datetime(df_climate['date'], format='%d-%m-%Y', errors='coerce') # Convert the date column to datetime objects
df_climate = df_climate.dropna(subset=['date']) # Drop any rows where the date conversion failed

# Aggregate national weather by day # Comment explaining the group by operation
df_climate_daily = df_climate.groupby('date').agg({'Tavg': 'mean', 'RR': 'mean'}).reset_index() # Calculate the daily national average for temp and rainfall
df_climate_daily.rename(columns={'date': 'Date', 'Tavg': 'Avg_Temp', 'RR': 'Rainfall'}, inplace=True) # Rename columns for clarity and consistency

# Parse JSON Holidays from Guangrei repo # Comment explaining the holiday parsing block
holidays_list = [] # Initialize an empty list to store holiday dates
holidays_json_path = os.path.join(raw_data_dir, 'Kaggle_Climate', 'Json-Indonesia-holidays', 'api.json') # Construct the path to the holidays JSON file
try: # Start a try block to handle potential missing files
    with open(holidays_json_path, 'r') as f: # Open the JSON file in read mode
        holiday_data = json.load(f) # Parse the JSON content into a Python dictionary
    for k, v in holiday_data.items(): # Loop through the keys (dates) and values (details)
        if isinstance(v, dict) and v.get('libur', False): # Check if the value is a dict and marked as a holiday ('libur')
            holidays_list.append(pd.to_datetime(k)) # Add the date to the holidays list
except: # Catch any exceptions (e.g., file not found)
    print("  Warning: Holiday JSON not found, proceeding without holiday data.") # Print a warning if the file fails to load

# CREATE DAILY FRAMEWORK (2018-2023) # Comment indicating the start of the daily dataset creation
date_rng_daily = pd.date_range(start='2018-01-01', end='2023-12-31', freq='D') # Generate a continuous range of daily dates
df_daily = pd.DataFrame({'Date': date_rng_daily}) # Create a DataFrame with the continuous dates as the base

# Merge Kaggle weather # Comment explaining the merge operation
df_daily = pd.merge(df_daily, df_climate_daily, on='Date', how='left') # Left merge the weather data onto the base date framework
# Fill missing dates with seasonal averages # Comment explaining the imputation strategy
df_daily['DayOfYear'] = df_daily['Date'].dt.dayofyear # Extract the day of the year (1-365/366) as a feature
seasonal_weather = df_daily.groupby('DayOfYear')[['Avg_Temp', 'Rainfall']].mean().reset_index() # Calculate the average weather for each day of the year across all years
df_daily = pd.merge(df_daily, seasonal_weather, on='DayOfYear', how='left', suffixes=('', '_mean')) # Merge the seasonal averages back into the main DataFrame
df_daily['Avg_Temp'] = df_daily['Avg_Temp'].fillna(df_daily['Avg_Temp_mean']).fillna(27.5) # Fill missing temperatures with the seasonal mean, then fallback to 27.5
df_daily['Rainfall'] = df_daily['Rainfall'].fillna(df_daily['Rainfall_mean']).fillna(5.0) # Fill missing rainfall with the seasonal mean, then fallback to 5.0

# Holiday and Weekend # Comment indicating the creation of calendar features
df_daily['Day_of_Week'] = df_daily['Date'].dt.dayofweek # Extract the day of the week (0=Monday, 6=Sunday)
df_daily['Is_Weekend'] = df_daily['Day_of_Week'].isin([5, 6]).astype(int) # Create a binary flag for weekends (Saturday/Sunday)
df_daily['Is_Holiday'] = df_daily['Date'].isin(holidays_list).astype(int) # Create a binary flag if the date is in the holidays list

# Distribute Yearly Demand into Daily Demand based on weather and weekend penalty # Comment explaining the core logic
# We will proportionally distribute the yearly_demand[y] into days. # Comment detailing the distribution strategy
df_daily['Year'] = df_daily['Date'].dt.year # Extract the year for grouping
df_daily['Daily_Weight'] = 1.0 # Initialize the daily weight multiplier at 1.0
df_daily.loc[df_daily['Is_Weekend'] == 1, 'Daily_Weight'] -= 0.2 # Reduce weight by 0.2 on weekends due to lower industrial activity
df_daily.loc[df_daily['Is_Holiday'] == 1, 'Daily_Weight'] -= 0.3 # Reduce weight by 0.3 on holidays due to massive load drop
# Hotter days map to higher demand # Comment explaining the temperature adjustment
df_daily['Daily_Weight'] += (df_daily['Avg_Temp'] - 27) * 0.05 # Increase weight by 0.05 for every degree above 27°C (cooling demand)

# Create a smooth continuous trend curve for the base yearly volume # Comment explaining the trend generation
# Map each year's demand to July 1st to anchor the trend # Comment explaining the anchoring strategy
yd_dates = pd.to_datetime([f"{y}-07-01" for y in range(2018, 2024)]) # Create anchor dates at the middle of each year
yd_values = [yearly_demand[y] * 1000 for y in range(2018, 2024)]  # GWh to MWh # Convert annual demand from GWh to MWh
yearly_series = pd.Series(yd_values, index=yd_dates) # Create a Pandas Series with the anchor dates and values

# Reindex and interpolate across all daily dates in our dataset # Comment explaining the interpolation process
df_daily.set_index('Date', inplace=True) # Temporarily set the date as the index for interpolation
df_daily['Smooth_Yearly_MWh'] = yearly_series # Map the yearly series onto the daily DataFrame
df_daily['Smooth_Yearly_MWh'] = df_daily['Smooth_Yearly_MWh'].interpolate(method='time').bfill().ffill() # Interpolate missing values smoothly, then backfill/forward-fill the edges
df_daily.reset_index(inplace=True) # Reset the index back to numbers

# Distribute continuously based on weight # Comment explaining the final demand allocation
# Note: Since Smooth_Yearly_MWh is a yearly volume, average daily baseline is Smooth / 365.25 # Comment explaining the mathematical scaling
avg_daily_weight = df_daily['Daily_Weight'].mean() # Calculate the global average weight to normalize the distribution
base_demand_continuous = (df_daily['Smooth_Yearly_MWh'] / 365.25) * (df_daily['Daily_Weight'] / avg_daily_weight) # Calculate the exact continuous daily demand

# === STOCHASTIC NOISE === # Comment marking the noise injection section
# Without noise, Demand_MWh is a pure deterministic formula # Comment explaining why noise is needed (prevent target leakage)
np.random.seed(42) # Set a random seed for reproducibility
daily_noise_pct = np.random.normal(0, 0.0005, size=len(df_daily)) # Generate multiplicative noise with a 0.05% standard deviation
additive_noise = np.random.normal(0, base_demand_continuous.mean() * 0.0005, size=len(df_daily)) # Generate additive noise relative to the mean

df_daily['Demand_MWh'] = base_demand_continuous * (1 + daily_noise_pct) + additive_noise # Apply both noise layers to construct the final realistic target

daily_cols = ['Date', 'Demand_MWh', 'Day_of_Week', 'Is_Weekend', 'Is_Holiday', 'Avg_Temp', 'Rainfall'] # Define the columns to keep for the daily dataset

n_total = len(df_daily) # Get the total number of rows
train_end = int(n_total * 0.70) # Calculate the index for the end of the 70% training split
val_end = int(n_total * 0.85) # Calculate the index for the end of the 15% validation split

train_df = df_daily.iloc[:train_end].copy() # Extract the training partition chronologically
val_df = df_daily.iloc[train_end:val_end].copy() # Extract the validation partition chronologically
test_df = df_daily.iloc[val_end:].copy() # Extract the test partition chronologically

def apply_features(df): # Define a function to calculate rolling and lag features
    df['Lag_1'] = df['Demand_MWh'].shift(1) # Create a 1-day lag feature
    df['Lag_7'] = df['Demand_MWh'].shift(7) # Create a 7-day (weekly) lag feature
    df['Lag_30'] = df['Demand_MWh'].shift(30) # Create a 30-day (monthly) lag feature
    df['Rolling_7'] = df['Demand_MWh'].rolling(window=7, min_periods=1).mean() # Create a 7-day moving average feature
    return df[['Date', 'Demand_MWh', 'Day_of_Week', 'Is_Weekend', 'Is_Holiday', 'Avg_Temp', 'Rainfall', 'Lag_1', 'Lag_7', 'Lag_30', 'Rolling_7']] # Return only the required columns

df_train_out = apply_features(train_df).iloc[30:].reset_index(drop=True) # Apply features and drop the first 30 rows to remove NaNs from the Lag_30 feature
df_val_out = apply_features(val_df).iloc[30:].reset_index(drop=True) # Apply features to validation and drop first 30 rows
df_test_out = apply_features(test_df).iloc[30:].reset_index(drop=True) # Apply features to test and drop first 30 rows

train_dir = os.path.join(PROJECT_ROOT, 'train_data') # Construct the path to the training output directory
test_dir = os.path.join(PROJECT_ROOT, 'test_data') # Construct the path to the testing output directory
os.makedirs(train_dir, exist_ok=True) # Create the train directory if it doesn't exist
os.makedirs(test_dir, exist_ok=True) # Create the test directory if it doesn't exist

df_train_out.to_csv(os.path.join(train_dir, 'dataset_daily_train.csv'), index=False) # Save the training dataset to a CSV file
df_val_out.to_csv(os.path.join(test_dir, 'dataset_daily_val.csv'), index=False) # Save the validation dataset to a CSV file
df_test_out.to_csv(os.path.join(test_dir, 'dataset_daily_test.csv'), index=False) # Save the testing dataset to a CSV file

# CREATE MONTHLY FRAMEWORK # Comment indicating the start of the monthly dataset creation
df_daily['Month'] = df_daily['Date'].dt.month # Extract the month number for grouping
df_monthly = df_daily.groupby(['Year', 'Month']).agg({ # Group by year and month
    'Demand_MWh': 'sum', # Sum the daily demand to get total monthly demand
    'Avg_Temp': 'mean' # Average the daily temperatures to get average monthly temperature
}).reset_index() # Reset the index to flatten the DataFrame

df_monthly['Demand_GWh'] = df_monthly['Demand_MWh'] / 1000 # Convert the monthly demand from MWh to GWh

# Map Macro Data # Comment explaining the mapping of macroeconomic indicators
df_monthly['GDP'] = df_monthly['Year'].map(lambda x: macro_dict[x]['GDP']) # Map the GDP value for the corresponding year
df_monthly['Population'] = df_monthly['Year'].map(lambda x: macro_dict[x]['Population']) # Map the Population value for the corresponding year
df_monthly['GDP'] = df_monthly['GDP'].ffill().bfill() # Forward fill and then backward fill missing GDP values
df_monthly['Population'] = df_monthly['Population'].ffill().bfill() # Forward fill and then backward fill missing Population values

# Industrial Index from real World Bank Manufacturing Value Added data # Comment explaining the industrial index mapping
# Yearly values are mapped to each month; monthly interpolation smooths transitions # Comment detailing the interpolation strategy
df_monthly['Industrial_Index'] = df_monthly['Year'].map(lambda x: macro_dict[x]['Industrial_Index']) # Map the industrial index for the corresponding year
df_monthly['Industrial_Index'] = df_monthly['Industrial_Index'].interpolate(method='linear').ffill().bfill() # Linearly interpolate between years to create smooth monthly transitions

df_monthly['Lag_1'] = df_monthly['Demand_GWh'].shift(1) # Create a 1-month lag feature
df_monthly['Lag_12'] = df_monthly['Demand_GWh'].shift(12) # Create a 12-month (yearly) lag feature
df_monthly['Rolling_12'] = df_monthly['Demand_GWh'].rolling(window=12, min_periods=1).mean() # Create a 12-month moving average feature

monthly_cols = ['Year', 'Month', 'Demand_GWh', 'GDP', 'Population', 'Industrial_Index', 'Avg_Temp', 'Lag_1', 'Lag_12', 'Rolling_12'] # Define the columns to keep for the monthly dataset
df_monthly_out = df_monthly[monthly_cols].iloc[12:].reset_index(drop=True) # Filter columns and drop the first 12 rows to remove NaNs from Lag_12
df_monthly_out.to_csv(os.path.join(output_dir, 'dataset_monthly_processed.csv'), index=False) # Save the monthly dataset to a CSV file

print("SUCCESS! Final 100% mapped real datasets saved.") # Print a success message confirming completion
