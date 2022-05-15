from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd
from . import layout
from . import callbacks

class Dashboard:
    def __init__(self, config):
        self.config = config
        self.app = Dash(__name__)

        self.app.layout = layout.MASTER_LAYOUT
        callbacks.register_callbacks(self.app)

    def run(self):
        self.app.run_server(debug=self.config['debug'])
