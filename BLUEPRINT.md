# Pricelist v6 — finální struktura

## Strom složek

```
<root>/
├── pricelist.xlsx                ← canonical, NOT in git (.gitignore)
├── pricelist.json                ← derived, IN git, konzumují appky
├── .gitignore
├── README.md
├── scripts/
│   ├── init_xlsx.py              ← bootstrap xlsx z hardcoded sample dat (jen pro day-0)
│   └── export_json.py            ← xlsx → pricelist.json (one-way, manual)
└── products/
    ├── pergola/
    │   └── <sku>/
    │       ├── knowledge.md      ← prose CZ
    │       ├── metadata.json     ← strukturovaná tech data
    │       └── prices.json       ← cenová matice (out of scope)
    ├── vypln/
    │   └── <sku>/ …
    ├── prislusenstvi/
    │   └── <sku>/ …
    └── sluzba/
        └── <sku>/ …
```

## `pricelist.xlsx` — canonical edit surface

- **15 sloupců**, fixní pořadí
- **freeze panes**: `A2` (header zamrzlý)
- **text format `@`** pinned na: `sku`, `category`, `name`, `description`, `price_formula`, `currency`, `unit`, `discount`, `delivery_weeks`, `color_summary`, `raynet_description` (zabraňuje Numbers/Excel auto-konverzím SKU jako `2024-01` → datum)
- **numeric format `#,##0`** na: `cost`, `cost_percent`, `raynet_cost`
- **wrap text** na: `description`, `color_summary`, `raynet_description`
- **auto-width** sloupců, capped na 50 znaků
- žádný limit počtu řádků

## `pricelist.json` — derived, flat array

```json
[
  {
    "sku": "alux-bioclimatic",
    "category": "pergola",
    "name": "ALUX Bioclimatic",
    "description": "Bioklimatická pergola s otočnými lamelami…",
    "standard_price": "matrix",
    "price_formula": null,
    "currency": "CZK",
    "unit": "ks",
    "cost": null,
    "cost_percent": 58,
    "discount": "0%",
    "delivery_weeks": "6-8",
    "color_summary": "rám RAL 7016, lamely RAL 9006/7016",
    "raynet_description": "<p>HTML popis pro Raynet…</p>",
    "raynet_cost": null
  }
]
```

## Schema — 15 polí

| # | klíč | typ | povinné | příklad | poznámka |
|---|---|---|---|---|---|
| 1 | `sku` | string | ✓ | `alux-bioclimatic` | join key, unique, beze změny napříč systémy |
| 2 | `category` | enum | ✓ | `pergola` | jedna z: `pergola`, `vypln`, `prislusenstvi`, `sluzba` |
| 3 | `name` | string | ✓ | `ALUX Bioclimatic` | krátký název CZ |
| 4 | `description` | string | – | `Bioklimatická pergola…` | jedna věta CZ |
| 5 | `standard_price` | number \| null | – | `8500` / `1` / `null` | fixní cena. Pokud je `1`, funguje jako placeholder — viz **Pricing convention** níže. |
| 6 | `price_formula` | string \| null | – | `"matrix"` / `"4% from price"` / `null` | flag/vzorec když cena není fixní. `"matrix"` = "vyhledej v `prices.json`". Jinak human-readable formula. |
| 7 | `currency` | string | ✓ | `CZK` | ISO kód |
| 8 | `unit` | string | ✓ | `ks` / `m²` / `hod` / `m` | jednotka prodeje |
| 9 | `cost` | number \| null | – | `4250` | nákupní cena |
| 10 | `cost_percent` | number \| null | – | `58` | marže nákladu jako % z prodejní |
| 11 | `discount` | string | – | `"0%"` | obchodní sleva (text kvůli `%`) |
| 12 | `delivery_weeks` | string | – | `"4-6"` | dodací lhůta jako text (rozsah) |
| 13 | `color_summary` | string | – | `RAL 7016 + RAL 9006` | textové shrnutí barevných variant |
| 14 | `raynet_description` | string \| null | – | `<p>HTML popis…</p>` | HTML popis pro sync do Raynet CRM |
| 15 | `raynet_cost` | number \| null | – | `1200` | náklad pro Raynet (override pokud se liší od `cost`) |

## Pricing convention

`standard_price` a `price_formula` se čtou společně. Aplikace, které konzumují `pricelist.json`, musí oba sloupce kombinovat:

| `standard_price` | `price_formula` | význam | jak app spočítá cenu |
|---|---|---|---|
| `<číslo>` | `null` | **fixní cena** | použij `standard_price` přímo |
| `1` | `"matrix"` | **maticová cena** | otevři `products/<category>/<sku>/prices.json` a vyhledej cenu podle dimenzí |
| `1` | `"<text>"` | **formula cena** | aplikuj vzorec z `price_formula` (např. `"4% from price"`, `"1300 czk per m2 of pergola"`) |
| `1` | `null` | **placeholder** | cena ještě není definovaná, zobraz jako "na vyžádání" / "TBD" |
| `null` | `null` | **bez ceny** | položka nemá cenu (např. obsoletní záznam) |

**Klíčový bod:** `1` v `standard_price` **není reálná cena 1 CZK** — je to magic placeholder. Reálnou cenu vždy určuje kombinace s `price_formula`.

Proč `1` a ne `null` nebo `"matrix"` přímo v `standard_price`? Numbers/Excel mají problém zachovat string `"matrix"` v jinak číselném sloupci a `null` se v xlsx neumí vyjádřit jednoznačně. `1` je validní číslo, které xlsx editor neporušuje.

## 4 kategorie (Czech, no diacritics)

| slug | význam | typický obsah |
|---|---|---|
| `pergola` | hlavní produkty | bioclimatic, carbo, glass, ram, thermo, … |
| `vypln` | výplně do pergoly / okolo | screeny, zasklení, markýzy |
| `prislusenstvi` | dokupované doplňky | stojny, ovladače, čidla, motory |
| `sluzba` | nezbožní položky | montáž, doprava, příplatky |

## Per-product folder — `products/<category>/<sku>/`

### `knowledge.md` (vždy)

```markdown
---
sku: alux-bioclimatic
---

# ALUX Bioclimatic

## Popis
Bioklimatická pergola s otočnými lamelami…

## Barvy a povrchy
- rám: RAL 7016 standard, jiné RAL na vyžádání
- lamely: RAL 9006 / RAL 7016 Axalta jemná struktura

## Specifikace
- max šířka: 6000 mm
- max hloubka: 4500 mm
- motor: Somfy IO

## Použití
…
```

- prose, čeština
- frontmatter musí obsahovat `sku` (= název složky)
- volné sekce, žádné rigidní schema

### `metadata.json` (jen když produkt potřebuje strukturovaná tech data)

```json
{
  "sku": "alux-bioclimatic",
  "display_name_cs": "ALUX Bioclimatic - rám RAL 7016, lamely RAL 9006/7016",
  "axes": {
    "horizontal": { "label": "šířka",  "unit": "mm" },
    "vertical":   { "label": "hloubka", "unit": "mm" }
  },
  "horizontal_footer": {
    "label": "počet lamel",
    "values": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
  },
  "motor": "Somfy IO",
  "odvodneni": "integrované v rámu",
  "accessories_included": [],
  "accessories_compatible": ["stojna-120-3000", "screen-zip-120"]
}
```

- **`display_name_cs` výjimka** — jediné pole se sufixem `_cs`, schválně, kvůli prezentační vrstvě
- ostatní klíče anglicky, hodnoty česky
- volné schema per produkt — `axes`, `motor`, `fabric`, `guide`, `max_width_mm` atd. podle toho, co produkt vyžaduje
- **`accessories_compatible`** = pole SKUs, slouží k cross-link doplňků
- jednoduché produkty (např. statická stojna) `metadata.json` nemají

### `prices.json` (out of scope)

Cenová matice. **Nedotýká se v tomhle kroku.** Až později.

## Pravidla, která se nemění

1. **Jednosměrný sync** `xlsx → json`. Nikdy zpět. Žádný auto-watcher.
2. **Manuální export.** `python3 scripts/export_json.py` jen na pokyn.
3. **`pricelist.xlsx` v `.gitignore`.** Tracked je jen `pricelist.json`.
4. **Klíče anglicky, hodnoty česky.** Jediná výjimka: `display_name_cs`.
5. **SKU = název složky = `pricelist.json[*].sku`.** Žádné mapování.
6. **Pricing matrix out of scope.** `prices.json` zůstane nedotčená.
7. **SalesQueze export out of scope.** Bude se stavět od nuly později.
8. **Konzumace appkami:** přes raw GitHub URL na `pricelist.json`.

## Workflow

**Day-0 bootstrap (jednou):**

```sh
python3 scripts/init_xlsx.py     # vytvoří pricelist.xlsx z sample dat
python3 scripts/export_json.py   # vytvoří pricelist.json
```

**Daily edit:**

```sh
open pricelist.xlsx              # editace v Numbers
# … po editaci:
python3 scripts/export_json.py   # přepočte pricelist.json
git add pricelist.json
git commit -m "update pricelist"
```

`pricelist.xlsx` se nikdy necommitne. Je jen na disku editora.

## `.gitignore`

```
pricelist.xlsx
.DS_Store
__pycache__/
*.pyc
*.pyo
*.swp
*~
~$*.xlsx
.~lock.*#
```

(`~$*.xlsx` a `.~lock.*#` jsou Excel/LibreOffice lock files vytvářené při otevření souboru.)
