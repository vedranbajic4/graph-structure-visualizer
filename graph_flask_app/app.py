import sys
import os

# Add project root to path so graph_platform can be imported
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)  # ✅ add this before importing graph_platform

from flask import Flask, render_template, jsonify, request
from graph_platform.core import GraphPlatform

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'shared', 'static'),
    static_url_path='/static',
    template_folder=os.path.join(BASE_DIR, 'shared', 'templates'),
)
app.secret_key = 'your-secret-key-here'

_ui_state = {
    'visualizer': 'simple',
    'cli_output': [],
}

def _get_platform() -> GraphPlatform:
    return GraphPlatform.get_instance()


@app.route('/')
def index():
    platform = _get_platform()
    ws = platform.get_active_workspace()
    return render_template('base.html',
        has_graph=ws is not None,
        workspace=ws,
        workspaces=platform.list_workspaces(),
        graph_html='',
        visualizers=platform.get_visualizer_names(),
        ui_state=_ui_state,
        csrf_token=''
    )


if __name__ == '__main__':
    app.run(debug=True, port=5001)
