"""
    Django views — thin HTTP layer over the GraphPlatform core.

    All view-building logic (Main View, Tree View, Bird View) lives in
    ``core.services.view_service.ViewService`` and is invoked through
    ``GraphPlatform.build_view_response()``.
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

_URLS = {
    'upload': '/api/upload/',
    'visualizer': '/api/visualizer/',
    'search': '/api/search/',
    'filter': '/api/filter/',
    'undo': '/api/undo/',
    'reset': '/api/reset/',
    'cli': '/api/cli/',
    'workspace_switch': '/api/workspace/switch/',
    'workspace_delete': '/api/workspace/delete/',
    'plugin_params': '/api/plugin/parameters/',
}


def _get_platform() -> GraphPlatform:
    return GraphPlatform.get_instance()


def _view_response(platform, visualizer_name=None):
    """Delegate view building to the core ViewService."""
    vis = visualizer_name or _ui_state.get('visualizer', 'simple')
    return platform.build_view_response(visualizer_name=vis)


# ── Page view ────────────────────────────────────────────────────

def index(request):
    platform = _get_platform()
    ctx = _view_response(platform)

    graph_data_json = json.dumps(ctx.get('graph_data'), default=str) \
        if ctx.get('graph_data') else 'null'
    tree_data_json = json.dumps(ctx.get('tree_data', []), default=str)

    ctx.update({
        'data_sources': platform.get_data_source_names(),
        'visualizers': platform.get_visualizer_names(),
        'active_visualizer': _ui_state.get('visualizer', 'simple'),
        'cli_output': _ui_state.get('cli_output', []),
        'graph_data_json': graph_data_json,
        'tree_data_json': tree_data_json,
        'urls_json': json.dumps(_URLS),
    })
    return render(request, 'base.html', ctx)


# ── AJAX endpoints ───────────────────────────────────────────────

@require_POST
def upload_file(request):
    platform = _get_platform()

    plugin_name = request.POST.get('plugin_name', '')
    uploaded_file = request.FILES.get('file')
    workspace_name = request.POST.get('workspace_name', '').strip()

    if not uploaded_file:
        return JsonResponse({'success': False, 'error': 'No file uploaded.'})
    if not plugin_name:
        return JsonResponse({'success': False, 'error': 'No data source selected.'})

    upload_dir = Path(settings.MEDIA_ROOT) / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / uploaded_file.name
    with open(file_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # Collect any extra plugin-specific parameters from the form
    _skip = {'plugin_name', 'workspace_name', 'csrfmiddlewaretoken'}
    extra_kwargs = {k: v for k, v in request.POST.items() if k not in _skip and v.strip()}

    try:
        platform.load_graph(plugin_name, workspace_name or None, file_path=str(file_path), **extra_kwargs)
        resp = _view_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        logger.exception("Upload failed")
        return JsonResponse({'success': False, 'error': str(exc)})


def plugin_parameters(request):
    """Return the extra (non-file) parameters declared by a data source plugin."""
    platform = _get_platform()
    plugin_name = request.GET.get('plugin', '')
    plugin = platform.get_data_source(plugin_name)
    if plugin is None:
        return JsonResponse({'params': []})
    params = [
        {
            'name': p.name,
            'label': p.label,
            'description': p.description,
            'required': p.required,
            'default': p.default,
        }
        for p in plugin.get_parameters()
        if p.name != 'file_path'
    ]
    return JsonResponse({'params': params})


@require_POST
def switch_visualizer(request):
    platform = _get_platform()
    data = json.loads(request.body)
    name = data.get('visualizer', 'simple')
    _ui_state['visualizer'] = name

    resp = _view_response(platform, name)
    resp['success'] = True
    return JsonResponse(resp, json_dumps_params={'default': str})


@require_POST
def search_graph(request):
    platform = _get_platform()
    data = json.loads(request.body)

    try:
        platform.search_graph(data.get('query', ''))
        resp = _view_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def filter_graph(request):
    platform = _get_platform()
    data = json.loads(request.body)

    try:
        platform.filter_graph(data.get('query', ''))
        resp = _view_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def undo_action(request):
    platform = _get_platform()
    result = platform.undo()
    if result is None:
        return JsonResponse({'success': False, 'error': 'Nothing to undo.'})

    resp = _view_response(platform)
    resp['success'] = True
    return JsonResponse(resp, json_dumps_params={'default': str})


@require_POST
def reset_graph(request):
    platform = _get_platform()
    try:
        platform.reset_workspace()
        resp = _view_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def cli_execute(request):
    platform = _get_platform()
    data = json.loads(request.body)
    command_text = data.get('command', '')

    try:
        result = platform.execute_command(command_text)

        entry = {
            'command': command_text,
            'message': result.message,
            'success': result.success,
        }
        _ui_state.setdefault('cli_output', []).append(entry)
        _ui_state['cli_output'] = _ui_state['cli_output'][-100:]

        resp = _view_response(platform)
        resp['success'] = result.success
        resp['message'] = result.message
        resp['cli_output'] = _ui_state['cli_output']
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def switch_workspace(request):
    platform = _get_platform()
    data = json.loads(request.body)

    try:
        platform.set_active_workspace(data.get('workspace_id', ''))
        resp = _view_response(platform)
        resp['success'] = True
        return JsonResponse(resp, json_dumps_params={'default': str})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_POST
def delete_workspace(request):
    platform = _get_platform()
    data = json.loads(request.body)

    platform.remove_workspace(data.get('workspace_id', ''))
    resp = _view_response(platform)
    resp['success'] = True
    return JsonResponse(resp, json_dumps_params={'default': str})