# Database folder

| File | Purpose | Commit to GitHub? |
|---|---|---|
| `source/DBMS_Database.xlsx` | **Your original dataset (never modified by any script).** 91,320 rows, 22 columns, 10 cities, 2000-01-01 → 2024-12-31. | Yes (≈14 MB, under GitHub's 100 MB limit) — if your college allows sharing the data. If not, leave it out; the project then cannot be reproduced without it. |
| `city_metadata.csv` | State, latitude/longitude and coastal flag for each city (the Excel file has no coordinates). | Yes |
| `heatverse.db` | SQLite database **generated** from the Excel file by `backend/scripts/import_excel.py`. Also holds the app tables (users, predictions…). | **No** — it is git-ignored. It contains user accounts after you use the app. Anyone can regenerate it. |

## Create the database

From the `backend` folder with the virtual environment active:

```powershell
python scripts\import_excel.py --excel ..\database\source\DBMS_Database.xlsx
```

The script validates the column names, refuses to continue if it finds duplicate (city, date) rows, inserts every row,
checks that the database row count equals the Excel row count, and records the import in the `import_log` table.
To rebuild the weather tables later add `--replace` (user accounts and predictions are kept).

See `docs/database-schema.md` for tables, keys, indexes and column mapping.
