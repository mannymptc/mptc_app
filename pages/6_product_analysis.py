import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.express as px

st.set_page_config(page_title="📊 Product Sales Analysis", layout="wide")
st.title("📦 Product Sales History & Dead Stock")

# ------------------ KPI CSS ------------------
st.markdown("""
    <style>
    .kpi-small .stMetricValue {
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ DB CONNECTION ------------------
def connect_db():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=mptcecommerce-sql-server.database.windows.net;"
        "DATABASE=mptcecommerce-db;"
        "UID=mptcadmin;"
        "PWD=Mptc@2025;"
        "Connection Timeout=60"
    )

# ------------------ LOAD DATA ------------------
@st.cache_data
def load_data():
    conn = connect_db()
    query = """
    SELECT od.order_id, od.product_sku, od.product_name, p.product_category,
           od.order_channel, od.order_date, od.product_qty, od.product_price,
           od.cost_price
    FROM OrdersDespatch od
    LEFT JOIN Products p ON od.product_sku = p.product_sku
    WHERE od.order_date >= '2024-01-01'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['sale_amount'] = df['product_qty'] * df['product_price']
    df['cost_amount'] = df['product_qty'] * df['cost_price']
    return df

df = load_data()
if df.empty:
    st.stop()

# ------------------ SIDEBAR DATE FILTERS ------------------
today = df['order_date'].max()
default_start = today - timedelta(days=30)
default_end = today

custom_range = st.sidebar.date_input("📅 Custom Order Date Range", value=(default_start, default_end))
quick_range = st.sidebar.selectbox("⏱ Quick Order Date Range", [
    "None", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
], index=0)

use_custom_range = isinstance(custom_range, tuple) and len(custom_range) == 2 and custom_range[0] != custom_range[1]

if use_custom_range:
    start_date, end_date = pd.to_datetime(custom_range[0]), pd.to_datetime(custom_range[1])
elif quick_range != "None":
    days_map = {
        "Last 7 Days": 7,
        "Last 30 Days": 30,
        "Last 3 Months": 90,
        "Last 6 Months": 180,
        "Last 12 Months": 365
    }
    end_date = today
    start_date = today - timedelta(days=days_map[quick_range])
else:
    start_date = default_start
    end_date = default_end

st.sidebar.caption(f"📆 Showing data from {start_date.date()} to {end_date.date()}")

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Sales History", "🧊 Unsold / Dead Stock", "📈 Advance Product Analysis", "📈 Advance Channel Analysis"])

# ------------------ TAB 1: SALES HISTORY ------------------
with tab1:

    # ---- Smart Filters ----
    col1, col2, col3 = st.columns(3)
    with col1: sku_input = st.text_input("🔍 SKU Filter")
    with col2: name_input = st.text_input("🔍 Name Filter")
    with col3: cat_input = st.text_input("🔍 Category Filter")

    filtered_df = df.copy()
    if sku_input:
        filtered_df = filtered_df[filtered_df['product_sku'].str.contains(sku_input, case=False, na=False)]
    if name_input:
        filtered_df = filtered_df[filtered_df['product_name'].str.contains(name_input, case=False, na=False)]
    if cat_input:
        filtered_df = filtered_df[filtered_df['product_category'].str.contains(cat_input, case=False, na=False)]

    filtered_df = filtered_df[filtered_df['order_date'].between(start_date, end_date)]
    if filtered_df.empty:
        st.warning("No data for selected filters.")
        st.stop()

    # ---- KPIs ----
    font_size_px = 20
    st.markdown(f"""
    <style>
    .kpi-box {{
        font-size: {font_size_px}px;
        text-align: center;
        padding: 6px;
        line-height: 1.2;
    }}
    .kpi-box .label {{ font-weight: bold; }}
    .kpi-box .value {{ font-weight: normal; }}
    </style>
    """, unsafe_allow_html=True)

    days_range = (end_date - start_date).days + 1
    total_qty = filtered_df['product_qty'].sum()
    total_rev = filtered_df['sale_amount'].sum()
    total_cost = filtered_df['cost_amount'].sum()
    avg_qty_mo = total_qty / (days_range / 30)
    avg_rev_mo = total_rev / (days_range / 30)

    labels = ["🔢 Qty Sold", "💰 Revenue", "💸 Cost", "📅 Days", "📦 Avg Qty/mo", "💵 Avg Rev/mo"]
    values = [f"{int(total_qty)}", f"£ {total_rev:,.2f}", f"£ {total_cost:,.2f}",
              f"{days_range}", f"{avg_qty_mo:.1f}", f"£ {avg_rev_mo:.1f}"]

    cols = st.columns(6)
    for col, label, value in zip(cols, labels, values):
        with col:
            st.markdown(f"""
            <div class="kpi-box">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    # ---- Channel Summary Table ----
    st.markdown("### 📊 Channel-wise Sales")
    summary = (
        filtered_df.groupby('order_channel')
        .agg(
            total_orders=('order_id', pd.Series.nunique),
            total_qty=('product_qty', 'sum'),
            total_revenue=('sale_amount', 'sum')
        ).reset_index()
    )
    total_row = pd.DataFrame({
        'order_channel': ['Grand Total'],
        'total_orders': [summary['total_orders'].sum()],
        'total_qty': [summary['total_qty'].sum()],
        'total_revenue': [summary['total_revenue'].sum()]
    })
    channel_table = pd.concat([summary, total_row]).reset_index(drop=True)

    styled_channel = channel_table.style.set_properties(**{
        'text-align': 'center'
    }).set_table_styles([
        {'selector': 'th', 'props': [('font-weight', 'bold'), ('text-align', 'center')]}
    ]).apply(lambda x: ['font-weight: bold' if x.name == len(channel_table) - 1 else '' for _ in x], axis=1)

    st.dataframe(styled_channel, use_container_width=True, height=350)

    # ---- Weekly History (Qty & Revenue) ----
    past_df = filtered_df.copy()
    today = df['order_date'].max()
    past_df = past_df[past_df['order_date'] >= today - timedelta(days=365)].copy()
    past_df['Month'] = past_df['order_date'].dt.strftime("%b-%y")
    past_df['Week'] = "W" + past_df['order_date'].dt.isocalendar().week.astype(str)
    past_df['SKU'] = past_df['product_sku']
    past_df['Name'] = past_df['product_name']

    def make_history_matrix(df, value_col):
        pivot = df.pivot_table(index=['Month', 'Week'], columns='SKU', values=value_col, aggfunc='sum')
        pivot = pivot.sort_index(ascending=False).fillna("-")
        sku_names = df[['SKU', 'Name']].drop_duplicates().set_index('SKU')['Name'].to_dict()
        pivot.columns = pd.MultiIndex.from_tuples([(sku, sku_names.get(sku, '')) for sku in pivot.columns])
        return pivot

    qty_matrix = make_history_matrix(past_df, 'product_qty')
    rev_matrix = make_history_matrix(past_df, 'sale_amount')

    st.markdown("#### 📦 Sales Quantity History")
    st.dataframe(qty_matrix, use_container_width=True, height=350)

    st.markdown("#### 💰 Revenue History")
    st.dataframe(rev_matrix, use_container_width=True, height=350)

    # ---- Raw Filtered Data ----
    row1, row2 = st.columns([0.8, 0.2])
    with row1:
        st.markdown("### 📄 Raw Filtered Sales Data")
    with row2:
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, file_name="filtered_sales_data.csv", mime="text/csv", use_container_width=True)

    st.dataframe(filtered_df, use_container_width=True, height=350)

# ------------------ TAB 2: DEAD STOCK ------------------
with tab2:
    from dateutil.relativedelta import relativedelta

    # 1. Calculate last sold dates
    last_sold = df.groupby(['product_sku', 'product_name'])['order_date'].max().reset_index()
    last_sold['Days Since Last Sale'] = (pd.Timestamp.now().normalize() - last_sold['order_date']).dt.days
    last_sold['Last Sold'] = last_sold['order_date'].dt.strftime('%Y-%m-%d')

    def time_since(date):
        delta = relativedelta(datetime.now().date(), date)
        parts = []
        if delta.years: parts.append(f"{delta.years} yr{'s' if delta.years > 1 else ''}")
        if delta.months: parts.append(f"{delta.months} mo")
        if delta.days: parts.append(f"{delta.days} d")
        return " ".join(parts) if parts else "Today"

    last_sold['Time Since Last Sale'] = pd.to_datetime(last_sold['order_date']).dt.date.apply(time_since)

    # 2. Define unsold age buckets
    unsold_buckets = {
        "7 days to 1 month": (7, 30),
        "1 to 3 months": (31, 90),
        "3 to 6 months": (91, 180),
        "6 months to 1 year": (181, 365),
        "more than 1 year": (366, float("inf"))
    }

    def assign_bucket(days):
        for bucket, (min_d, max_d) in unsold_buckets.items():
            if min_d <= days <= max_d:
                return bucket
        return None

    last_sold['Bucket'] = last_sold['Days Since Last Sale'].apply(assign_bucket)

    # 3. SKU Count KPI by bucket
    bucket_order = list(unsold_buckets.keys())
    bucket_counts = (
        last_sold.groupby('Bucket')['product_sku'].nunique()
        .reindex(bucket_order)
        .reset_index()
        .fillna(0)
    )
    bucket_counts.columns = ['Bucket', 'Unique SKU Count']

    # Row: Filter (left) + KPIs (right)
    row = st.columns([2] + [1 for _ in range(len(bucket_counts))])

    with row[0]:
        selected_buckets = st.multiselect(
            "📅 Select Unsold Time Range(s) to View Table",
            options=bucket_order,
            default=["1 to 3 months"]
        )

    for i, (_, r) in enumerate(bucket_counts.iterrows(), 1):
        bucket, count = r['Bucket'], r['Unique SKU Count']
        with row[i]:
            st.markdown(
                f"""
                <div style='text-align: center; font-size:17px; font-weight:600;'>{bucket}</div>
                <div style='text-align: center; font-size:20px; margin-top:4px;'>{int(count)} SKUs</div>
                """,
                unsafe_allow_html=True
            )

    # 4. Dead Stock Table based on selected buckets
    if not selected_buckets:
        st.warning("Please select at least one range.")
    else:
        dead_stock = last_sold[last_sold['Bucket'].isin(selected_buckets)].copy()
        if dead_stock.empty:
            st.info("✅ No dead stock found.")
        else:
            row1, row2 = st.columns([0.8, 0.2])
            with row1:
                st.markdown("### 🧾 Dead Stock List")
            with row2:
                csv_dead = dead_stock.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download CSV",
                    csv_dead,
                    file_name="dead_stock.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
            # Select relevant columns and reset index for display
            dead_table = dead_stock[[
                'product_sku',
                'product_name',
                'Bucket',
                'Last Sold',
                'Days Since Last Sale',
                'Time Since Last Sale'
            ]].reset_index(drop=True)
    
            # Display plain dataframe
            st.dataframe(dead_table, use_container_width=True, height=500)

# ---- Charts ----
   
    # Define desired sort order
    bucket_order = [
        "7 days to 1 month",
        "1 to 3 months",
        "3 to 6 months",
        "6 months to 1 year",
        "more than 1 year"
    ]
    
    # 1. Bar Chart
    bar_fig = px.bar(
        bucket_counts,
        x="Bucket",
        y="Unique SKU Count",
        title="🧊 Unsold SKU Count by Time Bucket",
        text="Unique SKU Count",
        category_orders={"Bucket": bucket_order}
    )
    bar_fig.update_traces(textposition="outside")
    bar_fig.update_layout(height=700)
    
    # 2. Box Plot
    box_data = last_sold.dropna(subset=['Bucket'])
    box_fig = px.box(
        box_data,
        x="Bucket",
        y="Days Since Last Sale",
        points="all",
        color="Bucket",
        title="📦 Days Since Last Sale Distribution",
        category_orders={"Bucket": bucket_order}
    )
    box_fig.update_layout(height=700)
    
    # Display side-by-side
    col1, col2 = st.columns(2)
    col1.plotly_chart(bar_fig, use_container_width=True)
    col2.plotly_chart(box_fig, use_container_width=True)
    
    # ---- Category Summary ----
    st.markdown("### 🧯 Unsold SKU Count by Product Category")
    df_with_cat = df.dropna(subset=['product_category'])
    sku_cat_map = df_with_cat[['product_sku', 'product_category']].drop_duplicates()
    dead_skus = pd.merge(last_sold.dropna(subset=['Bucket']), sku_cat_map, on='product_sku', how='left')
    
    category_counts = (
        dead_skus.groupby('product_category')['product_sku']
        .nunique()
        .reset_index()
        .rename(columns={'product_sku': 'Unsold SKU Count'})
        .sort_values(by='Unsold SKU Count', ascending=False)
    )
    
    st.dataframe(category_counts, use_container_width=True)
    
    fig_cat = px.bar(
        category_counts,
        x="product_category",
        y="Unsold SKU Count",
        title="📊 Unsold SKUs by Category",
        text="Unsold SKU Count"
    )
    fig_cat.update_traces(textposition="outside")
    fig_cat.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig_cat, use_container_width=True)


# ------------------ TAB 3: ADVANCE ANALYSIS ------------------
with tab3:
    st.markdown("## 📈 Product ABC Analysis (by Quantity Sold)")

    # ------------------ FILTERS ------------------
    st.markdown("### Smart Filters")
    col1, col2, col3 = st.columns(3)
    with col1: sku_filter = st.text_input("SKU")
    with col2: name_filter = st.text_input("Name")
    with col3: cat_filter = st.text_input("Category")

    # Filter data from already-loaded df
    df_filtered = df[df['order_date'].between(start_date, end_date)].copy()
    if sku_filter:
        df_filtered = df_filtered[df_filtered['product_sku'].str.contains(sku_filter, case=False, na=False)]
    if name_filter:
        df_filtered = df_filtered[df_filtered['product_name'].str.contains(name_filter, case=False, na=False)]
    if cat_filter:
        df_filtered = df_filtered[df_filtered['product_category'].str.contains(cat_filter, case=False, na=False)]

    # ------------------ ABC ANALYSIS BY QTY ------------------
    def compute_abc_qty(df):
        qty_df = df.groupby(['product_sku', 'product_name'])['product_qty'].sum().reset_index()
        qty_df = qty_df.sort_values(by='product_qty', ascending=False).reset_index(drop=True)
        qty_df['cumulative_qty'] = qty_df['product_qty'].cumsum()
        total_qty = qty_df['product_qty'].sum()
        qty_df['cumulative_pct'] = qty_df['cumulative_qty'] / total_qty

        def label_class(p):
            if p <= 0.7:
                return 'A'
            elif p <= 0.9:
                return 'B'
            else:
                return 'C'

        qty_df['ABC_Class'] = qty_df['cumulative_pct'].apply(label_class)
        return qty_df

    abc_all = compute_abc_qty(df_filtered)

    # ------------------ SECTION: PRODUCT WISE ABC ------------------
    st.markdown("## 🧾 Product wise ABC Analysis")
    col1, col2 = st.columns([0.5, 0.5])

    with col1:
        pie = px.pie(
            abc_all.groupby('ABC_Class')['product_qty'].sum().reset_index(),
            names='ABC_Class',
            values='product_qty',
            title="ABC for All Products (by Qty Sold)",
            hole=0.45
        )
        st.plotly_chart(pie, use_container_width=True)

    with col2:
        st.dataframe(abc_all, use_container_width=True, height=400)
        csv_all = abc_all.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download ABC Table", csv_all, file_name="abc_all_qty.csv", mime="text/csv")

    # ------------------ SECTION: A, B, C CATEGORY ------------------
    def show_category_section(letter):
        st.markdown(f"### 🅰️ Category {letter}'s ABC Analysis")
        df_cat = abc_all[abc_all['ABC_Class'] == letter]
        col1, col2 = st.columns([0.5, 0.5])

        with col1:
            if not df_cat.empty:
                pie = px.pie(df_cat, names='product_sku', values='product_qty', title=f"Category {letter} - Qty Share", hole=0.45)
                st.plotly_chart(pie, use_container_width=True)
            else:
                st.info(f"No products found in Category {letter}.")

        with col2:
            st.dataframe(df_cat, use_container_width=True, height=400)
            csv_cat = df_cat.to_csv(index=False).encode("utf-8")
            st.download_button(f"⬇️ Download Category {letter}", csv_cat, file_name=f"abc_{letter}_qty.csv", mime="text/csv")

    show_category_section('A')
    show_category_section('B')
    show_category_section('C')

# ------------------ TAB 4: ADVANCE CHANNEL ANALYSIS ------------------
with tab4:
    st.markdown("## 📈 Channel-wise ABC Analysis")

    # ------------------ Smart Filters ------------------
    col1, col2, col3 = st.columns(3)
    with col1: sku_filter = st.text_input("SKU", key="channel_sku")
    with col2: name_filter = st.text_input("Name", key="channel_name")
    with col3: cat_filter = st.text_input("Category", key="channel_cat")

    df_filtered = df[df['order_date'].between(start_date, end_date)].copy()
    if sku_filter:
        df_filtered = df_filtered[df_filtered['product_sku'].str.contains(sku_filter, case=False, na=False)]
    if name_filter:
        df_filtered = df_filtered[df_filtered['product_name'].str.contains(name_filter, case=False, na=False)]
    if cat_filter:
        df_filtered = df_filtered[df_filtered['product_category'].str.contains(cat_filter, case=False, na=False)]

    # ------------------ ABC BY TOTAL QTY SOLD (BY CHANNEL) ------------------
    st.markdown("### 🔢 ABC of All Channels by Quantity Sold")

    qty_by_channel = df_filtered.groupby('order_channel')['product_qty'].sum().reset_index().rename(columns={'product_qty': 'total_qty'})
    qty_by_channel = qty_by_channel.sort_values(by='total_qty', ascending=False).reset_index(drop=True)
    qty_by_channel['cumulative_qty'] = qty_by_channel['total_qty'].cumsum()
    total_qty = qty_by_channel['total_qty'].sum()
    qty_by_channel['cumulative_pct'] = qty_by_channel['cumulative_qty'] / total_qty

    def label_class(p):
        if p <= 0.7: return 'A'
        elif p <= 0.9: return 'B'
        else: return 'C'

    qty_by_channel['ABC_Class'] = qty_by_channel['cumulative_pct'].apply(label_class)

    pie_qty = px.pie(
        qty_by_channel,
        names='order_channel', values='total_qty', title="ABC by Quantity Sold (Channels)", hole=0.45,
        color='ABC_Class'
    )

    col1, col2 = st.columns([0.5, 0.5])
    with col1:
        st.plotly_chart(pie_qty, use_container_width=True)
    with col2:
        st.dataframe(qty_by_channel, use_container_width=True, height=400)
        csv_qty = qty_by_channel.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download ABC Qty Table", csv_qty, file_name="abc_qty_by_channel.csv", mime="text/csv")

    # ------------------ ABC BY REVENUE (BY CHANNEL) ------------------
    st.markdown("### 💰 ABC of All Channels by Revenue")

    # Calculate revenue only once per unique order
    order_revenue = df_filtered.groupby('order_id').agg({
        'order_channel': 'first',
        'sale_amount': 'sum'
    }).reset_index()

    revenue_by_channel = order_revenue.groupby('order_channel')['sale_amount'].sum().reset_index().rename(columns={'sale_amount': 'total_revenue'})
    revenue_by_channel = revenue_by_channel.sort_values(by='total_revenue', ascending=False).reset_index(drop=True)
    revenue_by_channel['cumulative_rev'] = revenue_by_channel['total_revenue'].cumsum()
    total_rev = revenue_by_channel['total_revenue'].sum()
    revenue_by_channel['cumulative_pct'] = revenue_by_channel['cumulative_rev'] / total_rev
    revenue_by_channel['ABC_Class'] = revenue_by_channel['cumulative_pct'].apply(label_class)

    pie_rev = px.pie(
        revenue_by_channel,
        names='order_channel', values='total_revenue', title="ABC by Revenue (Channels)", hole=0.45,
        color='ABC_Class'
    )

    col1, col2 = st.columns([0.5, 0.5])
    with col1:
        st.plotly_chart(pie_rev, use_container_width=True)
    with col2:
        st.dataframe(revenue_by_channel, use_container_width=True, height=400)
        csv_rev = revenue_by_channel.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download ABC Revenue Table", csv_rev, file_name="abc_revenue_by_channel.csv", mime="text/csv")

    # ------------------ INDIVIDUAL CHANNEL TABLES (BY QTY ABC) ------------------
    st.markdown("### 🧾 Individual Channel Tables (by Quantity Sold)")
    grouped = df_filtered.groupby(['order_channel', 'product_sku', 'product_name'])['product_qty'].sum().reset_index()
    grouped = grouped.sort_values(['order_channel', 'product_qty'], ascending=[True, False])

    def assign_abc_per_channel(df):
        df = df.copy()
        df['cumulative'] = df.groupby('order_channel')['product_qty'].cumsum()
        df['total'] = df.groupby('order_channel')['product_qty'].transform('sum')
        df['cumulative_pct'] = df['cumulative'] / df['total']
        df['ABC_Class'] = df['cumulative_pct'].apply(label_class)
        return df

    channel_sku_abc = assign_abc_per_channel(grouped)

    for ch in channel_sku_abc['order_channel'].unique():
        st.markdown(f"#### 📦 Channel: {ch}")
        ch_df = channel_sku_abc[channel_sku_abc['order_channel'] == ch][['product_sku', 'product_name', 'product_qty', 'ABC_Class']]
        st.dataframe(ch_df, use_container_width=True, height=300)
        csv_ch = ch_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"⬇️ Download {ch} ABC", csv_ch, file_name=f"abc_qty_{ch}.csv", mime="text/csv")
