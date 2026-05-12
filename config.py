from dataclasses import dataclass, field
from typing import List
import yaml


@dataclass
class Config:
    ben_column: str = "BEN"
    part_number_column: str = "Part Number"
    ben_aliases: List[str] = field(default_factory=lambda: ["P1A", "FCID"])
    exclude_columns: List[str] = field(default_factory=list)
    tool_order: List[str] = field(default_factory=list)
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = ""
    llm_api_key: str = "none"
    llm_timeout_seconds: int = 30
    llm_enabled: bool = True

    @property
    def composite_key_columns(self) -> List[str]:
        return [self.part_number_column, self.ben_column]


_KNOWN_KEYS = {f.name for f in Config.__dataclass_fields__.values()}  # type: ignore[attr-defined]


def load_config(path: str = "config.yaml") -> Config:
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}
    data.pop("composite_key_columns", None)
    filtered = {k: v for k, v in data.items() if k in _KNOWN_KEYS}
    return Config(**filtered)
