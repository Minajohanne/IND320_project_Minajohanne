import pandas as pd 
import streamlit as st 

@st.cache_data
def load_data(file):
    return pd.read_csv(file)

dat = load_data("data/reservoirs.csv") # reading the data 

dat["dato_Id"] = pd.to_datetime(dat["dato_Id"]) # converting "dato_Id" to a datetime object 

dat = dat.sort_values("dato_Id")

first_date = dat["dato_Id"].min() # first date in data 

first_month = dat[
    (dat["dato_Id"].dt.year == first_date.year) &
    (dat["dato_Id"].dt.month == first_date.month)
] # first month of data 

rows = []
for col in dat.columns: 
    values = first_month[col].to_list()
    rows.append({
        "variable" : col,
        "first_month" : values
    })
#print(rows)

tbl = pd.DataFrame(rows)
print(tbl.head())

# st.dataframe(
#     tbl,
#     column_config={
#         "first_month": st.column_config.LineChartColumn(
#             "First month"
#         )
#     }
# )


# flere observasjoner på samme dato?? 