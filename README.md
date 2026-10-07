# Importing avert_enrollee_all.csv into Postgres

This folder loads AVERT's `avert_enrollee_all.csv` export into the `enrollee`
table in the local `r21neg` Postgres database.

## Files

- `import_pipeline.py` — the pipeline. Checks the CSV against the table
  schema, reorders columns to match, and loads the data.
- `import_data_to_postgres.sql` — the full `CREATE TABLE enrollee` statement
  (source of truth for column order/types). Only needed when rebuilding the
  table from scratch.
- `load_enrollee.sql` / `reordercsv.py` — the old fully-manual steps, kept for
  reference. You shouldn't need these anymore; use the pipeline instead.
- `venv/` — Python virtualenv with `psycopg2-binary` installed.

## Quick start (the easy way)

1. Drop the new export in this folder as `avert_enrollee_all.csv`
   (overwrite the old one, or pass a path as an argument).
2. Dry-run it first — this checks the schema and writes a reordered CSV, but
   doesn't touch the database:

   ```bash
   venv/bin/python3 import_pipeline.py avert_enrollee_all.csv --dry-run
   ```

   - If it prints `STOP: the CSV has columns the 'enrollee' table doesn't
     have yet`, go to **Schema changes** below before continuing.
   - If it prints `Dry run OK`, you're clear to load.

3. Run it for real:

   ```bash
   venv/bin/python3 import_pipeline.py avert_enrollee_all.csv
   ```

   **Important:** `avert_enrollee_all.csv` is always a full export, not just
   new rows. So a real run always `TRUNCATE`s the `enrollee` table first,
   then loads every row from the CSV — otherwise re-running the pipeline
   would duplicate every enrollee. No confirmation prompt — it truncates
   every time, no exceptions.

   It prints how many rows it loaded and the table's new total row count.
   Sanity-check that total against the CSV's row count (`wc -l` minus 1 for
   the header).

That's it — no psql session, no manual reordering.

## Schema changes (new fields in the CSV)

The pipeline refuses to load if the CSV has a column the table doesn't have,
so you never silently drop data. When that happens:

1. Open "AVERT Data Dictionary_2026_07_13_en.xlsx" (`enrollee_dd` sheet) and
   find the new `FieldName` row(s). Note the `FieldType`.
2. Map `FieldType` → Postgres type:
   - `integer` → `INTEGER`
   - `text_decimal` → `NUMERIC`
   - `date` → `DATE`
   - `datetime` → `TIMESTAMP`
   - `text` → `TEXT`
3. Watch for the known trap: phone-number-style or zero-padded code fields
   (`phonenumber_ug`, `phonenumber_bf`, `mrc`, `subcounty`, `parish`,
   `village`) must stay `TEXT` even if the dictionary says `integer` —
   otherwise leading zeros get silently dropped/corrupted.
4. Add the column(s):

   ```bash
   psql -h localhost -U glavoy -d r21neg -c "ALTER TABLE enrollee ADD COLUMN new_field TEXT;"
   ```

   (Rebuilding the whole table with `import_data_to_postgres.sql` is the
   other option, but that drops existing data — only do this if you actually
   want a clean reload.)
5. Re-run the dry run — it should now say `Dry run OK`.

## Connection settings

The pipeline defaults to `localhost` / database `r21neg` / user `glavoy`
(matching local trust auth, no password needed). Override with env vars if
that ever changes:

```bash
PGHOST=... PGDATABASE=... PGUSER=... PGPASSWORD=... venv/bin/python3 import_pipeline.py
```

## First-time setup (already done, for reference)

```bash
python3 -m venv venv
venv/bin/pip install psycopg2-binary
```
