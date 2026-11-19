
import geopandas as gpd
import streamlit as st


@st.cache_data
def load_geojson(path: str) -> dict:
    """
    Read a shapefile and convert it to GeoJSON.

    Args:
        path (str): Path to the shapefile.

    Returns:
        dict: Geographic data in GeoJSON format.
    """
    # Read shapefile
    gdf = gpd.read_file(path)

    # Correct incorrectly encoded region names
    if "REGION" in gdf.columns:
        gdf["REGION"] = (
            gdf["REGION"]
            .str.replace("RÃ˜", "RØ", regex=False)
            .str.replace("RÃ\x98", "RØ", regex=False)
            .str.strip()
        )

    # Convert coordinates to latitude and longitude
    gdf = gdf.to_crs(epsg=4326)

    # Convert to GeoJSON
    return gdf.__geo_interface__


@st.cache_data
def create_vass_geojson(nve_geojson: dict) -> dict:
    """Merge precipitation regions into VASS areas."""

    vass_regions = {
        1: ["RS", "RØ"],
        2: ["RV"],
        3: ["RM", "RN"],
    }

    # Convert GeoJSON to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(
        nve_geojson["features"]
    )

    # Map precipitation regions to VASS area numbers
    region_to_vass = {
        region: area_number
        for area_number, regions in vass_regions.items()
        for region in regions
    }

    gdf["area_id"] = gdf["REGION"].map(region_to_vass)

    # Keep only mapped regions
    gdf = gdf.dropna(subset=["area_id"]).copy()
    gdf["area_id"] = gdf["area_id"].astype(int).astype(str)

    # Merge polygons belonging to the same VASS area
    gdf = gdf.dissolve(by="area_id", as_index=False)

    return gdf.__geo_interface__
