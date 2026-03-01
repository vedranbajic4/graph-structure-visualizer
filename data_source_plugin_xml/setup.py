from setuptools import setup, find_packages

setup(
    name='data-source-plugin-xml',
    version='1.0.0',
    description='XML Data Source Plugin for Graph Structure Visualizer',
    packages=find_packages(),
    install_requires=[
        'graph-visualizer-api',
        'lxml>=6.0.0'
    ],
    entry_points={
        'graph_visualizer.data_source': [
            'xml = data_source_plugin_xml.plugin:XmlDataSourcePlugin',
        ],
    },
    python_requires='>=3.8',
)
