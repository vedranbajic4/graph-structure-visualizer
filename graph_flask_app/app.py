"""
    Flask app — thin HTTP layer over the GraphPlatform core.

    All view-building logic (Main View, Tree View, Bird View) lives in
    ``core.services.view_service.ViewService`` and is invoked through
    ``GraphPlatform.build_view_response()``.
"""
import sys
import os
import json
import logging
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, jsonify, request
from graph_platform.core import GraphPlatform

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'shared', 'static'),
    static_url_path='/static',
    template_folder=os.path.join(BASE_DIR, 'shared', 'templates'),
)
app.secret_key = 'your-secret-key-here'
logger = logging.getLogger(__name__)

_ui_state: dict = {
    'visualizer': 'simple',
    'cli_output': [],
}

URLS = {
    'upload':           '/api/upload',
    'visualizer':       '/api/visualizer',
    'search':           '/api/search',
    'filter':           '/api/filter',
    'undo':             '/api/undo',
    'reset':            '/api/reset',
    'cli':              '/api/cli',
    'workspace_switch': '/api/workspace/switch',
    'workspace_delete': '/api/workspace/delete',
}

def _get_platform() -> GraphPlatform:
    return GraphPlatform.get_instance()

def _view_response(platform, visualizer_name=None):
    """Delegate view building to the core ViewService."""
    vis = visualizer_name or _ui_state.get('visualizer', 'simple')
    return platform.build_view_response(visualizer_name=vis)


# ── Page view ────────────────────────────────────────────────────

@app.route('/')
def index():
    platform = _get_platform()
    ctx = _view_response(platform)

    graph_data_json = json.dumps(ctx.get('graph_data'), default=str) \
        if ctx.get('graph_data') else 'null'
    tree_data_json = json.dumps(ctx.get('tree_data', []), default=str)

    return render_template('base.html',
        **ctx,
        data_sources=platform.get_data_source_names(),
        visualizers=platform.get_visualizer_names(),
        active_visualizer=_ui_state.get('visualizer', 'simple'),
        cli_output=_ui_state.get('cli_output', []),
        graph_data_json=graph_data_json,
        tree_data_json=tree_data_json,
        urls_json=json.dumps(URLS),
        csrf_token='',
    )


# ── AJAX endpoints ────────────────────────────────────────────────

@app.route('/api/upload', methods=['POST'])
def upload_file():
    platform = _get_platform()
    plugin_name = request.form.get('plugin_name', '')
    uploaded_file = request.files.get('file')
    workspace_name = request.form.get('workspace_name', '').strip()

    if not uploaded_file:
        return jsonify({'success': False, 'error': 'No file uploaded.'})
    if not plugin_name:
        return jsonify({'success': False, 'error': 'No data source selected.'})

    upload_dir = Path(BASE_DIR) / 'media' / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / uploaded_file.filename
    uploaded_file.save(str(file_path))

    try:
        platform.load_graph(plugin_name, workspace_name or None, file_path=str(file_path))
        resp = _view_response(platform)
        resp['success'] = True
        return jsonify(resp)
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/visualizer', methods=['POST'])
def switch_visualizer():
    platform = _get_platform()
    data = request.get_json()
    name = data.get('visualizer', 'simple')
    _ui_state['visualizer'] = name
    resp = _view_response(platform, name)
    resp['success'] = True
    return jsonify(resp)


@app.route('/api/search', methods=['POST'])
def search_graph():
    platform = _get_platform()
    data = request.get_json()
    try:
        platform.search_graph(data.get('query', ''))
        resp = _view_response(platform)
        resp['success'] = True
        return jsonify(resp)
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/filter', methods=['POST'])
def filter_graph():
    platform = _get_platform()
    data = request.get_json()
    try:
        platform.filter_graph(data.get('query', ''))
        resp = _view_response(platform)
        resp['success'] = True
        return jsonify(resp)
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/undo', methods=['POST'])
def undo_action():
    platform = _get_platform()
    result = platform.undo()
    if result is None:
        return jsonify({'success': False, 'error': 'Nothing to undo.'})
    resp = _view_response(platform)
    resp['success'] = True
    return jsonify(resp)


@app.route('/api/reset', methods=['POST'])
def reset_graph():
    platform = _get_platform()
    try:
        platform.reset_workspace()
        resp = _view_response(platform)
        resp['success'] = True
        return jsonify(resp)
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/cli', methods=['POST'])
def cli_execute():
    platform = _get_platform()
    data = request.get_json()
    command_text = data.get('command', '')
    try:
        result = platform.execute_command(command_text)
        entry = {'command': command_text, 'message': result.message, 'success': result.success}
        _ui_state.setdefault('cli_output', []).append(entry)
        _ui_state['cli_output'] = _ui_state['cli_output'][-100:]
        resp = _view_response(platform)
        resp['success'] = result.success
        resp['message'] = result.message
        resp['cli_output'] = _ui_state['cli_output']
        return jsonify(resp)
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/workspace/switch', methods=['POST'])
def switch_workspace():
    platform = _get_platform()
    data = request.get_json()
    try:
        platform.set_active_workspace(data.get('workspace_id', ''))
        resp = _view_response(platform)
        resp['success'] = True
        return jsonify(resp)
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/workspace/delete', methods=['POST'])
def delete_workspace():
    platform = _get_platform()
    data = request.get_json()
    platform.remove_workspace(data.get('workspace_id', ''))
    resp = _view_response(platform)
    resp['success'] = True
    return jsonify(resp)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
