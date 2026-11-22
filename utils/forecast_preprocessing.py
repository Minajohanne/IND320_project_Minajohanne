import pandas as pd


# Check that the required input columns are available.
def _require_columns(df: pd.DataFrame, columns: list[str], source: str) -> None:
    if df is None or df.empty:
        raise ValueError(f"No {source} data available.")
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing {source} columns: {', '.join(missing)}.")


# Prepare external variables for the forecasting model.
def preprocess_exogenous(
    df: pd.DataFrame,
    date_col: str,
    aggregation: dict,
    timezone: str | None = None,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Convert time series data to weekly observations."""
    _require_columns(df, [date_col, *aggregation.keys(), *(group_cols or [])], "input")
    data = df.copy()
    dates = pd.to_datetime(data[date_col], errors="coerce", utc=bool(timezone))
    if dates.isna().any():
        raise ValueError(f"Invalid or missing timestamps in '{date_col}'.")
    if timezone:
        dates = dates.dt.tz_convert(timezone)
    data[date_col] = dates
    for col in aggregation:
        data[col] = pd.to_numeric(data[col], errors="coerce")
        if data[col].notna().sum() == 0:
            raise ValueError(f"No valid numeric values in '{col}'.")
    iso = data[date_col].dt.isocalendar()
    data["iso_aar"] = iso.year.astype(int)
    data["iso_uke"] = iso.week.astype(int)
    keys = ["iso_aar", "iso_uke", *(group_cols or [])]
    result = data.groupby(keys, as_index=False).agg(aggregation)
    if result.empty:
        raise ValueError("Weekly aggregation returned no observations.")
    return result


# Aggregate weather observations to weekly values.
def prepare_weekly_weather(weather_data: pd.DataFrame) -> pd.DataFrame:
    """Use weekly mean temperature (°C) and sum of hourly precipitation (mm)."""
    return preprocess_exogenous(
        df=weather_data,
        date_col="date",
        aggregation={"temperature_2m": "mean", "precipitation": "sum"},
        timezone="Europe/Oslo",
    )


# Aggregate electricity flow data to weekly values.
def prepare_weekly_entsoe(entsoe_data: pd.DataFrame, area_number: int) -> pd.DataFrame:
    """Aggregate power flows as weekly mean MW, not weekly energy in MWh."""
    _require_columns(
        entsoe_data,
        ["from_zone", "to_zone", "timestamp", "quantity_mw", "direction"],
        "electricity",
    )
    df = entsoe_data.copy()
    df["from_zone"] = df["from_zone"].astype("string")
    df["to_zone"] = df["to_zone"].astype("string")
    df["norwegian_zone"] = df["from_zone"].where(
        df["from_zone"].str.match(r"^NO_?[1-5]$", na=False),
        df["to_zone"],
    )
    df["omrnr"] = pd.to_numeric(
        df["norwegian_zone"].str.extract(r"^NO_?([1-5])$")[0],
        errors="coerce",
    )
    df = df[df["omrnr"] == area_number].copy()
    if df.empty:
        raise ValueError(f"No electricity flow data available for NO{area_number}.")
    weekly = preprocess_exogenous(
        df=df,
        date_col="timestamp",
        aggregation={"quantity_mw": "mean"},
        timezone="Europe/Oslo",
        group_cols=["omrnr", "direction"],
    )
    weekly = weekly.pivot(
        index=["iso_aar", "iso_uke"],
        columns="direction", values="quantity_mw",
    ).reset_index()
    weekly.columns.name = None
    return weekly


# Prepare weekly exchange rate observations.
def prepare_weekly_exchange_rates(exchange_rates: pd.DataFrame) -> pd.DataFrame:
    """Average daily EUR/NOK and USD/NOK rates into weekly NOK per unit."""
    return preprocess_exogenous(
        df=exchange_rates, date_col="Date",
        aggregation={"EUR": "mean", "USD": "mean"},
    )


# Convert reservoir data to the format expected by the forecast model.
def prepare_reservoir_for_forecast(reservoir_data: pd.DataFrame) -> pd.DataFrame:
    """Restore column names expected by SARIMAX_filling."""
    _require_columns(
        reservoir_data,
        ["Area type", "Area number", "Iso year", "Iso week", "Filling level"],
        "reservoir",
    )
    return reservoir_data.rename(columns={
        "Area type": "omrType", "Area number": "omrnr",
        "Iso year": "iso_aar", "Iso week": "iso_uke",
        "Filling level": "fyllingsgrad",
    })
