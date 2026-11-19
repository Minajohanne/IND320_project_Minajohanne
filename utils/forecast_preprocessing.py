import pandas as pd


def preprocess_exogenous(
    df: pd.DataFrame,
    date_col: str,
    aggregation: dict,
    timezone: str | None = None,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Convert time series data to weekly observations."""

    data = df.copy()

    if timezone:
        data[date_col] = (
            pd.to_datetime(data[date_col], utc=True)
            .dt.tz_convert(timezone)
        )
    else:
        data[date_col] = pd.to_datetime(data[date_col])

    iso = data[date_col].dt.isocalendar()

    data["iso_aar"] = iso.year.astype(int)
    data["iso_uke"] = iso.week.astype(int)

    keys = ["iso_aar", "iso_uke"] + (group_cols or [])

    return (
        data.groupby(keys, as_index=False)
        .agg(aggregation)
    )


def prepare_weekly_weather(
    weather_data: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate hourly weather data to weekly observations."""

    return preprocess_exogenous(
        df=weather_data,
        date_col="date",
        aggregation={
            "temperature_2m": "mean",
            "precipitation": "sum",
        },
        timezone="Europe/Oslo",
    )


def prepare_weekly_entsoe(
    entsoe_data: pd.DataFrame,
    area_number: int,
) -> pd.DataFrame:
    """Prepare weekly import and export data for one electricity area."""

    weekly = preprocess_exogenous(
        df=entsoe_data,
        date_col="timestamp",
        aggregation={"quantity_mw": "mean"},
        timezone="Europe/Oslo",
        group_cols=["omrnr", "direction"],
    )

    weekly = weekly[
        weekly["omrnr"] == area_number
    ].copy()

    weekly = (
        weekly.pivot(
            index=["iso_aar", "iso_uke"],
            columns="direction",
            values="quantity_mw",
        )
        .reset_index()
    )

    weekly.columns.name = None

    return weekly


def prepare_weekly_exchange_rates(
    exchange_rates: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate daily exchange rates to weekly observations."""

    return preprocess_exogenous(
        df=exchange_rates,
        date_col="Date",
        aggregation={
            "EUR": "mean",
            "USD": "mean",
        },
    )


def prepare_reservoir_for_forecast(
    reservoir_data: pd.DataFrame,
) -> pd.DataFrame:
    """Restore column names expected by SARIMAX_filling."""

    return reservoir_data.rename(
        columns={
            "Area type": "omrType",
            "Area number": "omrnr",
            "Iso year": "iso_aar",
            "Iso week": "iso_uke",
            "Filling level": "fyllingsgrad",
        }
    )