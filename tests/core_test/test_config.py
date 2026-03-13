# tests/core_test/test_config.py
"""
Tests for PlatformConfig and SerializationConfig.

Covers:
    • Default values
    • effective_node_fields with include / exclude combos
    • effective_edge_fields with include / exclude combos
    • PlatformConfig wiring
"""
import pytest
from graph_platform.config import SerializationConfig, PlatformConfig


# ═════════════════════════════════════════════════════════════════
#  SerializationConfig defaults
# ═════════════════════════════════════════════════════════════════

class TestSerializationConfigDefaults:

    def test_default_include_node_fields_is_none(self):
        cfg = SerializationConfig()
        assert cfg.include_node_fields is None

    def test_default_exclude_node_fields_is_empty(self):
        cfg = SerializationConfig()
        assert cfg.exclude_node_fields == set()

    def test_default_include_edge_fields_is_none(self):
        cfg = SerializationConfig()
        assert cfg.include_edge_fields is None

    def test_default_exclude_edge_fields_is_empty(self):
        cfg = SerializationConfig()
        assert cfg.exclude_edge_fields == set()

    def test_default_include_types_is_true(self):
        cfg = SerializationConfig()
        assert cfg.include_types is True

    def test_default_date_format_is_iso(self):
        cfg = SerializationConfig()
        assert cfg.date_format == "iso"


# ═════════════════════════════════════════════════════════════════
#  effective_node_fields
# ═════════════════════════════════════════════════════════════════

class TestEffectiveNodeFields:

    def test_no_include_no_exclude_returns_all(self):
        """When include is None and exclude is empty, all fields returned."""
        cfg = SerializationConfig()
        available = {"Name", "Age", "City"}
        result = cfg.effective_node_fields(available)
        assert result == {"Name", "Age", "City"}

    def test_include_only_whitelisted(self):
        """Only fields in include_node_fields are kept."""
        cfg = SerializationConfig(include_node_fields={"Name", "Age"})
        available = {"Name", "Age", "City", "Score"}
        result = cfg.effective_node_fields(available)
        assert result == {"Name", "Age"}

    def test_include_with_nonexistent_field(self):
        """Include fields that aren't available are simply ignored."""
        cfg = SerializationConfig(include_node_fields={"Name", "Nonexistent"})
        available = {"Name", "Age"}
        result = cfg.effective_node_fields(available)
        assert result == {"Name"}

    def test_exclude_only(self):
        """Exclude removes specific fields from full set."""
        cfg = SerializationConfig(exclude_node_fields={"City"})
        available = {"Name", "Age", "City"}
        result = cfg.effective_node_fields(available)
        assert result == {"Name", "Age"}

    def test_exclude_nonexistent_field(self):
        """Excluding a field that doesn't exist has no effect."""
        cfg = SerializationConfig(exclude_node_fields={"Ghost"})
        available = {"Name", "Age"}
        result = cfg.effective_node_fields(available)
        assert result == {"Name", "Age"}

    def test_include_then_exclude(self):
        """Exclude is applied AFTER include."""
        cfg = SerializationConfig(
            include_node_fields={"Name", "Age", "City"},
            exclude_node_fields={"City"},
        )
        available = {"Name", "Age", "City", "Score"}
        result = cfg.effective_node_fields(available)
        assert result == {"Name", "Age"}

    def test_include_and_exclude_same_field(self):
        """If a field is in both include and exclude, exclude wins."""
        cfg = SerializationConfig(
            include_node_fields={"Name"},
            exclude_node_fields={"Name"},
        )
        available = {"Name", "Age"}
        result = cfg.effective_node_fields(available)
        assert result == set()

    def test_empty_available(self):
        """No available fields → empty result regardless of config."""
        cfg = SerializationConfig(include_node_fields={"Name"})
        result = cfg.effective_node_fields(set())
        assert result == set()


# ═════════════════════════════════════════════════════════════════
#  effective_edge_fields
# ═════════════════════════════════════════════════════════════════

class TestEffectiveEdgeFields:

    def test_no_include_no_exclude_returns_all(self):
        cfg = SerializationConfig()
        available = {"Weight", "Relation"}
        result = cfg.effective_edge_fields(available)
        assert result == {"Weight", "Relation"}

    def test_include_only_whitelisted(self):
        cfg = SerializationConfig(include_edge_fields={"Weight"})
        available = {"Weight", "Relation", "Since"}
        result = cfg.effective_edge_fields(available)
        assert result == {"Weight"}

    def test_exclude_only(self):
        cfg = SerializationConfig(exclude_edge_fields={"Since"})
        available = {"Weight", "Relation", "Since"}
        result = cfg.effective_edge_fields(available)
        assert result == {"Weight", "Relation"}

    def test_include_then_exclude(self):
        cfg = SerializationConfig(
            include_edge_fields={"Weight", "Relation"},
            exclude_edge_fields={"Relation"},
        )
        available = {"Weight", "Relation", "Since"}
        result = cfg.effective_edge_fields(available)
        assert result == {"Weight"}


# ═════════════════════════════════════════════════════════════════
#  PlatformConfig
# ═════════════════════════════════════════════════════════════════

class TestPlatformConfig:

    def test_default_serialization_config(self):
        cfg = PlatformConfig()
        assert isinstance(cfg.serialization, SerializationConfig)

    def test_default_max_history_depth(self):
        cfg = PlatformConfig()
        assert cfg.max_history_depth == 50

    def test_default_visualizer_is_none(self):
        cfg = PlatformConfig()
        assert cfg.default_visualizer is None

    def test_custom_values(self):
        ser = SerializationConfig(include_types=False)
        cfg = PlatformConfig(
            serialization=ser,
            max_history_depth=10,
            default_visualizer="simple",
        )
        assert cfg.serialization.include_types is False
        assert cfg.max_history_depth == 10
        assert cfg.default_visualizer == "simple"

    def test_serialization_config_fields_are_independent(self):
        """Two PlatformConfig instances should have independent SerializationConfigs."""
        cfg1 = PlatformConfig()
        cfg2 = PlatformConfig()
        cfg1.serialization.include_types = False
        assert cfg2.serialization.include_types is True
