# Norwegian Energy Dashboard

This project was developed as part of the IND320 course. It explores Norwegian reservoir statistics and cross-border electricity flows using data from NVE and ENTSO-E.

The project includes Jupyter Notebooks for data collection and processing, as well as an interactive Streamlit application for data visualization.

## Data Sources

- **NVE (Magasinstatistikk API):** Norwegian reservoir filling levels, storage capacity, and stored energy.
- **ENTSO-E Transparency Platform:** Cross-border electricity flows between Norway and neighboring countries.

## Technologies

- **Python, pandas and Plotly:** Data processing and visualization.
- **PySpark and Cassandra:** Processing and storing electricity flow data.
- **MongoDB:** Storing electricity flow data for the Streamlit application.
- **Streamlit:** Interactive web application.

## Streamlit Application

The application contains three main pages:

1. **Reservoir Data:** Interactive tables displaying reservoir statistics.
2. **Reservoir Trends:** Line plots with options to select variables, area types, and time intervals.
3. **Power Flows:** Visualizations of electricity imports and exports, including pie charts and interactive line plots.

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

## Data Sources

- [NVE](https://www.nve.no/)
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)