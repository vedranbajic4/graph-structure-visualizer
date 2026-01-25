"""
    Graph model - complete graph model.
    Support for directed/undirected, cyclic/acyclic graphs.
"""
from typing import Dict, List, Set, Optional
from copy import deepcopy
from .node import Node
from .edge import Edge, EdgeDirection


class Graph:
    """
        Class for graph representation.
        Supports directed, undirected, cyclic, acyclic graphs.
    """

    def __init__(self, graph_id: str):
        """
        Initialize a graph.
        Args:
            graph_id: Unique identifier of the graph
        """
        self.graph_id = graph_id
        self.nodes: Dict[str, Node] = {}  # node_id -> Node
        self.edges: Dict[str, Edge] = {}  # edge_id -> Edge
        self._adjacency_list: Dict[str, List[Edge]] = {}  # node_id -> [Edges]

    def add_node(self, node: Node) -> None:
        """Add a node to the graph"""
        if node.node_id in self.nodes:
            raise ValueError(f"Node with id {node.node_id} already exists")

        self.nodes[node.node_id] = node
        self._adjacency_list[node.node_id] = []

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph"""
        if edge.source_node.node_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_node.node_id} not in graph")
        if edge.target_node.node_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_node.node_id} not in graph")

        if edge.edge_id in self.edges:
            raise ValueError(f"Edge with id {edge.edge_id} already exists")

        self.edges[edge.edge_id] = edge

        # Add to adjacency list for both nodes (optimization for faster access)
        self._adjacency_list[edge.source_node.node_id].append(edge)
        if edge.source_node.node_id != edge.target_node.node_id:
            self._adjacency_list[edge.target_node.node_id].append(edge)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        return self.edges.get(edge_id)

    def get_all_nodes(self) -> List[Node]:
        return list(self.nodes.values())

    def get_all_edges(self) -> List[Edge]:
        return list(self.edges.values())

    def get_neighbors(self, node: Node) -> List[Node]:
        """Get all neighboring nodes"""
        neighbors = set()
        for edge in self._adjacency_list.get(node.node_id, []):
            other = edge.get_other_node(node)
            if other:
                neighbors.add(other)
            elif edge.source_node == node and edge.target_node == node:
                # Self-loop
                neighbors.add(node)
        return list(neighbors)

    def get_outgoing_edges(self, node: Node) -> List[Edge]:
        """
        Get all outgoing edges from the node.
        If edge is UNDIRECTED, it counts as outgoing even if we are the target.
        """
        result = []
        for edge in self._adjacency_list.get(node.node_id, []):
            if edge.source_node == node:
                result.append(edge)
            elif edge.direction == EdgeDirection.UNDIRECTED and edge.target_node == node:
                result.append(edge)
        return result

    def get_incoming_edges(self, node: Node) -> List[Edge]:
        """
        Get all incoming edges to the node.
        If edge is UNDIRECTED, it counts as incoming even if we are the source.
        """
        result = []
        for edge in self._adjacency_list.get(node.node_id, []):
            if edge.target_node == node:
                result.append(edge)
            elif edge.direction == EdgeDirection.UNDIRECTED and edge.source_node == node:
                result.append(edge)
        return result

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all connected edges."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not in graph")

        # 1. Identify edges to delete
        edges_to_delete = set()
        for edge in self._adjacency_list.get(node_id, []):
            edges_to_delete.add(edge.edge_id)

        # 2. Delete edges
        for edge_id in edges_to_delete:
            self.remove_edge(edge_id)

        # 3. Delete node
        del self.nodes[node_id]
        if node_id in self._adjacency_list:
            del self._adjacency_list[node_id]

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the graph"""
        if edge_id not in self.edges:
            return  # Safe delete is often better than raising ValueError

        edge = self.edges[edge_id]
        s_id = edge.source_node.node_id
        t_id = edge.target_node.node_id

        # Remove from source adjacency list
        if s_id in self._adjacency_list:
            self._adjacency_list[s_id] = [e for e in self._adjacency_list[s_id] if e.edge_id != edge_id]

        # Remove from target adjacency list
        if t_id in self._adjacency_list:
            self._adjacency_list[t_id] = [e for e in self._adjacency_list[t_id] if e.edge_id != edge_id]

        del self.edges[edge_id]

    def has_cycle(self) -> bool:
        """
        Check if the graph has a cycle.
        Supports mixed (directed/undirected) graphs.
        """
        visited = set()
        rec_stack = set()
        parent_map = {}  # Needed for undirected cycle detection

        def dfs(node_id: str, parent_id: Optional[str]) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            parent_map[node_id] = parent_id

            node = self.nodes[node_id]

            # Use get_outgoing_edges which now supports undirected edges
            for edge in self.get_outgoing_edges(node):
                neighbor = edge.get_other_node(node)
                if not neighbor and edge.source_node == edge.target_node:
                    neighbor = node  # Self loop

                neighbor_id = neighbor.node_id

                if neighbor_id not in visited:
                    if dfs(neighbor_id, node_id):
                        return True
                elif neighbor_id in rec_stack:
                    # For undirected, we must not go directly back to parent
                    if edge.direction == EdgeDirection.UNDIRECTED:
                        if neighbor_id != parent_id:
                            return True
                    else:
                        # Directed back-edge always means cycle
                        return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id, None):
                    return True

        return False

    def get_subgraph_by_nodes(self, node_ids: Set[str]) -> 'Graph':
        """
        Create a subgraph (deep copy) with specified nodes.
        """
        subgraph = Graph(f"{self.graph_id}_sub")

        # Use deepcopy so changes to the subgraph don't affect the main graph
        for node_id in node_ids:
            if node_id in self.nodes:
                subgraph.add_node(deepcopy(self.nodes[node_id]))

        # Add edges only if both nodes exist in the subgraph
        for edge in self.edges.values():
            if edge.source_node.node_id in node_ids and \
                    edge.target_node.node_id in node_ids:
                # Must find new instances of nodes in the subgraph
                new_source = subgraph.get_node(edge.source_node.node_id)
                new_target = subgraph.get_node(edge.target_node.node_id)

                new_edge = Edge(
                    edge.edge_id,
                    new_source,
                    new_target,
                    edge.direction,
                    **edge.attributes
                )
                subgraph.add_edge(new_edge)

        return subgraph

    def get_number_of_nodes(self) -> int:
        return len(self.nodes)

    def get_number_of_edges(self) -> int:
        return len(self.edges)

    def __repr__(self) -> str:
        return f"Graph({self.graph_id}, nodes={len(self.nodes)}, edges={len(self.edges)})"

    def to_dict(self) -> Dict:
        return {
            'id': self.graph_id,
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'edges': [edge.to_dict() for edge in self.edges.values()]
        }