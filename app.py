import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# ---------- DATA ----------
df = pd.read_csv("data/Ecommerce_Sales_Data_2024_2025.csv")

# Date parsing
df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
df['Month'] = df['Order Date'].dt.to_period('M').astype(str)

# Finance metrics
df['Margin %'] = df['Profit'] / df['Sales']

# ---------- APP ----------
app = dash.Dash(__name__)

# ---------- LAYOUT ----------
app.layout = html.Div([

    html.H1("E-commerce Profitability Dashboard",
            style={'textAlign':'center'}),

    # Dropdown filter
    dcc.Dropdown(
        id='category-filter',
        options=[{'label':'All', 'value':'All'}] +
                [{'label':c, 'value':c} for c in df['Category'].unique()],
        value=['All'],
        multi=True
    ),

    # KPI Cards
    html.Div(id='kpis',
             style={'display':'flex',
                    'justifyContent':'space-around',
                    'margin':'20px',
                    'fontSize':22}),

    # Charts
    dcc.Graph(id='rev-profit'),
    dcc.Graph(id='discount-impact'),
    dcc.Graph(id='pnl-chart')

])

# ---------- CALLBACK ----------
@app.callback(
    [Output('kpis','children'),
     Output('rev-profit','figure'),
     Output('discount-impact','figure'),
     Output('pnl-chart','figure')],
    [Input('category-filter','value')]
)

def update_dashboard(categories):

    # Filter logic
    if 'All' in categories:
        dff = df.copy()
    else:
        dff = df[df['Category'].isin(categories)]

    # ---------- KPIs ----------
    total_rev = round(dff['Sales'].sum(),2)
    total_profit = round(dff['Profit'].sum(),2)
    margin = round((dff['Profit'].sum()/dff['Sales'].sum())*100,2)

    kpis = [
        html.Div(f"Revenue: {total_rev}"),
        html.Div(f"Profit: {total_profit}"),
        html.Div(f"Margin %: {margin}")
    ]

    # ---------- Revenue vs Profit ----------
    monthly = dff.groupby('Month').agg({
        'Sales':'sum',
        'Profit':'sum'
    }).reset_index()

    fig1 = px.line(
        monthly,
        x='Month',
        y=['Sales','Profit'],
        title="Revenue vs Profit Trend"
    )

    # ---------- Discount Impact ----------
    disc = dff.groupby('Discount').agg({
        'Sales':'sum',
        'Profit':'sum'
    }).reset_index()

    disc['Margin %'] = disc['Profit']/disc['Sales']

    fig2 = px.line(
        disc,
        x='Discount',
        y='Margin %',
        markers=True,
        title="Discount Impact on Margin"
    )

    # ---------- P&L MODEL ----------
    pnl = monthly.copy()

    pnl['COGS'] = pnl['Sales'] - pnl['Profit']
    pnl['Marketing Cost'] = pnl['Sales'] * 0.15
    pnl['Contribution'] = pnl['Profit'] - pnl['Marketing Cost']
    pnl['Fixed Cost'] = 50000
    pnl['Net Profit'] = pnl['Contribution'] - pnl['Fixed Cost']

    fig3 = px.bar(
        pnl,
        x='Month',
        y=['Sales','COGS','Marketing Cost','Net Profit'],
        title="P&L Overview",
        barmode='group'
    )

    return kpis, fig1, fig2, fig3

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
