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
