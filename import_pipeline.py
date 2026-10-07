#!/usr/bin/env python3
"""Pipeline to import an avert_enrollee_all.csv export into the Postgres 'enrollee' table.

The CSV is a full export every time (not just new rows), so a real run
TRUNCATEs the table before loading — otherwise every enrollee would be
duplicated on each import.

What it does:
  1. Reads the CSV header and compares it against the enrollee table's columns
     (via information_schema) to catch schema drift before loading anything.
  2. Reorders the CSV columns in memory to match the table's column order.
  3. TRUNCATEs the table and streams the reordered data into Postgres with
     COPY, all in one transaction (so a failed load leaves the old data
     intact rather than leaving the table empty).

What it deliberately does NOT do:
  - Decide Postgres types for brand-new fields, or run ALTER TABLE/CREATE TABLE.
    If the CSV has columns the table doesn't know about yet, the script stops
    and tells you to update the schema first (see README.md step 1).

Usage:
    venv/bin/python3 import_pipeline.py [path/to/avert_enrollee_all.csv] [--dry-run]

--dry-run checks the schema and reorders the CSV (written to
avert_enrollee_reordered.csv) without touching the database.

Connection is read from standard PG* env vars, with these defaults:
    PGHOST=localhost  PGDATABASE=r21neg  PGUSER=glavoy  PGPASSWORD=(unset, uses trust/.pgpass)
"""
import csv
import io
import os
import sys

import psycopg2

TABLE = "enrollee"
SURROGATE_COLS = {"id", "created_at"}


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        dbname=os.environ.get("PGDATABASE", "r21neg"),
        user=os.environ.get("PGUSER", "glavoy"),
        password=os.environ.get("PGPASSWORD", ""),
    )


def get_table_columns(cur):
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (TABLE,),
    )
    return [r[0] for r in cur.fetchall()]


def build_reordered_csv(csv_path, load_cols):
    """Returns (StringIO of reordered CSV, row count)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(load_cols)
    n = 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            writer.writerow([row[c] for c in load_cols])
            n += 1
    buf.seek(0)
    return buf, n


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    positional = [a for a in args if a != "--dry-run"]
    csv_path = positional[0] if positional else "avert_enrollee_all.csv"

    if not os.path.exists(csv_path):
        sys.exit(f"CSV not found: {csv_path}")

    with open(csv_path, newline="") as f:
        header = next(csv.reader(f))

    conn = get_conn()
    cur = conn.cursor()
    table_cols = [c for c in get_table_columns(cur) if c not in SURROGATE_COLS]

    csv_set = set(header)
    table_set = set(table_cols)

    new_in_csv = [c for c in header if c not in table_set]
    missing_from_csv = [c for c in table_cols if c not in csv_set]

    if new_in_csv:
        print("STOP: the CSV has columns the 'enrollee' table doesn't have yet:")
        for c in new_in_csv:
            print(f"  - {c}")
        print(
            "\nUpdate the schema first (check the AVERT Data Dictionary for the "
            "FieldType, then ALTER TABLE ... ADD COLUMN ...). See README.md step 1."
        )
        cur.close()
        conn.close()
        sys.exit(1)

    if missing_from_csv:
        print("Note: these table columns aren't in the CSV and will load as NULL:")
        for c in missing_from_csv:
            print(f"  - {c}")

    load_cols = [c for c in table_cols if c in csv_set]
    buf, n = build_reordered_csv(csv_path, load_cols)

    if dry_run:
        reordered_path = "avert_enrollee_reordered.csv"
        with open(reordered_path, "w", newline="") as out:
            out.write(buf.getvalue())
        print(f"Dry run OK: schema matches, {n} rows reordered.")
        print(f"Reordered CSV written to {reordered_path} (not loaded).")
        cur.close()
        conn.close()
        return

    col_list = ",".join(load_cols)
    cur.execute(f"TRUNCATE TABLE {TABLE}")
    copy_sql = f"COPY {TABLE}({col_list}) FROM STDIN WITH (FORMAT csv, HEADER true)"
    cur.copy_expert(copy_sql, buf)
    conn.commit()

    cur.execute(f"SELECT count(*) FROM {TABLE}")
    total = cur.fetchone()[0]
    print(f"Truncated and loaded {n} rows from {csv_path}.")
    print(f"Table '{TABLE}' now has {total} rows total.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
