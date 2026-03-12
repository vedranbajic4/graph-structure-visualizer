"""
    View service — builds structured data for the three views
    (Main View, Tree View, Bird View).

    Moves view-building logic into the core platform so that both
    Django and Flask share identical view construction.
"""
from typing import Dict, Any, List, Optional, Set

from api.models.graph import Graph
from api.models.edge import EdgeDirection


class ViewService:
    """
    Builds view data for Tree View, Bird View, and Main View.
    """

    # ── Tree View ────────────────────────────────────────────────

    def build_tree_view_data(self, graph: Graph) -> List[Dict[str, Any]]:
        """
        Build a tree structure from the graph for the Tree View panel.

        Each node shows its ID. When expanded it reveals:
          - Its attributes (key-value pairs)
          - Connected nodes (which are themselves expandable)

        Cyclic references are detected: a node already on the current
        path is emitted with ``is_cycle_ref = True`` so the frontend
        can show it without infinite recursion.
        """
        if not graph.nodes:
            return []

        nodes = list(graph.nodes.values())
        edges = list(graph.edges.values())

        # adjacency: node_id → [{target, edge_id, edge_label}]
        adj: Dict[str, List[Dict[str, str]]] = {n.node_id: [] for n in nodes}

        for edge in edges:
            src = edge.source_node.node_id
            tgt = edge.target_node.node_id
            label = edge.attributes.get('label',
                        edge.attributes.get('Name', ''))
            entry = {
                'target': tgt,
                'edge_id': edge.edge_id,
                'edge_label': str(label) if label else '',
            }
            adj.setdefault(src, []).append(entry)

            if edge.direction == EdgeDirection.UNDIRECTED:
                adj.setdefault(tgt, []).append({
                    'target': src,
                    'edge_id': edge.edge_id,
                    'edge_label': str(label) if label else '',
                })

        def _display_name(node) -> str:
            """Pick the best human-readable name from a node's attributes."""
            for key in ('name', 'Name', 'title', 'Title', 'label', 'Label'):
                val = node.attributes.get(key)
                if val is not None:
                    return str(val)
            return node.node_id

        def _build_node(node_id: str, visited: Set[str]) -> Dict[str, Any]:
            node = graph.get_node(node_id)
            if node is None:
                return {
                    'id': node_id,
                    'display_name': node_id,
                    'is_cycle_ref': True,
                    'attributes': {},
                    'connections': [],
                }

            if node_id in visited:
                return {
                    'id': node_id,
                    'display_name': _display_name(node),
                    'is_cycle_ref': True,
                    'attributes': {},
                    'connections': [],
                }

            new_visited = visited | {node_id}

            # Serialize attributes (values → str for safe JSON transport)
            attrs = {}
            for k, v in node.attributes.items():
                attrs[k] = str(v) if v is not None else None

            # Connected nodes
            connections = []
            for conn in adj.get(node_id, []):
                connections.append({
                    'edge_id': conn['edge_id'],
                    'edge_label': conn['edge_label'],
                    'node': _build_node(conn['target'], new_visited),
                })

            return {
                'id': node_id,
                'display_name': _display_name(node),
                'is_cycle_ref': False,
                'attributes': attrs,
                'connections': connections,
            }

        # Start from the first node as root
        root_id = nodes[0].node_id
        result = [_build_node(root_id, set())]

        # Discover reachable set via BFS so disconnected components
        # each get their own root entry.
        reachable: Set[str] = set()
        queue = [root_id]
        reachable.add(root_id)
        while queue:
            current = queue.pop(0)
            for conn in adj.get(current, []):
                if conn['target'] not in reachable:
                    reachable.add(conn['target'])
                    queue.append(conn['target'])

        for node in nodes:
            if node.node_id not in reachable:
                result.append(_build_node(node.node_id, set()))

        return result

    # ── Bird View / Main View ─────────────────────────────────────

    def build_graph_data(self, graph: Graph) -> Dict[str, Any]:
        """
        Return the raw graph dict for Bird View and Main View panels.
        """
        return graph.to_dict()

    # ── Combined response ────────────────────────────────────────

    def build_response(
        self,
        graph: Optional[Graph],
        graph_html: str,
        workspace_dict: Optional[Dict],
        workspaces: List[Dict],
    ) -> Dict[str, Any]:
        """
        Build the complete view response combining all three views.

        Args:
            graph:          Current graph (None if no workspace).
            graph_html:     HTML string from the visualizer plugin.
            workspace_dict: Active workspace metadata.
            workspaces:     List of all workspace metadata dicts.

        Returns:
            Dict ready to be serialized as JSON for the frontend.
        """
        if graph is None:
            return {
                'has_graph': False,
                'graph_html': '',
                'graph_data': None,
                'tree_data': [],
                'workspace': None,
                'workspaces': workspaces,
            }

        return {
            'has_graph': True,
            'graph_html': graph_html,
            'graph_data': self.build_graph_data(graph),
            'tree_data': self.build_tree_view_data(graph),
            'workspace': workspace_dict,
            'workspaces': workspaces,
        }
