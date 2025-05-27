import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="📋 Channel-wise Detailed Report", layout="wide")
st.title("🧾 Channel-wise Detailed Analytics")

# ------------------ DATABASE CONNECTION ------------------
def connect_db():
    try:
        return pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=mptcecommerce-sql-server.database.windows.net;"
            "DATABASE=mptcecommerce-db;"
            "UID=mptcadmin;"
            "PWD=Mptc@2025;"
            "Connection Timeout=30"
        )
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# ------------------ LOAD DATA FUNCTION ------------------
@st.cache_data
def load_data():
    conn = connect_db()
    if conn is None:
        return pd.DataFrame()
    try:
        query = """
        SELECT order_id, order_channel, order_value, order_cust_postcode, product_sku, 
               product_name, product_qty, product_price, despatch_date
        FROM OrdersDespatch
        WHERE despatch_date >= DATEADD(MONTH, -12, GETDATE())
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Query failed: {e}")
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.stop()

df['despatch_date'] = pd.to_datetime(df['despatch_date'])

# ------------------ SIDEBAR: DESPATCH DATE FILTERS ------------------
st.sidebar.header("📅 Filter by Despatch Date")

# Manual + quick filters
selected_range = st.sidebar.date_input("Despatch Date Range", [])
quick_range = st.sidebar.selectbox("🕒 Quick Despatch Range", [
    "None", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
])

# Function to compute date ranges from dropdown option
def get_range_from_option(option, df_date_col):
    if df_date_col.empty:
        return None, None

    all_dates = sorted(df_date_col.dt.normalize().dropna().unique())
    latest_date = max(all_dates)

    if option == "Yesterday":
        # Use the latest date that has data
        return latest_date, latest_date
    elif option == "Last 7 Days":
        return latest_date - timedelta(days=6), latest_date
    elif option == "Last 30 Days":
        return latest_date - timedelta(days=29), latest_date
    elif option == "Last 3 Months":
        return latest_date - relativedelta(months=3), latest_date
    elif option == "Last 6 Months":
        return latest_date - relativedelta(months=6), latest_date
    elif option == "Last 12 Months":
        return latest_date - relativedelta(months=12), latest_date
    else:
        return None, None

# Determine final start_date and end_date
if quick_range != "None":
    start_date, end_date = get_range_from_option(quick_range, df['despatch_date'])
elif len(selected_range) == 1:
    start_date = end_date = pd.to_datetime(selected_range[0])
elif len(selected_range) == 2:
    start_date, end_date = pd.to_datetime(selected_range)
else:
    end_date = df['despatch_date'].max().normalize()
    start_date = end_date - timedelta(days=30)

# Normalize despatch_date
df['despatch_date'] = pd.to_datetime(df['despatch_date']).dt.normalize()

# Apply date filter
st.caption(f"Debug: Filtering from {start_date.date()} to {end_date.date()}")
st.caption(f"Max despatch date in data: {df['despatch_date'].max().date()}")
filtered_df = df[df['despatch_date'].between(start_date, end_date)]

# ------------------ CHANNEL FILTER ------------------
channels = sorted(filtered_df['order_channel'].dropna().unique().tolist())
all_option = "Select All"
channels_with_all = [all_option] + channels

selected_channels = st.multiselect("📦 Select Sales Channel(s)", options=channels_with_all, default=[all_option])

# Expand "Select All"
if all_option in selected_channels or not selected_channels:
    selected_channels = channels

# Final filter by channel
filtered_df = filtered_df[filtered_df['order_channel'].isin(selected_channels)]

# Exit early if empty
if filtered_df.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ------------------ TOP N DROPDOWN ------------------
top_n = st.selectbox("Show Top/Bottom N Records", [5, 10, 15, 20, 25], index=1)

# ------------------ KPIs ------------------
# ✅ Corrected KPI Calculation Logic (matches Page 1)
dedup_orders = (
    filtered_df
    .sort_values('order_value', ascending=False)
    .drop_duplicates(subset='order_id')
)

total_orders = dedup_orders['order_id'].nunique()
total_revenue = dedup_orders['order_value'].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
unique_skus = filtered_df['product_sku'].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.markdown(f"**🛒 Total Orders**<br><span style='font-size: 20px;'>{total_orders:,}</span>", unsafe_allow_html=True)
col2.markdown(f"**💰 Total Revenue**<br><span style='font-size: 20px;'>£ {total_revenue:,.2f}</span>", unsafe_allow_html=True)
col3.markdown(f"**📦 Avg Order Value**<br><span style='font-size: 20px;'>£ {avg_order_value:,.2f}</span>", unsafe_allow_html=True)
col4.markdown(f"**🔢 Unique SKUs Sold**<br><span style='font-size: 20px;'>{unique_skus:,}</span>", unsafe_allow_html=True)

# ------------------ SKU SUMMARY ------------------
# Step 1: Get order_id to product_sku mapping from deduped orders only
dedup_orders = (
    filtered_df
    .sort_values('order_value', ascending=False)
    .drop_duplicates(subset='order_id')
)

# Step 2: Create order→SKU mapping for unique order count per SKU
sku_orders = dedup_orders[['order_id', 'product_sku']].drop_duplicates()
sku_order_counts = sku_orders['product_sku'].value_counts().rename("unique_orders").reset_index()
sku_order_counts.columns = ['product_sku', 'unique_orders']

# Step 3: Get full sold_qty (sum from all rows, not deduped)
sku_qty = (
    filtered_df.groupby(['product_sku', 'product_name'])
    .agg(sold_qty=('product_qty', 'sum'))
    .reset_index()
)

# Step 4: Merge both
sku_summary = pd.merge(sku_qty, sku_order_counts, on='product_sku', how='left').fillna(0)
sku_summary['unique_orders'] = sku_summary['unique_orders'].astype(int)

# ------------------ RAW DATA + DOWNLOAD ------------------
st.markdown("### 🧾 Sample Raw Data")
st.dataframe(filtered_df.head(10), use_container_width=True)

csv_data = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Full Filtered Channel Data as CSV",
    data=csv_data,
    file_name=f"filtered_channel_orders.csv",
    mime="text/csv"
)
