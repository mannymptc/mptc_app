import streamlit as st
import pandas as pd
import pyodbc
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.express as px

st.set_page_config(page_title="📊 MPTC Business Dashboard", layout="wide")
st.title("🏠 Business Overview Dashboard")

# ------------------ DATABASE CONNECTION WITH RETRY ------------------
def connect_db():
    for attempt in range(3):
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
            st.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)
    st.error("❌ Could not connect to database after 3 attempts.")
    return None

# ------------------ LOAD DATA ------------------
@st.cache_data
def load_data():
    conn = connect_db()
    if conn is None:
        return pd.DataFrame()
    try:
        query = """
        SELECT order_id, order_channel, order_date, despatch_date, order_value, 
               order_cust_postcode, product_sku, product_name, product_qty, 
               customer_name, product_price, order_courier_service
        FROM OrdersDespatch
        WHERE despatch_date >= DATEADD(MONTH, -12, GETDATE())
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Query execution failed: {e}")
        return pd.DataFrame()

# ------------------ FILTER LOGIC ------------------
df = load_data()
if df.empty:
    st.stop()

df['order_date'] = pd.to_datetime(df['order_date']).dt.normalize()
df['despatch_date'] = pd.to_datetime(df['despatch_date']).dt.normalize()

despatch_dates = sorted(df['despatch_date'].dropna().unique())
order_dates = sorted(df['order_date'].dropna().unique())

# Sidebar filters
st.sidebar.header("🗓️ Filter by Date")

despatch_date_range = st.sidebar.date_input("Despatch Date Range", [])
despatch_quick = st.sidebar.selectbox("🕒 Quick Despatch Date Range", [
    "None", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
])

order_date_range = st.sidebar.date_input("Order Date Range", [])
order_quick = st.sidebar.selectbox("🕒 Quick Order Date Range", [
    "None", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
])

def get_range_from_option(option, available_dates):
    if len(available_dates) == 0:
        return None, None
    today = max(available_dates)
    if option == "Yesterday":
        return today, today
    elif option == "Last 7 Days":
        return today - timedelta(days=6), today
    elif option == "Last 30 Days":
        return today - timedelta(days=29), today
    elif option == "Last 3 Months":
        return today - relativedelta(months=3), today
    elif option == "Last 6 Months":
        return today - relativedelta(months=6), today
    elif option == "Last 12 Months":
        return today - relativedelta(months=12), today
    else:
        return None, None

# Final date ranges
if despatch_quick != "None":
    despatch_start, despatch_end = get_range_from_option(despatch_quick, despatch_dates)
elif len(despatch_date_range) == 1:
    despatch_start = despatch_end = pd.to_datetime(despatch_date_range[0])
elif len(despatch_date_range) == 2:
    despatch_start, despatch_end = pd.to_datetime(despatch_date_range)
else:
    despatch_start, despatch_end = max(despatch_dates) - timedelta(days=29), max(despatch_dates)

apply_order_filter = False
order_start = order_end = None
if order_quick != "None":
    order_start, order_end = get_range_from_option(order_quick, order_dates)
    apply_order_filter = True
elif len(order_date_range) == 1:
    order_start = order_end = pd.to_datetime(order_date_range[0])
    apply_order_filter = True
elif len(order_date_range) == 2:
    order_start, order_end = pd.to_datetime(order_date_range)
    apply_order_filter = True

# ------------------ FILTER & ANALYSIS ------------------
channels = sorted(df['order_channel'].dropna().unique().tolist())
selected_channels = st.sidebar.multiselect("Select Sales Channel(s)", ["Select All"] + channels, default=["Select All"])
if "Select All" in selected_channels or not selected_channels:
    selected_channels = channels

# Apply filters
filtered_df = df[
    (df['despatch_date'].between(despatch_start, despatch_end)) &
    (df['order_channel'].isin(selected_channels))
]
if apply_order_filter:
    filtered_df = filtered_df[filtered_df['order_date'].between(order_start, order_end)]

if filtered_df.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ------------------ KPI Metrics ------------------
dedup_orders = filtered_df.drop_duplicates(subset='order_id')
total_orders = dedup_orders['order_id'].nunique()
total_revenue = dedup_orders['order_value'].sum()
avg_order_value = dedup_orders['order_value'].mean()
unique_product_skus = filtered_df['product_sku'].nunique()
total_quantity_ordered = filtered_df['product_qty'].sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🚪 Total Orders", total_orders)
col2.metric("💰 Total Revenue", f"£ {total_revenue:,.2f}")
col3.metric("📦 Avg Order Value", f"£ {avg_order_value:,.2f}")
col4.metric("🔢 Unique SKUs", unique_product_skus)
col5.metric("📦 Total Quantity", total_quantity_ordered)

# ------------------ Visuals ------------------
df_line = dedup_orders.groupby('order_date')['order_value'].sum().reset_index()
fig_line = px.line(df_line, x='order_date', y='order_value', title="Order Value Over Time")
st.plotly_chart(fig_line, use_container_width=True)

channel_summary = dedup_orders.groupby('order_channel').agg(
    total_orders_value=('order_value', 'sum'),
    orders_count=('order_id', 'nunique')
).reset_index()

fig_value_bar = px.bar(channel_summary, x="order_channel", y="total_orders_value", text="total_orders_value")
st.plotly_chart(fig_value_bar, use_container_width=True)

fig_count_bar = px.bar(channel_summary, x="order_channel", y="orders_count", text="orders_count")
st.plotly_chart(fig_count_bar, use_container_width=True)

fig_donut_value = px.pie(channel_summary, names='order_channel', values='total_orders_value', hole=0.4)
st.plotly_chart(fig_donut_value, use_container_width=True)

fig_donut_count = px.pie(channel_summary, names='order_channel', values='orders_count', hole=0.4)
st.plotly_chart(fig_donut_count, use_container_width=True)
