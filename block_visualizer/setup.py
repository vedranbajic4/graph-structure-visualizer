from setuptools import setup, find_packages

setup(
    name='block-visualizer',
    version='1.0.0',
    description='Block Visualizer Plugin for Graph Structure Visualizer',
    packages=find_packages(),
    install_requires=[
        'graph-visualizer-api',
    ],
    entry_points={
        'graph_visualizer.visualizer': [
            'block = block_visualizer.plugin:BlockVisualizerPlugin',
        ],
    },
    python_requires='>=3.8',
)
