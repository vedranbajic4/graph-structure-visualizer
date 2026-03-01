import pytest
from pathlib import Path
from data_source_plugin_rdf.data_source_plugin_rdf.plugin import RDFTurtleDataSourcePlugin

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def plugin():
    return RDFTurtleDataSourcePlugin()


@pytest.fixture
def sample_ttl_path():
    return str(FIXTURES_DIR / "simple_graph1.ttl")


@pytest.fixture
def parsed_graph(plugin, sample_ttl_path):
    return plugin.parse(sample_ttl_path)
