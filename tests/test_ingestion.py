import pandas as pd
import pytest
from config import Config
from ingestion import validate_columns, find_duplicate_keys, load_sheet


def test_validate_columns_passes_when_all_present():
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [1]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [2]})
    config = Config()
    validate_columns(df_a, df_b, config)  # must not raise


def test_validate_columns_raises_on_missing_ben_in_sheet_b():
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"]})
    df_b = pd.DataFrame({"WRONG": ["T1"], "Part Number": ["P1"]})
    config = Config()
    with pytest.raises(ValueError, match="BEN"):
        validate_columns(df_a, df_b, config)


def test_validate_columns_raises_on_missing_part_number():
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"]})
    df_b = pd.DataFrame({"BEN": ["T1"], "WRONG": ["P1"]})
    config = Config()
    with pytest.raises(ValueError, match="Part Number"):
        validate_columns(df_a, df_b, config)


def test_validate_columns_lists_all_missing_columns():
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"]})
    df_b = pd.DataFrame({"X": ["T1"], "Y": ["P1"]})
    config = Config()
    with pytest.raises(ValueError) as exc_info:
        validate_columns(df_a, df_b, config)
    msg = str(exc_info.value)
    assert "BEN" in msg
    assert "Part Number" in msg


def test_validate_columns_checks_exclude_columns_exist():
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [1]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"]})
    config = Config(exclude_columns=["Qty"])
    with pytest.raises(ValueError, match="Qty"):
        validate_columns(df_a, df_b, config)


def test_find_duplicate_keys_identifies_affected_bens():
    config = Config()
    df = pd.DataFrame({
        "BEN": ["T1", "T1", "T2"],
        "Part Number": ["P1", "P1", "P2"],
        "Qty": [1, 2, 3],
    })
    bad_bens, offending = find_duplicate_keys(df, config, "Sheet A")
    assert "T1" in bad_bens
    assert "T2" not in bad_bens
    assert len(offending) > 0


def test_find_duplicate_keys_returns_empty_when_none():
    config = Config()
    df = pd.DataFrame({
        "BEN": ["T1", "T1", "T2"],
        "Part Number": ["P1", "P2", "P2"],
        "Qty": [1, 2, 3],
    })
    bad_bens, offending = find_duplicate_keys(df, config, "Sheet A")
    assert bad_bens == []
    assert offending == []


def test_find_duplicate_keys_includes_sheet_label_in_offending():
    config = Config()
    df = pd.DataFrame({
        "BEN": ["T1", "T1"],
        "Part Number": ["P1", "P1"],
    })
    bad_bens, offending = find_duplicate_keys(df, config, "rawdata_0312")
    assert offending[0]["sheet"] == "rawdata_0312"
