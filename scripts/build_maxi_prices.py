"""Ceny ALUX MAXI ze zdrojových ALUX ceníků (revize 29. 10. 2026).

1. anomálie ve zdrojových ALUX cenících (cena se šířkou / hloubkou neroste) → oprava v products/pergola/*/prices.json:
   malá anomálie = soused + rozdíl ze stejného místa o řádek (sloupec) výš, žádná interpolace přes schod
2. MAXI = opravený zdroj × MAXI_MARKUP
3. rozměry mimo zdroj: Glass 4600–5000 = Carbo plný, Thermo 5600–6000 krokem z celého známého rozsahu
4. Bioclimatic DUO = 1 pole + DUO_SHARE × (2 samostatné pergoly − 1 pole), z ALUX Bioclimatic, × MAXI_MARKUP
5. Fusion = DUO ze dvou krytin = (DUO A + DUO B) / 2 — kalibrace: Fusion se stejnou krytinou v obou polích = DUO té krytiny
Kontroly: monotónnost (nic se nezvedá o 1 Kč, porušení jen vypíše), MAXI = ALUX × 1,3, Fusion mezi DUO A a DUO B.
Informativně: rozměry Fusion, které jsou v čisté MAXI v zóně UNO. Report (srovnání se stávajícími cenami, log, kontroly)
→ export/ALUX-MAXI-revize-<datum>.xlsx. pricelist.xlsx ani texty nemění.

    python3 scripts/build_maxi_prices.py
    python3 scripts/build_maxi_prices.py --baseline 5b51b5f   # v reportu i srovnání s cenami z git revize
"""
import argparse, datetime, json, subprocess
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# --- parametry -------------------------------------------------------------
MAXI_MARKUP = 1.30     # MAXI = standardní ALUX × 1,30 (ceníková cena, obchodník dává slevu 0–20 %)
DUO_SHARE = 0.5        # DUO = 1 pole + podíl z rozdílu (2 samostatné pergoly − 1 pole)
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
# Carbo 16 mm: hloubky 6100–7000 (DUO - 2 stojny) extrapolací ze zdroje jako Thermo, i pravidlo 2900 / 3000
CW, CD, CP = SRC['alux-carbo-dutinkovy']
CD2, CP2 = ext_cols(CW, CD, CP, grid(6100, 7000))
for d in grid(6100, 7000):  # šířky 2700 / 2800 mají plošší krok hloubky → soused vlevo + rozdíl z hloubky 6000 (poslední známá)
    i = CD2.index(d)
    for w, ref in ((2700, 6000), (2800, 6000), (2900, 5200), (3000, 5200)):
        r, j = CD2.index(ref), CW.index(w)
        CP2[i][j] = CP2[i][j - 1] + CP2[r][j] - CP2[r][j - 1]
make('maxi-carbo-16', '', grid(2000, 8000), grid(2000, 7000),
     lambda w, d: lookup(CW, CD2, CP2, w, d) * MAXI_MARKUP, lambda w, d: d > CD[-1])
W_, D_, P_ = SRC['alux-carbo-plny']
make('maxi-carbo-6', '', grid(2000, 8000), grid(2000, 6000), lambda w, d: lookup(W_, D_, P_, w, d) * MAXI_MARKUP)
# Bioclimatic UNO
BW, BD, BP = SRC['alux-bioclimatic']
BIO_LOW_STEP = sum((r[3] - r[0]) / 3 for r in BP) / len(BP)  # průměrný krok řady 2390 → 2990 přes všechny hloubky
def bio_below(w, d):
    """ALUX Bioclimatic pod řadou lamel zdroje (1990, 2190): šířka 2390 − průměrný krok na lamelu (jeden pro celou
    tabulku, aby cena s hloubkou rostla stejně jako u 2390)."""
    return BP[BD.index(d)][0] - BIO_LOW_STEP * (BW[0] - w) / 200
UNO_LOW = [1990, 2190]
make('maxi-bioclimatic', '', UNO_LOW + BW, grid(2000, 4500),  # 1990–7990 (1990, 2190 dopočet), od 7790 UNO - 3 stojny
     lambda w, d: (bio_below(w, d) if w < BW[0] else lookup(BW, BD, BP, w, d)) * MAXI_MARKUP,
     lambda w, d: w < BW[0])
# Bioclimatic DUO = cena mezi jedním velkým polem a dvěma samostatnými pergolami (z ALUX Bioclimatic):
#   1 pole    = ALUX (šířka = Š v řadě lamel, hloubka = H)
#   2 pergoly = 2 × ALUX (šířka = H v řadě lamel, hloubka = Š / 2) — pole DUO jsou otočená o 90°, lamely dlouhé Š / 2
#   DUO = 2 pergoly − DUO_SHARE × (2 pergoly − 1 pole), × MAXI_MARKUP
#   jen kde obě varianty v ALUX existují (hloubka DUO v řadě lamel ALUX a do hloubky ALUX); jinde se dopočítá
#   přímo cena DUO průměrným krokem celé spočítané části (zvlášť pro každou šířku) — není s čím srovnat
def alux_bio(w, d):
    """ALUX Bioclimatic, šířka v řadě lamel (mimo řadu lineárně, 1990 / 2190 jako MAXI UNO), hloubka mimo mřížku
    lineárně, pod 2000 prodloužením kroku 2000 → 2100."""
    if w < BW[0]:
        c = [r[0] - BIO_LOW_STEP * (BW[0] - w) / 200 for r in BP]
    elif w in BW:
        c = [r[BW.index(w)] for r in BP]
    else:
        hi = next(k for k, x in enumerate(BW) if x > w)
        c = [r[hi - 1] + (r[hi] - r[hi - 1]) * (w - BW[hi - 1]) / (BW[hi] - BW[hi - 1]) for r in BP]
    if d in BD:
        return c[BD.index(d)]
    if d < BD[0]:
        return c[0] - (c[1] - c[0]) * (BD[0] - d) / (BD[1] - BD[0])
    hi = next(k for k, x in enumerate(BD) if x > d)
    return c[hi - 1] + (c[hi] - c[hi - 1]) * (d - BD[hi - 1]) / (BD[hi] - BD[hi - 1])
DUO_W, DUO_D = list(range(4000, 8001, 200)), list(range(1990, 5591, 200))
DUO_CALC = [d for d in DUO_D if d <= BD[-1]]  # 1990–4390: obě varianty v ALUX (1990, 2190 přes šířky MAXI UNO)
DUO_EXT_BASE = (2390, 4390)  # krok pro dopočet hloubek 4590–5590 (beze změny proti dřívějšku)
def one_field(w, d): return alux_bio(min(BW, key=lambda x: abs(x - w)), d)
def two_pergolas(w, d): return 2 * alux_bio(d, w / 2)
def duo_calc(w, d): return two_pergolas(w, d) - DUO_SHARE * (two_pergolas(w, d) - one_field(w, d))
def duo_alux(w, d):
    if d in DUO_CALC:
        return duo_calc(w, d)
    lo, hi = DUO_EXT_BASE
    step = (duo_calc(w, hi) - duo_calc(w, lo)) / (hi - lo)
    return duo_calc(w, hi) + step * (d - hi)
make('maxi-bioclimatic-duo', '', DUO_W, DUO_D, lambda w, d: duo_alux(w, d) * MAXI_MARKUP, lambda w, d: d not in DUO_CALC)

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--baseline', metavar='REF', help='git revize, se kterou se ceny MAXI v reportu ještě srovnají')
ap.add_argument('--bez-reportu', action='store_true', help='jen zapsat prices.json, report do export/ negenerovat')
ARGS = ap.parse_args()

# --- krok 5: Fusion = DUO ze dvou krytin -------------------------------------
# Stejná logika jako DUO: 2 otočené pergoly (pole A + pole B) − DUO_SHARE × (2 otočené pergoly − 1 velká pergola),
# 1 velká pergola = napůl A, napůl B. Matematicky totéž jako (DUO A + DUO B) / 2, kde DUO krytiny = hypotetické DUO
# z její čisté MAXI tabulky (Bio = MAXI Bioclimatic DUO).
def mval(key, w, d):
    """Čistá MAXI tabulka v libovolném bodě: lineárně mezi sousedy, pod minimem prodloužením prvního kroku."""
    W, D, P = NEW[key]
    def at(xs, x):
        if x in xs:
            return xs.index(x), xs.index(x), 0.0
        if x < xs[0]:
            return 0, 1, (x - xs[0]) / (xs[1] - xs[0])
        hi = next(k for k, v in enumerate(xs) if v > x)
        return hi - 1, hi, (x - xs[hi - 1]) / (xs[hi] - xs[hi - 1])
    j0, j1, tj = at(W, w); i0, i1, ti = at(D, d)
    row = lambda i: P[i][j0] + (P[i][j1] - P[i][j0]) * tj
    return row(i0) + (row(i1) - row(i0)) * ti
MAXI_OF = {'Bio': ('maxi-bioclimatic-duo', ''), 'Thermo': ('maxi-thermo', ''), 'Glass': ('maxi-glass', ''),
           'Carbo 16 mm': ('maxi-carbo-16', ''), 'Carbo 6 mm': ('maxi-carbo-6', '')}
def rotated(x, w, d):
    """1 otočená pergola krytiny x (šířka = hloubka DUO, hloubka = Š / 2); u Bio polovina MAXI DUO bez úspory nelze → None."""
    return mval(MAXI_OF[x], d, w / 2)
def duo_of(x, w, d):
    """Hypotetické DUO krytiny x (obě pole stejná). Bio = tabulka MAXI Bioclimatic DUO."""
    if x == 'Bio':
        return mval(MAXI_OF[x], w, d)
    two = 2 * rotated(x, w, d)
    return two - DUO_SHARE * (two - mval(MAXI_OF[x], w, d))
FUSION_W_CALC = 4000  # pod šířkou 4000 je pole užší než 2000 mm a není s čím srovnat → dopočet krokem
def fusion(a, b, W):
    def f(w, d):
        if w >= FUSION_W_CALC:
            return (duo_of(a, w, d) + duo_of(b, w, d)) / 2
        lo, hi = FUSION_W_CALC, W[-1]
        flo, fhi = f(lo, d), f(hi, d)
        return flo - (fhi - flo) / (hi - lo) * (lo - w)
    return f
FUSION = ['Bio - Glass', 'Bio - Carbo 16 mm', 'Bio - Carbo 6 mm', 'Thermo - Glass', 'Thermo - Carbo 16 mm', 'Thermo - Carbo 6 mm']
# všech 6 kombinací stejná mřížka jako Bio DUO: šířky 4000–8000, hloubky 1990–4990 (řada lamel), obojí po 200 mm
FUSION_GRID = {True: (DUO_W, list(range(1990, 4991, 200))), False: (DUO_W, list(range(1990, 4991, 200)))}
for lab in FUSION:
    a, b = lab.split(' - ')
    W, D = FUSION_GRID[lab.startswith('Bio')]
    make('maxi-fusion', lab, W, D, fusion(a, b, W), lambda w, d: w < FUSION_W_CALC)

# kalibrace: hypotetická Fusion se stejnou krytinou v obou polích = DUO té krytiny (± CALIB_TOL)
CALIB = []  # (tabulka, buněk, max. odchylka)
for x, key in MAXI_OF.items():
    W, D = FUSION_GRID[x == 'Bio']
    W = [w for w in W if w >= FUSION_W_CALC]
    dev = [(w, d, rnd(fusion(x, x, W)(w, d)), rnd(duo_of(x, w, d))) for d in D for w in W]
    bad = [r for r in dev if abs(r[2] - r[3]) > CALIB_TOL]
    if bad:
        raise SystemExit(f'kalibrace {x} / {x} nesedí: ' + '; '.join(f'{w} × {d}: {h} ≠ {m}' for w, d, h, m in bad[:20]))
    CALIB.append((f'Fusion {x} / {x}', f'DUO {x}' + (' (MAXI Bioclimatic DUO)' if x == 'Bio' else ' (hypotetické)'),
                  len(dev), max(abs(h - m) for _, _, h, m in dev)))

# --- log MAXI změn -------------------------------------------------------------
TITLES = {'maxi-thermo': 'MAXI Thermo', 'maxi-glass': 'MAXI Glass', 'maxi-bioclimatic': 'MAXI Bioclimatic UNO',
          'maxi-bioclimatic-duo': 'MAXI Bioclimatic DUO', 'maxi-carbo-16': 'MAXI Carbo 16 mm', 'maxi-carbo-6': 'MAXI Carbo 6 mm',
          'maxi-fusion': 'MAXI Fusion'}
def title(key):
    sku, lab = key
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
                cat = 'DUO z ALUX Bioclimatic'
            elif key[0] == 'maxi-glass' and d > 4500:
                cat = 'extrapolace'
            else:
                cat = None if o == n else 'přepočet ze zdroje'
            if cat and o != n:
                note = {'extrapolace': 'mimo rozsah zdroje', 'DUO z ALUX Bioclimatic': f'1 pole + {DUO_SHARE:g} × rozdílu', 'Fusion': 'DUO ze 2 krytin',
                        'přepočet ze zdroje': 'opravený zdroj × 1,3'}[cat]
                if key[0] == 'maxi-glass' and d > 4500: note = 'ALUX Carbo plný × 1,3'
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
# 2: MAXI = opravený ALUX × 1,3 tam, kde zdroj existuje
for key, s in ((('maxi-thermo', ''), 'alux-thermo'), (('maxi-glass', ''), 'alux-glass'), (('maxi-bioclimatic', ''), 'alux-bioclimatic'),
               (('maxi-carbo-16', ''), 'alux-carbo-dutinkovy'), (('maxi-carbo-6', ''), 'alux-carbo-plny')):
    W, D, P = NEW[key]; SW, SD, SP = SRC[s]
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if d in SD and w in SW and P[i][j] != rnd(lookup(SW, SD, SP, w, d) * MAXI_MARKUP):
                CHECKS.append(('2 MAXI = ALUX × 1,3', title(key), w, d, P[i][j], f'zdroj × 1,3 = {rnd(lookup(SW, SD, SP, w, d) * MAXI_MARKUP)}'))
# 3: Fusion mezi DUO A a DUO B
for lab in FUSION:
    W, D, P = NEW[('maxi-fusion', lab)]
    a, b = lab.split(' - ')
    for i, d in enumerate(D):
        for j, w in enumerate(W):
            if w < FUSION_W_CALC:
                continue
            va, vb = duo_of(a, w, d), duo_of(b, w, d)
            if not min(va, vb) - 0.5 <= P[i][j] <= max(va, vb) + 0.5:
                CHECKS.append(('3 Fusion mezi DUO A a DUO B', f'MAXI Fusion {lab}', w, d, P[i][j], f'{rnd(min(va, vb))} – {rnd(max(va, vb))}'))

# informativně: přechod MAXI UNO hloubka 4200 → DUO hloubka 4390 (šířka DUO vs. UNO o 10 mm užší v řadě lamel)
DUO_P = NEW[('maxi-bioclimatic-duo', '')]
UW, UD, UP = NEW[('maxi-bioclimatic', '')]
def duo(w, d): return DUO_P[2][DUO_P[1].index(d)][DUO_P[0].index(w)]
UNO_DUO_EDGE = [(d, UP[UD.index(d)][-1], duo(8000, d - 10), duo(8000, d - 10) / UP[UD.index(d)][-1] - 1)
                for d in range(2000, 4201, 200)]  # UNO 7990 × H vs. DUO 8000 × (H − 10)
TRANSITION = [(w, UP[UD.index(4200)][UW.index(w - 10)], duo(w, 4390), duo(w, 4390) / UP[UD.index(4200)][UW.index(w - 10)]) for w in DUO_W if w - 10 in UW]

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
NOTE_TAIL = f"Náklad 58 % (cost_percent). Parametry: přirážka MAXI {MAXI_MARKUP:g}, podíl DUO {DUO_SHARE:g}."
NOTES = {
    'maxi-thermo': "Prodejní cena = ALUX Thermo × 1,3 (zaokrouhleno na celé Kč). Hloubky 5600–6000 mm dopočítány průměrným krokem celého rozsahu hloubek zdroje (zvlášť pro každý sloupec); šířka 2900 / 3000 od hloubky 5400 = šířka 2800 + rozdíl z hloubky 5200.",
    'maxi-glass': "Prodejní cena = ALUX Glass × 1,3 (zaokrouhleno na celé Kč). Hloubky 4600–5000 mm = ALUX Carbo plný × 1,3 (Glass = Carbo plný).",
    'maxi-bioclimatic': "UNO. Prodejní cena = ALUX Bioclimatic × 1,3 (zaokrouhleno na celé Kč). Šířky 1990 a 2190 mm (pod řadou lamel ALUX) = šířka 2390 − průměrný krok řady 2390 → 2990 (průměr přes všechny hloubky) na lamelu.",
    'maxi-bioclimatic-duo': "DUO = zdvojená střecha: 2 pole otočená o 90° se společným rámem, středovým nosníkem a 2 motory. Prodejní cena = [2 otočené pergoly − 0,5 × (2 otočené pergoly − 1 velká pergola stejného celkového rozměru)] × 1,3 z ALUX Bioclimatic, zaokrouhleno na celé Kč; 2 otočené pergoly = 2 × ALUX Bioclimatic (šířka = hloubka DUO v řadě lamel, hloubka = šířka DUO / 2). Hloubky 1990 a 2190 mm: otočené pergoly šířky 1990 / 2190 jako MAXI Bioclimatic UNO. Hloubky 4590–5590 mm (1 velká pergola mimo rozsah ALUX, není s čím srovnat) dopočítány průměrným krokem spočítané části 2390–4390 mm, zvlášť pro každou šířku.",
    'maxi-carbo-16': "Prodejní cena = ALUX Carbo dutinkový × 1,3 (zaokrouhleno na celé Kč). Hloubky 6100–7000 mm dopočítány průměrným krokem celého rozsahu hloubek zdroje (zvlášť pro každý sloupec); šířka 2700 / 2800 = soused vlevo + rozdíl z hloubky 6000, šířka 2900 / 3000 = šířka 2800 + rozdíl z hloubky 5200.",
    'maxi-carbo-6': "Prodejní cena = ALUX Carbo plný × 1,3 (zaokrouhleno na celé Kč).",
    'maxi-fusion': "Fusion = DUO se dvěma různými krytinami, počítá se stejně jako DUO: prodejní cena = 2 otočené pergoly (pole A + pole B) − 0,5 × (2 otočené pergoly − 1 velká pergola napůl A a napůl B), tedy (DUO A + DUO B) / 2, zaokrouhleno na celé Kč. DUO krytiny = 2 otočené pergoly − 0,5 × rozdíl proti 1 velké pergole z čisté MAXI tabulky (MAXI = ALUX × 1,3); Bio = MAXI Bioclimatic DUO. Kalibrace: stejná krytina v obou polích = DUO té krytiny. Všech 6 kombinací má stejnou mřížku: šířky 4000–8000 mm, hloubky 1990–4990 mm, obojí po 200 mm.",
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
for txt in [f'Parametry: přirážka MAXI {MAXI_MARKUP:g} · podíl DUO {DUO_SHARE:g} · Fusion = DUO ze 2 krytin',
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
sheet('DUO výpočet', ['Šířka DUO', 'Hloubka DUO', '2 pergoly ALUX', '1 pole ALUX', 'Rozdíl', 'Rozdíl %', 'DUO ALUX', 'MAXI DUO (× 1,3)'],
      [(w, d, rnd(two_pergolas(w, d)), rnd(one_field(w, d)), rnd(two_pergolas(w, d) - one_field(w, d)),
        two_pergolas(w, d) / one_field(w, d) - 1, rnd(duo_alux(w, d)), duo(w, d)) if d in DUO_CALC else
       (w, d, None, None, None, None, rnd(duo_alux(w, d)), duo(w, d)) for d in DUO_D for w in DUO_W],
      [11, 12, 15, 13, 11, 10, 12, 16], {'C': '#,##0', 'D': '#,##0', 'E': '#,##0', 'F': '0.0%', 'G': '#,##0', 'H': '#,##0'})
sheet('UNO 7990 vs DUO 8000', ['Hloubka UNO', 'UNO 7990 × H', 'DUO 8000 × (H − 10)', 'Rozdíl Kč', 'Rozdíl %', 'Mimo +5 až +20 %'],
      [(d, u, du, du - u, r, '!' if not 0.05 <= r <= 0.20 else '') for d, u, du, r in UNO_DUO_EDGE], [12, 14, 20, 12, 10, 16],
      {'B': '#,##0', 'C': '#,##0', 'D': '#,##0', 'E': '0.0%'})
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
if not ARGS.bez_reportu:
    wb.save(REPORT)

print('opravené zdroje:', SRC_CHANGED)
print('UNO 7990 vs DUO 8000:', [(d, u, du, f'{r * 100:+.1f} %') for d, u, du, r in UNO_DUO_EDGE])
print('přechod UNO 4200 → DUO 4390:', [(w, f'{(r - 1) * 100:+.1f} %') for w, _, _, r in TRANSITION])
from collections import Counter
print('log:', Counter(c for c, *_ in LOG))
print('kalibrace:', CALIB)
print('Fusion v UNO:', UNO_INFO)
print('kontroly:', Counter(c for c, *_ in CHECKS))
for row in summ: print(f"  {row[0]:<30} změněno {row[2]:>5}/{row[1]:<5} průměr {row[3]*100:+6.1f} %  min {row[4]*100:+6.1f} %  max {row[5]*100:+6.1f} %  největší {row[6]} {row[7]}→{row[8]}")
