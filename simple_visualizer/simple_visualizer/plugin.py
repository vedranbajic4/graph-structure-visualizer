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
                "label": _safe_str(edge.get_attribute("label")) if edge.get_attribute("label") else "",
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
.simple-vis-container .sv-edge-label {{
    font: 10px sans-serif;
    fill: #555;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
    user-select: none;
    background: white;
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

    const zoomBehavior = d3.zoom()
        .scaleExtent([0.1, 8])
        .on('zoom', (event) => {{
            g.attr('transform', event.transform);
            const t = event.transform;
            document.dispatchEvent(new CustomEvent('sv-positions', {{
                detail: {{
                    positions: nodesData.map(n => ({{ id: n.id, x: n.x || 0, y: n.y || 0 }})),
                    edges: edgesData,
                    mainTransform: {{ k: t.k, x: t.x, y: t.y }},
                    viewWidth: width,
                    viewHeight: height,
                }}
            }}));
        }});
    svg.call(zoomBehavior);

    /* ── Listen for bird-navigate: pan to graph point ── */
    document.addEventListener('bird-navigate', (e) => {{
        const {{ graphX, graphY }} = e.detail;
        const currentT = d3.zoomTransform(svg.node());
        const newT = d3.zoomIdentity
            .translate(width / 2 - graphX * currentT.k, height / 2 - graphY * currentT.k)
            .scale(currentT.k);
        svg.transition().duration(300).call(zoomBehavior.transform, newT);
    }});

    /* ── Arrow markers ───────────────────────────────── */
    const defs = svg.append('defs');
    // Forward arrowhead (marker-end)
    defs.append('marker')
        .attr('id', 'sv-arrow-end')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 10).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('class', 'sv-arrow');
    // Reverse arrowhead (marker-start) — points back toward source
    defs.append('marker')
        .attr('id', 'sv-arrow-start')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 10).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto-start-reverse')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('class', 'sv-arrow');

    /* ── Merge bidirectional edge pairs into one visual line ── */
    // Build a map: canonical-key → [ edgeA, edgeB? ]
    const edgeMap = new Map();
    edgesData.forEach(e => {{
        const ids = [e.source, e.target].sort();
        const key = ids.join('|');
        if (!edgeMap.has(key)) edgeMap.set(key, []);
        edgeMap.get(key).push(e);
    }});

    // lineData: one entry per unique node pair, carries both edge refs
    const lineData = [];
    edgeMap.forEach(group => {{
        // group[0] is always the "forward" edge, group[1] the reverse (if any)
        lineData.push({{
            key: group.map(e => e.id).join('+'),
            fwd: group[0],                      // edge drawn source→target
            rev: group[1] || null,              // edge drawn target→source (if bi)
            sourceId: group[0].source,
            targetId: group[0].target,
        }});
    }});

    /* ── Force simulation — use original edgesData for physics ── */
    const simulation = d3.forceSimulation(nodesData)
        .force('link', d3.forceLink(edgesData).id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(20));

    const NODE_R = 10;

    // Resolve a node ref (string id or object after simulation binds it)
    function resolveNode(ref) {{
        if (typeof ref === 'object') return ref;
        return nodesData.find(n => n.id === ref);
    }}

    function lineCoords(ld) {{
        const s = resolveNode(ld.fwd.source);
        const t = resolveNode(ld.fwd.target);
        if (!s || !t) return {{ x1:0,y1:0,x2:0,y2:0 }};
        const dx = t.x - s.x, dy = t.y - s.y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        const off = NODE_R + 2;
        return {{
            x1: s.x + (dx/dist)*off,
            y1: s.y + (dy/dist)*off,
            x2: t.x - (dx/dist)*off,
            y2: t.y - (dy/dist)*off,
            s, t, dx, dy, dist,
        }};
    }}

    /* ── Draw one line per node-pair ─────────────────── */
    const link = g.append('g')
        .selectAll('line')
        .data(lineData)
        .join('line')
        .attr('class', 'sv-link')
        .attr('marker-end',   ld => ld.fwd.directed           ? 'url(#sv-arrow-end)'   : null)
        .attr('marker-start', ld => ld.rev && ld.rev.directed ? 'url(#sv-arrow-start)' : null);

    /* ── Label data: one entry per edge tip that has a label ── */
    // Each tip is {{ edge, atTarget: true/false }}
    const tipData = [];
    lineData.forEach(ld => {{
        if (ld.fwd.label) tipData.push({{ ld, edge: ld.fwd, atTarget: true  }});
        if (ld.rev && ld.rev.label) tipData.push({{ ld, edge: ld.rev, atTarget: false }});
    }});

    /* ── Label groups, hidden by default ─────────────── */
    const edgeLabelGroup = g.append('g').attr('class', 'sv-edge-labels');
    const edgeLabelGs = edgeLabelGroup
        .selectAll('g')
        .data(tipData)
        .join('g')
        .style('opacity', 0)
        .style('pointer-events', 'none');

    edgeLabelGs.append('rect')
        .attr('fill', 'rgba(255,255,255,0.92)')
        .attr('rx', 3).attr('ry', 3)
        .attr('height', 16).attr('y', -8)
        .each(function(td) {{
            const w = td.edge.label.length * 6.5 + 10;
            d3.select(this).attr('width', w).attr('x', -w / 2);
        }});

    edgeLabelGs.append('text')
        .attr('class', 'sv-edge-label')
        .text(td => td.edge.label);

    /* ── Hit zones: small transparent circles near each tip ── */
    // Rendered after labels so they sit on top
    const tipHit = g.append('g')
        .selectAll('circle')
        .data(tipData)
        .join('circle')
        .attr('r', 18)
        .attr('fill', 'transparent')
        .style('cursor', 'pointer')
        .on('mouseover', function(event, td) {{
            const idx = tipData.indexOf(td);
            d3.select(edgeLabelGs.nodes()[idx]).style('opacity', 1);
        }})
        .on('mouseout', function(event, td) {{
            const idx = tipData.indexOf(td);
            d3.select(edgeLabelGs.nodes()[idx]).style('opacity', 0);
        }});

    /* ── Draw nodes ──────────────────────────────────── */
    const node = g.append('g')
        .selectAll('g')
        .data(nodesData)
        .join('g')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag',  dragged)
            .on('end',   dragEnded));

    node.append('circle')
        .attr('class', 'sv-node-circle')
        .attr('r', NODE_R)
        .attr('fill', (d, i) => color(i % 10));

    node.append('text')
        .attr('class', 'sv-label')
        .attr('dy', -16)
        .text(d => d.label);

    /* ── Node tooltip ────────────────────────────────── */
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
    .on('mouseout', function() {{ tooltip.style.opacity = 0; }});

    /* ── Click-to-select ─────────────────────────────── */
    node.on('click', function(event, d) {{
        d3.selectAll('.sv-node-circle').classed('selected', false);
        d3.select(this).select('circle').classed('selected', true);
        container.dispatchEvent(new CustomEvent('node-selected', {{ detail: {{ nodeId: d.id }} }}));
    }});

    /* ── Tick ────────────────────────────────────────── */
    simulation.on('tick', () => {{
        // Update lines
        link.each(function(ld) {{
            const c = lineCoords(ld);
            d3.select(this)
                .attr('x1', c.x1).attr('y1', c.y1)
                .attr('x2', c.x2).attr('y2', c.y2);
        }});

        node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);

        // Position each tip hit-circle and label near the right arrowhead
        const TIP_BACK = NODE_R + 22; // px from the target node centre
        function tipPos(td) {{
            const c = lineCoords(td.ld);
            if (!c.s) return {{x:0,y:0}};
            if (td.atTarget) {{
                // near the target end of fwd edge
                return {{
                    x: c.t.x - (c.dx/c.dist) * TIP_BACK,
                    y: c.t.y - (c.dy/c.dist) * TIP_BACK,
                }};
            }} else {{
                // near the source end (= reverse arrow tip)
                return {{
                    x: c.s.x + (c.dx/c.dist) * TIP_BACK,
                    y: c.s.y + (c.dy/c.dist) * TIP_BACK,
                }};
            }}
        }}

        tipHit.attr('cx', td => tipPos(td).x).attr('cy', td => tipPos(td).y);
        edgeLabelGs.attr('transform', td => {{
            const p = tipPos(td);
            return `translate(${{p.x}},${{p.y}})`;
        }});

        /* Emit live node positions + zoom transform to bird view */
        const positions = nodesData.map(n => ({{ id: n.id, x: n.x, y: n.y }}));
        const t = d3.zoomTransform(svg.node());
        document.dispatchEvent(new CustomEvent('sv-positions', {{
            detail: {{
                positions,
                edges: edgesData,
                mainTransform: {{ k: t.k, x: t.x, y: t.y }},
                viewWidth: width,
                viewHeight: height,
            }}
        }}));
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