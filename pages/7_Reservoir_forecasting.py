import pandas as pd
import streamlit as st

# Area selector
from utils.area_selector import select_reservoir_area

from utils.plotting import apply_plot_theme

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


# Page title.

st.title("Reservoir Filling Forecast")

st.write(
    "Forecast weekly reservoir filling levels using "
    "River's SNARIMAX model. Select model parameters, "
    "training period, forecast horizon, and optional "
    "exogenous data sources."
)

# Get the reservoir area selected in the dashboard.
selected_area, selected_area_number = (select_reservoir_area())


# Load reservoir data.

url = (
    "https://biapi.nve.no/magasinstatistikk/api/"
    "Magasinstatistikk/HentOffentligData"
)

try:
    reservoir_data = load_reservoir_data(url)
except (ValueError, RuntimeError, KeyError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()

# Prepare reservoir columns for the forecasting function.
df_nve = prepare_reservoir_for_forecast(
    reservoir_data
)


# Keep data for the selected reservoir area.
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


# Training period and forecast horizon.

st.subheader("Forecast settings")

latest_date = area_data["Date"].max().date()
earliest_date = area_data["Date"].min().date()

# Choose the final training date.
training_end = st.date_input(
    "Training end date",
    value=latest_date,
    min_value=earliest_date,
    max_value=latest_date,
)

# Set how many weeks ahead to forecast.
horizon = st.slider(
    "Forecast horizon (weeks)",
    min_value=1,
    max_value=52,
    value=12,
)

# Choose the amount of historical training data.
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


# Model parameters.

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


# Seasonal parameters.
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


# Exogenous data sources.
st.subheader("Exogenous variables")

# Select optional external data sources for the model.
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


# Generate forecast.

# Run the forecast only when requested.
if st.button("Generate forecast", type="primary"):

    try:
        with st.spinner("Preparing data and forecasting..."):
            # Select training period.
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

            # Determine dates for external data.

            start_date = (
                training_end
                - pd.Timedelta(weeks=history + 1)
            ).strftime("%Y-%m-%d")

            end_date = (
                training_end + pd.Timedelta(days=6)
            ).strftime("%Y-%m-%d")

            # Initialize optional sources.

            weather = None
            electricity = None
            exchange = None

            # Open-meteo.

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

            # Entso-e.
            if "ENTSO-E" in selected_sources:

                entsoe_raw = pd.DataFrame(
                    load_electricity_data()
                )

                electricity = prepare_weekly_entsoe(
                    entsoe_raw,
                    area_number=selected_area_number,
                )
            # Norges bank.

            if "Norges Bank" in selected_sources:

                exchange_raw = get_exchange_rates(
                    start_date=start_date,
                    end_date=end_date,
                )

                exchange = prepare_weekly_exchange_rates(
                    exchange_raw
                )

            # Forecast.

            # Fit the model and generate the requested forecast.
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

            # Historical data for visualization.

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

        # Display results.

        st.success("Forecast generated successfully!")

        # Show the size and period of the training and forecast datasets.
        _forecast_cols = st.columns(3)
        _forecast_cols[0].metric("Training observations", f"{len(historical):,}")
        _forecast_cols[1].metric("Forecast rows", f"{len(forecast):,}")
        _forecast_cols[2].metric("Forecast horizon", f"{horizon} weeks")
        st.caption("Forecast filling levels are fractions (0–1); 0.5 corresponds to 50%.")

        st.subheader("Forecast results")

        st.dataframe(
            forecast,
            use_container_width=True,
        )

        # Plotly animation.

        st.subheader("Forecast animation")

        fig = plot_forecast_animation(
            historical_data=historical,
            forecast=forecast,
        )

        fig = apply_plot_theme(fig)
        fig.update_yaxes(title_text="Filling level (fraction)")
        fig.update_xaxes(title_text="Date")

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        # Download forecast.

        # Prepare the forecast results for CSV download.
        csv = forecast.to_csv(index=False)

        st.download_button(
            label="Download forecast as CSV",
            data=csv,
            file_name="reservoir_forecast.csv",
            mime="text/csv",
        )

    except (ValueError, RuntimeError, KeyError, OSError) as error:
        st.error(f"Forecast failed: {error}")

    except Exception as error:
        st.error(f"An unexpected error occurred: {error}")


with st.expander('How to interpret the results'):
    st.markdown('The SNARIMAX model forecasts weekly reservoir filling levels based on historical observations, with the option to include exogenous variables such as weather conditions, electricity flows, and exchange rates. Forecast accuracy depends on the selected training period, model parameters, and available data. When exogenous variables are included, their last observed values are assumed to remain constant throughout the forecast horizon. Forecasts are subject to uncertainty, particularly over longer horizons, and should be interpreted as model-based estimates rather than exact prediction.')

with st.expander('About the data'):
    st.markdown('Reservoir filling data are from [NVE Magasinstatistikk](https://www.nve.no/energi/energisystem/vannkraft/magasinstatistikk/). Optional explanatory variables come from [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), and [Norges Bank](https://www.norges-bank.no/). Filling level is a fraction (0–1). External series are aligned to weekly data for model input.')
