"""
Block Visualizer Plugin
"""
import json
from typing import Any

from api.models.graph import Graph
from api.plugins.base import VisualizerPlugin


class BlockVisualizerPlugin(VisualizerPlugin):
    """
    Visualizes a graph as block tables (nodes) and lines (edges)
    with a D3.js force-directed layout.
    """

    def get_plugin_name(self) -> str:
        return "Block Visualizer"

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
            node_attributes = node.attributes
            
            # If node represents value
            if 'value' in node.attributes:
                continue

            node_attributes = dict(node.attributes or {})

            outgoing = graph.get_outgoing_edges(node)

            for edge in outgoing:
                if edge.edge_id.startswith('attr'):
                    attr_name = edge.attributes.get('label')
                    attr_value = edge.target_node.attributes.get('value')
                    if attr_name is not None and attr_value is not None:
                        node_attributes[attr_name] = _safe_str(attr_value)

            label = (
                node.get_attribute("Name")
                or node.get_attribute("name")
                or node.get_attribute("label")
                or node.node_id
            )
            attrs = {}
            for k, v in node_attributes.items():
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

            # if attr node
            if edge.edge_id.startswith('attr'):
                continue

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

        font = 'sans-serif'
        font_size = '12px'

        return f"""
<style>

    .block-vis-container {{
        width: 100%;
        height: 100%;
        position: relative;
        overflow: hidden;
        background: #fafbfc;
        border-radius: 6px;
    }}
    .block-vis-container svg {{
        width: 100%;
        height: 100%;
        display: block;
    }}
    .block-vis-container .sv-link {{
        stroke: #999;
        stroke-opacity: 0.6;
        stroke-width: 1.5px;
        fill: none;
    }}

    .block-vis-container .sv-label {{
        font: 11px {font};
        fill: #333;
        pointer-events: none;
        text-anchor: middle;
        dominant-baseline: central;
        user-select: none;
    }}
    .block-vis-container .sv-arrow {{
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

    .sv-node-circle {{
        fill: none;
        stroke: transparent;
        stroke-width: 3px;
        pointer-events: none;
    }}

    .sv-node-circle.selected {{
        stroke: #ff6600;
    }}

    .sv-fo-wrapper {{ font: {font_size} {font}; }}
    .sv-table {{
    border-collapse: collapse;
    width: auto;
    table-layout: auto;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    border-radius: 4px;
    overflow: hidden;
    }}
    .sv-table .tbl-header {{
        background:#f2f2f2;
        color:#ffffff;
        text-align:center;
        padding:4px;
        font-weight:700;
        }}
    .sv-table td {{ padding: 4px 6px; border-top: 1px solid #eee; word-wrap: break-word; }}
    .sv-table td.k {{ font-weight:600; width: 45%; }}
    .sv-table td.v {{ width: 55%; }}
    .node-fo {{ pointer-events: all; }}

</style>

<div class="block-vis-container" id="block-vis-root">
    <div class="sv-tooltip" id="sv-tooltip"></div>
</div>

<script>
(function() {{
    const nodesData = {nodes_json};
    const edgesData = {edges_json};

    const container = document.getElementById('block-vis-root');
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
                    positions: nodesData.map((n, i) => ({{ id: n.id, x: n.x || 0, y: n.y || 0, width: n.width || 0, height: n.height || 0, label: n.label, colorIndex: i }})),
                    edges: edgesData,
                    mainTransform: {{ k: t.k, x: t.x, y: t.y }},
                    viewWidth: width,
                    viewHeight: height,
                }}
            }}));
        }});
    svg.call(zoomBehavior);

    /* ── Listen for bird-navigate ── */
    document.addEventListener('bird-navigate', (e) => {{
        const {{ graphX, graphY }} = e.detail;
        const currentT = d3.zoomTransform(svg.node());
        const newT = d3.zoomIdentity
            .translate(width / 2 - graphX * currentT.k, height / 2 - graphY * currentT.k)
            .scale(currentT.k);
        svg.transition().duration(300).call(zoomBehavior.transform, newT);
    }});

    /* ── Listen for bird-pan-delta: viewport drag in bird view ── */
    document.addEventListener('bird-pan-delta', (e) => {{
        const {{ dgx, dgy }} = e.detail;
        const currentT = d3.zoomTransform(svg.node());
        const newT = d3.zoomIdentity
            .translate(currentT.x - dgx * currentT.k, currentT.y - dgy * currentT.k)
            .scale(currentT.k);
        svg.call(zoomBehavior.transform, newT);
    }});

    /* ── Listen for bird-zoom: scroll wheel in bird view ── */
    document.addEventListener('bird-zoom', (e) => {{
        const {{ zoomIn }} = e.detail;
        const currentT = d3.zoomTransform(svg.node());
        const factor = zoomIn ? 1.15 : 1 / 1.15;
        const newK = currentT.k * factor;
        const newT = d3.zoomIdentity
            .translate(width / 2 - (width / 2 - currentT.x) * factor, height / 2 - (height / 2 - currentT.y) * factor)
            .scale(newK);
        svg.call(zoomBehavior.transform, newT);
    }});

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


    /* ── Draw edges ──────────────────────────────────── */
    const link = g.append('g')
        .selectAll('line')
        .data(edgesData)
        .join('line')
        .attr('class', 'sv-link')
        .attr('marker-end', d => d.directed ? 'url(#sv-arrowhead)' : null);

    /* ── Draw nodes ──────────────────────────────────── */
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.font = '{font_size} {font}';
    function textWidth(text) {{ return ctx.measureText(String(text)).width; }}

    const node = g.append('g')
        .selectAll('g')
        .data(nodesData)
        .join('g')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));

    function listFromAttributes(node) {{
        return Object.entries(node.attributes).map(([k,v]) => ({{ key:k, value:v }}));
    }}

    function tableSize(node) {{
        const rows = listFromAttributes(node);
        const pxPerRow = 40;
        const headerHeight = 26;
        const padding = 12;
        let maxText = Math.max(
            textWidth(node.label),
            ...rows.map(r => Math.max(textWidth(r.key), textWidth(r.value)))
            );
        const width = Math.ceil((maxText + padding) * 2); // width = width of longest text in cell + padding * 2
        const height = headerHeight + rows.length * pxPerRow;
        return {{ width, height }}
    }}

    const measure = document.createElement("div");
    measure.className = "sv-fo-wrapper"; 
    measure.style.position = "absolute";
    measure.style.visibility = "hidden";
    measure.style.pointerEvents = "none";
    measure.style.left = "-10000px";
    measure.style.top = "-10000px";
    measure.style.boxSizing = "border-box"; 
    measure.style.whiteSpace = "normal"; 
    document.body.appendChild(measure);


    node.each(function(d, i) {{
      const rows = listFromAttributes(d);

      const html = `
        <div class="sv-fo-wrapper">
          <table class="sv-table">
            <thead>
              <tr><th colspan="2" class="tbl-header" style="background:${{color(i % 10)}}">${{d.label}}</th></tr>
            </thead>
            <tbody>
              ${{rows.map(r => `<tr><td class="k">${{r.key}}</td><td class="v">${{r.value}}</td></tr>`).join("")}}
            </tbody>
          </table>
        </div>
      `;

      // first put the html table into measure area to get the size
      measure.innerHTML = html;
      
      const wrapper = measure.firstElementChild;

      const w = Math.ceil(wrapper.offsetWidth) + 2;
      const h = Math.ceil(wrapper.offsetHeight) + 4;

      d.width = w;
      d.height = h;

      // Highlight rectangle
      d3.select(this)
        .append("rect")
        .attr("class", "sv-node-circle")
        .attr("x", -w / 2 -1)
        .attr("y", -h / 2 -1)
        .attr("width", w + 2)
        .attr("height", h + 2)
        .attr("rx", 6)
        .attr("ry", 6);

      const fo = d3.select(this)
        .append("foreignObject")
        .attr("class", "node-fo")
        .attr("overflow", "visible")
        .attr("width", w)
        .attr("height", h)
        .attr("x", -w / 2)
        .attr("y", -h / 2);

      fo.append("xhtml:div")
        .attr("xmlns", "http://www.w3.org/1999/xhtml")
        .html(html);

    }});

    node.attr('data-node-id', d => d.id)
    
    const simulation = d3.forceSimulation(nodesData)
    .force('link', d3.forceLink(edgesData).id(d => d.id).distance(400))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('x', d3.forceX(width / 2).strength(0.04))
    .force('y', d3.forceY(height / 2).strength(0.04))
    .force('collision', d3.forceCollide(d =>
        Math.sqrt(d.width * d.width + d.height * d.height) / 2 + 4
    ))
    .velocityDecay(0.45);

    /* ── Tooltip ─────────────────────────────────────── */
    let isDragging = false;
    node.on('mouseover', function(event, d) {{
        if (isDragging) return;
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
        event.stopPropagation();
        d3.selectAll('.sv-node-circle').classed('selected', false);
        d3.select(this).select('.sv-node-circle').classed('selected', true);
        container.dispatchEvent(new CustomEvent('node-selected', {{ detail: {{ nodeId: d.id }} }}));
    }});

    /* Click SVG background → deselect */
    svg.on('click', function() {{
        if (typeof deselectAllNodes === 'function') deselectAllNodes();
    }});

    /* ── Tick ─────────────────────────────────────────── */

    simulation.on('tick', () => {{
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y - (d.source.height || 0) / 2)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y - (d.target.height || 0) / 2);

      node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);

      const t = d3.zoomTransform(svg.node());
      document.dispatchEvent(new CustomEvent('sv-positions', {{
        detail: {{
          positions: nodesData.map((n, i) => ({{ id: n.id, x: n.x || 0, y: n.y || 0, width: n.width || 0, height: n.height || 0, label: n.label, colorIndex: i }})),
          edges: edgesData,
          mainTransform: {{ k: t.k, x: t.x, y: t.y }},
          viewWidth: width,
          viewHeight: height,
        }}
      }}));
    }});


    /* ── Drag handlers ───────────────────────────────── */
    function dragStarted(event, d) {{
        isDragging = true;
        tooltip.style.opacity = 0;
        if (!event.active) simulation.alphaTarget(0.08).restart();
        d.fx = d.x; d.fy = d.y;
    }}
    function dragged(event, d) {{
        d.fx = event.x; d.fy = event.y;
    }}
    function dragEnded(event, d) {{
        isDragging = false;
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