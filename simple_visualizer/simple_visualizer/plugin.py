"""
Simple Visualizer Plugin — renders a graph as circles + lines using D3.js.

Design Pattern: Strategy (implements VisualizerPlugin contract).

Each node is drawn as a circle with its ID (or Name attribute) as a label.
Edges are drawn as lines (with arrowheads for directed edges).
The layout uses D3.js force simulation for automatic positioning.

Interactions provided:
    • Drag-and-drop on nodes
    • Zoom / pan on the SVG canvas
    • Mouseover tooltip with node details
    • Click-to-select highlighting
"""
import json
from typing import Any

from api.models.graph import Graph
from api.plugins.base import VisualizerPlugin


class SimpleVisualizerPlugin(VisualizerPlugin):
    """
    Visualizes a graph using simple circles (nodes) and lines (edges)
    with a D3.js force-directed layout.
    """

    def get_plugin_name(self) -> str:
        return "Simple Visualizer"

    # ── Public API ───────────────────────────────────────────────

    def visualize(self, graph: Graph) -> str:
        """
        Convert a Graph into an HTML string containing an SVG rendered
        by D3.js with a force-directed layout.

        Args:
            graph: The Graph instance to visualize.

        Returns:
            HTML string with embedded ``<script>`` and ``<style>`` tags.
        """
        nodes_data = self._build_nodes(graph)
        edges_data = self._build_edges(graph)

        return self._render_html(nodes_data, edges_data)

    # ── Data builders ────────────────────────────────────────────

    @staticmethod
    def _build_nodes(graph: Graph) -> list:
        """Build JSON-serializable node list for D3."""
        nodes = []
        for node in graph.get_all_nodes():
            label = (
                node.get_attribute("Name")
                or node.get_attribute("name")
                or node.get_attribute("label")
                or node.node_id
            )
            attrs = {}
            for k, v in node.attributes.items():
                attrs[k] = _safe_str(v)
            nodes.append({
                "id": node.node_id,
                "label": str(label),
                "attributes": attrs,
            })
        return nodes

    @staticmethod
    def _build_edges(graph: Graph) -> list:
        """Build JSON-serializable edge list for D3."""
        edges = []
        for edge in graph.get_all_edges():
            attrs = {}
            for k, v in edge.attributes.items():
                attrs[k] = _safe_str(v)
            edges.append({
                "id": edge.edge_id,
                "source": edge.source_node.node_id,
                "target": edge.target_node.node_id,
                "directed": edge.is_directed(),
                "attributes": attrs,
            })
        return edges

    # ── HTML / JS template ───────────────────────────────────────

    @staticmethod
    def _render_html(nodes: list, edges: list) -> str:
        nodes_json = json.dumps(nodes, ensure_ascii=False, default=str)
        edges_json = json.dumps(edges, ensure_ascii=False, default=str)

        return f"""
<style>
.simple-vis-container {{
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
    background: #fafbfc;
    border-radius: 6px;
}}
.simple-vis-container svg {{
    width: 100%;
    height: 100%;
    display: block;
}}
.simple-vis-container .sv-link {{
    stroke: #999;
    stroke-opacity: 0.6;
    stroke-width: 1.5px;
    fill: none;
}}
.simple-vis-container .sv-node-circle {{
    stroke: #fff;
    stroke-width: 2px;
    cursor: grab;
    transition: r 0.15s ease;
}}
.simple-vis-container .sv-node-circle:hover {{
    r: 14;
}}
.simple-vis-container .sv-node-circle.selected {{
    stroke: #ff6600;
    stroke-width: 3px;
}}
.simple-vis-container .sv-label {{
    font: 11px sans-serif;
    fill: #333;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
    user-select: none;
}}
.simple-vis-container .sv-arrow {{
    fill: #999;
}}
.sv-tooltip {{
    position: absolute;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.82);
    color: #fff;
    border-radius: 4px;
    font: 12px/1.4 sans-serif;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    max-width: 280px;
    word-wrap: break-word;
    z-index: 1000;
}}
</style>

<div class="simple-vis-container" id="simple-vis-root">
    <div class="sv-tooltip" id="sv-tooltip"></div>
</div>

<script>
(function() {{
    const nodesData = {nodes_json};
    const edgesData = {edges_json};

    const container = document.getElementById('simple-vis-root');
    const tooltip   = document.getElementById('sv-tooltip');
    const width     = container.clientWidth  || 800;
    const height    = container.clientHeight || 600;

    /* ── Color scale ─────────────────────────────────── */
    const color = d3.scaleOrdinal(d3.schemeCategory10);

    /* ── SVG + zoom group ────────────────────────────── */
    const svg = d3.select(container)
        .append('svg')
        .attr('viewBox', [0, 0, width, height]);

    const g = svg.append('g');

    svg.call(d3.zoom()
        .scaleExtent([0.1, 8])
        .on('zoom', (event) => g.attr('transform', event.transform))
    );

    /* ── Arrow marker for directed edges ─────────────── */
    svg.append('defs').append('marker')
        .attr('id', 'sv-arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 22)
        .attr('refY', 0)
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('class', 'sv-arrow');

    /* ── Force simulation ────────────────────────────── */
    const simulation = d3.forceSimulation(nodesData)
        .force('link', d3.forceLink(edgesData).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(20));

    /* ── Draw edges ──────────────────────────────────── */
    const link = g.append('g')
        .selectAll('line')
        .data(edgesData)
        .join('line')
        .attr('class', 'sv-link')
        .attr('marker-end', d => d.directed ? 'url(#sv-arrowhead)' : null);

    /* ── Draw nodes ──────────────────────────────────── */
    const node = g.append('g')
        .selectAll('g')
        .data(nodesData)
        .join('g')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));

    node.append('circle')
        .attr('class', 'sv-node-circle')
        .attr('r', 10)
        .attr('fill', (d, i) => color(i % 10));

    node.append('text')
        .attr('class', 'sv-label')
        .attr('dy', -16)
        .text(d => d.label);

    /* ── Tooltip ─────────────────────────────────────── */
    node.on('mouseover', function(event, d) {{
        let html = '<strong>' + d.label + '</strong> <em>(' + d.id + ')</em><br>';
        for (const [k, v] of Object.entries(d.attributes)) {{
            html += k + ': ' + v + '<br>';
        }}
        tooltip.innerHTML = html;
        tooltip.style.opacity = 1;
    }})
    .on('mousemove', function(event) {{
        const rect = container.getBoundingClientRect();
        tooltip.style.left = (event.clientX - rect.left + 14) + 'px';
        tooltip.style.top  = (event.clientY - rect.top  - 10) + 'px';
    }})
    .on('mouseout', function() {{
        tooltip.style.opacity = 0;
    }});

    /* ── Click-to-select ─────────────────────────────── */
    node.on('click', function(event, d) {{
        d3.selectAll('.sv-node-circle').classed('selected', false);
        d3.select(this).select('circle').classed('selected', true);
        /* Dispatch custom event for cross-view sync */
        container.dispatchEvent(new CustomEvent('node-selected', {{ detail: {{ nodeId: d.id }} }}));
    }});

    /* ── Tick ─────────────────────────────────────────── */
    simulation.on('tick', () => {{
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
    }});

    /* ── Drag handlers ───────────────────────────────── */
    function dragStarted(event, d) {{
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
    }}
    function dragged(event, d) {{
        d.fx = event.x; d.fy = event.y;
    }}
    function dragEnded(event, d) {{
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
    }}
}})();
</script>
"""


def _safe_str(value: Any) -> str:
    """Convert a value to a safe string for JSON serialization."""
    if value is None:
        return ""
    return str(value)
