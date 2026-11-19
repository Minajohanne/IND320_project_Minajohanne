import requests
import pandas as pd 
from io import StringIO


def get_exchange_rates(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Download historical EUR and USD exchange rates against NOK
    from the Norges Bank API.

    Args:
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.

    Returns:
        pd.DataFrame: DataFrame containing dates and exchange rates
        for EUR and USD against NOK.
    """
    url = "https://data.norges-bank.no/api/data/EXR/B.EUR+USD.NOK.SP"

    params = {
        "format": "csv",
        "startPeriod": start_date,
        "endPeriod": end_date,
        "locale": "en"
    }

    # Download data
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    # Convert CSV response to DataFrame
    df = pd.read_csv(StringIO(response.text), sep=";")

    # Select relevant columns
    df = df[["TIME_PERIOD", "BASE_CUR", "OBS_VALUE"]]

    # Convert data types
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"])
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"])

    # Reshape to one column per currency
    df = df.pivot(
        index="TIME_PERIOD",
        columns="BASE_CUR",
        values="OBS_VALUE"
    ).reset_index()

    # Rename columns
    df.columns = ["Date", "EUR", "USD"]
    df.columns.name = None

    return df.sort_values("Date").reset_index(drop=True)
