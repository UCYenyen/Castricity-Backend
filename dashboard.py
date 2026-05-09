import os # Import the os module for interacting with the operating system, like handling file paths
import streamlit as st # Import streamlit for building the interactive web dashboard interface
import pandas as pd # Import pandas for fast and efficient data manipulation and analysis
import plotly.graph_objects as go # Import plotly for creating interactive and dynamic charts
import matplotlib.pyplot as plt # Import matplotlib for static plotting (used specifically for Prophet components)
import joblib # Import joblib for loading the pre-trained machine learning models efficiently
import shap # Import shap to generate Explainable AI (XAI) feature attributions
import holidays # Import the holidays library to automatically detect national holidays
from prophet import Prophet # Import Prophet to support the loaded baseline model operations

st.set_page_config(page_title="Electricity Demand XAI Dashboard", layout="wide") # Configure the Streamlit page title and set it to wide mode for better visualization
st.title("⚡ Grid Demand Forecasting & Anomaly Detection") # Display the main title of the dashboard
st.markdown("*Hybrid Architecture: Prophet (Baseline) + LightGBM (Residuals) + Isolation Forest (Anomaly)*") # Display a subtitle explaining the underlying architecture

script_dir = os.path.dirname(os.path.abspath(__file__)) # Get the absolute path to the directory containing this script
models_dir = os.path.join(script_dir, 'Models') # Construct the path to the 'Models' folder
data_path = os.path.join(script_dir, 'Outputs', 'dataset_daily_with_predictions.csv') # Construct the path to the historical predictions CSV file
xai_candidates = [ # Define a list of potential paths for the pre-computed SHAP summary plot
    os.path.join(script_dir, 'Outputs', 'fig4_shap_summary.png'), # Primary expected path
    os.path.join(script_dir, 'output_xai.png'), # Fallback expected path
] # Close the list definition

@st.cache_resource # Use Streamlit's caching decorator to keep loaded models in memory across reruns
def load_models(_prophet_mtime, _lgbm_mtime, _iso_mtime): # Define a function to load the three core models, taking file modification times to invalidate cache if they change
    prophet_model = joblib.load(os.path.join(models_dir, 'prophet_model.joblib')) # Load the trained Prophet baseline model from disk
    lgbm_model = joblib.load(os.path.join(models_dir, 'lgbm_model.joblib')) # Load the trained LightGBM residual model from disk
    iso_forest = joblib.load(os.path.join(models_dir, 'iso_forest.joblib')) # Load the trained Isolation Forest anomaly detector from disk
    return prophet_model, lgbm_model, iso_forest # Return the loaded model objects

@st.cache_data # Use Streamlit's data caching decorator to keep the loaded dataframe in memory
def load_and_prep_data(_data_mtime): # Define a function to load historical data, invalidating cache if the file changes
    df = pd.read_csv(data_path) # Read the historical predictions CSV into a Pandas DataFrame
    df['Date'] = pd.to_datetime(df['Date']) # Convert the 'Date' column from string to proper datetime objects
    return df # Return the prepared DataFrame

try: # Start a try block to handle potential missing model files gracefully
    prophet_path = os.path.join(models_dir, 'prophet_model.joblib') # Get the full path to the Prophet model file
    lgbm_path = os.path.join(models_dir, 'lgbm_model.joblib') # Get the full path to the LightGBM model file
    iso_path = os.path.join(models_dir, 'iso_forest.joblib') # Get the full path to the Isolation Forest model file

    prophet_model, lgbm_model, iso_forest = load_models( # Call the cached loading function
        os.path.getmtime(prophet_path), # Pass Prophet model's last modification time
        os.path.getmtime(lgbm_path), # Pass LightGBM model's last modification time
        os.path.getmtime(iso_path), # Pass Isolation Forest model's last modification time
    ) # Close the function call
    data_mtime = os.path.getmtime(data_path) # Get the last modification time of the data file
    df = load_and_prep_data(data_mtime) # Call the cached data loading function
except FileNotFoundError as e: # Catch the specific error if any of the required files are missing
    st.error(f"Missing required file: {e}. Please run `Scripts/hybrid_model.py` first.") # Display a user-friendly error message instructing them to train the models
    st.stop() # Halt the Streamlit execution immediately to prevent further errors

st.caption( # Display a small caption text indicating when the artifacts were last updated
    "Loaded artifacts: " # Start the caption string
    f"data={pd.to_datetime(data_mtime, unit='s'):%Y-%m-%d %H:%M:%S}, " # Format and display the data file's timestamp
    f"models={pd.to_datetime(max(os.path.getmtime(prophet_path), os.path.getmtime(lgbm_path), os.path.getmtime(iso_path)), unit='s'):%Y-%m-%d %H:%M:%S}" # Find the most recent model timestamp and display it
) # Close the caption call

# Features must match what the model was trained on (daily dataset only, no macro columns) # Comment explaining the feature list requirement
model_features = [ # Define the exact list of 18 exogenous features used during model training
    'Day_of_Week', 'Is_Weekend', 'Is_Holiday', # Calendar and categorical features
    'Month', 'DayOfYear', 'WeekOfYear', 'Trend', # Temporal and structural features
    'Avg_Temp', 'Rainfall', 'Temp_Lag_1', # Weather and weather-lag features
    'Lag_1', 'Lag_2', 'Lag_7', 'Lag_14', 'Lag_30', # Autoregressive (lagged demand) features
    'Rolling_7', 'Rolling_14', 'Rolling_30', # Rolling average trend features
] # Close the feature list

# Only keep features that actually exist in the loaded data # Comment explaining the next line
available_features = [f for f in model_features if f in df.columns] # Use a list comprehension to dynamically filter out any unexpectedly missing features

df_clean = df.dropna(subset=available_features + ['Demand_MWh', 'Hybrid_Prediction']).copy() # Drop rows containing missing values in crucial columns to ensure clean evaluation
df_clean['Anomaly_Score'] = iso_forest.predict(df_clean[available_features]) # Run the Isolation Forest over historical data to generate anomaly flags (-1 or 1)

feature_dict = { # Define a dictionary mapping technical feature names to human-readable Indonesian labels
    'Day_of_Week': 'Siklus Hari (Day_of_Week)', # Map Day_of_Week
    'Is_Weekend': 'Status Akhir Pekan (Is_Weekend)', # Map Is_Weekend
    'Is_Holiday': 'Status Hari Libur (Is_Holiday)', # Map Is_Holiday
    'Month': 'Bulan (Month)', # Map Month
    'DayOfYear': 'Hari ke-n dalam setahun (DayOfYear)', # Map DayOfYear
    'WeekOfYear': 'Minggu ke-n dalam setahun (WeekOfYear)', # Map WeekOfYear
    'Trend': 'Tren (Trend)', # Map Trend
    'Avg_Temp': 'Suhu Rata-Rata (Avg_Temp)', # Map Avg_Temp
    'Rainfall': 'Curah Hujan (Rainfall)', # Map Rainfall
    'Temp_Lag_1': 'Suhu H-1 (Temp_Lag_1)', # Map Temp_Lag_1
    'Lag_1': 'Beban H-1 (Lag_1)', # Map Lag_1
    'Lag_2': 'Beban H-2 (Lag_2)', # Map Lag_2
    'Lag_7': 'Beban Minggu Lalu (Lag_7)', # Map Lag_7
    'Lag_14': 'Beban 2 Minggu Lalu (Lag_14)', # Map Lag_14
    'Lag_30': 'Beban Bulan Lalu (Lag_30)', # Map Lag_30
    'Rolling_7': 'Tren Rata-rata 7 Hari (Rolling_7)', # Map Rolling_7
    'Rolling_14': 'Tren Rata-rata 14 Hari (Rolling_14)', # Map Rolling_14
    'Rolling_30': 'Tren Rata-rata 30 Hari (Rolling_30)', # Map Rolling_30
} # Close the dictionary

feature_desc = { # Define a dictionary providing detailed business context for each feature
    'Day_of_Week': 'Siklus operasional mingguan (Senin-Minggu) yang membedakan ritme aktivitas masyarakat.', # Describe Day_of_Week
    'Is_Weekend': 'Mengurangi beban dasar secara signifikan karena perkantoran dan pasar tutup.', # Describe Is_Weekend
    'Is_Holiday': 'Penurunan drastis beban listrik akibat libur nasional/tanggal merah secara serentak.', # Describe Is_Holiday
    'Month': 'Perbedaan musiman antar bulan.', # Describe Month
    'DayOfYear': 'Pola tahunan beban yang berulang secara spesifik per harinya.', # Describe DayOfYear
    'WeekOfYear': 'Siklus beban berdasarkan minggu dalam tahun.', # Describe WeekOfYear
    'Trend': 'Indikator pergerakan beban seiring dengan waktu.', # Describe Trend
    'Avg_Temp': 'Suhu harian; suhu tinggi memicu penggunaan AC (Cooling Demand) secara masif.', # Describe Avg_Temp
    'Rainfall': 'Curah hujan memengaruhi visibilitas aktivitas luar ruang dan menekan suhu lokal.', # Describe Rainfall
    'Temp_Lag_1': 'Pengaruh suhu pada hari sebelumnya terhadap beban hari ini.', # Describe Temp_Lag_1
    'Lag_1': 'Inersia konsumsi dari 1 hari sebelumnya (Efek memori jangka pendek jaringan).', # Describe Lag_1
    'Lag_2': 'Inersia konsumsi dari 2 hari sebelumnya.', # Describe Lag_2
    'Lag_7': 'Cerminan historis pola beban pada hari yang sama persis di minggu sebelumnya.', # Describe Lag_7
    'Lag_14': 'Pola dari 2 minggu sebelumnya.', # Describe Lag_14
    'Lag_30': 'Cerminan historis pola beban pada siklus bulanan sebelumnya.', # Describe Lag_30
    'Rolling_7': 'Garis pergerakan rata-rata beban selama seminggu terakhir untuk melihat tren halus.', # Describe Rolling_7
    'Rolling_14': 'Pergerakan rata-rata beban dua minggu.', # Describe Rolling_14
    'Rolling_30': 'Pergerakan rata-rata beban sebulan terakhir.', # Describe Rolling_30
} # Close the description dictionary

tab1, tab2 = st.tabs(["📊 Validasi Sistem (Historis)", "🔮 Future Forecaster & Local XAI"]) # Create two main tabs for the Streamlit UI layout

with tab1: # Open the context block for the first tab (Historical Validation)
    st.header("1. System Validation & Anomaly Detection") # Display the header for the validation section
    anomalies = df_clean[df_clean['Anomaly_Score'] == -1] # Filter the historical dataframe to isolate only the detected anomalies

    total_rows = len(df_clean) # Calculate the total number of historical data points
    anomaly_count = len(anomalies) # Calculate the total number of flagged anomalies
    anomaly_ratio = (anomaly_count / total_rows * 100) if total_rows else 0.0 # Compute the percentage of data flagged as anomalous
    period_start = df_clean['Date'].min() # Find the earliest date in the dataset
    period_end = df_clean['Date'].max() # Find the latest date in the dataset
    period_days = (period_end - period_start).days + 1 if total_rows else 0 # Calculate the total duration in days

    actual_hist = df_clean['Demand_MWh'] # Extract the actual demand column
    hybrid_hist = df_clean['Hybrid_Prediction'] # Extract the hybrid prediction column
    abs_err_hybrid = (actual_hist - hybrid_hist).abs() # Calculate the absolute error for every row
    mae_hybrid = abs_err_hybrid.mean() # Calculate the Mean Absolute Error (MAE) for the hybrid model
    rmse_hybrid = ((actual_hist - hybrid_hist) ** 2).mean() ** 0.5 # Calculate the Root Mean Squared Error (RMSE) for the hybrid model
    non_zero_mask = actual_hist != 0 # Create a boolean mask to prevent division by zero in MAPE calculation
    mape_hybrid = ((abs_err_hybrid[non_zero_mask] / actual_hist[non_zero_mask]).mean() * 100) if non_zero_mask.any() else float('nan') # Calculate the Mean Absolute Percentage Error (MAPE)

    has_prophet_pred = 'Prophet_Pred' in df_clean.columns # Check if Prophet baseline predictions are available in the data
    if has_prophet_pred: # If Prophet predictions exist, calculate its metrics for comparison
        prophet_hist = df_clean['Prophet_Pred'] # Extract Prophet predictions
        abs_err_prophet = (actual_hist - prophet_hist).abs() # Calculate absolute error for Prophet
        mae_prophet = abs_err_prophet.mean() # Calculate MAE for Prophet
        rmse_prophet = ((actual_hist - prophet_hist) ** 2).mean() ** 0.5 # Calculate RMSE for Prophet
        mape_prophet = ((abs_err_prophet[non_zero_mask] / actual_hist[non_zero_mask]).mean() * 100) if non_zero_mask.any() else float('nan') # Calculate MAPE for Prophet

        rmse_gain = ((rmse_prophet - rmse_hybrid) / rmse_prophet * 100) if rmse_prophet != 0 else 0.0 # Calculate percentage improvement in RMSE
        mae_gain = ((mae_prophet - mae_hybrid) / mae_prophet * 100) if mae_prophet != 0 else 0.0 # Calculate percentage improvement in MAE
    else: # If Prophet predictions are missing
        rmse_gain = None # Set improvement to None
        mae_gain = None # Set improvement to None

    st.markdown( # Display introductory text explaining the purpose of Tab 1
        """
        **Tujuan panel historis ini** adalah mengevaluasi apakah sistem bekerja stabil pada data harian aktual.

        Arsitektur yang divalidasi:
        1. **Prophet** memodelkan pola utama jangka panjang (tren + musiman).
        2. **LightGBM** mengoreksi residual Prophet menggunakan variabel eksogen/cuaca + fitur lag.
        3. **Isolation Forest** menandai hari dengan pola fitur yang sangat tidak lazim sebagai anomali.

        Hasil yang perlu diperhatikan:
        - Seberapa dekat garis prediksi ke demand aktual.
        - Seberapa sering muncul anomali relatif terhadap total hari.
        - Seberapa besar error historis (MAE, RMSE, MAPE).
        """
    ) # Close the markdown block

    kpi_1, kpi_2, kpi_3, kpi_4, kpi_5 = st.columns(5) # Create 5 columns for top-level KPI metrics
    kpi_1.metric("Periode Data", f"{period_days:,} hari") # Display total days in data
    kpi_2.metric("Jumlah Observasi", f"{total_rows:,}") # Display total rows
    kpi_3.metric("Anomali Terdeteksi", f"{anomaly_count:,}", delta=f"{anomaly_ratio:.2f}% dari data") # Display anomaly count and ratio
    kpi_4.metric("MAE Hybrid", f"{mae_hybrid:,.0f} MWh") # Display the overall MAE
    kpi_5.metric("RMSE Hybrid", f"{rmse_hybrid:,.0f} MWh") # Display the overall RMSE

    st.markdown( # Display the specific date range evaluated
        f"**Rentang tanggal historis:** {period_start:%d %b %Y} -> {period_end:%d %b %Y}"
    ) # Close the markdown call

    st.caption( # Display a caption with MAPE and comparison against the Prophet baseline
        f"MAPE Hybrid historis: {mape_hybrid:.2f}%" # Show MAPE
        + ( # Conditionally append the improvement metrics if available
            f" | Gain vs Prophet: MAE {mae_gain:.2f}%, RMSE {rmse_gain:.2f}%" # Show performance gain
            if has_prophet_pred else # Check the condition
            " | Kolom Prophet_Pred tidak tersedia, sehingga perbandingan baseline Prophet tidak ditampilkan." # Fallback message
        ) # Close the condition block
    ) # Close the caption call

    fig_main = go.Figure() # Initialize an empty Plotly figure
    fig_main.add_trace(go.Scatter(x=df_clean['Date'], y=df_clean['Demand_MWh'], mode='lines', name='Actual Demand', line=dict(color='blue'))) # Add the solid blue line for Actual Demand
    fig_main.add_trace(go.Scatter(x=df_clean['Date'], y=df_clean['Hybrid_Prediction'], mode='lines', name='Hybrid Prediction', line=dict(color='orange', dash='dash'))) # Add the dashed orange line for Hybrid Prediction
    fig_main.add_trace(go.Scatter( # Add red X markers for detected anomalies
        x=anomalies['Date'], y=anomalies['Demand_MWh'], mode='markers', name='Grid Anomaly Detected', # Specify data and styling
        marker=dict(color='red', size=10, symbol='x', line=dict(color='black', width=1)), # Style the markers as red 'X's
        hovertemplate="<b>Date:</b> %{x}<br><b>Demand:</b> %{y}<extra>Anomaly</extra>" # Customize hover tooltip
    )) # Close the add_trace call
    fig_main.update_layout(height=400, template='plotly_white', hovermode='x unified') # Set layout height, theme, and enable unified hover for easy reading
    st.plotly_chart(fig_main, use_container_width=True) # Render the interactive Plotly chart taking up the full width

    with st.expander("Cara membaca grafik utama (Actual vs Hybrid + Anomali)", expanded=True): # Create a collapsible expander for chart instructions
        st.markdown( # Display the explanation text
            """
            1. **Garis biru (Actual Demand)** adalah beban listrik aktual harian.
            2. **Garis oranye putus-putus (Hybrid Prediction)** adalah hasil prediksi sistem hybrid.
            3. **Marker merah (Grid Anomaly Detected)** adalah hari yang oleh Isolation Forest dianggap tidak normal secara pola fitur.

            Interpretasi praktis:
            - Jika garis oranye menempel pada garis biru, model memiliki error rendah.
            - Jika marker merah muncul berkelompok, kemungkinan ada kejadian sistemik (event besar, gangguan, cuaca ekstrem, atau perubahan pola konsumsi).
            - Tidak semua anomali adalah kesalahan data; sebagian bisa menjadi sinyal operasional penting untuk investigasi.
            """
        ) # Close markdown
    
    col_a, col_b = st.columns(2) # Create a 2-column layout for the lower half of the tab
    with col_a: # Open the left column block
        st.subheader("Prophet Components") # Display subheader
        df_prophet = df_clean[['Date', 'Avg_Temp']].rename(columns={'Date': 'ds'}) # Prepare data format expected by Prophet ('ds' column)
        forecast = prophet_model.predict(df_prophet) # Generate historical Prophet predictions specifically to extract components
        fig_prophet = prophet_model.plot_components(forecast) # Tell Prophet to plot its internal additive components (Trend, Weekly, Yearly)
        st.pyplot(fig_prophet) # Render the Matplotlib figure in Streamlit
        with st.expander("Penjelasan Prophet Components", expanded=False): # Create a collapsible explanation for the Prophet components
            st.markdown( # Display the explanation text
                """
                Plot komponen Prophet menjelaskan dari mana baseline terbentuk:
                1. **Trend**: arah pertumbuhan/penurunan demand jangka panjang.
                2. **Weekly Seasonality**: pola berulang per hari dalam seminggu (hari kerja vs akhir pekan).
                3. **Yearly Seasonality**: pola musiman tahunan.

                Komponen ini belum memuat koreksi residual LightGBM, sehingga dipakai sebagai baseline struktural.
                """
            ) # Close markdown
    with col_b: # Open the right column block
        st.subheader("Global Feature Impact") # Display subheader
        xai_path = next((path for path in xai_candidates if os.path.exists(path)), None) # Find the first valid image path for the pre-computed SHAP plot
        if xai_path: # Check if the image was found
            st.image(xai_path, use_container_width=True) # Display the static SHAP summary plot image
            with st.expander("Penjelasan Global Feature Impact (SHAP)", expanded=False): # Create a collapsible explanation
                st.markdown( # Display the explanation text
                    """
                    Grafik SHAP global merangkum kontribusi fitur terhadap koreksi residual LightGBM.

                    Cara membaca:
                    1. **Sumbu Y**: urutan fitur dari paling berpengaruh ke paling kecil.
                    2. **Sumbu X (SHAP value)**:
                       - Nilai positif mendorong prediksi naik.
                       - Nilai negatif mendorong prediksi turun.
                    3. **Warna titik**:
                       - Warna lebih "panas" menandakan nilai fitur tinggi.
                       - Warna lebih "dingin" menandakan nilai fitur rendah.

                    Nilai bisnis:
                    - Mengidentifikasi pendorong demand utama (mis. suhu, lag konsumsi).
                    - Membantu validasi bahwa perilaku model konsisten dengan logika sistem tenaga.
                    """
                ) # Close markdown
        else: # Execute if the SHAP image is missing
            st.info("No XAI figure found. Run Scripts/hybrid_model.py to generate Outputs/fig4_shap_summary.png.") # Display an informational warning

    with st.expander("Kesimpulan Validasi Historis", expanded=True): # Create a final expander for historical conclusions
        st.markdown( # Display the text
            """
            Checklist cepat sebelum model dipakai operasional:
            1. **Akurasi**: MAE/RMSE/MAPE berada dalam batas toleransi operasional.
            2. **Stabilitas pola**: prediksi tidak sering melenceng besar dari aktual.
            3. **Anomali**: rasio anomali wajar dan dapat dijelaskan secara domain.
            4. **Interpretabilitas**: fitur dominan SHAP masuk akal secara fisik/operasional.

            Jika salah satu poin di atas tidak terpenuhi, lakukan retraining atau audit data (khususnya fitur lag, cuaca, dan label libur).
            """
        ) # Close markdown

with tab2: # Open the context block for the second tab (Future Forecaster & Local XAI)
    st.header("Prediksi Masa Depan & Penjelasan Keputusan (Local XAI)") # Display the main header
    st.markdown("Masukkan input kondisi lingkungan. Sistem otomatis mendeteksi hari libur nasional Indonesia untuk memperkuat presisi prediksi.") # Provide context instructions
    
    col1, col2 = st.columns(2) # Create a 2-column layout for input fields
    
    # Inisialisasi kalender Indonesia # Comment explaining the holiday library usage
    id_holidays = holidays.Indonesia() # Instantiate the Indonesian calendar object from the holidays library

    with col1: # Left column for date-related inputs
        target_date = st.date_input("Pilih Tanggal Prediksi", value=pd.to_datetime("2026-08-17")) # Create a date picker, default to Independence Day 2026
        
        # Auto-deteksi Libur Nasional # Comment for holiday logic
        is_auto_holiday = target_date in id_holidays # Check if the selected date falls on a known national holiday
        holiday_name = id_holidays.get(target_date) if is_auto_holiday else "Hari Kerja/Biasa (Bukan Libur Nasional)" # Retrieve the exact name of the holiday if true
        
        st.info(f"📅 **Deteksi Sistem Kalender:** {holiday_name}") # Display an info box with the auto-detected calendar status
        
        # Opsi override untuk What-If Scenario # Comment for the manual override option
        is_holiday_override = st.checkbox("Paksa hitung sebagai Hari Libur Nasional (Simulasi Manual)", value=is_auto_holiday) # Create a checkbox to allow the user to override the holiday status (useful for simulations)
        is_holiday = 1 if is_holiday_override else 0 # Convert the boolean override state to an integer flag (1 or 0)

    with col2: # Right column for weather-related inputs
        avg_temp = st.number_input("Input Suhu Udara (°C)", min_value=15.0, max_value=45.0, value=28.0, step=0.1, format="%.1f") # Create a number input for Temperature
        rainfall = st.number_input("Input Curah Hujan (mm)", min_value=0.0, max_value=300.0, value=5.0, step=1.0, format="%.1f") # Create a number input for Rainfall
        
    if st.button("Jalankan Prediksi AI 🚀", use_container_width=True): # Create a full-width action button. The block underneath executes only when clicked.
        day_of_week = target_date.weekday() # Calculate the day of the week (0=Mon, 6=Sun)
        is_weekend = 1 if day_of_week >= 5 else 0 # Determine if the date is a weekend
        
        last_known_data = df_clean.iloc[-1] # Retrieve the absolute last row of historical data to use for autoregressive lag imputation
        
        custom_data = pd.DataFrame({ # Construct a single-row DataFrame containing all 18 features required by LightGBM
            'Day_of_Week': [day_of_week], # Input the computed day of week
            'Is_Weekend': [is_weekend], # Input the computed weekend flag
            'Is_Holiday': [is_holiday], # Input the user/auto holiday flag
            'Month': [target_date.month], # Input the month number
            'DayOfYear': [target_date.timetuple().tm_yday], # Calculate and input the day of the year
            'WeekOfYear': [target_date.isocalendar()[1]], # Calculate and input the ISO week number
            'Trend': [(pd.to_datetime(target_date) - pd.Timestamp('2018-01-01')).days], # Calculate continuous days since the start of the dataset for the trend
            'Avg_Temp': [avg_temp], # Input the user-provided temperature
            'Rainfall': [rainfall], # Input the user-provided rainfall
            'Temp_Lag_1': [last_known_data.get('Avg_Temp', avg_temp)], # Impute yesterday's temp using the last known historical temp
            'Lag_1': [last_known_data['Demand_MWh']], # Impute Lag 1 with the last known demand
            'Lag_2': [last_known_data.get('Lag_1', last_known_data['Demand_MWh'])], # Impute Lag 2
            'Lag_7': [last_known_data.get('Lag_7', last_known_data['Demand_MWh'])], # Impute Lag 7
            'Lag_14': [last_known_data.get('Lag_14', last_known_data['Demand_MWh'])], # Impute Lag 14
            'Lag_30': [last_known_data.get('Lag_30', last_known_data['Demand_MWh'])], # Impute Lag 30
            'Rolling_7': [last_known_data.get('Rolling_7', last_known_data['Demand_MWh'])], # Impute 7-day rolling average
            'Rolling_14': [last_known_data.get('Rolling_14', last_known_data['Demand_MWh'])], # Impute 14-day rolling average
            'Rolling_30': [last_known_data.get('Rolling_30', last_known_data['Demand_MWh'])], # Impute 30-day rolling average
        }).astype(float) # Ensure all data types are floats to avoid LightGBM schema errors
        
        prophet_df = pd.DataFrame({'ds': [pd.to_datetime(target_date)], 'Avg_Temp': [avg_temp]}) # Create a minimal dataframe for Prophet inference
        base_demand = prophet_model.predict(prophet_df)['yhat'].values[0] # Ask Prophet to calculate the baseline temporal demand
        weather_residual = lgbm_model.predict(custom_data)[0] # Ask LightGBM to calculate the residual correction based on exogenous variables
        final_demand = base_demand + weather_residual # Combine baseline and residual for the final prediction
        anomaly_flag = iso_forest.predict(custom_data)[0] # Ask the Isolation Forest to check if this input combination is anomalous
        
        explainer = shap.TreeExplainer(lgbm_model) # Initialize the SHAP TreeExplainer specifically targeting the LightGBM model
        shap_vals = explainer.shap_values(custom_data)[0] # Calculate the localized Shapley values for this exact single prediction
        
        feature_impacts = list(zip(available_features, shap_vals)) # Combine the feature names with their computed SHAP values into a list of tuples
        feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True) # Sort the list by absolute SHAP value (magnitude of impact), descending
        top_3_impacts = feature_impacts[:3] # Slice the top 3 most influential features
        
        st.divider() # Draw a visual separator
        st.success(f"### ⚡ Hasil Prediksi: {final_demand:,.0f} MWh") # Display the final numerical prediction prominently
        st.write(f"*(Baseline Tren: {base_demand:,.0f} MWh | Penyesuaian AI: {weather_residual:+,.0f} MWh)*") # Break down the math showing how the hybrid components sum up
        
        if anomaly_flag == -1: # Check the anomaly flag
            st.error("🚨 **Peringatan:** Kombinasi fitur pada hari ini terdeteksi sebagai Anomali Jaringan ekstrem (Black-Swan Event).") # Display a critical alert if an anomaly is detected
            
        st.subheader("1. Narasi Eksekutif (Top 3 Faktor Penentu)") # Display subheader for the natural language narration
        status_arah = "TINGGI" if final_demand > base_demand else "RENDAH" # Determine if LightGBM pushed the final prediction higher or lower than the baseline
        st.markdown(f"Pada tanggal **{target_date.strftime('%d %B %Y')}**, prediksi model lebih **{status_arah}** dibandingkan tren baseline. 3 pendorong utamanya adalah:") # Print the contextual intro sentence
        
        for i, (feat, impact) in enumerate(top_3_impacts): # Loop through the top 3 features
            direction_text = "Meningkatkan Prediksi (Positif 📈)" if impact > 0 else "Menurunkan Prediksi (Negatif 📉)" # Translate the mathematical sign into human-readable direction
            st.markdown(f"**{i+1}. {feature_dict.get(feat, feat)}** ➔ {direction_text} berdampak **{abs(impact):,.0f} MWh**.") # Print the bullet point with feature name, direction, and magnitude

        st.subheader("2. Grafik Analisis Dampak (Local SHAP Plot)") # Display subheader for the local SHAP bar chart
        plot_data = sorted(feature_impacts, key=lambda x: x[1]) # Re-sort the impacts based on actual value (not absolute) for proper charting
        colors = ['#EF553B' if val < 0 else '#00CC96' for feat, val in plot_data] # Assign red to negative impacts and green to positive impacts
        
        fig_local = go.Figure(go.Bar( # Initialize a Plotly horizontal bar chart
            x=[val for feat, val in plot_data], # Set X-axis to SHAP values
            y=[feature_dict.get(feat, feat) for feat, val in plot_data], # Set Y-axis to localized feature names
            orientation='h', # Make it a horizontal bar chart
            marker_color=colors, # Apply the conditional colors
            text=[f"{val:+,.0f}" for feat, val in plot_data], # Format the text labels with signs (+/-)
            textposition='auto' # Automatically place text inside or outside the bars
        )) # Close the Bar trace
        fig_local.update_layout( # Configure chart aesthetics
            title="Seberapa Besar Setiap Variabel Mengubah Prediksi Hari Ini?", # Set chart title
            xaxis_title="Dampak terhadap Prediksi (MWh)", # Label X-axis
            template='plotly_white', # Apply clean theme
            height=400, # Set chart height
            margin=dict(l=0, r=0, t=40, b=0) # Adjust margins to fit labels
        ) # Close layout config
        st.plotly_chart(fig_local, use_container_width=True) # Render the interactive local XAI chart

        st.subheader("3. Rincian Lengkap Variabel, Nilai Input, dan Artinya") # Display subheader for the data table
        explanation_data = [] # Initialize an empty list to store dictionary rows for the table
        for feat, impact in feature_impacts: # Loop through all calculated features
            actual_val = custom_data[feat].values[0] # Retrieve the actual input value passed to the model
            
            if feat == 'Avg_Temp': val_str = f"{actual_val:.1f} °C" # Format temperature
            elif feat in ['Is_Holiday', 'Is_Weekend']: val_str = "Ya" if actual_val == 1 else "Tidak" # Translate boolean flags to Yes/No
            elif feat == 'Rainfall': val_str = f"{actual_val:.1f} mm" # Format rainfall
            elif feat == 'Day_of_Week': # Handle day of week mapping
                days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"] # Define Indonesian day names
                val_str = days[int(actual_val)] # Map integer to name
            else: val_str = f"{actual_val:,.0f}" # Format everything else (lags, MWh) as standard integers
            
            explanation_data.append({ # Add a new dictionary representing a row to the list
                "Variabel": feature_dict.get(feat, feat), # Localized feature name
                "Nilai Aktual Hari Ini": val_str, # Formatted input value
                "Dampak AI (MWh)": f"{impact:+,.0f}", # Formatted SHAP impact
                "Arti & Efek Fisiknya": feature_desc.get(feat, "") # Extensive business definition
            }) # Close the dictionary
            
        st.table(pd.DataFrame(explanation_data)) # Convert the list of dictionaries to a DataFrame and render it as a static Streamlit table