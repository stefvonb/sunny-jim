from dash.dependencies import Input, Output
from . import functions

CALLBACKS = {"test_callback":
    {'output': Output('my-output', 'children'),
    'input': Input('my-input', 'value'),
    'function': functions.update_output_div}
}

def register_callbacks(app):
    for callback_name, callback in CALLBACKS.items():
        app.callback(callback['output'], callback['input'])(callback['function'])
