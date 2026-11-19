import pandas as pd
import streamlit as st
import plotly.express as px
from utils.reservoir import load_reservoir_data
from utils.area_selector import select_reservoir_area, area_names

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

# Select measurement variable
selected_column = st.selectbox(
    "Select a variable:",
    options=["All columns"] + plot_columns,
)

# Shared area selector
selected_area, selected_area_number = select_reservoir_area()

# Filter by selected area
area_dat = dat[
    (dat["Area type"] == selected_area)
    & (dat["Area number"] == selected_area_number)
].copy()

if area_dat.empty:
    st.warning("No data available for the selected area.")
    st.stop()

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

area_description = area_names[selected_area][selected_area_number]

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
