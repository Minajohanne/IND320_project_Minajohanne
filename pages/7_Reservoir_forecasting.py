import pandas as pd
import streamlit as st

# Area selector
from utils.area_selector import select_reservoir_area

# Forecasting
from utils.forecasting import (
    SARIMAX_filling,
    plot_forecast_animation,
)

# Preprocessing
from utils.forecast_preprocessing import (
    prepare_weekly_weather,
    prepare_weekly_entsoe,
    prepare_weekly_exchange_rates,
    prepare_reservoir_for_forecast,
)

# Weather data
from utils.weather import (
    load_coordinates,
    get_area_coordinates,
    get_weather_data,
)

# Existing data-loading functions
from utils.reservoir import load_reservoir_data
from utils.mongoDB import load_electricity_data
from utils.exchange_rates import get_exchange_rates


# --------------------------------------------------
# Page title
# --------------------------------------------------

st.title("Reservoir Filling Forecast")

st.write(
    "Forecast weekly reservoir filling levels using "
    "River's SNARIMAX model. Select model parameters, "
    "training period, forecast horizon, and optional "
    "exogenous data sources."
)


# --------------------------------------------------
# Load reservoir data
# --------------------------------------------------

NVE_URL = (
    "https://biapi.nve.no/magasinstatistikk/api/"
    "Magasinstatistikk/HentOffentligData"
)

reservoir_data = load_reservoir_data(NVE_URL)

# Restore the column names expected by SARIMAX_filling
df_nve = prepare_reservoir_for_forecast(
    reservoir_data
)


# --------------------------------------------------
# Select reservoir area
# --------------------------------------------------

st.subheader("Reservoir area")

selected_area, selected_area_number = (
    select_reservoir_area()
)

area_data = df_nve[
    (df_nve["omrType"] == selected_area)
    & (df_nve["omrnr"] == selected_area_number)
].copy()

if area_data.empty:
    st.error("No reservoir data available for this area.")
    st.stop()

# Convert ISO weeks to Mondays
area_data["Date"] = pd.to_datetime(
    area_data["iso_aar"].astype(str)
    + "-W"
    + area_data["iso_uke"].astype(str).str.zfill(2)
    + "-1",
    format="%G-W%V-%u",
)

area_data = area_data.sort_values("Date")


# --------------------------------------------------
# Training period and forecast horizon
# --------------------------------------------------

st.subheader("Forecast settings")

latest_date = area_data["Date"].max().date()
earliest_date = area_data["Date"].min().date()

col1, col2 = st.columns(2)

with col1:
    training_end = st.date_input(
        "Training end date",
        value=latest_date,
        min_value=earliest_date,
        max_value=latest_date,
    )

with col2:
    horizon = st.slider(
        "Forecast horizon (weeks)",
        min_value=1,
        max_value=52,
        value=12,
    )

history = st.slider(
    "Training history (weeks)",
    min_value=52,
    max_value=260,
    value=156,
    step=4,
)

st.caption(
    "The model uses the selected number of historical "
    "weeks ending at the selected training date."
)


# --------------------------------------------------
# Model parameters
# --------------------------------------------------

st.subheader("Model parameters")

col1, col2, col3 = st.columns(3)

with col1:
    p = st.number_input(
        "AR order (p)",
        min_value=0,
        max_value=10,
        value=3,
    )

with col2:
    d = st.number_input(
        "Differencing (d)",
        min_value=0,
        max_value=2,
        value=1,
    )

with col3:
    q = st.number_input(
        "MA order (q)",
        min_value=0,
        max_value=10,
        value=1,
    )


# --------------------------------------------------
# Seasonal parameters
# --------------------------------------------------

with st.expander("Seasonal parameters"):

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sp = st.number_input(
            "Seasonal AR (sp)",
            min_value=0,
            max_value=3,
            value=0,
        )

    with col2:
        sd = st.number_input(
            "Seasonal differencing (sd)",
            min_value=0,
            max_value=2,
            value=0,
        )

    with col3:
        sq = st.number_input(
            "Seasonal MA (sq)",
            min_value=0,
            max_value=3,
            value=0,
        )

    with col4:
        m = st.number_input(
            "Seasonal period (m)",
            min_value=1,
            max_value=52,
            value=52,
        )


# --------------------------------------------------
# Exogenous data sources
# --------------------------------------------------

st.subheader("Exogenous variables")

available_sources = [
    "Open-Meteo",
    "Norges Bank",
]

# ENTSO-E data is organized by electricity price area
if selected_area == "EL":
    available_sources.insert(1, "ENTSO-E")

selected_sources = st.multiselect(
    "Select additional data sources",
    options=available_sources,
    default=[],
)

st.caption(
    "The default configuration uses only historical "
    "reservoir filling levels."
)


# --------------------------------------------------
# Generate forecast
# --------------------------------------------------

if st.button("Generate forecast", type="primary"):

    try:
        with st.spinner("Preparing data and forecasting..."):

            # --------------------------------------
            # Select training period
            # --------------------------------------

            training_end = pd.Timestamp(training_end)

            # Use complete ISO weeks only
            training_end = training_end - pd.Timedelta(
                days=training_end.weekday()
            )

            df_training = df_nve.copy()

            df_training["Date"] = pd.to_datetime(
                df_training["iso_aar"].astype(str)
                + "-W"
                + df_training["iso_uke"].astype(str).str.zfill(2)
                + "-1",
                format="%G-W%V-%u",
            )

            df_training = df_training[
                df_training["Date"] <= training_end
            ].copy()

            # --------------------------------------
            # Determine dates for external data
            # --------------------------------------

            start_date = (
                training_end
                - pd.Timedelta(weeks=history + 1)
            ).strftime("%Y-%m-%d")

            end_date = (
                training_end + pd.Timedelta(days=6)
            ).strftime("%Y-%m-%d")

            # --------------------------------------
            # Initialize optional sources
            # --------------------------------------

            weather = None
            electricity = None
            exchange = None

            # --------------------------------------
            # Open-Meteo
            # --------------------------------------

            if "Open-Meteo" in selected_sources:

                el_coordinates = load_coordinates(
                    "el_coordinates.json"
                )

                nve_coordinates = load_coordinates(
                    "nve_coordinates.json"
                )

                coordinates = get_area_coordinates(
                    area_type=selected_area,
                    area_number=selected_area_number,
                    el_coordinates=el_coordinates,
                    nve_coordinates=nve_coordinates,
                )

                region = (
                    f"{selected_area} "
                    f"{selected_area_number}"
                )

                weather_raw = get_weather_data(
                    region=region,
                    start_date=start_date,
                    end_date=end_date,
                    region_coordinates={
                        region: coordinates
                    },
                )

                weather = prepare_weekly_weather(
                    weather_raw
                )

            # --------------------------------------
            # ENTSO-E
            # --------------------------------------

            if "ENTSO-E" in selected_sources:

                entsoe_raw = pd.DataFrame(
                    load_electricity_data()
                )

                electricity = prepare_weekly_entsoe(
                    entsoe_raw,
                    area_number=selected_area_number,
                )

            # --------------------------------------
            # Norges Bank
            # --------------------------------------

            if "Norges Bank" in selected_sources:

                exchange_raw = get_exchange_rates(
                    start_date=start_date,
                    end_date=end_date,
                )

                exchange = prepare_weekly_exchange_rates(
                    exchange_raw
                )

            # --------------------------------------
            # Forecast
            # --------------------------------------

            forecast = SARIMAX_filling(
                df=df_training,
                area_type=selected_area,
                area_number=selected_area_number,
                history=history,
                horizon=horizon,
                p=p,
                d=d,
                q=q,
                m=m,
                sp=sp,
                sd=sd,
                sq=sq,
                evaluate=False,
                weather_data=weather,
                electricity_data=electricity,
                exchange_rates=exchange,
            )

            # --------------------------------------
            # Historical data for visualization
            # --------------------------------------

            historical = df_training[
                (df_training["omrType"] == selected_area)
                & (
                    df_training["omrnr"]
                    == selected_area_number
                )
            ].copy()

            historical = (
                historical
                .sort_values("Date")
                .tail(history)
            )

        # ------------------------------------------
        # Display results
        # ------------------------------------------

        st.success("Forecast generated successfully!")

        st.subheader("Forecast results")

        st.dataframe(
            forecast,
            use_container_width=True,
        )

        # ------------------------------------------
        # Plotly animation
        # ------------------------------------------

        st.subheader("Forecast animation")

        fig = plot_forecast_animation(
            historical_data=historical,
            forecast=forecast,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        # ------------------------------------------
        # Download forecast
        # ------------------------------------------

        csv = forecast.to_csv(index=False)

        st.download_button(
            label="Download forecast as CSV",
            data=csv,
            file_name="reservoir_forecast.csv",
            mime="text/csv",
        )

    except (ValueError, KeyError) as error:
        st.error(f"Forecast failed: {error}")

    except Exception as error:
        st.error(f"An unexpected error occurred: {error}")
