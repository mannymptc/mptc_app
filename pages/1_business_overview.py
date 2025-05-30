import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import streamlit_authenticator as stauth
from auth_config import credentials

st.set_page_config(page_title="📊 MPTC Business Dashboard", layout="wide")
st.title("🏭 Business Overview Dashboard")

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

# ------------------ DATABASE CONNECTION ------------------
def connect_db():
    try:
        return pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=mptcecommerce-sql-server.database.windows.net;"
            "DATABASE=mptcecommerce-db;"
            "UID=mptcadmin;"
            "PWD=Mptc@2025;"
            "Connection Timeout=60"
        )
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
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
               order_cust_postcode, product_sku, product_name, product_qty, customer_name, 
               product_price, order_courier_service
        FROM OrdersDespatch
        WHERE order_date >= DATEADD(MONTH, -12, GETDATE())
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Query execution failed: {e}")
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.stop()

df['order_date'] = pd.to_datetime(df['order_date']).dt.normalize()
df['despatch_date'] = pd.to_datetime(df['despatch_date']).dt.normalize()

# ------------------ KPI COMPARISON TABLE ------------------
st.markdown("### 📊 KPI Comparison Table (based on Order Date)")

from datetime import datetime, timedelta

# Define time periods
kpi_periods = {
    "Yesterday": 1,
    "Last 7 Days": 7,
    "Last 1 Month": 30,
    "Last 3 Months": 90,
    "Last 6 Months": 180,
    "Last 1 Year": 365
}

today = df['order_date'].max()
rows = []

# Arrow and dot logic
def arrow_colored(t1, t2):
    if pd.isna(t1) or pd.isna(t2): return "-"
    if t1 > t2:
        return f"{int(t1):,} <span style='color:#32cd32; font-size:18px;'>▲</span>"
    elif t1 < t2:
        return f"{int(t1):,} <span style='color:red; font-size:18px;'>▼</span>"
    else:
        return f"{int(t1):,} <span style='color:#f4c430; font-size:18px;'>⚫</span>"

# Build the table rows with correct de-duplication and calculations
for label, days in kpi_periods.items():
    if label == "Yesterday":
        t1_start = today - timedelta(days=1)
        t1_end = t1_start
        t2_start = today - timedelta(days=2)
        t2_end = t2_start
    else:
        t1_end = today
        t1_start = today - timedelta(days=days - 1)
        t2_end = t1_start - timedelta(days=1)
        t2_start = t2_end - timedelta(days=days - 1)

    # Filter time periods
    df_t1 = df[(df['order_date'] >= t1_start) & (df['order_date'] <= t1_end)]
    df_t2 = df[(df['order_date'] >= t2_start) & (df['order_date'] <= t2_end)]

    # ✅ Deduplicate based on highest order_value per order_id
    df_t1_unique = (
        df_t1.sort_values('order_value', ascending=False)
        .drop_duplicates(subset='order_id')
    )
    df_t2_unique = (
        df_t2.sort_values('order_value', ascending=False)
        .drop_duplicates(subset='order_id')
    )

    # ✅ Accurate KPIs
    orders_t1 = df_t1_unique['order_id'].nunique()
    orders_t2 = df_t2_unique['order_id'].nunique()
    revenue_t1 = df_t1_unique['order_value'].sum()
    revenue_t2 = df_t2_unique['order_value'].sum()
    aov_t1 = revenue_t1 / orders_t1 if orders_t1 > 0 else 0
    aov_t2 = revenue_t2 / orders_t2 if orders_t2 > 0 else 0
    sku_t1 = df_t1['product_sku'].nunique()
    sku_t2 = df_t2['product_sku'].nunique()

    row = {
        "Time": label,
        "Orders_T1": arrow_colored(orders_t1, orders_t2),
        "Orders_T2": f"{orders_t2:,}" if orders_t2 > 0 else "-",
        "Revenue_T1": arrow_colored(revenue_t1, revenue_t2),
        "Revenue_T2": f"{revenue_t2:,.0f}" if revenue_t2 > 0 else "-",
        "AOV_T1": arrow_colored(aov_t1, aov_t2),
        "AOV_T2": f"{aov_t2:,.0f}" if aov_t2 > 0 else "-",
        "SKU_T1": arrow_colored(sku_t1, sku_t2),
        "SKU_T2": f"{sku_t2:,}" if sku_t2 > 0 else "-"
    }
    rows.append(row)

kpi_df = pd.DataFrame(rows)

# Render table in HTML
def render_kpi_table(df):
    html = """
    <style>
    table.kpi-matrix {
        border-collapse: collapse;
        width: 100%;
        font-size: 15px;
    }
    table.kpi-matrix th, table.kpi-matrix td {
        border: 1px solid #ccc;
        padding: 6px 10px;
        text-align: center;
    }
    table.kpi-matrix th {
        background-color: #f2f2f2;
        font-weight: 600;
    }
    </style>
    <table class='kpi-matrix'>
        <thead>
            <tr>
                <th rowspan="2">KPI</th>
                <th colspan="2">Total Orders</th>
                <th colspan="2">Total Revenue</th>
                <th colspan="2">Avg Order Value</th>
                <th colspan="2">Unique SKUs</th>
            </tr>
            <tr>
                <th>T-1</th><th>T-2</th>
                <th>T-1</th><th>T-2</th>
                <th>T-1</th><th>T-2</th>
                <th>T-1</th><th>T-2</th>
            </tr>
        </thead>
        <tbody>
    """
    for _, row in df.iterrows():
        html += f"<tr><td>{row['Time']}</td>"
        html += f"<td>{row['Orders_T1']}</td><td>{row['Orders_T2']}</td>"
        html += f"<td>{row['Revenue_T1']}</td><td>{row['Revenue_T2']}</td>"
        html += f"<td>{row['AOV_T1']}</td><td>{row['AOV_T2']}</td>"
        html += f"<td>{row['SKU_T1']}</td><td>{row['SKU_T2']}</td></tr>"
    html += "</tbody></table>"
    return html

st.markdown(render_kpi_table(kpi_df), unsafe_allow_html=True)

# ------------------ SIDEBAR DATE FILTER ------------------
st.sidebar.header("📅 Filter by Date")

despatch_date_range = st.sidebar.date_input("Despatch Date Range", [])
despatch_quick = st.sidebar.selectbox("🕒 Quick Despatch Date Range", [
    "None", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
])

order_date_range = st.sidebar.date_input("Order Date Range", [])
order_quick = st.sidebar.selectbox("🕒 Quick Order Date Range", [
    "None", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
])

# --- Helper Function ---
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

despatch_dates = sorted(df['despatch_date'].dropna().unique())
order_dates = sorted(df['order_date'].dropna().unique())

# --- Final Despatch Date Range (Replicating Page 2 Logic) ---
if despatch_quick != "None":
    despatch_start, despatch_end = get_range_from_option(despatch_quick, despatch_dates)
elif len(despatch_date_range) == 1:
    despatch_start = despatch_end = pd.to_datetime(despatch_date_range[0])
elif len(despatch_date_range) == 2:
    despatch_start, despatch_end = pd.to_datetime(despatch_date_range)
else:
    # Same as Page 2: show latest available 30 days by default
    despatch_end = max(despatch_dates) if despatch_dates else datetime.today()
    despatch_start = despatch_end - timedelta(days=30)

# --- Final Order Date Range (Optional only when filtered) ---
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

# ------------------ GAP BEFORE ------------------
st.markdown("<br>", unsafe_allow_html=True)

# ------------------ CHANNEL FILTER + DEBUG (Same Line) ------------------

# Prepare channel filter options first
channels = sorted(df['order_channel'].dropna().unique().tolist())
all_option = "Select All"
channels_with_all = [all_option] + channels

# Now layout row with 2 columns
col1, col2 = st.columns([0.40, 0.60])

with col1:
    selected_channels = st.multiselect(
        "📦 Select Sales Channel(s)",
        options=channels_with_all,
        default=[all_option]
    )
    if all_option in selected_channels or not selected_channels:
        selected_channels = channels
    
with col2:
    despatch_info = f"📦 <b>Despatch Date:</b> {despatch_start.strftime('%Y-%m-%d')} → {despatch_end.strftime('%Y-%m-%d')}"
    order_info = (
        f"📑 <b>Order Date:</b> {order_start.strftime('%Y-%m-%d')} → {order_end.strftime('%Y-%m-%d')}"
        if apply_order_filter
        else "📑 <b>Order Date:</b> Not Selected"
    )
    
    st.markdown(f"""
        <div style='display: flex; align-items: center; height: 100%; font-size: 16px; padding-top: 12px;'>
            {despatch_info}&nbsp;&nbsp;&nbsp;&nbsp;{order_info}
        </div>
    """, unsafe_allow_html=True)


# ------------------ GAP AFTER ------------------
st.markdown("<br>", unsafe_allow_html=True)

# ------------------ APPLY FILTERS ------------------
filtered_df = df[
    (df['despatch_date'].between(despatch_start, despatch_end)) &
    (df['order_channel'].isin(selected_channels))
]

if apply_order_filter:
    filtered_df = filtered_df[filtered_df['order_date'].between(order_start, order_end)]

if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# ------------------ BUSINESS METRICS (Corrected) ------------------

# Step 1: De-duplicate based on highest order_value per order_id (safe method)
dedup_orders = (
    filtered_df
    .sort_values('order_value', ascending=False)
    .drop_duplicates(subset='order_id')
)

# Step 2: Apply correct logic
total_orders = dedup_orders['order_id'].nunique()
total_revenue = dedup_orders['order_value'].sum()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

# Step 3: Independent metrics
unique_product_skus = filtered_df['product_sku'].nunique()
total_quantity_ordered = filtered_df['product_qty'].sum()

# Step 4: Display
col1, col2, col3, col4, col5 = st.columns(5)
col1.markdown(f"**🛒 Total Orders**<br><span style='font-size: 20px;'>{total_orders:,}</span>", unsafe_allow_html=True)
col2.markdown(f"**💰 Total Revenue**<br><span style='font-size: 20px;'>£ {total_revenue:,.2f}</span>", unsafe_allow_html=True)
col3.markdown(f"**📦 Avg Order Value**<br><span style='font-size: 20px;'>£ {avg_order_value:,.2f}</span>", unsafe_allow_html=True)
col4.markdown(f"**🔢 Unique SKUs**<br><span style='font-size: 20px;'>{unique_product_skus:,}</span>", unsafe_allow_html=True)
col5.markdown(f"**📦 Total Quantity**<br><span style='font-size: 20px;'>{total_quantity_ordered:,}</span>", unsafe_allow_html=True)

# ------------------ VISUALIZATIONS ------------------
st.subheader("📈 Revenue Trend Over Time")
df_line = dedup_orders.groupby('order_date')['order_value'].sum().reset_index()
fig_line = px.line(df_line, x='order_date', y='order_value', title="Order Value Over Time")
st.plotly_chart(fig_line, use_container_width=True)

channel_summary = dedup_orders.groupby('order_channel').agg(
    total_orders_value=('order_value', 'sum'),
    orders_count=('order_id', 'nunique')
).reset_index()

st.subheader("📊 Total Orders Value by Channel")
fig_value_bar = px.bar(channel_summary, x="order_channel", y="total_orders_value", text="total_orders_value")
st.plotly_chart(fig_value_bar, use_container_width=True)

st.subheader("📦 Orders Count by Channel")
fig_count_bar = px.bar(channel_summary, x="order_channel", y="orders_count", text="orders_count")
st.plotly_chart(fig_count_bar, use_container_width=True)

st.subheader("🍩 Revenue Share by Channel")
fig_donut_value = px.pie(channel_summary, names='order_channel', values='total_orders_value', hole=0.4)
st.plotly_chart(fig_donut_value, use_container_width=True)

st.subheader("🍩 Orders Count Share by Channel")
fig_donut_count = px.pie(channel_summary, names='order_channel', values='orders_count', hole=0.4)
st.plotly_chart(fig_donut_count, use_container_width=True)
