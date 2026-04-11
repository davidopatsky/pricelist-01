# Pricelist data structure — the dilemma + a proposal

> **Briefing document for Claude.** Read before touching the folder structure.
> Last updated: 2026-04-11.

## TL;DR — proposed shape

- **One source of truth** = `pricelist.json` at the root: a flat JSON array of all 22 items. Every field you'd see as a column in Excel lives here. This IS the database.
- **Per-product folders** = `products/<category>/<sku>/` holding three files:
  - `knowledge.md` — long-form prose, multi-language (marketing, specs, description)
  - `technical.json` — structured extras that don't fit a spreadsheet cell (axes, lamela counts, accessory compat)
  - `prices.json` — the price matrix (products only)
- **SKU is the join key**. Folder name = SKU = `pricelist.json[i].sku`.
- **Excel stays as a derived mirror**: `pricelist.xlsx` is regenerated from `pricelist.json` anytime, round-trippable via sync script.
- **Nothing is deleted**; all previously dropped data is restored from backup.

```
/Users/david/Projects/0-pricelist-alux/
├── pricelist.json                          ← MAIN DATABASE (flat list)
├── pricelist.xlsx                          ← derived mirror, open in Excel
├── meta.json
├── viewer.html                             ← inline editor for pricelist.json
├── README.md  BLUEPRINT.md  docs/
└── products/
    └── <category>/
        └── <sku>/
            ├── knowledge.md
            ├── technical.json
            └── prices.json
```

---

## 1. The context (what the user is actually trying to build)

ALUX pricelist: 22 items today (10 pergolas, 1 screen, 2 glazings, 1 awning, 5 accessories, 3 surcharges). Consumed by a web configurator, quoting tool, and other apps via raw GitHub URLs. Edited by one person + Claude. Versioned in Git.

Each item has two kinds of data:

| Kind | Examples | Fits in a spreadsheet cell? |
|---|---|---|
| **Commercial** | SKU, name, short description, price, cost, currency, unit, discount, delivery time, category, product line, one-line color summary | ✅ |
| **Rich / technical** | full marketing description, price matrices (hundreds of cells), axis labels, lamela count lists, accessory compatibility, per-language long-form product knowledge | ❌ |

**The dilemma**: where do you draw the line, and how do you keep both sides linked?

## 2. The user's hard constraints

Confirmed in earlier turns; do not violate:

- [x] **One big database** that feels like Excel (user says: "ideally looks like an excel or is actually an excel")
- [x] **Don't delete anything** — every field from previous iterations must survive somewhere
- [x] **Keep `sku`** as the field name. Do NOT rename to `code`
- [x] **Split** commercial fields (main DB) from detailed per-product data (product folder)
- [x] **Interconnect** via SKU
- [x] **JSON is Git-tracked**, apps fetch raw URLs
- [x] **Viewer is a flat table**, no submenus or detail views
- [x] **Stay inside** `/Users/david/Projects/0-pricelist-alux/` — no other folders
- [x] **No Raynet audit bloat** (no created_at, modified_by, valid_from, tags, entity_id)
- [x] **Manual sync** — user runs `rebuild_xlsx.py` / `sync_from_xlsx.py` explicitly

## 3. History of iterations (what we tried, what broke)

| Version | Shape | Why it broke |
|---|---|---|
| v1 | `products/`, `pricing/`, `accessories/`, `pricing-accessories/` at root with deeply nested JSON (`names{cs,en,de,pl,hu}`, `commerce{…}`, `axes{…}`) | Too many folders, most language slots always null, rigid info/pricing split |
| v2 | Flattened `pergola/<sku>/item.json` with scalar fields | Flatten dropped `display_name_cs`, `horizontal_footer`, `axes` — data loss |
| v3 | Category folders moved under `products/<cat>/<sku>/` | Mostly OK but user then said the DB should look like Excel with Raynet-style columns |
| v4 (paused) | Raynet-shaped `item.json` with `code` instead of `sku` | User said "don't remove sku" and asked to plan before more changes |
| **v5 (this proposal)** | One `pricelist.json` + `products/<cat>/<sku>/{knowledge.md, technical.json, prices.json}` | — |

## 4. The proposed rule for drawing the line

> **If a value fits in a single Excel cell, it goes in `pricelist.json`.**
> **If it's prose, a big list, a matrix, or a nested object, it goes in the product folder.**

| Data | Location | Rationale |
|---|---|---|
| `sku` | `pricelist.json` + folder name | the join key |
| `category`, `product_line` | `pricelist.json` (folder path mirrors category) | table filtering |
| `name_cs`, `name_en` | `pricelist.json` | single scalars |
| Short description (1-2 sentences) | `pricelist.json` → `description_cs/en/de` | fits in a cell |
| `standard_price` | `pricelist.json` (`"matrix"` or number) | the commercial price |
| `cost`, `cost_percent` | `pricelist.json` | commercial |
| `discount`, `delivery_weeks` | `pricelist.json` | commercial |
| `currency`, `unit` | `pricelist.json` | commercial |
| One-line color summary | `pricelist.json` → `color_summary` | fits in a cell |
| — | | |
| Long marketing description (paragraphs) | `knowledge.md` (CZ/EN/DE sections) | prose |
| Full color + RAL spec | `knowledge.md` | prose |
| Product features, use cases | `knowledge.md` | prose |
| — | | |
| `display_name_cs` (longer marketing name) | `technical.json` | short structured extra |
| `axes` (label + unit per dimension) | `technical.json` | nested object |
| `horizontal_footer` (lamela counts) | `technical.json` | structured array |
| `accessories_included`, `accessories_compatible` | `technical.json` | SKU refs |
| — | | |
| Price matrix | `prices.json` | 2D number array, hundreds of cells |

## 5. Concrete shapes

### `pricelist.json`

```jsonc
{
  "meta": {
    "version": "5.0",
    "exported_at": "2026-04-11",
    "currency_default": "CZK",
    "vat_rate_default": 21
  },
  "items": [
    {
      "sku": "alux-bioclimatic",
      "category": "pergola",
      "product_line": "ALUX",
      "name_cs": "ALUX Bioclimatic",
      "name_en": "ALUX Bioclimatic",
      "description_cs": "Bioklimatická pergola - barva rámu RAL 7016...",
      "description_en": null,
      "description_de": null,
      "standard_price": "matrix",
      "currency": "CZK",
      "unit": "ks",
      "cost": null,
      "cost_percent": 58,
      "discount": "0-22%",
      "delivery_weeks": "7-8",
      "color_summary": "Rám RAL 7016, lamely RAL 9006 / 7016"
    },
    {
      "sku": "stojna-120-3000",
      "category": "accessory",
      "product_line": null,
      "name_cs": "stojna profil 120 x 120 - 3000 mm",
      "name_en": "Column 120 x 120 mm - 3000 mm",
      "description_cs": "Stojna profil 120 x 120 mm",
      "description_en": null,
      "description_de": null,
      "standard_price": 5100,
      "currency": "CZK",
      "unit": "ks",
      "cost": 2900,
      "cost_percent": null,
      "discount": null,
      "delivery_weeks": null,
      "color_summary": "RAL 7016"
    }
  ]
}
```

- `description_cs` is the SHORT 1-2 line version for the table. Full version goes in `knowledge.md`.
- `color_summary` is the short table-friendly version. Detailed color + RAL info goes in `knowledge.md`.

### `products/pergola/alux-bioclimatic/knowledge.md`

```markdown
---
sku: alux-bioclimatic
---

# ALUX Bioclimatic

## CZ

Bioklimatická pergola s otočnými lamelami, které se ovládají motorizovaně.
Rám RAL 7016, lamely RAL 9006 nebo RAL 7016 v Axalta jemné struktuře.

(full long-form description — paragraphs, bullet lists, whatever)

## EN

Bioclimatic pergola with adjustable louvers...

## DE

(optional)

## Barvy a povrchy

Rám: RAL 7016 (standard), jiné barvy na dotaz.
Lamely: RAL 9006 / RAL 7016 Axalta jemná struktura. Jiné barvy individuálně.

## Specifikace

- Motor: Somfy IO
- Odvodnění: integrované v rámu
- …
```

### `products/pergola/alux-bioclimatic/technical.json`

```json
{
  "sku": "alux-bioclimatic",
  "display_name_cs": "ALUX Bioclimatic - barva rámu RAL 7016, barva lamel RAL9006/7016 Axalta jemná struktura",
  "axes": {
    "horizontal": { "label": "šířka", "unit": "mm" },
    "vertical":   { "label": "hloubka", "unit": "mm" }
  },
  "horizontal_footer": {
    "label": "počet lamel",
    "values": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
  },
  "accessories_included": [],
  "accessories_compatible": []
}
```

### `products/pergola/alux-bioclimatic/prices.json`

Unchanged from today. Same schema (single-matrix or multi-matrix with `horizontal_values`, `vertical_values`, `prices`).

## 6. Open questions — what a Claude should ask the user before executing

1. **Main DB filename**: `pricelist.json` (proposed), or prefer `database.json` / `items.json`?
2. **Knowledge file layout**: one `knowledge.md` with CZ/EN/DE sections inside (proposed), OR separate files `knowledge.cs.md`, `knowledge.en.md`, `knowledge.de.md`?
3. **`technical.json` as a separate file** (proposed), OR fold its handful of fields into `pricelist.json` (risks bloating the DB with axes/lamela counts)?
4. **Always create `knowledge.md`** for every product (even empty skeletons), or only when there's content to put in it?
5. **Where does `color_summary` live** — in `pricelist.json` (one-line summary, proposed) or always in `knowledge.md` (full detail only, leave the DB column empty)?
6. **Extras (`extras/`)** — surcharges like `extra-ral-ram` have "4% percent from price" as a formula string. Should `standard_price` hold that string, or should we add a `price_formula` field?

## 7. What the Claude will do AFTER approval

Execute these steps in one sequence, then dry-run + show a diff:

1. Revert `code` → `sku` in all existing item.json (non-destructive string rename).
2. Read all 22 item.json + `/tmp/pricelist-alux-backup-20260411-154757/` for dropped fields.
3. Write `pricelist.json` at the root with the flat items array.
4. Write `products/<cat>/<sku>/technical.json` per product with the structured extras.
5. Write `products/<cat>/<sku>/knowledge.md` skeleton (header + empty CZ/EN/DE sections) per product.
6. Delete old per-item `item.json` (their data has moved to `pricelist.json` + `technical.json`).
7. Regenerate `pricelist.xlsx` from `pricelist.json`.
8. Update `viewer.html` to read + edit `pricelist.json` directly (not per-item files).
9. Update `scripts/rebuild_xlsx.py` (reads `pricelist.json`).
10. Update `scripts/sync_from_xlsx.py` (writes `pricelist.json`, preserves `technical.json` untouched).
11. Update `export/salesqueze-export/export.js` to read `pricelist.json` + `products/**/prices.json`.
12. Update `BLUEPRINT.md`, `README.md`, `meta.json`.
13. Show a summary of every file changed/created/deleted and wait for confirmation before committing.

## 8. What will NOT change

- Any `prices.json` matrix — untouched
- The folder layout under `products/<category>/<sku>/`
- The category names (`pergola`, `screen`, `glazing`, `awning`, `accessories`, `extras`)
- The Excel column shape (still Raynet-inspired subset)
- The File System Access API save path in the viewer

## 9. Counter-proposal slot (if another Claude / the user disagrees)

If the "one cell rule" is too coarse, alternatives:

- **Alt A — Everything in `pricelist.json`**: no `technical.json`, axes + lamela counts go into the big file as nested objects. Simpler (one source), uglier DB rows.
- **Alt B — Two main files**: `pricelist.json` (commercial) + `pricelist-technical.json` (structured extras), both at the root. No per-product `technical.json`. Closer to the original "two-folder rule".
- **Alt C — Only `pricelist.json` + `prices.json` per product**: drop the knowledge.md / technical.json idea. Put long descriptions into `pricelist.json` as `description_cs_long`. Works but `pricelist.json` gets wide.
- **Alt D — Excel as the canonical source**: drop `pricelist.json`. Edit `pricelist.xlsx` directly. Run a script that reads the xlsx and produces raw JSON for apps. Downside: hard for Claude to edit surgically, harder git diffs.
