
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from utils.plotting import apply_plot_theme
from utils.area_selector import select_reservoir_area
from utils.analysis import sliding_window_correlation
from utils.reservoir import load_reservoir_data
from utils.weather import (
    load_coordinates,
    get_area_coordinates,
    get_weather_data,
)

# Dashboard colors
BLUE = "#1676C1"
GREEN = "#348D73"
YELLOW = "#D39A35"

st.title("Meteorology and Reservoir Correlation")

st.write(
    "Explore how the correlation between meteorological conditions "
    "and reservoir filling changes over time."
)


# --------------------------------------------------
# LOAD RESERVOIR DATA
# --------------------------------------------------

url = (
    "https://biapi.nve.no/magasinstatistikk/api/"
    "Magasinstatistikk/HentOffentligData"
)

try:
    df_nve = load_reservoir_data(url)
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()

area_type, area_number = select_reservoir_area()


# --------------------------------------------------
# USER CONTROLS
# --------------------------------------------------

period = st.selectbox(
    "Analysis period",
    ["3 months", "6 months", "1 year", "3 years"],
    index=1,
)

weather_property = st.selectbox(
    "Weather property",
    ["Temperature", "Precipitation"],
)

lag = st.slider(
    "Lag (weeks)",
    min_value=0,
    max_value=12,
    value=0,
)

window_length = st.slider(
    "Rolling window (weeks)",
    min_value=4,
    max_value=52,
    value=12,
)

st.caption(
    "Lag specifies how many weeks earlier the weather is observed "
    "relative to reservoir filling."
)


# --------------------------------------------------
# PREPARE RESERVOIR DATA
# --------------------------------------------------

reservoir = df_nve[
    (df_nve["Area type"] == area_type)
    & (df_nve["Area number"] == area_number)
].copy()

if reservoir.empty:
    st.warning("No reservoir data available for this area.")
    st.stop()

reservoir["date"] = pd.to_datetime(
    reservoir["Iso year"].astype(str)
    + "-W"
    + reservoir["Iso week"].astype(str).str.zfill(2)
    + "-1",
    format="%G-W%V-%u",
)

reservoir = (
    reservoir.groupby("date", as_index=False)["Filling level"]
    .mean()
    .sort_values("date")
)


# --------------------------------------------------
# SELECT ANALYSIS PERIOD
# --------------------------------------------------

period_mapping = {
    "3 months": 3,
    "6 months": 6,
    "1 year": 12,
    "3 years": 36,
}

# Last available reservoir week
last_week = reservoir["date"].max()

# End of last available week
end = last_week + pd.Timedelta(days=6)

# Start of selected period
start = end - pd.DateOffset(
    months=period_mapping[period]
)

# Include the full ISO week containing the start date
start = start - pd.Timedelta(days=start.weekday())

start_date = start.date().isoformat()
end_date = end.date().isoformat()

# Filter reservoir data to the selected period
reservoir = reservoir[
    reservoir["date"] >= start
].copy()


# --------------------------------------------------
# LOAD WEATHER COORDINATES
# --------------------------------------------------

try:
    el_coordinates = load_coordinates("el_coordinates.json")
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()
try:
    nve_coordinates = load_coordinates("nve_coordinates.json")
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()

coordinates = get_area_coordinates(
    area_type=area_type,
    area_number=area_number,
    el_coordinates=el_coordinates,
    nve_coordinates=nve_coordinates,
)

# Limit to a maximum of 100 coordinates.
# The same coordinates are used for both weather variables.
coordinates = coordinates[
    ::max(1, (len(coordinates) + 99) // 100)
][:100]

if not coordinates:
    st.warning(
        "No weather coordinates available for this area."
    )
    st.stop()


# --------------------------------------------------
# DOWNLOAD AND PREPARE WEEKLY WEATHER DATA
# --------------------------------------------------

@st.cache_data(show_spinner=False)
def load_weekly_weather(
    area_type: str,
    area_number: int,
    coordinates: tuple,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Download weather data and aggregate observations by ISO week."""

    region = f"{area_type} {area_number}"

    weather = get_weather_data(
        region=region,
        start_date=start_date,
        end_date=end_date,
        region_coordinates={
            region: list(coordinates)
        },
    )

    if weather.empty:
        return pd.DataFrame()

    weather = weather.copy()
    weather["date"] = pd.to_datetime(weather["date"])

    iso = weather["date"].dt.isocalendar()

    weather["Iso year"] = iso.year.astype(int)
    weather["Iso week"] = iso.week.astype(int)

    weekly = (
        weather.groupby(
            ["Iso year", "Iso week"],
            as_index=False,
        )
        .agg(
            Temperature=("temperature_2m", "mean"),
            Precipitation=("precipitation", "sum"),
        )
    )

    weekly["date"] = pd.to_datetime(
        weekly["Iso year"].astype(str)
        + "-W"
        + weekly["Iso week"].astype(str).str.zfill(2)
        + "-1",
        format="%G-W%V-%u",
    )

    return weekly.sort_values("date")


# --------------------------------------------------
# DOWNLOAD BUTTON
# --------------------------------------------------

coordinate_tuple = tuple(
    tuple(coord) for coord in coordinates
)

cache_key = (
    area_type,
    area_number,
    start_date,
    end_date,
    coordinate_tuple,
)

if st.button(
    "Download weather data",
    type="primary",
):
    with st.spinner("Downloading weather data..."):
        try:
            weekly_weather = load_weekly_weather(
                area_type=area_type,
                area_number=area_number,
                coordinates=coordinate_tuple,
                start_date=start_date,
                end_date=end_date,
            )

            st.session_state[
                "correlation_weather"
            ] = weekly_weather

            st.session_state[
                "correlation_weather_key"
            ] = cache_key

        except Exception as error:
            st.error(
                f"Weather download failed: {error}"
            )
            st.stop()


# Check whether the downloaded data matches the selection
if (
    st.session_state.get("correlation_weather_key")
    != cache_key
):
    st.info(
        "Download weather data to start the analysis."
    )
    st.stop()

weekly_weather = st.session_state[
    "correlation_weather"
]

if weekly_weather.empty:
    st.warning("No weather data available.")
    st.stop()


# --------------------------------------------------
# MERGE WEEKLY DATA
# --------------------------------------------------

df = pd.merge(
    reservoir,
    weekly_weather[
        ["date", "Temperature", "Precipitation"]
    ],
    on="date",
    how="inner",
)

if df.empty:
    st.warning(
        "No overlapping reservoir and weather observations."
    )
    st.stop()

# Create a continuous weekly DatetimeIndex.
# Keep the date as the index for sliding_window_correlation().
df = (
    df.set_index("date")
    .sort_index()
    .asfreq("W-MON")
)


# --------------------------------------------------
# CHECK DATA AVAILABILITY
# --------------------------------------------------

if len(df) < window_length + lag:
    st.warning(
        "Not enough data for the selected window and lag. "
        "Try a longer analysis period or a smaller window."
    )
    st.stop()

# Check for enough valid observations.
valid_pairs = df[
    ["Filling level", weather_property]
].dropna()

if len(valid_pairs) < window_length:
    st.warning(
        "Not enough valid observations to calculate correlation. "
        "Try a longer analysis period or check for missing data."
    )
    st.stop()


# --------------------------------------------------
# CALCULATE SLIDING WINDOW CORRELATION
# --------------------------------------------------

result = sliding_window_correlation(
    data=df,
    weather_column=weather_property,
    window=window_length,
    lag=lag,
)

# Convert DatetimeIndex back to a column for Plotly
result = result.reset_index()

if result.empty:
    st.warning(
        "No correlation results were calculated."
    )
    st.stop()

if result["correlation"].dropna().empty:
    st.warning(
        "No valid correlations could be calculated. "
        "Try a longer analysis period, a smaller window, "
        "or a different lag."
    )
    st.stop()



# --------------------------------------------------
# CREATE PLOTLY FIGURE
# --------------------------------------------------

fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.08,
    subplot_titles=(
        "Reservoir filling",
        weather_property,
        "Sliding Window Correlation",
    ),
)

# Reservoir filling - Blue
fig.add_trace(
    go.Scatter(
        x=result["date"],
        y=result["Filling level"],
        mode="lines",
        name="Reservoir filling",
        line=dict(color=BLUE, width=2.5),
    ),
    row=1,
    col=1,
)

# Weather - Green
fig.add_trace(
    go.Scatter(
        x=result["date"],
        y=result[weather_property],
        mode="lines",
        name=weather_property,
        line=dict(color=GREEN, width=2.5),
    ),
    row=2,
    col=1,
)

# Sliding window correlation - Yellow
fig.add_trace(
    go.Scatter(
        x=result["date"],
        y=result["correlation"],
        mode="lines",
        name="SWC",
        line=dict(color=YELLOW, width=2.5),
    ),
    row=3,
    col=1,
)

# Zero reference line
fig.add_hline(
    y=0,
    line_dash="dash",
    line_color="#7A8B99",
    row=3,
    col=1,
)

# Axis labels
fig.update_yaxes(
    title_text="Filling level",
    row=1,
    col=1,
)

fig.update_yaxes(
    title_text=weather_property,
    row=2,
    col=1,
)

fig.update_yaxes(
    title_text="Correlation",
    range=[-1, 1],
    row=3,
    col=1,
)

fig.update_xaxes(
    title_text="Date",
    row=3,
    col=1,
)

fig.update_layout(
    height=850,
    hovermode="x unified",
    showlegend=False,
    title=(
        f"Sliding Window Correlation — "
        f"{area_type} {area_number}"
        f" | Period: {period}"
        f" | Lag: {lag} weeks"
        f" | Window: {window_length} weeks"
    ),
)

# Apply consistent theme
fig = apply_plot_theme(fig)

st.plotly_chart(
    fig,
    width="stretch",
)

# --------------------------------------------------
# SUMMARY STATISTICS
# --------------------------------------------------

st.subheader("Correlation Summary")

valid_correlations = result[
    "correlation"
].dropna()

if not valid_correlations.empty:

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Mean correlation",
        f"{valid_correlations.mean():.3f}",
    )

    col2.metric(
        "Minimum correlation",
        f"{valid_correlations.min():.3f}",
    )

    col3.metric(
        "Maximum correlation",
        f"{valid_correlations.max():.3f}",
    )

else:
    st.warning(
        "No valid correlations could be calculated."
    )
