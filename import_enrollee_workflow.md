# Importing a new avert_enrollee_all_yyyy-mm-dd.csv into Postgres

Start here once the CSV has been downloaded to your temp folder.

## 1. Check whether the schema needs to change

- Open the CSV header and compare it against the current `enrollee` table columns (`\d enrollee` in psql).
- Also check "AVERT Data Dictionary_2026_07_13_en.xlsx" (`enrollee_dd` sheet) for any new `FieldName` rows that weren't there before, and note each new field's `FieldType`.
- If there are new fields, decide: rebuild the whole table (`DROP TABLE` + `CREATE TABLE`, loses existing data) or add just the new columns (`ALTER TABLE enrollee ADD COLUMN ...`, keeps existing data). Adding columns is almost always the safer choice unless you're intentionally reloading everything.

## 2. Update the table schema (only if step 1 found changes)

- For new columns, use the `FieldType` → Postgres type mapping already established:
  - `integer` → `INTEGER`
  - `text_decimal` → `NUMERIC`
  - `date` → `DATE`
  - `datetime` → `TIMESTAMP`
  - `text` → `TEXT`
- Watch for the same traps as before: phone-number-style or zero-padded code fields (like `phonenumber_bf`, `mrc`, `subcounty`, `parish`, `village`) should stay `TEXT` even if the dictionary says `integer`, since leading zeros are meaningful.
- Run the `ALTER TABLE` (or new `CREATE TABLE`) statement in psql.

## 3. Reorder the CSV to match the table's column order

- The CSV's own header is alphabetized and won't match the table order. Reorder it with a quick pandas script (adjust the `cols` list if step 1/2 added new fields):

```python
python reordercsv.py
```

## 4. Connect to the database

- Open a **fresh** Terminal window (don't reuse a psql session that might be stuck mid-command — if the prompt ever shows a dash, e.g. `glavoy-#`, type `;` then `\q` to escape it first).
- Connect directly to the right database in one step:

```bash
psql -h localhost -U glavoy -d r21neg
```

- Confirm you're in the right place — the prompt should read `r21neg=#`, not `glavoy=#`.

## 5. Confirm the table is ready

```
\d enrollee
```

- Check the column list/order matches your reordered CSV.

## 6. Load the data

- Update the column list and file path in `load_enrollee.sql` if the schema changed, then run:

```
\i '/Users/glavoy/temp/load_enrollee.sql'
```

- Watch for the row count psql reports (`COPY <n>`) and sanity-check it against the CSV's row count.

## 7. Spot-check the load

```sql
SELECT count(*) FROM enrollee;
SELECT * FROM enrollee ORDER BY id DESC LIMIT 5;
```

- Confirm the row count matches expectations and the newest rows look correct.
