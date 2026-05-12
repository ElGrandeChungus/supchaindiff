import pytest
import yaml
from config import Config, load_config


def test_composite_key_always_derived():
    config = Config(ben_column="Tool ID", part_number_column="PN")
    assert config.composite_key_columns == ["PN", "Tool ID"]


def test_composite_key_updates_when_ben_column_changes():
    config = Config(ben_column="BEN", part_number_column="Part Number")
    assert config.composite_key_columns == ["Part Number", "BEN"]
    config.ben_column = "NEW_BEN"
    assert config.composite_key_columns == ["Part Number", "NEW_BEN"]


def test_composite_key_not_loaded_from_yaml(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "composite_key_columns: [EVIL_KEY]\n"
        "ben_column: BEN\n"
        "part_number_column: Part Number\n"
    )
    config = load_config(str(yaml_file))
    assert config.composite_key_columns == ["Part Number", "BEN"]
    assert "EVIL_KEY" not in config.composite_key_columns


def test_defaults():
    config = Config()
    assert config.ben_column == "BEN"
    assert config.part_number_column == "Part Number"
    assert config.ben_aliases == ["P1A", "FCID"]
    assert config.exclude_columns == []
    assert config.tool_order == []
    assert config.llm_base_url == "http://localhost:11434/v1"
    assert config.llm_timeout_seconds == 30
    assert config.llm_enabled is True


def test_load_config_reads_yaml(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "ben_column: MY_BEN\n"
        "part_number_column: MY_PN\n"
        "llm_enabled: false\n"
        "tool_order:\n  - T1\n  - T2\n"
    )
    config = load_config(str(yaml_file))
    assert config.ben_column == "MY_BEN"
    assert config.part_number_column == "MY_PN"
    assert config.llm_enabled is False
    assert config.tool_order == ["T1", "T2"]


def test_load_config_falls_back_to_defaults_for_missing_keys(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("ben_column: CUSTOM\n")
    config = load_config(str(yaml_file))
    assert config.part_number_column == "Part Number"
    assert config.llm_enabled is True
