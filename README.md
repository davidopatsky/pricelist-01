# Pricelist (ALUX)

Canonical pricelist for every ALUX product, accessory, and surcharge.

- **`pricelist.xlsx`** — canonical edit surface. Opened in Numbers/Excel. **NOT in git.**
- **`pricelist.json`** — derived, flat 14-field array. **IN git.** Apps consume via raw GitHub URL.
- **`products/<category>/<sku>/`** — per-product folder with `knowledge.md` (prose CZ), optional `metadata.json` (tech specs), and `prices.json` (price matrix).

See `BLUEPRINT.md` for the schema and folder layout.

## Kategorie

| slug | význam |
|---|---|
| `pergola` | hlavní produkty |
| `vypln` | výplně (screen, zasklení, markýzy) |
| `prislusenstvi` | dokupované doplňky |
| `sluzba` | nezbožní položky (příplatky, montáž) |

## Workflow

### Day-0 bootstrap (už provedeno)

```sh
python3 scripts/init_xlsx.py     # vytvoří pricelist.xlsx z pricelist.json
```

### Denní editace

```sh
open pricelist.xlsx              # edituj v Numbers / Excel / LibreOffice

# po editaci:
python3 scripts/export_json.py   # přepočte pricelist.json
python3 scripts/export_json.py --dry-run   # preview změn bez zápisu

git add pricelist.json
git commit -m "update pricelist"
```

`pricelist.xlsx` se **nikdy necommitne**. Je jen na disku editora.

## Struktura

```
0-pricelist-alux/
├── pricelist.xlsx              canonical, not in git
├── pricelist.json              derived, in git
├── .gitignore
├── BLUEPRINT.md                schema spec
├── README.md                   (this file)
├── scripts/
│   ├── init_xlsx.py            bootstrap xlsx z pricelist.json
│   └── export_json.py          xlsx → pricelist.json
└── products/
    ├── pergola/<sku>/
    │   ├── knowledge.md        prose CZ
    │   ├── metadata.json       strukturované tech data (volitelné)
    │   └── prices.json         cenová matice (out of scope, netknuté)
    ├── vypln/<sku>/…
    ├── prislusenstvi/<sku>/…
    └── sluzba/<sku>/…
```

## Pravidla

1. **Jednosměrný sync**: `xlsx → json`. Nikdy zpět.
2. **Manuální export**: `python3 scripts/export_json.py` jen na pokyn.
3. **`pricelist.xlsx` v `.gitignore`**. Tracked je jen `pricelist.json`.
4. **Klíče anglicky, hodnoty česky.** Jediná výjimka: `display_name_cs` v `metadata.json`.
5. **SKU = název složky = `pricelist.json[*].sku`.** Žádné mapování.
6. **Pricing matrix out of scope.** `prices.json` se nedotýká z žádného skriptu.

## Pricing convention (důležité pro app developery)

`standard_price` a `price_formula` se čtou společně. **`standard_price = 1` je magic placeholder, ne reálná cena 1 CZK.**

| `standard_price` | `price_formula` | význam |
|---|---|---|
| číslo (≠ 1) | `null` | fixní cena, použij přímo |
| `1` | `"matrix"` | matice — vyhledej v `products/<category>/<sku>/prices.json` |
| `1` | `"<text>"` | formula — aplikuj vzorec (např. `"4% from price"`) |
| `1` | `null` | placeholder — cena ještě není definovaná |
| `null` | `null` | bez ceny |

Detail viz `BLUEPRINT.md` → sekce **Pricing convention**.

## Počty

- sloupce v `pricelist.json` se auto-detekují z xlsx (přidání sloupce nerozbije žádný skript)
- 22 položek celkem:
  - 10 pergol
  - 4 výplně (1 screen + 2 zasklení + 1 markýza)
  - 5 příslušenství
  - 3 služby / příplatky
