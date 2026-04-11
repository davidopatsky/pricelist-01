#!/usr/bin/env python3
"""Bootstrap pricelist.xlsx from pricelist.json.

One-way: pricelist.json → pricelist.xlsx. Apply blueprint formatting:
- 14 columns, fixed order
- freeze panes A2
- text format @ on text columns
- numeric format #,##0 on cost + cost_percent
- wrap text on description + color_summary
- auto-width capped at 50 chars

Run:
    python3 scripts/init_xlsx.py
"""
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'pricelist.json'
OUT = ROOT / 'pricelist.xlsx'

# 16-field schema in fixed order (v6.2: added name_en)
#
# PRICING CONVENTION (see BLUEPRINT.md):
# `standard_price = 1` is a magic placeholder; the real meaning is encoded in
# the combination with `price_formula`. Matrix products use sp=1 + pf="matrix",
# formula-priced extras use sp=1 + pf="<rule text>", and unset items use sp=1
# + pf=null. The mixed cell type for standard_price tolerates both numeric and
# string values without auto-converting.
COLUMNS = [
    ('sku',                'text'),
    ('category',           'text'),
    ('name',               'text'),
    ('name_en',            'text'),
    ('description',        'wrap'),
    ('standard_price',     'mixed'),
    ('price_formula',      'text'),
    ('currency',           'text'),
    ('unit',               'text'),
    ('cost',               'num'),
    ('cost_percent',       'num'),
    ('discount',           'text'),
    ('delivery_weeks',     'text'),
    ('color_summary',      'wrap'),
    ('raynet_description', 'wrap'),
    ('raynet_cost',        'num'),
]

MAX_WIDTH = 50
HEADER_FONT = Font(name='Arial', size=10, bold=True, color='FFFFFF')
HEADER_FILL = PatternFill('solid', start_color='374151')
BODY_FONT = Font(name='Arial', size=10)

def build():
    if not SRC.exists():
        raise SystemExit(f'{SRC} not found — nothing to bootstrap from')
    items = json.loads(SRC.read_text())
    if not isinstance(items, list):
        raise SystemExit(f'{SRC} is not a flat array')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Pricelist'

    # Header row (row 1)
    for c, (key, _) in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=c, value=key)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='left', vertical='center')

    # Data rows
    for r, item in enumerate(items, 2):
        for c, (key, kind) in enumerate(COLUMNS, 1):
            v = item.get(key)
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BODY_FONT
            if kind == 'num':
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal='right', vertical='center')
            elif kind == 'wrap':
                cell.number_format = '@'
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            elif kind == 'mixed':
                # standard_price can be "matrix", number, or null — store as-is
                # If number, format it; if text, text format
                if isinstance(v, (int, float)):
                    cell.number_format = '#,##0'
                else:
                    cell.number_format = '@'
                cell.alignment = Alignment(horizontal='left', vertical='center')
            else:  # text
                cell.number_format = '@'
                cell.alignment = Alignment(horizontal='left', vertical='center')

    # Freeze header
    ws.freeze_panes = 'A2'

    # Auto-width, capped at 50 chars
    for c, (key, _) in enumerate(COLUMNS, 1):
        max_len = len(key)
        for r in range(2, len(items) + 2):
            v = ws.cell(row=r, column=c).value
            if v is None:
                continue
            max_len = max(max_len, len(str(v)))
        width = min(max_len + 2, MAX_WIDTH)
        ws.column_dimensions[get_column_letter(c)].width = width

    wb.save(OUT)
    print(f'Wrote {OUT} ({OUT.stat().st_size} bytes)')
    print(f'{len(items)} rows × {len(COLUMNS)} columns')

if __name__ == '__main__':
    build()
