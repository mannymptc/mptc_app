import streamlit as st
st.set_page_config(page_title="📦 All Products", layout="wide")

import pandas as pd
from utils.db import connect_db
from utils.auth_utils import run_auth  # ✅ Centralized login

#-------------------------------------------------------
# 🔐 Run login
name, username = run_auth()

# --------------------- PAGE TITLE ---------------------
st.title("📦 Products Information Portal")

# --------------------- LOAD DATA ---------------------
@st.cache_data
def load_data():
    conn = connect_db()
    return pd.read_sql("SELECT * FROM Products", conn)

df = load_data()
temp_df = df.copy()

# --------------------- FILTER SECTION ---------------------
st.markdown("### 🔍 Filter Products")

# Row 1 filters
col1, col2, col3, col4 = st.columns(4)
with col1:
    skus = st.multiselect("Product SKU", sorted(temp_df['product_sku'].dropna().unique()))
with col2:
    categories = st.multiselect("Category", sorted(temp_df['product_category'].dropna().unique()))
with col3:
    names = st.multiselect("Product Name", sorted(temp_df['product_name'].dropna().unique()))
with col4:
    descriptions = st.multiselect("Description", sorted(temp_df['product_description'].dropna().unique()))

# Apply first set of filters
filters = {
    "product_sku": skus,
    "product_category": categories,
    "product_name": names,
    "product_description": descriptions
}
for col, values in filters.items():
    if values:
        temp_df = temp_df[temp_df[col].isin(values)]

# Row 2 filters
col5, col6, col7, col8 = st.columns(4)
with col5:
    countries = st.multiselect("Source Country", sorted(temp_df['product_source_country'].dropna().unique()))
with col6:
    commodity_codes = st.multiselect("Commodity Code", sorted(temp_df['product_commodity_code'].dropna().unique()))
with col7:
    ean = st.multiselect("EAN Barcode", sorted(temp_df['ean_barcode'].dropna().unique()))
with col8:
    composition = st.multiselect("Product Composition", sorted(temp_df['product_composition'].dropna().unique()))

# Row 3 filters
col9, col10 = st.columns(2)
with col9:
    brand = st.multiselect("Brand Name", sorted(temp_df['brand_name'].dropna().unique()))
with col10:
    customs = st.multiselect("Customs Description", sorted(temp_df['customs_description'].dropna().unique()))

# Apply extra filters
extra_filters = {
    "product_source_country": countries,
    "product_commodity_code": commodity_codes,
    "ean_barcode": ean,
    "product_composition": composition,
    "brand_name": brand,
    "customs_description": customs
}
for col, values in extra_filters.items():
    if values:
        temp_df = temp_df[temp_df[col].isin(values)]

# --------------------- RESULTS ---------------------
if temp_df.empty:
    st.warning("⚠️ No records match your filters.")
else:
    st.dataframe(temp_df, use_container_width=True)

    csv = temp_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Filtered Products CSV",
        data=csv,
        file_name="filtered_products.csv",
        mime="text/csv"
    )
