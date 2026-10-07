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
- `venv/` — local Python virtualenv with `psycopg2-binary` installed.
  Create it on each machine using **First-time setup** below; it is not
  included in the repository.

## Quick start (the easy way)

Run these commands from the project folder. On a new machine, complete
**First-time setup** and **Connection settings** below first. The `r21neg`
database and `enrollee` table must already exist.

1. Drop the new export in this folder as `avert_enrollee_all.csv`
   (overwrite the old one, or pass a path as an argument).
2. Dry-run it first — this checks the schema and writes a reordered CSV, but
   doesn't touch the database:

   macOS / Linux:

   ```bash
   venv/bin/python3 import_pipeline.py avert_enrollee_all.csv --dry-run
   ```

   Windows (PowerShell):

   ```powershell
   .\venv\Scripts\python.exe import_pipeline.py avert_enrollee_all.csv --dry-run
   ```

   - If it prints `STOP: the CSV has columns the 'enrollee' table doesn't
     have yet`, go to **Schema changes** below before continuing.
   - If it prints `Dry run OK`, you're clear to load.

3. Run it for real:

   macOS / Linux:

   ```bash
   venv/bin/python3 import_pipeline.py avert_enrollee_all.csv
   ```

   Windows (PowerShell):

   ```powershell
   .\venv\Scripts\python.exe import_pipeline.py avert_enrollee_all.csv
   ```

   **Important:** `avert_enrollee_all.csv` is always a full export, not just
   new rows. So a real run always `TRUNCATE`s the `enrollee` table first,
   then loads every row from the CSV — otherwise re-running the pipeline
   would duplicate every enrollee. No confirmation prompt — it truncates
   every time, no exceptions.

   It prints how many rows it loaded and the table's new total row count.
   Sanity-check that total against the row count reported by the dry run.

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

The pipeline defaults to `localhost` / database `r21neg` / user `glavoy`.
The existing Mac setup uses local trust authentication, so it needs no
password. Windows may require the password you assigned to the `glavoy`
database role (which is separate from the `postgres` administrator role).
Override the connection settings with environment variables:

macOS / Linux:

```bash
PGHOST=... PGDATABASE=... PGUSER=... PGPASSWORD=... venv/bin/python3 import_pipeline.py
```

Windows (PowerShell; settings apply to the current terminal session):

```powershell
$env:PGHOST = 'localhost'
$env:PGDATABASE = 'r21neg'
$env:PGUSER = 'glavoy'
$credential = Get-Credential -UserName 'glavoy' -Message 'Enter the PostgreSQL password for glavoy'
$env:PGPASSWORD = $credential.GetNetworkCredential().Password
.\venv\Scripts\python.exe import_pipeline.py avert_enrollee_all.csv --dry-run
```

After importing, clear the password from the session:

```powershell
Remove-Item Env:PGPASSWORD
Remove-Variable credential
```

## First-time setup

Run these commands from the project folder. Python must be installed.
The virtual environment does not need to be activated because the commands
invoke its Python executable directly.

macOS / Linux:

```bash
python3 -m venv venv
venv/bin/pip install psycopg2-binary
```

Windows (PowerShell):

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install psycopg2-binary
```

If `py` is unavailable but `python` works, use `python -m venv venv` instead.
