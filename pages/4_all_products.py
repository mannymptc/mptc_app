import streamlit as st
import pandas as pd
import pyodbc
from utils.db import connect_db
import streamlit_authenticator as stauth
from auth_config import credentials

st.set_page_config(page_title="All Products", layout="wide")
st.title("📦 Products Information Portal")

#--------------------------------------------------------------------------
# Setup login form
authenticator = stauth.Authenticate(
    credentials,
    "mptc_app_cookie",           # cookie name
    "mptc_app_key",              # key used to encrypt the cookie
    cookie_expiry_days=0.1251    # 3 hour session time per login
)

name, auth_status, username = authenticator.login("Login", "main")

if auth_status is False:
    st.error("Incorrect username or password")

if auth_status is None:
    st.warning("Please enter your username and password")
    st.stop()

# Show logout
authenticator.logout("Logout", "sidebar")

#------------------------------------------------------------------------

@st.cache_data
def load_data():
    conn = connect_db()
    query = "SELECT * FROM Products"
    return pd.read_sql(query, conn)

df = load_data()

st.markdown("### 🔍 Filter Products")

temp_df = df.copy()

col1, col2, col3, col4 = st.columns(4)

with col1:
    skus = st.multiselect("Product SKU", sorted(temp_df['product_sku'].dropna().unique()))
with col2:
    categories = st.multiselect("Category", sorted(temp_df['product_category'].dropna().unique()))
with col3:
    names = st.multiselect("Product Name", sorted(temp_df['product_name'].dropna().unique()))
with col4:
    descriptions = st.multiselect("Description", sorted(temp_df['product_description'].dropna().unique()))

filters = {
    "product_sku": skus,
    "product_category": categories,
    "product_name": names,
    "product_description": descriptions
}

for col, values in filters.items():
    if values:
        temp_df = temp_df[temp_df[col].isin(values)]

col5, col6, col7, col8 = st.columns(4)

with col5:
    countries = st.multiselect("Source Country", sorted(temp_df['product_source_country'].dropna().unique()))
with col6:
    commodity_codes = st.multiselect("Commodity Code", sorted(temp_df['product_commodity_code'].dropna().unique()))
with col7:
    ean = st.multiselect("EAN Barcode", sorted(temp_df['ean_barcode'].dropna().unique()))
with col8:
    composition = st.multiselect("Product Composition", sorted(temp_df['product_composition'].dropna().unique()))

with col5:
    brand = st.multiselect("Brand Name", sorted(temp_df['brand_name'].dropna().unique()))
with col6:
    customs = st.multiselect("Customs Description", sorted(temp_df['customs_description'].dropna().unique()))

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

if temp_df.empty:
    st.warning("No records match your filters.")
else:
    st.dataframe(temp_df)

    csv = temp_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Filtered Products CSV",
        data=csv,
        file_name="filtered_products.csv",
        mime="text/csv"
    )
