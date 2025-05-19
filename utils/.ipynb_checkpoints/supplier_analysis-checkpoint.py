# utils/supplier_analysis.py

def generate_insights(df):
    summary = {}
    summary["Total Unique Products"] = df["Barcode"].nunique()
    summary["Total Units Sold"] = df["Units Sold"].sum()
    summary["Total Net Sales (Inc VAT)"] = df["Net Sales Inc VAT"].sum()
    summary["Average Price per Unit Sold"] = round(summary["Total Net Sales (Inc VAT)"] / summary["Total Units Sold"], 2)

    grouped = df.groupby(["Barcode", "Product Description"]).agg({
        "Units Sold": "sum",
        "Net Sales Inc VAT": "sum"
    }).reset_index()

    summary["Top Sellers"] = grouped.sort_values("Units Sold", ascending=False).head(10)
    summary["Slow Sellers"] = grouped.sort_values("Units Sold", ascending=True).head(10)
    summary["Top Value Products"] = grouped.sort_values("Net Sales Inc VAT", ascending=False).head(10)
    summary["Returns"] = df[df["Units Sold"] < 0]
    summary["One-Time Sellers"] = df[df["Units Sold"] == 1]
    
    return summary
