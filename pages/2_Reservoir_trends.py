
import pandas as pd
import streamlit as st
import plotly.express as px
from utils.reservoir import load_reservoir_data

st.title("Reservoir Trends")

url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

# Load reservoir data
dat = load_reservoir_data(url).copy()

# Create year-month values
dat["month"] = dat["Date"].dt.to_period("M").astype(str)

# Numerical measurement variables
plot_columns = [
    "Filling level",
    "Capacity (TWh)",
    "Stored Energy (TWh)",
    "Filling level previous week",
    "Change in filling level",
]

# Area descriptions
area_names = {
    "EL": {
        1: "NO1 - South-East",
        2: "NO2 - South-West",
        3: "NO3 - Central Norway",
        4: "NO4 - Northern Norway",
        5: "NO5 - Western Norway",
    },
    "NO": {
        0: "Whole Norway",
    },
    "VASS": {
        1: "Eastern Norway, Agder and parts of Rogaland",
        2: "Western Norway",
        3: "Central Norway and southern Nordland",
    },
}

# Select measurement variable
selected_column = st.selectbox(
    "Select a variable:",
    options=["All columns"] + plot_columns
)

# Restore previously selected area type
if "area_type" not in st.session_state:
    st.session_state["area_type"] = "EL"

# Select area type
selected_area = st.radio(
    "Select area type:",
    options=["EL", "NO", "VASS"],
    horizontal=True,
    key="area_type"
)

# Filter by area type
area_dat = dat[
    dat["Area type"] == selected_area
].copy()

if area_dat.empty:
    st.warning("No data available for the selected area type.")
    st.stop()

# Find available area numbers
area_numbers = sorted(
    area_dat["Area number"].dropna().astype(int).unique()
)

# Preserve the selected number when valid for this area type
previous_number = st.session_state.get("area_number")

if previous_number not in area_numbers:
    st.session_state["area_number"] = area_numbers[0]

# Select area number
selected_area_number = st.selectbox(
    "Select area number:",
    options=area_numbers,
    format_func=lambda number: (
        f"{number} - "
        f"{area_names.get(selected_area, {}).get(number, 'Unknown area')}"
    ),
    key="area_number"
)

# Store the selected area independently of widget state
st.session_state["selected_reservoir_area"] = (
    selected_area,
    int(selected_area_number)
)

# Filter by selected area number
area_dat = area_dat[
    area_dat["Area number"] == selected_area_number
].copy()

# Available months
months = sorted(area_dat["month"].dropna().unique().tolist())

if not months:
    st.warning("No monthly data available for the selected area.")
    st.stop()

# Select month range
start_month, end_month = st.select_slider(
    "Select month range:",
    options=months,
    value=(months[0], months[-1])
)

# Filter by selected month range
filtered_dat = area_dat[
    (area_dat["month"] >= start_month)
    & (area_dat["month"] <= end_month)
].copy()

# Sort data chronologically
filtered_dat = filtered_dat.sort_values("Date")

if filtered_dat.empty:
    st.warning("No data available for the selected interval.")
    st.stop()

# Get area description
area_description = area_names.get(
    selected_area, {}
).get(selected_area_number, "Unknown area")

# Plot all measurement columns
if selected_column == "All columns":

    # Calculate mean values for each date
    plot_data = (
        filtered_dat
        .groupby("Date")[plot_columns]
        .mean()
        .reset_index()
    )

    # Apply min-max scaling
    scaled_dat = plot_data.copy()

    for col in plot_columns:
        col_min = scaled_dat[col].min()
        col_max = scaled_dat[col].max()

        if col_max != col_min:
            scaled_dat[col] = (
                (scaled_dat[col] - col_min)
                / (col_max - col_min)
            )
        else:
            scaled_dat[col] = 0.0

    # Plot scaled measurements
    fig = px.line(
        scaled_dat,
        x="Date",
        y=plot_columns,
        title=f"Scaled reservoir measurements - {area_description}",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Scaled value (0-1)",
        legend_title="Variable",
        template="plotly_white",
    )

else:

    # Plot selected measurement
    fig = px.line(
        filtered_dat,
        x="Date",
        y=selected_column,
        title=f"{selected_column} over time - {area_description}",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_column,
        template="plotly_white",
    )

# Display plot
st.plotly_chart(fig, width="stretch")
