import re
import logging
from copy import copy as _copy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config import Config

logger = logging.getLogger(__name__)

_PROHIBITED = re.compile(r"[\[\]:*?/\\]")

# Colour fills
FILL_ADDED = PatternFill("solid", fgColor="C6EFCE")
FILL_REMOVED = PatternFill("solid", fgColor="FFC7CE")
FILL_CHANGED_CURRENT = PatternFill("solid", fgColor="FFEB9C")
FILL_CHANGED_PRIOR = PatternFill("solid", fgColor="FCE4D6")
FILL_SEV_HIGH = PatternFill("solid", fgColor="FF0000")
FILL_SEV_MEDIUM = PatternFill("solid", fgColor="FFBF00")
FILL_SEV_LOW_NONE = PatternFill("solid", fgColor="00B050")
FILL_SEV_UNSCORED = PatternFill("solid", fgColor="808080")


def sanitize_ben_for_sheet(ben: str, prefix: str = "DIFF_") -> str:
    """Strip prohibited chars; truncate BEN portion to 26 chars; prepend prefix."""
    clean = _PROHIBITED.sub("", ben)
    max_ben = 31 - len(prefix)  # 26 when prefix="DIFF_"
    return f"{prefix}{clean[:max_ben]}"


def assign_sheet_names(bens: List[str]) -> Dict[str, str]:
    """Return {original_ben: sheet_name} with collision resolution."""
    seen: Dict[str, int] = {}
    result: Dict[str, str] = {}
    for ben in bens:
        base = sanitize_ben_for_sheet(ben)
        if base not in seen:
            seen[base] = 1
            result[ben] = base
        else:
            seen[base] += 1
            n = seen[base]
            suffix = f"_{n}"
            result[ben] = base[: 31 - len(suffix)] + suffix
    return result


def write_diff_index(
    ws,
    groups: Dict[str, Dict[str, Any]],
    severities: Dict[str, Dict[str, Any]],
    sheet_names: Dict[str, str],
    skipped_bens: List[str],
    col_asymmetry: List[str],
    config: Config,
) -> None:
    """Write the DIFF_INDEX sheet to the given worksheet."""
    aliases = ", ".join(config.ben_aliases)
    ben_header = f"BEN (also known as: {aliases})" if aliases else "BEN"

    headers = [
        ben_header, "Sheet Name", "Added", "Removed", "Changed", "Unchanged",
        "Status", "Severity", "LLM Note",
    ]
    for col_i, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_i, value=h)
        cell.font = Font(bold=True)

    row = 2
    for ben, group in groups.items():
        sev_info = severities.get(ben, {"severity": "UNSCORED", "note": ""})
        severity = sev_info.get("severity", "UNSCORED")
        ws.cell(row=row, column=1, value=ben)
        ws.cell(row=row, column=2, value=sheet_names.get(ben, ""))
        ws.cell(row=row, column=3, value=len(group["added"]))
        ws.cell(row=row, column=4, value=len(group["removed"]))
        ws.cell(row=row, column=5, value=len(group["changed_b"]))
        ws.cell(row=row, column=6, value=len(group["unchanged"]))
        ws.cell(row=row, column=7, value="OK")
        sev_cell = ws.cell(row=row, column=8, value=severity)
        sev_cell.fill = _severity_fill(severity)
        ws.cell(row=row, column=9, value=sev_info.get("note", ""))
        row += 1

    for ben in skipped_bens:
        ws.cell(row=row, column=1, value=ben)
        ws.cell(row=row, column=7, value="SKIPPED — DUPLICATE KEYS")
        row += 1

    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{row - 1}"

    if col_asymmetry:
        row += 1
        note = f"Note: Column asymmetry detected — columns present in only one sheet: {', '.join(col_asymmetry)}"
        ws.cell(row=row, column=1, value=note)


def _severity_fill(severity: str) -> PatternFill:
    return {
        "HIGH": FILL_SEV_HIGH,
        "MEDIUM": FILL_SEV_MEDIUM,
        "LOW": FILL_SEV_LOW_NONE,
        "NONE": FILL_SEV_LOW_NONE,
    }.get(severity, FILL_SEV_UNSCORED)
