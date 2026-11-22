
import streamlit as st

st.set_page_config(
    page_title="Norwegian Energy Dashboard",
    page_icon="⚡",
    layout="wide",
)

# Color palette
BLUE = "#1676C1"
GREEN = "#348D73"
YELLOW = "#D39A35"


def colored_line(color):
    """Display a colored line at the top of a card."""
    st.markdown(
        f"""
        <div style="
            background-color: {color};
            height: 6px;
            border-radius: 5px;
            margin-bottom: 15px;
        "></div>
        """,
        unsafe_allow_html=True,
    )


def home():
    st.title("Norwegian Energy Dashboard")

    st.write(
        "Explore Norwegian reservoir statistics, cross-border electricity "
        "flows, weather data, and their relationships through interactive "
        "visualizations, statistical analysis, and forecasting."
    )

    st.divider()

    col1, col2, col3 = st.columns(3, gap="large")

    # EXPLORATION
    with col1:
        with st.container(border=True):
            colored_line(BLUE)

            st.subheader("🗺️ Exploration")

            st.write(
                "Explore Norwegian reservoir filling levels, "
                "electricity flows, geographical patterns, "
                "and historical trends."
            )

            st.page_link(
                "pages/1_Interactive_map.py",
                label="Interactive Map →",
            )

            st.page_link(
                "pages/2_Reservoir_data.py",
                label="Reservoir Data →",
            )

            st.page_link(
                "pages/5_Reservoir_trends.py",
                label="Reservoir Trends →",
            )

            st.page_link(
                "pages/4_Electricity_flows.py",
                label="Electricity Flows →",
            )

    # ANALYSIS
    with col2:
        with st.container(border=True):
            colored_line(GREEN)

            st.subheader("📊 Analysis")

            st.write(
                "Investigate seasonal patterns, weather anomalies, "
                "and relationships between meteorological conditions "
                "and reservoir filling levels."
            )

            st.page_link(
                "pages/3_Reservoir_seasonality.py",
                label="Reservoir Seasonality →",
            )

            st.page_link(
                "pages/6_Weather_analysis.py",
                label="Weather Analysis →",
            )

            st.page_link(
                "pages/8_Meterology_reservoir_correlation.py",
                label="Reservoir Correlation →",
            )

    # FORECASTING
    with col3:
        with st.container(border=True):
            colored_line(YELLOW)

            st.subheader("📈 Forecasting")

            st.write(
                "Forecast future reservoir filling levels using "
                "time series models and optional exogenous variables "
                "from weather, electricity, and exchange rate data."
            )

            st.page_link(
                "pages/7_Reservoir_forecasting.py",
                label="Reservoir Forecasting →",
            )


# Sidebar navigation
pages = {
    "Home": [
        st.Page(
            home,
            title="Home",
            icon="🏠",
            default=True,
        ),
    ],
    "Exploration": [
        st.Page(
            "pages/1_Interactive_map.py",
            title="Interactive Map",
            icon="🗺️",
        ),
        st.Page(
            "pages/2_Reservoir_data.py",
            title="Reservoir Data",
            icon="💧",
        ),
        st.Page(
            "pages/5_Reservoir_trends.py",
            title="Reservoir Trends",
            icon="📈",
        ),
        st.Page(
            "pages/4_Electricity_flows.py",
            title="Electricity Flows",
            icon="⚡",
        ),
    ],
    "Analysis": [
        st.Page(
            "pages/3_Reservoir_seasonality.py",
            title="Reservoir Seasonality",
            icon="📊",
        ),
        st.Page(
            "pages/6_Weather_analysis.py",
            title="Weather Analysis",
            icon="🌦️",
        ),
        st.Page(
            "pages/8_Meterology_reservoir_correlation.py",
            title="Reservoir Correlation",
            icon="🔗",
        ),
    ],
    "Forecasting": [
        st.Page(
            "pages/7_Reservoir_forecasting.py",
            title="Reservoir Forecasting",
            icon="🔮",
        ),
    ],
}

navigation = st.navigation(pages, position="sidebar")
navigation.run()
