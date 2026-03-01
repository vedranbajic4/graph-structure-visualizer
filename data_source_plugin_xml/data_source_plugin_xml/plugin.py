from api.plugins import DataSourcePlugin

from api.models.graph import Graph
from api.models.edge import Edge, EdgeDirection
from api.models.node import Node

from lxml import etree
from typing import Dict, List, Tuple


class XMLNode(Node):
    pass

class XmlDataSourcePlugin(DataSourcePlugin):
    """
    DataSourcePlugin for XML files.
    """

    def get_plugin_name(self) -> str:
        return "XML Parser"

    # TODO: Add checks if XML file is valid

    def parse(self, file_path: str) -> Graph:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_comments=True)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()

        graph = Graph(graph_id=file_path)

        id_map = {}
        self._assign_node_ids(tree, root, id_map, {})

        connection_map = {}
        self._build_graph(graph, tree, root, id_map, connection_map)

        for source_key, connections in connection_map.items():
            source_node = graph.get_node(source_key)

            for relation_name, target_id in connections:
                target_node = graph.get_node(target_id)

                edge = Edge(edge_id=f'child:{source_key}->{target_id}',
                            source_node=source_node,
                            target_node=target_node,
                            label=relation_name)
                
                graph.add_edge(edge)

        return graph
    
    def _build_graph(self,
                     graph: Graph,
                     tree: etree._ElementTree,
                     root: etree._Element,
                     id_map: Dict[str, str],
                     connection_map: Dict[str, List[Tuple]]
                     ) -> Node:
        current_id = id_map[tree.getpath(root)]
        label = etree.QName(root.tag).localname
        current_node = XMLNode(current_id, label=label)

        graph.add_node(current_node)

        for attr_name, attr_value in root.attrib.items():
            attr_node = XMLNode(node_id=f'{current_id}:{attr_name}', value=attr_value)
            graph.add_node(attr_node)
            attr_edge = Edge(source_node=current_node,
                             target_node=attr_node,
                             edge_id=f'attr:{current_id}->{attr_name}',
                             EdgeDirection = EdgeDirection.DIRECTED,
                             attr=attr_name)
            graph.add_edge(attr_edge)
        
        for child in root:
            # Handle cyclic edges
            # Child is wrapper for reference
            if len(child) == 1 and 'reference' in child[0].attrib:
                relation_name = etree.QName(child.tag).localname

                node_xpath = child[0].attrib['reference']
                targets = tree.getroot().xpath(node_xpath)

                if len(targets) != 1:
                    raise ValueError(
                    f"Invalid reference '{node_xpath}' in XML: expected exactly 1 target, found {len(targets)}."
                    )
                
                target = targets[0]
                target_id = id_map[tree.getpath(target)]
                connection_map.setdefault(current_id, []).append((relation_name, target_id))

            # Leaf node -> same as attribute
            elif len(child) == 0:
                attribute_name = etree.QName(child.tag).localname

                leaf_text = child.text.strip() if child.text else ''
                attr_node = XMLNode(node_id=f'{current_id}:{attribute_name}', value=leaf_text)
                graph.add_node(attr_node)

                # If the edge has any attributes just add them directly
                edge_attributes = dict(child.attrib)

                attr_edge = Edge(edge_id=f'attr:{current_id}->{attribute_name}',
                                    source_node=current_node,
                                    target_node=attr_node,
                                    EdgeDirection=EdgeDirection.DIRECTED,
                                    label=attribute_name,
                                    **edge_attributes)

                graph.add_edge(attr_edge)

            # Has grandchildren -> new child object
            else:
                child_node = self._build_graph(graph, tree, child, id_map, connection_map)

                child_xpath = tree.getpath(child)
                child_id = id_map.get(child_xpath)
                edge_id = f"child:{current_id}->{child_id}"

                graph.add_edge(Edge(edge_id=edge_id,
                                    source_node=current_node,
                                    target_node=child_node,
                                    EdgeDirection=EdgeDirection.DIRECTED,
                                    label="Child")) # TODO: Vidi sta ces sa label kada ima GUI

        return current_node
    
    def _assign_node_ids(self,
                        tree: etree._ElementTree,
                        root: etree._Element,
                        id_map: Dict[str, str],
                        tag_count: Dict[str, int]
                        ) -> Dict[str, str]:
        """
        Creates a map which maps absolute xpaths into human readable unique ids.
        """
        if 'reference' in root.attrib:
            return id_map

        local = etree.QName(root.tag).localname

        tag_count[local] = tag_count.get(local, 0) + 1

        # i.e. Person[1], Person[2]
        generated_id = f"{local}[{tag_count[local]}]"

        id_map[tree.getpath(root)] = generated_id

        for child in root:
            self._assign_node_ids(tree, child, id_map, tag_count)
        
        return id_map

if __name__ == '__main__':
    plugin = XmlDataSourcePlugin()

    graph = plugin.parse("tests/plugin_test/fixtures/xml_graph1.xml")

    nodes = graph.get_all_nodes()
    edges = graph.get_all_edges()

    for node in nodes:
        print(node.node_id)
        print(node.get_all_attributes())
        print("----")
    print("------------------------")

    for edge in edges:
        print(edge.edge_id)
        print(edge.get_all_attributes())
        print("----")