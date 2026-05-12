import math
import numpy as np
import pandas as pd
import pytest
from config import Config
from diff import align_columns, compute_diff, group_by_ben


# --- align_columns tests ---

def test_align_columns_no_change_when_identical():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    aligned_a, aligned_b, asymmetric = align_columns(df_a, df_b, config)
    assert list(aligned_a.columns) == list(aligned_b.columns)
    assert asymmetric == []


def test_align_columns_adds_missing_col_to_a_with_nan():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Weight": [1.5]})
    aligned_a, aligned_b, asymmetric = align_columns(df_a, df_b, config)
    assert "Weight" in aligned_a.columns
    assert "Qty" in aligned_b.columns
    assert math.isnan(aligned_a["Weight"].iloc[0])
    assert math.isnan(aligned_b["Qty"].iloc[0])


def test_align_columns_reports_asymmetric_columns():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Weight": [1.5]})
    _, _, asymmetric = align_columns(df_a, df_b, config)
    assert set(asymmetric) == {"Qty", "Weight"}


def test_align_columns_preserves_key_columns():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Weight": [1.5]})
    aligned_a, aligned_b, _ = align_columns(df_a, df_b, config)
    assert "BEN" in aligned_a.columns
    assert "Part Number" in aligned_a.columns
    assert "BEN" in aligned_b.columns
    assert "Part Number" in aligned_b.columns


# --- compute_diff tests ---

def test_added_row():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"BEN": ["T1", "T1"], "Part Number": ["P1", "P2"], "Qty": [5, 10]})
    result = compute_diff(df_a, df_b, config)
    assert len(result["added"]) == 1
    assert result["added"].iloc[0]["Part Number"] == "P2"
    assert len(result["removed"]) == 0
    assert len(result["changed_b"]) == 0
    assert len(result["unchanged"]) == 1


def test_removed_row():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1", "T1"], "Part Number": ["P1", "P2"], "Qty": [5, 10]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    result = compute_diff(df_a, df_b, config)
    assert len(result["removed"]) == 1
    assert result["removed"].iloc[0]["Part Number"] == "P2"
    assert len(result["added"]) == 0


def test_changed_row():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [10]})
    result = compute_diff(df_a, df_b, config)
    assert len(result["changed_b"]) == 1
    assert len(result["changed_a"]) == 1
    assert len(result["unchanged"]) == 0
    assert len(result["field_diffs"]) == 1
    fd = result["field_diffs"][0]
    assert fd["field"] == "Qty"
    assert fd["old"] == 5
    assert fd["new"] == 10
    assert fd["ben"] == "T1"
    assert fd["part"] == "P1"


def test_unchanged_row():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    result = compute_diff(df_a, df_b, config)
    assert len(result["unchanged"]) == 1
    assert len(result["changed_b"]) == 0
    assert result["field_diffs"] == []


def test_nan_nan_is_unchanged():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [float("nan")]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [float("nan")]})
    result = compute_diff(df_a, df_b, config)
    assert len(result["unchanged"]) == 1
    assert len(result["changed_b"]) == 0


def test_nan_vs_value_is_changed():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [float("nan")]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [5]})
    result = compute_diff(df_a, df_b, config)
    assert len(result["changed_b"]) == 1
    fd = result["field_diffs"][0]
    assert fd["old"] is None
    assert fd["new"] == 5


def test_field_diff_old_nan_serializes_as_none():
    config = Config()
    df_a = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [float("nan")]})
    df_b = pd.DataFrame({"BEN": ["T1"], "Part Number": ["P1"], "Qty": [99]})
    result = compute_diff(df_a, df_b, config)
    assert result["field_diffs"][0]["old"] is None


def test_changed_a_and_changed_b_are_row_aligned():
    config = Config()
    df_a = pd.DataFrame({
        "BEN": ["T1", "T1"],
        "Part Number": ["P1", "P2"],
        "Qty": [5, 20],
    })
    df_b = pd.DataFrame({
        "BEN": ["T1", "T1"],
        "Part Number": ["P1", "P2"],
        "Qty": [10, 20],
    })
    result = compute_diff(df_a, df_b, config)
    assert len(result["changed_b"]) == 1
    assert len(result["changed_a"]) == 1
    assert result["changed_b"].iloc[0]["Qty"] == 10
    assert result["changed_a"].iloc[0]["Qty"] == 5


def test_compute_diff_uses_configured_column_names():
    config = Config(ben_column="Tool", part_number_column="PN")
    df_a = pd.DataFrame({"Tool": ["T1"], "PN": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"Tool": ["T1"], "PN": ["P1"], "Qty": [10]})
    result = compute_diff(df_a, df_b, config)
    fd = result["field_diffs"][0]
    assert fd["ben"] == "T1"
    assert fd["part"] == "P1"


# --- group_by_ben tests ---

def test_group_by_ben_splits_by_ben_value():
    config = Config()
    diff_result = {
        "added": pd.DataFrame({"BEN": ["T1", "T2"], "Part Number": ["P1", "P2"], "Qty": [1, 2]}),
        "removed": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "changed_b": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "changed_a": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "unchanged": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "field_diffs": [],
    }
    groups = group_by_ben(diff_result, config, tool_order=[])
    assert set(groups.keys()) == {"T1", "T2"}
    assert len(groups["T1"]["added"]) == 1
    assert len(groups["T2"]["added"]) == 1


def test_group_by_ben_respects_tool_order():
    config = Config()
    diff_result = {
        "added": pd.DataFrame({"BEN": ["T3", "T1", "T2"], "Part Number": ["P1", "P2", "P3"], "Qty": [1, 2, 3]}),
        "removed": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "changed_b": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "changed_a": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "unchanged": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "field_diffs": [],
    }
    groups = group_by_ben(diff_result, config, tool_order=["T2", "T3"])
    keys = list(groups.keys())
    assert keys[0] == "T2"
    assert keys[1] == "T3"
    assert keys[2] == "T1"


def test_group_by_ben_falls_back_to_alphabetical():
    config = Config()
    diff_result = {
        "added": pd.DataFrame({"BEN": ["ZEBRA", "ALPHA"], "Part Number": ["P1", "P2"], "Qty": [1, 2]}),
        "removed": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "changed_b": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "changed_a": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "unchanged": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "field_diffs": [],
    }
    groups = group_by_ben(diff_result, config, tool_order=[])
    keys = list(groups.keys())
    assert keys[0] == "ALPHA"
    assert keys[1] == "ZEBRA"


def test_group_by_ben_changed_a_and_b_remain_row_aligned():
    config = Config()
    diff_result = {
        "added": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "removed": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "changed_b": pd.DataFrame({"BEN": ["T1", "T1"], "Part Number": ["P1", "P2"], "Qty": [10, 20]}),
        "changed_a": pd.DataFrame({"BEN": ["T1", "T1"], "Part Number": ["P1", "P2"], "Qty": [5, 15]}),
        "unchanged": pd.DataFrame(columns=["BEN", "Part Number", "Qty"]),
        "field_diffs": [
            {"ben": "T1", "part": "P1", "field": "Qty", "old": 5, "new": 10},
            {"ben": "T1", "part": "P2", "field": "Qty", "old": 15, "new": 20},
        ],
    }
    groups = group_by_ben(diff_result, config, tool_order=[])
    t1 = groups["T1"]
    assert len(t1["changed_b"]) == 2
    assert len(t1["changed_a"]) == 2
    assert t1["changed_b"].iloc[0]["Qty"] == 10
    assert t1["changed_a"].iloc[0]["Qty"] == 5
