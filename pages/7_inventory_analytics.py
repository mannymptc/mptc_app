from io import BytesIO
import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
from io import StringIO
import xlsxwriter
import streamlit_authenticator as stauth
from auth_config import credentials

st.set_page_config(page_title="📈 Inventory Forecast & Planning", layout="wide")
st.title("🗓️ Inventory Forecast & Planning")

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

# ------------------ DB CONNECTION ------------------
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
    query = """
    SELECT 
        od.order_id,
        od.product_sku,
        od.product_name,
        p.product_category,
        od.order_date,
        od.product_qty
    FROM OrdersDespatch od
    LEFT JOIN Products p ON od.product_sku = p.product_sku
    WHERE od.order_date >= '2024-01-01'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df

# ------------------ UTILITY: EXPORT SALES MATRICES TO EXCEL ------------------
def export_sales_matrices_to_excel(matrices_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sku, (product_name, sales_data) in matrices_dict.items():
            # Find max week length across months
            max_weeks = max(len(weeks) for weeks in sales_data.values())
            
            # Pad each month’s week list with zeros
            padded_sales_data = {
                month: weeks + [0] * (max_weeks - len(weeks))
                for month, weeks in sales_data.items()
            }
            
            matrix_df = pd.DataFrame(padded_sales_data)
            matrix_df.index = [f"w{i+1}" for i in range(max_weeks)]
            matrix_df = matrix_df.T  # Transpose to get months as rows

            # Safe sheet name
            sheet_name = str(sku)[:31]
            matrix_df.to_excel(writer, sheet_name=sheet_name)
    output.seek(0)
    return output

# ------------------ UTILITY: GENERATE HTML TABLE ------------------
def generate_html_table(df, title, highlight_cols=None):
    highlight_cols = highlight_cols or []
    table_style = """
    <style>
    .custom-table {
        border-collapse: collapse;
        width: 100%;
        font-size: 14px;
    }
    .custom-table th, .custom-table td {
        border: 1px solid #ccc;
        padding: 6px 10px;
        text-align: center;
    }
    .custom-table th {
        background-color: #f2f2f2;
    }
    .custom-table .highlight {
        background-color: #c9daf8;
        font-weight: bold;
    }
    </style>
    """

    # Only add heading if title is not empty
    html = table_style
    if title:
        html += f"<h4 style='margin-bottom: 8px;'>{title}</h4>"

    html += "<table class='custom-table'><thead><tr>"
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            val = row[col]
            style = "highlight" if col in highlight_cols else ""
            html += f"<td class='{style}'>{round(val, 1) if isinstance(val, float) else val}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html

# ------------------ LOAD DATA ------------------
df = load_data()
if df.empty:
    st.stop()
today = pd.to_datetime(df['order_date'].max())

# ------------------ FILTERS ------------------
st.markdown("### 🌟 Smart Search Filters")
col1, col2, col3 = st.columns(3)
with col1:
    sku_input = st.text_input("🔍 SKU Filter")
with col2:
    name_input = st.text_input("🔍 Name Filter")
with col3:
    cat_input = st.text_input("🔍 Category Filter")

sku_terms = [term.strip().lower() for term in sku_input.split(',') if term.strip()]
name_terms = [term.strip().lower() for term in name_input.split(',') if term.strip()]
cat_terms = [term.strip().lower() for term in cat_input.split(',') if term.strip()]

filtered_df = df.copy()
if sku_terms:
    sku_mask = pd.Series(False, index=filtered_df.index)
    for term in sku_terms:
        sku_mask |= filtered_df['product_sku'].astype(str).str.lower().str.contains(term)
    filtered_df = filtered_df[sku_mask]
if name_terms:
    name_mask = pd.Series(False, index=filtered_df.index)
    for term in name_terms:
        name_mask |= filtered_df['product_name'].astype(str).str.lower().str.contains(term)
    filtered_df = filtered_df[name_mask]
if cat_terms:
    cat_mask = pd.Series(False, index=filtered_df.index)
    for term in cat_terms:
        cat_mask |= filtered_df['product_category'].astype(str).str.lower().str.contains(term)
    filtered_df = filtered_df[cat_mask]

if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# ------------------ FORECAST SETTINGS ------------------
st.sidebar.markdown("## ⚙️ Forecast Settings")

selected_ranges = st.sidebar.multiselect(
    label="⏳ Forecast Horizon",
    options=["Next 7 Days", "Next 1 Month", "Next 3 Months"],
    default=["Next 1 Month"]
)

safety_pct = st.sidebar.slider(
    "🛆 Safety Stock %",
    min_value=0,
    max_value=100,
    value=10,
    step=1
)

range_map = {
    "Next 7 Days": 7,
    "Next 1 Month": 30,
    "Next 3 Months": 90
}
label_map = {7: "7d", 30: "1mo", 90: "3mo"}

forecast_days_list = [range_map[r] for r in selected_ranges]

if not forecast_days_list:
    st.warning("Please select at least one forecast horizon.")
    st.stop()

# ------------------ RUN FORECAST ------------------

def calculate_forecast_by_range(df, sku_col, date_col, qty_col, ranges, today):
    df[date_col] = pd.to_datetime(df[date_col])
    result = []

    for sku in df[sku_col].unique():
        sku_df = df[df[sku_col] == sku]
        row = {"product_sku": sku}
        for days in ranges:
            base_qty_total = 0
            for i in range(1, days + 1):
                target_date = today + timedelta(days=i)
                past_date = target_date - timedelta(days=365)
                mask = (sku_df[date_col] >= past_date - timedelta(days=3)) & \
                       (sku_df[date_col] <= past_date + timedelta(days=3))
                base_qty_total += sku_df.loc[mask, qty_col].sum()

            base_label = f"base_qty_{label_map[days]}"
            forecast_label = f"forecast_qty_{label_map[days]}"
            row[base_label] = round(base_qty_total, 1)
            row[forecast_label] = round(base_qty_total * 1.05, 1)
        result.append(row)

    return pd.DataFrame(result)

forecast_summary = calculate_forecast_by_range(
    df=filtered_df,
    sku_col='product_sku',
    date_col='order_date',
    qty_col='product_qty',
    ranges=forecast_days_list,
    today=today
)

# Add product names
product_names = filtered_df[['product_sku', 'product_name']].drop_duplicates().set_index('product_sku')
forecast_summary = forecast_summary.set_index('product_sku').join(product_names).reset_index()

# Historical sales summaries
hist_7d = (
    filtered_df[filtered_df['order_date'] >= today - timedelta(days=6)]
    .groupby('product_sku')['product_qty'].sum().rename("qty_last_7d")
)
hist_30d = (
    filtered_df[filtered_df['order_date'] >= today - timedelta(days=29)]
    .groupby('product_sku')['product_qty'].sum().rename("qty_last_1mo")
)
hist_90d = (
    filtered_df[filtered_df['order_date'] >= today - timedelta(days=89)]
    .groupby('product_sku')['product_qty'].sum().rename("qty_last_3mo")
)

forecast_summary = forecast_summary.set_index('product_sku')
forecast_summary = forecast_summary.join([hist_7d, hist_30d, hist_90d])
forecast_summary.reset_index(inplace=True)
forecast_summary.fillna(0, inplace=True)

# ------------------ Generate Forecast Table ------------------
forecast_html = generate_html_table(
    forecast_summary,
    title="",
    highlight_cols=[
        col for col in forecast_summary.columns if col.startswith("forecast_qty_")
    ] + [
        col for col in forecast_summary.columns if col.startswith("base_qty_")
    ]
)

row_f1, row_f2 = st.columns([0.8, 0.2])
with row_f1:
    st.markdown("<h5>🔮 SKU-Level Sales Forecast</h5>", unsafe_allow_html=True)
with row_f2:
    def prepare_forecast_csv(df):
        return df.to_csv(index=False).encode("utf-8")

    forecast_csv = prepare_forecast_csv(forecast_summary)
    st.download_button(
        label="⬇️ Download CSV",
        data=forecast_csv,
        file_name="forecast_summary.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown(forecast_html, unsafe_allow_html=True)

# ------------------ Generate Inventory Table ------------------
rec_df = forecast_summary[['product_sku', 'product_name'] + [f"forecast_qty_{label_map[d]}" for d in forecast_days_list]].copy()

for days in forecast_days_list:
    label = label_map[days]
    avg_daily = rec_df[f"forecast_qty_{label}"] / days
    safety = avg_daily * days * (safety_pct / 100)
    rec_df[f"safety_stock_{label}"] = safety
    rec_df[f"recommended_inventory_{label}"] = rec_df[f"forecast_qty_{label}"] + safety

rec_df['current_inventory'] = 100
main_label = label_map[max(forecast_days_list)]
rec_df['po_quantity'] = rec_df[f"recommended_inventory_{main_label}"] - rec_df['current_inventory']
rec_df['po_quantity'] = rec_df['po_quantity'].apply(lambda x: max(0, round(x)))

inventory_html = generate_html_table(
    rec_df,
    title="",
    highlight_cols=[col for col in rec_df.columns if col.startswith("recommended_inventory_")]
)

row_i1, row_i2 = st.columns([0.8, 0.2])
with row_i1:
    st.markdown("<h5>🧰 Recommended Inventory Planning</h5>", unsafe_allow_html=True)
with row_i2:
    rec_csv = prepare_forecast_csv(rec_df)
    st.download_button(
        label="⬇️ Download CSV",
        data=rec_csv,
        file_name="inventory_recommendation.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown(inventory_html, unsafe_allow_html=True)

# ------------------ SALES MATRIX HTML TABLES ------------------
st.markdown(
    "<h5 style='margin-top: 20px; margin-bottom: 10px;'>📘 Sales History Summary per Product</h5>",
    unsafe_allow_html=True
)

def generate_scrollable_sales_matrix(product_sku, product_name, sales_data):
    html = f"""
    <style>
        .scroll-container {{
            overflow-x: auto;
            padding-bottom: 10px;
        }}
        .sales-table {{
            border-collapse: collapse;
            font-size: 14px;
            margin-bottom: 30px;
            min-width: 900px;
        }}
        .sales-table th, .sales-table td {{
            border: 1px solid #999;
            padding: 6px 10px;
            text-align: center;
        }}
        .sales-table th {{
            background-color: #f2f2f2;
        }}
        .header-row th {{
            background-color: #d9ead3;
            font-weight: bold;
        }}
    </style>

    <h6>🔹 {product_sku} — {product_name}</h6>
    <div class="scroll-container">
    <table class="sales-table">
        <tr class="header-row">
    """
    for month in sales_data.keys():
        html += f'<th colspan="{len(sales_data[month])}">{month}</th>'
    html += '</tr><tr>'
    for month, weeks in sales_data.items():
        for i in range(1, len(weeks) + 1):
            html += f'<th>w{i}</th>'
    html += '</tr><tr>'
    for month, weeks in sales_data.items():
        for qty in weeks:
            html += f'<td>{int(qty)}</td>'
    html += '</tr><tr>'
    for month, weeks in sales_data.items():
        html += f'<td colspan="{len(weeks)}"><b>{int(sum(weeks))}</b></td>'
    html += '</tr></table></div>'
    return html

# Sales matrix generation and collection
all_matrices = {}
for sku in forecast_summary['product_sku'].unique():
    sku_df = filtered_df[filtered_df['product_sku'] == sku].copy()
    if sku_df.empty:
        continue
    product_name = sku_df['product_name'].iloc[0]
    recent_df = sku_df[sku_df['order_date'] >= today - timedelta(days=365)].copy()
    recent_df['month_label'] = recent_df['order_date'].dt.strftime('%b-%y')
    recent_df['week_number'] = recent_df['order_date'].dt.isocalendar().week
    sales_data = {}
    for month in sorted(recent_df['month_label'].unique(), key=lambda m: datetime.strptime(m, "%b-%y")):
        month_df = recent_df[recent_df['month_label'] == month]
        weekly_totals = (
            month_df.groupby('week_number')['product_qty']
            .sum()
            .sort_index()
            .tolist()
        )
        sales_data[month] = weekly_totals
    if not sales_data:
        continue
    all_matrices[sku] = (product_name, sales_data)
    html_output = generate_scrollable_sales_matrix(sku, product_name, sales_data)
    st.markdown(html_output, unsafe_allow_html=True)

# Download Excel of all matrices
if all_matrices:
    excel_file = export_sales_matrices_to_excel(all_matrices)
    st.download_button(
        label="⬇️ Download Sales History Excel",
        data=excel_file,
        file_name="sales_history_matrices.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
