from dash.dependencies import Input, Output
from . import functions
from . import tabs

CALLBACKS = {
    "tabs": {
        'output': Output('tab-content', 'children'),
        'input': [Input("tabs", "active_tab"), Input("store", "data")],
        'function': tabs.render_tab_content
    }
}


def register_callbacks(app):
    for callback_name, callback in CALLBACKS.items():
        app.callback(callback['output'], callback['input'])(callback['function'])
