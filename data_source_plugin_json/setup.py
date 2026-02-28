from setuptools import setup, find_packages

setup(
    name='data-source-plugin-json',
    version='1.0.0',
    description='JSON Data Source Plugin for Graph Structure Visualizer',
    packages=find_packages(),
    install_requires=[
        'graph-visualizer-api',
    ],
    entry_points={
        'graph_visualizer.data_source': [
            'json = data_source_plugin_json.plugin:JsonDataSourcePlugin',
        ],
    },
    python_requires='>=3.8',
)
