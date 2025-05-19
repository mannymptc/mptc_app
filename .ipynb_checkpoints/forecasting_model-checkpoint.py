import pandas as pd

def forecast_multiple_skus(df, sku_col, date_col, qty_col, forecast_days=30):
    df[date_col] = pd.to_datetime(df[date_col])
    latest_date = df[date_col].max()

    forecast_records = []

    for sku in df[sku_col].unique():
        sku_df = df[df[sku_col] == sku].copy()
        if sku_df.empty:
            continue

        for day_offset in range(1, forecast_days + 1):
            forecast_date = latest_date + pd.Timedelta(days=day_offset)
            past_date = forecast_date - pd.DateOffset(years=1)

            # Use ±3 day window around past_date
            mask = (sku_df[date_col] >= past_date - pd.Timedelta(days=3)) & \
                   (sku_df[date_col] <= past_date + pd.Timedelta(days=3))
            base_qty = sku_df.loc[mask, qty_col].sum()

            forecast_qty = round(base_qty * 1.05, 1)
            forecast_records.append({
                'product_sku': sku,
                'forecast_date': forecast_date,
                'base_qty_last_year': round(base_qty, 1),
                'forecast_qty': max(0, forecast_qty),
                'forecast_days_ahead': day_offset
            })

    forecast_df = pd.DataFrame(forecast_records)
    return forecast_df

def prepare_forecast_csv(forecast_df):
    return forecast_df.to_csv(index=False).encode("utf-8")
