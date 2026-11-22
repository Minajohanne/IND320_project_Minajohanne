import geopandas as gpd
import streamlit as st


# Load geographical boundaries from a GeoJSON file.
@st.cache_data
def load_geojson(path: str) -> dict:
    """Read a shapefile and convert it to GeoJSON."""
    try:
        gdf = gpd.read_file(path)
    except (OSError, ValueError) as e:
        raise ValueError(f"Could not read geographic data from '{path}'.") from e
    if gdf.empty or "geometry" not in gdf.columns or gdf.geometry.isna().all():
        raise ValueError("Geographic data contains no valid geometries.")
    if gdf.crs is None:
        raise ValueError("Geographic data has no coordinate reference system (CRS).")
    if "REGION" in gdf.columns:
        gdf["REGION"] = (
            gdf["REGION"].str.replace("RÃ˜", "RØ", regex=False)
            .str.replace("RÃ\x98", "RØ", regex=False).str.strip()
        )
    try:
        gdf = gdf.to_crs(epsg=4326)
    except (ValueError, RuntimeError) as e:
        raise ValueError("Could not transform geographic coordinates to WGS84.") from e
    return gdf.__geo_interface__


# Combine regional boundaries into reservoir area geometries.
@st.cache_data
def create_vass_geojson(nve_geojson: dict) -> dict:
    """Merge precipitation regions into VASS areas."""
    if not isinstance(nve_geojson, dict) or not nve_geojson.get("features"):
        raise ValueError("No precipitation region features available.")
    gdf = gpd.GeoDataFrame.from_features(nve_geojson["features"])
    if "REGION" not in gdf.columns:
        raise ValueError("Missing REGION column in geographic data.")
    vass_regions = {1: ["RS", "RØ"], 2: ["RV"], 3: ["RM", "RN"]}
    region_to_vass = {
        region: area_number
        for area_number, regions in vass_regions.items()
        for region in regions
    }
    gdf["area_id"] = gdf["REGION"].map(region_to_vass)
    gdf = gdf.dropna(subset=["area_id"]).copy()
    if gdf.empty:
        raise ValueError("No precipitation regions match the VASS mapping.")
    gdf["area_id"] = gdf["area_id"].astype(int).astype(str)
    gdf = gdf.dissolve(by="area_id", as_index=False)
    return gdf.__geo_interface__
