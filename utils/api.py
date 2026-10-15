import requests
import pandas as pd


def get_reservoir_data(url: str) -> pd.DataFrame:
    """
    Fetch reservoir data from the NVE API and return a DataFrame.

    Args:
        url (str): URL of the NVE reservoir data API endpoint.

    Returns:
        pd.DataFrame: DataFrame containing the reservoir data.

    Raises:
        requests.exceptions.RequestException: If the API request fails.
        ValueError: If the response contains invalid JSON.
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        return pd.DataFrame(data)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching reservoir data: {e}")
        raise

    except ValueError as e:
        print(f"Error processing API response: {e}")
        raise


# API endpoint
url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

# Fetch data
df = get_reservoir_data(url)
print(df.head())