from io import StringIO
import pandas as pd
import requests


def get_exchange_rates(start_date: str, end_date: str) -> pd.DataFrame:
    """Download historical EUR and USD exchange rates against NOK."""
    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start) or pd.isna(end) or start > end:
        raise ValueError("Invalid exchange rate date range.")
    url = "https://data.norges-bank.no/api/data/EXR/B.EUR+USD.NOK.SP"
    params = {
        "format": "csv", "startPeriod": start_date,
        "endPeriod": end_date, "locale": "en",
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.Timeout as e:
        raise RuntimeError("Norges Bank API timed out. Please try again.") from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError("Could not download exchange rates from Norges Bank.") from e
    try:
        df = pd.read_csv(StringIO(response.text), sep=";")
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as e:
        raise ValueError("Norges Bank returned an unreadable or empty CSV.") from e
    required = ["TIME_PERIOD", "BASE_CUR", "OBS_VALUE"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing exchange rate columns: {', '.join(missing)}.")
    if df.empty:
        raise ValueError("No exchange rates available for the selected period.")
    df = df[required].copy()
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"], errors="coerce")
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    if df["TIME_PERIOD"].isna().any():
        raise ValueError("Exchange rates contain invalid dates.")
    if df["OBS_VALUE"].isna().any():
        raise ValueError("Exchange rates contain missing or invalid values.")
    if df.duplicated(["TIME_PERIOD", "BASE_CUR"]).any():
        raise ValueError("Duplicate currency observations found for a date.")
    df = df.pivot(index="TIME_PERIOD", columns="BASE_CUR", values="OBS_VALUE")
    missing_currencies = [currency for currency in ["EUR", "USD"] if currency not in df.columns]
    if missing_currencies:
        raise ValueError(f"Missing currencies: {', '.join(missing_currencies)}.")
    df = df[["EUR", "USD"]].rename_axis("Date").reset_index()
    df.columns.name = None
    return df.sort_values("Date").reset_index(drop=True)
