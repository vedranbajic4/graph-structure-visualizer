# tests/core_test/test_filter_service.py

import pytest
from core.services.filter_service import FilterService
from core.services.exceptions import FilterParseError


@pytest.fixture
def service():
    return FilterService()


class TestCommit1Validation:

    def test_filter_empty_query_raises_error(self, service, stub_graph):
        with pytest.raises(FilterParseError):
            service.filter(stub_graph, "")

        with pytest.raises(FilterParseError):
            service.filter(stub_graph, "   ")

    def test_filter_none_query_raises_error(self, service, stub_graph):
        with pytest.raises(FilterParseError):
            service.filter(stub_graph, None)