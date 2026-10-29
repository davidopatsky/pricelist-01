"""Ceny ALUX MAXI ze zdrojových ALUX ceníků (revize 29. 10. 2026).

1. anomálie ve zdrojových ALUX cenících (cena se šířkou / hloubkou neroste) → oprava v products/pergola/*/prices.json:
   malá anomálie = soused + rozdíl ze stejného místa o řádek (sloupec) výš, žádná interpolace přes schod
2. MAXI = opravený zdroj × MAXI_MARKUP
3. rozměry mimo zdroj: Glass 4600–5000 = Carbo plný, Thermo 5600–6000 krokem z celého známého rozsahu
4. Bioclimatic DUO = 2 × MAXI UNO (šířka = H, hloubka = Š/2) × k; k = medián z překryvu UNO a DUO tak, aby DUO / UNO = DUO_UNO_RATIO
5. Fusion = (MAXI A + MAXI B) / 2 — kalibrace: Fusion se stejnou krytinou v obou polích = čistá MAXI (jinak skript skončí)
Kontroly: monotónnost (nic se nezvedá o 1 Kč, porušení jen vypíše), MAXI = ALUX × 1,2, Fusion mezi čistou MAXI A a B, poměr DUO / UNO.
Informativně: rozměry Fusion, které jsou v čisté MAXI v zóně UNO. Report (srovnání se stávajícími cenami, log, kontroly)
→ export/ALUX-MAXI-revize-<datum>.xlsx. pricelist.xlsx ani texty nemění.

    python3 scripts/build_maxi_prices.py
    python3 scripts/build_maxi_prices.py --baseline 5b51b5f   # v reportu i srovnání s cenami z git revize
"""
import argparse, datetime, json, statistics, subprocess
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# --- parametry -------------------------------------------------------------
MAXI_MARKUP = 1.20     # MAXI = standardní ALUX × 1,20
DUO_UNO_RATIO = 1.117  # cílový poměr DUO / UNO stejného rozměru (UNO 300 000 → DUO cca 335 000)
K_RANGE = (0.85, 1.00) # koeficient úspory k mimo rozsah → skript skončí
DUO_RATIO_OK = (1.05, 1.20)  # DUO / UNO mimo rozmezí → výpis
CALIB_TOL = 2000       # kalibrace Fusion: tolerance v Kč
# zadání: šířka 3000 (a 2900 mezi) v hloubkách od 5400 = šířka 2800 + rozdíl 2800 → 3000 z hloubky 5200
REF_ROW = {s: {2900: 5200, 3000: 5200} for s in ('alux-thermo', 'alux-carbo-dutinkovy', 'alux-trapez')}

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / 'export' / f'ALUX-MAXI-revize-{datetime.date.today().isoformat()}.xlsx'
SOURCES = ['alux-bioclimatic', 'alux-thermo', 'alux-glass', 'alux-carbo-dutinkovy', 'alux-carbo-plny', 'alux-trapez']
NAMES = {'alux-bioclimatic': 'ALUX Bioclimatic', 'alux-thermo': 'ALUX Thermo', 'alux-glass': 'ALUX Glass',
         'alux-carbo-dutinkovy': 'ALUX Carbo dutinkový', 'alux-carbo-plny': 'ALUX Carbo plný', 'alux-trapez': 'ALUX Trapez'}

def rnd(x): return int(Decimal(str(x)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
def rj(p): return json.loads(p.read_text(encoding='utf-8'))
def wj(p, o): p.write_text(json.dumps(o, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

LOG = []  # (kategorie, tabulka, šířka, hloubka, stará, nová, poznámka)

# --- krok 1: anomálie ve zdroji ---------------------------------------------
def anomalies(P):
    return sum(1 for r in P for j in range(1, len(r)) if r[j] <= r[j - 1]) + \
           sum(1 for i in range(1, len(P)) for j in range(len(P[0])) if P[i][j] <= P[i - 1][j])

def fix_table(P, W, D, ref_row=None):
    """Krok 1: buňka, kde cena se šířkou (hloubkou) neroste, = soused vlevo (nad ní) + rozdíl ze stejného místa
    v nejbližším platném řádku výš (sloupci vlevo); ref_row {šířka: hloubka} určí řádek pevně. Prochází se po řádcích,
    takže navazující buňky se srovnávají už s opravenými. Plochý začátek řádku / sloupce = minimální rozměr, platí."""
    P = [list(r) for r in P]
    ref_row = ref_row or {}
    for i in range(len(D)):
        for j in range(len(W)):
            cand = []
            if j and P[i][j] <= P[i][j - 1] and any(P[i][k] != P[i][0] for k in range(j + 1)):
                if W[j] in ref_row and D[i] > ref_row[W[j]]:
                    r = D.index(ref_row[W[j]])
                else:
                    r = next((k for k in range(i - 1, -1, -1) if P[k][j] > P[k][j - 1]), None)
                if r is not None:
                    cand.append(P[i][j - 1] + P[r][j] - P[r][j - 1])
            if i and P[i][j] <= P[i - 1][j] and any(P[k][j] != P[0][j] for k in range(i + 1)):
                c = next((k for k in range(j - 1, -1, -1) if P[i][k] > P[i - 1][k]), None)
                if c is not None:
                    cand.append(P[i - 1][j] + P[i][c] - P[i - 1][c])
            if cand:
                P[i][j] = max(cand)
    return P

SRC, SRC_ORIG, SRC_CHANGED = {}, {}, []
for s in SOURCES:
    p = rj(ROOT / 'products/pergola' / s / 'prices.json')
    W, D, P0 = p['horizontal_values'], p['vertical_values'], p['prices']
    P = fix_table(P0, W, D, REF_ROW.get(s))
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if P[i][j] != P0[i][j]:
                LOG.append(('anomálie', NAMES[s], w, d, P0[i][j], P[i][j], 'zdroj ALUX'))
    if P != P0:
        SRC_CHANGED.append(s)
    SRC[s], SRC_ORIG[s] = (W, D, P), (W, D, P0)

# --- rozšířené zdroje (extrapolace krokem z celého známého rozsahu) -------------
def ext_cols(W, D, P, new_D):
    """Přidá hloubky new_D: v každém sloupci průměrný krok celého známého rozsahu hloubek."""
    rows = [list(r) for r in P]
    for d in new_D:
        rows.append([P[-1][j] + (P[-1][j] - P[0][j]) / (D[-1] - D[0]) * (d - D[-1]) for j in range(len(W))])
    return list(D) + list(new_D), rows

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
TD2, TP2 = ext_cols(TW, TD, TP, grid(5600, 6000))
for d in grid(5600, 6000):  # zadání: i v dopočtu šířka 2900 / 3000 = soused vlevo + rozdíl z hloubky 5200
    r, i = TD2.index(5200), TD2.index(d)
    for w in (2900, 3000):
        j = TW.index(w)
        TP2[i][j] = TP2[i][j - 1] + TP2[r][j] - TP2[r][j - 1]
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
# Bioclimatic DUO = dvě pole UNO otočená o 90°: řada lamel UNO (šířka) = hloubka DUO, rozpětí pole = Š / 2
UW, UD, UP = NEW[('maxi-bioclimatic', '')]
def uno(w, d):
    """MAXI UNO; šířka pod řadou (1990, 2190) průměrným krokem řady 2390 → 2990, mimo mřížku lineárně."""
    def col(w):
        if w < UW[0]:
            return [r[0] - (r[3] - r[0]) / 3 * (UW[0] - w) / 200 for r in UP]
        if w in UW:
            return [r[UW.index(w)] for r in UP]
        hi = next(k for k, x in enumerate(UW) if x > w)
        t = (w - UW[hi - 1]) / (UW[hi] - UW[hi - 1])
        return [r[hi - 1] + (r[hi] - r[hi - 1]) * t for r in UP]
    c = col(w)
    if d in UD:
        return c[UD.index(d)]
    hi = next(k for k, x in enumerate(UD) if x > d)
    return c[hi - 1] + (c[hi] - c[hi - 1]) * (d - UD[hi - 1]) / (UD[hi] - UD[hi - 1])
DUO_W, DUO_D = list(range(4000, 8001, 200)), list(range(1990, 5591, 200))
def two_fields(w, d): return 2 * uno(d, w / 2)
OVERLAP = [(w, d) for d in DUO_D for w in DUO_W if w <= UW[-1] and UW[0] <= d <= UD[-1]]
K_CELLS = [(w, d, DUO_UNO_RATIO * uno(w, d) / two_fields(w, d)) for w, d in OVERLAP]
K = statistics.median(k for *_, k in K_CELLS)
if not K_RANGE[0] <= K <= K_RANGE[1]:
    raise SystemExit(f'k = {K:.4f} mimo {K_RANGE}: DUO (2 pole) vs. UNO stejného rozměru neodpovídá zadání — '
                     f'min {min(k for *_, k in K_CELLS):.4f}, max {max(k for *_, k in K_CELLS):.4f}')
make('maxi-bioclimatic-duo', '', DUO_W, DUO_D, lambda w, d: two_fields(w, d) * K, lambda w, d: d < UW[0])

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--baseline', metavar='REF', help='git revize, se kterou se ceny MAXI v reportu ještě srovnají')
ARGS = ap.parse_args()

# --- krok 5: Fusion = [MAXI_A + MAXI_B] / 2 -----------------------------------
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
    W, D = (DUO_W, list(range(1990, 4991, 200))) if lab.startswith('Bio') else (grid(2000, 8000), grid(2000, 5000))
    make('maxi-fusion', lab, W, D, lambda w, d, a=a, b=b: (interp(a, w, d) + interp(b, w, d)) / 2)

# kalibrace: hypotetická Fusion se stejnou krytinou v obou polích = čistá MAXI stejného rozměru (± CALIB_TOL)
CALIB = []  # (tabulka, buněk, max. odchylka)
for x, key in MAXI_OF.items():
    W, D = (DUO_W, list(range(1990, 4991, 200))) if x == 'Bio' else (grid(2000, 8000), grid(2000, 5000))
    dev = [(w, d, rnd((interp(key, w, d) + interp(key, w, d)) / 2), interp(key, w, d)) for d in D for w in W]
    bad = [r for r in dev if abs(r[2] - r[3]) > CALIB_TOL]
    if bad:
        raise SystemExit(f'kalibrace {x} / {x} nesedí: ' + '; '.join(f'{w} × {d}: {h} ≠ {m}' for w, d, h, m in bad[:20]))
    CALIB.append((f'Fusion {x} / {x}', ' '.join(filter(None, key)), len(dev), max(abs(h - m) for _, _, h, m in dev)))

# --- log MAXI změn -------------------------------------------------------------
TITLES = {'maxi-thermo': 'MAXI Thermo', 'maxi-glass': 'MAXI Glass', 'maxi-bioclimatic': 'MAXI Bioclimatic UNO',
          'maxi-bioclimatic-duo': 'MAXI Bioclimatic DUO', 'maxi-carbo': 'MAXI Carbo', 'maxi-fusion': 'MAXI Fusion'}
def title(key):
    sku, lab = key
    if sku == 'maxi-carbo': return f"MAXI Carbo {lab.split()[0]}"
    if sku == 'maxi-fusion': return f"MAXI Fusion {lab}"
    return TITLES[sku]
def cells(o, key):
    """{(š, h): cena} matice produktu (u multi-matrix varianty key[1])."""
    if o['type'] == 'multi-matrix':
        o = next(v for v in o['variants'] if v['label'] == key[1])
    return {(w, d): o['prices'][i][j] for i, d in enumerate(o['vertical_values']) for j, w in enumerate(o['horizontal_values'])}
def base_cells(key):
    """Matice z git revize --baseline, jinak {}."""
    if not ARGS.baseline:
        return {}
    o = json.loads(subprocess.run(['git', '-C', str(ROOT), 'show', f'{ARGS.baseline}:products/maxi/{key[0]}/prices.json'],
                                  capture_output=True, text=True, check=True).stdout)
    return cells(o, key)
COMPARE = []  # (tabulka, w, d, stará, nová, baseline) — jen rozměry, které byly i ve staré mřížce
for key, (W, D, P) in NEW.items():
    OC, BC = cells(old(key[0]), key), base_cells(key)
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            o, n = OC.get((w, d)), P[i][j]
            if o is None:
                continue
            COMPARE.append((title(key), w, d, o, n, BC.get((w, d))))
            if key[0] == 'maxi-fusion':
                cat = 'Fusion'
            elif (w, d) in EXTRA[key]:
                cat = 'extrapolace'
            elif key[0] == 'maxi-bioclimatic-duo':
                cat = 'DUO = 2 × UNO × k'
            elif key[0] == 'maxi-glass' and d > 4500:
                cat = 'extrapolace'
            else:
                cat = None if o == n else 'přepočet ze zdroje'
            if cat and o != n:
                note = {'extrapolace': 'mimo rozsah zdroje', 'DUO = 2 × UNO × k': f'k = {K:.4f}', 'Fusion': '(A + B) / 2',
                        'přepočet ze zdroje': 'opravený zdroj × 1,2'}[cat]
                if key[0] == 'maxi-glass' and d > 4500: note = 'ALUX Carbo plný × 1,2'
                LOG.append((cat, title(key), w, d, o, n, note))

# --- kontroly ------------------------------------------------------------------
CHECKS = []  # (pravidlo, tabulka, w, d, hodnota, detail)
for s_ in SOURCES:  # zbylé anomálie ve zdroji (pravidlo kroku 1 je neopravilo) → ruční kontrola
    W, D, P = SRC[s_]
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if j and P[i][j] <= P[i][j - 1] and any(P[i][k] != P[i][0] for k in range(j + 1)):
                CHECKS.append(('0 zdroj ALUX (šířka)', NAMES[s_], w, d, P[i][j], f'≤ {P[i][j-1]} u šířky {W[j-1]}'))
            if i and P[i][j] <= P[i - 1][j] and any(P[k][j] != P[0][j] for k in range(i + 1)):
                CHECKS.append(('0 zdroj ALUX (hloubka)', NAMES[s_], w, d, P[i][j], f'≤ {P[i-1][j]} u hloubky {D[i-1]}'))
for key, (W, D, P) in NEW.items():
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if j and P[i][j] <= P[i][j - 1]:
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
            if not min(va, vb) - 0.5 <= P[i][j] <= max(va, vb) + 0.5:
                CHECKS.append(('3 Fusion mezi čistou MAXI A a B', f'MAXI Fusion {lab}', w, d, P[i][j], f'{rnd(min(va, vb))} – {rnd(max(va, vb))}'))

# 5: poměr DUO / UNO stejného rozměru (překryv), přechod UNO 4200 → DUO 4390
DUO_P = NEW[('maxi-bioclimatic-duo', '')]
def duo(w, d): return DUO_P[2][DUO_P[1].index(d)][DUO_P[0].index(w)]
RATIO = [(w, d, rnd(uno(w, d)), duo(w, d), duo(w, d) / uno(w, d)) for w, d in OVERLAP]
for w, d, u, du, r in RATIO:
    if not DUO_RATIO_OK[0] <= r <= DUO_RATIO_OK[1]:
        CHECKS.append(('5 DUO / UNO mimo +5 až +20 %', 'MAXI Bioclimatic DUO', w, d, du, f'UNO {u} → {(r - 1) * 100:+.1f} %'))
TRANSITION = [(w, rnd(uno(w, UD[-1])), duo(w, 4390), duo(w, 4390) / uno(w, UD[-1])) for w in DUO_W if w <= UW[-1]]

# informativně: rozměry Fusion, které jsou v čisté MAXI (Thermo, Glass, Carbo) v zóně UNO — ceny se neupravují
def zone_label_at(sku, w, d):
    for z in rj(ROOT / 'products/maxi' / sku / 'metadata.json')['support_zones']:
        if ('sirka_od' in z and w < z['sirka_od']) or ('hloubka_od' in z and d < z['hloubka_od']):
            continue
        return z['popisek']
UNO_INFO = []  # (kombinace, krytina, max. šířka, max. hloubka, buněk)
for lab in FUSION:
    W, D, _ = NEW[('maxi-fusion', lab)]
    for x in lab.split(' - '):
        sku = MAXI_OF[x][0]
        cells = [(w, d) for d in D for w in W if zone_label_at(sku, w, d).startswith('UNO')]
        if cells:
            UNO_INFO.append((f'Fusion {lab}', f'{x} ({title(MAXI_OF[x])})', max(w for w, _ in cells), max(d for _, d in cells), len(cells), len(W) * len(D)))

# --- zápis prices.json ---------------------------------------------------------
for s in SRC_CHANGED:
    p = rj(ROOT / 'products/pergola' / s / 'prices.json')
    p['prices'] = SRC[s][2]
    wj(ROOT / 'products/pergola' / s / 'prices.json', p)
NOTE_TAIL = f"Náklad 58 % (cost_percent). Parametry: přirážka MAXI {MAXI_MARKUP:g}, poměr DUO / UNO {DUO_UNO_RATIO:g}, k = {K:.4f}."
NOTES = {
    'maxi-thermo': "Prodejní cena = ALUX Thermo × 1,2 (zaokrouhleno na celé Kč). Hloubky 5600–6000 mm dopočítány průměrným krokem celého rozsahu hloubek zdroje (zvlášť pro každý sloupec); šířka 2900 / 3000 od hloubky 5400 = šířka 2800 + rozdíl z hloubky 5200.",
    'maxi-glass': "Prodejní cena = ALUX Glass × 1,2 (zaokrouhleno na celé Kč). Hloubky 4600–5000 mm = ALUX Carbo plný × 1,2 (Glass = Carbo plný).",
    'maxi-bioclimatic': "UNO. Prodejní cena = ALUX Bioclimatic × 1,2 (zaokrouhleno na celé Kč).",
    'maxi-bioclimatic-duo': "DUO = dvě pole UNO otočená o 90° se společným rámem a středovým nosníkem: prodejní cena = 2 × MAXI Bioclimatic UNO (šířka UNO = hloubka DUO, hloubka UNO = šířka DUO / 2) × k, zaokrouhleno na celé Kč. Koeficient úspory k = medián přes rozměry, kde existuje UNO i DUO, aby DUO stálo o 11,7 % víc než UNO stejného rozměru. Hloubky 1990 a 2190 (pod řadou UNO) průměrným krokem řady 2390 → 2990.",
    'maxi-carbo': "Prodejní cena = ALUX Carbo dutinkový × 1,2, resp. ALUX Carbo plný × 1,2 (zaokrouhleno na celé Kč). Zóny stejné pro oba ceníky.",
    'maxi-fusion': "Fusion = jedna konstrukce (společný rám a stojny, mezi poli středový nosník). Každé pole nese polovinu ceny své čisté MAXI: prodejní cena = (MAXI krytina A + MAXI krytina B) / 2 ve stejném rozměru, zaokrouhleno na celé Kč (kalibrace: stejná krytina v obou polích = čistá MAXI); Bio = MAXI Bioclimatic DUO (verze s Bio od šířky 4000 po 200 mm jako DUO), Glass = MAXI Glass, Carbo 16 mm = MAXI Carbo dutinkový, Carbo 6 mm = MAXI Carbo plný, Thermo = MAXI Thermo. Chybějící hloubky (1990 vs. 2000 apod.) lineárně mezi sousedy.",
}
for sku in TITLES:
    o = old(sku)
    o['note'] = NOTES[sku] + ' ' + NOTE_TAIL
    for m in (o['variants'] if o['type'] == 'multi-matrix' else [o]):
        m['horizontal_values'], m['vertical_values'], m['prices'] = NEW[(sku, m.get('label', ''))]
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
for t, w, d, o, n, b in COMPARE:
    by_t.setdefault(t, []).append((w, d, o, n, b))
for t, cells in by_t.items():
    pct = [(n - o) / o for w, d, o, n, b in cells]
    mx = max(cells, key=lambda c: abs(c[3] - c[2]))
    changed = sum(1 for c in cells if c[2] != c[3])
    bpct = [(n - b) / b for w, d, o, n, b in cells if b]
    summ.append((t, len(cells), changed, sum(pct) / len(pct), min(pct), max(pct), f"{mx[0]} × {mx[1]}", mx[2], mx[3], mx[3] - mx[2],
                 sum(bpct) / len(bpct) if bpct else None))
ws = sheet('Souhrn', ['Tabulka', 'Buněk', 'Změněno', 'Průměrná změna', 'Min. změna', 'Max. změna', 'Největší změna (š × h)', 'Stará', 'Nová', 'Rozdíl Kč',
                      f'Průměr proti {ARGS.baseline}' if ARGS.baseline else ''],
           summ, [30, 8, 10, 15, 12, 12, 22, 12, 12, 12, 18], {'D': '0.0%', 'E': '0.0%', 'F': '0.0%', 'H': '#,##0', 'I': '#,##0', 'J': '#,##0', 'K': '0.0%'})
r = ws.max_row + 2
for txt in [f'Parametry: přirážka MAXI {MAXI_MARKUP:g} · poměr DUO / UNO {DUO_UNO_RATIO:g} · k = {K:.4f} · Fusion = (A + B) / 2',
            f'Opravené zdrojové ALUX tabulky: {", ".join(NAMES[s] for s in SRC_CHANGED) or "žádná"}',
            f'Kontroly: {len(CHECKS)} buněk nesplňuje pravidla (list Kontroly)']:
    ws.cell(r, 1, txt); r += 1
sheet('Log', ['Kategorie', 'Tabulka', 'Šířka', 'Hloubka', 'Stará', 'Nová', 'Rozdíl Kč', 'Rozdíl %', 'Poznámka'],
      [(c, t, w, d, o, n, n - o, (n - o) / o if o else None, note) for c, t, w, d, o, n, note in LOG],
      [20, 30, 8, 9, 11, 11, 11, 10, 34], {'E': '#,##0', 'F': '#,##0', 'G': '#,##0', 'H': '0.0%'})
sheet('Kontroly', ['Pravidlo', 'Tabulka', 'Šířka', 'Hloubka', 'Cena', 'Detail'], CHECKS or [('vše v pořádku', '', '', '', '', '')],
      [32, 30, 8, 9, 11, 40], {'E': '#,##0'})
sheet('Srovnání', ['Tabulka', 'Šířka', 'Hloubka', 'Stará', 'Nová', 'Rozdíl Kč', 'Rozdíl %'] +
      ([f'Cena {ARGS.baseline}', f'Rozdíl Kč proti {ARGS.baseline}', f'Rozdíl % proti {ARGS.baseline}'] if ARGS.baseline else []),
      [(t, w, d, o, n, n - o, (n - o) / o) + ((b, n - b if b else None, (n - b) / b if b else None) if ARGS.baseline else ())
       for t, w, d, o, n, b in COMPARE],
      [30, 8, 9, 11, 11, 11, 10, 13, 16, 16], {'D': '#,##0', 'E': '#,##0', 'F': '#,##0', 'G': '0.0%', 'H': '#,##0', 'I': '#,##0', 'J': '0.0%'})
sheet('Kalibrace Fusion', ['Hypotetická Fusion', 'Musí se rovnat', 'Buněk', 'Max. odchylka Kč', 'Výsledek'],
      [c + (f'shoda (±{CALIB_TOL} Kč)',) for c in CALIB], [24, 34, 8, 16, 16])
sheet('Fusion v zóně UNO', ['Kombinace', 'Krytina (čistá MAXI)', 'UNO do šířky', 'UNO do hloubky', 'Buněk v UNO', 'Buněk celkem'],
      UNO_INFO, [28, 34, 13, 15, 13, 13])
ks = [k for *_, k in K_CELLS]
ws = sheet('Koeficient k', ['Šířka DUO', 'Hloubka DUO', 'MAXI UNO (Š × H)', '2 × UNO (š = H, h = Š/2)', 'k buňky'],
           [(w, d, rnd(uno(w, d)), rnd(two_fields(w, d)), k) for w, d, k in K_CELLS], [11, 12, 17, 24, 10],
           {'C': '#,##0', 'D': '#,##0', 'E': '0.0000'})
ws.cell(1, 7, f'k = medián {K:.4f} · min {min(ks):.4f} · max {max(ks):.4f} · buněk {len(ks)} · cílový poměr {DUO_UNO_RATIO:g}')
sheet('Poměr DUO - UNO', ['Šířka', 'Hloubka', 'MAXI UNO', 'MAXI DUO', 'DUO / UNO'], RATIO, [9, 9, 12, 12, 11],
      {'C': '#,##0', 'D': '#,##0', 'E': '0.0%'})
sheet('Přechod UNO-DUO', ['Šířka', 'UNO hloubka 4200', 'DUO hloubka 4390', 'DUO / UNO'], TRANSITION, [9, 17, 17, 11],
      {'B': '#,##0', 'C': '#,##0', 'D': '0.0%'})
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
print(f'k = {K:.4f} (min {min(ks):.4f}, max {max(ks):.4f}, {len(ks)} buněk)')
print('přechod UNO 4200 → DUO 4390:', [(w, f'{(r - 1) * 100:+.1f} %') for w, _, _, r in TRANSITION])
from collections import Counter
print('log:', Counter(c for c, *_ in LOG))
print('kalibrace:', CALIB)
print('Fusion v UNO:', UNO_INFO)
print('kontroly:', Counter(c for c, *_ in CHECKS))
for row in summ: print(f"  {row[0]:<30} změněno {row[2]:>5}/{row[1]:<5} průměr {row[3]*100:+6.1f} %  min {row[4]*100:+6.1f} %  max {row[5]*100:+6.1f} %  největší {row[6]} {row[7]}→{row[8]}")
