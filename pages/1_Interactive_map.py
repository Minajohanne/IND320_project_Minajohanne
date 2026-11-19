
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from datetime import date, timedelta

from utils.map import load_geojson, create_vass_geojson
from utils.reservoir import load_reservoir_data
from utils.weather import load_coordinates, get_weather_data


st.title("Interactive Map")

st.write(
    "Explore reservoir filling levels and weather conditions "
    "across Norwegian regions."
)

# loading the data 
url = (
    "https://biapi.nve.no/magasinstatistikk/api/"
    "Magasinstatistikk/HentOffentligData"
)

df_nve = load_reservoir_data(url)

# Load geographical data
geojson_el = load_geojson("data/Budområder")
geojson_weather = load_geojson("data/NVE_Region")

# Create VASS geometries
geojson_vass = create_vass_geojson(geojson_weather)


@st.cache_data
def get_weather_map_data(
    start_date: str,
    end_date: str,
    nve_coordinates: dict
) -> pd.DataFrame:
    """Download and aggregate weather data for precipitation regions."""

    results = []

    for region in nve_coordinates:

        df = get_weather_data(
            region=region,
            start_date=start_date,
            end_date=end_date,
            region_coordinates=nve_coordinates
        )

        if df.empty:
            continue

        results.append({
            "REGION": region,
            "Temperature": df["temperature_2m"].mean(),
            "Precipitation": df["precipitation"].sum()
        })

    return pd.DataFrame(
        results,
        columns=["REGION", "Temperature", "Precipitation"]
    )



# select areay type and week 
area_type = st.selectbox(
    "Select area type",
    ["Price area", "Water area", "Weather property"]
)

weeks = (
    df_nve[["Iso year", "Iso week"]]
    .drop_duplicates()
    .sort_values(["Iso year", "Iso week"])
)

week_options = [
    (int(year), int(week))
    for year, week in weeks.itertuples(index=False, name=None)
]

if not week_options:
    st.warning("No reservoir data available.")
    st.stop()

selected_year, selected_week = st.selectbox(
    "Select week",
    options=week_options,
    index=len(week_options) - 1,
    format_func=lambda x: f"{x[0]} - Week {x[1]}"
)



# price area 
if area_type == "Price area":

    map_data = df_nve[
        (df_nve["Area type"] == "EL")
        & (df_nve["Iso year"] == selected_year)
        & (df_nve["Iso week"] == selected_week)
    ].copy()

    map_data["area_id"] = (
        "NO " + map_data["Area number"].astype(str)
    )

    geojson = geojson_el
    feature_id = "properties.budomr"
    color_column = "Filling level"
    area_code = "EL"


# water area 
elif area_type == "Water area":

    map_data = df_nve[
        (df_nve["Area type"] == "VASS")
        & (df_nve["Iso year"] == selected_year)
        & (df_nve["Iso week"] == selected_week)
    ].copy()

    map_data["area_id"] = (
        map_data["Area number"].astype(str)
    )

    geojson = geojson_vass
    feature_id = "properties.area_id"
    color_column = "Filling level"
    area_code = "VASS"



# weather property 
else:

    weather_property = st.selectbox(
        "Select weather property",
        ["Temperature", "Precipitation"]
    )

    # Convert ISO year and week to dates
    start = date.fromisocalendar(
        selected_year,
        selected_week,
        1
    )

    end = start + timedelta(days=6)

    # Load sampled coordinates
    nve_coordinates = load_coordinates(
        "nve_coordinates.json"
    )

    # Download and aggregate weather data
    with st.spinner("Loading weather data..."):
        map_data = get_weather_map_data(
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            nve_coordinates=nve_coordinates
        )

    if not map_data.empty:
        map_data["area_id"] = map_data["REGION"]

    geojson = geojson_weather
    feature_id = "properties.REGION"
    color_column = weather_property
    area_code = "WEATHER"



# create map 
if map_data.empty:
    st.warning(
        "No data available for the selected area type and week."
    )
    st.stop()

fig = px.choropleth_map(
    map_data,
    geojson=geojson,
    locations="area_id",
    featureidkey=feature_id,
    color=color_column,
    color_continuous_scale="Blues",
    opacity=0.6,
    map_style="open-street-map",
    center={"lat": 64, "lon": 12},
    zoom=4,
    hover_name="area_id",
    labels={
        color_column: color_column
    }
)

# Set fixed colour scale for reservoir filling levels
if area_code in ["EL", "VASS"]:
    fig.update_coloraxes(
        cmin=0,
        cmax=1
    )

# Show area outlines
fig.update_traces(
    marker_line_width=1,
    marker_line_color="black"
)


# highlight selected area 
# --------------------------------------------------
# HIGHLIGHT SELECTED AREA
# --------------------------------------------------

selected_area = st.session_state.get("selected_area")
selected_type = st.session_state.get("selected_area_type")

if selected_area is not None and selected_type == area_code:

    # Find the selected area's position in the DataFrame
    locations = map_data["area_id"].astype(str).tolist()

    if str(selected_area) in locations:
        selected_index = locations.index(str(selected_area))

        # Create a separate outline for the selected polygon
        selected_features = [
            feature
            for feature in geojson["features"]
            if str(
                feature["properties"].get(
                    feature_id.split(".")[-1]
                )
            ) == str(selected_area)
        ]

        if selected_features:
            selected_geojson = {
                "type": "FeatureCollection",
                "features": selected_features
            }

            fig.add_trace(
                go.Choroplethmap(
                    geojson=selected_geojson,
                    locations=[str(selected_area)],
                    z=[1],
                    featureidkey=feature_id,
                    colorscale=[
                        [0, "#FFD700"],
                        [1, "#FFD700"]
                    ],
                    marker_opacity=0.15,
                    marker_line_width=5,
                    marker_line_color="#FFD700",
                    showscale=False,
                    hoverinfo="skip"
                )
            )

# map layout 
fig.update_layout(
    height=650,
    margin=dict(
        l=0,
        r=0,
        t=0,
        b=0
    )
)



# display map and save selection 
event = st.plotly_chart(
    fig,
    key=f"interactive_map_{area_code}",
    on_select="rerun",
    selection_mode="points",
    use_container_width=True
)

# Inspect and save selected points
if event.selection.points:

    point = event.selection.points[0]

    clicked_area = point.get("location")

    if clicked_area is not None:

        if (
            clicked_area != st.session_state.get("selected_area")
            or area_code != st.session_state.get("selected_area_type")
        ):
            st.session_state["selected_area"] = clicked_area
            st.session_state["selected_area_type"] = area_code
            st.rerun()



# display selected area 
if st.session_state.get("selected_area_type") == area_code:

    selected_area = st.session_state.get("selected_area")

    if selected_area is not None:
        st.write(f"Selected area: {selected_area}")
