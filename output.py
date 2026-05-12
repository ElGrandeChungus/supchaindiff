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
