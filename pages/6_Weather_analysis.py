from utils.plotting import apply_plot_theme
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

selected_area, selected_area_number = select_reservoir_area()


st.write(
    "Explore unusual weather observations across Norwegian regions. "
    "SPC (Statistical Process Control) is used to identify precipitation outliers, while LOF (Local Outlier Factor) "
    "detects unusual temperature values."
)

# Load sampled coordinates
@st.cache_data
# Cache coordinates for the electricity and weather regions.
def load_region_coordinates():
    el = load_coordinates("el_coordinates.json")
    nve = load_coordinates("nve_coordinates.json")
    return el, nve


el_coordinates, nve_coordinates = load_region_coordinates()


# Get area name
area_name = (
    "Whole Norway"
    if selected_area == "NO"
    else f"{selected_area} {selected_area_number}"
)

# Choose the period for weather data.
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

@st.cache_data(show_spinner="Downloading weather data...")
# Download weather observations for the selected area.
def load_weather(
    area_type: str,
    area_number: int,
    start: str,
    end: str,
    el_coordinates: dict,
    nve_coordinates: dict,
) -> pd.DataFrame:

    # Get coordinates for selected area
    coords = get_area_coordinates(
        area_type=area_type,
        area_number=area_number,
        el_coordinates=el_coordinates,
        nve_coordinates=nve_coordinates,
    )

    # Download weather data
    weather_df = get_weather_data(
        region="selected_area",
        start_date=start,
        end_date=end,
        region_coordinates={"selected_area": coords},
    )

    return weather_df

# Only download weather data when the button is clicked.
if st.button("Download weather data"):
    try:
        weather_data = load_weather(
        selected_area,
        selected_area_number,
        str(start_date),
        str(end_date),
        el_coordinates,
        nve_coordinates,
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

# Ensure cached session data matches the current settings.
current_selection = (
    selected_area,
    selected_area_number,
    str(start_date),
    str(end_date),
)


with st.expander('About the data'):
    st.markdown('Historical temperature and precipitation data are obtained from [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). Temperature is in °C and precipitation is in mm. Values are aggregated over sampled coordinates for the selected area; the displayed observations are hourly.')
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

# Separate SPC outlier detection and LOF anomaly detection.
tab1, tab2 = st.tabs(["Outlier / SPC", "Anomaly / LOF"])


# TAB 1: SPC
with tab1:

    st.subheader("Weather Outlier Detection (SPC)")

    st.write(
        "Statistical Process Control (SPC) identifies unusual "
        "weather observations by comparing high-frequency variations "
        "with robust control limits based on the median and MAD."
    )

    # Select weather property
    weather_property = st.selectbox(
        "Select weather property",
        ["Temperature", "Precipitation"],
        index=0,
        key="spc_weather_property"
    )

    weather_column = {
        "Temperature": "temperature_2m",
        "Precipitation": "precipitation"
    }[weather_property]

    # Choose the cutoff period for the SPC analysis.
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
        subset=["date", weather_column]
    ).copy()

    if len(spc_data) < 2:
        st.warning("Not enough weather observations.")
    else:
        try:
            fig, summary = plot_precipitation_spc(
                spc_data,
                cutoff_frequency=1 / cutoff_period,
                n_std=n_std,
                area_name=area_name,
                weather_column=weather_column
            )
    
        except (ValueError, RuntimeError) as error:
            st.warning(f"Analysis unavailable: {error}")
            st.stop()

        fig = apply_plot_theme(fig)


        st.plotly_chart(fig, use_container_width=True)

        st.subheader("SPC Statistics")
        st.dataframe(summary, hide_index=True)



# TAB 2: LOF
with tab2:

    st.subheader("Weather Anomaly Detection (LOF)")

    st.write(
        "Local Outlier Factor (LOF) compares each weather observation "
        "with nearby values in feature space. Observations with "
        "unusually low local density are classified as anomalies."
    )

    # Select weather property
    weather_property = st.selectbox(
        "Select weather property",
        ["Temperature", "Precipitation"],
        index=0,
        key="lof_weather_property"
    )

    weather_column = {
        "Temperature": "temperature_2m",
        "Precipitation": "precipitation"
    }[weather_property]

    # Set the expected fraction of anomalies for LOF.
    contamination = st.slider(
        "Expected proportion of anomalies:",
        min_value=0.001,
        max_value=0.10,
        value=0.01,
        step=0.001,
        format="%.3f"
    )

    # Remove missing observations
    lof_data = weather_data.dropna(
        subset=["date", weather_column]
    ).copy()

    max_neighbors = min(100, len(lof_data) - 1)

    if max_neighbors < 2:
        st.warning(
            "Not enough weather observations for LOF."
        )

    else:
        n_neighbors = st.slider(
            "Number of neighbors:",
            min_value=2,
            max_value=max_neighbors,
            value=min(20, max_neighbors)
        )

        try:
            fig, summary = plot_temperature_lof(
                lof_data,
                contamination=contamination,
                n_neighbors=n_neighbors,
                area_name=area_name,
                weather_column=weather_column
            )
    
        except (ValueError, RuntimeError) as error:
            st.warning(f"Analysis unavailable: {error}")
            st.stop()

        fig = apply_plot_theme(fig)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("LOF Statistics")
        st.dataframe(
            summary,
            hide_index=True
        )

with st.expander('How to interpret the results'):
    st.markdown('**SPC:** Observations beyond robust control limits are flagged as unusual, not necessarily incorrect. **LOF:** Points with lower local density than their neighbours are flagged as anomalies. Results depend on the selected cutoff, threshold, neighbours and contamination.')

with st.expander('About the data'):
    st.markdown('Historical temperature and precipitation data are obtained from [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). Temperature is in °C and precipitation is in mm. Values are aggregated over sampled coordinates for the selected area; the displayed observations are hourly.')

# Summarize the data used in this view.
st.subheader("Data summary")
_summary = weather_data
_summary_dates = pd.to_datetime(_summary['date'], errors="coerce").dropna()
_sum_cols = st.columns(3)
_sum_cols[0].metric("Observations", f"{len(_summary):,}")
_sum_cols[1].metric("Missing values", f"{int(_summary.isna().sum().sum()):,}")
_sum_cols[2].metric("Date range", (f"{_summary_dates.min():%Y-%m-%d} to {_summary_dates.max():%Y-%m-%d}" if not _summary_dates.empty else "N/A"))

st.caption("Temperature: °C; precipitation: mm. SPC frequency uses hours; LOF scores are unitless.")
