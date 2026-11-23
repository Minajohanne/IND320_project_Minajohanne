
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from river import time_series, metrics


# Fit the forecasting model and predict future reservoir filling.
def SARIMAX_filling(
    df: pd.DataFrame,
    area_number: int,
    area_type: str = "EL",
    history: int = 156,
    horizon: int = 12,
    p: int = 1,
    d: int = 0,
    q: int = 0,
    m: int = 52,
    sp: int = 1,
    sd: int = 0,
    sq: int = 0,
    evaluate: bool = False,
    weather_data: pd.DataFrame | None = None,
    electricity_data: pd.DataFrame | None = None,
    exchange_rates: pd.DataFrame | None = None,
    end_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Forecast weekly reservoir filling levels using River's SNARIMAX.

    Optional exogenous variables include weather, electricity flows,
    and exchange rates. The model is trained sequentially and can
    either evaluate historical predictions or forecast future values.

    Args:
        df: Reservoir data from Magasinstatistikk.
        area_number: Selected reservoir area number.
        area_type: Reservoir area type (EL, NO, or VASS).
        history: Number of historical weeks used.
        horizon: Number of weeks to forecast.
        p: Autoregressive order.
        d: Differencing order.
        q: Moving average order.
        m: Seasonal period.
        sp: Seasonal autoregressive order.
        sd: Seasonal differencing order.
        sq: Seasonal moving average order.
        evaluate: Whether to evaluate on historical observations.
        weather_data: Weekly weather data.
        electricity_data: Weekly electricity flow data.
        exchange_rates: Weekly currency exchange rates.
        end_date: Last date included in the historical period.

    Returns:
        DataFrame containing weekly forecast values.
    """

    # --------------------------------------------------
    # Validate parameters
    # --------------------------------------------------

    if history < 2 or horizon < 1:
        raise ValueError(
            "History must be >= 2 and horizon >= 1."
        )

    if evaluate and horizon >= history:
        raise ValueError(
            "Horizon must be smaller than history."
        )

    valid_areas = {
        "EL": range(1, 6),
        "NO": [0],
        "VASS": range(1, 4),
    }

    if area_type not in valid_areas:
        raise ValueError("Invalid area type.")

    if area_number not in valid_areas[area_type]:
        raise ValueError(
            f"Invalid area number for {area_type}."
        )

    if df is None or df.empty:
        raise ValueError("No reservoir data available for forecasting.")
    required = ["omrType", "omrnr", "iso_aar", "iso_uke", "fyllingsgrad"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing reservoir columns: {', '.join(missing)}.")
    if any(not isinstance(v, int) or v < 0 for v in (p, d, q, sp, sd, sq)):
        raise ValueError("SNARIMAX model orders must be non-negative integers.")
    if not isinstance(m, int) or m < 1:
        raise ValueError("Seasonal period must be a positive integer.")

    # Select reservoir area
    data = df[
        (df["omrType"] == area_type)
        & (df["omrnr"] == area_number)
    ].copy()

    if data.empty:
        raise ValueError(
            "No reservoir data found for the selected area."
        )

    # Convert ISO year and week to Monday dates
    data["Date"] = pd.to_datetime(
        data["iso_aar"].astype(str)
        + "-W"
        + data["iso_uke"].astype(str).str.zfill(2)
        + "-1",
        format="%G-W%V-%u",
    )

    data = data.sort_values("Date")

    # Select training end date
    if end_date is not None:
        end_date = pd.Timestamp(end_date)

        data = data[
            data["Date"] <= end_date
        ].copy()

    # Merge optional exogenous data sources
    sources = {
        "weather": weather_data,
        "electricity": electricity_data,
        "exchange": exchange_rates,
    }

    feature_columns = []
    keys = ["iso_aar", "iso_uke"]

    for source_name, source_df in sources.items():

        if source_df is None:
            continue

        if source_df.empty:
            raise ValueError(f"No {source_name} data available.")
        if any(key not in source_df.columns for key in keys):
            raise ValueError(f"Missing ISO year/week columns in {source_name}.")
        source = source_df.copy()

        # Select numerical features
        columns = [
            col
            for col in source.select_dtypes(
                include="number"
            ).columns
            if col not in keys
        ]

        if not columns:
            raise ValueError(
                f"No numerical features found in {source_name}."
            )

        # Prefix feature names
        rename_map = {
            col: f"{source_name}_{col}"
            for col in columns
        }

        source = source.rename(columns=rename_map)
        new_features = list(rename_map.values())

        # Check duplicate weeks
        if source.duplicated(keys).any():
            raise ValueError(
                f"{source_name} contains duplicate ISO weeks."
            )

        # Merge on ISO year and week
        data = data.merge(
            source[keys + new_features],
            on=keys,
            how="left",
            validate="one_to_one",
        )

        feature_columns.extend(new_features)

    # Select historical observations
    data = (
        data.sort_values("Date")
        .tail(history)
        .reset_index(drop=True)
    )

    if len(data) < history:
        raise ValueError(
            f"Only {len(data)} observations available. "
            f"Requested {history} weeks."
        )

    data["fyllingsgrad"] = pd.to_numeric(data["fyllingsgrad"], errors="coerce")
    if not np.isfinite(data["fyllingsgrad"].to_numpy(dtype=float)).all():
        raise ValueError(
            "Missing reservoir filling values."
        )

    # Verify consecutive weekly observations
    if not data["Date"].diff().dropna().eq(
        pd.Timedelta(weeks=1)
    ).all():
        raise ValueError(
            "Reservoir data must contain consecutive weeks."
        )

    # Check missing exogenous values
    if feature_columns:
        if not np.isfinite(data[feature_columns].to_numpy(dtype=float)).all():
            raise ValueError(
                "Missing exogenous values. Check that all "
                "selected data sources cover the history period."
            )

    # Create SNARIMAX model
    model = time_series.SNARIMAX(
        p=p,
        d=d,
        q=q,
        m=m,
        sp=sp,
        sd=sd,
        sq=sq,
    )

    # Split training and test data
    if evaluate:
        train = data.iloc[:-horizon]
        test = data.iloc[-horizon:]
    else:
        train = data
        test = None

    # Train model sequentially
    for _, row in train.iterrows():

        y = float(row["fyllingsgrad"])

        x = {
            col: float(row[col])
            for col in feature_columns
        }

        model.learn_one(y, x=x)

    # Prepare future exogenous variables
    if feature_columns:

        # Persistence assumption:
        # Keep last observed values constant
        last_x = {
            col: float(train.iloc[-1][col])
            for col in feature_columns
        }

        future_xs = [
            last_x.copy()
            for _ in range(horizon)
        ]

    else:
        future_xs = None

    # Forecast
    predictions = model.forecast(
        horizon=horizon,
        xs=future_xs,
    )

    if len(predictions) != horizon or not np.isfinite(np.asarray(predictions, dtype=float)).all():
        raise ValueError("Forecast returned missing or invalid predictions.")

    # Historical evaluation
    if evaluate:

        mae = metrics.MAE()
        rmse = metrics.RMSE()

        for y_true, y_pred in zip(
            test["fyllingsgrad"],
            predictions,
        ):
            mae.update(float(y_true), float(y_pred))
            rmse.update(float(y_true), float(y_pred))

        print(f"MAE:  {mae.get():.4f}")
        print(f"RMSE: {rmse.get():.4f}")

        return pd.DataFrame({
            "Date": test["Date"].to_numpy(),
            "Actual filling level":
                test["fyllingsgrad"].to_numpy(),
            "Predicted filling level": predictions,
        })

    # Generate future dates
    future_dates = pd.date_range(
        start=(
            data["Date"].iloc[-1]
            + pd.Timedelta(weeks=1)
        ),
        periods=horizon,
        freq="W-MON",
    )

    return pd.DataFrame({
        "Date": future_dates,
        "Predicted filling level": predictions,
    })


# Visualize historical reservoir levels and forecast values.
def plot_forecast_animation(
    historical_data: pd.DataFrame,
    forecast: pd.DataFrame,
) -> go.Figure:
    """
    Create a Plotly animation of weekly reservoir filling forecasts.

    The animation reveals the predicted values one week at a time.

    Args:
        historical_data: DataFrame with Date and fyllingsgrad.
        forecast: DataFrame returned by SARIMAX_filling.

    Returns:
        Animated Plotly figure.
    """

    historical = historical_data.sort_values("Date").copy()
    forecast = forecast.sort_values("Date").copy()

    if historical.empty or forecast.empty:
        raise ValueError(
            "Historical and forecast data must not be empty."
        )

    # Connect forecast to last historical observation
    last_date = historical["Date"].iloc[-1]
    last_value = historical["fyllingsgrad"].iloc[-1]

    forecast_dates = [last_date] + forecast["Date"].tolist()
    forecast_values = (
        [last_value]
        + forecast["Predicted filling level"].tolist()
    )

    # Animation frames
    frames = []

    for step in range(1, len(forecast) + 1):

        frames.append(
            go.Frame(
                data=[
                    go.Scatter(
                        x=forecast_dates[:step + 1],
                        y=forecast_values[:step + 1],
                        mode="lines+markers",
                        name="Forecast",
                        line=dict(
                            color="red",
                            dash="dash",
                        ),
                    )
                ],
                traces=[1],
                name=str(step),
            )
        )

    # Create figure
    fig = go.Figure(
        data=[
            go.Scatter(
                x=historical["Date"],
                y=historical["fyllingsgrad"],
                mode="lines",
                name="Historical filling",
                line=dict(color="blue"),
            ),
            go.Scatter(
                x=forecast_dates[:2],
                y=forecast_values[:2],
                mode="lines+markers",
                name="Forecast",
                line=dict(
                    color="red",
                    dash="dash",
                ),
            ),
        ],
        frames=frames,
    )

    # Layout and animation controls
    fig.update_layout(
        title="Reservoir Filling Forecast",
        xaxis_title="Date",
        yaxis_title="Filling level (fraction)",
        yaxis=dict(range=[0, 1]),  # Physical range for reservoir filling fractions
        hovermode="x unified",
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {
                                    "duration": 400,
                                    "redraw": True,
                                },
                                "fromcurrent": True,
                            },
                        ],
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[
                            [None],
                            {
                                "frame": {
                                    "duration": 0,
                                    "redraw": False,
                                },
                                "mode": "immediate",
                            },
                        ],
                    ),
                ],
            )
        ],
    )

    return fig
