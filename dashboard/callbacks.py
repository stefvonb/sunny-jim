from dash.dependencies import Input, Output, State
from . import functions
from . import tabs

CALLBACKS = {
    "tabs": {
        'output': Output('tab-content', 'children'),
        'input': [Input("tabs", "active_tab"), Input("store", "data")],
        'function': tabs.render_tab_content
    },
    "logs": {
        'output': [Output('logs-textarea', 'value'), Output('logs-autoupdate', 'run')],
        'input': [Input('logs-interval', 'n_intervals')],
        'function': functions.update_logs_data
    }
}


def register_callbacks(app):
    for callback_name, callback in CALLBACKS.items():
        app.callback(callback['output'], callback['input'], callback.get('state', []))(callback['function'])
