# utils/supplier_cleaning.py

import pandas as pd

def clean_supplier_excel(file):
    raw_df = pd.read_excel(file, header=None)
    first_data_row = raw_df[raw_df.iloc[:, 0].astype(str).str.match(r'^\d{7,}$', na=False)].index[0]
    sales_data = raw_df.iloc[first_data_row:].copy()

    clean_columns = [
        "Barcode", "Product Description", "Supplier", "Product Code", "Group", "Colour Code",
        "Colour Description", "Units Per Case", "Code1", "Code2", "Code3", "Code4", "Code5",
        "Code6", "Category", "Brand", "Range", "Code7", "Code8", "Code9",
        "Units Sold", "Net Sales Inc VAT"
    ]
    sales_data = sales_data.iloc[:, :len(clean_columns)]
    sales_data.columns = clean_columns
    sales_data = sales_data[~sales_data["Barcode"].astype(str).str.contains("Total|Grand", na=False)]
    sales_data["Units Sold"] = pd.to_numeric(sales_data["Units Sold"], errors="coerce")
    sales_data["Net Sales Inc VAT"] = pd.to_numeric(sales_data["Net Sales Inc VAT"], errors="coerce")
    return sales_data
