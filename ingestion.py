import logging
from typing import List, Tuple, Dict, Any

import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


def load_sheet(filepath: str, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(filepath, sheet_name=sheet_name, engine="openpyxl")


def validate_columns(df_a: pd.DataFrame, df_b: pd.DataFrame, config: Config) -> None:
    required = set([config.ben_column, config.part_number_column] + config.exclude_columns)
    missing_a = required - set(df_a.columns)
    missing_b = required - set(df_b.columns)
    if missing_a or missing_b:
        parts = []
        if missing_a:
            parts.append(f"Sheet A missing: {sorted(missing_a)}")
        if missing_b:
            parts.append(f"Sheet B missing: {sorted(missing_b)}")
        raise ValueError(f"Column validation failed. {'; '.join(parts)}")


def find_duplicate_keys(
    df: pd.DataFrame, config: Config, sheet_label: str
) -> Tuple[List[str], List[Dict[str, Any]]]:
    keys = config.composite_key_columns
    dup_mask = df.duplicated(subset=keys, keep=False)
    duplicates = df[dup_mask]
    if duplicates.empty:
        return [], []
    bad_bens: List[str] = duplicates[config.ben_column].unique().tolist()
    offending_rows = (
        duplicates[keys]
        .drop_duplicates()
        .assign(sheet=sheet_label)
        .to_dict("records")
    )
    logger.warning(
        "Duplicate composite keys in %s — affected BENs: %s", sheet_label, bad_bens
    )
    return bad_bens, offending_rows


def prepare_sheets(
    filepath: str, sheet_a: str, sheet_b: str, config: Config
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str], List[Dict[str, Any]]]:
    """Load, validate, drop excluded columns, detect and exclude duplicate-key BEN groups.

    Returns:
        df_a, df_b: cleaned DataFrames with excluded columns dropped and dup-BEN rows removed
        skipped_bens: list of BEN values excluded due to duplicate keys
        dup_warnings: list of offending-row dicts for display
    """
    df_a = load_sheet(filepath, sheet_a)
    df_b = load_sheet(filepath, sheet_b)

    validate_columns(df_a, df_b, config)

    if config.exclude_columns:
        df_a = df_a.drop(columns=config.exclude_columns)
        df_b = df_b.drop(columns=config.exclude_columns)

    bad_a, warn_a = find_duplicate_keys(df_a, config, sheet_a)
    bad_b, warn_b = find_duplicate_keys(df_b, config, sheet_b)
    skipped_bens = sorted(set(bad_a) | set(bad_b))
    dup_warnings = warn_a + warn_b

    if skipped_bens:
        df_a = df_a[~df_a[config.ben_column].isin(skipped_bens)].reset_index(drop=True)
        df_b = df_b[~df_b[config.ben_column].isin(skipped_bens)].reset_index(drop=True)

    return df_a, df_b, skipped_bens, dup_warnings
