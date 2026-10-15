import requests
import pandas as pd
import streamlit as st 

@st.cache_data
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


def map_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename the columns of a DataFrame from Norwegian to English.

    Args:
        df (pd.DataFrame): DataFrame containing Norwegian column names.

    Returns:
        pd.DataFrame: DataFrame with English column names.
    """
    # Map names dictionary
    map_names = {
        "dato_Id": "Date",
        "omrType": "Area type",
        "omrnr": "Area number",
        "iso_aar": "Iso year",
        "iso_uke": "Iso week",
        "fyllingsgrad": "Filling level",
        "kapasitet_TWh": "Capacity (TWh)",
        "fylling_TWh": "Stored Energy (TWh)",
        "neste_Publiseringsdato": "Next publication date",
        "fyllingsgrad_forrige_uke": "Filling level previous week",
        "endring_fyllingsgrad": "Change in filling level"
    }

    # Rename columns
    df = df.rename(columns=map_names)
    return df


import pandas as pd
import streamlit as st

@st.cache_data
def load_reservoir_data(url: str) -> pd.DataFrame:
    """
    Load and prepare reservoir statistics from the NVE API.

    Args:
        url (str): URL of the NVE API endpoint.

    Returns:
        pd.DataFrame: DataFrame containing prepared reservoir data.
    """
    df = get_reservoir_data(url)

    # Rename columns
    df = map_names(df)

    # Convert dates
    df["Date"] = pd.to_datetime(df["Date"])

    # Sort by date
    df = df.sort_values("Date")

    return df