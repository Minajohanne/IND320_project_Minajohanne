import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.figure import Figure
from scipy.signal import stft
from scipy.fft import dct, idct
from statsmodels.tsa.seasonal import STL
from sklearn.neighbors import LocalOutlierFactor

def plot_stl(
    data: pd.DataFrame,
    seasonal: int = 13,
    trend: int = 105,
    robust: bool = True
) -> Figure:
    """
    Perform STL decomposition on weekly reservoir filling levels.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing weekly filling levels.
    seasonal : int, default=13
        Length of the seasonal LOESS smoother.
    trend : int, default=105
        Length of the trend LOESS smoother.
    robust : bool, default=True
        Whether to use robust fitting to reduce the effect of outliers.

    Returns
    -------
    Figure
        Matplotlib figure showing the STL decomposition.
    """
    stl = STL(
        data["Filling level"],
        period=52,
        seasonal=seasonal,
        trend=trend,
        robust=robust
    )

    result = stl.fit()
    fig = result.plot()

    return fig


def plot_spectrogram(
    data: pd.DataFrame,
    nperseg: int = 104,
    noverlap: int = 52
) -> Figure:
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
    Figure
        Matplotlib figure showing the spectrogram.
    """
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
    fig, ax = plt.subplots(figsize=(12, 5))

    mesh = ax.pcolormesh(
        t,
        f,
        np.abs(Zxx),
        shading="auto"
    )

    ax.set_title("Spectrogram of reservoir filling levels")
    ax.set_xlabel("Time (weeks)")
    ax.set_ylabel("Frequency (cycles/week)")

    fig.colorbar(mesh, ax=ax, label="Magnitude")

    return fig


def plot_precipitation_spc(
    df: pd.DataFrame,
    cutoff_frequency: float = 1 / 168,
    n_std: float = 3.0,
    area_name: str = "Selected area"
) -> tuple[Figure, pd.DataFrame]:
    """
    Plot hourly precipitation with robust SPC control limits.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing date and precipitation columns.
    cutoff_frequency : float, default=1/168
        DCT cutoff frequency in cycles per hour,
        corresponding to a period of 7 days.
    n_std : float, default=3.0
        Number of robust standard deviations for SPC limits.

    Returns
    -------
    tuple[Figure, pd.DataFrame]
        Matplotlib figure and a summary of detected outliers.
    """
    # Extract precipitation and dates
    precipitation = df["precipitation"].to_numpy()
    dates = df["date"]
    start_year = pd.to_datetime(dates).min().year
    end_year = pd.to_datetime(dates).max().year

    period = (
        str(start_year)
        if start_year == end_year
        else f"{start_year}–{end_year}"
    )

    # Apply DCT high-pass filtering
    N = len(precipitation)
    W = np.arange(N) / (2 * (N - 1))

    dct_signal = dct(precipitation, type=1, norm="forward")
    filtered_dct = dct_signal.copy()
    filtered_dct[W < cutoff_frequency] = 0

    filtered = idct(filtered_dct, type=1, norm="forward")

    # Calculate robust statistics using median and MAD
    median = np.median(filtered)
    mad = np.median(np.abs(filtered - median))
    robust_std = 1.4826 * mad

    ucl = median + n_std * robust_std
    lcl = median - n_std * robust_std

    # Identify outliers in the filtered signal
    outliers = (filtered > ucl) | (filtered < lcl)

    # Convert SPC limits to the original precipitation scale
    trend = precipitation - filtered
    upper_boundary = trend + ucl
    lower_boundary = trend + lcl

    # Plot precipitation and control limits
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        dates, precipitation,
        color="steelblue",
        linewidth=0.8,
        label="Average precipitation"
    )

    ax.plot(
        dates, upper_boundary,
        "r--",
        label="Upper control limit"
    )

    ax.plot(
        dates, lower_boundary,
        "r--",
        label="Lower control limit"
    )

    ax.scatter(
        dates[outliers],
        precipitation[outliers],
        color="darkorange",
        s=15,
        label="Outliers",
        zorder=3
    )

    ax.set_title(f"Average Precipitation with SPC Limits ({area_name}, {period})")    
    ax.set_xlabel("Date")
    ax.set_ylabel("Average precipitation (mm)")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()

    # Create outlier summary table
    outlier_summary = pd.DataFrame({
        "Metric": [
            "Total observations",
            "Number of outliers",
            "Percentage of outliers (%)",
            "Maximum outlier precipitation (mm)"
        ],
        "Value": [
            len(precipitation),
            int(outliers.sum()),
            round(outliers.mean() * 100, 2),
            round(float(precipitation[outliers].max()), 3)
            if outliers.any() else np.nan
        ]
    })

    return fig, outlier_summary


def plot_temperature_lof(
    df: pd.DataFrame,
    contamination: float = 0.01,
    n_neighbors: int = 20,
    area_name: str = "Selected area"
) -> tuple[Figure, pd.DataFrame]:
    """
    Detect temperature outliers using Local Outlier Factor (LOF).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing date and temperature_2m columns.
    contamination : float
        Expected proportion of outliers (default: 0.01).
    n_neighbors : int
        Number of nearest neighbors used by LOF (default: 20).

    Returns
    -------
    tuple[Figure, pd.DataFrame]
        Matplotlib figure and a summary table of detected outliers.
    """

    # Extract temperature as a 2D array
    temp = df[["temperature_2m"]].to_numpy()

    # Apply Local Outlier Factor
    lof = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination
    )

    pred_labels = lof.fit_predict(temp)

    # Identify outliers
    outliers = pred_labels == -1

    start_year = pd.to_datetime(df["date"]).min().year
    end_year = pd.to_datetime(df["date"]).max().year

    period = (
        str(start_year)
        if start_year == end_year
        else f"{start_year}–{end_year}"
    )

    # Plot temperature and highlight outliers
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        df["date"],
        df["temperature_2m"],
        color="steelblue",
        linewidth=0.8,
        label="Average temperature"
    )

    ax.scatter(
        df.loc[outliers, "date"],
        df.loc[outliers, "temperature_2m"],
        color="darkorange",
        s=20,
        label="Outliers",
        zorder=3
    )

    ax.set_title(f"Average Temperature with LOF Outliers ({area_name}, {period})")    
    ax.set_xlabel("Date")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()

    # Create outlier summary table
    outlier_summary = pd.DataFrame({
        "Metric": [
            "Total observations",
            "Number of outliers",
            "Percentage of outliers (%)",
            "Minimum outlier temperature (°C)",
            "Maximum outlier temperature (°C)"
        ],
        "Value": [
            len(df),
            int(outliers.sum()),
            round(outliers.mean() * 100, 2),
            round(float(temp[outliers].min()), 2)
            if outliers.any() else np.nan,
            round(float(temp[outliers].max()), 2)
            if outliers.any() else np.nan
        ]
    })

    return fig, outlier_summary