# Norwegian Energy Dashboard

This project was developed as part of the IND320 course. It explores Norwegian reservoir statistics, cross-border electricity flows, and meteorological data using data from NVE, ENTSO-E, Open-Meteo, and Norges Bank.

The project includes Jupyter Notebooks for data collection, processing, and analysis, as well as an interactive Streamlit application for data exploration, visualization, statistical analysis, and forecasting.

## Data Sources

- **NVE (Magasinstatistikk API):** Norwegian reservoir filling levels, storage capacity, and stored energy.
- **ENTSO-E Transparency Platform:** Cross-border electricity flows between Norway and neighboring countries.
- **Open-Meteo:** Historical temperature and precipitation data.
- **Norges Bank:** Economic data used as external variables in forecasting.

## Technologies

- **Python, pandas, NumPy, Matplotlib, and Plotly:** Data processing, statistical analysis, and visualization.
- **PySpark and Cassandra:** Processing and storing electricity flow data.
- **MongoDB:** Storing data used by the Streamlit application.
- **Streamlit:** Interactive web application.
- **Scikit-learn, SciPy, and statsmodels:** Statistical analysis, anomaly detection, and time series modeling.

## Streamlit Application

The application contains eight main pages:

1. **Interactive Map:** Geographical visualization of Norwegian reservoir areas and related energy data.
2. **Reservoir Data:** Interactive tables displaying reservoir statistics.
3. **Reservoir Trends:** Line plots with options to select variables, area types, and time intervals.
4. **Electricity Flows:** Visualizations of electricity imports and exports, including pie charts and interactive line plots.
5. **Reservoir Seasonality:** STL decomposition and spectrogram analysis of reservoir filling levels to explore seasonal patterns and changes over time.
6. **Weather Analysis:** Statistical Process Control (SPC) for identifying precipitation outliers and Local Outlier Factor (LOF) for detecting temperature anomalies.
7. **Reservoir Forecasting:** Time series forecasting of reservoir filling levels, with options to include external variables from Open-Meteo and Norges Bank.
8. **Meteorology–Reservoir Correlation:** Analysis of relationships between meteorological variables and reservoir filling levels, including sliding window correlation.

The application allows users to select reservoir areas and explore data across different time periods.

## Running the Application

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Configure the MongoDB connection in `.streamlit/secrets.toml`:

```toml
mongo_uri = "YOUR_MONGODB_CONNECTION_STRING"
```

Start the Streamlit application:

```bash
streamlit run main.py
```

## Data Sources and References

- [NVE](https://www.nve.no/)
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
- [Open-Meteo](https://open-meteo.com/)
- [Norges Bank](https://www.norges-bank.no/)