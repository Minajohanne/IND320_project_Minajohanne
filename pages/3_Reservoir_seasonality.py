import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from utils.reservoir import load_reservoir_data
from utils.analysis import plot_stl, plot_spectrogram
from utils.area_selector import select_reservoir_area


st.title("Seasonal Analysis")

st.write(
    "Explore seasonal patterns and long-term changes in Norwegian "
    "reservoir filling levels using STL decomposition and spectrogram analysis. "
    "Select an area and time period to investigate."
)

# Load reservoir data
url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
dat = load_reservoir_data(url).copy()


# Shared area selector
selected_area, selected_area_number = select_reservoir_area()

# Filter by selected area
filtered_dat = dat[
    (dat["Area type"] == selected_area)
    & (dat["Area number"] == selected_area_number)
].copy()

if filtered_dat.empty:
    st.warning("No data available for the selected area.")
    st.stop()

filtered_dat = filtered_dat.sort_values("Date")


filtered_dat = filtered_dat.sort_values("Date")

# Select date range
min_date = filtered_dat["Date"].min().date()
max_date = filtered_dat["Date"].max().date()

start_date, end_date = st.slider(
    "Select date range:",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filter by selected date range
filtered_dat = filtered_dat[
    (filtered_dat["Date"].dt.date >= start_date) &
    (filtered_dat["Date"].dt.date <= end_date)
].copy()

filtered_dat = filtered_dat.dropna(subset=["Filling level"])

# Check sufficient data
if len(filtered_dat) < 104:
    st.warning(
        "Please select a longer time period. "
        "At least two years of weekly observations are required."
    )
    st.stop()

# Create tabs
tab1, tab2 = st.tabs(["STL Decomposition", "Spectrogram"])


# TAB 1: STL
with tab1:
    st.subheader("STL Decomposition")

    st.write(
        "STL separates reservoir filling levels into three components: "
        "trend, seasonal and residual. The trend represents long-term changes, "
        "the seasonal component shows recurring annual patterns, "
        "and the residual captures remaining variation."
    )

    seasonal = st.slider(
        "Seasonal smoother length:",
        min_value=7,
        max_value=51,
        value=13,
        step=2
    )

    trend = st.slider(
        "Trend smoother length:",
        min_value=55,
        max_value=209,
        value=105,
        step=2
    )

    robust = st.checkbox(
        "Use robust fitting",
        value=True
    )

    fig = plot_stl(
        filtered_dat,
        seasonal=seasonal,
        trend=trend,
        robust=robust
    )

    st.plotly_chart(fig, use_container_width=True)  


# TAB 2: Spectrogram
with tab2:
    st.subheader("Spectrogram")

    st.write(
        "The spectrogram shows how the frequency content of reservoir "
        "filling levels changes over time. The color intensity represents "
        "the magnitude of different frequency components."
    )

    nperseg = st.slider(
        "Window length (weeks):",
        min_value=26,
        max_value=min(208, len(filtered_dat)),
        value=min(104, len(filtered_dat))
    )

    noverlap = st.slider(
        "Overlap (weeks):",
        min_value=0,
        max_value=nperseg - 1,
        value=min(52, nperseg - 1)
    )

    fig = plot_spectrogram(
        filtered_dat,
        nperseg=nperseg,
        noverlap=noverlap
    )

    st.plotly_chart(fig, use_container_width=True)
  
