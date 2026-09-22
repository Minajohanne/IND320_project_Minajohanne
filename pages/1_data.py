import pandas as pd 
import streamlit as st 

st.title("Reservoir data table")

@st.cache_data
def load_data(file):
    """Read reservoir data from the local CSV file."""
    return pd.read_csv(file)

 # reading the data 
dat = load_data("data/reservoirs.csv")

# converting "dato_Id" to a datetime object 
dat["dato_Id"] = pd.to_datetime(dat["dato_Id"]) 
dat = dat.sort_values("dato_Id")

# find the first month of data 
first_date = dat["dato_Id"].min() 

first_month = dat[
    (dat["dato_Id"].dt.year == first_date.year) &
    (dat["dato_Id"].dt.month == first_date.month)
] 

# one table row for each column in the original CSV file 
rows = []
for col in dat.columns: 
    # LineChartColumn requires numeric values 
    if pd.api.types.is_numeric_dtype(dat[col]):
        values = first_month[col].tolist()
    else: 
        values = None 
    rows.append({
        "variable" : col,
        "first_month" : values
    })

tbl = pd.DataFrame(rows)

# Display the first month as a table with rowwise line charts
st.dataframe(
    tbl,
    column_config={
        "variable": "Variable",
        "first_month": st.column_config.LineChartColumn(
            "First month"
        ),
    },
    hide_index=True,
)


# flere observasjoner på samme dato?? 
# hva skal jeg gjøre med kategoriske variabler? 
# er main.py side 1? 