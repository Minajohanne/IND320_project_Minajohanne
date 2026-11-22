
import pandas as pd
import streamlit as st

from utils.reservoir import load_reservoir_data
from utils.area_selector import select_reservoir_area

st.title("Reservoir data table")

selected_area, selected_area_number = select_reservoir_area()


url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

try:
    dat = load_reservoir_data(url).copy()
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()

# Select area type and number

# Filter by selected area type and number
area_dat = dat[
    (dat["Area type"] == selected_area)
    & (dat["Area number"] == selected_area_number)
].copy()

if area_dat.empty:
    st.warning("No data available for the selected area.")
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

with st.expander('How to interpret the results'):
    st.markdown('The first table contains the earliest month available for the selected area. The miniature line charts show how each measurement changes over the available weeks. Filling levels are fractions: 0.5 corresponds to 50%.')

with st.expander('About the data'):
    st.markdown('Reservoir statistics are retrieved from [NVE Magasinstatistikk](https://www.nve.no/energi/energisystem/vannkraft/magasinstatistikk/). Filling level and previous-week filling level are fractions (0–1), capacity and stored energy are in TWh, and changes in filling level are differences between fractions.')

# Summarize the data used in this view.
st.subheader("Data summary")
_summary = first_month
_summary_dates = pd.to_datetime(_summary['Date'], errors="coerce").dropna()
_sum_cols = st.columns(3)
_sum_cols[0].metric("Observations", f"{len(_summary):,}")
_sum_cols[1].metric("Missing values", f"{int(_summary.isna().sum().sum()):,}")
_sum_cols[2].metric("Date range", (f"{_summary_dates.min():%Y-%m-%d} to {_summary_dates.max():%Y-%m-%d}" if not _summary_dates.empty else "N/A"))

st.caption("Mini-chart units: filling level and previous-week filling level (fraction, 0–1); capacity and stored energy (TWh); change in filling level (fraction difference).")
