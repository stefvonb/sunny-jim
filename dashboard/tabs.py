import visdcc
from dash import dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html


def render_tab_content(active_tab, data):
    # Making some phony data for now
    data = {
        'measurements': {
            'grid_power': 250,
            'battery_power': 300,
            'solar_power': 100
        }
    }

    if data is None:
        return "Problem retrieving data"

    if active_tab:
        # The summary tab
        if active_tab == "summary-tab":
            power_gauge_figures = [go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': source})) for source, value in data['measurements'].items()]
            content = [dbc.Col(dcc.Graph(figure=figure), width=4) for figure in power_gauge_figures]
            return dbc.Row(content)

        # The logs tab
        elif active_tab == "logs-tab":
            content = html.Div([
                dbc.Textarea(className="bg-dark text-light",
                             style={"resize": "none", "height": "100%", "font-family": "monospace"},
                             readonly=True, rows=16, id="logs-textarea"),
                dcc.Interval(id='logs-interval', interval=5*1000, n_intervals=0),
                visdcc.Run_js(id="logs-autoupdate", run="")
            ])
            return dbc.Row([content])
    return "No tab selected"
