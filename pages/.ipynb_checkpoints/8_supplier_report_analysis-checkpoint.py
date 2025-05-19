# pages/supplier_sales_analysis.py

import streamlit as st
import pandas as pd
from utils.supplier_cleaning import clean_supplier_excel
from utils.supplier_analysis import generate_insights

st.title("📦 Supplier Sales Analysis")
st.write("Upload your weekly supplier sales Excel report to generate detailed business insights.")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    df = clean_supplier_excel(uploaded_file)
    st.success("✅ File cleaned and processed!")

    insights = generate_insights(df)

    st.metric("Total Products", insights["Total Unique Products"])
    st.metric("Units Sold", insights["Total Units Sold"])
    st.metric("Net Sales (Inc VAT)", f"£{insights['Total Net Sales (Inc VAT)']:.2f}")
    st.metric("Avg Price Per Unit", f"£{insights['Average Price per Unit Sold']:.2f}")

    st.subheader("🔝 Top Selling Products")
    st.dataframe(insights["Top Sellers"])

    st.subheader("📉 Slow Selling Products")
    st.dataframe(insights["Slow Sellers"])

    st.subheader("💰 Highest Revenue Products")
    st.dataframe(insights["Top Value Products"])

    st.subheader("⚠️ Returns or Negative Sales")
    st.dataframe(insights["Returns"])

    st.subheader("🔍 Products Sold Only Once")
    st.dataframe(insights["One-Time Sellers"])

    # Optionally store report history
    # df.to_csv(f"data/supplier_reports_history/supplier_report_{today}.csv", index=False)
