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
    Explore Norwegian reservoir statistics and cross-border
    electricity flows through interactive data visualizations.
    """
)

st.divider()

# Two main sections
col1, col2 = st.columns(2, gap="large")

with col1:
    with st.container(border=True):
        st.subheader("💧 Reservoir Data")

        st.write(
            """
            Explore Norwegian reservoir filling levels, storage
            capacity, and stored energy using data from the
            Norwegian Water Resources and Energy Directorate (NVE).
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

with col2:
    with st.container(border=True):
        st.subheader("⚡ Power Flows")

        st.write(
            """
            Explore electricity imports and exports between Norway
            and neighboring countries using data from the
            ENTSO-E Transparency Platform.
            """
        )

        st.page_link(
            "pages/3_Electricity_flows.py",
            label="Explore Power Flows →"
        )