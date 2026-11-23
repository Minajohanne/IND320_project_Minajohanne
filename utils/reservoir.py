"""Fetch and prepare weekly reservoir statistics from NVE."""

import pandas as pd
import requests
import streamlit as st


# Fetch reservoir statistics from the NVE API.
@st.cache_data
def get_reservoir_data(url: str) -> pd.DataFrame:
    """Fetch reservoir observations from NVE with useful error messages."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("The NVE API request timed out. Please try again.") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError("Could not connect to the NVE API. Please try again later.") from exc
    except ValueError as exc:
        raise RuntimeError("The NVE API returned invalid JSON data.") from exc

    if not isinstance(data, list) or not data:
        raise ValueError("The NVE API returned no reservoir observations.")
    df = pd.DataFrame(data)
    if df.empty:
        raise ValueError("The NVE API returned an empty dataset.")
    return df


# Rename reservoir data columns for use in the dashboard.
def map_names(df: pd.DataFrame) -> pd.DataFrame:
    """Rename NVE columns; filling levels are fractions (0–1), energy is TWh."""
    column_mapping = {
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
        "endring_fyllingsgrad": "Change in filling level",
    }
    return df.rename(columns=column_mapping)


# Load and prepare reservoir observations.
@st.cache_data(ttl=3600)
def load_reservoir_data(url: str) -> pd.DataFrame:
    """Load, validate, and sort NVE reservoir statistics."""
    df = map_names(get_reservoir_data(url))
    required = ["Date", "Area type", "Area number", "Iso year", "Iso week", "Filling level"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"NVE data is missing required columns: {', '.join(missing)}.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if df["Date"].isna().any():
        raise ValueError("NVE data contains invalid or missing dates.")

    for column in ("Area number", "Iso year", "Iso week", "Filling level"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if df[["Area type", "Area number", "Iso year", "Iso week"]].isna().any().any():
        raise ValueError("NVE data contains missing or invalid area/week identifiers.")
    if df["Filling level"].isna().any():
        raise ValueError("NVE data contains missing or invalid filling levels.")

    return df.sort_values("Date").reset_index(drop=True)
