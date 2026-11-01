
import streamlit as st

st.set_page_config(
    page_title="Norwegian Energy Dashboard",
    page_icon="⚡",
    layout="wide"
)

# Main title
st.title("Norwegian Energy Dashboard")

st.write(
    """
    Explore Norwegian reservoir statistics, cross-border electricity
    flows, and weather data through interactive visualizations
    and statistical analysis.
    """
)

st.divider()

# Three main sections
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    with st.container(border=True):
        st.subheader("💧 Reservoir Data & Analysis")

        st.write(
            """
            Explore Norwegian reservoir filling levels, storage
            capacity, and stored energy using data from NVE.
            Analyze historical trends and seasonal patterns
            through interactive visualizations and statistical methods.
            """
        )

        st.page_link(
            "pages/1_Reservoir_data.py",
            label="View Reservoir Data →"
        )

        st.page_link(
            "pages/2_Reservoir_trends.py",
            label="Explore Reservoir Trends →"
        )

        st.page_link(
            "pages/3_Reservoir_seasonality.py",
            label="Explore Reservoir Seasonality →"
        )

with col2:
    with st.container(border=True):
        st.subheader("⚡ Electricity Flows")

        st.write(
            """
            Explore electricity imports and exports between Norway
            and neighboring countries using data from the
            ENTSO-E Transparency Platform.
            """
        )

        st.page_link(
            "pages/4_Electricity_flows.py",
            label="Explore Electricity Flows →"
        )

with col3:
    with st.container(border=True):
        st.subheader("🌦️ Weather Analysis")

        st.write(
            """
            Explore historical temperature and precipitation
            data across Norwegian regions. Identify unusual
            weather observations using statistical process
            control (SPC) and Local Outlier Factor (LOF).
            """
        )

        st.page_link(
            "pages/5_Weather_analysis.py",
            label="Explore Weather Analysis →"
        )
