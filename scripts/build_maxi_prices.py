"""Ceny ALUX MAXI ze zdrojových ALUX ceníků (revize 29. 10. 2026).

1. anomálie ve zdrojových ALUX cenících (cena se šířkou / hloubkou neroste) → oprava v products/pergola/*/prices.json
2. MAXI = opravený zdroj × MAXI_MARKUP
3. rozměry mimo zdroj: Glass 4600–5000 = Carbo plný, Thermo a Bioclimatic DUO průměrný krok posledních 3 kroků
4. Bioclimatic DUO × DUO_SURCHARGE
5. Fusion = (MAXI A + MAXI B) / 2 × (1 + FUSION_P)
Kontroly: monotónnost, MAXI = ALUX × 1,2, Fusion mezi čistými MAXI. Report (srovnání se stávajícími cenami, log, kontroly)
→ export/ALUX-MAXI-revize-<datum>.xlsx. pricelist.xlsx ani texty nemění.

    python3 scripts/build_maxi_prices.py
"""
import copy, datetime, json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# --- parametry -------------------------------------------------------------
MAXI_MARKUP = 1.20     # MAXI = standardní ALUX × 1,20
DUO_SURCHARGE = 1.05   # Bioclimatic DUO: druhé pole, druhý motor, středový nosník
FUSION_P = 0.04        # Fusion: příplatek za kombinaci krytin (přechod, těsnění u středového nosníku)

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / 'export' / f'ALUX-MAXI-revize-{datetime.date.today().isoformat()}.xlsx'
SOURCES = ['alux-bioclimatic', 'alux-thermo', 'alux-glass', 'alux-carbo-dutinkovy', 'alux-carbo-plny', 'alux-trapez']
NAMES = {'alux-bioclimatic': 'ALUX Bioclimatic', 'alux-thermo': 'ALUX Thermo', 'alux-glass': 'ALUX Glass',
         'alux-carbo-dutinkovy': 'ALUX Carbo dutinkový', 'alux-carbo-plny': 'ALUX Carbo plný', 'alux-trapez': 'ALUX Trapez'}

def rnd(x): return int(Decimal(str(x)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
def rj(p): return json.loads(p.read_text(encoding='utf-8'))
def wj(p, o): p.write_text(json.dumps(o, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

RAISED = []  # dopočítané buňky zvednuté kvůli monotónnosti (šířka zdroje, hloubka zdroje)
LOG = []  # (kategorie, tabulka, šířka, hloubka, stará, nová, poznámka)

# --- krok 1: anomálie ve zdroji ---------------------------------------------
def fix_line(vals, keep=0):
    """Prvních keep buněk je pevných (zdroj u dopočítaných tabulek). Platné buňky = nejdelší rostoucí podposloupnost
    (počáteční plochý úsek = min. rozměr, platí); neplatné: vnitřní → lineární interpolace mezi platnými sousedy,
    okrajové → průměrný krok posledních 3 platných."""
    n = len(vals)
    if keep:
        fixed, first, floor = set(range(keep)), keep, vals[keep - 1]
    else:
        lead = 0
        while lead + 1 < n and vals[lead + 1] == vals[0]:
            lead += 1
        fixed, first, floor = set(range(lead)), lead, float('-inf')
    idx = [x for x in range(first, n) if vals[x] > floor]
    best = {x: 1 for x in idx}; prev = {x: None for x in idx}
    for a, i in enumerate(idx):
        for k in idx[:a]:
            if vals[k] < vals[i] and best[k] + 1 > best[i]:
                best[i], prev[i] = best[k] + 1, k
    valid = set(fixed)
    if idx:
        i = max(idx, key=lambda x: (best[x], -x))
        while i is not None:
            valid.add(i); i = prev[i]
    out = list(vals)
    v = sorted(valid)
    for i in range(n):
        if i in valid:
            continue
        lo = max((k for k in v if k < i), default=None)
        hi = min((k for k in v if k > i), default=None)
        if lo is not None and hi is not None:
            out[i] = rnd(vals[lo] + (vals[hi] - vals[lo]) * (i - lo) / (hi - lo))
        else:
            last = [k for k in v if k < i][-3:]
            step = (vals[last[-1]] - vals[last[0]]) / (last[-1] - last[0])
            out[i] = rnd(vals[last[-1]] + step * (i - last[-1]))
    return out

def anomalies(P):
    return sum(1 for r in P for j in range(1, len(r)) if r[j] <= r[j - 1]) + \
           sum(1 for i in range(1, len(P)) for j in range(len(P[0])) if P[i][j] <= P[i - 1][j])

def fix_table(P, keep_rows=0):
    """Krok 1 na celé tabulce: řádky (šířka) a sloupce (hloubka) střídavě, dokud cena všude roste.
    Prvních keep_rows řádků (zdroj) se nemění."""
    for _ in range(50):
        if not anomalies(P):
            return P
        P = [r if i < keep_rows else fix_line(r) for i, r in enumerate(P)]
        cols = [fix_line([P[i][j] for i in range(len(P))], keep_rows) for j in range(len(P[0]))]
        P = [[cols[j][i] for j in range(len(P[0]))] for i in range(len(P))]
    raise SystemExit('anomálie nejdou odstranit')

SRC, SRC_ORIG, SRC_CHANGED = {}, {}, []
for s in SOURCES:
    p = rj(ROOT / 'products/pergola' / s / 'prices.json')
    W, D, P0 = p['horizontal_values'], p['vertical_values'], p['prices']
    P = fix_table(copy.deepcopy(P0))
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if P[i][j] != P0[i][j]:
                LOG.append(('anomálie', NAMES[s], w, d, P0[i][j], P[i][j], 'zdroj ALUX'))
    if P != P0:
        SRC_CHANGED.append(s)
    SRC[s], SRC_ORIG[s] = (W, D, P), (W, D, P0)

# --- rozšířené zdroje (extrapolace průměrným krokem posledních 3 kroků) --------
def ext_cols(W, D, P, new_D, name):
    """Přidá hloubky new_D: v každém sloupci průměrný krok posledních 3 kroků (na 100 mm)."""
    rows = [list(r) for r in P]; D = list(D)
    for d in new_D:
        rows.append([P[-1][j] + (P[-1][j] - P[-4][j]) / (D[-1] - D[-4]) * (d - D[len(P) - 1]) for j in range(len(W))])
    # sloupce se prodlužují každý svým krokem → v dopočítané části by cena se šířkou mohla klesnout;
    # tam se zvedne na souseda vlevo / nad ní + 1 Kč (nikdy se nesnižuje, buňky zdroje se nemění)
    fixed = [list(r) for r in rows]
    for i in range(len(P), len(fixed)):
        for j in range(len(W)):
            low = max(fixed[i - 1][j], fixed[i][j - 1] if j else float('-inf')) + 1
            if fixed[i][j] < low:
                RAISED.append((name, W[j], D[len(P) - 1] + 100 * (i - len(P) + 1), rnd(fixed[i][j]), rnd(low)))
                fixed[i][j] = low
    return list(D) + list(new_D), fixed

def ext_width(W, P, new_w):
    """Přidá šířku new_w: v každém řádku průměrný krok posledních 3 kroků."""
    return list(W) + [new_w], [list(r) + [r[-1] + (r[-1] - r[-4]) / (W[-1] - W[-4]) * (new_w - W[-1])] for r in P]

def lookup(W, D, P, w, d):
    return P[D.index(d)][W.index(w)]

# --- krok 2–4: MAXI tabulky ---------------------------------------------------
def grid(a, b, step=100): return list(range(a, b + 1, step))
OLD = {}
def old(sku):
    if sku not in OLD:
        OLD[sku] = rj(ROOT / 'products/maxi' / sku / 'prices.json')
    return OLD[sku]

NEW = {}  # (sku, variant label or '') → (W, D, P)
EXTRA = {}  # (sku, label) → set((w, d)) extrapolované buňky

def make(sku, label, W, D, f, extra=lambda w, d: False):
    NEW[(sku, label)] = (W, D, [[rnd(f(w, d)) for w in W] for d in D])
    EXTRA[(sku, label)] = {(w, d) for d in D for w in W if extra(w, d)}

# Thermo: hloubky 5600–6000 extrapolací ze zdroje Thermo
TW, TD, TP = SRC['alux-thermo']
TD2, TP2 = ext_cols(TW, TD, TP, grid(5600, 6000), 'ALUX Thermo')
make('maxi-thermo', '', grid(2000, 8000), grid(2000, 6000),
     lambda w, d: lookup(TW, TD2, TP2, w, d) * MAXI_MARKUP, lambda w, d: d > TD[-1])
# Glass: hloubky 4600–5000 = Carbo plný
GW, GD, GP = SRC['alux-glass']; CPW, CPD, CPP = SRC['alux-carbo-plny']
make('maxi-glass', '', grid(2000, 8000), grid(2000, 5000),
     lambda w, d: (lookup(GW, GD, GP, w, d) if d in GD else lookup(CPW, CPD, CPP, w, d)) * MAXI_MARKUP)
# Carbo
for lab, s in (('dutinkový polykarbonát', 'alux-carbo-dutinkovy'), ('plný polykarbonát', 'alux-carbo-plny')):
    W_, D_, P_ = SRC[s]
    make('maxi-carbo', lab, grid(2000, 8000), grid(2000, 6000), lambda w, d, W_=W_, D_=D_, P_=P_: lookup(W_, D_, P_, w, d) * MAXI_MARKUP)
# Bioclimatic UNO
BW, BD, BP = SRC['alux-bioclimatic']
make('maxi-bioclimatic', '', [w for w in BW if w <= 7590], grid(2000, 4200), lambda w, d: lookup(BW, BD, BP, w, d) * MAXI_MARKUP)
# Bioclimatic DUO: šířka → nejbližší vyšší šířka řady BIO (8000 → 8190 extrapolace), hloubka → nahoru na 100 mm
BW2, BP2 = ext_width(BW, BP, BW[-1] + 200)
BD2, BP2 = ext_cols(BW2, BD, BP2, grid(4600, 5600), 'ALUX Bioclimatic')
def bio_w(w): return next(x for x in BW2 if x >= w)
def up100(d): return max(2000, -(-d // 100) * 100)
make('maxi-bioclimatic-duo', '', grid(2000, 8000), list(range(1990, 5591, 200)),
     lambda w, d: lookup(BW2, BD2, BP2, bio_w(w), up100(d)) * MAXI_MARKUP * DUO_SURCHARGE,
     lambda w, d: bio_w(w) > BW[-1] or up100(d) > BD[-1])

# --- krok 5: Fusion = [MAXI_A + MAXI_B] / 2 × (1 + p) -------------------------
def interp(key, w, d):
    """Hodnota MAXI tabulky; chybějící hloubka (1990 vs. 2000 apod.) lineárně mezi sousedy (pod minimem prodloužením)."""
    W, D, P = NEW[key]
    j = W.index(w)
    if d in D:
        return P[D.index(d)][j]
    lo = max((x for x in D if x < d), default=D[0]); hi = min((x for x in D if x > d), default=None)
    if lo == D[0] and d < D[0]:
        lo, hi = D[0], D[1]
    a, b = P[D.index(lo)][j], P[D.index(hi)][j]
    return a + (b - a) * (d - lo) / (hi - lo)
MAXI_OF = {'Bio': ('maxi-bioclimatic-duo', ''), 'Thermo': ('maxi-thermo', ''), 'Glass': ('maxi-glass', ''),
           'Carbo 16 mm': ('maxi-carbo', 'dutinkový polykarbonát'), 'Carbo 6 mm': ('maxi-carbo', 'plný polykarbonát')}
FUSION = ['Bio - Glass', 'Bio - Carbo 16 mm', 'Bio - Carbo 6 mm', 'Thermo - Glass', 'Thermo - Carbo 16 mm', 'Thermo - Carbo 6 mm']
for lab in FUSION:
    a, b = (MAXI_OF[x] for x in lab.split(' - '))
    D = list(range(1990, 4991, 200)) if lab.startswith('Bio') else grid(2000, 5000)
    make('maxi-fusion', lab, grid(2000, 8000), D, lambda w, d, a=a, b=b: (interp(a, w, d) + interp(b, w, d)) / 2 * (1 + FUSION_P))

# --- log MAXI změn -------------------------------------------------------------
TITLES = {'maxi-thermo': 'MAXI Thermo', 'maxi-glass': 'MAXI Glass', 'maxi-bioclimatic': 'MAXI Bioclimatic UNO',
          'maxi-bioclimatic-duo': 'MAXI Bioclimatic DUO', 'maxi-carbo': 'MAXI Carbo', 'maxi-fusion': 'MAXI Fusion'}
def title(key):
    sku, lab = key
    if sku == 'maxi-carbo': return f"MAXI Carbo {lab.split()[0]}"
    if sku == 'maxi-fusion': return f"MAXI Fusion {lab}"
    return TITLES[sku]
def old_matrix(key):
    o = old(key[0])
    if o['type'] == 'multi-matrix':
        o = next(v for v in o['variants'] if v['label'] == key[1])
    return o['horizontal_values'], o['vertical_values'], o['prices']
COMPARE = []  # (tabulka, w, d, stará, nová)
for key, (W, D, P) in NEW.items():
    OW, OD, OP = old_matrix(key)
    assert (OW, OD) == (W, D), key
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            o, n = OP[i][j], P[i][j]
            COMPARE.append((title(key), w, d, o, n))
            if key[0] == 'maxi-fusion':
                cat = 'Fusion'
            elif (w, d) in EXTRA[key]:
                cat = 'extrapolace'
            elif key[0] == 'maxi-bioclimatic-duo':
                cat = 'DUO +5 %'
            elif key[0] == 'maxi-glass' and d > 4500:
                cat = 'extrapolace'
            else:
                cat = None if o == n else 'přepočet ze zdroje'
            if cat and o != n:
                note = {'extrapolace': 'mimo rozsah zdroje', 'DUO +5 %': f'× {DUO_SURCHARGE}', 'Fusion': f'(A + B) / 2 × {1 + FUSION_P:g}',
                        'přepočet ze zdroje': 'opravený zdroj × 1,2'}[cat]
                if key[0] == 'maxi-glass' and d > 4500: note = 'ALUX Carbo plný × 1,2'
                LOG.append((cat, title(key), w, d, o, n, note))

# --- kontroly ------------------------------------------------------------------
CHECKS = []  # (pravidlo, tabulka, w, d, hodnota, detail)
def lamella_flat(key, W, j):  # DUO: šířky zaokrouhlené na stejnou šířku řady lamel BIO (i minimální 2390) = záměrně stejná cena
    return key[0] == 'maxi-bioclimatic-duo' and bio_w(W[j]) == bio_w(W[j - 1])
for key, (W, D, P) in NEW.items():
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if j and P[i][j] <= P[i][j - 1] and not lamella_flat(key, W, j):
                CHECKS.append(('1 monotónnost (šířka)', title(key), w, d, P[i][j], f'≤ {P[i][j-1]} u šířky {W[j-1]}'))
            if i and P[i][j] <= P[i - 1][j]:
                CHECKS.append(('1 monotónnost (hloubka)', title(key), w, d, P[i][j], f'≤ {P[i-1][j]} u hloubky {D[i-1]}'))
# 2: MAXI = opravený ALUX × 1,2 tam, kde zdroj existuje
for key, s in ((('maxi-thermo', ''), 'alux-thermo'), (('maxi-glass', ''), 'alux-glass'), (('maxi-bioclimatic', ''), 'alux-bioclimatic'),
               (('maxi-carbo', 'dutinkový polykarbonát'), 'alux-carbo-dutinkovy'), (('maxi-carbo', 'plný polykarbonát'), 'alux-carbo-plny')):
    W, D, P = NEW[key]; SW, SD, SP = SRC[s]
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if d in SD and w in SW and P[i][j] != rnd(lookup(SW, SD, SP, w, d) * MAXI_MARKUP):
                CHECKS.append(('2 MAXI = ALUX × 1,2', title(key), w, d, P[i][j], f'zdroj × 1,2 = {rnd(lookup(SW, SD, SP, w, d) * MAXI_MARKUP)}'))
# 3, 4: Fusion mezi čistými MAXI
for lab in FUSION:
    W, D, P = NEW[('maxi-fusion', lab)]
    a, b = (MAXI_OF[x] for x in lab.split(' - '))
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            va, vb = interp(a, w, d), interp(b, w, d)
            if P[i][j] < min(va, vb) - 0.5:
                CHECKS.append(('3 Fusion ≥ levnější MAXI', f'MAXI Fusion {lab}', w, d, P[i][j], f'min = {rnd(min(va, vb))}'))
            if P[i][j] > max(va, vb) * (1 + FUSION_P) + 0.5:
                CHECKS.append(('4 Fusion ≤ dražší MAXI × (1 + p)', f'MAXI Fusion {lab}', w, d, P[i][j], f'max × (1 + p) = {rnd(max(va, vb) * (1 + FUSION_P))}'))

# --- zápis prices.json ---------------------------------------------------------
for s in SRC_CHANGED:
    p = rj(ROOT / 'products/pergola' / s / 'prices.json')
    p['prices'] = SRC[s][2]
    wj(ROOT / 'products/pergola' / s / 'prices.json', p)
NOTE_TAIL = f"Náklad 58 % (cost_percent). Parametry: přirážka MAXI {MAXI_MARKUP:g}, příplatek DUO {DUO_SURCHARGE:g}, příplatek Fusion p = {FUSION_P:g}."
NOTES = {
    'maxi-thermo': "Prodejní cena = ALUX Thermo × 1,2 (zaokrouhleno na celé Kč). Hloubky 5600–6000 mm dopočítány průměrným krokem posledních 3 kroků zdroje (zvlášť pro každý sloupec).",
    'maxi-glass': "Prodejní cena = ALUX Glass × 1,2 (zaokrouhleno na celé Kč). Hloubky 4600–5000 mm = ALUX Carbo plný × 1,2 (Glass = Carbo plný).",
    'maxi-bioclimatic': "UNO. Prodejní cena = ALUX Bioclimatic × 1,2 (zaokrouhleno na celé Kč).",
    'maxi-bioclimatic-duo': "DUO. Prodejní cena = ALUX Bioclimatic × 1,2 × 1,05 (druhé pole, druhý motor, středový nosník), zaokrouhleno na celé Kč. Šířka → nejbližší vyšší šířka řady lamel BIO (8000 → 8190), hloubka → nahoru na 100 mm; mimo rozsah zdroje (šířka 8190, hloubky nad 4500 mm) průměrný krok posledních 3 kroků.",
    'maxi-carbo': "Prodejní cena = ALUX Carbo dutinkový × 1,2, resp. ALUX Carbo plný × 1,2 (zaokrouhleno na celé Kč). Zóny stejné pro oba ceníky.",
    'maxi-fusion': "Fusion = jedna konstrukce (společný rám a stojny, mezi poli středový nosník). Prodejní cena = (MAXI krytina A + MAXI krytina B) / 2 × (1 + p) ve stejném rozměru; Bio = MAXI Bioclimatic DUO, Glass = MAXI Glass, Carbo 16 mm = MAXI Carbo dutinkový, Carbo 6 mm = MAXI Carbo plný, Thermo = MAXI Thermo. Chybějící hloubky (1990 vs. 2000 apod.) lineárně mezi sousedy.",
}
for sku in TITLES:
    o = old(sku)
    o['note'] = NOTES[sku] + ' ' + NOTE_TAIL
    for m in (o['variants'] if o['type'] == 'multi-matrix' else [o]):
        m['prices'] = NEW[(sku, m.get('label', ''))][2]
    wj(ROOT / 'products/maxi' / sku / 'prices.json', o)

# --- report ----------------------------------------------------------------------
wb = Workbook()
HEAD = Font(bold=True, color='FFFFFF'); HFILL = PatternFill('solid', fgColor='242424')
def sheet(name, header, rows, widths, fmt=None):
    ws = wb.create_sheet(name)
    ws.append(header)
    for c in ws[1]: c.font, c.fill = HEAD, HFILL
    for r in rows: ws.append(list(r))
    for k, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(k)].width = w
    for col, f in (fmt or {}).items():
        for c in ws[col][1:]: c.number_format = f
    ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
    return ws
wb.remove(wb.active)
# souhrn
summ = []
by_t = {}
for t, w, d, o, n in COMPARE:
    by_t.setdefault(t, []).append((w, d, o, n))
for t, cells in by_t.items():
    pct = [(n - o) / o for w, d, o, n in cells]
    mx = max(cells, key=lambda c: abs(c[3] - c[2]))
    changed = sum(1 for c in cells if c[2] != c[3])
    summ.append((t, len(cells), changed, sum(pct) / len(pct), min(pct), max(pct), f"{mx[0]} × {mx[1]}", mx[2], mx[3], mx[3] - mx[2]))
ws = sheet('Souhrn', ['Tabulka', 'Buněk', 'Změněno', 'Průměrná změna', 'Min. změna', 'Max. změna', 'Největší změna (š × h)', 'Stará', 'Nová', 'Rozdíl Kč'],
           summ, [30, 8, 10, 15, 12, 12, 22, 12, 12, 12], {'D': '0.0%', 'E': '0.0%', 'F': '0.0%', 'H': '#,##0', 'I': '#,##0', 'J': '#,##0'})
r = ws.max_row + 2
for txt in [f'Parametry: přirážka MAXI {MAXI_MARKUP:g} · příplatek DUO {DUO_SURCHARGE:g} · příplatek Fusion p = {FUSION_P:g}',
            f'Opravené zdrojové ALUX tabulky: {", ".join(NAMES[s] for s in SRC_CHANGED) or "žádná"}',
            f'Kontroly: {len(CHECKS)} buněk nesplňuje pravidla (list Kontroly)']:
    ws.cell(r, 1, txt); r += 1
sheet('Log', ['Kategorie', 'Tabulka', 'Šířka', 'Hloubka', 'Stará', 'Nová', 'Rozdíl Kč', 'Rozdíl %', 'Poznámka'],
      [(c, t, w, d, o, n, n - o, (n - o) / o if o else None, note) for c, t, w, d, o, n, note in LOG],
      [20, 30, 8, 9, 11, 11, 11, 10, 34], {'E': '#,##0', 'F': '#,##0', 'G': '#,##0', 'H': '0.0%'})
sheet('Kontroly', ['Pravidlo', 'Tabulka', 'Šířka', 'Hloubka', 'Cena', 'Detail'], CHECKS or [('vše v pořádku', '', '', '', '', '')],
      [32, 30, 8, 9, 11, 40], {'E': '#,##0'})
sheet('Srovnání', ['Tabulka', 'Šířka', 'Hloubka', 'Stará', 'Nová', 'Rozdíl Kč', 'Rozdíl %'],
      [(t, w, d, o, n, n - o, (n - o) / o) for t, w, d, o, n in COMPARE],
      [30, 8, 9, 11, 11, 11, 10], {'D': '#,##0', 'E': '#,##0', 'F': '#,##0', 'G': '0.0%'})
sheet('Dopočet zvednut', ['Zdroj', 'Šířka zdroje', 'Hloubka zdroje', 'Dopočet', 'Zvednuto na', 'Poznámka'],
      [r + ('cena by se šířkou klesla → soused + 1 Kč (bez přirážky × 1,2)',) for r in RAISED], [20, 13, 15, 12, 12, 56], {'D': '#,##0', 'E': '#,##0'})
for s in SRC_CHANGED:  # opravené ALUX tabulky, změněné buňky zvýrazněné
    W, D, P = SRC[s]; _, _, P0 = SRC_ORIG[s]
    ws = wb.create_sheet(f'{NAMES[s]} opr.'[:31])
    ws.cell(1, 1, 'hloubka ↓ šířka →').font = Font(bold=True)
    for j, w in enumerate(W): ws.cell(1, 2 + j, w).font = Font(bold=True)
    for i, d in enumerate(D):
        ws.cell(2 + i, 1, d).font = Font(bold=True)
        for j in range(len(W)):
            c = ws.cell(2 + i, 2 + j, P[i][j]); c.number_format = '#,##0'
            if P[i][j] != P0[i][j]: c.fill = PatternFill('solid', fgColor='FFD966')
    ws.freeze_panes = 'B2'
wb.save(REPORT)

print('opravené zdroje:', SRC_CHANGED)
print('zvednuto v dopočtu:', len(RAISED))
from collections import Counter
print('log:', Counter(c for c, *_ in LOG))
print('kontroly:', Counter(c for c, *_ in CHECKS))
for row in summ: print(f"  {row[0]:<30} změněno {row[2]:>5}/{row[1]:<5} průměr {row[3]*100:+6.1f} %  min {row[4]*100:+6.1f} %  max {row[5]*100:+6.1f} %  největší {row[6]} {row[7]}→{row[8]}")
