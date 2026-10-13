from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REAL_DB = ROOT / "database" / "heatverse.db"

needs_data = pytest.mark.skipif(not REAL_DB.exists(), reason="database/heatverse.db not found - run scripts/import_excel.py first")
