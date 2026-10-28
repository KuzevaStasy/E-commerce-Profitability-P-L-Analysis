from pathlib import Path

import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# ---------- MODEL ASSUMPTIONS (same as notebooks/P_L.ipynb) ----------
MARKETING_RATE = 0.10        # marketing spend as a share of sales
MONTHLY_FIXED_COST = 50000   # company-wide fixed overhead per month

# ---------- DATA ----------
DATA_FILE = Path(__file__).resolve().parent / "data" / "Ecommerce_Sales_Data_2024_2025.csv"
df = pd.read_csv(DATA_FILE)

# Dates are stored as MM/DD/YY
df['Order Date'] = pd.to_datetime(df['Order Date'], format='%m/%d/%y')
df['Month'] = df['Order Date'].dt.to_period('M').astype(str)

# The data ends mid-month; an incomplete last month would distort trends and be charged a full month of fixed cost
last_day = df['Order Date'].max()
if last_day < last_day + pd.offsets.MonthEnd(0):
    df = df[df['Month'] != last_day.strftime('%Y-%m')].copy()

# Total sales per month across all categories, used to allocate fixed cost when a category filter is applied
month_total_sales = df.groupby('Month')['Sales'].sum()

# ---------- APP ----------
app = dash.Dash(__name__)

# ---------- LAYOUT ----------
app.layout = html.Div([

    html.H1("E-commerce Profitability Dashboard",
            style={'textAlign': 'center'}),

    # Dropdown filter (clearing it is treated as "All")
    dcc.Dropdown(
        id='category-filter',
        options=[{'label': 'All', 'value': 'All'}] +
                [{'label': c, 'value': c} for c in sorted(df['Category'].unique())],
        value=['All'],
        multi=True
    ),

    # KPI Cards
    html.Div(id='kpis',
             style={'display': 'flex',
                    'justifyContent': 'space-around',
                    'margin': '20px',
                    'fontSize': 22}),

    # Charts
    dcc.Graph(id='rev-profit'),
    dcc.Graph(id='discount-impact'),
    dcc.Graph(id='pnl-chart')

])


# ---------- CALLBACK ----------
@app.callback(
    [Output('kpis', 'children'),
     Output('rev-profit', 'figure'),
     Output('discount-impact', 'figure'),
     Output('pnl-chart', 'figure')],
    [Input('category-filter', 'value')]
)
def update_dashboard(categories):

    # Filter logic: an empty selection or "All" shows everything
    if not categories or 'All' in categories:
        dff = df.copy()
    else:
        dff = df[df['Category'].isin(categories)]

    # ---------- KPIs ----------
    total_rev = dff['Sales'].sum()
    total_profit = dff['Profit'].sum()
    margin = (total_profit / total_rev * 100) if total_rev else 0

    kpis = [
        html.Div(f"Revenue: ${total_rev:,.0f}"),
        html.Div(f"Profit: ${total_profit:,.0f}"),
        html.Div(f"Margin: {margin:.2f}%")
    ]

    # ---------- Revenue vs Profit ----------
    monthly = dff.groupby('Month').agg({
        'Sales': 'sum',
        'Profit': 'sum'
    }).reset_index()

    fig1 = px.line(
        monthly,
        x='Month',
        y=['Sales', 'Profit'],
        title="Revenue vs Profit Trend",
        labels={'value': 'USD ($)', 'variable': ''}
    )

    # ---------- Discount Impact ----------
    disc = dff.groupby('Discount').agg({
        'Sales': 'sum',
        'Profit': 'sum'
    }).reset_index()

    disc['Margin %'] = disc['Profit'] / disc['Sales']

    fig2 = px.line(
        disc,
        x='Discount',
        y='Margin %',
        markers=True,
        title="Discount Impact on Margin",
        labels={'Discount': 'Discount (%)'}
    )
    fig2.update_yaxes(tickformat='.1%')

    # ---------- P&L MODEL ----------
    pnl = monthly.copy()

    pnl['COGS'] = pnl['Sales'] - pnl['Profit']
    pnl['Marketing Cost'] = pnl['Sales'] * MARKETING_RATE
    pnl['Contribution'] = pnl['Profit'] - pnl['Marketing Cost']
    # Fixed overhead is company-wide: with a category filter it is allocated by the category's share of monthly sales
    pnl['Fixed Cost'] = MONTHLY_FIXED_COST * pnl['Sales'] / pnl['Month'].map(month_total_sales)
    pnl['Net Profit'] = pnl['Contribution'] - pnl['Fixed Cost']

    fig3 = px.bar(
        pnl,
        x='Month',
        y=['Sales', 'COGS', 'Marketing Cost', 'Net Profit'],
        title=f"P&L Overview (marketing {MARKETING_RATE:.0%} of sales, fixed cost ${MONTHLY_FIXED_COST:,}/month)",
        barmode='group',
        labels={'value': 'USD ($)', 'variable': ''}
    )

    return kpis, fig1, fig2, fig3


# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
