import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc

df = pd.DataFrame({
            "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
            "Amount": [4, 1, 2, 2, 4, 5],
            "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
        })

fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")

MASTER_LAYOUT = html.Div(children=[html.H1(children="Sunny Jim"),
            html.Div(children='''
            Dash: A web application framework for your data.
        '''),

        dcc.Graph(
            id='example-graph',
            figure=fig
        ),
        html.Div([
        "Input: ",
        dcc.Input(id='my-input', value='initial value', type='text')
    ]),
    html.Br(),
    html.Div(id='my-output'),])