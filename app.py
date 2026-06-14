import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils import (
    clean_data,
    get_daily_sales,
    run_prophet,
    product_analysis,
    dead_stock,
    profit_analysis,
    recommendations,
    generate_executive_summary
)

st.set_page_config(
    page_title="Retail AI Dashboard",
    layout="wide"
)
# =============================
# CUSTOM STYLING
# =============================
st.markdown("""
<style>

/* Main App Background */
.stApp {
    background: linear-gradient(
        135deg,           
        #000000 0%,     /* Black */
        #001F3F 30%,
        #007FFF 65%,
        #00BFFF 100%        /* Electric Blue */
    );
    color: white;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: rgba(0, 0, 0, 0.85);
}

/* Headers */
h1, h2, h3 {
    color: white !important;
}

/* Metric Cards */
[data-testid="metric-container"] {
    background-color: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    padding: 15px;
    border-radius: 12px;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    color: white;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    background-color: rgba(255,255,255,0.05);
    border-radius: 10px;
}

/* Buttons */
.stButton > button {
    background-color: #00BFFF;
    color: white;
    border-radius: 10px;
    border: none;
}

</style>
""", unsafe_allow_html=True)
# =============================
# LOGO
# =============================
st.image(
    "logo.PNG",  # <-- replace with your path
    width=180
)
st.title("AutoRetail AI Dashboard (Prophet + Analytics)")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("Upload your Retail CSV", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    df = clean_data(df)

    st.success("Data Loaded Successfully!")

    # SIDEBAR CONTROLS
    st.sidebar.header("Controls")

    forecast_days = st.sidebar.slider("Forecast Days", 30, 365, 90)

    # -----------------------------
    # TABS
    # -----------------------------
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Overview",
        "📈 Forecasting",
        "📦 Product Analysis",
        "⚠️ Inventory",
        "🧠 Recommendations",
        "📄 Reports",
        "📖 Insights & Explanation"
    ])

    # =============================
    # TAB 1 - OVERVIEW
    # =============================
    with tab1:

        st.subheader("Sales Overview")

        daily = get_daily_sales(df)

        fig = px.line(daily, x='ds', y='y', title="Daily Revenue Trend")

        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Revenue", round(df['Revenue'].sum(), 2))
        col2.metric("Total Transactions", len(df))
        col3.metric("Unique Products", df['Description'].nunique())

    # =============================
    # TAB 2 - FORECAST
    # =============================
    with tab2:

        st.subheader("AI Forecasting (Prophet)")

        daily = get_daily_sales(df)

        model, forecast = run_prophet(daily, forecast_days)

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=daily['ds'], y=daily['y'], name="Actual"))
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], name="Forecast"))

        fig.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat_upper'],
            line=dict(dash='dot'),
            name="Upper Bound"
        ))

        fig.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat_lower'],
            line=dict(dash='dot'),
            name="Lower Bound"
        ))

        st.plotly_chart(fig, use_container_width=True)

    # =============================
    # TAB 3 - PRODUCT ANALYSIS
    # =============================
    with tab3:

        st.subheader("Product Performance")

        prod = product_analysis(df).head(20)

        fig = px.bar(
            x=prod.values,
            y=prod.index,
            orientation='h',
            title="Top Products"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.write("Top Products Table")
        st.dataframe(prod)

    # =============================
    # TAB 4 - INVENTORY
    # =============================
    with tab4:

        st.subheader("Dead Stock Detection")

        dead = dead_stock(df)

        st.dataframe(dead)

        st.metric("Dead Stock Items", len(dead))

        st.subheader("Profit Analysis")

        profit = profit_analysis(df).head(20)

        fig = px.bar(
            x=profit.values,
            y=profit.index,
            orientation='h',
            title="Top Profitable Products"
        )

        st.plotly_chart(fig)

    # =============================
    # TAB 5 - RECOMMENDATIONS
    # =============================
    with tab5:

        st.subheader("AI Recommendations Engine")

        rec = recommendations(df)

        st.write("🔥 High Demand Products")
        st.write(rec['high_demand'])

        st.write("⚠️ Low Demand Products")
        st.write(rec['low_demand'])

        st.info("Recommendations are rule-based AI logic + Prophet forecasting insights")

    with tab6:

        summary_text = generate_executive_summary(
        df=df,
        forecast=forecast,
        recommendations=rec,
        dead_stock_df=dead
    )

    # =============================
    # TAB 7 - INSIGHTS & EXPLANATION
    # =============================
    with tab7:

        st.subheader("Dashboard Results Explained")

        st.markdown("""
        ## 📊 Sales Overview

        - **Total Revenue** shows the total sales generated from all transactions.
        - **Total Transactions** indicates how many purchases were made.
        - **Unique Products** represents the diversity of products sold.
        - The **Daily Revenue Trend** chart helps identify seasonality, growth, and sales fluctuations.

        ---

        ## 📈 Forecasting

        The forecasting model uses **Facebook Prophet** to predict future revenue.

        - **Actual Line** = Historical sales data.
        - **Forecast Line** = Predicted future sales.
        - **Upper Bound** = Optimistic scenario.
        - **Lower Bound** = Conservative scenario.

        ### How to use it:
        - Plan inventory levels.
        - Anticipate demand spikes.
        - Support budgeting and staffing decisions.

        ---

        ## 📦 Product Analysis

        This section identifies your best-performing products.

        - Products at the top generate the highest sales.
        - These items should receive:
            - More inventory allocation
            - Promotional focus
            - Strategic placement

        ---

        ## ⚠️ Inventory Analysis

        ### Dead Stock Detection
        Products appearing here have little or no recent sales activity.

        Potential actions:
        - Discount or bundle products.
        - Reduce future purchasing.
        - Remove obsolete inventory.

        ### Profit Analysis
        Shows products generating the highest profits.

        Focus on:
        - Increasing stock levels.
        - Cross-selling opportunities.
        - Marketing campaigns.

        ---

        ## 🧠 AI Recommendations

        The recommendation engine identifies:

        🔥 High Demand Products
        - Fast-moving items.
        - Candidates for increased inventory.

        ⚠️ Low Demand Products
        - Slow-moving items.
        - Candidates for promotions or discontinuation.

        ---

        ## 📄 Executive Summary

        The generated report summarizes:

        - Revenue performance
        - Forecast outlook
        - Inventory risks
        - Product opportunities
        - AI-generated recommendations

        This report can be shared directly with management and stakeholders.
        """)

        # Optional dynamic insights
        st.subheader("Quick Business Interpretation")

        revenue = round(df['Revenue'].sum(), 2)

        st.success(
            f"""
            Revenue analyzed: {revenue}

            Use the forecasting tab to determine whether future demand
            is increasing or decreasing. Review dead stock items regularly
            to improve inventory turnover and profitability.
            """
        )

        st.subheader("Download Reports")

        st.download_button(
            "📄 Summary Report",
            data=summary_text,
            file_name="summary.txt"
        )

        # st.download_button(
        #     "📥 PDF Report",
        #     pdf_bytes,
        #     file_name="report.pdf"
        # )

        # st.download_button(
        #     "📊 Excel Report",
        #     excel_file,
        #     file_name="report.xlsx"
        # )

else:
    st.info("Upload a CSV file to start analysis")
