import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from utils.weather import (
    load_coordinates,
    get_area_coordinates,
    get_weather_data,
)
from utils.analysis import (
    plot_precipitation_spc,
    plot_temperature_lof,
)
from utils.area_selector import select_reservoir_area


st.title("Weather Outlier and Anomaly Analysis")

st.write(
    "Explore unusual weather observations across Norwegian regions. "
    "SPC (Statistical Process Control) is used to identify precipitation outliers, while LOF (Local Outlier Factor) "
    "detects unusual temperature values."
)

# Load sampled coordinates
@st.cache_data
def load_region_coordinates():
    el = load_coordinates("el_coordinates.json")
    nve = load_coordinates("nve_coordinates.json")
    return el, nve


el_coordinates, nve_coordinates = load_region_coordinates()

# Shared area selector
selected_area, selected_area_number = select_reservoir_area()

# Get area name
area_name = (
    "Whole Norway"
    if selected_area == "NO"
    else f"{selected_area} {selected_area_number}"
)

# Select weather data period
start_date = st.date_input(
    "Start date:",
    value=pd.Timestamp("2024-01-01").date(),
    key="weather_start_date",
)

end_date = st.date_input(
    "End date:",
    value=pd.Timestamp("2024-12-31").date(),
    key="weather_end_date",
)

if start_date > end_date:
    st.error("Start date must be before end date.")
    st.stop()

# Cache downloads for the selected area and dates
@st.cache_data(show_spinner="Downloading weather data...")
def load_weather(
    area_type: str,
    area_number: int,
    start: str,
    end: str,
) -> pd.DataFrame:

    coords = get_area_coordinates(
        area_type=area_type,
        area_number=area_number,
        el_coordinates=load_coordinates("el_coordinates.json"),
        nve_coordinates=load_coordinates("nve_coordinates.json"),
    )

    return get_weather_data(
        coordinates=coords,
        start_date=start,
        end_date=end,
    )


# Download only when requested
if st.button("Download weather data"):
    try:
        weather_data = load_weather(
            selected_area,
            selected_area_number,
            str(start_date),
            str(end_date),
        )

        st.session_state["weather_data"] = weather_data
        st.session_state["weather_selection"] = (
            selected_area,
            selected_area_number,
            str(start_date),
            str(end_date),
        )

    except Exception as e:
        st.error(f"Could not download weather data: {e}")

# Check that stored weather data matches the current selection
current_selection = (
    selected_area,
    selected_area_number,
    str(start_date),
    str(end_date),
)

if (
    "weather_data" not in st.session_state
    or st.session_state.get("weather_selection") != current_selection
):
    st.info("Select an area and period, then download weather data.")
    st.stop()

weather_data = st.session_state["weather_data"].copy()
weather_data["date"] = pd.to_datetime(weather_data["date"])
weather_data = weather_data.sort_values("date").reset_index(drop=True)

st.success(f"Loaded {len(weather_data)} hourly observations.")

# Create tabs
tab1, tab2 = st.tabs(["Outlier / SPC", "Anomaly / LOF"])


# TAB 1: SPC
with tab1:
    st.subheader("Precipitation Outlier Detection (SPC)")

    st.write(
        "Statistical Process Control (SPC) identifies unusual "
        "precipitation values by comparing high-frequency variations "
        "with robust control limits based on the median and MAD."
    )

    cutoff_period = st.slider(
        "Cutoff period (hours):",
        min_value=24,
        max_value=336,
        value=168,
        step=24,
    )

    n_std = st.slider(
        "Number of robust standard deviations:",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.5,
    )

    spc_data = weather_data.dropna(
        subset=["date", "precipitation"]
    ).copy()

    if len(spc_data) < 2:
        st.warning("Not enough precipitation observations.")
    else:
        fig, summary = plot_precipitation_spc(
            spc_data,
            cutoff_frequency=1 / cutoff_period,
            n_std=n_std,
            area_name=area_name,
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("SPC Statistics")
        st.dataframe(summary, hide_index=True)


# TAB 2: LOF
with tab2:
    st.subheader("Temperature Anomaly Detection (LOF)")

    st.write(
        "Local Outlier Factor (LOF) compares each temperature "
        "observation with nearby values in feature space. "
        "Observations with unusually low local density "
        "are classified as anomalies."
    )

    contamination = st.slider(
        "Expected proportion of anomalies:",
        min_value=0.001,
        max_value=0.10,
        value=0.01,
        step=0.001,
        format="%.3f",
    )

    lof_data = weather_data.dropna(
        subset=["date", "temperature_2m"]
    ).copy()

    max_neighbors = min(100, len(lof_data) - 1)

    if max_neighbors < 2:
        st.warning("Not enough temperature observations for LOF.")
    else:
        n_neighbors = st.slider(
            "Number of neighbors:",
            min_value=2,
            max_value=max_neighbors,
            value=min(20, max_neighbors),
        )

        fig, summary = plot_temperature_lof(
            lof_data,
            contamination=contamination,
            n_neighbors=n_neighbors,
            area_name=area_name,
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("LOF Statistics")
        st.dataframe(summary, hide_index=True)
