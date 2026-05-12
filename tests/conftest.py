import pandas as pd
import pytest
from config import Config


@pytest.fixture
def basic_config():
    return Config()


@pytest.fixture
def df_a():
    return pd.DataFrame({
        "BEN": ["T1", "T1", "T2"],
        "Part Number": ["P1", "P2", "P3"],
        "Qty": [10, 20, 30],
        "Ship Date": ["2025-01-01", "2025-02-01", "2025-03-01"],
    })


@pytest.fixture
def df_b():
    return pd.DataFrame({
        "BEN": ["T1", "T1", "T2", "T2"],
        "Part Number": ["P1", "P2", "P4", "P5"],
        "Qty": [15, 20, 40, 50],
        "Ship Date": ["2025-01-15", "2025-02-01", "2025-04-01", "2025-05-01"],
    })
