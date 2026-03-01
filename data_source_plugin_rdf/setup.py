from setuptools import setup, find_packages

setup(
    name='data-source-plugin-rdf-turtle',
    version='1.0.0',
    description='RDF Turtle Data Source Plugin for Graph Structure Visualizer',
    packages=find_packages(),
    install_requires=[
        'graph-visualizer-api',
        'rdflib>=6.0.0',
    ],
    entry_points={
        'graph_visualizer.data_source': [
            'rdf_turtle = data_source_plugin_rdf_turtle.plugin:RDFTurtleDataSourcePlugin',
        ],
    },
    python_requires='>=3.8',
)
