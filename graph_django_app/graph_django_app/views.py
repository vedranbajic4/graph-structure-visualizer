"""
    Django views — wires the GraphPlatform core into HTTP endpoints.

    The index view renders the full 3-panel page.
    All other endpoints are AJAX (return JsonResponse) so the
    page updates without a full reload.
"""
import json
import logging
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from graph_platform.core import GraphPlatform

logger = logging.getLogger(__name__)

# ── Module-level UI state (single-user app per spec §2.1) ────────
_ui_state: dict = {
    'visualizer': 'simple',
    'cli_output': [],
}


# ── Helpers ──────────────────────────────────────────────────────

def _get_platform() -> GraphPlatform:
    """Return the singleton GraphPlatform, creating it on first call."""
    return GraphPlatform.get_instance()


def _graph_response(platform, visualizer_name=None):
    """
    Build a dict suitable for JsonResponse with the current graph state.
    Includes the HTML from the visualizer plugin + raw graph data for
    Tree View / Bird View.
    """
    ws = platform.get_active_workspace()
    if ws is None:
        return {
            'has_graph': False,
            'graph_html': '',
            'graph_data': None,
            'workspace': None,
            'workspaces': platform.list_workspaces(),
        }

    vis_name = visualizer_name or _ui_state.get('visualizer', 'simple')
    try:
        graph_html = platform.visualize(vis_name)
    except Exception as exc:
        graph_html = f'<div class="vis-error">Visualization error: {exc}</div>'

    return {
        'has_graph': True,
        'graph_html': graph_html,
        'graph_data': ws.current_graph.to_dict(),
        'workspace': ws.to_dict(),
        'workspaces': platform.list_workspaces(),
    }


# ── Page view ────────────────────────────────────────────────────

def index(request):
    """
    Render the full Graph Explorer page with the three-panel layout.
    All subsequent interactions happen via AJAX endpoints below.
    """
    platform = _get_platform()
    ctx = _graph_response(platform)

    # Serialize graph data for embedding in <script> tag
    graph_data_json = json.dumps(ctx.get('graph_data'), default=str) \
        if ctx.get('graph_data') else 'null'

    ctx.update({
        'data_sources': platform.get_data_source_names(),
        'visualizers': platform.get_visualizer_names(),
        'active_visualizer': _ui_state.get('visualizer', 'simple'),
        'cli_output': _ui_state.get('cli_output', []),
        'graph_data_json': graph_data_json,
    })

    return render(request, 'base.html', ctx)


# ── AJAX endpoints (all return JsonResponse) ─────────────────────

@require_POST
def upload_file(request):
    """
    Handle file upload + data source selection → parse → create workspace.

    Expects multipart/form-data with:
        - file: the data file
        - plugin_name: entry-point name of the data source plugin
        - workspace_name (optional): human-readable label
    """
    platform = _get_platform()

    plugin_name = request.POST.get('plugin_name', '')
    uploaded_file = request.FILES.get('file')
    workspace_name = request.POST.get('workspace_name', '').strip()

    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'No file uploaded.'})
    if not plugin_name:
        return JsonResponse({'success': False, 'error': 'No data source selected.'})

    # Save uploaded file to media/uploads/
    upload_dir = Path(settings.MEDIA_ROOT) / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / uploaded_file.name
    with open(file_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    try:
        platform.load_graph(
            plugin_name,
            str(file_path),
            workspace_name or None,
        )
        resp = _graph_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        logger.exception("Upload failed")
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def switch_visualizer(request):
    """Change the active visualizer plugin (simple / block)."""
    platform = _get_platform()
    data = json.loads(request.body)
    name = data.get('visualizer', 'simple')
    _ui_state['visualizer'] = name

    resp = _graph_response(platform, name)
    resp['success'] = True
    return JsonResponse(resp, json_dumps_params={'default': str})


@require_POST
def search_graph(request):
    """
    Apply a search query on the active workspace (server-side).
    Per spec §2.1.2: "Nije dozvoljeno pretragu i filtriranje raditi u JS-u."
    """
    platform = _get_platform()
    data = json.loads(request.body)
    query = data.get('query', '')

    try:
        platform.search_graph(query)
        resp = _graph_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def filter_graph(request):
    """
    Apply a filter query on the active workspace (server-side).
    Format: "<attribute> <comparator> <value>"
    """
    platform = _get_platform()
    data = json.loads(request.body)
    query = data.get('query', '')

    try:
        platform.filter_graph(query)
        resp = _graph_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def undo_action(request):
    """Undo the last search / filter operation."""
    platform = _get_platform()

    result = platform.undo()
    if result is None:
        return JsonResponse({'success': False, 'error': 'Nothing to undo.'})

    resp = _graph_response(platform)
    resp['success'] = True
    return JsonResponse(resp, json_dumps_params={'default': str})


@require_POST
def reset_graph(request):
    """Reset the active workspace to its original graph."""
    platform = _get_platform()

    try:
        platform.reset_workspace()
        resp = _graph_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def cli_execute(request):
    """
    Execute a CLI command on the active workspace's graph.
    Returns the command result message and the updated graph.
    """
    platform = _get_platform()
    data = json.loads(request.body)
    command_text = data.get('command', '')

    try:
        result = platform.execute_command(command_text)

        # Keep a rolling history of CLI interactions
        entry = {
            'command': command_text,
            'message': result.message,
            'success': result.success,
        }
        _ui_state.setdefault('cli_output', []).append(entry)
        _ui_state['cli_output'] = _ui_state['cli_output'][-100:]

        resp = _graph_response(platform)
        resp['success'] = result.success
        resp['message'] = result.message
        resp['cli_output'] = _ui_state['cli_output']
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def switch_workspace(request):
    """Activate a different workspace."""
    platform = _get_platform()
    data = json.loads(request.body)
    workspace_id = data.get('workspace_id', '')

    try:
        platform.set_active_workspace(workspace_id)
        resp = _graph_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def delete_workspace(request):
    """Remove a workspace."""
    platform = _get_platform()
    data = json.loads(request.body)
    workspace_id = data.get('workspace_id', '')

    platform.remove_workspace(workspace_id)
    resp = _graph_response(platform)
    resp['success'] = True
    return JsonResponse(resp, json_dumps_params={'default': str})