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


def compute_diff(*args, **kwargs):
    """Stub for Task 5."""
    raise NotImplementedError("compute_diff not yet implemented")


def group_by_ben(*args, **kwargs):
    """Stub for Task 6."""
    raise NotImplementedError("group_by_ben not yet implemented")
