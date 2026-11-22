import streamlit as st


# Display the shared reservoir area selector and return the selection.
def select_reservoir_area() -> tuple[str, int]:
    """Select reservoir area and preserve the selection across pages."""
    area_numbers = {"EL": [1, 2, 3, 4, 5], "VASS": [1, 2, 3], "NO": [0]}
    selection = st.session_state.get("selected_reservoir_area", ("EL", 1))
    if (
        not isinstance(selection, (tuple, list))
        or len(selection) != 2
        or selection[0] not in area_numbers
        or selection[1] not in area_numbers[selection[0]]
    ):
        selection = ("EL", 1)
    selected_area, selected_area_number = selection
    area_types = list(area_numbers)
    area_type = st.radio(
        "Select reservoir area type", options=area_types,
        index=area_types.index(selected_area), horizontal=True,
    )
    if area_type != selected_area:
        selected_area_number = area_numbers[area_type][0]
    area_number = st.selectbox(
        "Select area number", options=area_numbers[area_type],
        index=area_numbers[area_type].index(selected_area_number),
    )
    st.session_state["selected_reservoir_area"] = (area_type, area_number)
    return area_type, area_number
