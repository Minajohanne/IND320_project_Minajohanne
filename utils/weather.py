
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
        ] 

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
    region: str,
    start_date: str,
    end_date: str,
    region_coordinates: dict[str, list[tuple[float, float]]],
    batch_size: int = 25
) -> pd.DataFrame:
    """
    Download hourly ERA5 weather data and calculate regional averages.

    Args:
        region: Region identifier, e.g. "NO 3".
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        region_coordinates: Dictionary of longitude-latitude pairs.
        batch_size: Number of coordinates per API request.

    Returns:
        DataFrame with hourly average temperature and precipitation.
    """
    coordinates = region_coordinates[region]

    if not coordinates:
        raise ValueError(f"No coordinates found for {region}.")

    url = "https://archive-api.open-meteo.com/v1/archive"

    session = requests.Session()

    total = None
    count = None

    total_batches = (
        len(coordinates) + batch_size - 1
    ) // batch_size

    print(
        f"Downloading {len(coordinates)} locations "
        f"for {region} ({total_batches} batches)"
    )

    for i in range(0, len(coordinates), batch_size):

        batch = coordinates[i:i + batch_size]
        batch_number = i // batch_size + 1

        print(
            f"Requesting batch {batch_number}/{total_batches}",
            flush=True
        )

        params = {
            "latitude": ",".join(str(lat) for lon, lat in batch),
            "longitude": ",".join(str(lon) for lon, lat in batch),
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,precipitation",
            "models": "era5",
            "timezone": "GMT",
        }

        # Retry failed requests
        for attempt in range(5):
            try:
                response = session.get(
                    url,
                    params=params,
                    timeout=(15, 60)
                )

                if response.status_code == 429:
                    print("API rate limit reached. Waiting 65 seconds.")
                    if attempt < 4:
                        time.sleep(65)
                        continue

                if response.status_code in (500, 502, 503, 504):
                    print(
                        f"Server error {response.status_code}. "
                        "Retrying..."
                    )
                    if attempt < 4:
                        time.sleep(10 * (attempt + 1))
                        continue

                response.raise_for_status()
                results = response.json()
                break

            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError
            ) as e:
                print(
                    f"Request failed: {e}. "
                    f"Attempt {attempt + 1}/5"
                )

                if attempt == 4:
                    raise RuntimeError(
                        f"Failed to download batch {batch_number}"
                    ) from e

                time.sleep(5)

        # API returns a dictionary for one location,
        # and a list for multiple locations
        if isinstance(results, dict):
            results = [results]

        if len(results) != len(batch):
            raise RuntimeError(
                f"Expected {len(batch)} responses, "
                f"received {len(results)}."
            )

        # Accumulate hourly values across locations
        for result in results:

            hourly = pd.DataFrame(result["hourly"])
            hourly["time"] = pd.to_datetime(
                hourly["time"],
                utc=True
            )
            hourly = hourly.set_index("time")

            hourly = hourly[
                ["temperature_2m", "precipitation"]
            ].apply(pd.to_numeric, errors="coerce")

            if total is None:
                total = hourly.fillna(0)
                count = hourly.notna().astype(int)

            else:
                total = total.add(
                    hourly.fillna(0),
                    fill_value=0
                )

                count = count.add(
                    hourly.notna().astype(int),
                    fill_value=0
                )

        print(
            f"Downloaded {min(i + batch_size, len(coordinates))}"
            f"/{len(coordinates)} locations",
            flush=True
        )

    # Calculate average for each variable and timestamp
    regional_average = (
        total.div(count.where(count != 0))
        .reset_index()
        .rename(columns={"time": "date"})
    )

    session.close()

    print(
        f"Finished downloading {region}: "
        f"{len(regional_average)} hourly observations"
    )

    return regional_average



# def get_weather_data(
#     region: str,
#     start_date: str,
#     end_date: str,
#     region_coordinates: dict[str, list[tuple[float, float]]]
# ) -> pd.DataFrame:
#     """
#     Download hourly historical weather data from the Open-Meteo API using the ERA5 model.

#     Retrieves temperature and precipitation data for 1000 randomly sampled
#     locations within the specified region and calculates the hourly average
#     across all locations.

#     Args:
#         region (str): Region identifier, e.g. "NO 3".
#         start_date (str): Start date in YYYY-MM-DD format.
#         end_date (str): End date in YYYY-MM-DD format.
#         region_coordinates (dict[str, list[tuple[float, float]]]): 
#         Dictionary containing longitude-latitude pairs for each region.

#     Returns:
#         pd.DataFrame: DataFrame containing hourly timestamps, average temperature
#         (°C), and average precipitation (mm) for the selected region.
#     """
#     # Setup Open-Meteo API client
#     cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
#     retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
#     openmeteo = openmeteo_requests.Client(session=retry_session)

#     # Get coordinates for the selected region
#     coordinates = region_coordinates[region]

#     lon = [lon for lon, lat in coordinates]
#     lat = [lat for lon, lat in coordinates]

#     # API URL
#     url = "https://archive-api.open-meteo.com/v1/archive"

#     # Store data for each location
#     dataframes = []
#     batch_size = 10

#     # Download weather data in batches
#     for i in range(0, len(lat), batch_size):

#         lat_batch = lat[i:i + batch_size]
#         lon_batch = lon[i:i + batch_size]

#         # API parameters
#         params = {
#             "latitude": lat_batch,
#             "longitude": lon_batch,
#             "start_date": start_date,
#             "end_date": end_date,
#             "hourly": ["temperature_2m", "precipitation"],
#             "models": "era5",
#         }

#         max_retries = 5

#         for attempt in range(max_retries):
#             try:
#                 responses = openmeteo.weather_api(url, params=params)
#                 break

#             except OpenMeteoRequestsError as e:
#                 error_message = str(e)

#                 if "Minutely API request limit exceeded" in error_message:
#                     print(
#                         f"API limit reached. Waiting 60 seconds... "
#                         f"({attempt + 1}/{max_retries})"
#                     )

#                     if attempt < max_retries - 1:
#                         time.sleep(60)

#                 elif "Daily API request limit exceeded" in error_message:
#                     raise RuntimeError(
#                         "Daily API limit reached. Try again tomorrow."
#                     ) from e

#                 elif "503" in error_message or "service is overloaded" in error_message.lower():
#                     raise RuntimeError(
#                         "Open-Meteo is currently overloaded. "
#                         "Please try downloading the data later."
#                     ) from e

#                 else:
#                     raise

#         else:
#             raise RuntimeError(
#                 f"Failed to download batch after {max_retries} attempts."
#             )

#         # Process data for each location
#         for response in responses:
#             hourly = response.Hourly()

#             temperature = hourly.Variables(0).ValuesAsNumpy()
#             precipitation = hourly.Variables(1).ValuesAsNumpy()

#             dates = pd.date_range(
#                 start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
#                 end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
#                 freq=pd.Timedelta(seconds=hourly.Interval()),
#                 inclusive="left"
#             )

#             df = pd.DataFrame({
#                 "date": dates,
#                 "temperature_2m": temperature,
#                 "precipitation": precipitation
#             })

#             dataframes.append(df)

#         print(f"Downloaded {min(i + batch_size, len(lat))}/{len(lat)} locations")

#     # Combine all locations
#     weather_data = pd.concat(dataframes, ignore_index=True)

#     # Calculate hourly averages across the region
#     regional_average = (
#         weather_data
#         .groupby("date")[["temperature_2m", "precipitation"]]
#         .mean()
#         .reset_index()
#     )

#     return regional_average
