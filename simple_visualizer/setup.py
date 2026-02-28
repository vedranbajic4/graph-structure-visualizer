from setuptools import setup, find_packages

setup(
    name='simple-visualizer',
    version='1.0.0',
    description='Simple Visualizer Plugin for Graph Structure Visualizer',
    packages=find_packages(),
    install_requires=[
        'graph-visualizer-api',
    ],
    entry_points={
        'graph_visualizer.visualizer': [
            'simple = simple_visualizer.plugin:SimpleVisualizerPlugin',
        ],
    },
    python_requires='>=3.8',
)
