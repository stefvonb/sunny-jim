from dash import Dash
import dash_bootstrap_components as dbc
from . import layout
from . import callbacks


class Dashboard:
    def __init__(self, config):
        self.config = config
        self.app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])

        self.app.layout = layout.MASTER_LAYOUT
        callbacks.register_callbacks(self.app)

    def run(self):
        self.app.run_server(debug=self.config['application']['debug'])
