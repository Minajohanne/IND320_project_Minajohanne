"""Load regional coordinates and download hourly ERA5 weather observations."""

import json
import time
from pathlib import Path

import numpy as np
import openmeteo_requests
import pandas as pd
import requests
import requests_cache
import streamlit as st
from openmeteo_requests.Client import OpenMeteoRequestsError
from retry_requests import retry


# Load saved coordinates for the weather regions.
def load_coordinates(filename: str) -> dict:
    """Load and validate sampled longitude/latitude pairs from a JSON file."""
    file_path = Path(__file__).resolve().parent.parent / "data" / filename
    try:
        with file_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
    except FileNotFoundError as exc:
        raise ValueError(f"Coordinate file '{filename}' was not found.") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read coordinate file '{filename}'.") from exc

    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"Coordinate file '{filename}' has no regions.")

    coordinates = {}
    for key, points in raw.items():
        if not isinstance(key, str) or not isinstance(points, list) or not points:
            raise ValueError(f"Invalid region or empty coordinates in '{filename}'.")
        region = key.replace("RÃ˜", "RØ").replace("RÃ\x98", "RØ")
        cleaned = []
        for point in points[:100]:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError(f"Invalid coordinate pair in region '{region}'.")
            try:
                lon, lat = float(point[0]), float(point[1])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Non-numeric coordinate in region '{region}'.") from exc
            if not (np.isfinite(lon) and np.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError(f"Coordinates out of range in region '{region}'.")
            cleaned.append((lon, lat))
        coordinates[region] = cleaned
    return coordinates


# Find coordinates belonging to the selected reservoir area.
def get_area_coordinates(
    area_type: str,
    area_number: int,
    el_coordinates: dict[str, list[tuple[float, float]]],
    nve_coordinates: dict[str, list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    """Return sampled coordinates for the selected reservoir area."""
    if area_type == "EL":
        regions, source = [f"NO {area_number}"], el_coordinates
    elif area_type == "NO" and area_number == 0:
        regions, source = list(el_coordinates), el_coordinates
    elif area_type == "VASS":
        vass_regions = {1: ["RS", "RØ"], 2: ["RV"], 3: ["RM", "RN"]}
        if area_number not in vass_regions:
            raise ValueError(f"Unknown reservoir area: VASS {area_number}.")
        regions, source = vass_regions[area_number], nve_coordinates
    else:
        raise ValueError(f"Unknown area: {area_type} {area_number}.")

    missing = [region for region in regions if region not in source]
    if missing:
        raise ValueError(f"Missing coordinates for regions: {', '.join(missing)}.")
    coordinates = [point for region in regions for point in source[region]]
    if not coordinates:
        raise ValueError(f"No coordinates available for {area_type} {area_number}.")
    return coordinates


# Download and combine weather observations for the selected region.
@st.cache_data
def get_weather_data(
    region: str,
    start_date: str,
    end_date: str,
    region_coordinates: dict[str, list[tuple[float, float]]],
) -> pd.DataFrame:
    """Download hourly ERA5 temperature (°C) and precipitation (mm).

    Each timestamp is averaged across sampled locations. Precipitation
    therefore represents mean regional hourly precipitation, not its sum.
    """
    if region not in region_coordinates or not region_coordinates[region]:
        raise ValueError(f"No coordinates available for region '{region}'.")
    try:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid weather dates. Use YYYY-MM-DD format.") from exc
    if start > end:
        raise ValueError("Start date cannot be after end date.")

    coordinates = region_coordinates[region]
    for point in coordinates:
        if len(point) != 2:
            raise ValueError(f"Invalid coordinate pair for region '{region}'.")
    lon = [float(point[0]) for point in coordinates]
    lat = [float(point[1]) for point in coordinates]
    if not all(np.isfinite(lon + lat)) or any(not -180 <= x <= 180 for x in lon) or any(not -90 <= x <= 90 for x in lat):
        raise ValueError(f"Invalid latitude or longitude for region '{region}'.")

    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://archive-api.open-meteo.com/v1/archive"
    dataframes = []
    batch_size = 100
    max_retries = 5

    for i in range(0, len(lat), batch_size):
        params = {
            "latitude": lat[i:i + batch_size],
            "longitude": lon[i:i + batch_size],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ["temperature_2m", "precipitation"],
            "models": "era5",
        }
        for attempt in range(max_retries):
            try:
                responses = openmeteo.weather_api(url, params=params)
                break
            except OpenMeteoRequestsError as exc:
                message = str(exc).lower()
                if "minute" in message and "limit" in message:
                    if attempt < max_retries - 1:
                        print(f"Open-Meteo minute limit reached; waiting 60 s ({attempt + 1}/{max_retries})")
                        time.sleep(60)
                        continue
                    raise RuntimeError("Open-Meteo minute request limit reached. Please try again later.") from exc
                if "hourly" in message and "limit" in message:
                    raise RuntimeError("Open-Meteo hourly API limit reached. Please try again in about one hour.") from exc
                if "daily" in message and "limit" in message:
                    raise RuntimeError("Open-Meteo daily API limit reached. Please try again later.") from exc
                if "503" in message or "overloaded" in message:
                    raise RuntimeError("Open-Meteo is overloaded. Please try again later.") from exc
                raise RuntimeError("Open-Meteo could not provide weather data for the selected period.") from exc
            except requests.exceptions.RequestException as exc:
                raise RuntimeError("Could not connect to Open-Meteo. Please check your connection.") from exc
        else:
            raise RuntimeError("Open-Meteo request failed after multiple attempts.")

        if not responses:
            raise ValueError(f"Open-Meteo returned no weather data for region '{region}'.")

        for response in responses:
            try:
                hourly = response.Hourly()
                temperature = hourly.Variables(0).ValuesAsNumpy()
                precipitation = hourly.Variables(1).ValuesAsNumpy()
                dates = pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left",
                )
            except (AttributeError, IndexError, TypeError, ValueError) as exc:
                raise ValueError("Open-Meteo returned incomplete hourly weather data.") from exc
            if len(dates) != len(temperature) or len(dates) != len(precipitation):
                raise ValueError("Open-Meteo returned inconsistent weather timestamps and values.")
            dataframes.append(pd.DataFrame({
                "date": dates,
                "temperature_2m": temperature,
                "precipitation": precipitation,
            }))
        print(f"Downloaded {min(i + batch_size, len(lat))}/{len(lat)} locations")

    if not dataframes:
        raise ValueError("No weather observations were downloaded.")
    weather_data = pd.concat(dataframes, ignore_index=True)
    regional_average = (
        weather_data.groupby("date")[["temperature_2m", "precipitation"]]
        .mean()
        .reset_index()
    )
    if regional_average.empty:
        raise ValueError("No weather observations are available for the selected period.")
    return regional_average
