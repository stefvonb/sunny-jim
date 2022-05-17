from dash import dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go


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
        if active_tab == "summary-tab":
            power_gauge_figures = [go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': source})) for source, value in data['measurements'].items()]
            content = [dbc.Col(dcc.Graph(figure=figure), width=4) for figure in power_gauge_figures]
            return dbc.Row(content)
    return "No tab selected"
