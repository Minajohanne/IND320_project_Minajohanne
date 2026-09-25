import streamlit as st

st.title("Page 4")

# simple calculator app
st.title("Simple Calculator")
st.write("Enter two numbers:")

num1 = st.number_input("Enter the first number:")
num2 = st.number_input("Enter the second number:")
operation = st.selectbox("Select an operation:", ("Add", "Subtract", "Multiply", "Divide"))

if st.button("Calculate"):
    if operation == "Add":
        result = num1 + num2
    elif operation == "Subtract":
        result = num1 - num2
    elif operation == "Multiply":
        result = num1 * num2
    elif operation == "Divide":
        if num2 != 0:
            result = num1 / num2
        else:
            st.error("Error: Division by zero is not allowed.")
    st.success(f"The result is: {result}")