# pages/5_routine_reports.py

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.supplier_cleaning import clean_supplier_excel
from utils.supplier_analysis import generate_insights
import streamlit_authenticator as stauth
from auth_config import credentials

st.set_page_config(page_title="📊 Routine Reports", layout="wide")
st.title("📊 Routine Reports Suite")

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

#---------------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs([
    "🧾 Channel-wise Invoices", 
    "🔄 Mintsoft vs Opera Delta Report", 
    "📦 Supplier Sales Analysis"
])

# --- Channel-wise Invoice
with tab1:
    st.title("📦 Channel-wise SKU Invoices")
    uploaded_file = st.file_uploader("Upload Channel-wise Invoice file", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        st.dataframe(df.head())

        channel_col = df.columns[0]
        channels = df[channel_col].unique()
        col_layout = st.columns(2)

        for idx, channel in enumerate(channels):
            filtered_df = df[df[channel_col] == channel]
            summary = filtered_df.groupby("product_sku").agg(
                total_qty=('product_qty', 'sum'),
                total_value=('order_value', 'sum')
            ).reset_index()

            with col_layout[idx % 2]:
                st.subheader(f"🔹 Channel: {channel}")
                st.dataframe(summary, use_container_width=True)
                csv = summary.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download CSV", data=csv, file_name=f"{channel}_summary.csv", mime='text/csv')

# --- Mintsoft vs Opera Delta
with tab2:
    st.title("🔄 Delta Report: Mintsoft vs Opera Stock")
    col1, col2 = st.columns(2)
    with col1:
        opera_file = st.file_uploader("Upload Opera Stock (.xlsx)", type=["xlsx"])
    with col2:
        mintsoft_file = st.file_uploader("Upload Mintsoft Export (.xlsx)", type=["xlsx"])

    if opera_file and mintsoft_file:
        try:
            opera_df = pd.read_excel(opera_file, header=0)
            opera_df.columns = [col.strip().lower().replace("  ", " ").replace("_", " ") for col in opera_df.columns]
            sku_col = next((col for col in opera_df.columns if "stock reference" in col), None)
            stock_col = next((col for col in opera_df.columns if "free stock quantity" in col), None)

            if not sku_col or not stock_col:
                st.error("❌ 'Opera Stock' file must contain columns like 'Stock Reference' and 'Free Stock Quantity'")
                st.write("🔍 Detected columns:", opera_df.columns.tolist())
                st.stop()

            opera_df = opera_df[[sku_col, stock_col]].rename(columns={sku_col: 'SKU', stock_col: 'Opera_Stock'})
            mintsoft_df = pd.read_excel(mintsoft_file)
            mintsoft_df = mintsoft_df[['ProductSKU', 'Location', 'Quantity']].rename(
                columns={'ProductSKU': 'SKU', 'Quantity': 'Mintsoft_Quantity'}
            )

            opera_df['SKU'] = opera_df['SKU'].astype(str)
            mintsoft_df['SKU'] = mintsoft_df['SKU'].astype(str)
            opera_df['Opera_Stock'] = opera_df['Opera_Stock'].apply(lambda x: max(x, 0))

            mintsoft_total = mintsoft_df.groupby('SKU')['Mintsoft_Quantity'].sum().reset_index()
            mintsoft_total.rename(columns={'Mintsoft_Quantity': 'Total_Mintsoft_Stock'}, inplace=True)

            delta_df = opera_df.merge(mintsoft_total, on='SKU', how='inner')
            delta_df['Delta_Stock'] = delta_df['Opera_Stock'] - delta_df['Total_Mintsoft_Stock']

            final_report_list = []

            for _, row in delta_df.iterrows():
                sku = row['SKU']
                delta_stock = row['Delta_Stock']
                mintsoft_locations = mintsoft_df[mintsoft_df['SKU'] == sku]

                if delta_stock > 0:
                    for _, loc_row in mintsoft_locations.iterrows():
                        final_report_list.append({
                            'Client': 'MPTC',
                            'SKU': sku,
                            'Warehouse': 'Main',
                            'Location': loc_row['Location'],
                            'BestBefore': '',
                            'BatchNo': '',
                            'SerialNo': '',
                            'Quantity': delta_stock,
                            'Comment': 'Quantity added to inventory'
                        })
                        break
                elif delta_stock < 0:
                    remaining_delta = abs(delta_stock)
                    mintsoft_locations = mintsoft_locations.sort_values(by=['Mintsoft_Quantity', 'Location'])
                    for _, loc_row in mintsoft_locations.iterrows():
                        if remaining_delta <= 0:
                            break
                        loc_quantity = loc_row['Mintsoft_Quantity']
                        reduce_quantity = min(loc_quantity, remaining_delta)
                        remaining_delta -= reduce_quantity
                        final_report_list.append({
                            'Client': 'MPTC',
                            'SKU': sku,
                            'Warehouse': 'Main',
                            'Location': loc_row['Location'],
                            'BestBefore': '',
                            'BatchNo': '',
                            'SerialNo': '',
                            'Quantity': -reduce_quantity,
                            'Comment': 'Quantity removed from inventory'
                        })

            final_report = pd.DataFrame(final_report_list)
            final_report = final_report[final_report['Quantity'] != 0]

            st.subheader("📌 Final Delta Report Preview")
            st.dataframe(final_report, use_container_width=True)
            today_str = datetime.now().strftime("%d-%b-%Y")
            csv = final_report.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV",
                data=csv,
                file_name=f"Final_Delta_Report_{today_str}.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"❌ Error processing files: {e}")

# --- Supplier Sales Analysis
with tab3:
    st.title("📦 Supplier Sales Analysis")
    st.write("Upload your weekly supplier sales Excel report to generate detailed business insights.")
    supplier_file = st.file_uploader("Upload Excel File", type=["xlsx"], key="supplier_upload")

    if supplier_file:
        df = clean_supplier_excel(supplier_file)
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
