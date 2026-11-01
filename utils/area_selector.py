import streamlit as st


area_names = {
    "EL": {
        1: "NO1 - South-East",
        2: "NO2 - South-West",
        3: "NO3 - Central Norway",
        4: "NO4 - Northern Norway",
        5: "NO5 - Western Norway",
    },
    "NO": {
        0: "Whole Norway",
    },
    "VASS": {
        1: "Eastern Norway, Agder and parts of Rogaland",
        2: "Western Norway",
        3: "Central Norway and southern Nordland",
    },
}


def select_reservoir_area() -> tuple[str, int]:
    """Select and preserve a reservoir area across Streamlit pages."""

    # Restore the previously saved area selection
    saved_area = st.session_state.get(
        "selected_reservoir_area", ("EL", 1)
    )

    if "area_type" not in st.session_state:
        st.session_state["area_type"] = saved_area[0]

    # Select area type
    selected_area = st.radio(
        "Select area type:",
        options=["EL", "NO", "VASS"],
        horizontal=True,
        key="area_type",
    )

    # Get available area numbers for the selected type
    area_numbers = sorted(area_names[selected_area])

    # Restore previously selected area number
    if "area_number" not in st.session_state:
        st.session_state["area_number"] = saved_area[1]

    # Ensure the area number is valid for the selected type
    if st.session_state["area_number"] not in area_numbers:
        st.session_state["area_number"] = area_numbers[0]

    # Select area number
    selected_area_number = st.selectbox(
        "Select area number:",
        options=area_numbers,
        format_func=lambda number: (
            f"{number} - {area_names[selected_area][number]}"
        ),
        key="area_number",
    )

    # Store the selection independently of widget state
    st.session_state["selected_reservoir_area"] = (
        selected_area,
        int(selected_area_number),
    )

    return selected_area, int(selected_area_number)
