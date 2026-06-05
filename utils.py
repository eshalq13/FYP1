import pandas as pd
import numpy as np
from prophet import Prophet

# -----------------------------
# DATA CLEANING
# -----------------------------
def clean_data(df):

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

    df = df[df['Quantity'] > 0]
    df = df[df['UnitPrice'] > 0]

    df['Revenue'] = df['Quantity'] * df['UnitPrice']

    df['Profit'] = df['Revenue'] * 0.25  # assumed margin

    return df


# -----------------------------
# DAILY AGGREGATION
# -----------------------------
def get_daily_sales(df):

    daily = df.groupby(df['InvoiceDate'].dt.date)['Revenue'].sum().reset_index()
    daily.columns = ['ds', 'y']
    daily['ds'] = pd.to_datetime(daily['ds'])

    return daily


# -----------------------------
# PROPHEt FORECASTING
# -----------------------------
def run_prophet(df, periods=90):

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )

    model.fit(df)

    future = model.make_future_dataframe(periods=periods)

    forecast = model.predict(future)

    return model, forecast


# -----------------------------
# PRODUCT PERFORMANCE
# -----------------------------
def product_analysis(df):

    product_sales = df.groupby('Description')['Quantity'].sum().sort_values(ascending=False)

    return product_sales


# -----------------------------
# DEAD STOCK
# -----------------------------
def dead_stock(df):

    last_sale = df.groupby('Description')['InvoiceDate'].max().reset_index()

    last_sale['DaysInactive'] = (
        pd.Timestamp.today() - last_sale['InvoiceDate']
    ).dt.days

    return last_sale[last_sale['DaysInactive'] > 90]


# -----------------------------
# PROFIT ANALYSIS
# -----------------------------
def profit_analysis(df):

    return df.groupby('Description')['Profit'].sum().sort_values(ascending=False)


# -----------------------------
# RECOMMENDATION ENGINE
# -----------------------------
def recommendations(df):

    product_sales = df.groupby('Description')['Quantity'].sum()

    low_stock = product_sales[product_sales < 10]

    return {
        "low_demand": low_stock.index.tolist(),
        "high_demand": product_sales.sort_values(ascending=False).head(5).index.tolist()
    }

def generate_executive_summary(
    df,
    forecast,
    recommendations,
    dead_stock_df=None,
    product_col="Description"
):
    total_revenue = df['Revenue'].sum()

    total_products = df[product_col].nunique()

    total_transactions = len(df)

    avg_order_value = df['Revenue'].mean()

    top_product = (
        df.groupby(product_col)['Revenue']
          .sum()
          .idxmax()
    )

    top_product_revenue = (
        df.groupby(product_col)['Revenue']
          .sum()
          .max()
    )

    next_30_forecast = forecast.tail(30)['yhat'].mean()

    latest_revenue = (
        df.groupby(df['InvoiceDate'].dt.date)['Revenue']
          .sum()
          .iloc[-1]
    )

    growth_rate = (
        (next_30_forecast - latest_revenue)
        / latest_revenue
    ) * 100

    dead_stock_count = len(dead_stock_df) if dead_stock_df is not None else 0

    high_demand = recommendations.get('high_demand', [])
    low_demand = recommendations.get('low_demand', [])

    summary = f"""
SMART RETAIL AI EXECUTIVE SUMMARY

Total Revenue: ${total_revenue:,.2f}
Total Transactions: {total_transactions:,}
Unique Products: {total_products:,}

Top Product:
{top_product}

Top Product Revenue:
${top_product_revenue:,.2f}

Dead Stock Items:
{dead_stock_count}

Forecasted Average Revenue (Next 30 Days):
${next_30_forecast:,.2f}

Expected Growth:
{growth_rate:.2f}%

High Demand Products:
{', '.join(high_demand[:5])}

Low Demand Products:
{', '.join(low_demand[:5])}

RECOMMENDATIONS

1. Increase inventory for high-demand products.
2. Review low-performing products.
3. Discount dead-stock items.
4. Align purchasing with forecast demand.

Generated automatically by Smart Retail AI Dashboard.
"""

    return summary