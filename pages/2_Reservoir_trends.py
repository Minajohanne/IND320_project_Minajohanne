import pandas as pd
import streamlit as st
import plotly.express as px
from utils.reservoir import load_reservoir_data

st.title("Reservoir Trends")

url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

dat = load_reservoir_data(url)

# Convert date column and sort
dat["Date"] = pd.to_datetime(dat["Date"])
dat = dat.sort_values("Date")

# Create year-month values for the select_slider
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
    options=["All columns"] + plot_columns
)

# Select area type
selected_area = st.radio(
    "Select area type:",
    options=["EL", "NO", "VASS"],
    horizontal=True
)

# Filter by area type
area_dat = dat[dat["Area type"] == selected_area].copy()

# Available months
months = dat["month"].unique().tolist()

# Select month range
start_month, end_month = st.select_slider(
    "Select month range:",
    options=months,
    value=(months[0], months[-1])
)

# Filter by selected month range
filtered_dat = area_dat[
    (area_dat["month"] >= start_month) &
    (area_dat["month"] <= end_month)
].copy()

# Check if data is available
if filtered_dat.empty:
    st.warning("No data available for the selected interval.")
    st.stop()


# Plot all measurement columns
if selected_column == "All columns":

    # Calculate mean values for each date
    plot_data = (
        filtered_dat
        .groupby("Date")[plot_columns]
        .mean()
        .reset_index()
    )

    # Make a copy for scaling
    scaled_dat = plot_data.copy()

    # Reverse min-max scaling
    for col in plot_columns:
        col_min = scaled_dat[col].min()
        col_max = scaled_dat[col].max()

        scaled_dat[col] = (
            scaled_dat[col] * (col_max - col_min) + col_min
        )

    # Plot scaled measurements together
    fig = px.line(
        scaled_dat,
        x="Date",
        y=plot_columns,
        title=f"Average scaled reservoir measurements ({selected_area})",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Scaled value",
        legend_title="Variable",
        template="plotly_white",
    )

else:

    # Prepare data for plotting each area number separately
    plot_dat = filtered_dat.copy()

    # Treat area numbers as categorical variables
    plot_dat["Area number"] = plot_dat["Area number"].astype(str)

    # Sort by area number and date
    plot_dat = plot_dat.sort_values(["Area number", "Date"])

    # Plot selected measurement for each area number
    fig = px.line(
        plot_dat,
        x="Date",
        y=selected_column,
        color="Area number",
        title=f"{selected_column} over time ({selected_area})",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_column,
        legend_title="Area number",
        template="plotly_white",
    )


# Display plot
st.plotly_chart(fig, width="stretch")