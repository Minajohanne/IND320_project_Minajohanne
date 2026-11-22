
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from datetime import date, timedelta
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

from utils.geojson import load_geojson, create_vass_geojson
from utils.reservoir import load_reservoir_data
from utils.weather import load_coordinates, get_weather_data


st.title("Interactive Map")

st.write(
    "Explore reservoir filling levels and weather conditions "
    "across Norwegian regions."
)


# --------------------------------------------------
# LOAD DATA
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

try:
    geojson_el = load_geojson("data/Budområder")
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()
try:
    geojson_weather = load_geojson("data/NVE_Region")
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()
geojson_vass = create_vass_geojson(geojson_weather)


# --------------------------------------------------
# CREATE GEOJSON FOR WHOLE NORWAY
# --------------------------------------------------

@st.cache_data
def create_norway_geojson(geojson_el):
    """Combine EL areas into one Norway geometry."""

    geometries = [
        shape(feature["geometry"])
        for feature in geojson_el["features"]
    ]

    norway_geometry = unary_union(geometries)

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"area_id": "0"},
                "geometry": mapping(norway_geometry),
            }
        ],
    }


# --------------------------------------------------
# DOWNLOAD WEATHER DATA
# --------------------------------------------------

@st.cache_data(show_spinner=False)
def get_weather_map_data(
    start_date: str,
    end_date: str,
    nve_coordinates: dict,
) -> pd.DataFrame:
    """Download and aggregate weather data for each region."""

    results = []

    for region in nve_coordinates:

        df = get_weather_data(
            region=region,
            start_date=start_date,
            end_date=end_date,
            region_coordinates=nve_coordinates,
        )

        if df.empty:
            continue

        temperature = df["temperature_2m"].mean()
        precipitation = df["precipitation"].sum(min_count=1)

        if pd.isna(temperature) or pd.isna(precipitation):
            st.warning(
                f"Missing weather data for region {region}. "
                "This region will be excluded from the weather map."
            )
            continue

        results.append(
            {
                "REGION": region,
                "Temperature": temperature,
                "Precipitation": precipitation,
            }
        )

    return pd.DataFrame(
        results,
        columns=["REGION", "Temperature", "Precipitation"],
    )


# --------------------------------------------------
# SELECT AREA TYPE AND WEEK
# --------------------------------------------------

area_type = st.radio(
    "Select area type",
    options=["EL", "VASS", "NO"],
    horizontal=True,
)

weeks = (
    df_nve[["Iso year", "Iso week"]]
    .drop_duplicates()
    .sort_values(
        ["Iso year", "Iso week"],
        ascending=False
    )
)

week_options = [
    (int(year), int(week))
    for year, week in weeks.itertuples(index=False, name=None)
]

selected_year, selected_week = st.selectbox(
    "Select week",
    options=week_options,
    index=0,
    format_func=lambda x: f"{x[0]} - Week {x[1]}",
)

st.session_state["selected_map_week"] = (
    selected_year,
    selected_week,
)


# --------------------------------------------------
# SELECT COLOUR PROPERTY
# --------------------------------------------------

colour_property = st.selectbox(
    "Colour areas by",
    options=[
        "Reservoir filling",
        "Temperature",
        "Precipitation",
    ],
)


# --------------------------------------------------
# PREPARE GEOJSON AND AREA IDENTIFIERS
# --------------------------------------------------

if area_type == "EL":

    geojson = geojson_el
    feature_id = "properties.budomr"
    area_code = "EL"

    area_ids = [
        str(feature["properties"]["budomr"])
        for feature in geojson["features"]
    ]

elif area_type == "VASS":

    geojson = geojson_vass
    feature_id = "properties.area_id"
    area_code = "VASS"

    area_ids = [
        str(feature["properties"]["area_id"])
        for feature in geojson["features"]
    ]

else:

    geojson = create_norway_geojson(geojson_el)
    feature_id = "properties.area_id"
    area_code = "NO"
    area_ids = ["0"]


# --------------------------------------------------
# PREPARE MAP DATA
# --------------------------------------------------

if colour_property == "Reservoir filling":

    map_data = df_nve[
        (df_nve["Area type"] == area_type)
        & (df_nve["Iso year"] == selected_year)
        & (df_nve["Iso week"] == selected_week)
    ].copy()

    if area_type == "EL":
        map_data["area_id"] = (
            "NO " + map_data["Area number"].astype(str)
        )

    else:
        map_data["area_id"] = (
            map_data["Area number"].astype(str)
        )

    color_column = "Filling level"

else:

    weather_property = colour_property

    start_date = date.fromisocalendar(
        selected_year,
        selected_week,
        1,
    )

    end_date = start_date + timedelta(days=6)

    nve_coordinates = load_coordinates(
        "nve_coordinates.json"
    )

    with st.spinner("Loading weather data..."):
        weather_data = get_weather_map_data(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            nve_coordinates=nve_coordinates,
        )

    if weather_data.empty:
        st.warning("No weather data available.")
        st.stop()

    # Weather data is available by precipitation region.
    # Match each map area to the weather regions it covers.

    weather_mapping = {
        "EL": {
            "NO 1": ["RØ"],
            "NO 2": ["RS", "RV"],
            "NO 3": ["RM"],
            "NO 4": ["RN"],
            "NO 5": ["RV"],
        },
        "VASS": {
            "1": ["RS", "RØ"],
            "2": ["RV"],
            "3": ["RM", "RN"],
        },
        "NO": {
            "0": ["RS", "RØ", "RV", "RM", "RN"],
        },
    }

    results = []

    for area_id in area_ids:

        regions = weather_mapping[area_type].get(
            area_id, []
        )

        subset = weather_data[
            weather_data["REGION"].isin(regions)
        ]

        if subset.empty:
            continue

        results.append(
            {
                "area_id": area_id,
                weather_property: subset[
                    weather_property
                ].mean(),
            }
        )

    map_data = pd.DataFrame(
        results,
        columns=["area_id", weather_property],
    )

    color_column = weather_property


# --------------------------------------------------
# CHECK DATA
# --------------------------------------------------

if map_data.empty:
    st.warning(
        "No data available for the selected week and property."
    )
    st.stop()

map_data["area_id"] = map_data["area_id"].astype(str)


# --------------------------------------------------
# CREATE MAP
# --------------------------------------------------

if colour_property == "Temperature":
    colour_scale = "RdBu_r"
else:
    colour_scale = "Blues"

fig = px.choropleth_map(
    map_data,
    geojson=geojson,
    locations="area_id",
    featureidkey=feature_id,
    color=color_column,
    color_continuous_scale=colour_scale,
    opacity=0.6,
    map_style="open-street-map",
    center={"lat": 64, "lon": 12},
    zoom=4,
    hover_name="area_id",
    labels={color_column: color_column},
)

# Fixed colour scale for reservoir filling
if colour_property == "Reservoir filling":
    fig.update_coloraxes(
        cmin=0,
        cmax=1,
    )

# Show geographical outlines
fig.update_traces(
    marker_line_width=1,
    marker_line_color="black",
)


# --------------------------------------------------
# HIGHLIGHT SELECTED AREA
# --------------------------------------------------

selected_area = st.session_state.get("selected_area")
selected_type = st.session_state.get("selected_area_type")

if (
    selected_area is not None
    and selected_type == area_code
):

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
            "features": selected_features,
        }

        fig.add_trace(
            go.Choroplethmap(
                geojson=selected_geojson,
                locations=[str(selected_area)],
                z=[1],
                featureidkey=feature_id,
                colorscale=[
                    [0, "#FFD700"],
                    [1, "#FFD700"],
                ],
                marker_opacity=0.15,
                marker_line_width=5,
                marker_line_color="#FFD700",
                showscale=False,
                hoverinfo="skip",
            )
        )


# --------------------------------------------------
# MAP LAYOUT
# --------------------------------------------------

fig.update_layout(
    height=650,
    margin=dict(l=0, r=0, t=0, b=0),
)


# --------------------------------------------------
# DISPLAY MAP
# --------------------------------------------------

event = st.plotly_chart(
    fig,
    key=f"interactive_map_{area_code}",
    on_select="rerun",
    selection_mode="points",
    use_container_width=True,
)


# --------------------------------------------------
# SAVE SELECTED AREA
# --------------------------------------------------

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

            if area_code == "EL":
                area_number = int(
                    str(clicked_area).replace("NO ", "")
                )
            else:
                area_number = int(clicked_area)

            st.session_state["selected_reservoir_area"] = (
                area_code,
                area_number,
            )

            st.rerun()


# --------------------------------------------------
# DISPLAY SELECTED AREA
# --------------------------------------------------

if st.session_state.get("selected_area_type") == area_code:

    selected_area = st.session_state.get("selected_area")

    if selected_area is not None:
        st.write(f"Selected area: {selected_area}")
