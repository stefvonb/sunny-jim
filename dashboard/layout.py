import dash_bootstrap_components as dbc
from dash import html, dcc

MASTER_LAYOUT = dbc.Container(
    [
        dcc.Store(id="store"),
        html.H1("Sunny Jim"),
        html.H3("Solar power monitor", className="text-muted"),
        html.Hr(),
        dbc.Tabs(
            [
                dbc.Tab(label="Summary", tab_id="summary-tab"),
                dbc.Tab(label="Logs", tab_id="logs-tab", id="logs=tab")
            ],
            id="tabs",
            active_tab="summary-tab",
        ),
        html.Div(id="tab-content", className="p-4"),
    ],
    className="p-5",
)
