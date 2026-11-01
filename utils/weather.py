
import time
import pandas as pd
import openmeteo_requests
import requests_cache
from openmeteo_requests.Client import OpenMeteoRequestsError
from retry_requests import retry
import json 
from pathlib import Path


def load_coordinates(filename: str) -> dict:
    """Load sampled coordinates from a JSON file."""

    file_path = Path(__file__).resolve().parent.parent / "data" / filename # ?

    with open(file_path, "r", encoding="utf-8") as f:
        coordinates = json.load(f)

    # correct incorrectly encoded region names
    coordinates = {
        key.replace("RÃ˜", "RØ").replace("RÃ\x98", "RØ"): value
        for key, value in coordinates.items()
    } 

    return coordinates

    
def get_area_coordinates(
    area_type: str,
    area_number: int,
    el_coordinates: dict[str, list[tuple[float, float]]],
    nve_coordinates: dict[str, list[tuple[float, float]]]
) -> list[tuple[float, float]]:
    """Return sampled coordinates for the selected reservoir area."""

    if area_type == "EL":
        return el_coordinates[f"NO {area_number}"]

    elif area_type == "NO" and area_number == 0:
        return [
            point
            for region in el_coordinates.values()
            for point in region
        ] # ? 

    elif area_type == "VASS":
        vass_regions = {
            1: ["RS", "RØ"],
            2: ["RV"],
            3: ["RM", "RN"],
        }

        regions = vass_regions[area_number]

        return [
            point
            for region in regions
            for point in nve_coordinates[region]
        ]

    else:
        raise ValueError(
            f"Unknown area: {area_type} {area_number}"
        )


def get_weather_data(
    coordinates: list[tuple[float, float]],
    start_date: str,
    end_date: str,
    batch_size: int = 10
) -> pd.DataFrame:
    """
    Download hourly ERA5 temperature and precipitation from Open-Meteo.

    Args:
        coordinates: List of (longitude, latitude) pairs.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        batch_size: Number of locations per API request.

    Returns:
        DataFrame with hourly average temperature and precipitation.
    """
    if not coordinates:
        raise ValueError("No coordinates provided.")

    # Set up API client with caching and retries
    cache_session = requests_cache.CachedSession(
        ".cache",
        expire_after=-1
    )
    retry_session = retry(
        cache_session,
        retries=5,
        backoff_factor=0.2
    )
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://archive-api.open-meteo.com/v1/archive"

    dataframes = []

    # Download data in smaller batches
    for i in range(0, len(coordinates), batch_size):
        batch = coordinates[i:i + batch_size]

        params = {
            "latitude": [lat for lon, lat in batch],
            "longitude": [lon for lon, lat in batch],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ["temperature_2m", "precipitation"],
            "models": "era5",
        }

        # Handle temporary API limits ??
        for attempt in range(5):
            try:
                responses = openmeteo.weather_api(url, params=params)
                break

            except OpenMeteoRequestsError as e:
                message = str(e)

                if "Minutely API request limit exceeded" in message:
                    if attempt == 4:
                        raise RuntimeError(
                            "Minute API limit still exceeded after retries."
                        ) from e
                    time.sleep(60)

                elif "Hourly API request limit exceeded" in message:
                    raise RuntimeError(
                        "Hourly API limit reached. Try again later."
                    ) from e

                else:
                    raise

        # Process each location's hourly data
        for response in responses:
            hourly = response.Hourly()

            dates = pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            )

            df = pd.DataFrame({
                "date": dates,
                "temperature_2m": (hourly.Variables(0).ValuesAsNumpy()),
                "precipitation": (hourly.Variables(1).ValuesAsNumpy())
            })
            dataframes.append(df)

    # Combine downloaded data
    weather_data = pd.concat(
        dataframes,
        ignore_index=True
    )

    # Calculate hourly average across all locations
    regional_average = (
        weather_data
        .groupby("date")[["temperature_2m", "precipitation"]]
        .mean()
        .reset_index()
    )

    return regional_average
