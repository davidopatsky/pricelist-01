"""Sestaví konfiguracni-soubor/ z products/<kategorie>/<sku>/config.json.

  pergoly-konfigurace.xlsx  – list Pergoly (řádek = pergola), list MAXI Fusion (řádek = kombinace),
                              list Popis parametrů
  pergoly-konfigurace.json  – všechny config.json v jednom souboru (klíč = SKU)

Spuštění: python3 scripts/build_konfiguracni_soubor.py
"""
import glob
import json
import os

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'konfiguracni-soubor')
P = {x['sku']: x for x in json.load(open(os.path.join(ROOT, 'pricelist.json')))}


def cs(o):
    return o.get('cs') if isinstance(o, dict) else (o or '')


def yn(v):
    return 'ano' if v is True else 'ne' if v is False else ''


def surch(v):
    return 'příplatek' if v == 'surcharge' else ''


def colours(rc):
    return '; '.join(cs(o) + (' (příplatek)' if o.get('surcharge') else '') for o in (rc or {}).get('options', []))


def roof_cols(c):
    rc, lc, mt = c.get('roof_color') or {}, c.get('louvre_color'), c.get('motor_type')
    return dict(
        typ_strechy=cs(c.get('roof_type')),
        barva_strechy=colours(rc),
        vlastni_barva_strechy=yn(rc['custom_allowed']) if 'custom_allowed' in rc else '',
        poznamka_barva_strechy=cs(rc.get('note')),
        barva_lamel_standard='; '.join(cs(o) for o in lc['standard']) if lc else '',
        ostatni_barvy_lamel=surch(lc.get('other_colors')) if lc else '',
        typ_motoru='; '.join(cs(o) for o in mt['options']) if mt else '',
        motor_standard=mt.get('standard', '') if mt else '',
    )


rows, allcfg, fusion = [], {}, []
for cat in ('pergola', 'maxi', 'simple'):
    for d in sorted(glob.glob(os.path.join(ROOT, 'products', cat, '*', ''))):
        sku = os.path.basename(d[:-1])
        if sku not in P:
            continue
        r = {'sku': sku, 'kategorie': cat, 'nazev': P[sku]['name']}
        cf = os.path.join(d, 'config.json')
        if not os.path.exists(cf):
            r['stav'] = 'k doladění'
            m = json.load(open(os.path.join(d, 'metadata.json')))
            fr = next((x for x in m.get('standard_colors', []) if x['part'] == 'frame'), None)
            if fr:
                r['barva_ramu_standard'] = fr['options'][0]['cs']
            rows.append(r)
            continue
        c = json.load(open(cf))
        allcfg[sku] = c
        r['stav'] = 'vyplněno'
        r['barva_ramu_standard'] = cs(c['frame_color']['standard'])
        r['ostatni_barvy_ramu'] = surch(c['frame_color'].get('other_colors'))
        r['led_lamely_krokve'] = yn(c.get('led_rafters'))
        r['led_obvod'] = yn(c.get('led_perimeter')) + (' (příplatek)' if c.get('led_perimeter_note') else '')
        if 'roof_combination' in c:  # Fusion
            f = c['roof_fields']
            r['typ_strechy'] = 'Kombinace 2 polí: ' + '; '.join(o['variant'] for o in c['roof_combination']['options'])
            r['poznamka_barva_strechy'] = 'barvy podle pole – viz list MAXI Fusion'
            for o in c['roof_combination']['options']:
                a, b = roof_cols(f[o['field_1']]), roof_cols(f[o['field_2']])
                fusion.append({
                    'kombinace': o['variant'],
                    'pole1_typ': a['typ_strechy'],
                    'pole1_barvy': a['barva_strechy'] or a['barva_lamel_standard'],
                    'pole1_vlastni': a['vlastni_barva_strechy'] or ('příplatek' if a['ostatni_barvy_lamel'] else ''),
                    'motor': a['typ_motoru'],
                    'motor_standard': a['motor_standard'],
                    'pole2_typ': b['typ_strechy'],
                    'pole2_barvy': b['barva_strechy'],
                    'pole2_vlastni': b['vlastni_barva_strechy'],
                    'pole2_poznamka': b['poznamka_barva_strechy'],
                })
        else:
            r.update(roof_cols(c))
        rows.append(r)

HF = PatternFill('solid', fgColor='1F2937')
THIN = Side(style='thin', color='D1D5DB')
YEL = PatternFill('solid', fgColor='FEF3C7')


def sheet(ws, cols, data, widths, freeze):
    for i, (_, label) in enumerate(cols, 1):
        c = ws.cell(1, i, label)
        c.font, c.fill = Font(bold=True, color='FFFFFF'), HF
        c.alignment = Alignment(wrap_text=True, vertical='center')
    for ri, r in enumerate(data, 2):
        for i, (k, _) in enumerate(cols, 1):
            c = ws.cell(ri, i, r.get(k) or None)
            c.alignment, c.border = Alignment(wrap_text=True, vertical='top'), Border(bottom=THIN)
            if r.get('stav') == 'k doladění':
                c.fill = YEL
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes, ws.row_dimensions[1].height = freeze, 42


wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Pergoly'
sheet(ws, [('sku', 'SKU'), ('kategorie', 'Kategorie'), ('nazev', 'Název'), ('stav', 'Stav'),
           ('barva_ramu_standard', 'Barva rámu – standard'), ('ostatni_barvy_ramu', 'Ostatní barvy rámu'),
           ('typ_strechy', 'Typ střechy'), ('barva_strechy', 'Barva střechy – možnosti'),
           ('vlastni_barva_strechy', 'Vlastní (atypická) barva střechy'), ('poznamka_barva_strechy', 'Poznámka k barvě střechy'),
           ('barva_lamel_standard', 'Barva lamel – standard'), ('ostatni_barvy_lamel', 'Ostatní barvy lamel'),
           ('typ_motoru', 'Typ motoru – možnosti'), ('motor_standard', 'Motor v ceně'),
           ('led_lamely_krokve', 'LED lamely / krokve'), ('led_obvod', 'LED obvod')],
      rows, [24, 11, 40, 11, 30, 12, 34, 48, 14, 34, 34, 12, 22, 12, 12, 16], 'D2')

ws = wb.create_sheet('MAXI Fusion')
sheet(ws, [('kombinace', 'Kombinace (ceník)'), ('pole1_typ', 'Pole 1 – typ střechy'), ('pole1_barvy', 'Pole 1 – barvy'),
           ('pole1_vlastni', 'Pole 1 – vlastní / ostatní barva'), ('motor', 'Typ motoru – možnosti'), ('motor_standard', 'Motor v ceně'),
           ('pole2_typ', 'Pole 2 – typ střechy'), ('pole2_barvy', 'Pole 2 – barvy'), ('pole2_vlastni', 'Pole 2 – vlastní barva'),
           ('pole2_poznamka', 'Pole 2 – poznámka')],
      fusion, [22, 34, 44, 16, 20, 12, 34, 40, 14, 40], 'B2')

ws = wb.create_sheet('Popis parametrů')
for i, (a, b) in enumerate([
    ('Parametr', 'Význam / hodnoty'),
    ('Barva rámu – standard', 'standardní barva rámu'),
    ('Ostatní barvy rámu', '„příplatek“ = jiné barvy rámu za příplatek'),
    ('Typ střechy', 'typ střešní výplně'),
    ('Barva střechy – možnosti', 'nabízené barvy střechy; u Thermo spodní / horní strana panelu'),
    ('Vlastní barva střechy', 'ano = kromě nabízených lze zadat jinou / atypickou barvu ručně'),
    ('Barva lamel, Typ motoru', 'jen Bioclimatic (ALUX i MAXI) a pole Bio u MAXI Fusion'),
    ('LED lamely / krokve, LED obvod', 'ano / ne; prázdné = zatím nevyplněno; „(příplatek)“ = příplatková možnost'),
    ('MAXI Fusion', 'vždy DUO, 2 pole s různou krytinou; pole 1 = Bio nebo Thermo, pole 2 = Glass / Carbo 16 mm / Carbo 6 mm; list MAXI Fusion'),
    ('Stav', '„k doladění“ (žlutě) = config.json zatím chybí, jen barva rámu z metadat'),
], 1):
    ws.cell(i, 1, a)
    ws.cell(i, 2, b)
    if i == 1:
        ws.cell(1, 1).font = ws.cell(1, 2).font = Font(bold=True)
ws.column_dimensions['A'].width, ws.column_dimensions['B'].width = 34, 100

os.makedirs(OUT, exist_ok=True)
wb.save(os.path.join(OUT, 'pergoly-konfigurace.xlsx'))
with open(os.path.join(OUT, 'pergoly-konfigurace.json'), 'w') as fh:
    json.dump(allcfg, fh, ensure_ascii=False, indent=2)
    fh.write('\n')
print(f'{len(rows)} pergol, {len(allcfg)} s config.json, {len(fusion)} kombinací Fusion')
