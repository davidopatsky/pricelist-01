# Pricelist consumers (briefing pro Claude Code)

> Krátký integration guide pro Claude Code instance v **jiných projektech** (web configurator, quoting tool, Raynet sync, …) které potřebují číst tento pricelist.

## Co tu je

Centrální ALUX pricelist. Single source of truth: 27 položek (pergoly, výplně, příslušenství, služby).

Repo: **`davidopatsky/pricelist-01`** (GitHub, **private** — fetch vyžaduje token).

## 1. Hlavní database

```
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/pricelist.json
```

JSON array, každý objekt má N polí (aktuálně 16, může přibývat — apps by měly číst po klíčích, ne po indexech):

```json
{
  "sku": "alux-bioclimatic",
  "category": "pergola",
  "name": "ALUX Bioclimatic",
  "name_en": "ALUX Bioclimatic",
  "description": "Bioklimatická pergola...",
  "standard_price": 1,
  "price_formula": "matrix",
  "currency": "CZK",
  "unit": "ks",
  "cost": 1,
  "cost_percent": 58,
  "discount": "0-22%",
  "delivery_weeks": "7-8",
  "color_summary": "RAL 7016 + RAL 9006",
  "raynet_description": "<p>HTML pro Raynet...</p>",
  "raynet_cost": null
}
```

`name_en` je volitelné — pokud je `null`, fallback na `name`.

`category` je jeden z: `pergola` / `vypln` / `prislusenstvi` / `elektro` / `priplatky` / `profily` / `sluzba`. SKU je join key.

## 2. ⚠️ Pricing convention — POVINNÉ ČÍST

**`standard_price = 1` je magic placeholder, NE reálná cena 1 CZK.**

Skutečná cena vychází z **kombinace** `standard_price` + `price_formula`:

| `standard_price` | `price_formula` | význam | co s tím |
|---|---|---|---|
| číslo (≠ 1) | `null` | **fixní cena** | použij `standard_price` přímo |
| `1` | `"matrix"` | **maticová cena** | fetchni `prices.json` produktu a vyhledej podle dimenzí |
| `1` | `"<text>"` | **formula** | aplikuj vzorec (např. `"4% from price"`) |
| `1` | `null` | **placeholder (TBD)** | cena ještě není známá → zobraz "na vyžádání" |
| `null` | `null` | **bez ceny** | nemá smysl prodávat samostatně |

Když uvidíš `standard_price === 1`, **nikdy** to nezobrazuj jako "1 CZK". Vždy se podívej na `price_formula`.

## 3. Per-product files (jen pro maticové / prose-rich produkty)

Každý SKU má složku `products/<category>/<sku>/`:

```
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/products/<category>/<sku>/prices.json
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/products/<category>/<sku>/metadata.json
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/products/<category>/<sku>/knowledge.md
```

### `prices.json` (jen pro produkty s `price_formula === "matrix"`)

**Single matrix:**
```json
{
  "type": "matrix",
  "horizontal_values": [2390, 2590, ...],   // šířky v mm
  "vertical_values":   [2000, 2100, ...],   // hloubky v mm
  "prices": [
    [81928, 84692, ...],
    ...
  ]
}
```

`prices[verticalIndex][horizontalIndex]` = cena v **CZK bez DPH**. `null` nebo `0` = "není dostupné v této dimenzi".

**Multi-matrix** (zasklení s 2D/3D/4D variantami):
```json
{
  "type": "multi-matrix",
  "variants": [
    { "label": "2D", "horizontal_values": [...], "vertical_values": [...], "prices": [...] },
    ...
  ]
}
```

### `metadata.json` (volitelné, jen pro produkty se strukturovanými daty)

Obsahuje `axes`, `horizontal_footer` (např. počet lamel), `display_name_cs`, `accessories_compatible`. Neexistuje pro jednoduché položky (např. `montaz`, `stojna-*`).

### `knowledge.md` (vždy)

Markdown s frontmatterem `sku:` a sekcemi `## Popis`, `## Specifikace`, případně `### Description (EN)`. Použij na detail page nebo info modal.

## 4. Authentication

Repo je private. Tvoje fetch musí mít hlavičku:

```
Authorization: Bearer <github_pat>
```

Token vygeneruj na github.com/settings/tokens (scope: `repo`). V Node:

```js
const headers = { 'Authorization': `Bearer ${process.env.GITHUB_TOKEN}` };
const items = await fetch(URL, { headers }).then(r => r.json());
```

## 5. Příklad — kompletní lookup

```js
const BASE = 'https://raw.githubusercontent.com/davidopatsky/pricelist-01/main';
const headers = { 'Authorization': `Bearer ${process.env.GITHUB_TOKEN}` };

const items = await fetch(`${BASE}/pricelist.json`, { headers }).then(r => r.json());

async function priceFor(sku, width_mm, depth_mm) {
  const item = items.find(i => i.sku === sku);
  if (!item) return null;

  // 1. Fixní cena
  if (item.standard_price !== 1 && item.price_formula == null) {
    return item.standard_price;
  }
  // 2. Matice
  if (item.price_formula === 'matrix') {
    const m = await fetch(
      `${BASE}/products/${item.category}/${item.sku}/prices.json`,
      { headers }
    ).then(r => r.json());
    const wIdx = m.horizontal_values.indexOf(width_mm);
    const dIdx = m.vertical_values.indexOf(depth_mm);
    if (wIdx < 0 || dIdx < 0) return null;
    return m.prices[dIdx][wIdx] || null;  // null = N/A in this dimension
  }
  // 3. Formula
  if (item.price_formula) {
    return { formula: item.price_formula };  // app must interpret
  }
  // 4. Placeholder / no price
  return null;
}
```

## 6. Caching

GitHub raw URL CDN cache TTL ~5 min. **Necachuj per-request** — fetchni `pricelist.json` jednou při startu, cachuj v paměti, refresh každých pár minut nebo po webhooku.

## 7. Pinning na verzi (volitelné)

Místo `main` můžeš pinnout commit hash:

```
https://raw.githubusercontent.com/davidopatsky/pricelist-01/<commit-sha>/pricelist.json
```

## 8. Když se něco rozbije

- Plný schema spec: `BLUEPRINT.md` v rootu repa
- Workflow + history: `BLUEPRINT.md` → sekce "Projektový kontext"
- Tento soubor (`CONSUMERS.md`) — pravidelně aktualizuju když se schema změní
