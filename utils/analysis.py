import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import stft
from scipy.fft import dct, idct
from statsmodels.tsa.seasonal import STL
from sklearn.neighbors import LocalOutlierFactor

def plot_stl(
    data: pd.DataFrame,
    seasonal: int = 13,
    trend: int = 105,
    robust: bool = True
) -> go.Figure:
    """
    Perform STL decomposition on weekly reservoir filling levels.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing Date and Filling level columns.
    seasonal : int, default=13
        Length of the seasonal LOESS smoother.
    trend : int, default=105
        Length of the trend LOESS smoother.
    robust : bool, default=True
        Whether to use robust fitting to reduce the effect of outliers.

    Returns
    -------
    go.Figure
        Plotly figure showing the STL decomposition.
    """
    # Sort data chronologically
    data = data.sort_values("Date").reset_index(drop=True)

    stl = STL(
        data["Filling level"],
        period=52,
        seasonal=seasonal,
        trend=trend,
        robust=robust
    )

    result = stl.fit()

    # Create four subplots
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "Observed",
            "Trend",
            "Seasonal",
            "Residual"
        ],
        vertical_spacing=0.07
    )

    components = [
        data["Filling level"],
        result.trend,
        result.seasonal,
        result.resid
    ]

    for i, component in enumerate(components, start=1):
        fig.add_trace(
            go.Scatter(
                x=data["Date"],
                y=component,
                mode="lines",
                line=dict(color="steelblue", width=1),
                name=["Observed", "Trend", "Seasonal", "Residual"][i - 1]
            ),
            row=i,
            col=1
        )

    fig.update_layout(
        title="STL Decomposition of Reservoir Filling Levels",
        height=850,
        showlegend=False,
        template="plotly_white"
    )

    fig.update_xaxes(title_text="Date", row=4, col=1)

    return fig

def plot_spectrogram(
    data: pd.DataFrame,
    nperseg: int = 104,
    noverlap: int = 52
) -> go.Figure:
    """
    Create a spectrogram of weekly reservoir filling levels.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing weekly filling levels.
    nperseg : int, default=104
        Window length in weeks.
    noverlap : int, default=52
        Number of overlapping observations between windows.

    Returns
    -------
    go.Figure
        Plotly figure showing the spectrogram.
    """
    # Sort data chronologically
    data = data.sort_values("Date").reset_index(drop=True)

    # Extract filling levels
    y = data["Filling level"].to_numpy()

    # Compute short-time Fourier transform
    f, t, Zxx = stft(
        y,
        fs=1,
        nperseg=nperseg,
        noverlap=noverlap
    )

    # Create spectrogram
    fig = go.Figure(
        data=go.Heatmap(
            x=t,
            y=f,
            z=np.abs(Zxx),
            colorscale="Viridis",
            colorbar=dict(title="Magnitude")
        )
    )

    fig.update_layout(
        title="Spectrogram of Reservoir Filling Levels",
        xaxis_title="Time (weeks)",
        yaxis_title="Frequency (cycles/week)",
        template="plotly_white",
        height=500
    )

    return fig



def plot_precipitation_spc(
    df: pd.DataFrame,
    cutoff_frequency: float = 1 / 168,
    n_std: float = 3.0,
    area_name: str = "Selected area",
    weather_column: str = "temperature_2m"
) -> tuple[go.Figure, pd.DataFrame]:
    """
    Plot hourly weather observations with robust SPC control limits.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing date and the selected weather property.
    cutoff_frequency : float, default=1/168
        DCT cutoff frequency in cycles per hour.
    n_std : float, default=3.0
        Number of robust standard deviations for SPC limits.
    area_name : str, default="Selected area"
        Name of the selected area.
    weather_column : str, default="temperature_2m"
        Weather property to analyze.

    Returns
    -------
    tuple[go.Figure, pd.DataFrame]
        Plotly figure and a summary of detected outliers.
    """

    # Define labels for weather properties
    weather_labels = {
        "temperature_2m": ("Temperature", "°C"),
        "precipitation": ("Precipitation", "mm")
    }

    if weather_column not in weather_labels:
        raise ValueError("Invalid weather property.")

    property_name, unit = weather_labels[weather_column]

    # Remove missing observations
    df = df.dropna(
        subset=["date", weather_column]
    ).copy().reset_index(drop=True)

    # Extract weather observations and dates
    values = df[weather_column].to_numpy()
    dates = pd.to_datetime(df["date"])

    start_year = dates.min().year
    end_year = dates.max().year

    period = (
        str(start_year)
        if start_year == end_year
        else f"{start_year}–{end_year}"
    )

    # Apply DCT high-pass filtering
    N = len(values)
    W = np.arange(N) / (2 * (N - 1))

    dct_signal = dct(values, type=1, norm="forward")
    filtered_dct = dct_signal.copy()
    filtered_dct[W < cutoff_frequency] = 0

    filtered = idct(filtered_dct, type=1, norm="forward")

    # Calculate robust statistics using median and MAD
    median = np.median(filtered)
    mad = np.median(np.abs(filtered - median))
    robust_std = 1.4826 * mad

    ucl = median + n_std * robust_std
    lcl = median - n_std * robust_std

    # Identify outliers
    outliers = (filtered > ucl) | (filtered < lcl)

    # Convert SPC limits to original weather scale
    trend = values - filtered
    upper_boundary = trend + ucl
    lower_boundary = trend + lcl

    # Create Plotly figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines",
            name=f"Average {property_name.lower()}",
            line=dict(color="steelblue", width=1)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=upper_boundary,
            mode="lines",
            name="Upper control limit",
            line=dict(color="red", dash="dash")
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=lower_boundary,
            mode="lines",
            name="Lower control limit",
            line=dict(color="red", dash="dash")
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates[outliers],
            y=values[outliers],
            mode="markers",
            name="Outliers",
            marker=dict(color="darkorange", size=6)
        )
    )

    fig.update_layout(
        title=(
            f"Average {property_name} with SPC Limits "
            f"({area_name}, {period})"
        ),
        xaxis_title="Date",
        yaxis_title=f"Average {property_name.lower()} ({unit})",
        template="plotly_white",
        height=500,
        hovermode="x unified"
    )

    # Create outlier summary table
    outlier_summary = pd.DataFrame({
        "Metric": [
            "Total observations",
            "Number of outliers",
            "Percentage of outliers (%)",
            f"Maximum outlier {property_name.lower()} ({unit})"
        ],
        "Value": [
            len(values),
            int(outliers.sum()),
            round(outliers.mean() * 100, 2),
            round(float(values[outliers].max()), 3)
            if outliers.any() else np.nan
        ]
    })

    return fig, outlier_summary




def plot_temperature_lof(
    df: pd.DataFrame,
    contamination: float = 0.01,
    n_neighbors: int = 20,
    area_name: str = "Selected area",
    weather_column: str = "temperature_2m"
) -> tuple[go.Figure, pd.DataFrame]:
    """
    Detect weather outliers using Local Outlier Factor (LOF).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing date and the selected weather property.
    contamination : float, default=0.01
        Expected proportion of outliers.
    n_neighbors : int, default=20
        Number of nearest neighbors used by LOF.
    area_name : str, default="Selected area"
        Name of the selected area.
    weather_column : str, default="temperature_2m"
        Weather property to analyze.

    Returns
    -------
    tuple[go.Figure, pd.DataFrame]
        Plotly figure and a summary table of detected outliers.
    """

    # Define labels for the selected weather property
    weather_labels = {
        "temperature_2m": ("Temperature", "°C"),
        "precipitation": ("Precipitation", "mm")
    }

    if weather_column not in weather_labels:
        raise ValueError("Invalid weather property.")

    property_name, unit = weather_labels[weather_column]

    # Remove missing values and reset index
    df = df.dropna(
        subset=["date", weather_column]
    ).copy().reset_index(drop=True)

    # Extract selected weather property as a 2D array
    values = df[[weather_column]].to_numpy()

    # Apply Local Outlier Factor
    lof = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination
    )

    pred_labels = lof.fit_predict(values)

    # Identify outliers
    outliers = pred_labels == -1

    dates = pd.to_datetime(df["date"])

    start_year = dates.min().year
    end_year = dates.max().year

    period = (
        str(start_year)
        if start_year == end_year
        else f"{start_year}–{end_year}"
    )

    # Create Plotly figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=df[weather_column],
            mode="lines",
            name=f"Average {property_name.lower()}",
            line=dict(color="steelblue", width=1)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates[outliers],
            y=df.loc[outliers, weather_column],
            mode="markers",
            name="Outliers",
            marker=dict(color="darkorange", size=7)
        )
    )

    fig.update_layout(
        title=(
            f"Average {property_name} with LOF Outliers "
            f"({area_name}, {period})"
        ),
        xaxis_title="Date",
        yaxis_title=f"{property_name} ({unit})",
        template="plotly_white",
        height=500,
        hovermode="x unified"
    )

    # Create outlier summary table
    outlier_summary = pd.DataFrame({
        "Metric": [
            "Total observations",
            "Number of outliers",
            "Percentage of outliers (%)",
            f"Minimum outlier {property_name.lower()} ({unit})",
            f"Maximum outlier {property_name.lower()} ({unit})"
        ],
        "Value": [
            len(df),
            int(outliers.sum()),
            round(outliers.mean() * 100, 2),
            round(float(values[outliers].min()), 2)
            if outliers.any() else np.nan,
            round(float(values[outliers].max()), 2)
            if outliers.any() else np.nan
        ]
    })

    return fig, outlier_summary
