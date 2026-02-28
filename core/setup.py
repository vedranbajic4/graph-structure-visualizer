from setuptools import setup, find_packages

setup(
    name='graph-visualizer-core',
    version='1.0.0',
    description='Core platform for Graph Structure Visualizer',
    packages=find_packages(),
    install_requires=[
        'graph-visualizer-api',
    ],
    python_requires='>=3.8',
)
