"""
URL configuration for the Graph Explorer Django application.
"""
from django.urls import path
from . import views

urlpatterns = [
    # ── Page ─────────────────────────────────────────────────────
    path('', views.index, name='index'),

    # ── AJAX endpoints ───────────────────────────────────────────
    path('api/upload/', views.upload_file, name='upload_file'),
    path('api/visualizer/', views.switch_visualizer, name='switch_visualizer'),
    path('api/search/', views.search_graph, name='search_graph'),
    path('api/filter/', views.filter_graph, name='filter_graph'),
    path('api/undo/', views.undo_action, name='undo_action'),
    path('api/reset/', views.reset_graph, name='reset_graph'),
    path('api/cli/', views.cli_execute, name='cli_execute'),
    path('api/workspace/switch/', views.switch_workspace, name='switch_workspace'),
    path('api/workspace/delete/', views.delete_workspace, name='delete_workspace'),
    path('api/workspace/create/', views.create_workspace_view, name='create_workspace'),
    path('api/plugin/parameters/', views.plugin_parameters, name='plugin_parameters'),
]