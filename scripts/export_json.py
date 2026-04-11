#!/usr/bin/env python3
"""Export pricelist.xlsx → pricelist.json (one-way, manual).

Reads pricelist.xlsx at the project root, validates against the 14-field
blueprint schema, and overwrites pricelist.json. Never reads or writes
any per-product files (products/**/knowledge.md, metadata.json, prices.json
are all out of scope for this script).

Run:
    python3 scripts/export_json.py
    python3 scripts/export_json.py --dry-run    # show what would change, don't write
"""
import json
import sys
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / 'pricelist.xlsx'
OUT = ROOT / 'pricelist.json'

# Blueprint schema — 15 fields, fixed order (v6.1: dropped product_line, added raynet_*)
#
# PRICING CONVENTION:
# `standard_price` and `price_formula` are read together by consumers.
# `standard_price = 1` is a MAGIC PLACEHOLDER, not a real 1 CZK price.
#
#   standard_price | price_formula | meaning
#   --------------|---------------|----------------------------------------
#   <number != 1> | null          | fixed price — use as-is
#   1             | "matrix"      | matrix — look up in products/<cat>/<sku>/prices.json
#   1             | "<text>"      | formula — apply rule (e.g. "4% from price")
#   1             | null          | placeholder — price not yet defined
#   null          | null          | no price
#
# This script preserves both fields verbatim — it does NOT compute or normalize them.
# See BLUEPRINT.md → "Pricing convention" for details.
FIELDS = [
    ('sku',                 'text',  True),   # required
    ('category',            'enum',  True),   # required
    ('name',                'text',  True),   # required
    ('description',         'text',  False),
    ('standard_price',      'mixed', False),  # number | "matrix" | null
    ('price_formula',       'text',  False),
    ('currency',            'text',  True),   # required
    ('unit',                'text',  True),   # required
    ('cost',                'num',   False),
    ('cost_percent',        'num',   False),
    ('discount',            'text',  False),
    ('delivery_weeks',      'text',  False),
    ('color_summary',       'text',  False),
    ('raynet_description',  'text',  False),  # HTML for Raynet sync
    ('raynet_cost',         'num',   False),
]

ALLOWED_CATEGORIES = {'pergola', 'vypln', 'prislusenstvi', 'sluzba'}

def parse_args():
    return '--dry-run' in sys.argv[1:]

def normalize_value(raw, kind):
    if raw is None:
        return None
    if kind == 'num':
        if isinstance(raw, (int, float)):
            return raw
        try:
            s = str(raw).strip()
            if s == '':
                return None
            n = float(s)
            return int(n) if n.is_integer() else n
        except ValueError:
            return None
    if kind == 'mixed':
        if isinstance(raw, (int, float)):
            return raw
        s = str(raw).strip()
        if s == '':
            return None
        if s.lower() == 'matrix':
            return 'matrix'
        try:
            n = float(s)
            return int(n) if n.is_integer() else n
        except ValueError:
            return s  # keep as string (edge case)
    # text / enum
    s = '' if raw is None else str(raw).strip()
    return s if s != '' else None

def read_xlsx():
    if not XLSX.exists():
        raise SystemExit(f'{XLSX} not found. Run scripts/init_xlsx.py first.')
    wb = load_workbook(XLSX, data_only=True)
    ws = wb.active

    # Header row expected at row 1
    header = [str(c.value).strip() if c.value else None for c in ws[1]]
    header_map = {}
    for i, name in enumerate(header):
        if name:
            header_map[name] = i

    missing_headers = [f for f, _, _ in FIELDS if f not in header_map]
    if missing_headers:
        raise SystemExit(f'Missing columns in xlsx header: {missing_headers}')

    items = []
    errors = []
    seen_skus = set()

    for r_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if all(v is None or str(v).strip() == '' for v in row):
            continue  # skip blank rows

        entry = {}
        row_errors = []
        for field, kind, required in FIELDS:
            raw = row[header_map[field]] if header_map[field] < len(row) else None
            val = normalize_value(raw, kind)
            entry[field] = val
            if required and val in (None, ''):
                row_errors.append(f'row {r_idx}: {field} is required')

        sku = entry.get('sku')
        if sku:
            if sku in seen_skus:
                row_errors.append(f'row {r_idx}: duplicate sku "{sku}"')
            seen_skus.add(sku)

        cat = entry.get('category')
        if cat and cat not in ALLOWED_CATEGORIES:
            row_errors.append(f'row {r_idx}: category "{cat}" not in {sorted(ALLOWED_CATEGORIES)}')

        errors.extend(row_errors)
        items.append(entry)

    return items, errors

def main():
    dry = parse_args()
    items, errors = read_xlsx()

    if errors:
        print('ERRORS:')
        for e in errors:
            print(f'  {e}')
        sys.exit(1)

    # Compare to existing pricelist.json if present
    old = []
    if OUT.exists():
        old = json.loads(OUT.read_text())

    new_json = json.dumps(items, indent=2, ensure_ascii=False) + '\n'
    old_json = json.dumps(old, indent=2, ensure_ascii=False) + '\n'

    if new_json == old_json:
        print(f'No changes. {len(items)} items.')
        return

    added = [i['sku'] for i in items if i['sku'] not in {o['sku'] for o in old}]
    removed = [o['sku'] for o in old if o['sku'] not in {i['sku'] for i in items}]
    changed = 0
    old_by = {o['sku']: o for o in old}
    for i in items:
        if i['sku'] in old_by and i != old_by[i['sku']]:
            changed += 1

    print(f'Changes:')
    print(f'  {len(added)} added: {added if added else "—"}')
    print(f'  {len(removed)} removed: {removed if removed else "—"}')
    print(f'  {changed} modified')

    if dry:
        print('(dry run — pricelist.json NOT written)')
        return

    OUT.write_text(new_json)
    print(f'Wrote {OUT} ({len(items)} items)')

if __name__ == '__main__':
    main()
