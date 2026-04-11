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
viewer.html
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

---

# Projektový kontext (recovery doc)

> Tahle sekce je samostatná briefing dokumentace pro novou AI session nebo nového člověka, který otvírá repo poprvé. Pokud spadne chat, čti odsud.

## Cíl projektu

Centralizovaný **pricelist + product database** pro firmu ALUX (pergoly, výplně, příslušenství, služby). Jediný zdroj pravdy pro:
- Web konfigurátor pergol
- Quoting tool
- Sync do Raynet CRM (přes HTML pole `raynet_description`)
- Případně další apps, které čtou raw JSON přes GitHub raw URL

GitHub repo: **`davidopatsky/pricelist-01`** (private).

## Inventář souborů (k 2026-04-11)

### Canonical (in git)

| cesta | účel |
|---|---|
| `pricelist.json` | derivovaný flat array, **single source pro apps** |
| `BLUEPRINT.md` | tento soubor |
| `README.md` | krátký workflow guide |
| `.gitignore` | excludes xlsx/viewer/macOS junk |
| `scripts/init_xlsx.py` | bootstrap `pricelist.xlsx` z `pricelist.json` |
| `scripts/export_json.py` | `pricelist.xlsx → pricelist.json`, jediný směr |
| `products/<cat>/<sku>/knowledge.md` | prose CZ + EN/DE sekce v frontmatteru/sekcích |
| `products/<cat>/<sku>/metadata.json` | strukturovaná tech data (axes, lamela counts, …) — jen pro produkty co to potřebují |
| `products/<cat>/<sku>/prices.json` | cenové matice (out of scope skriptů — netknuté) |

### Local-only (gitignored)

| cesta | důvod |
|---|---|
| `pricelist.xlsx` | canonical edit surface, edituje se v Numbers/Excel; nikdy se necommituje |
| `viewer.html` | starý HTML viewer z předchozí iterace (v3), nečte v6 schema, mimo workflow |
| `temp/pricelist.xlsx` | původní upload uživatele z předchozí konverzace; sandbox |
| `.DS_Store`, `__pycache__/`, `~$*.xlsx`, `.~lock.*#` | OS/editor junk |

### Legacy / kandidáti na úklid (zatím v repu, nejsou potřeba)

| cesta | proč legacy | doporučení |
|---|---|---|
| `meta.json` | v2 config s **starými 6 kategoriemi** (pergola/screen/glazing/awning/accessories/extras) a starými field jmény (`commerce.cost_percent`). Žádný současný skript ho nečte. | smazat |
| `export/pricelist.xlsx` | duplicitní xlsx s celými cenovými maticemi z dřívějšího experimentu (v3 éra). 208 KB. | smazat |
| `export/salesqueze-export/` | starý export skript pro SalesQueeze, čte neexistující `item.json` (v3 schema), podle blueprintu **out of scope, postaví se znova od nuly později**. 548 KB. | smazat nebo nechat pro historii |
| `viewer.html` | gitignored, ale fyzicky na disku. Stará verze, nečte v6. | možno smazat z disku |

**Pokud delete nepřipadá v úvahu** (uživatel říká "nic nemazat"): nech být. Skripty se jich nedotýkají, jen zaberou místo.

## Schema version history

| verze | datum | tvar | proč skončila |
|---|---|---|---|
| v1 | původní | 4 root folders: `products/`, `pricing/`, `accessories/`, `pricing-accessories/` s deeply nested JSON | rigidní info/pricing split, nested language objects, většina null |
| v2 | early refactor | flat `pergola/<sku>/item.json` | flatten dropped některá pole (display_name, axes) |
| v3 | category folders | `pergola/<sku>/{item.json, prices.json}` v rootu | uživatel chtěl "products" parent folder |
| v4 | products parent | `products/<cat>/<sku>/{item.json, prices.json}` | uživatel chtěl xlsx round-trip + Raynet-shape |
| v5 (paused) | Raynet-shape | rename `sku → code`, přidány `product_line` a další | uživatel řekl "don't remove sku" + plán znovu |
| **v6.0** | blueprint | 4 nové kategorie (`pergola`, `vypln`, `prislusenstvi`, `sluzba`), per-item `knowledge.md` + `metadata.json` + `prices.json`, root `pricelist.json` (14 polí), one-way `xlsx → json` workflow | uživatel přidal Raynet sloupce |
| **v6.1** *(current)* | + Raynet | drop `product_line`, add `raynet_description` + `raynet_cost`, total **15 polí** | — |

## Klíčová rozhodnutí (decisions log)

1. **JSON je canonical at rest, XLSX je canonical for editing.** Apps čtou JSON přes raw GitHub URL. Editor edituje XLSX v Numbers/Excel. `xlsx → json` je jednosměrný export přes `scripts/export_json.py`. **Žádný auto-watcher, žádný roundtrip.**
2. **`pricelist.xlsx` v `.gitignore`.** Jen `pricelist.json` jde do gitu. XLSX je local-only artifact.
3. **SKU je join key.** SKU = název složky `products/<cat>/<sku>/` = `pricelist.json[*].sku`. Žádné mapování, žádné aliasy.
4. **`standard_price = 1` je magic placeholder, ne 1 CZK.** Real meaning je v `price_formula`. Detail v sekci "Pricing convention" výše. Důvod proč `1` a ne `"matrix"` přímo: Numbers/Excel auto-konvertují string v jinak číselném sloupci.
5. **`pricing.json` matrices jsou out of scope všech skriptů.** Editují se ručně. `init_xlsx.py` ani `export_json.py` se jich nedotknou.
6. **Klíče anglicky, hodnoty česky.** Jediná výjimka: `display_name_cs` v `metadata.json` (kvůli prezentační vrstvě).
7. **Per-product `metadata.json` je volitelná.** Vytváří se jen pro produkty co mají strukturovaná tech data (osy, lamela counts, kompatibility…). Jednoduché položky jako `montaz` ji nemají.
8. **`knowledge.md` má frontmatter s `sku`.** Krom toho zachovává multilingvní data v sekcích `### Description (EN)` a `### Beschreibung (DE)` — i když `pricelist.json` má jen jednu jazykovou variantu.
9. **Raynet sync.** `raynet_description` (HTML, multi-line) a `raynet_cost` jsou specifické pro sync do Raynet CRM. Když jsou null, položka se do Raynetu neposílá nebo se vezmou defaulty.
10. **`product_line` byl dropnut ve v6.1.** Je odvoditelný z prefixu SKU (`alux-*` → ALUX, `strada-*` → Strada, `simple-*` → Simple, `somfy_*` → Somfy). Pokud ho budou apps potřebovat, dopočítají si ho samy.

## Jak obnovit kontext (recovery)

**Pokud spadne chat a otevřeš nový session:**

1. Přečti tenhle blueprint celý. Začni od horní části (Strom složek).
2. Spusť `python3 scripts/export_json.py --dry-run` — pokud řekne "No changes. N items.", repo je v synchronu.
3. `git log --oneline -5` — uvidíš poslední commits.
4. `cat pricelist.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d), 'items')"` — kolik je teď položek.
5. `find products -type d -mindepth 2 -maxdepth 2 | sort` — strom všech SKU folderů.

**Pokud uživatel řekne "edituj cenu položky X":**
- Uprav `pricelist.xlsx` v Numbers nebo přímo v `pricelist.json` (oba jsou OK, ale json edit musí být následován bootstrap přes `init_xlsx.py` aby se přepsal xlsx zpět na disk)
- `python3 scripts/export_json.py` (pokud editoval xlsx) NEBO `python3 scripts/init_xlsx.py` (pokud editoval json)
- `git add pricelist.json && git commit -m "..." && git push`

**Pokud uživatel řekne "přidej produkt":**
- Přidej řádek do xlsx (nebo do json, viz výše)
- Vytvoř `products/<cat>/<sku>/knowledge.md` (skeleton se sekcemi Popis, Specifikace)
- (optional) `metadata.json` a `prices.json` pokud je to maticový produkt
- Export + commit + push

**Pokud uživatel řekne "smaž produkt":**
- Vymaž řádek z xlsx
- `python3 scripts/export_json.py` přepíše json
- Smaž `products/<cat>/<sku>/` celý folder
- Commit + push

## Open TODO / known issues

- Žádné aktivní bugy ke 2026-04-11.
- `viewer.html` je stale a mimo workflow — pokud ho někdy chceš znovu, musí se rebuildnout aby četl `pricelist.json` (ne starý `item.json`).
- `export/salesqueze-export/` neběží — blueprint říká "postaví se znova od nuly později".
- Žádná validace `cost_percent ∈ [0, 100]`, žádná validace SKU formátu (kebab-case). Můžeme přidat do `export_json.py` až bude potřeba.

## Backup pointers (na disku, mimo repo)

- `/tmp/pricelist-alux-backup-20260411-154757/` — v1 stav (původní 4 folders)
- `/tmp/pricelist-alux-v6-backup-20260411-233022/` — v5 stav před v6 migrací (products/scripts/meta.json/viewer.html/pricelist.xlsx/README.md)

Pokud `/tmp` zmizí (reboot), backupy se ztratí. Pro permanentní backup je git history.
