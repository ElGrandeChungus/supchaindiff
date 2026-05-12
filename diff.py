import logging
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


def align_columns(
    df_a: pd.DataFrame, df_b: pd.DataFrame, config: Config
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """Return (aligned_a, aligned_b, asymmetric_cols).

    Both returned DataFrames have the same column set (union).
    asymmetric_cols lists columns present in only one sheet.
    """
    keys = config.composite_key_columns
    non_key_a = [c for c in df_a.columns if c not in keys]
    non_key_b = [c for c in df_b.columns if c not in keys]

    # Union preserving Sheet A order, then Sheet B extras
    seen: Dict[str, None] = {}
    for c in non_key_a:
        seen[c] = None
    for c in non_key_b:
        seen[c] = None
    all_non_key = list(seen)

    only_in_a = [c for c in non_key_a if c not in set(non_key_b)]
    only_in_b = [c for c in non_key_b if c not in set(non_key_a)]
    asymmetric = only_in_a + only_in_b

    out_a = df_a.copy()
    out_b = df_b.copy()
    for col in all_non_key:
        if col not in out_a.columns:
            out_a[col] = np.nan
        if col not in out_b.columns:
            out_b[col] = np.nan

    return out_a[keys + all_non_key], out_b[keys + all_non_key], asymmetric


def _nan_equal(a: Any, b: Any) -> bool:
    """NaN == NaN → True. NaN vs value → False. Otherwise standard equality."""
    try:
        a_nan = bool(pd.isna(a))
    except (TypeError, ValueError):
        a_nan = False
    try:
        b_nan = bool(pd.isna(b))
    except (TypeError, ValueError):
        b_nan = False
    if a_nan and b_nan:
        return True
    if a_nan != b_nan:
        return False
    return bool(a == b)


def compute_diff(df_a: pd.DataFrame, df_b: pd.DataFrame, config: Config) -> Dict[str, Any]:
    """Classify all rows as added/removed/changed/unchanged.

    Returns dict with keys:
        added (DataFrame): rows in Sheet B only
        removed (DataFrame): rows in Sheet A only
        changed_b (DataFrame): current values for changed rows (Sheet B)
        changed_a (DataFrame): prior values for changed rows (Sheet A), row-aligned with changed_b
        unchanged (DataFrame): Sheet B rows where nothing changed
        field_diffs (list[dict]): {ben, part, field, old, new} for every changed field
    """
    keys = config.composite_key_columns

    # Classify using merge indicator
    key_only_a = df_a[keys].copy()
    key_only_a["__in_a"] = True
    key_only_b = df_b[keys].copy()
    key_only_b["__in_b"] = True
    key_merge = key_only_a.merge(key_only_b, on=keys, how="outer")

    added_keys = key_merge.loc[key_merge["__in_a"].isna(), keys]
    removed_keys = key_merge.loc[key_merge["__in_b"].isna(), keys]
    common_keys = key_merge.loc[
        key_merge["__in_a"].notna() & key_merge["__in_b"].notna(), keys
    ].reset_index(drop=True)

    added = df_b.merge(added_keys, on=keys).reset_index(drop=True)
    removed = df_a.merge(removed_keys, on=keys).reset_index(drop=True)

    common_a = (
        df_a.merge(common_keys, on=keys).sort_values(keys).reset_index(drop=True)
    )
    common_b = (
        df_b.merge(common_keys, on=keys).sort_values(keys).reset_index(drop=True)
    )

    non_key = [c for c in common_b.columns if c not in keys]

    changed_indices: List[int] = []
    all_field_diffs: List[Dict[str, Any]] = []

    for i in range(len(common_b)):
        row_field_diffs: List[Dict[str, Any]] = []
        for col in non_key:
            val_a = common_a.at[i, col] if col in common_a.columns else np.nan
            val_b = common_b.at[i, col]
            if not _nan_equal(val_a, val_b):
                row_field_diffs.append(
                    {
                        "ben": str(common_b.at[i, config.ben_column]),
                        "part": str(common_b.at[i, config.part_number_column]),
                        "field": col,
                        "old": None if (isinstance(val_a, float) and pd.isna(val_a)) else val_a,
                        "new": None if (isinstance(val_b, float) and pd.isna(val_b)) else val_b,
                    }
                )
        if row_field_diffs:
            changed_indices.append(i)
            all_field_diffs.extend(row_field_diffs)

    unchanged_indices = [i for i in range(len(common_b)) if i not in set(changed_indices)]

    return {
        "added": added,
        "removed": removed,
        "changed_b": common_b.iloc[changed_indices].reset_index(drop=True),
        "changed_a": common_a.iloc[changed_indices].reset_index(drop=True),
        "unchanged": common_b.iloc[unchanged_indices].reset_index(drop=True),
        "field_diffs": all_field_diffs,
    }


def group_by_ben(*args, **kwargs):
    """Stub for Task 6."""
    raise NotImplementedError("group_by_ben not yet implemented")
