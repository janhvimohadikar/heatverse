"""
Import the supplied Excel workbook into the HEATVERSE SQLite database.

What this script does
---------------------
1. Reads the workbook (the original file is opened read-only and NEVER modified).
2. Validates that every expected column exists and that there are no duplicate (city, date) pairs.
3. Creates the historical tables `city`, `weather_observation` and `import_log`.
4. Inserts EVERY row (nothing is silently dropped or altered; only column names are made SQL-friendly).
5. Verifies that the number of rows in the database equals the number of rows in the Excel file.

Usage (from the backend folder, with the virtual environment active):
    python scripts/import_excel.py --excel ../database/source/DBMS_Database.xlsx
    python scripts/import_excel.py --excel path/to/file.xlsx --db ../database/heatverse.db --replace
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "1.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "database" / "heatverse.db"
CITY_CSV = PROJECT_ROOT / "database" / "city_metadata.csv"

# Excel header -> database column.  Units are those stated in the Excel headers;
# where the header has no unit (ppt_sum, rain_sum, wind_*), the unit follows the
# Open-Meteo convention (mm and km/h) -- this is documented in docs/database-schema.md.
COLUMN_MAP = {
    "temp_2m_max(°C)": "temp_max_c",
    "temp_2m_min(°C)": "temp_min_c",
    "apparent_temp_max(°C)": "apparent_max_c",
    "apparent_temp_min(°C)": "apparent_min_c",
    "ppt_sum": "precipitation_sum_mm",
    "rain_sum": "rain_sum_mm",
    "weather_code": "weather_code",
    "wind_speed_10m_max": "wind_speed_max_kmh",
    "wind_gusts_10m_max": "wind_gusts_max_kmh",
    "wind_direction_10m_dominant": "wind_direction_deg",
    "temp_2m_mean (°C)": "temp_mean_c",
    "apparent_temp_mean (°C)": "apparent_mean_c",
    "sunrise (iso8601)": "sunrise",
    "sunset (iso8601)": "sunset",
    "daylight_duration (s)": "daylight_duration_s",
    "sunshine_duration (s)": "sunshine_duration_s",
    "et0_fao_evapotranspiration (mm)": "et0_evapotranspiration_mm",
    "soil_moisture_0_to_7cm_mean (m³/m³)": "soil_moisture_m3m3",
    "soil_temperature_0_to_7cm_mean (°C)": "soil_temp_c",
    "precipitation_hours (h)": "precipitation_hours_h",
}
REQUIRED_COLUMNS = ["city", "date"] + list(COLUMN_MAP.keys())
DB_COLUMNS = list(COLUMN_MAP.values())

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS city (
    city_id      INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    state        TEXT,
    latitude     REAL,
    longitude    REAL,
    is_coastal   INTEGER NOT NULL DEFAULT 0 CHECK (is_coastal IN (0, 1)),
    coord_source TEXT
);

CREATE TABLE IF NOT EXISTS weather_observation (
    observation_id            INTEGER PRIMARY KEY,
    city_id                   INTEGER NOT NULL REFERENCES city(city_id),
    obs_date                  TEXT    NOT NULL,          -- ISO date YYYY-MM-DD
    temp_max_c                REAL,
    temp_min_c                REAL,
    apparent_max_c            REAL,
    apparent_min_c            REAL,
    precipitation_sum_mm      REAL,
    rain_sum_mm               REAL,
    weather_code              INTEGER,
    wind_speed_max_kmh        REAL,
    wind_gusts_max_kmh        REAL,
    wind_direction_deg        INTEGER,
    temp_mean_c               REAL,
    apparent_mean_c           REAL,
    sunrise                   TEXT,                      -- ISO datetime
    sunset                    TEXT,
    daylight_duration_s       REAL,
    sunshine_duration_s       REAL,
    et0_evapotranspiration_mm REAL,
    soil_moisture_m3m3        REAL,
    soil_temp_c               REAL,
    precipitation_hours_h     INTEGER,
    UNIQUE (city_id, obs_date)
);
CREATE INDEX IF NOT EXISTS idx_obs_date ON weather_observation (obs_date, city_id);

CREATE TABLE IF NOT EXISTS import_log (
    import_id        INTEGER PRIMARY KEY,
    source_file      TEXT NOT NULL,
    source_sha256    TEXT NOT NULL,
    rows_read        INTEGER NOT NULL,
    rows_inserted    INTEGER NOT NULL,
    cities           INTEGER NOT NULL,
    date_min         TEXT,
    date_max         TEXT,
    script_version   TEXT NOT NULL,
    imported_at_utc  TEXT NOT NULL
);
"""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_city_metadata() -> dict[str, dict]:
    if not CITY_CSV.exists():
        return {}
    with open(CITY_CSV, newline="", encoding="utf-8") as f:
        return {row["city"].strip(): row for row in csv.DictReader(f)}


def import_workbook(excel_path: Path, db_path: Path, replace: bool = False) -> dict:
    import pandas as pd  # imported here so the module can be inspected without pandas

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    print(f"Reading {excel_path} (read-only) ... this can take a minute.")
    df = pd.read_excel(excel_path)
    rows_read = len(df)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "The workbook does not have the expected columns.\n"
            f"Missing: {missing}\nFound:   {list(df.columns)}"
        )

    df["city"] = df["city"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"])

    dups = int(df.duplicated(["city", "date"]).sum())
    if dups:
        raise ValueError(f"{dups} duplicate (city, date) rows found. Refusing to drop data silently; please review the file.")

    if db_path.exists():
        if not replace:
            raise FileExistsError(f"{db_path} already exists. Use --replace to rebuild the historical tables.")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    existed_before = db_path.exists()
    # isolation_level=None -> we control transactions explicitly (BEGIN/COMMIT/ROLLBACK)
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        if replace:
            # Only the three historical tables are rebuilt; application tables (users, predictions...) are untouched.
            conn.execute("DROP TABLE IF EXISTS weather_observation")
            conn.execute("DROP TABLE IF EXISTS import_log")
            # city may be referenced by application tables, so update rather than drop it.
        conn.executescript(SCHEMA_SQL)

        meta = load_city_metadata()
        cities = sorted(df["city"].unique())
        city_ids: dict[str, int] = {}
        for name in cities:
            m = meta.get(name, {})
            conn.execute(
                """INSERT INTO city (name, state, latitude, longitude, is_coastal, coord_source)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET state=excluded.state, latitude=excluded.latitude,
                   longitude=excluded.longitude, is_coastal=excluded.is_coastal, coord_source=excluded.coord_source""",
                (
                    name,
                    m.get("state") or None,
                    float(m["latitude"]) if m.get("latitude") else None,
                    float(m["longitude"]) if m.get("longitude") else None,
                    int(m.get("is_coastal", 0) or 0),
                    m.get("coord_source") or None,
                ),
            )
            if not m:
                print(f"WARNING: no coordinates for '{name}' in city_metadata.csv; it will not appear on the map.")
        for cid, name in conn.execute("SELECT city_id, name FROM city"):
            city_ids[name] = cid

        out = df[["city", "date"] + list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)
        out["obs_date"] = out["date"].dt.strftime("%Y-%m-%d")
        out["city_id"] = out["city"].map(city_ids)
        for c in ("sunrise", "sunset"):
            out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%dT%H:%M:%S")

        insert_cols = ["city_id", "obs_date"] + DB_COLUMNS
        records = out[insert_cols].astype(object).where(out[insert_cols].notna(), None).values.tolist()
        placeholders = ",".join("?" * len(insert_cols))
        conn.execute("BEGIN")
        conn.executemany(
            f"INSERT INTO weather_observation ({','.join(insert_cols)}) VALUES ({placeholders})", records
        )

        rows_inserted = conn.execute("SELECT COUNT(*) FROM weather_observation").fetchone()[0]
        if rows_inserted != rows_read:
            conn.execute("ROLLBACK")
            raise RuntimeError(f"Row count mismatch: Excel has {rows_read}, database has {rows_inserted}. Import rolled back.")

        date_min, date_max = conn.execute("SELECT MIN(obs_date), MAX(obs_date) FROM weather_observation").fetchone()
        conn.execute(
            """INSERT INTO import_log (source_file, source_sha256, rows_read, rows_inserted, cities, date_min, date_max,
                                       script_version, imported_at_utc) VALUES (?,?,?,?,?,?,?,?,?)""",
            (excel_path.name, sha256_of(excel_path), rows_read, rows_inserted, len(cities), date_min, date_max,
             SCRIPT_VERSION, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        conn.close()
        if not existed_before and db_path.exists():
            db_path.unlink()  # do not leave a half-built database behind
        raise
    finally:
        conn.close()
    return {"rows_read": rows_read, "rows_inserted": rows_inserted, "cities": len(cities),
            "date_min": date_min, "date_max": date_max}


def main() -> int:
    p = argparse.ArgumentParser(description="Import the HEATVERSE Excel workbook into SQLite.")
    p.add_argument("--excel", required=True, type=Path, help="Path to the .xlsx file")
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"SQLite file to create (default: {DEFAULT_DB})")
    p.add_argument("--replace", action="store_true", help="Rebuild historical tables if the database already exists")
    a = p.parse_args()
    try:
        result = import_workbook(a.excel, a.db, a.replace)
    except Exception as exc:  # show a friendly message to beginners
        print(f"\nIMPORT FAILED: {exc}", file=sys.stderr)
        return 1
    print("\nImport complete and verified:")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"\nDatabase written to: {a.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
