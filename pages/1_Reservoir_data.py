import pandas as pd
import streamlit as st
from utils.reservoir import load_reservoir_data

st.title("Reservoir data table")

url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

dat = load_reservoir_data(url).copy()

# Select area type
selected_area = st.radio(
    "Select area type:",
    options=["EL", "NO", "VASS"],
    horizontal=True
)

# Filter by area type
area_dat = dat[dat["Area type"] == selected_area].copy()

if area_dat.empty:
    st.warning("No data available for the selected area type.")
    st.stop()

# Find the first month in the dataset
first_month_date = area_dat["Date"].min().to_period("M")

# Filter data from the first month
first_month = area_dat[
    area_dat["Date"].dt.to_period("M") == first_month_date
].copy()

# Display data
st.subheader(f"Data from {first_month_date}")

st.dataframe(
    first_month,
    hide_index=True,
    width="stretch"
)

# Numerical measurement variables for line charts
plot_columns = [
    "Filling level",
    "Capacity (TWh)",
    "Stored Energy (TWh)",
    "Filling level previous week",
    "Change in filling level",
]

# Create one row per area number
rows = []

for area_number, group in first_month.groupby("Area number"):
    group = group.sort_values("Date")

    row = {"Area number": area_number}

    for col in plot_columns:
        row[col] = group[col].tolist()

    rows.append(row)

# Create DataFrame
tbl = pd.DataFrame(rows)

st.subheader("Reservoir measurements during the first month")

# Configure line chart columns
column_config = {
    "Area number": "Area number"
}

for col in plot_columns:

    if col == "Capacity (TWh)":
        capacity_max = first_month[col].max()

        column_config[col] = st.column_config.LineChartColumn(
            col,
            y_min=0,
            y_max=max(float(capacity_max) * 1.1, 1.0)
        )

    else:
        column_config[col] = st.column_config.LineChartColumn(
            col
        )
        
# Display table
st.dataframe(
    tbl,
    column_config=column_config,
    hide_index=True,
    width="stretch"
)