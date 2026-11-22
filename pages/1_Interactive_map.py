
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


# Load reservoir data and geographical boundaries
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


# Create geojson for whole norway

@st.cache_data
def create_norway_geojson(geojson_el):
    """Combine EL areas into one Norway geometry."""

    # Convert each electricity area into a Shapely geometry
    geometries = [
        shape(feature["geometry"])
        for feature in geojson_el["features"]
    ]

    # Merge all areas into one geometry for the national map
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


# Download weather data

@st.cache_data(show_spinner=False)
def get_weather_map_data(
    start_date: str,
    end_date: str,
    nve_coordinates: dict,
) -> pd.DataFrame:
    """Download and aggregate weather data for each region."""

    results = []

    # Download weather observations for each precipitation region
    for region in nve_coordinates:

        df = get_weather_data(
            region=region,
            start_date=start_date,
            end_date=end_date,
            region_coordinates=nve_coordinates,
        )

        if df.empty:
            continue

        # Calculate mean temperature and total precipitation for the selected week
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


# Select area type and week

area_type = st.radio(
    "Select area type",
    options=["EL", "VASS", "NO"],
    horizontal=True,
)

# Get available year/week combinations, with the newest first
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

# Keep the selected week available to other pages
st.session_state["selected_map_week"] = (
    selected_year,
    selected_week,
)


# Select colour property

colour_property = st.selectbox(
    "Colour areas by",
    options=[
        "Reservoir filling",
        "Temperature",
        "Precipitation",
    ],
)


# Prepare geojson and area identifiers

# Choose the boundaries and identifiers used to match data to map regions
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


# Prepare map data

# Use reservoir statistics or weather data depending on the selected variable
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

    # Convert the selected ISO week into a date range
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

    # Link electricity and reservoir areas to precipitation regions
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

    # Aggregate weather values for each displayed map area
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


# Check data

if map_data.empty:
    st.warning(
        "No data available for the selected week and property."
    )
    st.stop()

map_data["area_id"] = map_data["area_id"].astype(str)


# Create map

if colour_property == "Temperature":
    colour_scale = "RdBu_r"
else:
    colour_scale = "Blues"

# Create a choropleth map using the selected boundaries and values
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
    labels={color_column: {"Filling level": "Filling level (fraction)", "Temperature": "Temperature (°C)", "Precipitation": "Precipitation (mm)"}.get(color_column, color_column)},
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


# Highlight selected area

# Read the currently selected area from the shared session state
selected_area = st.session_state.get("selected_area")
selected_type = st.session_state.get("selected_area_type")

if (
    selected_area is not None
    and selected_type == area_code
):

    # Find the geographical feature corresponding to the selected area
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

        # Draw a highlighted outline on top of the map
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


# Map layout

fig.update_layout(
    height=650,
    margin=dict(l=0, r=0, t=0, b=0),
)


# Display map

# Display the map and capture clicks on map regions
event = st.plotly_chart(
    fig,
    key=f"interactive_map_{area_code}",
    on_select="rerun",
    selection_mode="points",
    use_container_width=True,
)


# Save selected area

if event.selection.points:

    # Use the first selected map region
    point = event.selection.points[0]
    clicked_area = point.get("location")

    if clicked_area is not None:

        if (
            clicked_area != st.session_state.get("selected_area")
            or area_code != st.session_state.get("selected_area_type")
        ):

            # Save the selected area so other pages can use it
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


# Display selected area

if st.session_state.get("selected_area_type") == area_code:

    selected_area = st.session_state.get("selected_area")

    if selected_area is not None:
        st.write(f"Selected area: {selected_area}")

with st.expander('How to interpret the results'):
    st.markdown('The map shows values for the selected ISO week. Colours indicate relative values across displayed regions; the legend provides the measurement scale. Reservoir filling is a fraction, not a percentage. Weather conditions are regional estimates, and precipitation totals refer to the selected week.')

with st.expander('About the data'):
    st.markdown('Reservoir filling and geographical regions are based on [NVE Magasinstatistikk](https://www.nve.no/energi/energisystem/vannkraft/magasinstatistikk/). Weather data are obtained from [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). Reservoir filling is stored as a fraction (0–1), while temperature is in °C and precipitation is in mm. Weather values are aggregated from sampled locations; these are regional estimates, not measurements at every reservoir.')

# Show the number of regions included in the selected map.
st.caption(f"Data summary: {len(map_data)} mapped area(s) for ISO week {selected_week}, {selected_year}; {int(map_data[color_column].isna().sum())} missing map values.")
