"""Podklady pro konfigurátor (anglicky) → export/konfigurator/.

Strada (všechny typy) a ALUX MAXI (všechny typy) — co soubor, to Excel: co matice, to list (velký list, bez A4),
nahoře popis + technické údaje + pravidla zón stojen, pod tím matice cen s barvou zóny v každé buňce.
K tomu CSV (každý rozměr = řádek se zónou stojen), CSV s pravidly zón a README.md pro AI.

Čte pricelist.json a products/<kategorie>/<sku>/{prices,metadata}.json + knowledge.en.md. Nic nemění.

    python3 scripts/build_konfigurator_export.py
"""
import csv, datetime, json, re
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'export' / 'konfigurator'
TODAY = datetime.date.today().isoformat()
GROUPS = {
    'strada': ('pergola', ['strada-carbo-dutinkovy', 'strada-carbo-plny', 'strada-glass']),
    'maxi': ('maxi', ['maxi-thermo', 'maxi-glass', 'maxi-bioclimatic', 'maxi-bioclimatic-duo', 'maxi-carbo-16', 'maxi-carbo-6', 'maxi-fusion']),
}
# zóny: barva podle popisku (MAXI) nebo podle (stojny, výztuha) (Strada); výchozí 2 stojny bez barvy
FILL_BY_LABEL = {'UNO - 2 posts': 'E2EFDA', 'UNO - 3 posts': 'A9D08E', 'DUO - 2 posts': 'BDD7EE', 'DUO - 3 posts': 'FFD966'}
FILL_BY_KEY = {(2, False): None, (2, True): 'A4D282', (3, False): 'FFD966', (3, True): 'F6B26B', (4, False): 'E67C73', (4, True): 'E67C73'}
FUSION_ROOF = {'Bio': 'Bioclimatic – adjustable louvres', 'Thermo': 'Thermo – 4 cm insulated thermo panel', 'Glass': 'Glass',
               'Carbo 16 mm': 'Carbo – 16 mm multiwall polycarbonate', 'Carbo 6 mm': 'Carbo – 6 mm solid polycarbonate'}

def rj(p): return json.loads(p.read_text(encoding='utf-8'))
ITEMS = {i['sku']: i for i in rj(ROOT / 'pricelist.json')}

def knowledge_en(path):
    """knowledge.en.md → [(sekce, [řádky])]."""
    text = re.sub(r'^---\n.*?\n---\n', '', path.read_text(encoding='utf-8'), flags=re.S)
    out = []
    for line in text.splitlines():
        s = line.strip().replace('**', '')
        if not s or s.startswith('# '):
            continue
        if s.startswith('## '):
            out.append((s[3:], []))
        elif out:
            out[-1][1].append(s[2:] if s.startswith(('- ', '* ')) else s)
    return out

def zone_rules(meta):
    """Pravidla zón shora dolů + výchozí zóna (když nesedí žádné → 2 posts)."""
    rules = [dict(z) for z in meta.get('support_zones') or []]
    last = rules[-1] if rules else None
    default = None if last and 'sirka_od' not in last and 'hloubka_od' not in last else {'stojny': 2, 'popisek_en': '2 posts'}
    return rules, default

def zone_at(rules, default, w, d):
    for z in rules:
        if 'sirka_od' in z and w < z['sirka_od']: continue
        if 'sirka_do' in z and w > z['sirka_do']: continue
        if 'hloubka_od' in z and d < z['hloubka_od']: continue
        if 'hloubka_do' in z and d > z['hloubka_do']: continue
        return z
    return default

def zone_label(z): return z.get('popisek_en') or f"{z['stojny']} posts" + (' + reinforcement' if z.get('pricky') else '')
def zone_fill(z, by_label):
    return FILL_BY_LABEL.get(zone_label(z)) if by_label else FILL_BY_KEY.get((z['stojny'], bool(z.get('pricky'))), 'DBDBDB')
def version(z):
    lab = zone_label(z)
    return lab.split(' - ')[0] if lab.startswith(('UNO', 'DUO')) else ''

def rule_text(z):
    cond = []
    if 'sirka_od' in z: cond.append(f"width ≥ {z['sirka_od']} mm")
    if 'sirka_do' in z: cond.append(f"width ≤ {z['sirka_do']} mm")
    if 'hloubka_od' in z: cond.append(f"depth ≥ {z['hloubka_od']} mm")
    if 'hloubka_do' in z: cond.append(f"depth ≤ {z['hloubka_do']} mm")
    return ' and '.join(cond) or 'all remaining sizes'

def matrices(sku, cat):
    p = rj(ROOT / 'products' / cat / sku / 'prices.json')
    return [(v['label'], v) for v in p['variants']] if p['type'] == 'multi-matrix' else [('', p)]

B = Font(bold=True); H = Font(bold=True, size=16); WH = Font(bold=True, color='FFFFFF')
DARK = PatternFill('solid', fgColor='242424'); GREY = PatternFill('solid', fgColor='F2F2F2')
THIN = Side(style='thin', color='BFBFBF'); BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical='top')

def build_sheet(wb, sku, cat, label, m, rows_csv, rules_csv):
    item, meta = ITEMS[sku], rj(ROOT / 'products' / cat / sku / 'metadata.json')
    by_label = cat == 'maxi'
    rules, default = zone_rules(meta)
    name = item['name_en'] + (f' – {label}' if label else '')
    tab = (name.replace('ALUX MAXI ', 'MAXI ').replace('Strada Carbo multiwall polycarbonate 16 mm', 'Strada Carbo 16 mm')
           .replace('Strada Carbo solid polycarbonate 6 mm', 'Strada Carbo 6 mm').replace('Strada Glass laminated glass VSG 44.2', 'Strada Glass')
           .replace('MAXI Fusion – ', 'Fusion '))[:31]
    ws = wb.create_sheet(tab)
    W, D, P = m['horizontal_values'], m['vertical_values'], m['prices']
    ws.column_dimensions['A'].width = 24
    for j in range(len(W) + 1):
        ws.column_dimensions[get_column_letter(2 + j)].width = 11
    r = 1
    ws.cell(r, 1, name).font = H; r += 1
    ws.cell(r, 1, f'SKU: {sku}' + (f'   ·   variant: {label}' if label else '') + f'   ·   prices in CZK excl. VAT (list price)   ·   data {TODAY}'); r += 2

    def text_row(head, text):
        nonlocal r
        ws.cell(r, 1, head).font = B; ws.cell(r, 1).fill = GREY; ws.cell(r, 1).alignment = WRAP
        c = ws.cell(r, 2, text); c.alignment = WRAP
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=min(1 + len(W), 22))
        ws.row_dimensions[r].height = 15 * max(1, len(text) // 150 + 1 + text.count('\n'))
        r += 1
    text_row('Description', item.get('description_en') or '')
    if sku == 'maxi-fusion':
        a, b = label.split(' - ')
        text_row('Fusion roof', f'Always DUO: the middle beam divides the roof into 2 fields. Field 1: {FUSION_ROOF[a]}. Field 2: {FUSION_ROOF[b]}. '
                 'The roofing materials are the same as on the standard pergolas – only the rafters are rotated and the roof slopes to the sides.')
    sections = knowledge_en(ROOT / 'products' / cat / sku / 'knowledge.en.md')
    for head, lines in sections:
        if head.lower() == 'description':
            continue
        text_row(head, '\n'.join('• ' + x for x in lines) if len(lines) > 1 else ' '.join(lines))
    if item.get('color_summary_en') and not any(h.lower().startswith('colo') for h, _ in sections):
        text_row('Colours', item['color_summary_en'])
    r += 1
    # pravidla zón
    ws.cell(r, 1, 'Post zones (rules evaluated top-down, first match applies)').font = B; r += 1
    for k, t in enumerate(['#', 'Zone', 'Condition', 'Posts', 'Reinforcement', 'Roof version']):
        c = ws.cell(r, 1 + k, t); c.font = WH; c.fill = DARK
    r += 1
    all_rules = rules + ([default] if default else [])
    for n, z in enumerate(all_rules, 1):
        cond = rule_text(z) if z is not default else 'no rule above matches'
        vals = [n, zone_label(z), cond, z['stojny'], 'yes' if z.get('pricky') else 'no', version(z) or '–']
        f = zone_fill(z, by_label)
        for k, v in enumerate(vals):
            c = ws.cell(r, 1 + k, v); c.border = BOX
            if f: c.fill = PatternFill('solid', fgColor=f)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=3)
        rules_csv.append([sku, item['name_en'], label, n, zone_label(z), z.get('sirka_od', ''), z.get('sirka_do', ''), z.get('hloubka_od', ''),
                          z.get('hloubka_do', ''), z['stojny'], 'yes' if z.get('pricky') else 'no', version(z), cond])
        r += 1
    ws.column_dimensions['C'].width = 11
    if any(z.get('pricky') for z in rules) and cat == 'pergola':
        ws.cell(r, 1, 'Reinforcement cost is already included in the matrix prices.').font = Font(italic=True); r += 1
    r += 1
    # matice
    hf, vf = meta.get('horizontal_footer'), meta.get('vertical_footer')
    ws.cell(r, 1, 'depth ↓ / width → (mm)').font = B
    for j, w in enumerate(W):
        c = ws.cell(r, 2 + j, w); c.font = WH; c.fill = DARK; c.alignment = Alignment(horizontal='center')
    if vf:
        c = ws.cell(r, 2 + len(W), vf.get('label_en', 'louvres')); c.font = WH; c.fill = DARK
    top = r; r += 1
    for i, d in enumerate(D):
        c = ws.cell(r, 1, d); c.font = WH; c.fill = DARK
        for j, w in enumerate(W):
            z = zone_at(rules, default, w, d)
            c = ws.cell(r, 2 + j, P[i][j]); c.number_format = '#,##0'; c.border = BOX
            f = zone_fill(z, by_label) if z else None
            if f: c.fill = PatternFill('solid', fgColor=f)
            louv = hf['values'][j] if hf else (vf['values'][i] if vf else '')
            rows_csv.append([sku, item['name_en'], label, w, d, P[i][j], zone_label(z) if z else '2 posts', z['stojny'] if z else 2,
                             'yes' if z and z.get('pricky') else 'no', version(z) if z else '',
                             (f"{louv}{vf.get('value_suffix_en', '')}" if vf else louv)])
        if vf:
            ws.cell(r, 2 + len(W), f"{vf['values'][i]}{vf.get('value_suffix_en', '')}")
        r += 1
    if hf:
        ws.cell(r, 1, hf.get('label_en', 'louvres')).font = B
        for j, v in enumerate(hf['values']):
            ws.cell(r, 2 + j, v).alignment = Alignment(horizontal='center')
        r += 1
    ws.freeze_panes = ws.cell(top + 1, 2)
    return tab, name, W, D

README_HEAD = """# ALUX pergola configurator data – {title}

Generated {today} from the ALUX pricelist repository. Prices are **list prices in CZK excluding VAT** (before any dealer discount).

## Files

| File | Content |
|---|---|
| `{prefix}.xlsx` | One sheet per price matrix: description, technical data, post-zone rules, price matrix (cells coloured by post zone). |
| `{prefix}.csv` | One row per size: `sku, product, variant, width_mm, depth_mm, price_czk, zone, posts, reinforcement, roof_version, louvres`. |
| `{prefix}-zones.csv` | The post-zone rules per product/variant in evaluation order. |

## Dimensions

- **width** (horizontal axis) = length of the pergola along the house wall, in mm.
- **depth** (vertical axis) = projection from the house wall, in mm.
- Prices exist only for the listed grid sizes (see the step of each axis in the matrix). The data contains no rule for sizes between grid points; a size outside the grid is not available.

## Post zones (how to read them)

- Each product has a list of zone rules. They are evaluated **top to bottom; the first rule whose conditions match applies**.
- Conditions: `width ≥ X` / `depth ≥ Y` (inclusive). A rule with several conditions needs all of them.
- If no rule matches, the size has the default zone (stated as the last row of the rules table).
- `posts` = number of posts of the pergola. `reinforcement = yes` = an extra reinforcement beam is part of the construction.
- The `zone` column in the CSV is already evaluated for every size – use it directly.
"""

STRADA_TEXT = """
## Strada – what it is

- Sloped pergola, **mounting on a wall plate only**, frame RAL 7016 Axalta fine structure.
- Types: **Carbo 16 mm** (multiwall polycarbonate 16 mm 5X, clear / anthracite / opal), **Carbo 6 mm** (solid polycarbonate 6 mm, clear / opal / anthracite / other colours, all in the price), **Glass** (laminated safety glass VSG 44.2, max. depth 4,000 mm).
- Zones: `2 posts` (default), `2 posts + reinforcement`, `3 posts`, `3 posts + reinforcement`. The reinforcement cost is **already included** in the matrix price – do not add it again.
- Note: at some zone borders the price can drop (e.g. "2 posts + reinforcement" → "3 posts" without reinforcement). This is intended; always take the price from the matrix.
"""

MAXI_TEXT = """
## ALUX MAXI – what it is

- Large pergola with a massive perimeter profile **300 × 150 mm** (main profile height 300 mm), **posts 150 × 150 mm**, frame RAL 7016 Axalta fine structure.
- Primarily designed as **wall-mounted** (anchored to the house). The profiles have space for integrated perimeter LED lighting (optional surcharge).
- **UNO** = one roof field (no middle beam, rafters parallel to the depth, slope to the front).
- **DUO** = a middle beam divides the roof into **2 fields** (saddle roof sloping to the sides, rafters parallel to the width).
- For Thermo, Glass, Carbo 16 mm and Carbo 6 mm the version (UNO / DUO) is **given by the size** – it is in the zone name: `UNO - 2 posts`, `UNO - 3 posts`, `DUO - 2 posts`, `DUO - 3 posts`.
- **Bioclimatic UNO** (`maxi-bioclimatic`): adjustable louvres, 1 field; widths follow the louvre series (1,990 – 7,990 mm in 200 mm steps), number of louvres per width is in the `louvres` column.
- **Bioclimatic DUO** (`maxi-bioclimatic-duo`): always DUO, 2 fields; the louvre series is in the **depth** (1,990 – 5,590 mm); `louvres` = louvres per field "× 2 fields". The louvres run parallel to the house and both fields can be operated independently.
- **Fusion** (`maxi-fusion`): always DUO, **the roof is divided into 2 fields with different roofing**. The roofing materials are the same as on the standard pergolas – only the rafters are rotated and the roof slopes to the sides. 6 combinations (= `variant`): Bio / Glass, Bio / Carbo 16 mm, Bio / Carbo 6 mm, Thermo / Glass, Thermo / Carbo 16 mm, Thermo / Carbo 6 mm. All have the same grid (widths 4,000 – 8,000, depths 1,990 – 4,990, 200 mm steps) and the same zones.
"""

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, (cat, skus) in GROUPS.items():
        prefix = 'ALUX-Strada-configurator' if key == 'strada' else 'ALUX-MAXI-configurator'
        wb = Workbook(); ov = wb.active; ov.title = 'Overview'
        rows_csv, rules_csv, overview = [], [], []
        for sku in skus:
            for label, m in matrices(sku, cat):
                tab, name, W, D = build_sheet(wb, sku, cat, label, m, rows_csv, rules_csv)
                overview.append((tab, name, sku, label, f'{W[0]}–{W[-1]}', f'{D[0]}–{D[-1]}', len(W) * len(D)))
        ov['A1'] = f"ALUX {'Strada' if key == 'strada' else 'MAXI'} – configurator data"; ov['A1'].font = H
        ov['A2'] = f'Prices in CZK excl. VAT (list price). Generated {TODAY}. See README.md for the rules.'
        for k, t in enumerate(['Sheet', 'Product', 'SKU', 'Variant', 'Width (mm)', 'Depth (mm)', 'Sizes']):
            c = ov.cell(4, 1 + k, t); c.font = WH; c.fill = DARK
        for n, row in enumerate(overview, 5):
            for k, v in enumerate(row):
                ov.cell(n, 1 + k, v)
        for k, wdt in enumerate([28, 52, 24, 20, 14, 14, 8], 1):
            ov.column_dimensions[get_column_letter(k)].width = wdt
        wb.save(OUT / f'{prefix}.xlsx')
        with open(OUT / f'{prefix}.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['sku', 'product', 'variant', 'width_mm', 'depth_mm', 'price_czk', 'zone', 'posts', 'reinforcement', 'roof_version', 'louvres'])
            w.writerows(rows_csv)
        with open(OUT / f'{prefix}-zones.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['sku', 'product', 'variant', 'order', 'zone', 'width_from_mm', 'width_to_mm', 'depth_from_mm', 'depth_to_mm',
                                           'posts', 'reinforcement', 'roof_version', 'condition'])
            w.writerows(rules_csv)
        # README: obecná pravidla + popis řady + tabulka zón a rozměrů z dat
        lines = [README_HEAD.format(title='Strada' if key == 'strada' else 'ALUX MAXI', today=TODAY, prefix=prefix),
                 STRADA_TEXT if key == 'strada' else MAXI_TEXT, '\n## Products, sizes and zones\n']
        seen = set()
        first_variant = {}
        for z in rules_csv:
            sku, name, variant = z[0], z[1], z[2]
            first_variant.setdefault(sku, variant)
            if sku == 'maxi-fusion' and variant != first_variant[sku]:
                continue  # Fusion: všech 6 variant má stejné zóny
            if (sku, variant) not in seen:
                seen.add((sku, variant))
                ovr = next(o for o in overview if o[2] == sku and (o[3] == variant))
                title = name + (' (all 6 variants)' if sku == 'maxi-fusion' else (f' – {variant}' if variant else ''))
                lines.append(f'\n### {title} (`{sku}`)\n\nWidth {ovr[4]} mm, depth {ovr[5]} mm.\n\n| # | Zone | Condition | Posts | Reinforcement |\n|---|---|---|---|---|')
            lines.append(f'| {z[3]} | {z[4]} | {z[12]} | {z[9]} | {z[10]} |')
        (OUT / f'README-{key}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'{prefix}: {len(overview)} listů, {len(rows_csv)} rozměrů')

if __name__ == '__main__':
    main()
